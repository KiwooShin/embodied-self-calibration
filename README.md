# Embodied self-calibration

Can an AI teaching agent tell when a robot needs a motor experiment, practice, or a demonstration from a robot with a different body? The experiment scores the skill *after* both teachers disconnect.

**[Watch the milestone films and read the results](progress.md)** · [Research plan and related work](RESEARCH_PLAN.md) · [Reproduce the pilot](experiments/drawer/README.md)

The first experiment pairs two physical causes for a failed drawer pull. A student Cartesian rig has a horizontal motor and a lift motor. Its teacher has two serial horizontal motors with unequal strokes plus a lift motor. The transferable demonstration is a measured handle trajectory. Qwen receives text telemetry, the student updates a two-parameter skill, and an independent evaluator measures drawer travel.
