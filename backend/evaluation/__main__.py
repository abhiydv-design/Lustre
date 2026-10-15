"""Fidelity evaluation harness (spec §10.5–10.7, §11).

    python -m evaluation init     datasets/v1                 create an empty dataset to fill in
    python -m evaluation demo     datasets/demo               a synthetic dataset to learn the tool
    python -m evaluation validate datasets/v1                 check paths, labels and image rights
    python -m evaluation run      datasets/v1 --name baseline --presets white,marble --repeats 2
    python -m evaluation review   runs/baseline               review in the browser
    python -m evaluation report   runs/baseline [--compare runs/older] [--gate gate.toml]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m evaluation", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "demo", "validate"):
        sub.add_parser(name).add_argument("dataset", type=Path)
    r = sub.add_parser("run")
    r.add_argument("dataset", type=Path)
    r.add_argument("--name", required=True, help="unique run name, e.g. baseline-2026-10")
    r.add_argument("--presets", default="white,marble")
    r.add_argument("--aspect", default="1:1")
    r.add_argument("--repeats", type=int, default=1, help="generations per example and preset")
    r.add_argument("--out", type=Path, default=HERE / "runs")
    r.add_argument("--allow-unverified-rights", action="store_true")
    v = sub.add_parser("review")
    v.add_argument("run_dir", type=Path)
    v.add_argument("--port", type=int, default=8765)
    p = sub.add_parser("report")
    p.add_argument("run_dir", type=Path)
    p.add_argument("--compare", type=Path)
    p.add_argument("--gate", type=Path, default=HERE / "gate.toml")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        from .dataset import write_template
        print(f"Created {write_template(a.dataset)}. Put photos in {a.dataset / 'images'}; see COLUMNS.md.")
    elif a.cmd == "demo":
        from .demo import make_demo
        print(f"Demo dataset in {make_demo(a.dataset)} (synthetic drawings, for learning the tool only).")
    elif a.cmd == "validate":
        from .dataset import load
        ds = load(a.dataset)
        for w in ds.warnings:
            print("warning:", w)
        for e in ds.errors:
            print("ERROR:", e)
        print(f"{len(ds.items)} examples, {len(ds.errors)} errors, {len(ds.warnings)} warnings")
        return 1 if ds.errors else 0
    elif a.cmd == "run":
        from .dataset import load
        from .runner import run
        ds = load(a.dataset)
        try:
            out = run(ds, a.out, a.name, [p.strip() for p in a.presets.split(",") if p.strip()], a.aspect,
                      a.repeats, a.allow_unverified_rights)
        except (ValueError, PermissionError, FileExistsError) as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"Done: {out}\nNext: python -m evaluation review {out}")
    elif a.cmd == "review":
        import uvicorn
        from .review import create_review_app
        print(f"Open http://127.0.0.1:{a.port} (Ctrl+C to stop). Reviews save to {a.run_dir / 'reviews.json'}")
        uvicorn.run(create_review_app(a.run_dir), host="127.0.0.1", port=a.port, log_level="warning")
    elif a.cmd == "report":
        from .report import compare, summarise, to_markdown
        s = summarise(a.run_dir, a.gate)
        cmp = compare(s, summarise(a.compare, a.gate)) if a.compare else None
        md = to_markdown(s, cmp)
        (a.run_dir / "report.md").write_text(md, encoding="utf-8")
        (a.run_dir / "summary.json").write_text(json.dumps({**s, "comparison": cmp}, indent=2), encoding="utf-8")
        print(md)
        return {"PASS": 0, "INCOMPLETE": 2}.get(s["verdict"], 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
