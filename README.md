# Embodied self-calibration

When an unfamiliar robot fails, should it test its motors, practice, or ask a differently built robot to show the task? This project scores what the student can still do after both the teaching agent and source robot disconnect.

**[Read the six-page research paper](paper/embodied-self-calibration.pdf)** · **[Watch the narrated walkthrough](videos/15-paper-walkthrough.mp4)** · [Progress and all 16 milestone films](progress.md) · [Research plan and related work](RESEARCH_PLAN.md)

A sliding student opened three simulated drawers after observing a rotary teacher. With the right object-motion segment it passed 9/9 starts; shuffling the segments produced 0/9. When the agent had to decide whether to ask for a segment on eight new teaching episodes, Qwen3-8B passed five. Qwen3-32B and a fixed telemetry rule passed all eight. The larger model requested twelve demonstrations and the rule requested six. [Measured decisions and costs](progress.md#manuscript-and-model-review)

Two simulated arms also learned to move 10 cm left from bounded motor probes. A prediction-error threshold fitted on the two-link arm retained the same 39/48 successes as Qwen3-8B on a new three-link grid with 54 fewer pulses. Physical DROID recordings supply an offline teacher-data audit. Physical student experiments and locomotion are next research stages. [Reaching experiments](experiments/reach/README.md) · [DROID audit](experiments/droid/README.md) · [Locomotion protocol](RESEARCH_PLAN.md#next-locomotion-experiment)

The daily review checks the paper and trial records, then executes the next of 28 registered observation-error replications. [Review status and next seed](progress.md#recurring-research-review) · [Reproduce the drawer studies](experiments/drawer/README.md) · [Rebuild the paper](paper/README.md)
