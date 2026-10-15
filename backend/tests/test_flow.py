import hashlib
import hmac
import io
import json

import numpy as np
from PIL import Image

from tests.conftest import ring_photo


def _upload(client, auth, n=2):
    files = [("files", (f"ring{i}.jpg", ring_photo(), "image/jpeg")) for i in range(n)]
    r = client.post("/shoots", headers=auth, files=files, data={"jewellery_type": "ring", "metal": "yellow_gold"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _generate(client, auth, shoot_id, style="marble", fmt="1:1", count=4):
    r = client.post(f"/shoots/{shoot_id}/jobs", headers=auth, json={"style": style, "format": fmt, "count": count})
    assert r.status_code == 202, r.text
    job = client.get(f"/jobs/{r.json()['id']}", headers=auth).json()  # background task already ran
    assert job["status"] == "done", job
    return job


def test_full_flow_preview_download_and_credits(client, auth):
    assert client.get("/me", headers=auth).json()["credits"] == 3
    job = _generate(client, auth, _upload(client, auth))
    assert len(job["variations"]) == 4
    assert all(s["done"] for s in job["steps"])
    assert all(v["fidelity"] >= 0.995 for v in job["variations"])

    vid = job["variations"][0]["id"]
    prev = Image.open(io.BytesIO(client.get(f"/variations/{vid}/preview", headers=auth).content))
    assert prev.size == (1024, 1024)

    assert client.post(f"/variations/{vid}/download", headers=auth).json()["status"] == "rendering"
    r = client.get(f"/variations/{vid}/download", headers=auth)
    assert r.status_code == 200
    final = Image.open(io.BytesIO(r.content))
    assert final.size == (3840, 3840)
    assert float(r.headers["x-fidelity"]) >= 0.995
    assert client.get("/me", headers=auth).json()["credits"] == 2

    # Re-download is free
    client.post(f"/variations/{vid}/download", headers=auth)
    assert client.get("/me", headers=auth).json()["credits"] == 2


def test_white_catalog_is_pure_white(client, auth):
    job = _generate(client, auth, _upload(client, auth, n=1), style="white", fmt="16:9", count=2)
    vid = job["variations"][0]["id"]
    client.post(f"/variations/{vid}/download", headers=auth)
    final = np.asarray(Image.open(io.BytesIO(client.get(f"/variations/{vid}/download", headers=auth).content)))
    assert final.shape[:2] == (2160, 3840)
    assert (final[:40, :40] == 255).all()  # corners are #FFFFFF for marketplaces


def test_white_balance_neutralises_warm_cast():
    from app.pipeline.cutout import ThresholdCutout
    from app.pipeline.prepare import load_photo, white_balance_gains
    photo = load_photo(ring_photo())
    gains = white_balance_gains(photo, ThresholdCutout()(photo).getchannel("A"))
    assert gains[2] > 1.0 > gains[0]  # boost blue, reduce red


def test_out_of_credits_and_unavailable_style(client, auth):
    shoot = _upload(client, auth, n=1)
    r = client.post(f"/shoots/{shoot}/jobs", headers=auth, json={"style": "on_model", "count": 2})
    assert r.status_code == 422
    job = _generate(client, auth, shoot, count=4)
    codes = [client.post(f"/variations/{v['id']}/download", headers=auth).status_code for v in job["variations"]]
    assert codes == [202, 202, 202, 402]


def test_other_users_cannot_see_photos(client, auth):
    job = _generate(client, auth, _upload(client, auth, n=1), count=1)
    other = {"Authorization": "Bearer " + client.post("/auth/dev-login", json={"name": "x"}).json()["token"]}
    assert client.get(f"/variations/{job['variations'][0]['id']}/preview", headers=other).status_code == 404


def test_razorpay_webhook_adds_credits_once(client, auth):
    order = client.post("/payments/orders", headers=auth, json={"pack": "shop"}).json()
    assert order["amount"] == 99900
    body = json.dumps({"event": "order.paid", "payload": {"payment": {"entity": {"order_id": order["order_id"]}}}}).encode()
    sig = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()
    bad = client.post("/payments/webhook", content=body, headers={"X-Razorpay-Signature": "nope"})
    assert bad.status_code == 400
    for _ in range(2):  # Razorpay retries webhooks; must not double-credit
        assert client.post("/payments/webhook", content=body, headers={"X-Razorpay-Signature": sig}).status_code == 200
    assert client.get("/me", headers=auth).json()["credits"] == 53


def test_failed_4k_render_refunds_credit(client, auth, monkeypatch):
    import app.pipeline.run as run
    job = _generate(client, auth, _upload(client, auth, n=1), count=1)
    vid = job["variations"][0]["id"]
    monkeypatch.setattr(run, "render_final", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("upscaler down")))
    client.post(f"/variations/{vid}/download", headers=auth)
    assert client.get(f"/variations/{vid}/download", headers=auth).json()["status"] == "failed"
    assert client.get("/me", headers=auth).json()["credits"] == 3  # charged, then refunded
    monkeypatch.undo()
    client.post(f"/variations/{vid}/download", headers=auth)  # retry charges again and succeeds
    assert client.get(f"/variations/{vid}/download", headers=auth).status_code == 200
    assert client.get("/me", headers=auth).json()["credits"] == 2
