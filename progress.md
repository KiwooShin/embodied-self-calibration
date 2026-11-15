# Research progress

## Protocol for the next evaluation

After running the two single-fault fixtures, freeze the observation adapter, prompt, student update rules, budgets, teacher script, and threshold. Evaluate the two remaining cells of the horizontal-channel-polarity × latch-presence design: both faults together and neither fault. Score three frozen-student starts per cell. Run the telemetry rule and Qwen with the derived task score. Report all outcomes, including early stops and unsuccessful tests. The comparison measures compositional diagnostics within this fixture. The cases share the same two-axis student geometry.

The initial paired results, recordings, and independent evaluation will be linked here as they are verified.

## Registered follow-up on agent call timing

On the independent ODE fixture, hold the Qwen weights, decision prompt, derived measurements, student update rule and five-decision budget fixed. Compare calling Qwen at every decision with a scheduler that automatically practices after a probe or demonstration and automatically freezes after observed success. Qwen still chooses the diagnostic intervention after a failed practice. Use a new student response gain of 0.92 and a 6 mm training gap. Run all four fault combinations, including the nominal control, for both supervisors and the fixed rule. Record the number of model calls, teacher requests, physical practice seconds and independent successes. This tests the proposed division of work between a numerical controller and the language model. A reduction in calls is only desirable if independent performance is preserved.
