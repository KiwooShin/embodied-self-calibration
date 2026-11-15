#set document(title: "When Should a Robot Probe Its Body or Ask Another Robot for Help?", author: "Embodied Self-Calibration Project")
#let ink = rgb("#183448")
#let teal = rgb("#116b64")
#let gray = rgb("#56656d")
#set page(paper: "us-letter", margin: (x: 0.85in, top: 0.76in, bottom: 0.76in),
  header: context if counter(page).get().first() > 1 {text(size: 8.2pt, fill: gray)[Embodied Self-Calibration Project #h(1fr) Teaching decisions on unfamiliar robots]},
  footer: context [#line(length: 100%, stroke: .4pt + rgb("#b9c4c7")) #v(2pt)
    #text(size: 8.2pt, fill: gray)[Research manuscript · November 2026 #h(1fr) #counter(page).display("1")]])
#set text(font: "Libertinus Serif", size: 11.3pt, fill: ink)
#set par(justify: true, leading: 0.70em, spacing: 0.72em)
#set heading(numbering: none)
#show heading.where(level: 1): it => block(above: 9pt, below: 8pt)[#text(size: 17pt, weight: "bold",fill: ink)[#it.body]]
#show heading.where(level: 2): it => block(above: 8pt, below: 4pt)[#text(size: 12.2pt, weight: "bold",fill: teal)[#it.body]]
#let cap(body) = block(above:3pt,below:5pt)[#set text(size:9.2pt, fill:gray)
#set par(leading:.44em,justify:false)
#body]
#let th(body) = text(weight:"bold")[#body]
#let repo = "https://github.com/KiwooShin/embodied-self-calibration"
#let models = json("model-results.json")

#text(size: 10pt, fill: teal, weight: "bold")[EMPIRICAL ROBOTICS · RESEARCH MANUSCRIPT]
#v(4pt)
#text(size: 24pt, weight: "bold")[When Should a Robot Probe Its Body or Ask Another Robot for Help?]
#v(5pt)
#text(size: 11pt)[Embodied Self-Calibration Project #h(1fr) November 2026]
#v(6pt)
#line(length:100%,stroke:.8pt+teal)

== Abstract
When a robot fails to open a drawer, observing another robot can reveal a missing movement. The same demonstration can be wasted if the student's motor channel is reversed. We study a teaching supervisor that chooses among probing the student, requesting a segment from a differently actuated teacher, practicing, and testing the frozen student. We evaluate open-weight Qwen supervisors against a fixed telemetry rule in controlled simulation. On a keyed drawer, a sliding student given a matching rotary-teacher segment passed nine of nine starts. Shuffling the segments reduced this to zero. When Qwen3-8B had to decide whether to request that segment on new fixtures, it solved five of eight teaching episodes, compared with eight for the rule. In a separate three-link reaching evaluation, Qwen3-8B chose recalibration on all 48 trials. A prediction-error threshold developed on a two-link arm attained the same 39 successes with 54 fewer motor pulses. These experiments isolate two capabilities: transferring an informative behavior across bodies, and recognizing when acquiring that behavior is worth the interaction cost.

= 1. Introduction
A request such as “move 10 cm left” supplies a goal in the observer's frame. The student must still discover which of its motors moves the endpoint left from its current posture. A teacher with a different arm can show the effect of pushing a latch, yet its joint trajectory may be unusable on the student. Even a successful coached attempt leaves a further question: can the student perform the skill after the teacher disconnects?

We evaluate these questions separately. First, we intervene on the content of a teacher demonstration while holding the student learning rule fixed. Second, we let a language model choose its own experiments and requests. Finally, we measure what the frozen student can do from new starts. This design exposes cases in which a useful transferred skill coexists with poor teaching decisions. We use task-level success after teaching as the outcome. A compelling diagnosis in natural language earns no credit unless the selected intervention leaves the student with a usable skill.

#align(center,image("figures/cross-body.svg",width:100%))
#cap[*Figure 1.* A rotary-lift teacher opens a gated drawer. The sliding student receives measured handle motion from the matching fixture (B) or another fixture (C). Gold is the handle and catch, red the fixed gate, and teal the tool. The dotted path follows the measured tool endpoint. The examples share a student starting gap of 8 mm.]

#pagebreak()
= 2. Problem formulation and related work
Let a student retain parameters $theta$ and expose bounded motor commands, a controller mode, a clock, and measured task coordinates. An episode begins with a task goal and a hidden actuator or fixture configuration. At a teaching decision the supervisor receives the public history $H_t$ of issued commands, observed motion, object progress, and previous interventions. The executor can inspect the simulator configuration to instantiate and score an episode. Its hidden condition label is excluded from $H_t$. A source teacher may use a different mechanism and policy, and its motor commands are private.

The supervisor selects one action from a finite menu. A *probe* changes the student model using a bounded diagnostic measurement. A *teacher request* returns a task-space observation sequence and updates a student subgoal. *Practice* executes the student's current skill. *Assess* ends teaching. We also end teaching when the decision budget expires. We then copy or freeze $theta$, create fresh starting configurations, and disable the teaching agent and source teacher. The evaluation measures the joint effect of curriculum selection and student learning. It makes no assumption that the supervisor's verbal explanation identifies the true cause.

== What transfers across bodies?
Active self-modeling has shown that a robot can infer useful aspects of its structure through interaction and use them to recover or control motion @selfmodel @kwia. In our experiments that insight motivates a quantitative competitor: a local mapping from anonymous motor pulses to measured endpoint displacement. Confidence-based autonomy already lets a learner request demonstrations at uncertain states @cba. Its precedent makes the *type of uncertainty* important here. A motor sign can be learned from the student's motion, whereas a missing latch-release sequence can be observed on another robot.

Cross-embodiment inverse reinforcement learning uses demonstrations from different bodies to recover a shared measure of task progress @xirl. Generalist policies such as Octo use heterogeneous demonstrations for pretraining and adaptation @octo. We instead provide a small, explicit correspondence: drawer translation and handle height expressed in a calibrated common frame. The keyed-fixture experiment asks whether this restricted communication channel carries enough information for a different actuator mechanism. It does not estimate performance with learned visual correspondences or unknown camera calibration.

== Agent efficiency and evaluation
Language Model Predictive Control studies teaching efficiency through corrections during human–robot interaction @lmpc. We measure the lasting student skill after teaching and distinguish three resources: target-robot interaction, teacher demonstrations, and model calls. They have different costs. A supervisor can save inference by practicing automatically, yet spend more time on an unsuccessful skill. We therefore report the metrics separately. Only the development-stage threshold-selection criterion fixes an explicit exchange rate between success and motor pulses.

Our empirical questions are (i) whether a matching object-motion segment transfers across different joint types, (ii) whether a supervisor can distinguish a mapping failure from a strategy failure, and (iii) whether a discrepancy between predicted and observed motion can identify when recalibration pays for itself. Task-specific numerical rules are strong comparators because they use the same observable evidence and avoid inference cost. The experiments evaluate the restricted tasks on which those rules were constructed.

== Interpreting the comparison
A failed drawer pull gives a single binary observation. In the reversed-motor case the tool travels away from the handle. In the gated case it moves forward until contact arrests the catch. A task label alone collapses these observations. A tool-motion report distinguishes them in the ideal fixture; a future camera-based system would also need uncertainty on direction, occlusion, and contact. A demonstration intervenes on the next attempted subgoal, and a free-space pulse intervenes on the student's action map. Testing both on the same student separates the value of information from the choice to acquire it.

#pagebreak()
= 3. Teaching and evaluation protocol
== Drawer teaching
The initial student has two linear actuators for pulling and lifting. Its skill stores a horizontal polarity and a lift target, initially $+1$ and zero. A plain pull requests 90 mm. A positive 12 mm free-space pulse measures signed travel and updates the polarity if the absolute movement exceeds 4 mm. Position drives are force-limited. Physics advances at 240 Hz. Each command ramps and settles over 0.6 simulated seconds, and the trial log samples positions at 20 Hz. A successful independent trial requires at least 60 mm of drawer travel.

In the initial paired experiment the horizontal channel is reversed on an open fixture, or a stop obstructs the catch on a normally mapped fixture. The source teacher has two serial horizontal slides carrying unequal fractions of the stroke plus a lift motor. The student receives handle height and drawer displacement until the drawer first crosses 5 mm. It stores the maximum observed height plus a fixed 6 mm pin clearance. We run the pair in Isaac Sim 5.1 with PhysX and replicate the mechanisms with native Open Dynamics Engine (ODE) slider joints, springs, and contact constraints. All drawer variants use an idealized, gravity-free fixture.

The harder ODE fixture has a lateral gate with a 10 mm vertical passage. Both insufficient and excessive lift can block travel. Its teacher rotates a 150 mm lever on a translating carriage. The student uses a linear pin and a fixed 3 mm clearance. Expert motion may depend on the source teacher's own fixture. The student receives only task-space measurements from the requested segment. The matched and cyclically shuffled conditions use equal numbers of segments from the same library. A fixed 40 mm lift controls for a useful average behavior.

== Supervisor interface
The Qwen models @qwen run locally on a DGX Spark using llama.cpp, Q4_K_M weights, 12 CPU threads, temperature zero, seed 13, and disabled reasoning mode. A schema-constrained reply selects an action and supplies a short evidence statement. The original prompt describes the available updates. A raw report contains measured values. A later derived report also labels the direction of travel relative to the intended pull and whether the latest practice reached 60 mm. We introduced that report after observing raw-report errors and use separate combined-fault and new-height evaluations. The fixed rule probes when the tool moves backward on failed practice, requests a segment after other failed practice, practices after an update, and assesses after success.

#table(columns:(1.1fr,2.1fr,2.1fr),inset:5pt,stroke:.35pt+rgb("#bac6c7"),
table.header(th[Evaluation], th[Conditions varied], th[Experimental unit]),
[Paired drawers],[Motor sign × presence of a stop],[One budgeted teaching episode per fault combination],
[Keyed transfer],[3 gate heights × 4 sources of lift guidance],[Frozen skill at 3 starting gaps per combination],
[Integrated teaching],[Open or 16/34/52 mm lower gate edge × 2 motor signs],[8 episodes per supervisor, 3 tests per trained skill],
[Reaching],[2 or 3 revolute joints, anonymous channel order/sign],[Frozen map across new postures and directions])
#cap[*Table 1.* Hidden fixture IDs and annotated causes are available to the evaluator. The eight integrated cases are matched across supervisors. The 24 independent-execution starts within each method share eight teaching histories.]

Test pin gaps are 3, 8, and 12 mm. The initial practice counts toward interaction time and precedes five decision slots. Resets are automatic. Human reset labor and physical setup costs remain unmeasured.

#pagebreak()
= 4. Manipulation results
== Correct demonstrations transfer
At lower passage bounds of 12, 30 and 48 mm, the source teacher produced visibly different handle trajectories. The sliding student passed all 9 starts with the matching demonstration. With segments cyclically assigned to the wrong gate it passed 0/9. The fixed lift passed 3/9, all on the middle gate. A plain pull passed 0/9. In the middle fixture, the measured teacher lift reached about 36.6 mm before first translation. In the 8 mm-gap example the matched student opened the drawer 82.0 mm, while the mismatched one stopped at 4.0 mm. The content intervention establishes a causal effect within these fixtures conditional on obtaining a demonstration.

== Choosing when to ask
On the original two single-fault cases, the 8B raw-report model passed 0/6 starts. It assessed a skill after a 90.2 mm backward movement with zero drawer displacement. The derived report improved success to 3/6. On the latch-only trial Qwen repeatedly practiced despite a verified positive motor response. ODE reproduced the same success counts for the derived report and the fixed rule (3/6 and 6/6). On the two remaining PhysX combinations, both Qwen and the rule passed 6/6. A probe-then-demo sequence solved the combined fault but also requested an unnecessary demonstration when only polarity was wrong.

#let row(label, d) = (label, str(d.episodes)+"/8", str(d.passed)+"/24", str(d.calls),str(d.queries),str(d.pulses))
#table(columns:(1.7fr,1fr,1fr,.8fr,.9fr,.8fr),inset:5pt,stroke:.35pt+rgb("#bac6c7"),
table.header(th[Supervisor],th[Episodes],th[Starts],th[Calls],th[Demos],th[Probes]),
..row([Fixed rule],models.rule),..row([Qwen3-8B],models.small),
..(if "large" in models {row([Qwen3-32B],models.large)} else {()}))
#cap[*Table 2.* Integrated keyed drawers. An episode passes when the frozen student succeeds at all three new gaps. Calls, requested full teacher executions, and diagnostic pulses are totals across the eight teaching episodes.]

The 8B model solved both open drawers and all three reversed-channel keyed drawers. It failed each normally mapped keyed drawer, for 5/8 episodes. On those failures it verified the mapped motor and continued practicing the unchanged skill. It requested four demonstrations in total, including one on an open, reversed-channel fixture. The rule requested six, one for each keyed fixture, and passed 8/8 episodes. Thus a lower query count alone would favor a method that withheld needed lessons.

#let size-note = if "large" in models [Under the same prompt and episode budget, Qwen3-32B passed #models.large.episodes of eight episodes, made #models.large.calls calls and requested #models.large.queries demonstrations. Median decision latency was #models.large.latency s for 32B and #models.small.latency s for 8B on the Spark CPU. These descriptive timings include prompt processing and generation.] else [The 32B paired comparison was still running at the time of this compile.]
#size-note

== Does calling the agent less often help?
On four additional ODE cases with horizontal gain 0.92 and a 6 mm training gap, automatically practicing after an update and assessing after observed success reduced Qwen calls from 13 to 7. Teacher requests fell from two to zero. Success fell from 9/12 to 6/12 starts, while student interaction increased from 7.2 to 7.8 simulated seconds. The rule passed 12/12 in 7.2 seconds with two demonstrations. Giving routine steps to a controller changed which observations reached the supervisor at its next decision.

#let cells(d)=("normal","reverse").map(pol => ("open","16","34","52").map(g => str(d.splits.at(g+"-"+pol))+"/3")).flatten()
#table(columns:(1.55fr, ..(0.70fr,)*8),inset:3.5pt,stroke:.30pt+rgb("#bac6c7"),
table.header(th[Map / gate],table.cell(colspan:4,align:center)[*Normal motor*],table.cell(colspan:4,align:center)[*Reversed motor*]),
[Lower bound], [Open],[16],[34],[52],[Open],[16],[34],[52],
[Qwen3-8B],..cells(models.small),..(if "large" in models {([Qwen3-32B],..cells(models.large))} else {()}),
[Fixed rule],..cells(models.rule))
#cap[*Table 3.* Held-out starts passed per teaching episode. Columns refer to lower bounds on permitted handle lift in millimetres. All supervisors have access to the same matching teacher.]

#pagebreak()
= 5. Reaching and selective recalibration
The planar arms have two or three torque-driven revolute joints with different lengths and hidden channel orders and signs. The student sees the endpoint in a calibrated plane. A +0.07 rad target pulse on channel $j$ estimates column $j$ of a local motor map $J$ from the measured endpoint displacement divided by pulse amplitude. At each control step it computes $Delta u = J^top (J J^top + 0.0004 I)^(-1) e$ for endpoint error $e$ and clips each component to ±0.2 rad. The map remains frozen during independent execution. Physics runs at 960 Hz, and the controller may issue up to twelve 0.6 s commands.

For a 100 mm leftward displacement, both Qwen-selected calibration and a fixed one-pulse-per-channel sequence passed all six new-posture tests within 10 mm. Their final errors were identical (3.0–8.4 mm). Qwen consumed nine pulses across the two arms before its decision budgets expired. Five pulses sufficed to fit the same columns. The untrained zero map produced 100 mm error on every start.

#align(center,image("figures/workspace.svg",width:96%))
#cap[*Figure 2.* Each cell is one 100 mm reaching trial. Rows within each panel are target directions and columns are starting-posture shifts. Green indicates success, rust a miss within the radial bound, and gray a target outside the geometric reach annulus including tolerance. The bound ignores joint limits.]

Across 13 posture shifts and eight directions per arm, the retained map passed 102/208 trials and locally refitting at each posture passed 166/208. Of 208 targets, 35 lay outside the radial bound and failed both methods. Refitting adds two or three pulses per starting posture and can be amortized across directions. The difference is largest on the three-link arm (41 versus 85 successes), motivating a decision about when the extra measurements are worthwhile.

We compare four switching policies on a distinct 48-case three-link grid. A diagnostic first move yields a residual equal to the norm of actual minus predicted displacement divided by predicted displacement norm. On the two-link development grid we selected a threshold by maximizing successful trials minus 0.05 per additional pulse. The resulting threshold, 0.5182, was frozen. On the test grid, shifts are ±12°, ±36° and ±72°, and the eight target directions are offset by 22.5°. Each reprobing decision incurs a reset and three pulses.

Always keeping the old map passed 24/48. Qwen3-8B always requested reprobing, matching the always-refit method at 39/48 with 48 resets and 144 extra pulses. The threshold also passed 39/48 with 30 resets and 90 pulses. Counting the diagnostic step, probes, and movement commands, the threshold used 344 commands versus 414 for always-refit. The observed trade-off favors a simple residual gate on this structured task. The rule threshold was fitted using two-link outcomes. The language model received the first-step measurements and reprobe cost but no three-link outcomes when choosing. Both continuation options were subsequently simulated from matched initial states. This paired evaluation can reveal unnecessary probes without exposing counterfactual success to the acting supervisor.

#pagebreak()
= 6. Real demonstrations, limits, and next tests
A recorded teacher may not expose the object measurements our simulator supplies. We audited the first three episodes selected by an exact drawer-opening task pattern in a pinned LeRobot conversion of DROID @droid. The pattern selected 132 of 92,233 metadata entries in that conversion. We reviewed both exterior cameras and the wrist camera, marked broad visible-opening intervals, and tested an upward crossing of 0.1 in the observed gripper channel. Only episode 877 crossed, at frame 102. The gripper channel was constant throughout episodes 290 and 2081 even though their drawers visibly opened. These observations motivate tracking object progress directly. Three ordered clips cannot establish a detection rate for DROID as a whole.

#align(center,image("figures/droid.jpg",width:100%))
#cap[*Figure 3.* Exterior frames from the reviewed opening intervals. DROID, Khazatsky et al. @droid, CC BY 4.0, via the IPEC-COMMUNITY conversion. Frames were extracted, resized, and labelled for this audit.]

== Scope of the evidence
Online tests use small, deterministic simulated fixtures with predefined actions, calibrated coordinates, and resettable starts. The teacher is scripted and can know its own fixture. Its query cost includes simulated execution, while creating the expert policy has no measured cost here. The initial drawers share Cartesian axes, and the keyed experiment supplies a known object correspondence. Runtime comparisons use local CPU inference. Qwen output depends on checkpoint, quantization, decoding settings, prompt, and tool descriptions. We report matched outcomes and paired costs without treating multiple starts from one learned skill as independent teaching runs. The demonstrations in Figure 3 are physical recordings; no student policy in this work was tested on hardware.

A hardware study should blind the cause of each failure and preregister task thresholds, interaction budgets, and episode-level repetitions. First test two arm families with camera-estimated object motion and independent motor limits. Pair a reachable alternative strategy with an infeasible task to score premature abandonment. Then test balance or locomotion with source contact timing and different student dynamics. The central question remains whether task-conditioned information gathering beats a tuned numerical policy after counting physical practice, resets, demonstrations, and independent success.

#cap[*Artifacts.* #link(repo)[Code, prompts, measured trajectories, milestone films, and evaluation protocols.] The released logs retain failed trials, student checkpoints or skill parameters, and supervisor choices.]
#v(2pt)
#text(size:13pt,weight:"bold")[References]
#block[#set text(size:8.8pt)
#set par(leading:.35em, spacing:.25em)
#bibliography("references.bib",style:"ieee",title:none)]
