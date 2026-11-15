# Rebuilding the six-page manuscript

[Read the PDF](embodied-self-calibration.pdf) or edit [the Typst source](manuscript.typ). The report uses project authorship and does not claim venue submission or acceptance.

From the repository root, run the following with Python, NumPy, Matplotlib, Pillow, FFmpeg and Typst 0.15.1:

```bash
python paper/model_results.py
python paper/figures.py
typst compile paper/manuscript.typ paper/embodied-self-calibration.pdf
pdfinfo paper/embodied-self-calibration.pdf
```

Figure 1 is a projection of saved mechanism positions from the keyed demonstration control. Figure 2 uses all recorded workspace outcomes. Figure 3 uses resized DROID frames from the attributed milestone film. [DROID source and attribution](../experiments/droid/README.md)

Tables 2–3 read model-results.json, generated from the complete eight-episode runs. Each group of three starts shares a frozen skill. The count of starts is an execution metric and is not a count of independent teaching episodes. [All results and milestone videos](../progress.md)

The supplementary observation-error study uses paired ODE executions under prespecified noise and frame offsets. The headline manuscript figures use the original four noise seeds. Additional daily replications are reported separately in the progress ledger. [Observation study protocol and records](../progress.md#next-experiment-registered-before-execution--observation-error)

The walkthrough pairs each manuscript page with measured footage and an English subtitle track. Rebuild it with Pillow, Poppler, FFmpeg and piper-tts 1.8.0, using the [LJSpeech medium voice and model card](https://huggingface.co/rhasspy/piper-voices/blob/1162a9173d0ce503555aed757976b7a9912eae4c/en/en_US/ljspeech/medium/MODEL_CARD). The last chapter reuses the credited DROID replay. From the repository root:

```bash
python paper/walkthrough.py /path/to/en_US-ljspeech-medium.onnx runs/walkthrough.mp4
```
