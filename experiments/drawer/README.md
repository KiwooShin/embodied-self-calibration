# Reproducing the drawer study

## Run the physics and teaching loop

Run from the repository root. The reference PhysX run used an existing native ARM64 Isaac Sim 5.1 source build (47d886f2) on a DGX Spark. Set ISAAC_PYTHON to the installation's python.sh. An Isaac container needs the repository mounted inside it and access to the local model endpoint. The fixture is procedural and requires no asset download.

```bash
"$ISAAC_PYTHON" experiments/drawer/run.py --mode rule --out runs/isaac-rule.json
"$ISAAC_PYTHON" experiments/drawer/run.py --mode qwen --out runs/isaac-raw.json
"$ISAAC_PYTHON" experiments/drawer/run.py --mode qwen-observed --out runs/isaac-scored.json
"$ISAAC_PYTHON" experiments/drawer/run.py --mode qwen-observed --suite transfer --out runs/isaac-transfer.json
```

Serve the official Qwen3-8B Q4_K_M GGUF using a local llama.cpp server. The experiment used CPU inference with 12 threads while Isaac used the Spark GPU. No external inference service or key is required. The default endpoint is loopback port 18081. Override it with --endpoint if needed. A failed model request terminates the run.

```bash
llama-server -m /path/to/Qwen3-8B-Q4_K_M.gguf --alias qwen3-8b -t 12 -c 4096 \
  --parallel 1 --reasoning off --no-webui --port 18081 --host 127.0.0.1
```

The llama.cpp revision was e574a17b062be51b98e239ccd3d3743e3d902333. The model file has SHA-256 d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785. The request uses temperature zero, seed 13, a four-action JSON schema and a 160-token output limit. [GGUF files at the evaluated revision](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/7c41481f57cb95916b40956ab2f0b139b296d974) · [llama.cpp](https://github.com/ggml-org/llama.cpp/tree/e574a17b062be51b98e239ccd3d3743e3d902333)

For the independent ODE implementation, use Python with the Ubuntu python3-pyode package. The reference setup used ODE 0.16.2 and PyODE 1.2.0.dev15. These commands use the same supervisors and frozen-student evaluator.

```bash
/usr/bin/python3 experiments/drawer/run.py --backend ode --mode rule --out runs/ode-rule.json
/usr/bin/python3 experiments/drawer/run.py --backend ode --mode qwen-observed --out runs/ode-qwen.json
```

## What a trial measures

- Initial skill assumes positive polarity and zero lift. Practice begins from a standardized tool/handle arrangement. The independent fixtures vary the world origin and initial pin gap (3, 8 and 12 mm).
- Each motor command takes 0.6 simulated seconds, with a ramp and settling interval. Physics steps at 240 Hz. Traces sample at 20 Hz. Position targets and measured tool/handle/drawer displacement are expressed in millimetres.
- A bounded 12 mm probe updates one motor sign. A scripted three-axis teacher lifts, then pulls. Only the observed handle lift and drawer translation up to first crossing 5 mm are shown to the supervisor during a query. The student estimates peak handle lift from that segment and adds a fixed 6 mm clearance.
- Teacher access, fault identity, and simulator geometry belong to the executor. The supervisor sees its action menu and public measurements. Fault names label saved results and films for the viewer. Teacher and student share a calibrated frame and common task axes.
- Each decision consumes one of five slots. After assessment or budget exhaustion, a fresh scene loads the frozen polarity and lift. Scoring never calls Qwen. At least 60 mm of drawer travel constitutes success. The three deterministic test poses probe sensitivity to initial state. They are not independent model-training runs.
- qwen uses raw numeric observations. qwen-observed additionally receives the signed travel direction and last measured progress against the 60 mm task goal. qwen-scheduled automatically practices following an update and assesses after observed success. Its remaining decisions use the same prompt and scored report as qwen-observed.
- The shifted ODE evaluation uses --shifted with either --suite paired or --suite transfer. It changes horizontal gain to 0.92 and training gap to 6 mm. Latched cases can yield ODE contact-solver warnings near redundant contacts. Inspect full trajectories and reproduce the comparison on hardware before interpreting contact-force accuracy.

## Make a milestone film

Replay uses the measured terminal tool, handle, and drawer poses from the JSON. RTX images have decorative rails and housings. The teacher extension stroke in the illustration is apportioned from tool travel. It is not an independently measured teacher motor trajectory. Time is slowed, and each phase receives an equal screen duration. The score is computed from the original physics trace. Use an empty render cache when changing the scene design.

```bash
"$ISAAC_PYTHON" experiments/drawer/render.py results/drawer-qwen.json --cache .replay-cache/local
python experiments/drawer/replay.py results/drawer-qwen.json runs/raw.mp4 \
  --cache .replay-cache/local --title "When the teacher stops too soon"
```

The edit step requires Pillow, DejaVu Sans and FFmpeg with an H.264 encoder. The Spark run used --encoder libopenh264. Each film shows both cases, the following supervisory decision, and the largest-gap independent test. All three evaluation outcomes appear in the closing score.

## Keyed passage and different joint types

Run keyed.py with a new output JSON using PyODE. Render the sectional comparison with keyed_film.py, passing the JSON, the MP4 path and optionally --encoder libopenh264. The side-view projection shows the catch and passage in a plane beside the pin. The teacher can use its own fixture parameters to demonstrate the skill. A student receiving an example sees only measured object motion. Lift targets and source-fixture assignments are recorded so the shuffled-segment control can be checked.

For the integrated evaluation, run integrated.py with --mode rule or --mode qwen-observed and a new output JSON. For a larger checkpoint, set both --model and --endpoint to the identity and address of the corresponding server. Independent tests always use the same actor parameters saved at the end of teaching. The supervisor does not receive the fixture identifier.

## Matched model-size comparison

Use the official [Qwen3-32B Q4_K_M revision](https://huggingface.co/Qwen/Qwen3-32B-GGUF/tree/938a7432affaec9157f883a87164e2646ae17555). The evaluated file has SHA-256 efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689. Serve it with the 8B llama.cpp revision and flags shown above, changing the file, the alias to qwen3-32b, and the port to 18082. Quantization family, CPU threads, prompt, student, teacher and independent starts are matched. Report wall time per call alongside accuracy. A single host and run per case give descriptive latency measurements.

```bash
/usr/bin/python3 experiments/drawer/integrated.py --mode qwen-observed \
  --model qwen3-32b --endpoint http://127.0.0.1:18082/v1 runs/integrated-32b.json
python experiments/drawer/verify.py runs/integrated-32b.json
```

## Teacher observation error

The rotary teacher still completes its own task. Corrupt only its observed handle height for the student. Each per-frame standard-normal draw is shared across estimators, offsets and noise levels within a gate and seed. The score comes from a fresh ODE execution. The optional median uses the last three available frames. At zero frame noise, repeated seeds give identical observations and are counted once in the pilot.

```bash
/usr/bin/python3 experiments/drawer/observations.py --seeds 0 1 2 3 -- runs/observation-errors.json
python experiments/drawer/observation_film.py runs/observation-errors.json runs/observation-errors.mp4
```
