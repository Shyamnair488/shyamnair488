"""
Self-hosted SVG renderers for the profile README.

Every visual is generated here (pure standard library) and committed to
`assets/`, so the profile never depends on third-party card services.
Animations use SMIL + a little CSS, which GitHub renders inside <img> tags.
"""

from __future__ import annotations

import html
import math
import textwrap

FONT = "'Segoe UI',system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

CYAN, BLUE, VIOLET, PINK = "#00f7ff", "#0e75b6", "#7b2ff7", "#ff4d8d"
GREEN, GOLD, ORANGE = "#3fb950", "#f1c40f", "#ff9f43"
TEXT, MUTE, BORDER = "#e6edf3", "#8b949e", "#30363d"

PALETTE = [CYAN, VIOLET, PINK, GOLD, GREEN, ORANGE, BLUE, "#e84393"]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt(n) -> str:
    n = int(n)
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"


# --------------------------------------------------------------------------- #
# building blocks
# --------------------------------------------------------------------------- #
BASE_DEFS = f"""
<linearGradient id="g-accent" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/>
</linearGradient>
<linearGradient id="g-warm" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{GOLD}"/>
</linearGradient>
<linearGradient id="g-panel" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#161b22"/><stop offset="1" stop-color="#0d1117"/>
</linearGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
  <feGaussianBlur stdDeviation="3" result="b"/>
  <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
"""


def svg(w: int, h: int, body: str, defs: str = "", css: str = "", title: str = "") -> str:
    t = f"<title>{esc(title)}</title>" if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">{t}\n<defs>{BASE_DEFS}{defs}</defs>\n'
        f"<style>text{{font-family:{FONT}}}.m{{font-family:{MONO}}}{css}</style>\n"
        f"{body}\n</svg>\n"
    )


def card(w: int, h: int) -> str:
    return (
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="16" fill="url(#g-panel)" '
        f'stroke="{BORDER}" stroke-width="2"/>'
        f'<rect x="28" y="1" width="90" height="3" rx="1.5" fill="url(#g-accent)"/>'
    )


def delayed(attr: str, start, end, delay: float, dur: float, extra: str = "") -> str:
    """<animate> that holds `start` for `delay` seconds then eases to `end`.
    Starts at t=0 so there is no flash of the final state before the delay."""
    total = delay + dur
    k = delay / total if total else 0
    return (
        f'<animate attributeName="{attr}" values="{start};{start};{end}" '
        f'keyTimes="0;{k:.4f};1" dur="{total:.2f}s" begin="0s" fill="freeze" {extra}/>'
    )


def wrap(text: str, width: int, lines: int) -> list[str]:
    out = textwrap.wrap(text or "", width=width)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1].rstrip(" .,;") + "…"
    return out


def ago_days(days: int) -> str:
    if days < 1:
        return "today"
    if days < 14:
        return f"{days}d ago"
    if days < 60:
        return f"{days // 7}w ago"
    if days < 700:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


# --------------------------------------------------------------------------- #
# 1. HERO
# --------------------------------------------------------------------------- #
def hero(name: str, subtitle: str, roles: list[str], w: int = 1000, h: int = 290) -> str:
    slot = 3.2
    n = max(len(roles), 1)
    role_els = []
    for i, role in enumerate(roles or [""]):
        first = i == 0
        kt = f"0;0.03;{0.95/n:.4f};{1/n:.4f};1"
        vals = "0;1;1;0;0"
        anim = (
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{kt}" '
            f'dur="{n*slot:.1f}s" begin="{i*slot:.1f}s" repeatCount="indefinite"/>'
        )
        role_els.append(
            f'<text class="m" x="64" y="232" font-size="25" fill="{CYAN}" opacity="{1 if first else 0}">'
            f'<tspan fill="{PINK}">&gt;</tspan> {esc(role)}{anim}</text>'
        )
    cursor = (
        f'<rect x="64" y="244" width="14" height="3" fill="{CYAN}">'
        f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>'
    )

    defs = f"""
<linearGradient id="hero-bg" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#070b16"/><stop offset="0.55" stop-color="#101234"/>
  <stop offset="1" stop-color="#1a0f3a"/>
</linearGradient>
<linearGradient id="hero-name" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="{CYAN}"/>
  <stop offset="1" stop-color="{VIOLET}"/>
</linearGradient>
<filter id="blur"><feGaussianBlur stdDeviation="38"/></filter>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
  <path d="M40 0H0V40" fill="none" stroke="#ffffff" stroke-opacity="0.045" stroke-width="1"/>
</pattern>
<clipPath id="hero-clip"><rect width="{w}" height="{h}" rx="20"/></clipPath>
"""
    orbit = ""
    for i, (r, dur, col) in enumerate([(58, 14, CYAN), (92, 22, VIOLET), (126, 34, PINK)]):
        sign = 360 if i % 2 == 0 else -360
        orbit += (
            f'<circle r="{r}" fill="none" stroke="{col}" stroke-opacity="0.35" stroke-dasharray="3 9"/>'
            f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="{sign}" '
            f'dur="{dur}s" repeatCount="indefinite"/>'
            f'<circle cx="{r}" r="6" fill="{col}" filter="url(#glow)"/></g>'
        )

    body = f"""
<g clip-path="url(#hero-clip)">
  <rect width="{w}" height="{h}" fill="url(#hero-bg)"/>
  <rect width="{w}" height="{h}" fill="url(#grid)"/>
  <circle cx="190" cy="70" r="120" fill="{CYAN}" opacity="0.30" filter="url(#blur)">
    <animate attributeName="cx" values="190;420;190" dur="14s" repeatCount="indefinite"/>
  </circle>
  <circle cx="820" cy="230" r="130" fill="{VIOLET}" opacity="0.40" filter="url(#blur)">
    <animate attributeName="cx" values="820;600;820" dur="16s" repeatCount="indefinite"/>
  </circle>
  <circle cx="900" cy="40" r="90" fill="{PINK}" opacity="0.22" filter="url(#blur)">
    <animate attributeName="cy" values="40;140;40" dur="12s" repeatCount="indefinite"/>
  </circle>
  <g transform="translate({w-170},{h/2})">{orbit}
    <circle r="34" fill="#0d1117" stroke="url(#g-accent)" stroke-width="2"/>
    <text x="0" y="9" text-anchor="middle" font-size="24" font-weight="800" fill="{TEXT}">SN</text>
  </g>
  <text x="62" y="122" font-size="78" font-weight="800" letter-spacing="3" fill="url(#hero-name)">{esc(name.upper())}</text>
  <rect x="64" y="142" width="150" height="4" rx="2" fill="url(#g-warm)">
    <animate attributeName="width" values="30;220;30" dur="6s" repeatCount="indefinite"/>
  </rect>
  <text x="64" y="188" font-size="21" fill="#b6c2d0" letter-spacing="0.5">{esc(subtitle)}</text>
  {''.join(role_els)}
  {cursor}
</g>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="20" fill="none" stroke="{BORDER}" stroke-width="2"/>
"""
    return svg(w, h, body, defs, title=f"{name} — {subtitle}")


# --------------------------------------------------------------------------- #
# 2. TERMINAL (neofetch style)
# --------------------------------------------------------------------------- #
def terminal(handle: str, rows: list[tuple[str, str]], w: int = 1000) -> str:
    line_h = 27
    top = 92
    h = top + len(rows) * line_h + 36
    out = [card(w, h)]
    # window chrome
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        out.append(f'<circle cx="{34+i*22}" cy="30" r="6.5" fill="{c}"/>')
    out.append(
        f'<text class="m" x="{w/2}" y="35" text-anchor="middle" font-size="14" fill="{MUTE}">'
        f"{esc(handle)}@github: ~/profile</text>"
    )
    out.append(f'<line x1="1" y1="52" x2="{w-1}" y2="52" stroke="{BORDER}"/>')
    out.append(
        f'<text class="m" x="34" y="78" font-size="16" fill="{GREEN}">$ '
        f'<tspan fill="{TEXT}">neofetch --live</tspan></text>'
    )
    # vector logo (no dependency on font glyph widths)
    lx, ly = 150, top + 82
    hexpts = " ".join(
        f"{lx + 66*math.cos(math.pi/6 + k*math.pi/3):.1f},{ly + 66*math.sin(math.pi/6 + k*math.pi/3):.1f}"
        for k in range(6)
    )
    out.append(
        f'<polygon points="{hexpts}" fill="#0d1117" stroke="url(#g-accent)" stroke-width="3" filter="url(#glow)"/>'
        f'<text x="{lx}" y="{ly+19}" text-anchor="middle" font-size="52" font-weight="800" fill="url(#g-accent)">SN</text>'
        f'<g transform="translate({lx},{ly})"><g>'
        f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="9s" repeatCount="indefinite"/>'
        f'<circle cx="82" r="5" fill="{PINK}" filter="url(#glow)"/></g></g>'
        f'<text class="m" x="{lx}" y="{ly+104}" text-anchor="middle" font-size="13" fill="{MUTE}">@{esc(handle)}</text>'
    )
    # info rows
    x_key, x_val = 330, 500
    for i, (k, v) in enumerate(rows):
        y = top + 20 + i * line_h
        d = 0.35 + i * 0.28
        out.append(
            f'<g opacity="1"><animate attributeName="opacity" values="0;0;1" '
            f'keyTimes="0;{d/(d+0.3):.3f};1" dur="{d+0.3:.2f}s" begin="0s" fill="freeze"/>'
            f'<text class="m" x="{x_key}" y="{y}" font-size="16" font-weight="700" fill="{CYAN}">{esc(k)}</text>'
            f'<text class="m" x="{x_val}" y="{y}" font-size="16" fill="{TEXT}">{esc(v)}</text></g>'
        )
    # colour bar
    for i, c in enumerate(PALETTE):
        out.append(f'<rect x="{x_key+i*30}" y="{h-30}" width="26" height="10" rx="3" fill="{c}"/>')
    out.append(
        f'<rect x="{x_key+len(PALETTE)*30+6}" y="{h-32}" width="9" height="14" fill="{CYAN}">'
        f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>'
    )
    return svg(w, h, "".join(out), title="Live profile summary")


# --------------------------------------------------------------------------- #
# 3. DEVELOPER CARD (level / XP / achievements)
# --------------------------------------------------------------------------- #
def dev_card(name: str, handle: str, location: str, level: int, title: str,
             xp: int, xp_floor: int, xp_next: int, achievements: list[tuple[str, str]],
             mini: list[tuple[str, str]], avatar_uri: str | None, w: int = 500, h: int = 380) -> str:
    out = [card(w, h)]
    defs = '<clipPath id="av"><circle cx="72" cy="78" r="38"/></clipPath>'
    if avatar_uri:
        out.append(
            f'<image href="{avatar_uri}" x="34" y="40" width="76" height="76" clip-path="url(#av)"/>'
        )
    else:
        out.append(f'<circle cx="72" cy="78" r="38" fill="#1f2937"/>'
                   f'<text x="72" y="90" text-anchor="middle" font-size="32" font-weight="800" fill="{CYAN}">'
                   f'{esc(name[:1].upper())}</text>')
    out.append(
        f'<circle cx="72" cy="78" r="41" fill="none" stroke="url(#g-accent)" stroke-width="3">'
        f'<animate attributeName="stroke-opacity" values="1;0.35;1" dur="3s" repeatCount="indefinite"/></circle>'
    )
    out.append(f'<text x="128" y="68" font-size="26" font-weight="800" fill="{TEXT}">{esc(name)}</text>')
    out.append(f'<text class="m" x="128" y="90" font-size="14" fill="{MUTE}">@{esc(handle)} · {esc(location)}</text>')
    out.append(
        f'<rect x="128" y="100" width="{44+len(title)*8.6:.0f}" height="22" rx="11" fill="{VIOLET}" fill-opacity="0.25" '
        f'stroke="{VIOLET}"/><text x="{128+13}" y="115.5" font-size="12.5" font-weight="700" fill="#cdb8ff">'
        f"LVL {level} · {esc(title.upper())}</text>"
    )
    # XP bar
    span = max(xp_next - xp_floor, 1)
    pct = min(max((xp - xp_floor) / span, 0), 1)
    bw = 432 * pct
    out.append(f'<text class="m" x="34" y="156" font-size="12" fill="{MUTE}">XP {fmt(xp)} / {fmt(xp_next)}</text>')
    out.append(f'<text class="m" x="466" y="156" font-size="12" text-anchor="end" fill="{MUTE}">{pct*100:.0f}% to LVL {level+1}</text>')
    out.append(f'<rect x="34" y="165" width="432" height="12" rx="6" fill="#21262d"/>')
    out.append(
        f'<rect x="34" y="165" width="{bw:.1f}" height="12" rx="6" fill="url(#g-accent)" filter="url(#glow)">'
        f'{delayed("width", 0, f"{bw:.1f}", 0.2, 1.4)}</rect>'
    )
    # mini stats
    cell = 432 / max(len(mini), 1)
    for i, (val, lab) in enumerate(mini):
        cx = 34 + i * cell
        out.append(f'<text x="{cx:.0f}" y="217" font-size="26" font-weight="800" fill="{TEXT}">{esc(val)}</text>')
        out.append(f'<text class="m" x="{cx:.0f}" y="236" font-size="11.5" fill="{MUTE}">{esc(lab)}</text>')
    # achievements
    out.append(f'<text class="m" x="34" y="268" font-size="12" fill="{MUTE}">ACHIEVEMENTS UNLOCKED</text>')
    x, y = 34, 280
    for emoji, label in achievements[:10]:
        pw = 30 + len(label) * 6.6
        if x + pw > 468:
            x, y = 34, y + 28
        if y > h - 30:
            break
        out.append(
            f'<rect x="{x:.0f}" y="{y}" width="{pw:.0f}" height="22" rx="11" fill="#21262d" stroke="{BORDER}"/>'
            f'<text x="{x+9:.0f}" y="{y+15}" font-size="12">{emoji}</text>'
            f'<text x="{x+28:.0f}" y="{y+15}" font-size="11.5" fill="{TEXT}">{esc(label)}</text>'
        )
        x += pw + 8
    return svg(w, h, "".join(out), defs, title=f"{name} developer card")


# --------------------------------------------------------------------------- #
# 4. SKILL RADAR
# --------------------------------------------------------------------------- #
def radar(axes: list[tuple[str, int]], counts: dict[str, int], w: int = 500, h: int = 380) -> str:
    cx, cy, R = w / 2, 214, 108
    n = len(axes)

    def pt(i, frac):
        a = -math.pi / 2 + i * 2 * math.pi / n
        return cx + R * frac * math.cos(a), cy + R * frac * math.sin(a)

    out = [card(w, h)]
    out.append(f'<text x="30" y="40" font-size="18" font-weight="800" fill="{TEXT}">Skill Radar</text>')
    out.append(f'<text class="m" x="30" y="58" font-size="12" fill="{MUTE}">computed from my repositories</text>')
    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{pt(i, ring)[0]:.1f},{pt(i, ring)[1]:.1f}" for i in range(n))
        out.append(f'<polygon points="{pts}" fill="none" stroke="{BORDER}" stroke-width="1"/>')
    for i in range(n):
        x, y = pt(i, 1)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{BORDER}"/>')
    poly = " ".join(f"{pt(i, v/100)[0]-cx:.1f},{pt(i, v/100)[1]-cy:.1f}" for i, (_, v) in enumerate(axes))
    dots = "".join(
        f'<circle cx="{pt(i, v/100)[0]-cx:.1f}" cy="{pt(i, v/100)[1]-cy:.1f}" r="4.5" fill="{CYAN}" stroke="#0d1117" stroke-width="2"/>'
        for i, (_, v) in enumerate(axes)
    )
    out.append(
        f'<g transform="translate({cx},{cy})"><g>'
        f'<animateTransform attributeName="transform" type="scale" values="0.02;0.02;1" keyTimes="0;0.2;1" dur="1.6s" fill="freeze"/>'
        f'<polygon points="{poly}" fill="{CYAN}" fill-opacity="0.22" stroke="url(#g-accent)" stroke-width="3" stroke-linejoin="round" filter="url(#glow)"/>'
        f"{dots}</g></g>"
    )
    for i, (label, v) in enumerate(axes):
        x, y = pt(i, 1.0)
        a = -math.pi / 2 + i * 2 * math.pi / n
        lx, ly = cx + (R + 24) * math.cos(a), cy + (R + 24) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        out.append(
            f'<text x="{lx:.1f}" y="{ly-1:.1f}" text-anchor="{anchor}" font-size="13" font-weight="700" fill="{TEXT}">{esc(label)}</text>'
            f'<text class="m" x="{lx:.1f}" y="{ly+14:.1f}" text-anchor="{anchor}" font-size="11" fill="{MUTE}">{counts.get(label, 0)} repos</text>'
        )
    return svg(w, h, "".join(out), title="Skill radar")


# --------------------------------------------------------------------------- #
# 5. STAT TILES
# --------------------------------------------------------------------------- #
def tiles(title: str, subtitle: str, items: list[tuple[str, str, str]], w: int = 500, h: int = 380) -> str:
    out = [card(w, h)]
    out.append(f'<text x="30" y="40" font-size="18" font-weight="800" fill="{TEXT}">{esc(title)}</text>')
    out.append(f'<text class="m" x="30" y="58" font-size="12" fill="{MUTE}">{esc(subtitle)}</text>')
    tw, th, gap = 205, 130, 18
    for i, (icon, value, label) in enumerate(items[:4]):
        col, row = i % 2, i // 2
        x, y = 30 + col * (tw + gap), 80 + row * (th + gap)
        grad = ["g-accent", "g-warm", "g-accent", "g-warm"][i % 4]
        out.append(
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="12" fill="#0d1117" stroke="{BORDER}"/>'
            f'<text x="{x+16}" y="{y+38}" font-size="24">{icon}</text>'
            f'<text x="{x+16}" y="{y+86}" font-size="42" font-weight="800" fill="url(#{grad})">{esc(value)}'
            f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;0.3;1" dur="1s" fill="freeze"/></text>'
            f'<text class="m" x="{x+16}" y="{y+112}" font-size="12" fill="{MUTE}">{esc(label)}</text>'
        )
    return svg(w, h, "".join(out), title=title)


# --------------------------------------------------------------------------- #
# 6. LANGUAGE DONUT
# --------------------------------------------------------------------------- #
def donut(items: list[tuple[str, float, int]], total_repos: int, w: int = 500, h: int = 380) -> str:
    out = [card(w, h)]
    out.append(f'<text x="30" y="40" font-size="18" font-weight="800" fill="{TEXT}">Language Mix</text>')
    out.append(f'<text class="m" x="30" y="58" font-size="12" fill="{MUTE}">primary language of my own repos</text>')
    cx, cy, r, sw = 130, 224, 70, 28
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#21262d" stroke-width="{sw}"/>')
    circ = 2 * math.pi * r
    offset = 0.0
    for i, (lang, pct, n) in enumerate(items):
        col = PALETTE[i % len(PALETTE)]
        seg = max(pct / 100 * circ - 3, 1)
        d = 0.15 * i
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" '
            f'stroke-dasharray="{seg:.2f} {circ-seg:.2f}" stroke-dashoffset="{-offset/100*circ:.2f}" '
            f'transform="rotate(-90 {cx} {cy})">'
            f'<animate attributeName="stroke-dasharray" values="0 {circ:.2f};0 {circ:.2f};{seg:.2f} {circ-seg:.2f}" '
            f'keyTimes="0;{d/(d+1.0):.3f};1" dur="{d+1.0:.2f}s" fill="freeze"/></circle>'
        )
        offset += pct
    out.append(f'<text x="{cx}" y="{cy+6}" text-anchor="middle" font-size="30" font-weight="800" fill="{TEXT}">{total_repos}</text>')
    out.append(f'<text class="m" x="{cx}" y="{cy+24}" text-anchor="middle" font-size="11" fill="{MUTE}">own repos</text>')
    y = 96
    for i, (lang, pct, n) in enumerate(items):
        col = PALETTE[i % len(PALETTE)]
        out.append(
            f'<rect x="250" y="{y}" width="12" height="12" rx="3" fill="{col}"/>'
            f'<text x="272" y="{y+11}" font-size="14" font-weight="600" fill="{TEXT}">{esc(lang)}</text>'
            f'<text class="m" x="470" y="{y+11}" text-anchor="end" font-size="13" fill="{MUTE}">{pct:.1f}%</text>'
            f'<rect x="272" y="{y+19}" width="198" height="5" rx="2.5" fill="#21262d"/>'
            f'<rect x="272" y="{y+19}" width="{198*pct/100:.1f}" height="5" rx="2.5" fill="{col}">'
            f'{delayed("width", 0, f"{198*pct/100:.1f}", 0.2 + 0.1*i, 1.0)}</rect>'
        )
        y += 38
    return svg(w, h, "".join(out), title="Language mix")


# --------------------------------------------------------------------------- #
# 7. PULSE (area chart)
# --------------------------------------------------------------------------- #
def pulse(title: str, subtitle: str, values: list[float], labels: list[tuple[int, str]],
          peak_note: str = "", w: int = 1000, h: int = 280) -> str:
    out = [card(w, h)]
    out.append(f'<text x="32" y="42" font-size="20" font-weight="800" fill="{TEXT}">{esc(title)}</text>')
    out.append(f'<text class="m" x="32" y="62" font-size="12.5" fill="{MUTE}">{esc(subtitle)}</text>')
    if peak_note:
        out.append(f'<text class="m" x="{w-32}" y="42" text-anchor="end" font-size="13" fill="{GOLD}">{esc(peak_note)}</text>')
    x0, x1, ytop, ybase = 40, w - 40, 92, h - 48
    n = max(len(values), 2)
    vmax = max(max(values or [1]), 1)
    for k in range(4):
        gy = ytop + (ybase - ytop) * k / 3
        out.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{BORDER}" stroke-dasharray="2 6"/>')
    pts = [(x0 + (x1 - x0) * i / (n - 1), ybase - (ybase - ytop) * (v / vmax)) for i, v in enumerate(values)]
    if len(pts) < 2:
        pts = [(x0, ybase), (x1, ybase)]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        mx = (xa + xb) / 2
        d += f" C{mx:.1f},{ya:.1f} {mx:.1f},{yb:.1f} {xb:.1f},{yb:.1f}"
    area = d + f" L{pts[-1][0]:.1f},{ybase} L{pts[0][0]:.1f},{ybase} Z"
    defs = (
        f'<linearGradient id="pl-fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0.45"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>'
    )
    out.append(
        f'<path d="{area}" fill="url(#pl-fill)"><animate attributeName="opacity" values="0;0;1" keyTimes="0;0.4;1" dur="2s" fill="freeze"/></path>'
    )
    out.append(
        f'<path d="{d}" fill="none" stroke="url(#g-accent)" stroke-width="3.5" stroke-linecap="round" pathLength="1" '
        f'stroke-dasharray="1" filter="url(#glow)"><animate attributeName="stroke-dashoffset" from="1" to="0" dur="2s" fill="freeze"/></path>'
    )
    imax = max(range(len(values)), key=lambda i: values[i]) if values else 0
    if values:
        px, py = pts[imax]
        out.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="{GOLD}" stroke="#0d1117" stroke-width="2.5">'
            f'<animate attributeName="r" values="6;9;6" dur="2.2s" repeatCount="indefinite"/></circle>'
        )
    for idx, lab in labels:
        lx = x0 + (x1 - x0) * idx / (n - 1)
        out.append(f'<text class="m" x="{lx:.1f}" y="{h-22}" text-anchor="middle" font-size="11.5" fill="{MUTE}">{esc(lab)}</text>')
    return svg(w, h, "".join(out), defs, title=title)


# --------------------------------------------------------------------------- #
# 8. TECH ORBIT
# --------------------------------------------------------------------------- #
def orbit(rings: list[list[str]], w: int = 1000, h: int = 470) -> str:
    cx, cy = w / 2, h / 2
    radii = [88, 158, 218]
    durs = [38, 56, 80]
    colors = [CYAN, VIOLET, PINK]
    out = [card(w, h)]
    out.append(f'<text x="32" y="44" font-size="20" font-weight="800" fill="{TEXT}">Tech Orbit</text>')
    out.append(f'<text class="m" x="32" y="64" font-size="12.5" fill="{MUTE}">the tools I orbit around, hover-free and always moving</text>')
    out.append(f'<g transform="translate({cx},{cy+8})">')
    out.append(
        f'<circle r="46" fill="#0d1117" stroke="url(#g-accent)" stroke-width="3" filter="url(#glow)"/>'
        f'<circle r="46" fill="none" stroke="{CYAN}" stroke-opacity="0.5"><animate attributeName="r" values="46;78;46" dur="4s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="0.5;0;0.5" dur="4s" repeatCount="indefinite"/></circle>'
        f'<text y="10" text-anchor="middle" font-size="30" font-weight="800" fill="{TEXT}">SN</text>'
    )
    for ri, names in enumerate(rings[:3]):
        r, dur, col = radii[ri], durs[ri], colors[ri]
        direction = 1 if ri % 2 == 0 else -1
        out.append(f'<circle r="{r}" fill="none" stroke="{col}" stroke-opacity="0.28" stroke-dasharray="4 8"/>')
        nodes = []
        for k, name in enumerate(names):
            a = 2 * math.pi * k / max(len(names), 1) + ri * 0.6
            x, y = r * math.cos(a), r * math.sin(a)
            pw = 26 + len(name) * 7.4
            nodes.append(
                f'<g transform="translate({x:.1f},{y:.1f})"><g>'
                f'<animateTransform attributeName="transform" type="rotate" from="0" to="{-360*direction}" dur="{dur}s" repeatCount="indefinite"/>'
                f'<rect x="{-pw/2:.1f}" y="-13" width="{pw:.1f}" height="26" rx="13" fill="#0d1117" stroke="{col}" stroke-width="1.6"/>'
                f'<text y="5" text-anchor="middle" font-size="12.5" font-weight="700" fill="{TEXT}">{esc(name)}</text>'
                f"</g></g>"
            )
        out.append(
            f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="{360*direction}" dur="{dur}s" repeatCount="indefinite"/>'
            + "".join(nodes) + "</g>"
        )
    out.append("</g>")
    return svg(w, h, "".join(out), title="Tech orbit")


# --------------------------------------------------------------------------- #
# 9. PROJECT CARD
# --------------------------------------------------------------------------- #
def project_card(name: str, blurb: str, tags: list[str], language: str | None, stars: int,
                 forks: int, days: int, live: bool, w: int = 490, h: int = 184) -> str:
    out = [card(w, h)]
    out.append(
        f'<path d="M26 34h9l3 4h14a3 3 0 0 1 3 3v15a3 3 0 0 1-3 3H26a3 3 0 0 1-3-3V37a3 3 0 0 1 3-3z" fill="{CYAN}" fill-opacity="0.85"/>'
    )
    out.append(f'<text class="m" x="64" y="52" font-size="17" font-weight="800" fill="{TEXT}">{esc(name if len(name) <= 30 else name[:29] + "…")}</text>')
    if live:
        out.append(
            f'<rect x="{w-92}" y="30" width="66" height="22" rx="11" fill="{GREEN}" fill-opacity="0.16" stroke="{GREEN}"/>'
            f'<circle cx="{w-78}" cy="41" r="4" fill="{GREEN}"><animate attributeName="opacity" values="1;0.2;1" dur="1.6s" repeatCount="indefinite"/></circle>'
            f'<text x="{w-69}" y="45" font-size="11.5" font-weight="700" fill="{GREEN}">LIVE</text>'
        )
    for i, ln in enumerate(wrap(blurb, 62, 2)):
        out.append(f'<text x="26" y="{84+i*19}" font-size="13.5" fill="#b6c2d0">{esc(ln)}</text>')
    x = 26
    for tg in tags[:4]:
        pw = 18 + len(tg) * 6.8
        out.append(
            f'<rect x="{x:.0f}" y="{h-62}" width="{pw:.0f}" height="22" rx="11" fill="{VIOLET}" fill-opacity="0.2" stroke="{VIOLET}" stroke-opacity="0.6"/>'
            f'<text x="{x+pw/2:.0f}" y="{h-47}" text-anchor="middle" font-size="11.5" fill="#d6c8ff">{esc(tg)}</text>'
        )
        x += pw + 7
    out.append(f'<line x1="26" y1="{h-34}" x2="{w-26}" y2="{h-34}" stroke="{BORDER}"/>')
    fx = 26
    if language:
        out.append(
            f'<circle cx="{fx+5}" cy="{h-16}" r="5" fill="{GOLD}"/>'
            f'<text class="m" x="{fx+16}" y="{h-12}" font-size="12" fill="{MUTE}">{esc(language)}</text>'
        )
        fx += 28 + len(language) * 7.2
    out.append(f'<text class="m" x="{fx:.0f}" y="{h-12}" font-size="12" fill="{MUTE}">★ {stars}   ⑂ {forks}</text>')
    out.append(f'<text class="m" x="{w-26}" y="{h-12}" text-anchor="end" font-size="12" fill="{MUTE}">updated {ago_days(days)}</text>')
    return svg(w, h, "".join(out), title=name)


# --------------------------------------------------------------------------- #
# 10. DIVIDER
# --------------------------------------------------------------------------- #
def divider(w: int = 1000, h: int = 26) -> str:
    defs = (
        f'<linearGradient id="dv" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="0.5" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>'
    )
    body = (
        f'<rect x="0" y="12" width="{w}" height="2" fill="url(#dv)" opacity="0.55"/>'
        f'<circle cy="13" r="5" fill="{CYAN}" filter="url(#glow)">'
        f'<animate attributeName="cx" values="0;{w};0" dur="9s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{w/2}" cy="13" r="3.5" fill="{PINK}"/>'
    )
    return svg(w, h, body, defs, title="divider")
