# =============================================================================
# HYDRA-UMC EDITOR-URDF - render/viewport.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real-time 3D viewport for an arbitrary, freshly-imported URDF -
# QOpenGLWidget + a small GLSL shader (core profile), structurally a port
# of HYDRA-UMC-SUITE's own render/viewport.py (per [[No reference -> reuse,
# don't invent]]) generalized from "pose one of a fixed registry of KNOWN
# robots" to "pose whatever models.Robot the operator just imported."
#
# Z-UP world, not Y-up - this is the one deliberate divergence from
# HYDRA-UMC-SUITE's own viewport: URDF itself is a Z-up format (gravity
# is -Z, a robot's own <origin>/<axis> are authored assuming it), and
# this app's job is to show/edit a URDF faithfully in ITS OWN convention,
# not re-orient it into whatever a downstream viewer (Three.js/SUITE's
# OpenGL scene) happens to prefer - see render/kinematics.py's own header.
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
from OpenGL import GL as gl
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from hydra_editor_urdf.models import BoxGeometry, CylinderGeometry, Material, MeshGeometry, Robot, SphereGeometry, Visual
from hydra_editor_urdf.render.kinematics import compute_link_world_transforms, default_joint_values, origin_to_matrix
from hydra_editor_urdf.render.mesh import Mesh, UnsupportedMeshFormat, load_mesh_file, make_box_mesh, make_cylinder_mesh, make_sphere_mesh

VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat3 uNormalMatrix;

out vec3 vNormalWorld;
out vec3 vPositionWorld;

void main() {
    vec4 worldPos = uModel * vec4(inPosition, 1.0);
    vPositionWorld = worldPos.xyz;
    vNormalWorld = normalize(uNormalMatrix * inNormal);
    gl_Position = uProjection * uView * worldPos;
}
"""

FRAGMENT_SHADER = """
#version 330 core
in vec3 vNormalWorld;
in vec3 vPositionWorld;

uniform vec3 uBaseColor;
uniform float uAlpha;
uniform vec3 uCameraPos;
uniform vec3 uSelectHighlight;  // added to color when this link is selected in the properties panel

out vec4 fragColor;

void main() {
    // Lit from "above" in Z-up world, not Y-up - keeps the same 2-light
    // rig HYDRA-UMC-SUITE's own shader uses, just re-aimed for this
    // viewport's own up axis.
    vec3 lightDir1 = normalize(vec3(0.5, 0.6, 0.8));
    vec3 lightDir2 = normalize(vec3(-0.4, -0.5, 0.3));
    vec3 n = normalize(vNormalWorld);

    float diffuse1 = max(dot(n, lightDir1), 0.0);
    float diffuse2 = max(dot(n, lightDir2), 0.0) * 0.35;
    float ambient = 0.28;

    vec3 viewDir = normalize(uCameraPos - vPositionWorld);
    vec3 halfVec = normalize(lightDir1 + viewDir);
    float spec = pow(max(dot(n, halfVec), 0.0), 32.0) * 0.4;

    float rim = pow(1.0 - max(dot(n, viewDir), 0.0), 3.0) * 0.5;
    vec3 rimColor = vec3(0.13, 0.83, 0.93);

    vec3 color = uBaseColor * (ambient + diffuse1 + diffuse2) + vec3(spec) + rimColor * rim + uSelectHighlight;
    fragColor = vec4(color, uAlpha);
}
"""


def perspective(fovy_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / np.tan(np.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, 0:3] = s
    m[1, 0:3] = u
    m[2, 0:3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


class GLMeshBuffer:
    """One VBO holding a single visual's interleaved position+normal data."""

    def __init__(self, mesh: Mesh):
        interleaved = np.hstack([mesh.vertices, mesh.normals]).astype(np.float32)
        self.vertex_count = len(mesh.vertices)
        self.vao = gl.glGenVertexArrays(1)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, interleaved.nbytes, interleaved, gl.GL_STATIC_DRAW)
        stride = 6 * 4
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, gl.ctypes.c_void_p(3 * 4))
        gl.glEnableVertexAttribArray(1)
        gl.glBindVertexArray(0)

    def draw(self) -> None:
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.vertex_count)
        gl.glBindVertexArray(0)


DEFAULT_COLOR = (0.72, 0.75, 0.80)


class UrdfViewport(QOpenGLWidget):
    """Orbit camera (left-drag rotate, wheel zoom, right/middle-drag pan)
    over whatever models.Robot is currently loaded - rebuilt from scratch
    (rebuild_buffers()) every time a new URDF is imported or a link's own
    geometry/scale changes; re-posed cheaply (set_joint_values()) on every
    jog-preview slider move, which does NOT touch the GPU buffers at all,
    only the per-visual model matrix computed at draw time."""

    def __init__(self, mesh_resolver: Callable[[str], "Path | None"], parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._mesh_resolver = mesh_resolver
        self._program: int | None = None
        self._gl_ready = False

        self._robot: Robot | None = None
        self._joint_values: dict[str, float] = {}
        self._selected_link: str | None = None

        # (link_name, visual_index) -> GLMeshBuffer - rebuilt wholesale by
        # rebuild_buffers(), not incrementally patched, since a geometry/
        # scale edit anywhere in the tree is rare enough (compared to a
        # jog-slider move, which is the actual hot path) that simplicity
        # wins over partial-update bookkeeping.
        self._buffers: dict[tuple[str, int], GLMeshBuffer] = {}
        self._colors: dict[tuple[str, int], tuple[float, float, float, float]] = {}
        self._pending_robot: Robot | None = None  # set by rebuild_buffers() before GL is ready; consumed in initializeGL

        self._yaw = -35.0
        self._pitch = 20.0
        self._distance = 1.5
        self._target = np.array([0.0, 0.0, 0.2], dtype=np.float32)
        self._last_mouse_pos: QPointF | None = None
        self._drag_button: Qt.MouseButton | None = None

    # --- public API used by app.py / ui/panels ---------------------------------

    def set_selected_link(self, link_name: str | None) -> None:
        self._selected_link = link_name
        self.update()

    def set_joint_values(self, values: dict[str, float]) -> None:
        self._joint_values = dict(values)
        self.update()

    def rebuild_buffers(self, robot: Robot | None) -> None:
        """Call after loading a new URDF, or after any edit that changes
        a link's geometry/scale/material set (adding/removing a visual,
        changing a mesh's scale, retyping a joint that changes DOF but
        not the tree shape). Cheap edits that only change a NUMBER
        already on screen (recolor, jog) should call the narrower
        set_joint_values()/refresh_colors() instead of paying for a full
        GPU re-upload."""
        self._robot = robot
        self._joint_values = default_joint_values(robot) if robot is not None else {}
        if not self._gl_ready:
            self._pending_robot = robot
            return
        self._rebuild_buffers_now(robot)

    def refresh_colors(self) -> None:
        """Cheap path for "operator picked a new color for this link's
        visual" - no GPU buffer changes needed, just the cached rgba this
        widget reads at draw time."""
        if self._robot is None:
            return
        self._colors = self._collect_colors(self._robot)
        self.update()

    @staticmethod
    def _collect_colors(robot: Robot) -> dict[tuple[str, int], tuple[float, float, float, float]]:
        colors: dict[tuple[str, int], tuple[float, float, float, float]] = {}
        for link in robot.links.values():
            for i, visual in enumerate(link.visuals):
                colors[(link.name, i)] = visual.material.rgba if visual.material is not None else (*DEFAULT_COLOR, 1.0)
        return colors

    def _rebuild_buffers_now(self, robot: Robot | None) -> None:
        self.makeCurrent()
        try:
            self._buffers = {}
            if robot is not None:
                self._colors = self._collect_colors(robot)
                for link in robot.links.values():
                    for i, visual in enumerate(link.visuals):
                        mesh = self._build_visual_mesh(visual)
                        if mesh is not None:
                            self._buffers[(link.name, i)] = GLMeshBuffer(mesh)
        finally:
            self.doneCurrent()
        self.update()

    def _build_visual_mesh(self, visual: Visual) -> Mesh | None:
        geometry = visual.geometry
        if isinstance(geometry, BoxGeometry):
            return make_box_mesh(geometry.size)
        if isinstance(geometry, CylinderGeometry):
            return make_cylinder_mesh(geometry.radius, geometry.length)
        if isinstance(geometry, SphereGeometry):
            return make_sphere_mesh(geometry.radius)
        if isinstance(geometry, MeshGeometry):
            resolved = self._mesh_resolver(geometry.filename)
            if resolved is None:
                return None
            try:
                mesh = load_mesh_file(resolved)
            except (UnsupportedMeshFormat, OSError):
                return None
            if geometry.scale != (1.0, 1.0, 1.0):
                mesh = mesh.scaled(geometry.scale)
            return mesh
        return None

    # --- Qt/OpenGL lifecycle -------------------------------------------------

    def initializeGL(self) -> None:
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        self._program = self._compile_program(VERTEX_SHADER, FRAGMENT_SHADER)
        self._gl_ready = True
        if self._pending_robot is not None or self._robot is not None:
            self._rebuild_buffers_now(self._pending_robot or self._robot)
            self._pending_robot = None

    def resizeGL(self, w: int, h: int) -> None:
        gl.glViewport(0, 0, max(1, w), max(1, h))

    def paintGL(self) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self._program is None or self._robot is None:
            return

        gl.glUseProgram(self._program)

        eye = self._camera_eye()
        up = np.array([0.0, 0.0, 1.0], dtype=np.float32)  # Z-up, see this module's own header
        view = look_at(eye, self._target, up)
        aspect = max(self.width(), 1) / max(self.height(), 1)
        proj = perspective(45.0, aspect, 0.01, 50.0)

        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self._program, "uView"), 1, gl.GL_TRUE, view)
        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self._program, "uProjection"), 1, gl.GL_TRUE, proj)
        gl.glUniform3f(gl.glGetUniformLocation(self._program, "uCameraPos"), *eye)

        world_transforms = compute_link_world_transforms(self._robot, self._joint_values)
        for link in self._robot.links.values():
            link_world = world_transforms.get(link.name)
            if link_world is None:
                continue  # disconnected link (dof.py already flags this as infeasible) - nothing to pose it against
            highlight = (0.06, 0.06, 0.0) if link.name == self._selected_link else (0.0, 0.0, 0.0)
            for i, visual in enumerate(link.visuals):
                buf = self._buffers.get((link.name, i))
                if buf is None:
                    continue
                model = link_world @ origin_to_matrix(visual.origin)
                color = self._colors.get((link.name, i), (*DEFAULT_COLOR, 1.0))
                self._draw_model(model, buf, color, highlight)

    def _draw_model(self, model: np.ndarray, buf: GLMeshBuffer, color: tuple[float, float, float, float], highlight: tuple[float, float, float]) -> None:
        model32 = model.astype(np.float32)
        normal_matrix = np.linalg.inv(model32[:3, :3]).T.astype(np.float32)
        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self._program, "uModel"), 1, gl.GL_TRUE, model32)
        gl.glUniformMatrix3fv(gl.glGetUniformLocation(self._program, "uNormalMatrix"), 1, gl.GL_TRUE, normal_matrix)
        gl.glUniform3f(gl.glGetUniformLocation(self._program, "uBaseColor"), color[0], color[1], color[2])
        gl.glUniform1f(gl.glGetUniformLocation(self._program, "uAlpha"), color[3])
        gl.glUniform3f(gl.glGetUniformLocation(self._program, "uSelectHighlight"), *highlight)
        buf.draw()

    # --- camera (Z-up pan/orbit, see this module's own header) ----------------

    def _camera_eye(self) -> np.ndarray:
        yaw = np.radians(self._yaw)
        pitch = np.radians(self._pitch)
        x = self._distance * np.cos(pitch) * np.cos(yaw)
        y = self._distance * np.cos(pitch) * np.sin(yaw)
        z = self._distance * np.sin(pitch)
        return self._target + np.array([x, y, z], dtype=np.float32)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = event.position()
        self._drag_button = event.button()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = None
        self._drag_button = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_mouse_pos is None:
            return
        delta = event.position() - self._last_mouse_pos
        self._last_mouse_pos = event.position()
        if self._drag_button == Qt.MouseButton.LeftButton:
            self._yaw -= delta.x() * 0.4
            self._pitch = float(np.clip(self._pitch + delta.y() * 0.4, -85.0, 85.0))
            self.update()
        elif self._drag_button in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            yaw = np.radians(self._yaw)
            right = np.array([-np.sin(yaw), np.cos(yaw), 0.0], dtype=np.float32)
            up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            pan_scale = self._distance * 0.0015
            self._target -= right * delta.x() * pan_scale
            self._target += up * delta.y() * pan_scale
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 0.9 if event.angleDelta().y() > 0 else 1.1
        self._distance = float(np.clip(self._distance * factor, 0.05, 15.0))
        self.update()

    # --- shader compilation -----------------------------------------------

    @staticmethod
    def _compile_shader(source: str, shader_type: int) -> int:
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
            log = gl.glGetShaderInfoLog(shader).decode()
            raise RuntimeError(f"Shader compile error:\n{log}")
        return shader

    @classmethod
    def _compile_program(cls, vertex_src: str, fragment_src: str) -> int:
        vs = cls._compile_shader(vertex_src, gl.GL_VERTEX_SHADER)
        fs = cls._compile_shader(fragment_src, gl.GL_FRAGMENT_SHADER)
        program = gl.glCreateProgram()
        gl.glAttachShader(program, vs)
        gl.glAttachShader(program, fs)
        gl.glLinkProgram(program)
        if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
            log = gl.glGetProgramInfoLog(program).decode()
            raise RuntimeError(f"Shader link error:\n{log}")
        gl.glDeleteShader(vs)
        gl.glDeleteShader(fs)
        return program
