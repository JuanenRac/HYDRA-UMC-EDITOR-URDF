# Simulation bench

The editor can run without the models of a real robot. The simulated robots are serial arms of random length with random joint types, axes, origins, limits, masses and shapes, drawn from a fixed seed. The real parser, writer, degrees-of-freedom check, kinematics and physical check run on them. The pose of every link is compared with a product of matrices that the bench computes itself, and the robots are then damaged the way files are damaged.

## Run it

```
PYTHONPATH=. python -m pytest -q tests/test_simulation_bench.py
```

## What the scenarios check

| Scenario | What it shows |
|----------|---------------|
| forty generated robots | written to URDF and read back as the same robot, and writing what was read changes nothing |
| forty robots | the degrees of freedom are the movable joints, the root is found, and only three to six are feasible |
| thirty robots posed at random | the pose of every link equals the product of the joints that lead to it |
| twenty-five healthy robots | no physical warning, and the same findings every time |
| seventeen kinds of damage (a mass of zero or in grams, an inertia that is not a number, cannot exist or breaks the triangle rule, a missing or inverted limit, a speed or an effort that is not positive, an axis of zero or not a unit, a length in millimetres, an angle in degrees, a link nobody declared, a link without a joint, a second root, two parents, a loop) | the check names the rule of each |
| a structure that is not a tree | infeasible, and the pose still ends |
| twelve texts that are not a robot | refused with the parse error and nothing else |
| three hundred damaged copies of a robot | read or refused, never another kind of error, and whatever is read can be checked |
| the same seed twice, another seed | the same robots, and really different ones |

The workflow named "Simulation bench" runs the bench on every change, so the simulated path has its own visible job.

## What it cannot show

How the editor behaves with the models of real robots, with their meshes, their xacro and their mistakes, needs the models. The status of the repository therefore stays at "simulated" for the hardware row until a person has run the service on the bench.
