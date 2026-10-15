"""Operations console: report review queue, governed image access, §16 metrics."""
import hashlib
import hmac
import json

import pytest

from app import db
from app.config import get_settings
from tests.conftest import generate, make_product, sign_in

PRIYA = {"Authorization": "Bearer tok-priya"}


def under_review_report(client, member):
    """Three detail reports: the first two refund automatically (limit 2 in tests), the third waits."""
    pid = make_product(client, member)
    ids = [generate(client, member, pid).json()["id"] for _ in range(3)]
    for gid in ids:
        r = client.post(f"/generations/{gid}/report", headers=member,
                        json={"kind": "product_detail", "category": "stones", "note": "a stone is missing"})
    assert r.json()["refund"] == "under_review"
    queue = client.get("/admin/api/reports", headers=PRIYA).json()
    return ids[2], next(x for x in queue if x["status"] == "under_review" and x["signals"]["detail_reports_30d"] == 3)


def test_access_control(client, member):
    assert client.get("/admin/api/reports").status_code == 401
    assert client.get("/admin/api/reports", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/admin/api/reports", headers=member).status_code == 401  # customers aren't staff
    assert "Studio operations" in client.get("/admin").text


def test_console_disabled_without_admin_tokens(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKENS", "")
    get_settings.cache_clear()
    try:
        assert client.get("/admin").status_code == 404
        assert client.get("/admin/api/metrics", headers=PRIYA).status_code == 404
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_approve_refund_after_review(client, member):
    gid, report = under_review_report(client, member)
    assert report["signals"]["images_made"] == 3 and "phone" not in json.dumps(report)
    assert client.get("/me", headers=member).json()["credits"] == 2

    for which in ("original", "output"):
        assert client.get(f"/admin/api/reports/{report['id']}/image/{which}", headers=PRIYA).status_code == 200
    r = client.post(f"/admin/api/reports/{report['id']}/resolve", headers=PRIYA,
                    json={"decision": "approve", "internal_note": "centre stone missing in output"})
    assert r.json()["status"] == "refunded" and r.json()["resolved_by"] == "priya"
    assert client.get("/me", headers=member).json()["credits"] == 3
    seen = client.get(f"/generations/{gid}", headers=member).json()["reports"][0]
    assert seen["refund"] == "refunded" and "returned your credit" in seen["message"]
    assert client.post(f"/admin/api/reports/{report['id']}/resolve", headers=PRIYA,
                       json={"decision": "approve"}).status_code == 409

    log = client.get("/admin/api/audit", headers=PRIYA).json()
    actions = [(a["admin"], a["action"], a["detail"]) for a in log[:4]]
    assert ("priya", "resolve_report", "approve -> refunded") in actions
    assert ("priya", "view_image", "output") in actions and ("priya", "view_image", "original") in actions


def test_decline_needs_a_reason_and_is_shown_to_customer(client, member):
    gid, report = under_review_report(client, member)
    url = f"/admin/api/reports/{report['id']}/resolve"
    assert client.post(url, headers=PRIYA, json={"decision": "decline"}).status_code == 422
    r = client.post(url, headers={"Authorization": "Bearer tok-rahul"},
                    json={"decision": "decline", "user_message": "We compared both images: all three stones are there."})
    assert r.json()["status"] == "declined" and r.json()["resolved_by"] == "rahul"
    assert client.get("/me", headers=member).json()["credits"] == 2
    seen = client.get(f"/generations/{gid}", headers=member).json()["reports"][0]
    assert seen["refund"] == "declined" and "all three stones" in seen["message"]


def test_refund_still_works_after_customer_deleted_the_image(client, member):
    gid, report = under_review_report(client, member)
    client.delete(f"/generations/{gid}", headers=member)
    assert client.get(f"/admin/api/reports/{report['id']}/image/output", headers=PRIYA).status_code == 410
    r = client.post(f"/admin/api/reports/{report['id']}/resolve", headers=PRIYA, json={"decision": "approve"})
    assert r.json()["status"] == "refunded"
    assert client.get("/me", headers=member).json()["credits"] == 3


@pytest.fixture
def fresh_db(tmp_path):
    saved = db.SessionLocal
    db.init_db(f"sqlite:///{tmp_path / 'm.db'}")
    yield
    db.SessionLocal = saved


def test_metrics_match_known_activity(client, fresh_db):
    member, _ = sign_in(client)
    idle = {"Authorization": "Bearer " + client.post("/auth/start").json()["token"]}  # never uploads
    pid = make_product(client, member)
    g1 = generate(client, member, pid, preset="marble").json()["id"]   # AI look: costs 2.5 + 1.5
    g2 = generate(client, member, pid, preset="white").json()["id"]    # flat look: no provider cost
    client.post(f"/generations/{g1}/accept", headers=member)
    client.get(f"/generations/{g1}/download", headers=member)
    client.post(f"/generations/{g1}/events", headers=member, json={"type": "share", "channel": "WhatsApp"})
    client.post(f"/generations/{g2}/report", headers=member, json={"kind": "visual_quality", "category": "shadow"})
    order = client.post("/payments/orders", headers=member, json={"pack": "shop"}).json()
    body = json.dumps({"event": "order.paid", "payload": {"payment": {"entity": {"order_id": order["order_id"]}}}}).encode()
    client.post("/payments/webhook", content=body,
                headers={"X-Razorpay-Signature": hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()})

    m = client.get("/admin/api/metrics?days=30", headers=PRIYA).json()
    u, q, b = m["usage"], m["quality"], m["business"]
    assert u["new_accounts"] == 2
    assert u["accepted_image_rate"] == 0.5 and u["download_rate"] == 0.5 and u["share_rate"] == 0.5
    assert u["shares_by_channel"] == {"whatsapp": 1}
    assert u["repeat_generation_rate"] == 1.0 and u["upload_to_generation_conversion"] == 1.0
    assert u["median_minutes_to_first_result"] is not None
    assert q["visual_quality_complaint_rate"] == 0.5 and q["product_detail_complaint_rate"] == 0.0
    assert q["technical_failure_rate"] == 0.0 and q["user_judged_usable_rate"] == 0.5
    assert set(q["by_preset"]) == {"marble", "white"} and q["by_category"]["ring"]["generations"] == 2
    assert b["trial_activation_rate"] == 0.5 and b["trial_to_purchase_conversion"] == 1.0
    assert b["paying_accounts"] == 1 and b["revenue_inr"] == 999.0
    assert b["estimated_provider_cost_inr"] == 4.0 and b["cost_per_accepted_image_inr"] == 4.0
    assert client.post(f"/generations/{g1}/events", headers=member, json={"type": "hack"}).status_code == 422
