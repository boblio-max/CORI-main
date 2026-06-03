# CORI-main

Control for CORI — Computer Operated Robot Interface. This repository provides the control and visualization stack for CORI, including a dashboard, real-time hand tracking, inverse-kinematics, simulation tools, and small AI helpers.

## Overview
- Hand tracking and landmarking utilities.
- Robot inverse-kinematics solvers and simulation harnesses.
- Small servers/clients for connecting to external devices (e.g., Raspberry Pi).
- Scripts and notebooks for data collection and AI model training.

## Requirements
- Python 3.10+ (use a virtual environment)
- Common packages: `numpy`, `opencv-python`, `tensorflow` or `torch` depending on models used. See each module for details.

## Quick setup
1. Create and activate a virtualenv: 

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. Install needed packages (example):

```bash
pip install -r requirements.txt || pip install numpy opencv-python
```

(If there is no `requirements.txt`, inspect modules like `AI/` and `core/config.py` for dependencies.)

## Quick start
- Run the orchestrator that coordinates runs:

```bash
python RUN/orchestrator.py
```

- Run simulation:

```bash
python sim/sim.py
```

- Run hand-tracking demo:

```bash
python hand_tracking/handtracking.py
```

- Train or run model helpers in `AI/`:

```bash
python AI/train_model.py
python AI/run_with_AI.py
```

## Repo structure (top-level)
- AI/ - model training and inference helpers
- core/ - configuration and shared utilities
- dashboard/ - visualization and dashboard code
- error_handling/ - custom error helpers
- hand_tracking/ - main hand tracking scripts
- Robot_math/ - IK solver(s)
- RUN/ - orchestrator and runtime scripts
- servers/ - client/server utilities
- sim/ - simulation environment

## Notes
- Many scripts expect local hardware (camera, robot, or Pi clients). Run in a controlled environment.
- Add a `requirements.txt` with pinned package versions for reproducible setups.
