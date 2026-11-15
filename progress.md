# Research progress

**November 14, 2026 · DGX Spark.** [Watch the 81-second narrated briefing](videos/research-briefing.mp4) for the drawer and reaching results through milestone 8. Each film below follows a measured trial or evaluation grid.

[![Two simulated drawer trials, with measured tool travel and a 60 mm success threshold](videos/briefing-preview.jpg)](videos/research-briefing.mp4)

**Current status.** Ten milestone films are published. A numeric threshold learned on the two-link arm matched Qwen on 48 held-out three-link reaching tasks while spending 54 fewer probe pulses. Matching the teacher to the fixture now has a measured causal effect in simulation.

| Milestone | Film | Finding | Recorded trials |
| --- | --- | --- | --- |
| 1 · Physics and student learning | [Two failures that look alike](videos/01-physics.mp4) | Rule selected a diagnostic probe for reversed motion and a teacher segment for the latch. Both frozen skills passed all three starts, 6/6 total. | [PhysX rule](results/drawer-rule.json) |
| 2 · Live Qwen | [When the teacher stops too soon](videos/02-raw-qwen.mp4) | With raw measurements, Qwen stopped early and passed 0/6. It described backward motion as successful even though the drawer stayed closed. | [Raw Qwen](results/drawer-qwen.json) |
| 3 · Explicit task score | [Does a clearer observation help?](videos/03-evidence.mp4) | After adding signed direction and a goal-met field, Qwen passed 3/6. It acquired the correct polarity but also requested an unnecessary teacher segment. In the latch case, it kept practicing and exhausted the budget. | [Qwen with derived score](results/drawer-qwen-observed.json) |
| 4 · Combined and absent faults | [Two faults together, or none at all](videos/04-transfer.mp4) | Frozen Qwen and the rule each passed 6/6. Qwen used the same probe-then-demo sequence it used on the reversed-only trial. Success on both faults alone gives weak evidence that Qwen isolated the latch. | [Qwen](results/transfer-qwen-observed.json) · [Rule](results/transfer-rule.json) |
| 5 · Independent physics engine | [Does the failure survive a new engine?](videos/05-cross-engine.mp4) | ODE reimplemented the drives, constraints and collision response. On the original pair, Qwen again passed 3/6, with all failures on the latch. The rule passed 6/6. | [ODE Qwen](results/ode-qwen-observed.json) · [ODE rule](results/ode-rule.json) |
| 6 · Agent call timing | [One student, two ways to call Qwen](videos/06-call-schedule.mp4) | On the shifted fixtures, scheduling cut model calls from 13 to 7. Frozen-student success fell from 9/12 to 6/12. The scheduled agent used zero teacher demonstrations and missed the combined fault. | [Every decision, paired](results/shifted-qwen-observed-paired.json) · [combined/nominal](results/shifted-qwen-observed-transfer.json) · [scheduled, paired](results/shifted-qwen-scheduled-paired.json) · [combined/nominal](results/shifted-qwen-scheduled-transfer.json) |
| 7 · Learn “10 cm left” | [Two-link and three-link arms](videos/07-ten-centimetres.mp4) | Both frozen motor maps passed 6/6 posture tests. Qwen used nine probes across the two bodies. Probing each channel once used five and reached the same final errors (3.0–8.4 mm). With zero calibration, all six errors remained 100 mm. | [Qwen](results/reach-qwen.json) · [All channels](results/reach-all_channels.json) · [Untrained](results/reach-untrained.json) |
| 8 · Workspace stress test | [How far does one calibration transfer?](videos/08-workspace.mp4) | Across 208 posture/direction pairs, one frozen map passed 102. Refitting at each posture passed 166. The three-link arm improved from 41/104 to 85/104. | [All paired outcomes](results/workspace-sweep.json) |
| 9 · Decide when to recalibrate | [Is this motor map still useful?](videos/09-recalibrate.mp4) | Qwen chose to reprobe on every one of 48 trials. It passed 39, using 144 extra pulses and 48 resets. The two-link residual threshold passed 39 with 90 pulses and 30 resets. Keeping the original map passed 24. | [Decisions, evidence and both simulated outcomes](results/recalibration-switch.json) |
| 10 · Transfer the right teacher segment | [A rotary teacher and a sliding student](videos/10-cross-body-teacher.mp4) | Matching object-motion segments passed 9/9 starts. Cyclically shuffled segments passed 0/9, a fixed lift passed 3/9, and a plain pull passed 0/9. This intervention isolates demonstration content, with the query supplied by the evaluator. | [Teacher observations and 36 student trials](results/keyed-teacher.json) |

**What the films show.** The teal tool, gold handle and red stop are positioned from the simulation traces. Each decision follows the observed motion. The final shot uses a fresh fixture, the largest held-out gap, and the frozen student without Qwen or teacher access. These RTX replays illustrate two- and three-axis mechanisms with common Cartesian axes. No physical robots have been tested. The PyODE replication runs ODE directly and does not use the Webots application.

**How to interpret the evidence.** The learner has two writable parameters and a predefined action menu. A fixed rule already solves these fixtures. The student has yet to demonstrate calibration of arbitrary joints or strategy transfer between articulated robot families. The next comparison measures whether an event-triggered call schedule can save agent calls while preserving success.


## Combined-fault protocol

After running the two single-fault fixtures, freeze the observation adapter, prompt, student update rules, budgets, teacher script, and threshold. Evaluate the two remaining cells of the horizontal-channel-polarity × latch-presence design: both faults together and neither fault. Score three frozen-student starts per cell. Run the telemetry rule and Qwen with the derived task score. Report all outcomes, including early stops and unsuccessful tests. The comparison measures compositional diagnostics within this fixture. The cases share the same two-axis student geometry.


## Registered follow-up on agent call timing

On the independent ODE fixture, hold the Qwen weights, decision prompt, derived measurements, student update rule and five-decision budget fixed. Compare calling Qwen at every decision with a scheduler that automatically practices after a probe or demonstration and automatically freezes after observed success. Qwen still chooses the diagnostic intervention after a failed practice. Use a new student response gain of 0.92 and a 6 mm training gap. Run all four fault combinations, including the nominal control, for both supervisors and the fixed rule. Record the number of model calls, teacher requests, physical practice seconds and independent successes. This tests the proposed division of work between a numerical controller and the language model. A reduction in calls is only desirable if independent performance is preserved.

## Reaching protocol

Test the original 10 cm instruction in a planar workspace on a two-joint arm and a three-joint arm. Hide link geometry and scramble command-channel order and signs. A bounded single-channel pulse estimates one column of a local action-to-endpoint map. Compare fixed calibration, no calibration, and Qwen choosing which channel to investigate or when to test. The teacher option returns an endpoint trace from the other morphology. Freeze the fitted matrix and score previously unused starts with a 10 mm tolerance. This experiment addresses discovery of movement directions beyond the two-parameter drawer skill.

### Cost of the call schedules

| Supervisor on four shifted ODE cases | Frozen successes | Qwen calls | Teacher requests | Student interaction | Teacher interaction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen at every decision | 9/12 | 13 | 2 | 7.2 sim s | 2.4 sim s |
| Qwen after failed practice | 6/12 | 7 | 0 | 7.8 sim s | 0.0 sim s |
| Fixed telemetry rule | 12/12 | 0 | 2 | 7.2 sim s | 2.4 sim s |

The scheduled variant can still assess prematurely after a failed practice. Its zero teacher cost came with an unsolved combined fault. The fixed rule remains the strongest method on these restricted fixtures. [Rule single-fault trials](results/shifted-rule-paired.json) · [Rule combined and nominal trials](results/shifted-rule-transfer.json)


The reaching film shows measured hinge centres and tool paths. Each +0.07 rad pulse starts at the calibration posture. The student stores a two-dimensional endpoint response for that channel. Qwen repeated measurements already in memory until the decision budget expired. Some of its explanations quoted displacements before they had been measured. The student always fits the map using simulator observations. A torque-driven commissioning check caught an immobile velocity-drive setup before scored trials. [Reproduction notes](experiments/reach/README.md)

## Workspace stress test protocol

Freeze the one-posture controller and measure where it stops working. Sweep initial posture shifts from −90° through +90° in 15° steps and eight directions of a 100 mm target. Compare the frozen map with a diagnostic baseline that remeasures each channel at the current starting posture. Record endpoint error, success, geometric reach bounds and probe cost. This is a stress test of the chosen controller, separate from the six original teaching trials.

The two-link arm improved from 61/104 to 81/104. Of all 208 targets, 173 intersected the geometric reach annulus with the 10 mm tolerance. The other 35 are retained in the denominator and failed both controllers. The annulus is a necessary reach condition and ignores joint limits. Local refitting uses two or three additional pulses per start. The eight directions at a posture reuse that map.

## Recalibration decision protocol

Use the first commanded movement as a diagnostic. Compare four choices on a new three-link grid: always keep the map, always reset and reprobe, switch when prediction residual exceeds a threshold selected on the two-link arm, or ask Qwen. Select the threshold on two-link data by maximizing success minus 0.05 per extra probe. The held-out grid has six new posture shifts (−72°, −36°, −12°, +12°, +36°, +72°) and eight targets offset 22.5° from the previous directions. Each Qwen call receives only goal displacement, measured and predicted first-step motion, residual, remaining error, and reprobe cost. Report successes and probes separately. Reprobing requires a reset to the original start; count this reset explicitly.

The overview uses locally synthesized narration with the [Piper LJSpeech voice](https://huggingface.co/rhasspy/piper-voices/blob/1162a9173d0ce503555aed757976b7a9912eae4c/en/en_US/ljspeech/medium/MODEL_CARD). [Narration and edit script](experiments/media/briefing.py)


## Cross-body demonstration control

A single demonstration with a fixed lift might work as a generic script. Compare a matching teacher segment against a cyclically mismatched segment, a fixed-height lift, and no demonstration. Give a prismatic student and a rotary-lift teacher the same drawer goal. Change the catch's vertical passage across three fixtures, so that excessive lift can also fail. Freeze the student's measured handle subgoal, disconnect the teacher, and test at three new initial pin gaps. Keep the acquisition and scoring rules common to matched and mismatched demonstrations.


## Integrated test protocol

Test the frozen scored-report Qwen supervisor and fixed rule on new passage heights (16, 34, and 52 mm), plus an unrestricted drawer. Cross each with normal and reversed student polarity. In every case the teacher uses a rotary lift and the student uses two linear channels. Give each supervisor five decision slots and hide the gate assignment. A teacher request returns only the measured handle trajectory before the drawer first travels 5 mm. The student stores peak lift plus a fixed 3 mm clearance. Report all eight cases, and independent outcomes from three starts per case.

## Paired model-size comparison

Repeat the eight integrated teaching cases with Qwen3-32B Q4_K_M. Freeze the prompt, observation adapter, student, fixtures, teacher, action schema, decision budget, quantization family and seed. Keep llama.cpp revision, CPU thread count and disabled reasoning mode aligned with the 8B run. Compare episode-level choices, independent success, teacher requests, simulation time, model calls and measured decision latency. The same cases support a matched model comparison; they do not establish generalization to another task family.
