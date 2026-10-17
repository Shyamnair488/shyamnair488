#!/usr/bin/env python3
"""
Profile builder.

Reads  : profile.config.json + the public GitHub REST/GraphQL API
Writes : assets/*.svg (self-hosted visuals) and the marker sections of README.md

Standard library only, so the workflow needs no `pip install`.
Run locally:  GITHUB_TOKEN=xxxx python .github/scripts/build_profile.py
"""

from __future__ import annotations

import base64
import collections
import datetime as dt
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_cards as sc  # noqa: E402

ROOT = Path(os.environ.get("PROFILE_ROOT", ".")).resolve()
CONFIG = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
README = ROOT / "README.md"
ASSETS = ROOT / "assets"

USER = os.environ.get("GH_USER") or CONFIG["handle"]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
NOW = dt.datetime.now(dt.timezone.utc)

HIDDEN = {USER.lower()} | {r.lower() for r in CONFIG.get("hidden_repos", [])}
changed_files: list[str] = []


# --------------------------------------------------------------------------- #
# GitHub access
# --------------------------------------------------------------------------- #
def _request(url: str, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-builder")
    if data:
        req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def api(path: str, params: dict | None = None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    return json.loads(_request(url))


def graphql(query: str, variables: dict):
    if not TOKEN:
        return None
    body = json.dumps({"query": query, "variables": variables}).encode()
    out = json.loads(_request(f"{API}/graphql", body))
    return None if out.get("errors") else out.get("data")


def fetch_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos",
                    {"per_page": 100, "page": page, "sort": "pushed", "type": "owner"})
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos if r["name"].lower() not in HIDDEN]


def fetch_calendar() -> list[dict] | None:
    """Daily contribution counts for the last year (needs a token)."""
    try:
        data = graphql(
            """query($login:String!){user(login:$login){contributionsCollection{
                 contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}""",
            {"login": USER},
        )
        weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        return [d for w in weeks for d in w["contributionDays"]]
    except Exception as exc:  # network, auth or schema problems must never break the build
        print(f"::notice::Contribution calendar unavailable ({exc}); using repo cadence instead.")
        return None


def fetch_avatar(user: dict) -> str | None:
    try:
        raw = _request(user["avatar_url"] + ("&" if "?" in user["avatar_url"] else "?") + "s=160")
        mime = "image/jpeg" if raw[:2] == b"\xff\xd8" else "image/png"
        return f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    except Exception as exc:
        print(f"::notice::Avatar unavailable ({exc}); using initial.")
        return None


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def parse_ts(v: str) -> dt.datetime:
    return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))


def days_since(v: str) -> int:
    return max((NOW - parse_ts(v)).days, 0)


def ago(v: str) -> str:
    return sc.ago_days(days_since(v))


def clean(text: str | None, limit: int = 90, name: str = "") -> str:
    if text and text.strip().lower() == name.lower():
        return ""
    text = (text or "").replace("|", "/").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")
    changed_files.append(str(path.relative_to(ROOT)))


# --------------------------------------------------------------------------- #
# Insights
# --------------------------------------------------------------------------- #
DOMAINS: dict[str, dict] = {
    "Web": {
        "lang": {"HTML", "CSS", "JavaScript", "TypeScript", "Vue"},
        "kw": ["web", "site", "react", "next", "nextjs", "portfolio", "landing", "tailwind", "carousel",
               "commerce", "academy", "gallery", "weather", "todo", "housie", "email", "lwc", "ui"],
    },
    "Backend": {
        "lang": {"Java"},
        "kw": ["server", "backend", "api", "flask", "express", "node", "database", "schema", "java"],
    },
    "Cloud": {
        "lang": {"Shell"},
        "kw": ["aws", "docker", "ecr", "compose", "autoscal", "devops", "deploy", "kube", "terraform"],
    },
    "IoT": {
        "lang": set(),
        "kw": ["esp", "esp8266", "esp32", "arduino", "iot", "raspberry", "automation", "wifi", "sensor", "repeater"],
    },
    "AI/ML": {
        "lang": {"Jupyter Notebook"},
        "kw": ["ml", "ai", "cv", "model", "learning", "vision", "speech", "llm", "detection", "tensorflow",
               "tflite", "nlp", "mnist", "recommend", "ocular", "agro", "friday", "robo", "transformers"],
    },
    "Data": {
        "lang": {"R"},
        "kw": ["data", "practical", "science", "analysis", "preprocessing", "statistics", "internship"],
    },
}
AXES = list(DOMAINS)


def tokens(repo: dict) -> list[str]:
    text = f'{repo["name"]} {repo.get("description") or ""}'.lower()
    return re.findall(r"[a-z0-9]+", text)


def matches(repo: dict, domain: str) -> bool:
    spec = DOMAINS[domain]
    if repo.get("language") in spec["lang"]:
        return True
    toks = tokens(repo)
    for kw in spec["kw"]:
        if len(kw) <= 3:
            if kw in toks:
                return True
        elif any(t.startswith(kw) for t in toks):
            return True
    return False


def domain_counts(own: list[dict]) -> dict[str, int]:
    return {d: sum(1 for r in own if matches(r, d)) for d in AXES}


def level_info(xp: int) -> tuple[int, int, int]:
    level = int(math.sqrt(xp / 12)) + 1
    return level, 12 * (level - 1) ** 2, 12 * level**2


def title_for(level: int) -> str:
    for threshold, name in reversed([(1, "Newbie"), (5, "Apprentice"), (8, "Builder"), (12, "Engineer"),
                                     (18, "Architect"), (25, "Wizard"), (35, "Legend")]):
        if level >= threshold:
            return name
    return "Newbie"


def streaks(days: list[dict]) -> tuple[int, int]:
    counts = [d["contributionCount"] for d in sorted(days, key=lambda d: d["date"])]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    idx = len(counts) - 1
    if idx >= 0 and counts[idx] == 0:  # today may not have contributions yet
        idx -= 1
    current = 0
    while idx >= 0 and counts[idx]:
        current += 1
        idx -= 1
    return current, longest


def achievements(own: list[dict], repos: list[dict], dom: dict[str, int], langs: int,
                 live: int, streak: int | None) -> list[tuple[str, str]]:
    forks = sum(1 for r in repos if r["fork"])
    recent = any(days_since(r["pushed_at"]) <= 14 for r in repos)
    rules = [
        ("🌐", "Polyglot", langs >= 5),
        ("📦", "Prolific", len(own) >= 50),
        ("☁️", "Cloud Native", dom["Cloud"] >= 3),
        ("🔌", "Hardware Hacker", dom["IoT"] >= 3),
        ("🧠", "ML Practitioner", dom["AI/ML"] >= 5),
        ("🚀", "Shipper", live >= 3),
        ("🔥", "On Fire", recent),
        ("⚡", "7-Day Streak", bool(streak and streak >= 7)),
        ("🍴", "Open-Source Explorer", forks >= 15),
    ]
    out = [(e, t) for e, t, ok in rules if ok]
    out += [("🏅", a) for a in CONFIG.get("github_achievements", [])]
    return out


# --------------------------------------------------------------------------- #
# Markdown sections
# --------------------------------------------------------------------------- #
def md_featured(by_name: dict[str, dict]) -> str:
    cells = []
    for i, item in enumerate(CONFIG["featured"]):
        repo = by_name.get(item["repo"].lower())
        href = repo["html_url"] if repo else f"https://github.com/{USER}/{item['repo']}"
        cells.append(f'<a href="{href}"><img src="assets/project-{i+1}.svg" width="49%" alt="{item["repo"]}"/></a>')
    return '<div align="center">\n\n' + "\n".join(cells) + "\n\n</div>"


def md_live_sites() -> str:
    rows = ["| | Project | Link |", "|:-:|:--|:--|"]
    for s in CONFIG["live_sites"]:
        host = re.sub(r"^https?://", "", s["url"]).rstrip("/")
        rows.append(f'| {s["emoji"]} | **{s["name"]}** | [{host}]({s["url"]}) |')
    return "\n".join(rows)


def md_recent(own: list[dict]) -> str:
    rows = ["| 📦 Repository | 💬 About | 🧪 Language | ⭐ | 🕒 Last push |", "|:--|:--|:--:|:--:|:--:|"]
    for r in own[:6]:
        about = clean(r["description"], 90, r["name"]) or "—"
        if r.get("homepage"):
            about += f' · [🔴 live]({r["homepage"]})'
        rows.append(f'| [**{r["name"]}**]({r["html_url"]}) | {about} | {r["language"] or "—"} '
                    f'| {r["stargazers_count"]} | {ago(r["pushed_at"])} |')
    return "\n".join(rows)


def describe_event(ev: dict) -> str | None:
    repo = ev["repo"]["name"]
    link = f"[{repo}](https://github.com/{repo})"
    p, kind = ev.get("payload", {}), ev["type"]
    if kind == "PushEvent":
        n = p.get("size") or len(p.get("commits") or [])
        return f"⬆️ Pushed {n} commit{'s' if n != 1 else ''} to {link}" if n else f"⬆️ Pushed to {link}"
    if kind == "CreateEvent":
        ref = p.get("ref_type", "item")
        return f"🆕 Created repository {link}" if ref == "repository" else f"🆕 Created {ref} in {link}"
    if kind == "WatchEvent":
        return f"⭐ Starred {link}"
    if kind == "ForkEvent":
        return f"🍴 Forked {link}"
    if kind == "PullRequestEvent":
        pr = p.get("pull_request", {})
        verb = "Merged" if pr.get("merged") else p.get("action", "updated").capitalize()
        return f"🔀 {verb} a pull request in {link}"
    if kind == "IssuesEvent":
        return f"🐞 {p.get('action', 'updated').capitalize()} an issue in {link}"
    if kind == "IssueCommentEvent":
        return f"💬 Commented on an issue in {link}"
    if kind == "ReleaseEvent":
        return f"🚀 Published a release in {link}"
    if kind == "PublicEvent":
        return f"🌍 Open-sourced {link}"
    return None


def md_activity(events: list[dict]) -> str:
    items: list[str] = []
    for ev in events:
        text = describe_event(ev)
        if not text:
            continue
        line = f"- {text} · <sub>{ago(ev['created_at'])}</sub>"
        if items and items[-1].split(" · <sub>")[0] == line.split(" · <sub>")[0]:
            continue
        items.append(line)
        if len(items) >= 8:
            break
    return "\n".join(items) if items else "_No recent public activity._"


def md_spotlight(own: list[dict]) -> str:
    pool = [r for r in own if r.get("description") or r.get("homepage") or r["language"]] or own
    if not pool:
        return ""
    r = pool[NOW.date().toordinal() % len(pool)]
    quotes = CONFIG.get("quotes") or [""]
    q = quotes[NOW.date().toordinal() % len(quotes)]
    desc = clean(r["description"], 120, r["name"])
    bits = [b for b in [r["language"], f'★ {r["stargazers_count"]}', f'updated {ago(r["pushed_at"])}'] if b]
    return (
        f'> 🎯 **Repo of the day:** [{r["name"]}]({r["html_url"]})'
        f'{" — " + desc if desc else ""}  \n> <sub>{" · ".join(bits)}</sub>\n>\n'
        f"> 💭 *{q}*"
    )


def md_all_repos(repos: list[dict]) -> str:
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for r in repos:
        groups[r["language"] or "Other"].append(r)
    blocks = []
    for lang, items in sorted(groups.items(), key=lambda kv: (kv[0] == "Other", -len(kv[1]), kv[0])):
        rows = []
        for r in items:
            desc = clean(r["description"], 80, r["name"])
            live = f' · [🔴 live]({r["homepage"]})' if r.get("homepage") and "vercel.app" in r["homepage"] else ""
            rows.append(f'- [{r["name"]}]({r["html_url"]}){" 🍴" if r["fork"] else ""}'
                        f'{" — " + desc if desc else ""}{live}')
        blocks.append(f"<details>\n<summary><b>{lang}</b> &nbsp;<sub>({len(items)})</sub></summary>\n\n"
                      + "\n".join(rows) + "\n\n</details>")
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------- #
# README plumbing
# --------------------------------------------------------------------------- #
def section_re(name: str) -> re.Pattern:
    n = re.escape(name)
    return re.compile(rf"(<!--START_SECTION:{n}-->)(.*?)(<!--END_SECTION:{n}-->)", re.S)


def put(text: str, name: str, body: str) -> str:
    pat = section_re(name)
    if not pat.search(text):
        print(f"::warning::Marker '{name}' not found in README.md")
        return text
    return pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text, count=1)


def strip_stamp(text: str) -> str:
    return section_re("updated").sub("", text)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    changed_files.clear()
    user = api(f"/users/{USER}")
    repos = fetch_repos()
    own = [r for r in repos if not r["fork"]]
    by_name = {r["name"].lower(): r for r in repos}
    try:
        events = api(f"/users/{USER}/events/public", {"per_page": 50})
    except urllib.error.HTTPError:
        events = []
    calendar = fetch_calendar()
    avatar = fetch_avatar(user)

    # ---- numbers ----------------------------------------------------------
    stars = sum(r["stargazers_count"] for r in own)
    followers = user.get("followers", 0)
    lang_counts = collections.Counter(r["language"] for r in own if r["language"])
    live_sites = [r for r in own if r.get("homepage")]
    dom = domain_counts(own)
    cur_streak = longest_streak = total_contrib = None
    if calendar:
        cur_streak, longest_streak = streaks(calendar)
        total_contrib = sum(d["contributionCount"] for d in calendar)

    xp = (len(own) * 10 + stars * 5 + followers * 8 + len(lang_counts) * 3 + len(live_sites) * 10
          + (total_contrib or 0) // 10)
    level, xp_floor, xp_next = level_info(xp)
    title = title_for(level)
    achv = achievements(own, repos, dom, len(lang_counts), len(live_sites), cur_streak)
    since = parse_ts(user["created_at"]).year if user.get("created_at") else "—"
    years = max(NOW.year - since, 0) if isinstance(since, int) else 0
    last = own[0] if own else None

    # ---- hero & divider ---------------------------------------------------
    write_if_changed(ASSETS / "hero.svg", sc.hero(CONFIG["name"], CONFIG["subtitle"], CONFIG["roles"]))
    write_if_changed(ASSETS / "divider.svg", sc.divider())

    # ---- terminal ---------------------------------------------------------
    top_domains = sorted(dom.items(), key=lambda kv: -kv[1])[:3]
    rows = [
        ("name", CONFIG["name"]),
        ("location", CONFIG["location"]),
        ("role", "Full Stack Developer"),
        ("github", f"since {since} · {followers} followers"),
        ("repos", f'{user.get("public_repos", len(repos))} public · {len(own)} original · {len(repos) - len(own)} forks'),
        ("top lang", ", ".join(l for l, _ in lang_counts.most_common(3)) or "—"),
        ("focus", " · ".join(f"{d} ({n})" for d, n in top_domains)),
        ("live sites", f"{len(live_sites)} deployed"),
        ("last push", f'{last["name"]} · {ago(last["pushed_at"])}' if last else "—"),
        ("level", f"LVL {level} {title} · {xp:,} XP"),
        ("status", "open to internships & freelance"),
    ]
    if cur_streak is not None:
        rows.insert(9, ("streak", f"{cur_streak} days current · {longest_streak} longest"))
    write_if_changed(ASSETS / "terminal.svg", sc.terminal(USER, rows))

    # ---- dev card & radar -------------------------------------------------
    mini = [(str(len(own)), "original repos"), (str(stars), "stars earned"),
            (str(followers), "followers"), (f"{years}y", "on GitHub")]
    write_if_changed(ASSETS / "dev-card.svg", sc.dev_card(
        CONFIG["name"], USER, CONFIG["location"], level, title, xp, xp_floor, xp_next, achv, mini, avatar))
    axes = [(d, round(100 * (1 - math.exp(-dom[d] / 5)))) for d in AXES]
    write_if_changed(ASSETS / "radar.svg", sc.radar(axes, dom))

    # ---- stat tiles & languages ------------------------------------------
    if calendar:
        tile_items = [("🔥", f"{cur_streak}", "current streak (days)"),
                      ("🏆", f"{longest_streak}", "longest streak (days)"),
                      ("⚡", sc.fmt(total_contrib), "contributions · 12 months"),
                      ("⭐", str(stars), "stars earned")]
        tile_sub = "from my real contribution calendar"
    else:
        tile_items = [("📦", str(user.get("public_repos", len(repos))), "public repositories"),
                      ("🛠️", str(len(own)), "original projects"),
                      ("⭐", str(stars), "stars earned"),
                      ("👥", str(followers), "followers")]
        tile_sub = "live numbers from the GitHub API"
    write_if_changed(ASSETS / "stats.svg", sc.tiles("Live Stats", tile_sub, tile_items))

    total_lang = sum(lang_counts.values()) or 1
    lang_items = [(l, n / total_lang * 100, n) for l, n in lang_counts.most_common(6)]
    write_if_changed(ASSETS / "languages.svg", sc.donut(lang_items, len(own)))

    # ---- pulse ------------------------------------------------------------
    if calendar:
        days = sorted(calendar, key=lambda d: d["date"])
        weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
        values = [sum(d["contributionCount"] for d in w) for w in weeks]
        labels, prev = [], None
        for i, w in enumerate(weeks):
            month = w[0]["date"][5:7]
            if month != prev:
                labels.append((i, dt.date.fromisoformat(w[0]["date"]).strftime("%b")))
                prev = month
        pulse_svg = sc.pulse("Contribution Pulse", f"{total_contrib:,} contributions in the last 12 months · weekly totals",
                             values, labels, f"peak week: {max(values)}")
    else:
        months = [(NOW.replace(day=1) - dt.timedelta(days=30 * k)) for k in range(17, -1, -1)]
        keys = [(m.year, m.month) for m in months]
        created = collections.Counter((parse_ts(r["created_at"]).year, parse_ts(r["created_at"]).month) for r in own)
        values = [created.get(k, 0) for k in keys]
        labels = [(i, dt.date(k[0], k[1], 1).strftime("%b")) for i, k in enumerate(keys) if i % 2 == 0]
        pulse_svg = sc.pulse("Build Cadence", "new repositories created per month · last 18 months",
                             values, labels, f"best month: {max(values)} repos")
    write_if_changed(ASSETS / "pulse.svg", pulse_svg)

    # ---- orbit ------------------------------------------------------------
    write_if_changed(ASSETS / "orbit.svg", sc.orbit(CONFIG["orbit"]))

    # ---- featured project cards -------------------------------------------
    for i, item in enumerate(CONFIG["featured"]):
        r = by_name.get(item["repo"].lower())
        is_live = bool(item.get("live") or (r and r.get("homepage")))
        write_if_changed(ASSETS / f"project-{i+1}.svg", sc.project_card(
            item["repo"], item.get("blurb") or (r or {}).get("description") or "", item.get("tags", []),
            (r or {}).get("language"), (r or {}).get("stargazers_count", 0), (r or {}).get("forks_count", 0),
            days_since(r["pushed_at"]) if r else 0, is_live))

    # ---- README sections --------------------------------------------------
    old = README.read_text(encoding="utf-8")
    new = old
    for name, body in [
        ("featured", md_featured(by_name)),
        ("live-sites", md_live_sites()),
        ("recent-repos", md_recent(own)),
        ("activity", md_activity(events)),
        ("spotlight", md_spotlight(own)),
        ("all-repos", md_all_repos(repos)),
    ]:
        new = put(new, name, body)

    body_changed = strip_stamp(new) != strip_stamp(old)
    if body_changed or changed_files:
        stamp = NOW.strftime("%d %b %Y, %H:%M UTC")
        new = put(new, "updated", f"<sub>🤖 Auto-generated by GitHub Actions · last refreshed <b>{stamp}</b></sub>")
        README.write_text(new, encoding="utf-8")
        changed_files.append("README.md")
        print("Updated:", ", ".join(changed_files))
    else:
        print("Everything already up to date.")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Profile build\n- Level **{level} {title}** ({xp:,} XP)\n"
                     f"- Repos: {len(repos)} ({len(own)} original) · Stars: {stars}\n"
                     f"- Contribution calendar: {'yes' if calendar else 'no (fallback used)'}\n"
                     f"- Files changed: {len(changed_files)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
