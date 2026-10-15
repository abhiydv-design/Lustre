"""The jeweller's path: open app → add photos → see photos → download. Nothing else required."""
import hashlib
import hmac
import io
import json
import zipfile

import pytest
from PIL import Image

from app.config import get_settings
from tests.conftest import ring_photo


@pytest.fixture
def friendly(monkeypatch):
    monkeypatch.setenv("AUTO_JOBS", "white:1,marble:4")
    monkeypatch.setenv("PRERENDER_PER_JOB", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_photos_only_upload_starts_generating_and_detects_metal(client, friendly):
    auth = {"Authorization": "Bearer " + client.post("/auth/start").json()["token"]}  # no form at all
    files = [("files", ("ring.jpg", ring_photo(), "image/jpeg"))]
    r = client.post("/shoots", headers=auth, files=files)  # no type, no metal, no style
    assert r.status_code == 201, r.text
    body = r.json()
    assert [j["style"] for j in body["jobs"]] == ["white", "marble"]

    shoot = client.get(f"/shoots/{body['id']}", headers=auth).json()
    assert shoot["metal"] == "yellow_gold" and shoot["metal_detected"]

    for j in body["jobs"]:
        job = client.get(f"/jobs/{j['id']}", headers=auth).json()
        assert job["status"] == "done"
        assert job["variations"][0]["instant"]  # 4K already waiting

    # One-tap fix if detection is wrong
    assert client.patch(f"/shoots/{body['id']}", headers=auth, json={"metal": "rose_gold"}).status_code == 200


def test_soft_upload_rules(client, auth):
    small = Image.new("RGB", (900, 700), (240, 240, 240))
    buf = io.BytesIO(); small.save(buf, "JPEG")
    files = [("files", (f"r{i}.jpg", ring_photo(), "image/jpeg")) for i in range(5)]
    files += [("files", ("broken.jpg", b"not an image", "image/jpeg"))]
    r = client.post("/shoots", headers=auth, files=files, data={"auto_generate": "false"})
    assert r.status_code == 201
    assert any("first 4" in n for n in r.json()["notices"])
    r = client.post("/shoots", headers=auth, data={"auto_generate": "false"},
                    files=[("files", ("small.jpg", buf.getvalue(), "image/jpeg")),
                           ("files", ("broken.png", b"nope", "image/png"))])
    assert r.status_code == 201  # small photo accepted with a tip, broken one skipped politely
    assert "small" in r.json()["photos"][0]["hints"][0]
    assert any("couldn't open" in n for n in r.json()["notices"])


def _job(client, auth, count=4):
    shoot = client.post("/shoots", headers=auth, data={"auto_generate": "false"},
                        files=[("files", ("ring.jpg", ring_photo(), "image/jpeg"))]).json()["id"]
    jid = client.post(f"/shoots/{shoot}/jobs", headers=auth, json={"style": "silk", "count": count}).json()["id"]
    return client.get(f"/jobs/{jid}", headers=auth).json()


def test_prepare_makes_download_instant(client, auth):
    vid = _job(client, auth, count=1)["variations"][0]["id"]
    assert client.post(f"/variations/{vid}/prepare", headers=auth).json()["status"] == "rendering"
    assert client.get("/me", headers=auth).json()["credits"] == 3  # warming is free
    assert client.post(f"/variations/{vid}/download", headers=auth).json()["status"] == "ready"
    assert client.get("/me", headers=auth).json()["credits"] == 2


def test_download_all_as_zip(client, auth):
    job = _job(client, auth, count=2)
    assert client.post(f"/jobs/{job['id']}/download-all", headers=auth).status_code == 202
    r = client.get(f"/jobs/{job['id']}/download-all", headers=auth)
    assert r.status_code == 200
    assert len(zipfile.ZipFile(io.BytesIO(r.content)).namelist()) == 2
    assert client.get("/me", headers=auth).json()["credits"] == 1


def test_out_of_credits_buy_then_photo_arrives_by_itself(client, auth):
    job = _job(client, auth, count=4)
    r = client.post(f"/jobs/{job['id']}/download-all", headers=auth)
    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "needs_credits" and detail["needed"] == 1 and detail["packs"]

    order = client.post("/payments/orders", headers=auth,
                        json={"pack": "shop", "then_download": [v["id"] for v in job["variations"]]}).json()
    body = json.dumps({"event": "order.paid", "payload": {"payment": {"entity": {"order_id": order["order_id"]}}}}).encode()
    sig = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()
    assert client.post("/payments/webhook", content=body, headers={"X-Razorpay-Signature": sig}).status_code == 200

    assert client.get(f"/jobs/{job['id']}/download-all", headers=auth).status_code == 200  # no extra tap
    assert client.get("/me", headers=auth).json()["credits"] == 3 + 50 - 4


def test_friendly_message_when_no_jewellery_found(client, auth):
    blank = Image.new("RGB", (1600, 1200), (245, 245, 245))
    buf = io.BytesIO(); blank.save(buf, "JPEG")
    shoot = client.post("/shoots", headers=auth, data={"auto_generate": "false"},
                        files=[("files", ("empty.jpg", buf.getvalue(), "image/jpeg"))]).json()["id"]
    jid = client.post(f"/shoots/{shoot}/jobs", headers=auth, json={"style": "marble", "count": 1}).json()["id"]
    job = client.get(f"/jobs/{jid}", headers=auth).json()
    assert job["status"] == "failed" and "plain, light background" in job["message"]
