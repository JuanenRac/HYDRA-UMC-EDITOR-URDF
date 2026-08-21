"""Repro script (scratch, not part of the app) - confirms whether
render/kinematics.py's compute_link_world_transforms() hangs on a
genuine directed cycle in the joint graph that IS reachable from the
root link (as opposed to the already-fixed multi-parent "diamond"
reconvergence case, which does not form a real cycle).

Construction: root A -> B (j1), B -> C (j2), C -> B (j3, closes the
cycle back onto B - B is now the <child> of both j1 and j2... wait,
actually child of j1 and j3). This makes B a multi-parent link (dof.py
already flags this as infeasible), but nothing in the render pipeline
(viewport.py's paintGL) checks is_feasible before calling
compute_link_world_transforms - so the infinite loop, if it exists,
would still hang a real editing session that loads this URDF.

Run with a hard wall-clock timeout so a real infinite loop reports
itself instead of hanging the test forever.
"""
import signal
import sys

sys.path.insert(0, r"C:\Users\juane\Documents\GitHub\HYDRA-UMC-EDITOR-URDF")

from hydra_editor_urdf.models import Joint, JointType, Link, Robot
from hydra_editor_urdf.render.kinematics import compute_link_world_transforms
from hydra_editor_urdf.urdf.dof import validate

robot = Robot(name="cyclic_test")
robot.links = {name: Link(name=name) for name in ("A", "B", "C")}
robot.joints = {
    "j1": Joint(name="j1", type=JointType.FIXED, parent="A", child="B"),
    "j2": Joint(name="j2", type=JointType.FIXED, parent="B", child="C"),
    "j3": Joint(name="j3", type=JointType.FIXED, parent="C", child="B"),  # closes a real cycle B->C->B
}

report = validate(robot)
print("DofReport.is_feasible:", report.is_feasible)
print("DofReport.multi_parent_link_names:", report.multi_parent_link_names)
print("DofReport.reasons:", report.reasons)
print("root_link_name():", robot.root_link_name())


def _on_timeout(signum, frame):
    print("TIMEOUT: compute_link_world_transforms did not return within 3s - CONFIRMED infinite loop.")
    sys.exit(1)


# Windows has no SIGALRM - use a watchdog thread instead so this repro
# works on the actual dev machine (Windows), not just POSIX.
import threading

def _watchdog():
    import time
    time.sleep(3)
    print("TIMEOUT: compute_link_world_transforms did not return within 3s - CONFIRMED infinite loop.")
    import os
    os._exit(1)

t = threading.Thread(target=_watchdog, daemon=True)
t.start()

print("Calling compute_link_world_transforms()...")
result = compute_link_world_transforms(robot, {})
print("Returned normally. world dict keys:", list(result.keys()))
