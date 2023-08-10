#!/usr/bin/env python
from pathlib import Path
from typing import cast

import plotly.graph_objects as go
from bs4 import BeautifulSoup
from minify_html import minify
from plotly.offline import get_plotlyjs

from ridgeplot._testing import import_pyscript_as_module, patch_plotly_show

PATH_ROOT = Path(__file__).parents[1]
PATH_EXAMPLES = PATH_ROOT.joinpath("examples")
PATH_CHARTS = PATH_ROOT.joinpath("docs/_static/charts")

RAW_HTML_IFRAME_RST_TEMPLATE = """
```{{raw}} html
<iframe src="/{src}" height="{height}" width="{width}" style="{style}"></iframe>
```
"""


def _compile_plotly_fig(example_script: Path, minify_html: bool = True) -> None:
    print(f"Getting the Plotly Figure from: {example_script}...")
    example_module = import_pyscript_as_module(example_script)
    main_func = example_module.main
    fig = cast(go.Figure, main_func())

    width = fig.layout.width
    height = fig.layout.height
    assert isinstance(width, int)
    assert isinstance(height, int)

    # Reduce the figure's margins to more tightly fit the chart
    # (only if the user hasn't already customized the margins!)
    if fig.layout.margin == go.layout.Margin():
        fig = fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))

    html_str = fig.to_html(include_plotlyjs="directory", full_html=True)

    # Edit the style of the <body> tag to remove the default margins
    # (these margin values can be inherited from user agent stylesheets)
    soup = BeautifulSoup(html_str, "html.parser")
    assert soup.body.style is None
    soup.body["style"] = "margin: 0; padding: 0;"
    html_str = str(soup)

    if minify_html:
        html_str = minify(html_str, minify_js=True)

    out_path = PATH_CHARTS / f"{example_script.stem}.html"
    print(f"Writing HTML artefact to {out_path}...")
    out_path.write_text(html_str, "utf-8")

    out_image = PATH_CHARTS / f"{example_script.stem}.webp"
    print(f"Writing WebP artefact to {out_image}...")
    fig.write_image(
        out_image,
        format="webp",
        width=width,
        height=height,
        scale=3,
        engine="kaleido",
    )

    src = out_path.relative_to(PATH_ROOT.joinpath("docs")).as_posix()
    raw_html_iframe_rst_snippet = RAW_HTML_IFRAME_RST_TEMPLATE.format(
        src=src,
        height=height,
        width="100%",
        style="border:none;overflow:hidden;",
    )
    print("Success! Copy and past the following MyST snippet to include the chart in the docs:")
    print("=" * 80)
    print(raw_html_iframe_rst_snippet)
    print("=" * 80)
    print()


def _write_plotlyjs_bundle():
    bundle_path = PATH_CHARTS / "plotly.min.js"
    plotlyjs = get_plotlyjs()
    bundle_path.write_text(plotlyjs, encoding="utf-8")


def main():
    print("Writing Plotly.js bundle...")
    _write_plotlyjs_bundle()
    print("Patching `plotly.show()`...")
    patch_plotly_show()
    for example_script in PATH_EXAMPLES.glob("*.py"):
        _compile_plotly_fig(example_script)


if __name__ == "__main__":
    main()
