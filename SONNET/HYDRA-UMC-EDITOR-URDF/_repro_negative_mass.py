"""Repro (scratch, not part of the app) - confirms urdf/dof.py's own
validate() now flags a link with a negative <inertial><mass> as
infeasible, and that a normal non-negative-mass robot is unaffected
(no false positive introduced)."""
import sys

sys.path.insert(0, r"C:\Users\juane\Documents\GitHub\HYDRA-UMC-EDITOR-URDF")

from hydra_editor_urdf.models import Inertial, Joint, JointLimit, JointType, Link, Robot
from hydra_editor_urdf.urdf.dof import validate

# Control case: a valid 3-DOF chain, all masses non-negative (incl. one
# link with NO <inertial> at all, which is legal per spec).
good = Robot(name="good")
good.links = {
    "base": Link(name="base"),
    "mid": Link(name="mid", inertial=Inertial(mass=1.5)),
    "tip": Link(name="tip", inertial=None),
}
good.joints = {
    "j1": Joint(name="j1", type=JointType.REVOLUTE, parent="base", child="mid", limit=JointLimit(lower=-1, upper=1)),
    "j2": Joint(name="j2", type=JointType.REVOLUTE, parent="mid", child="tip", limit=JointLimit(lower=-1, upper=1)),
    "j3": Joint(name="j3", type=JointType.REVOLUTE, parent="tip", child="base2", limit=JointLimit(lower=-1, upper=1)),
}
good.links["base2"] = Link(name="base2")
good_report = validate(good)
print("GOOD case - is_feasible:", good_report.is_feasible, "reasons:", good_report.reasons)
assert not any("negative" in r for r in good_report.reasons), "FALSE POSITIVE: flagged a non-negative-mass robot"

# Bad case: same shape, but "mid" has a negative mass.
bad = Robot(name="bad")
bad.links = {
    "base": Link(name="base"),
    "mid": Link(name="mid", inertial=Inertial(mass=-2.0)),
    "tip": Link(name="tip"),
}
bad.joints = dict(good.joints)  # reuse the same valid joint shape (base->mid->tip->base2 minus base2 link, close enough for this check)
bad.joints = {
    "j1": Joint(name="j1", type=JointType.REVOLUTE, parent="base", child="mid", limit=JointLimit(lower=-1, upper=1)),
    "j2": Joint(name="j2", type=JointType.REVOLUTE, parent="mid", child="tip", limit=JointLimit(lower=-1, upper=1)),
}
bad_report = validate(bad)
print("BAD case  - is_feasible:", bad_report.is_feasible, "reasons:", bad_report.reasons)
assert any("negative" in r and "mid" in r for r in bad_report.reasons), "MISSED: did not flag the negative-mass link"

print("OK - negative mass is flagged, valid robots are unaffected.")
