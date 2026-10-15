"""The fidelity evaluation harness (spec §10.5–10.7, §11)."""
import csv
import json

import pytest
from fastapi.testclient import TestClient

from evaluation import runner
from evaluation.dataset import load
from evaluation.demo import make_demo
from evaluation.report import compare, summarise, to_markdown
from evaluation.review import create_review_app


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    return make_demo(tmp_path_factory.mktemp("ds") / "demo")


@pytest.fixture(scope="module")
def run_dir(demo, tmp_path_factory):
    return runner.run(load(demo), tmp_path_factory.mktemp("runs"), "r1", ["white", "marble"], log=lambda *_: None)


def lenient_gate(tmp_path, **over):
    g = {"min_items": 1, "min_categories": 1, "required_tags": [], "require_all_reviewed": True,
         "max_critical": 0, "max_major_rate": 0.5, "max_minor_rate": 1.0, "min_usable_rate": 0.5,
         "max_technical_failure_rate": 0.5, **over}
    path = tmp_path / "gate.toml"
    path.write_text("\n".join(f"{k} = {json.dumps(v)}" for k, v in g.items()))
    return path


def review_all(run_dir, severity_for=lambda oid: None):
    client = TestClient(create_review_app(run_dir))
    for r in json.loads((run_dir / "results.json").read_text()):
        if r["status"] != "ok":
            continue
        sev = severity_for(r["output_id"])
        body = {"usable": True, "detail_changed": sev is not None, "severity": sev,
                "change_types": ["metal"] if sev else [], "reviewer": "test"}
        assert client.post(f"/api/reviews/{r['output_id']}", json=body).status_code == 200
    return client


def test_dataset_validation_catches_mistakes(tmp_path, demo):
    ds = load(demo)
    assert not ds.errors and len(ds.items) == 5
    assert "multi_angle" in next(i for i in ds.items if i.example_id == "D005").tags
    bad = tmp_path / "bad"
    make_demo(bad)
    rows = list(csv.DictReader((bad / "items.csv").open()))
    rows[0]["category"] = "tiara"
    rows[1]["original"] = "images/missing.jpg"
    rows[2]["example_id"] = rows[0]["example_id"]
    with (bad / "items.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    errors = " ".join(load(bad).errors)
    assert "category" in errors and "not found" in errors and "duplicate" in errors


def test_rights_block_external_processing(tmp_path, demo, monkeypatch):
    ds = load(demo)
    ds.items[0].rights = "unknown"
    monkeypatch.setattr(runner, "uses_external_processing", lambda: True)
    with pytest.raises(PermissionError, match="D001"):
        runner.run(ds, tmp_path, "blocked", ["white"], log=lambda *_: None)


def test_run_records_everything(run_dir):
    results = json.loads((run_dir / "results.json").read_text())
    meta = json.loads((run_dir / "run.json").read_text())
    assert len(results) == 10 and all(r["status"] == "ok" for r in results)
    r = results[0]
    assert r["pixel_match"] >= 0.995 and r["seconds"] is not None
    assert (run_dir / "images" / r["files"]["output"]).exists() and (run_dir / "images" / r["files"]["full"]).exists()
    assert meta["providers"]["white_balance_strength"] == 0.5 and len(meta["items"]) == 5


def test_review_api_validates_and_saves(run_dir):
    c = TestClient(create_review_app(run_dir))
    assert "Fidelity review" in c.get("/").text
    oid = c.get("/api/run").json()["results"][0]["output_id"]
    assert c.post(f"/api/reviews/{oid}", json={"severity": "catastrophic"}).status_code == 422
    assert c.post("/api/reviews/nope", json={}).status_code == 404
    saved = c.post(f"/api/reviews/{oid}", json={"usable": True, "detail_changed": False, "severity": "major"}).json()
    assert saved["severity"] == "presentation_only"  # no change means presentation-only
    assert json.loads((run_dir / "reviews.json").read_text())[oid]["usable"] is True
    assert c.get("/images/../run.json").status_code == 404


def test_gate_verdicts(run_dir, tmp_path):
    (run_dir / "reviews.json").write_text("{}")
    gate = lenient_gate(tmp_path)
    assert summarise(run_dir, gate)["verdict"] == "INCOMPLETE"
    review_all(run_dir)
    s = summarise(run_dir, gate)
    assert s["verdict"] == "PASS" and s["outputs"] == 8 and s["excluded_development_outputs"] == 2
    # The real default gate fails the demo: too few examples and missing coverage
    real = summarise(run_dir)
    assert real["verdict"] == "FAIL" and "transparent_stone" not in real["tags_missing"]
    assert any("examples" in r for r in real["reasons"])
    # One critical change fails even the lenient gate
    review_all(run_dir, lambda oid: "critical" if oid == "D002__white__1" else None)
    s = summarise(run_dir, gate)
    assert s["verdict"] == "FAIL" and s["counts"]["critical"] == 1
    md = to_markdown(s)
    assert "not a guarantee" in md and "Critical | 1" in md


def test_compare_finds_regressions(run_dir, tmp_path):
    gate = lenient_gate(tmp_path)
    review_all(run_dir)
    before = summarise(run_dir, gate)
    review_all(run_dir, lambda oid: "major" if oid.startswith("D004__marble") else None)
    after = summarise(run_dir, gate)
    cmp = compare(after, before)
    assert cmp["regressions"] == [{"example": "D004 · marble", "before": "presentation_only", "after": "major"}]
    assert "Regressions" in to_markdown(after, cmp)


def test_cli_end_to_end(tmp_path):
    from evaluation.__main__ import main
    ds = tmp_path / "ds"
    assert main(["demo", str(ds)]) == 0
    assert main(["validate", str(ds)]) == 0
    assert main(["run", str(ds), "--name", "cli", "--presets", "white", "--out", str(tmp_path / "runs")]) == 0
    assert main(["run", str(ds), "--name", "cli", "--presets", "white", "--out", str(tmp_path / "runs")]) == 1  # name taken
    assert main(["report", str(tmp_path / "runs" / "cli")]) == 1  # default gate: FAIL
    assert (tmp_path / "runs" / "cli" / "report.md").exists()
