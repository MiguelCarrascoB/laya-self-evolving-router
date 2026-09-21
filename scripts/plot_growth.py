"""Render the cold-start curve from a results JSON into a standalone SVG.

Usage: python scripts/plot_growth.py [results.json] [out.svg]

Plots, against the prompt stream: the registry size at route time, and the
share of the last WINDOW prompts that landed in `other`. Only first-pass
events count -- the log also holds re-route events, and mixing the two makes
the curve climb at the tail, where the hardest prompts are drained.
"""

from __future__ import annotations

import json
import sys

WINDOW = 50
W, H = 880, 330
L, R, T, B = 56, 52, 40, 46  # margins
OTHER, CATS, AXIS = "#E69F00", "#56B4E9", "#8b949e"  # Okabe-Ito, matches the visualizer


def first_pass(events: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for e in events:
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e)
    return out


def series(events: list[dict]) -> tuple[list[float], list[int]]:
    rate, cats = [], []
    for i, e in enumerate(events):
        win = events[max(0, i - WINDOW + 1) : i + 1]
        rate.append(sum(1 for w in win if w["route"] == "other") / len(win))
        cats.append(e["categories_at_route"])
    return rate, cats


def path(values, n, vmax) -> str:
    pts = []
    for i, v in enumerate(values):
        x = L + (W - L - R) * (i / max(n - 1, 1))
        y = T + (H - T - B) * (1 - v / vmax)
        pts.append(f"{x:.1f},{y:.1f}")
    return "M" + " L".join(pts)


def render(results: dict) -> str:
    events = first_pass(results["events"])
    rate, cats = series(events)
    n = len(events)
    cap = max(max(cats), 1)
    top = -(-cap // 4) * 4  # round the right axis up so its ticks land on gridlines
    x0, x1, y0, y1 = L, W - R, T, H - B

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="11" role="img" '
        f'aria-label="The other-rate falls as the registry grows from 0 to {cap} categories, then plateaus">'
    ]
    for frac in (0, 0.25, 0.5, 0.75, 1):
        y = y1 - (y1 - y0) * frac
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{AXIS}" stroke-opacity="0.2"/>')
        p.append(f'<text x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{AXIS}">{frac * 100:.0f}%</text>')
        p.append(f'<text x="{x1 + 8}" y="{y + 4:.1f}" fill="{AXIS}">{frac * top:.0f}</text>')
    for frac in (0, 0.25, 0.5, 0.75, 1):
        x = x0 + (x1 - x0) * frac
        p.append(f'<text x="{x:.1f}" y="{y1 + 20}" text-anchor="middle" fill="{AXIS}">{frac * n:.0f}</text>')

    p.append(f'<path d="{path(cats, n, top)}" fill="none" stroke="{CATS}" stroke-width="2"/>')
    p.append(f'<path d="{path(rate, n, 1.0)}" fill="none" stroke="{OTHER}" stroke-width="2"/>')

    p.append(f'<text x="{x0}" y="{T - 18}" fill="{OTHER}" font-weight="600">'
             f'share of last {WINDOW} prompts routed to "other" (left)</text>')
    p.append(f'<text x="{x1}" y="{T - 18}" text-anchor="end" fill="{CATS}" font-weight="600">'
             f'categories in registry (right)</text>')
    p.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{H - 8}" text-anchor="middle" fill="{AXIS}">'
             f'prompts seen (first pass, n={n})</text>')
    p.append("</svg>")
    return "\n".join(p) + "\n"


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "results/results-v3-full.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "docs/growth.svg"
    with open(src, encoding="utf-8") as f:
        svg = render(json.load(f))
    with open(dst, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {dst} from {src}")
