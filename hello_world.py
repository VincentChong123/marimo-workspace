# /// script
# dependencies = [
#     "altair>=6.3.0",
#     "marimo>=0.23.3",
#     "numpy>=2.5.3",
#     "pandas>=3.0.6",
#     "pillow>=12.3.0",
# ]
# [tool.marimo.runtime]
# auto_instantiate = false
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():

    import marimo as mo
    import numpy as np
    from PIL import Image


    return Image, mo, np


@app.cell
def _(mo):
    mo.md("""
    # Hello, world — Marimo demo

    This mini notebook shows how to display an image pasted from your clipboard into a markdown cell, alongside some basic interactivity.

    Instructions to paste an image into a markdown cell:

    1. Copy an image to your clipboard.
    2. Create a new markdown cell (press M in command mode or use the + button and choose Markdown).
    3. Paste (Ctrl/Cmd+V) directly in the markdown editor.
    4. Marimo will embed the image and render it below.

    Below is a placeholder image to verify rendering. Replace this cell with your own pasted image when ready.
    """)


@app.cell
def _(Image, mo, np):
    # Placeholder image displayed with mo.image(). You can remove this once you paste your own image in markdown.
    # We programmatically generate a small image so the notebook is fully self-contained in Pyodide.

    # Create a simple RGB gradient image in memory
    w, h = 128, 64
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            arr[y, x, 0] = int(255 * x / (w - 1))
            arr[y, x, 1] = int(255 * y / (h - 1))
            arr[y, x, 2] = 128

    img = Image.fromarray(arr, mode="RGB")
    mo.image(img)


@app.cell
def _(mo):
    # A minimal interactive widget to show reactivity works
    name_input = mo.ui.text(value="Marimo", label="Your name")
    name_input
    return (name_input,)


@app.cell
def _(mo, name_input):
    # Use the value from the previous cell in a reactive markdown greeting
    mo.md(f"Hello, {name_input.value}! Paste an image into a markdown cell above to see it render inline.")


@app.cell
def _(mo):
    # Optional: show how markdown with pasted image looks. After you paste an image in a markdown cell,
    # it will appear as an <img> with a data URL. Here's an example template you can copy into a markdown cell:

    mo.md("""
    Paste an image here by focusing this markdown cell and pressing Ctrl/Cmd+V.

    Example (you will replace this with your own pasted image):

    ![Pasted image goes here](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/eq8qH0AAAAASUVORK5CYII=)
    """)


if __name__ == "__main__":
    app.run()
