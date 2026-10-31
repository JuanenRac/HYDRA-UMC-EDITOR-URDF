# Physical check of a model

A URDF can be valid XML, pass the degree-of-freedom check and still describe a body that could not exist: a mass of zero, an inertia tensor that no solid has, a lower limit above the upper one, a length in millimetres where metres are expected. The physical check lists such things as **warnings**. It is read-only: it never changes the robot, never changes whether the robot is feasible and never changes what is saved. Every warning carries a suggested correction, and the correction is only text for the user to apply by hand.

## Switch and command line

| Where | How |
| --- | --- |
| Editor | `"physical_check": true` in `hydra_editor_urdf_config.json`. Off when the setting is missing or is not the boolean `true` (the behaviour without it is unchanged). With it on, the warnings appear in the DOF screen after the reasons, with the usual `Warning:` prefix, and are refreshed on every edit, and the "Physical validation" panel (below) exists. |
| Command line | `python main.py --cli physical-check FILE.urdf [--json] [--mesh-root DIR]`. It needs no window and does not import Qt. Exit code 0: nothing found. 1: warnings. 2: the file could not be read or parsed, or the arguments are wrong. `--json` prints a list of objects with `rule`, `element`, `value`, `limit`, `fix` and `message`. |

The command line is an explicit request, so it does not need the switch. It never writes the model.

## The "Physical validation" panel

With `physical_check` true the editor has a panel of its own for the warnings, in the classic window (a dock tabbed with the DOF screen, with its entry in the View menu and a button in the command deck) and in the Qt Quick deck (`main.py --qtquick`, a tab beside Source and DOF). The switch is read when the window is built, so changing it needs a restart; with it off (the default) none of this exists and the interface is the one of the version without the panel.

| Part | What it does |
| --- | --- |
| List | One row per warning: severity, rule (the text and the code in brackets), element, value, limit and suggestion. |
| Severity | Decided by the rule, not by the check: `error` (the model is not a valid tree or body: no root, a cycle, a mass of zero, a tensor no solid has, inverted limits, a zero axis, a name used twice), `warning` (probably wrong: a missing limit, a mesh not found, a link out of reach) and `hint` (a guess from the size of a number, or a stretched mesh). |
| Filters | By severity, by rule (only the rules that have rows) and by a text that must appear in the element name (case ignored). |
| Order | By severity (errors first), by rule (the order of the table below) or by element; ties keep the order of the check, so the same model always gives the same list. |
| Counter | `shown of total`, and the number of errors, warnings and hints of the whole list. |
| Check again | Reads the model and the settings again (for example a changed `physical_max_length_m`). The panel also refreshes by itself on every edit and every load. |
| Copy JSON / Export JSON | The rows shown now (after the filters and the order), as a JSON list with the keys `severity`, `rule`, `element`, `value`, `limit`, `message`, `suggestion` and `fix`. Two exports of the same model are the same text. |

The panel is read-only. There is deliberately **no "Apply suggestion" button**: a suggestion is a sentence with a number in it ("add 0.5 to ixx, iyy and izz", "if it is in millimetres, use 5 m"), several of them need a judgement the check cannot make (is it millimetres or really 5000 m?) and an undo for a change of the inertia of a link does not exist in this editor. Applying a suggestion by hand in the Properties panel stays the way.

## What is checked

Each warning is `[rule] what - element: value (limit: limit). Suggestion: fix`, in the language of the editor. The element is written `link:NAME`, `joint:NAME` or `link:NAME/visual[N]` (or `collision[N]`).

| Rule | Warns when | Suggested correction |
| --- | --- | --- |
| `tree_no_root` | there are joints and every linked link has a parent | remove the joint that closes the loop |
| `tree_multiple_roots` | more than one linked link has no parent | join the extra roots to the tree |
| `tree_cycle` | the joints form a cycle | remove one joint of the loop |
| `tree_orphan_link` | a link is in no joint (and there is more than one link) | join it or delete it |
| `tree_unreachable_link` | with one root, a link cannot be reached from it | join it to the chain of the root |
| `tree_multiple_parents` | a link is the child of more than one joint | keep one |
| `tree_unknown_link` | a joint names a link that does not exist | add the link or fix the name |
| `duplicate_name` | a link or joint name is used twice (the file is read from the XML, because the reader refuses it), or a visual or collision name repeats inside a link | rename |
| `mass_not_positive` | a link with an `<inertial>` has a mass that is not above 0 (or is not a number) | a mass above 0, 0.001 kg as an example |
| `inertia_not_finite` | a component of the tensor is NaN or infinite | finite numbers |
| `inertia_not_positive_definite` | the smallest principal moment (eigenvalue of the 3x3 tensor) is not above 0 | add the printed number to ixx, iyy and izz |
| `inertia_triangle` | for the principal moments `a <= b <= c`, `a + b < c` (Ixx + Iyy >= Izz and the permutations) | raise the smallest moment by the printed number |
| `limit_missing` | a revolute or prismatic joint has no `<limit>` | add one |
| `limit_inverted` | lower is above upper (or not finite) | swap them |
| `velocity_not_positive`, `effort_not_positive` | the velocity or effort of a limit is not above 0 | a value above 0 |
| `continuous_with_limits` | a continuous joint has a non-zero lower or upper | remove them |
| `axis_zero` | the axis of a revolute, prismatic, continuous or planar joint is zero or not finite | a direction |
| `axis_not_unit` | the axis is not of length 1 (tolerance 1e-6) | the normalised axis |
| `mesh_missing` | the mesh file is not found by the resolver of the editor (not checked without one) | fix the path |
| `mesh_scale_invalid` | a scale component is not above 0, not finite or outside `physical_mesh_scale_min` to `physical_mesh_scale_max` | a reasonable scale |
| `mesh_scale_anisotropic` | the three scale components differ | the same scale on the three axes |
| `units_length` | a joint origin, a prismatic limit or a shape is larger than `physical_max_length_m` | divide by 1000 (millimetres) |
| `units_angle` | a revolute limit or an origin angle is larger than `physical_max_angle_rad` | convert degrees to radians |
| `units_mass` | a mass is larger than `physical_max_mass_kg` | divide by 1000 (grams) |

The inertia tensor is stored as six numbers (ixx, ixy, ixz, iyy, iyz, izz), so it is symmetric by construction; what is checked is that they are finite. The principal moments do not depend on the rotation of the inertial frame.

A joint that follows another with `<mimic>` is checked like any other joint.

## Settings

All in `hydra_editor_urdf_config.json`; a value that is not a positive finite number is ignored and the default is used.

| Setting | Default | Meaning |
| --- | --- | --- |
| `physical_check` | off | the switch of the editor |
| `physical_max_length_m` | 100 | above this a length is taken for millimetres |
| `physical_max_angle_rad` | 4 pi | above this an angle is taken for degrees |
| `physical_max_mass_kg` | 10000 | above this a mass is taken for grams |
| `physical_mesh_scale_min`, `physical_mesh_scale_max` | 0.0001 and 1000 | the range of a reasonable mesh scale |

## Limits of the check

* It judges numbers, not shapes: a tensor that is coherent is not necessarily the tensor of the real part, and the units rules are guesses from the size of a value.
* The mesh files are looked for with the resolver of the editor (relative to the model, `package://` tails, the opened folder); a mesh the editor can find is not reported.
* The panel was tested offscreen (the classic window, the panel and the Qt Quick deck load and behave as described) and by its logic; it has not been looked at on a real display with a real robot, and the severity of a rule is a judgement of this editor.
* The Qt Quick tests need PyOpenGL (the bridge imports the 3D renderer) and a Qt platform plugin; where they are missing those tests are skipped.
* It has been tested with generated models and the simulated cases of the test suite, not against a catalogue of real robot descriptions.
