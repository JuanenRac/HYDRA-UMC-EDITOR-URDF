# Contributing to HYDRA-UMC-EDITOR-URDF 🦾

## Technology Stack
- **Language**: Python.
- **XML**: `xml.etree.ElementTree`.
- **UI**: PySide6.

## Guidelines
1. **URDF Spec**: Follow the ROS URDF XML schema strictly.
2. **Mesh Resolution**: Ensure the millimeter-to-meter heuristic is applied to any new loader.
3. **Testing**: Verify DOF validation with complex multi-link chains.
