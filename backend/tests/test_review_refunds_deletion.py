"""Spec §9.5 review/report, §12.3 refunds, §9.8/§14 deletion, technical-failure refunds."""
from app import storage
from app.db import Generation, new_session
from tests.conftest import generate, make_product


def test_detail_report_refunds_once_and_respects_limit(client, member):
    pid = make_product(client, member)
    ids = [generate(client, member, pid).json()["id"] for _ in range(3)]
    assert client.get("/me", headers=member).json()["credits"] == 0

    r = client.post(f"/generations/{ids[0]}/report", headers=member,
                    json={"kind": "product_detail", "category": "stones", "note": "one stone missing"})
    assert r.json()["refund"] == "refunded" and r.json()["balance"] == 1
    again = client.post(f"/generations/{ids[0]}/report", headers=member,
                        json={"kind": "product_detail", "category": "setting"})
    assert again.json()["refund"] == "duplicate"
    client.post(f"/generations/{ids[1]}/report", headers=member, json={"kind": "product_detail", "category": "metal"})
    third = client.post(f"/generations/{ids[2]}/report", headers=member, json={"kind": "product_detail", "category": "shape"})
    assert third.json()["refund"] == "under_review"  # auto limit is 2 in tests
    assert client.get("/me", headers=member).json()["credits"] == 2
    g = client.get(f"/generations/{ids[0]}", headers=member).json()
    assert g["review"] == "reported" and len(g["reports"]) == 2


def test_visual_quality_report_is_recorded_not_refunded(client, member):
    pid = make_product(client, member)
    gid = generate(client, member, pid).json()["id"]
    r = client.post(f"/generations/{gid}/report", headers=member, json={"kind": "visual_quality", "category": "shadow"})
    assert r.json()["refund"] == "not_eligible"
    bad = client.post(f"/generations/{gid}/report", headers=member, json={"kind": "visual_quality", "category": "stones"})
    assert bad.status_code == 422


def test_technical_failure_refunds_automatically(client, member, monkeypatch):
    import app.pipeline.run as run
    pid = make_product(client, member)
    monkeypatch.setattr(run, "render", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("provider down")))
    gid = generate(client, member, pid).json()["id"]
    g = client.get(f"/generations/{gid}", headers=member).json()
    assert g["status"] == "failed" and "credit has been returned" in g["message"]
    assert client.get("/me", headers=member).json()["credits"] == 3
    history = client.get("/me/credits", headers=member).json()["transactions"]
    assert [t["reason"] for t in history[:2]] == ["refund_technical", "generation"]
    monkeypatch.undo()
    assert client.get(f"/products/{pid}/quote", headers=member).json()["additional"] is False  # failed one doesn't count


def test_interrupted_generations_refunded_on_restart(client, member):
    from app.pipeline.run import recover_interrupted
    pid = make_product(client, member)
    gid = generate(client, member, pid).json()["id"]
    with new_session() as s:  # simulate a crash mid-generation
        s.get(Generation, gid).status = "running"
        s.commit()
    assert recover_interrupted() == 1
    assert client.get(f"/generations/{gid}", headers=member).json()["status"] == "failed"
    assert client.get("/me", headers=member).json()["credits"] == 3


def test_deleting_really_removes_files(client, member):
    pid = make_product(client, member, photos=2)
    gid = generate(client, member, pid).json()["id"]
    with new_session() as s:
        g = s.get(Generation, gid)
        keys = [g.final_key, g.preview_key, g.scene_key]
    assert all(storage.path_for(k).exists() for k in keys)
    client.delete(f"/generations/{gid}", headers=member)
    assert not any(storage.path_for(k).exists() for k in keys)

    detail = client.get(f"/products/{pid}", headers=member).json()
    photo_id = detail["photos"][0]["id"]
    gid2 = generate(client, member, pid, photo_id=photo_id).json()["id"]
    client.delete(f"/photos/{photo_id}", headers=member)
    g2 = client.get(f"/generations/{gid2}", headers=member).json()
    assert g2["original_deleted"] and client.get(f"/generations/{gid2}/original", headers=member).status_code == 410

    client.delete(f"/products/{pid}", headers=member)
    assert not storage.path_for(f"products/{pid}").exists()
