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
