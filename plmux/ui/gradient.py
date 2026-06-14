"""Shared color gradient utilities for clock and status bar effects."""

from __future__ import annotations

import colorsys


def try_parse_hex(color: str) -> tuple[int, int, int] | None:
    c = color.lstrip("#")
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except (ValueError, IndexError):
        return None


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> str:
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return rgb_to_hex(r, g, b)


def hsl_gradient(
    base_rgb: tuple[int, int, int],
    num_steps: int,
    *,
    hue_range: float = 60,
    sat_boost: float = 1.15,
    light_start_offset: float = 0.30,
    light_end_offset: float = -0.10,
    sat_min: float = 0.4,
    sat_max: float = 0.85,
    light_min: float = 0.20,
    light_max: float = 0.80,
) -> list[str]:
    r, g, b = (x / 255.0 for x in base_rgb)
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)

    start_hue = (h * 360 - hue_range * 0.45) % 360
    sat = max(sat_min, min(sat_max, s * sat_boost))

    result = []
    for i in range(num_steps):
        t = i / max(1, num_steps - 1)
        smooth_t = t * t * (3 - 2 * t)

        hue = (start_hue + hue_range * smooth_t) / 360
        light = lightness + light_start_offset * (1 - smooth_t) + light_end_offset * smooth_t
        light = max(light_min, min(light_max, light))

        rr, gg, bb = colorsys.hls_to_rgb(hue, light, sat)
        result.append(f"#{int(rr * 255):02x}{int(gg * 255):02x}{int(bb * 255):02x}")

    return result


def pick_base_color(fg: str, bg: str) -> tuple[int, int, int] | None:
    base = try_parse_hex(fg)
    if base:
        return base
    return try_parse_hex(bg)
