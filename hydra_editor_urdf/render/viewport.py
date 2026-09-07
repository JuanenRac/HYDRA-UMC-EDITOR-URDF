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
#
# UrdfGLRenderer below owns every real GL call and every piece of pose/
# camera state - genuinely context-agnostic (it never touches
# QOpenGLWidget itself), driven entirely through the `make_current`/
# `done_current` callables its own constructor takes, exactly the same
# real split HYDRA-UMC-SUITE's own RobotGLRenderer/RobotViewport/
# OffscreenRobotRenderer already use (see that file's own header) - this
# is that SAME pattern, reused rather than reinvented, so this app's own
# Qt Quick command deck (qt_editor_urdf.py) can feed its 3D preview
# through a QQuickImageProvider-fed OffscreenUrdfRenderer exactly the way
# SUITE's own Viewport panel does, without a second, drifting rendering
# implementation. UrdfViewport (the classic QOpenGLWidget
# viewport_panel.py already embeds) is now a thin wrapper delegating
# initializeGL/resizeGL/paintGL/every public setter to one
# UrdfGLRenderer instance, with IDENTICAL real behavior to the
# pre-refactor version (mesh_warning included - see on_mesh_warning
# below for how that Signal survives the split).
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
from OpenGL import GL as gl
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QOffscreenSurface, QOpenGLContext, QSurfaceFormat, QWheelEvent
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from hydra_editor_urdf.models import BoxGeometry, CylinderGeometry, Material, MeshGeometry, Robot, SphereGeometry, Visual
from hydra_editor_urdf.render.kinematics import compute_link_world_transforms, default_joint_values, origin_to_matrix
from hydra_editor_urdf.render.mesh import MalformedMeshFile, Mesh, UnsupportedMeshFormat, load_mesh_file, make_box_mesh, make_cylinder_mesh, make_sphere_mesh

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

    def delete(self) -> None:
        """Frees the actual GPU-side VAO/VBO. Must be called (with the
        right GL context current) before the last Python reference to
        this object goes away - garbage-collecting a GLMeshBuffer does
        NOT free its GPU resources on its own (no __del__ here on
        purpose: by the time the GC runs, the GL context that owns these
        handles may no longer be current on this thread, which is a
        recipe for a wrong-context glDelete* call or a silent no-op, not
        a reliable free - see _rebuild_buffers_now's own explicit call
        to this, inside its own make_current()/done_current() block)."""
        gl.glDeleteVertexArrays(1, [self.vao])
        gl.glDeleteBuffers(1, [self.vbo])


DEFAULT_COLOR = (0.72, 0.75, 0.80)


class UrdfGLRenderer:
    """Every real GL call and every piece of pose/camera/geometry state
    for the 3D viewport - genuinely context-agnostic. `make_current`/
    `done_current` are real callables the OWNER (a QOpenGLWidget, or an
    offscreen FBO wrapper) provides, exactly the same real reason
    HYDRA-UMC-SUITE's own RobotGLRenderer takes them (see that file's
    own header) - mesh uploads that happen outside initialize_gl()
    (importing a new URDF, editing a link's scale) bind the right
    context regardless of which real owner this renderer belongs to.

    `on_mesh_warning`, if given, is called with one human-readable string
    whenever rebuild_buffers() skips one or more visuals it couldn't
    resolve/load - the same real "silent ghost model" bug UrdfViewport's
    own pre-refactor mesh_warning Signal already fixed (see that Signal's
    own former docstring, now split across this callback and each real
    owner's own Signal/attribute). A plain callable, not a Qt Signal
    itself, because this class must stay usable by a non-QObject owner
    (OffscreenUrdfRenderer, below) too."""

    def __init__(
        self,
        make_current: Callable[[], None],
        done_current: Callable[[], None],
        mesh_resolver: Callable[[str], "Path | None"],
        on_mesh_warning: Callable[[str], None] | None = None,
    ):
        self._make_current = make_current
        self._done_current = done_current
        self._mesh_resolver = mesh_resolver
        self._on_mesh_warning = on_mesh_warning

        self._program: int | None = None
        self._gl_ready = False
        self._uniforms: dict[str, int] = {}

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
        self._pending_robot: Robot | None = None  # set by rebuild_buffers() before GL is ready; consumed in initialize_gl

        self._yaw = -35.0
        self._pitch = 20.0
        self._distance = 1.5
        self._target = np.array([0.0, 0.0, 0.2], dtype=np.float32)

        self._width = 320
        self._height = 240

    # --- public setters (owner decides whether/how to schedule a
    # repaint after calling one of these) ----------------------------------

    def set_selected_link(self, link_name: str | None) -> None:
        self._selected_link = link_name

    def set_joint_values(self, values: dict[str, float]) -> None:
        self._joint_values = dict(values)

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
        renderer reads at draw time."""
        if self._robot is None:
            return
        self._colors = self._collect_colors(self._robot)

    @staticmethod
    def _collect_colors(robot: Robot) -> dict[tuple[str, int], tuple[float, float, float, float]]:
        colors: dict[tuple[str, int], tuple[float, float, float, float]] = {}
        for link in robot.links.values():
            for i, visual in enumerate(link.visuals):
                colors[(link.name, i)] = visual.material.rgba if visual.material is not None else (*DEFAULT_COLOR, 1.0)
        return colors

    def _rebuild_buffers_now(self, robot: Robot | None) -> None:
        self._make_current()
        try:
            # See GLMeshBuffer.delete()'s own docstring - freeing the
            # previous set's real GPU handles here, not just dropping
            # their Python references, is what keeps a long editing
            # session (recolor/rescale/retype, each triggering a full
            # rebuild) from leaking VAO/VBO GPU memory.
            for buf in self._buffers.values():
                buf.delete()
            self._buffers = {}
            missing: list[str] = []
            if robot is not None:
                self._colors = self._collect_colors(robot)
                for link in robot.links.values():
                    for i, visual in enumerate(link.visuals):
                        mesh = self._build_visual_mesh(visual, link.name, missing)
                        if mesh is not None:
                            self._buffers[(link.name, i)] = GLMeshBuffer(mesh)
        finally:
            self._done_current()
        if missing and self._on_mesh_warning is not None:
            count_label = f"{len(missing)} mesh(es)" if len(missing) > 1 else "1 mesh"
            self._on_mesh_warning(f"{count_label} could not be loaded and won't be shown: {', '.join(missing[:3])}" + (", ..." if len(missing) > 3 else ""))

    def _build_visual_mesh(self, visual: Visual, link_name: str = "", missing: list[str] | None = None) -> Mesh | None:
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
                if missing is not None:
                    missing.append(f"{link_name}: {geometry.filename}" if link_name else geometry.filename)
                return None
            try:
                mesh = load_mesh_file(resolved)
            except (UnsupportedMeshFormat, MalformedMeshFile, OSError):
                if missing is not None:
                    missing.append(f"{link_name}: {geometry.filename}" if link_name else geometry.filename)
                return None
            if geometry.scale != (1.0, 1.0, 1.0):
                mesh = mesh.scaled(geometry.scale)
            return mesh
        return None

    def orbit(self, dx: float, dy: float) -> None:
        self._yaw -= dx * 0.4
        self._pitch = float(np.clip(self._pitch + dy * 0.4, -85.0, 85.0))

    def pan(self, dx: float, dy: float) -> None:
        yaw = np.radians(self._yaw)
        right = np.array([-np.sin(yaw), np.cos(yaw), 0.0], dtype=np.float32)
        up = np.array([0.0, 0.0, 1.0], dtype=np.float32)  # Z-up, see this module's own header
        pan_scale = self._distance * 0.0015
        self._target -= right * dx * pan_scale
        self._target += up * dy * pan_scale

    def zoom(self, factor: float) -> None:
        self._distance = float(np.clip(self._distance * factor, 0.05, 15.0))

    # --- GL lifecycle (called by the owner's own initializeGL/resizeGL/
    # paintGL, or by the offscreen owner's own equivalent explicit calls -
    # a real GL context is already current by the time any of these run,
    # guaranteed by the owner) -------------------------------------------

    def initialize_gl(self) -> None:
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        self._program = self._compile_program(VERTEX_SHADER, FRAGMENT_SHADER)
        self._uniforms = {
            name: gl.glGetUniformLocation(self._program, name)
            for name in ("uModel", "uView", "uProjection", "uNormalMatrix", "uBaseColor", "uAlpha", "uCameraPos", "uSelectHighlight")
        }
        self._gl_ready = True
        if self._pending_robot is not None or self._robot is not None:
            self._rebuild_buffers_now(self._pending_robot or self._robot)
            self._pending_robot = None

    def resize_gl(self, w: int, h: int) -> None:
        self._width, self._height = max(1, w), max(1, h)
        gl.glViewport(0, 0, self._width, self._height)

    def paint_gl(self) -> None:
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self._program is None or self._robot is None:
            return

        gl.glUseProgram(self._program)

        eye = self._camera_eye()
        up = np.array([0.0, 0.0, 1.0], dtype=np.float32)  # Z-up, see this module's own header
        view = look_at(eye, self._target, up)
        aspect = max(self._width, 1) / max(self._height, 1)
        proj = perspective(45.0, aspect, 0.01, 50.0)

        gl.glUniformMatrix4fv(self._uniforms["uView"], 1, gl.GL_TRUE, view)
        gl.glUniformMatrix4fv(self._uniforms["uProjection"], 1, gl.GL_TRUE, proj)
        gl.glUniform3f(self._uniforms["uCameraPos"], *eye)

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
        gl.glUniformMatrix4fv(self._uniforms["uModel"], 1, gl.GL_TRUE, model32)
        gl.glUniformMatrix3fv(self._uniforms["uNormalMatrix"], 1, gl.GL_TRUE, normal_matrix)
        gl.glUniform3f(self._uniforms["uBaseColor"], color[0], color[1], color[2])
        gl.glUniform1f(self._uniforms["uAlpha"], color[3])
        gl.glUniform3f(self._uniforms["uSelectHighlight"], *highlight)
        buf.draw()

    # --- camera (Z-up pan/orbit, see this module's own header) ----------------

    def _camera_eye(self) -> np.ndarray:
        yaw = np.radians(self._yaw)
        pitch = np.radians(self._pitch)
        x = self._distance * np.cos(pitch) * np.cos(yaw)
        y = self._distance * np.cos(pitch) * np.sin(yaw)
        z = self._distance * np.sin(pitch)
        return self._target + np.array([x, y, z], dtype=np.float32)

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


class UrdfViewport(QOpenGLWidget):
    """Orbit camera (left-drag rotate, wheel zoom, right/middle-drag pan)
    over whatever models.Robot is currently loaded - a thin QOpenGLWidget
    wrapper around one real UrdfGLRenderer, with IDENTICAL real behavior
    to the pre-refactor version (see this module's own header for why the
    GL logic itself now lives in UrdfGLRenderer instead of here)."""

    # This widget's own way of telling ui/panels/viewport_panel.py "I
    # silently skipped drawing one or more visuals" (see
    # UrdfGLRenderer._build_visual_mesh()'s own "BUG (found in audit)"
    # comment), so that panel can surface it to the operator via
    # EditorController.status_message - the same status-bar path
    # load_failed/robot_loaded already use - instead of the operator only
    # ever finding out by noticing a part of the robot is missing in the
    # viewport with zero indication of why.
    mesh_warning = Signal(str)

    def __init__(self, mesh_resolver: Callable[[str], "Path | None"], parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self._renderer = UrdfGLRenderer(self.makeCurrent, self.doneCurrent, mesh_resolver, on_mesh_warning=self.mesh_warning.emit)
        self._last_mouse_pos: QPointF | None = None
        self._drag_button: Qt.MouseButton | None = None

    # --- public API used by app.py / ui/panels ---------------------------------

    def set_selected_link(self, link_name: str | None) -> None:
        self._renderer.set_selected_link(link_name)
        self.update()

    def set_joint_values(self, values: dict[str, float]) -> None:
        self._renderer.set_joint_values(values)
        self.update()

    def rebuild_buffers(self, robot: Robot | None) -> None:
        self._renderer.rebuild_buffers(robot)
        self.update()

    def refresh_colors(self) -> None:
        self._renderer.refresh_colors()
        self.update()

    # --- Qt/OpenGL lifecycle -------------------------------------------------

    def initializeGL(self) -> None:
        self._renderer.initialize_gl()

    def resizeGL(self, w: int, h: int) -> None:
        self._renderer.resize_gl(w, h)

    def paintGL(self) -> None:
        self._renderer.paint_gl()

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
            self._renderer.orbit(delta.x(), delta.y())
            self.update()
        elif self._drag_button in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._renderer.pan(delta.x(), delta.y())
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 0.9 if event.angleDelta().y() > 0 else 1.1
        self._renderer.zoom(factor)
        self.update()


class OffscreenUrdfRenderer:
    """The Qt Quick shell's own real render path for the 3D Viewport
    panel (qt_editor_urdf.py) - a genuinely separate QOpenGLContext/
    QOffscreenSurface/QOpenGLFramebufferObject, entirely independent of
    Qt Quick's own scenegraph (which defaults to Direct3D11 on Windows,
    not OpenGL). Reuses UrdfGLRenderer's exact real rendering code rather
    than a second, drifting copy - see this module's own header, and
    HYDRA-UMC-SUITE's own OffscreenRobotRenderer (the proven original of
    this exact pattern, including the real reentrancy bug fixed below)
    for the full reasoning. Deliberately NOT Qt Quick's own
    QQuickFramebufferObject: that API requires the whole app's Quick
    backend forced onto OpenGL just to support this one panel, and needs
    real same-API GPU resource sharing with Quick's own render thread.
    Every render() call happens synchronously on the calling (GUI)
    thread, right after a real state mutation, with no window ever
    created for this context - the result is a plain QImage the caller
    hands to QML through a QQuickImageProvider, the same real pattern
    SUITE's own ViewportFrameProvider already uses.

    mesh_warning is exposed as a plain attribute (`last_mesh_warning`),
    not a Qt Signal - this class is deliberately NOT a QObject (a real
    GL resource owner has no business also being a signal source; the
    Qt Quick bridge that owns this instance already has its own Signal
    for that, and reads this attribute after every rebuild_buffers()
    call to decide whether to fire it)."""

    def __init__(self, mesh_resolver: Callable[[str], "Path | None"]) -> None:
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)

        self._surface = QOffscreenSurface()
        self._surface.setFormat(fmt)
        self._surface.create()
        if not self._surface.isValid():
            raise RuntimeError("Failed to create an offscreen surface for the 3D Viewport panel")

        self._context = QOpenGLContext()
        self._context.setFormat(fmt)
        if not self._context.create():
            raise RuntimeError("Failed to create an offscreen OpenGL context for the 3D Viewport panel")

        self._fbo: QOpenGLFramebufferObject | None = None
        self._width = 640
        self._height = 480
        # Same real reentrancy counter SUITE's own OffscreenRobotRenderer
        # needed for the same real reason (see that class's own comment,
        # bisected there against a minimal repro script): a nested
        # doneCurrent()/makeCurrent() cycle (triggered here by a lazy
        # mesh load during initialize_gl(), same trigger as SUITE's own
        # bug) segfaults the very next QOpenGLFramebufferObject
        # construction against a standalone QOpenGLContext/
        # QOffscreenSurface pair unless only the OUTERMOST
        # make_current()/done_current() call pair ever touches the real
        # context.
        self._current_depth = 0
        self.last_mesh_warning: str | None = None

        self._renderer = UrdfGLRenderer(self._make_current, self._done_current, mesh_resolver, on_mesh_warning=self._on_mesh_warning)
        self._make_current()
        try:
            self._renderer.initialize_gl()
            self._ensure_fbo()
        finally:
            self._done_current()

    def _on_mesh_warning(self, message: str) -> None:
        self.last_mesh_warning = message

    def _make_current(self) -> None:
        if self._current_depth == 0:
            self._context.makeCurrent(self._surface)
        self._current_depth += 1

    def _done_current(self) -> None:
        self._current_depth -= 1
        if self._current_depth == 0:
            self._context.doneCurrent()

    def _ensure_fbo(self) -> None:
        if self._fbo is not None and self._fbo.size().width() == self._width and self._fbo.size().height() == self._height:
            return
        fbo_format = QOpenGLFramebufferObjectFormat()
        fbo_format.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        self._fbo = QOpenGLFramebufferObject(self._width, self._height, fbo_format)
        self._renderer.resize_gl(self._width, self._height)

    def resize(self, width: int, height: int) -> None:
        width, height = max(1, int(width)), max(1, int(height))
        if width == self._width and height == self._height:
            return
        self._width, self._height = width, height
        self._make_current()
        try:
            self._ensure_fbo()
        finally:
            self._done_current()

    def render(self) -> QImage:
        """Real, synchronous render - bind the FBO, run the exact same
        paint_gl() the widget path uses, read the real pixels back."""
        self._make_current()
        try:
            self._ensure_fbo()
            self._fbo.bind()
            self._renderer.paint_gl()
            self._fbo.release()
            return self._fbo.toImage()
        finally:
            self._done_current()

    # -- forwarded setters (mirrors UrdfViewport's own real public API -
    # the caller (qt_editor_urdf.py's own bridge) always calls render()
    # again right after one of these) --------------------------------

    def rebuild_buffers(self, robot: Robot | None) -> None:
        self.last_mesh_warning = None
        self._renderer.rebuild_buffers(robot)

    def refresh_colors(self) -> None:
        self._renderer.refresh_colors()

    def set_joint_values(self, values: dict[str, float]) -> None:
        self._renderer.set_joint_values(values)

    def set_selected_link(self, link_name: str | None) -> None:
        self._renderer.set_selected_link(link_name)

    def orbit(self, dx: float, dy: float) -> None:
        self._renderer.orbit(dx, dy)

    def pan(self, dx: float, dy: float) -> None:
        self._renderer.pan(dx, dy)

    def zoom(self, factor: float) -> None:
        self._renderer.zoom(factor)
