# Copy-Space Visualizer (optional)

This is an optional Streamlit UI for visualizing scheduler v0 schedules.

Install (recommended):
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install -e .
  python -m pip install -r tools/visualizer/requirements.txt

Run:
  python -m streamlit run tools/visualizer/app.py

Default input:
- uses scripts/scheduler/tests/demo_instance.json
- can generate baseline/greedy schedules or accept uploaded JSON
