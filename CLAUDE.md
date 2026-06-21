# CORI-main

CORI-main is the control and visualization stack for CORI (Computer Operated Robot Interface): a dashboard, real-time hand tracking, inverse-kinematics solvers, a simulation harness, and small AI training helpers, all aimed at driving a physical robot from a local machine (or a Raspberry Pi client).

## Build / Test / Lint Commands

- Install: `python -m venv .venv && pip install -r requirements.txt` (numpy, opencv-python, mediapipe, websockets, pygame, torch, g4f, adafruit-circuitpython-servokit)
- Build: not applicable (interpreted Python)
- Test: no automated tests; verify via the run scripts below
- Lint: not configured
- Dev / run:
  - Orchestrator: `python RUN/orchestrator.py`
  - Simulation: `python sim/sim.py`
  - Hand tracking: `python hand_tracking/handtracking.py`
  - AI helpers: `python AI - ANTIGRAVITY/train_model.py` (note the spaced directory name)

## Code Style Rules

- Language/version: Python 3.10+
- Paradigm: top-level domain folders (`core`, `dashboard`, `hand_tracking`, `Robot_math`, `servers`, `sim`, `RUN`, `AI - ANTIGRAVITY`, `error_handling`); entry-point scripts per module
- Types: mostly untyped; some use of `numpy` arrays and dataclasses
- Formatting: PEP 8 (no formatter configured)
- Imports / module style: absolute imports of sibling top-level packages
- Dependencies: hardware-dependent (`opencv-python`, `mediapipe`, `adafruit-circuitpython-servokit`, `torch`); see `requirements.txt`

## Verification Criteria

Before claiming any task done, Claude MUST:
1. Run `python -c "import core.config"` (or the touched module) to confirm imports resolve.
2. Confirm `pip install -r requirements.txt` succeeds in a clean `.venv` (hardware-only deps may be skipped on a headless dev box).
3. Boot the orchestrator or sim entry point and confirm it opens without a traceback.
4. Report the exact commands run and their outcomes in the final message.
