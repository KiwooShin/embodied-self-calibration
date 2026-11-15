# Reach 100 mm on an unfamiliar arm

Two- and three-link ODE hinge chains have hidden geometry, scrambled anonymous actuator channels, and unknown motor signs. A pulse starts from a fresh neutral rig. The student's two-dimensional local motor map is measured endpoint displacement divided by commanded motion. The damped least-squares controller uses the frozen matrix and live endpoint measurements. Each decision may select a pulse, a teacher endpoint demonstration, or assessment. Qwen can issue redundant requests. If it exhausts its budget, the evaluator freezes the student.

The score is endpoint error ≤10 mm from the new start plus the leftward 100 mm target. Tests use three new postures. Different lengths, mappings and dimensions are fixed in the evaluator. These experiments use sensor-accessible tool coordinates, ideal joints and actuator command units, so they leave visual estimation and hardware calibration open.

Run the following using Python with NumPy and PyODE. Use the same local Qwen server as the drawer experiment.

```bash
/usr/bin/python3 experiments/reach/run.py --mode untrained --out runs/reach-untrained.json
/usr/bin/python3 experiments/reach/run.py --mode all_channels --out runs/reach-fixed.json
/usr/bin/python3 experiments/reach/run.py --mode qwen --out runs/reach-qwen.json
python experiments/reach/film.py results/reach-qwen.json runs/reach.mp4 --encoder libopenh264
```

Physics uses a 960 Hz step, bounded torques, 0.6 simulated seconds per command, and a 20 Hz trace. Each held-out start resets the simulator and retains only the learned matrix. The optional teacher computes its own movement on the other morphology and returns its endpoint trajectory relative to its starting position. No teacher request occurred in the recorded Qwen run.

For the workspace sweep, run workspace.py with the saved Qwen calibration JSON and a fresh output filename using the ODE Python environment. Then run workspace_film.py with the sweep JSON, a new MP4 filename and the selected FFmpeg encoder. Each body contributes 13 posture shifts × 8 directions. Local refitting is a diagnostic baseline with access to repeatable resets.
