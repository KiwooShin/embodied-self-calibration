# Cross-body walking pilot

A long, 4.50 kg quadruped executes a scripted diagonal gait. Each leg has roll, hip pitch and knee pitch. The 2.95 kg student has just hip and knee pitch, shorter and differently proportioned legs, its own stride period (0.46 s versus the teacher's 0.56 s) and its own foot-placement controller. Both trunks float under gravity in MuJoCo. Both controllers start with local inverse kinematics, an upright stance and anatomically labelled feet. Only the student motor permutation, signs and gait phase are initially unknown to its learner. These are procedural research mechanisms. No external robot assets or pretrained walking policies are required.

## Student, teacher and assessment

- Eight supported 0.13 rad pulses identify the student's channel-to-encoder map and sign. The pulse and settle periods take 3.2 simulated seconds in total. The learned adapter actually translates walking commands to the scrambled interface. Both conditions have the same wiring, actuator bounds, search order, initial practice and reset procedure per seed.
- The student searches four relative foot timings in quarter-cycle units. Front-left fixes the time origin. Twelve common schedules appear first in a seeded permutation, followed by the remaining schedules, for full coverage of 64 possibilities. Refinement tries the nearest untested pattern to the best observed one using circular phase distance. A teacher request spends one practice testing the inferred schedule on the student's own body.
- Contact transfer measures the longest circular swing interval per foot and estimates the following touchdown. The secondary adapter uses the frame of maximum measured foot height relative to the trunk. Both use the same observed 0.55 s source stride at 100 Hz. The student receives projected foot timing only. Preparing the reusable recording takes one 0.4 s settle and one 3.2 s teacher rollout. Each request is charged 0.55 s playback.
- Each free student practice settles for 0.4 s and moves for 3.2 s. The best observed training candidate becomes the retained policy. Ranking uses training success, upright execution, then forward travel minus 1.4 times lateral drift and the airborne fraction. Training stops at its first level-ground pass or after six practices. After training, each distinct retained checkpoint is replayed on three unseen starts. Repeated checkpoints reuse the identical evaluation.
- The main outcome is the first practice after which **all three unassisted tests** pass their motion, balance and contact criteria. A failure receives the six-practice cap for the capped-time metric even if training stopped early. Review success counts alongside capped time and actual interaction. Held-out executions never affect Qwen, the learner or the stopping rule. A reset is required for each practice or evaluation.

## Files and reproduction

The rig implements physics, calibration and trial scoring. The learner extracts the source lesson and builds the paired search queue. Only the agent module connects to Qwen. The study runs teaching and then evaluates frozen checkpoints. The metrics module audits saved trials.

Install the pinned Python simulation dependencies in an isolated environment. Serve the same official Qwen3-8B Q4_K_M weights and llama.cpp revision as the [drawer experiment](../drawer/README.md), with 12 CPU threads, disabled reasoning, a 4096-token context and a loopback endpoint. The scripts use port 18085 by default. Each study needs a fresh output filename. A request journal permits byte-identical inference reuse, including across matched/shuffled conditions before a demonstration. The log records full requests, replies, usage and latency. Summed call seconds charge reused replies their original duration; actual unique inference time is the sum over the journal.

```bash
python -m pip install -r experiments/locomotion/requirements.txt
mkdir -p runs
python -m experiments.locomotion.study runs/contact.json --journal runs/contact-requests.json
python -m experiments.locomotion.study --secondary runs/height.json --journal runs/height-requests.json
python -m experiments.locomotion.study --gated runs/gate.json --journal runs/gate-requests.json
python -m experiments.locomotion.metrics runs/contact.json runs/height.json runs/gate.json
python -m pytest -q experiments/locomotion/tests
```

The primary seeds are 410–421. Secondary foot-height and contact observations use seeds 510–521. The exploratory two-stage query policy uses seeds 610–621. Each comparison uses its own paired no-teacher control. The numerical label-swap control exchanges the hind-foot phase estimates while retaining the other observations and budget. The three cohorts share one student morphology and three deterministic held-out starts. The demonstration-query gate is calibrated on neither held-out successes nor hidden trial scores. An initial unscored commissioning request exceeded a 96-token reply limit; the frozen scored interface allows 192 tokens and caps the reason at 120 characters.

The simulations use the [MuJoCo Python bindings](https://mujoco.readthedocs.io/en/stable/python.html). The robot-to-robot timing abstraction has a related precedent in [learning locomotion skills by imitating animals](https://xbpeng.github.io/projects/Robotic_Imitation/).
