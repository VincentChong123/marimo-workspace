import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium", app_title="Marimo Workspace")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    return alt, mo, np, pd


@app.cell
def _(mo):
    mo.md("""
    # 🪐 Welcome to Marimo Workspace

    This workspace contains reactive Python notebooks, data apps, and agentic workflows built with [marimo](https://marimo.io).

    ### Features:
    - **Pure Python**: Every notebook is stored as a standard `.py` file.
    - **Reactive Execution**: When an input changes, only dependent cells re-run.
    - **ASGI & Production Ready**: Deploy directly as a web application.
    """)


@app.cell
def _(mo):
    # Interactive UI Controls
    slider = mo.ui.slider(start=10, stop=100, step=5, value=30, label="Sample Size")
    metric = mo.ui.dropdown(
        options=["Gaussian", "Uniform", "Exponential"],
        value="Gaussian",
        label="Distribution",
    )
    mo.hstack([slider, metric], justify="start")
    return metric, slider


@app.cell
def _(alt, metric, np, pd, slider):
    # Reactive Data Generation
    n = slider.value
    dist = metric.value

    rng = np.random.default_rng(42)
    if dist == "Gaussian":
        data = rng.normal(loc=0, scale=1, size=n)
    elif dist == "Uniform":
        data = rng.uniform(low=-2, high=2, size=n)
    else:
        data = rng.exponential(scale=1, size=n)

    df = pd.DataFrame({"Index": range(1, n + 1), "Value": data})

    chart = (
        alt.Chart(df)
        .mark_bar(opacity=0.7, color="#4F46E5")
        .encode(
            x=alt.X("Index:Q", title="Index"),
            y=alt.Y("Value:Q", title="Value"),
            tooltip=["Index", "Value"],
        )
        .properties(title=f"{dist} Distribution ({n} samples)", width="container", height=300)
    )
    return chart, df


@app.cell
def _(chart, df, mo):
    mo.vstack([
        chart,
        mo.accordion({"View Raw Data": mo.ui.table(df, pagination=True)}),
    ])


if __name__ == "__main__":
    app.run()
