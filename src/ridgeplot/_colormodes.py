from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from ridgeplot._colors import ColorScale, apply_alpha, interpolate_color, normalise_colorscale
from ridgeplot._types import CollectionL2
from ridgeplot._utils import get_xy_extrema, normalise_min_max

if TYPE_CHECKING:
    from collections.abc import Collection

    from ridgeplot._colors import Color
    from ridgeplot._types import Densities, Numeric

Colormode = Literal["row-index", "trace-index", "trace-index-row-wise", "mean-minmax", "mean-means"]
"""The :paramref:`ridgeplot.ridgeplot.colormode` argument in
:func:`ridgeplot.ridgeplot()`."""

ColorsArray = CollectionL2[str]
"""A :data:`ColorsArray` represents the colors of traces in a ridgeplot.

Example
-------

>>> colors_array: ColorsArray = [
...     ["red", "blue", "green"],
...     ["orange", "purple"],
... ]
"""

ColorscaleInterpolants = CollectionL2[float]
"""A :data:`ColorscaleInterpolants` contains the interpolants for a :data:`ColorScale`.

Example
-------

>>> interpolants: ColorscaleInterpolants = [
...     [0.2, 0.5, 1],
...     [0.3, 0.7],
... ]
"""


@dataclass
class InterpolationContext:
    densities: Densities
    n_rows: int
    n_traces: int
    x_min: Numeric
    x_max: Numeric

    @classmethod
    def from_densities(cls, densities: Densities) -> InterpolationContext:
        x_min, x_max, _, _ = map(float, get_xy_extrema(densities=densities))
        return cls(
            densities=densities,
            n_rows=len(densities),
            n_traces=sum(len(row) for row in densities),
            x_min=x_min,
            x_max=x_max,
        )


class InterpolationFunc(Protocol):
    def __call__(self, ctx: InterpolationContext) -> ColorscaleInterpolants: ...


def _mul(a: tuple[Numeric, ...], b: tuple[Numeric, ...]) -> tuple[Numeric, ...]:
    """Multiply two tuples element-wise."""
    return tuple(a_i * b_i for a_i, b_i in zip(a, b))


def _interpolate_row_index(ctx: InterpolationContext) -> ColorscaleInterpolants:
    return [
        [((ctx.n_rows - 1) - ith_row) / (ctx.n_rows - 1)] * len(row)
        for ith_row, row in enumerate(ctx.densities)
    ]


def _interpolate_trace_index(ctx: InterpolationContext) -> ColorscaleInterpolants:
    ps = []
    ith_trace = 0
    for row in ctx.densities:
        ps_row = []
        for _ in row:
            ps_row.append(((ctx.n_traces - 1) - ith_trace) / (ctx.n_traces - 1))
            ith_trace += 1
        ps.append(ps_row)
    return ps


def _interpolate_trace_index_row_wise(ctx: InterpolationContext) -> ColorscaleInterpolants:
    return [
        [((len(row) - 1) - ith_row_trace) / (len(row) - 1) for ith_row_trace in range(len(row))]
        for row in ctx.densities
    ]


def _interpolate_mean_minmax(ctx: InterpolationContext) -> ColorscaleInterpolants:
    ps = []
    for row in ctx.densities:
        ps_row = []
        for trace in row:
            x, y = zip(*trace)
            ps_row.append(
                normalise_min_max(sum(_mul(x, y)) / sum(y), min_=ctx.x_min, max_=ctx.x_max)
            )
        ps.append(ps_row)
    return ps


def _interpolate_mean_means(ctx: InterpolationContext) -> ColorscaleInterpolants:
    means = []
    for row in ctx.densities:
        means_row = []
        for trace in row:
            x, y = zip(*trace)
            means_row.append(sum(_mul(x, y)) / sum(y))
        means.append(means_row)
    min_mean = min([min(row) for row in means])
    max_mean = max([max(row) for row in means])
    return [
        [normalise_min_max(mean, min_=min_mean, max_=max_mean) for mean in row] for row in means
    ]


def compute_trace_colors(
    colorscale: ColorScale | Collection[Color] | str,
    colormode: Colormode,
    coloralpha: float | None,
    interpolation_ctx: InterpolationContext,
) -> ColorsArray:
    colorscale = normalise_colorscale(colorscale)
    if coloralpha is not None:
        coloralpha = float(coloralpha)

    def _get_color(p: float) -> str:
        color = interpolate_color(colorscale, p=p)
        if coloralpha is not None:
            color = apply_alpha(color, alpha=coloralpha)
        return color

    if colormode not in COLORMODE_MAPS:
        raise ValueError(
            f"The colormode argument should be one of "
            f"{tuple(COLORMODE_MAPS)}, got {colormode} instead."
        )

    interpolate_func = COLORMODE_MAPS[colormode]
    interpolants = interpolate_func(ctx=interpolation_ctx)
    return [[_get_color(p) for p in row] for row in interpolants]


COLORMODE_MAPS: dict[Colormode, InterpolationFunc] = {
    "row-index": _interpolate_row_index,
    "trace-index": _interpolate_trace_index,
    "trace-index-row-wise": _interpolate_trace_index_row_wise,
    "mean-minmax": _interpolate_mean_minmax,
    "mean-means": _interpolate_mean_means,
}
