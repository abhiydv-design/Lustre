"""Summarise a reviewed run and judge it against the launch gate (§10.6, §10.7)."""
from __future__ import annotations

import json
import statistics
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

LEVEL = {"presentation_only": 0, "minor": 1, "major": 2, "critical": 3, "technical_failure": 4}
LABEL = {"presentation_only": "Presentation only", "minor": "Minor", "major": "Major", "critical": "Critical",
         "technical_failure": "Technical failure", "unreviewed": "Not reviewed"}
DEFAULT_GATE = Path(__file__).parent / "gate.toml"


def _load(run_dir: Path):
    read = lambda n: json.loads((run_dir / n).read_text(encoding="utf-8"))
    return read("run.json"), read("results.json"), read("reviews.json")


def _complete(r: dict | None) -> bool:
    return bool(r) and r.get("usable") is not None and r.get("detail_changed") is not None and \
        (r["detail_changed"] is False or bool(r.get("severity")))


def outcome(result: dict, review: dict | None) -> str:
    if result["status"] != "ok":
        return "technical_failure"
    if not _complete(review):
        return "unreviewed"
    return review["severity"] or "presentation_only"


def summarise(run_dir: Path, gate_path: Path = DEFAULT_GATE) -> dict:
    run_dir = Path(run_dir)
    meta, results, reviews = _load(run_dir)
    gate = tomllib.loads(Path(gate_path).read_text(encoding="utf-8"))
    items = {i["example_id"]: i for i in meta["items"]}
    ev = [r for r in results if r["split"] == "evaluation"]
    excluded = len(results) - len(ev)

    outcomes = [outcome(r, reviews.get(r["output_id"])) for r in ev]
    counts = Counter(outcomes)
    reviewed = [r for r, o in zip(ev, outcomes) if o not in ("technical_failure", "unreviewed")]
    n_rev = len(reviewed)
    usable = sum(1 for r in reviewed if reviews[r["output_id"]]["usable"])
    rate = lambda k: (counts[k] / n_rev) if n_rev else 0.0
    successes = sum(1 for r, o in zip(ev, outcomes)
                    if o in ("presentation_only", "minor") and reviews[r["output_id"]]["usable"])

    ev_items = [i for i in meta["items"] if i["split"] == "evaluation"]
    tags = set()
    for i in ev_items:
        tags.update(i["tags"])
        tags.add("single_view" if i["angles"] == 1 else "multi_angle")
    categories = {i["category"] for i in ev_items}

    by_cat = defaultdict(Counter)
    for r, o in zip(ev, outcomes):
        by_cat[r["category"]][o] += 1
    change_types = Counter(t for r in reviewed for t in reviews[r["output_id"]].get("change_types", []))
    seconds = [r["seconds"] for r in ev if r["seconds"] is not None]
    costs = [r["cost_usd"] for r in ev if r["cost_usd"] is not None]

    worst: dict[str, int] = {}  # per example+preset, the worst outcome across repeats (-1 = not reviewed)
    for r, o in zip(ev, outcomes):
        key = f"{r['example_id']}|{r['preset']}"
        worst[key] = max(worst.get(key, -1), LEVEL.get(o, -1))

    reasons, incomplete = [], []
    if len(ev_items) < gate["min_items"]:
        reasons.append(f"Only {len(ev_items)} evaluation examples; the gate needs {gate['min_items']}.")
    if len(categories) < gate["min_categories"]:
        reasons.append(f"Only {len(categories)} categories covered; the gate needs {gate['min_categories']}.")
    missing = [t for t in gate["required_tags"] if t not in tags]
    if missing:
        reasons.append("Test set doesn't cover: " + ", ".join(missing) + ".")
    if gate.get("require_all_reviewed", True) and counts["unreviewed"]:
        incomplete.append(f"{counts['unreviewed']} outputs still need a complete review.")
    if counts["critical"] > gate["max_critical"]:
        reasons.append(f"{counts['critical']} critical changes (max {gate['max_critical']}).")
    if rate("major") > gate["max_major_rate"]:
        reasons.append(f"Major-change rate {rate('major'):.1%} (max {gate['max_major_rate']:.1%}).")
    if rate("minor") > gate["max_minor_rate"]:
        reasons.append(f"Minor-change rate {rate('minor'):.1%} (max {gate['max_minor_rate']:.1%}).")
    if n_rev and usable / n_rev < gate["min_usable_rate"]:
        reasons.append(f"Usable rate {usable / n_rev:.1%} (min {gate['min_usable_rate']:.1%}).")
    tech_rate = counts["technical_failure"] / len(ev) if ev else 0.0
    if tech_rate > gate["max_technical_failure_rate"]:
        reasons.append(f"Technical failure rate {tech_rate:.1%} (max {gate['max_technical_failure_rate']:.1%}).")
    if not ev:
        reasons.append("No evaluation outputs in this run.")
    verdict = "FAIL" if reasons else ("INCOMPLETE" if incomplete else "PASS")

    return {
        "run": meta["name"], "git_commit": meta.get("git_commit"), "providers": meta["providers"],
        "presets": meta["presets"], "verdict": verdict, "reasons": reasons + incomplete,
        "outputs": len(ev), "excluded_development_outputs": excluded, "examples": len(ev_items),
        "reviewed": n_rev, "counts": dict(counts), "usable_rate": usable / n_rev if n_rev else None,
        "success_rate": successes / len(ev) if ev else None, "technical_failure_rate": tech_rate,
        "categories": sorted(categories), "tags_covered": sorted(tags), "tags_missing": missing,
        "by_category": {c: dict(v) for c, v in sorted(by_cat.items())},
        "change_types": dict(change_types.most_common()),
        "median_seconds": statistics.median(seconds) if seconds else None,
        "total_cost_usd": round(sum(costs), 4) if costs else None,
        "worst": worst,
    }


def compare(new: dict, old: dict) -> dict:
    """Per example and preset, did the worst outcome get better or worse? (§10.7 regressions)"""
    names = {v: k for k, v in LEVEL.items()}
    regressions, improvements = [], []
    for key, level in new["worst"].items():
        if key in old["worst"] and level >= 0 and old["worst"][key] >= 0 and level != old["worst"][key]:
            row = {"example": key.replace("|", " · "), "before": names[old["worst"][key]], "after": names[level]}
            (regressions if level > old["worst"][key] else improvements).append(row)
    return {"against": old["run"], "regressions": regressions, "improvements": improvements}


def _pct(x):
    return "—" if x is None else f"{x:.1%}"


def to_markdown(s: dict, cmp: dict | None = None) -> str:
    L = [f"# Fidelity evaluation: {s['run']}", "",
         f"**Verdict: {s['verdict']}**", ""]
    if s["reasons"]:
        L += [f"- {r}" for r in s["reasons"]] + [""]
    L += ["Results describe this test set only. They are evidence, not a guarantee that every future image "
          "will preserve every detail (§10.7).", "",
          "## Setup", "",
          f"- Code: `{s['git_commit'] or 'unknown'}`",
          f"- Providers: cut-out `{s['providers']['cutout']}`, scene `{s['providers']['scene']}`, upscale `{s['providers']['upscale']}`",
          f"- Presets: {', '.join(s['presets'])}",
          f"- {s['examples']} evaluation examples, {s['outputs']} outputs ({s['excluded_development_outputs']} development outputs excluded)",
          "", "## Outcomes", "",
          "| Outcome | Count |", "|---|---|"]
    for k in ("presentation_only", "minor", "major", "critical", "technical_failure", "unreviewed"):
        L.append(f"| {LABEL[k]} | {s['counts'].get(k, 0)} |")
    L += ["", f"- Successful outputs (usable, no major or critical change): **{_pct(s['success_rate'])}**",
          f"- Usable rate (of reviewed): {_pct(s['usable_rate'])}",
          f"- Technical failure rate: {_pct(s['technical_failure_rate'])}",
          f"- Median time per image: {s['median_seconds'] if s['median_seconds'] is not None else '—'} s",
          f"- Estimated provider cost: {'$' + str(s['total_cost_usd']) if s['total_cost_usd'] is not None else 'not measured (set EVAL_*_COST_USD)'}",
          "", "## By category", "", "| Category | Presentation only | Minor | Major | Critical | Tech. failure | Unreviewed |",
          "|---|---|---|---|---|---|---|"]
    for cat, c in s["by_category"].items():
        L.append(f"| {cat} | " + " | ".join(str(c.get(k, 0)) for k in
                 ("presentation_only", "minor", "major", "critical", "technical_failure", "unreviewed")) + " |")
    if s["change_types"]:
        L += ["", "## What changed most often", ""] + [f"- {k}: {v}" for k, v in s["change_types"].items()]
    L += ["", "## Coverage", "", f"- Categories: {', '.join(s['categories']) or '—'}",
          f"- Covered: {', '.join(s['tags_covered']) or '—'}",
          f"- Missing: {', '.join(s['tags_missing']) or 'none'}"]
    if cmp:
        L += ["", f"## Compared with {cmp['against']}", ""]
        if not cmp["regressions"] and not cmp["improvements"]:
            L.append("No example changed outcome.")
        for title, rows in (("Regressions", cmp["regressions"]), ("Improvements", cmp["improvements"])):
            if rows:
                L += [f"**{title}**", ""] + [f"- {r['example']}: {LABEL[r['before']]} → {LABEL[r['after']]}" for r in rows] + [""]
    return "\n".join(L) + "\n"
