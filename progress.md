# Research progress

**November 14, 2026 · DGX Spark.** The first study has a live text-only Qwen supervisor, two physics implementations, a fixed-rule comparison, and teacher-disconnected tests. Start with film 1 to see the task, then film 3 to see where the learned supervisor gets stuck.

| Milestone | Film | Finding | Recorded trials |
| --- | --- | --- | --- |
| 1 · Physics and student learning | [Two failures that look alike](videos/01-physics.mp4) | Rule selected a diagnostic probe for reversed motion and a teacher segment for the latch. Both frozen skills passed all three starts, 6/6 total. | [PhysX rule](results/drawer-rule.json) |
| 2 · Live Qwen | [When the teacher stops too soon](videos/02-raw-qwen.mp4) | With raw measurements, Qwen stopped early and passed 0/6. It described backward motion as successful even though the drawer stayed closed. | [Raw Qwen](results/drawer-qwen.json) |
| 3 · Explicit task score | [Does a clearer observation help?](videos/03-evidence.mp4) | After adding signed direction and a goal-met field, Qwen passed 3/6. It acquired the correct polarity but also requested an unnecessary teacher segment. In the latch case, it kept practicing and exhausted the budget. | [Qwen with derived score](results/drawer-qwen-observed.json) |
| 4 · Combined and absent faults | [Two faults together, or none at all](videos/04-transfer.mp4) | Frozen Qwen and the rule each passed 6/6. Qwen used the same probe-then-demo sequence it used on the reversed-only trial. Success on both faults alone gives weak evidence that Qwen isolated the latch. | [Qwen](results/transfer-qwen-observed.json) · [Rule](results/transfer-rule.json) |
| 5 · Independent physics engine | [Does the failure survive a new engine?](videos/05-cross-engine.mp4) | ODE reimplemented the drives, constraints and collision response. On the original pair, Qwen again passed 3/6, with all failures on the latch. The rule passed 6/6. | [ODE Qwen](results/ode-qwen-observed.json) · [ODE rule](results/ode-rule.json) |
| 6 · Agent call timing | [One student, two ways to call Qwen](videos/06-call-schedule.mp4) | On the shifted fixtures, scheduling cut model calls from 13 to 7. Frozen-student success fell from 9/12 to 6/12. The scheduled agent used zero teacher demonstrations and missed the combined fault. | [Every decision, paired](results/shifted-qwen-observed-paired.json) · [combined/nominal](results/shifted-qwen-observed-transfer.json) · [scheduled, paired](results/shifted-qwen-scheduled-paired.json) · [combined/nominal](results/shifted-qwen-scheduled-transfer.json) |

**What the films show.** The teal tool, gold handle and red stop are positioned from the simulation traces. Each decision follows the observed motion. The final shot uses a fresh fixture, the largest held-out gap, and the frozen student without Qwen or teacher access. These RTX replays illustrate two- and three-axis mechanisms with common Cartesian axes. No physical robots have been tested. The PyODE replication runs ODE directly and does not use the Webots application.

**How to interpret the evidence.** The learner has two writable parameters and a predefined action menu. A fixed rule already solves these fixtures. The student has yet to demonstrate calibration of arbitrary joints or strategy transfer between articulated robot families. The next comparison measures whether an event-triggered call schedule can save agent calls while preserving success.


## Protocol for the next evaluation

After running the two single-fault fixtures, freeze the observation adapter, prompt, student update rules, budgets, teacher script, and threshold. Evaluate the two remaining cells of the horizontal-channel-polarity × latch-presence design: both faults together and neither fault. Score three frozen-student starts per cell. Run the telemetry rule and Qwen with the derived task score. Report all outcomes, including early stops and unsuccessful tests. The comparison measures compositional diagnostics within this fixture. The cases share the same two-axis student geometry.


## Registered follow-up on agent call timing

On the independent ODE fixture, hold the Qwen weights, decision prompt, derived measurements, student update rule and five-decision budget fixed. Compare calling Qwen at every decision with a scheduler that automatically practices after a probe or demonstration and automatically freezes after observed success. Qwen still chooses the diagnostic intervention after a failed practice. Use a new student response gain of 0.92 and a 6 mm training gap. Run all four fault combinations, including the nominal control, for both supervisors and the fixed rule. Record the number of model calls, teacher requests, physical practice seconds and independent successes. This tests the proposed division of work between a numerical controller and the language model. A reduction in calls is only desirable if independent performance is preserved.

## Next manipulation milestone

Test the original 10 cm instruction in a planar workspace on a two-joint arm and a three-joint arm. Hide link geometry and scramble command-channel order and signs. A bounded single-channel pulse estimates one column of a local action-to-endpoint map. Compare fixed calibration, no calibration, and Qwen choosing which channel to investigate or when to test. The teacher option returns an endpoint trace from the other morphology. Freeze the fitted matrix and score previously unused starts with a 10 mm tolerance. This experiment addresses discovery of movement directions beyond the two-parameter drawer skill.

### Cost of the call schedules

| Supervisor on four shifted ODE cases | Frozen successes | Qwen calls | Teacher requests | Student interaction | Teacher interaction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen at every decision | 9/12 | 13 | 2 | 7.2 sim s | 2.4 sim s |
| Qwen after failed practice | 6/12 | 7 | 0 | 7.8 sim s | 0.0 sim s |
| Fixed telemetry rule | 12/12 | 0 | 2 | 7.2 sim s | 2.4 sim s |

The scheduled variant can still assess prematurely after a failed practice. Its zero teacher cost came with an unsolved combined fault. The fixed rule remains the strongest method on these restricted fixtures. [Rule single-fault trials](results/shifted-rule-paired.json) · [Rule combined and nominal trials](results/shifted-rule-transfer.json)
