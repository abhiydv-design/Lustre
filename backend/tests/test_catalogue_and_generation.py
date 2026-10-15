"""Spec §9.3 catalogue, §9.4 generation, §9.7 credits."""
import io

from PIL import Image

from tests.conftest import generate, make_product, ring_photo


def test_product_crud_with_suggested_name(client, guest):
    assert client.post("/products", headers=guest, json={"category": "tiara"}).status_code == 422
    p = client.post("/products", headers=guest, json={"category": "ring"}).json()
    assert p["name"] == "Ring 1"  # required name, suggested so nobody has to type
    r = client.patch(f"/products/{p['id']}", headers=guest, json={"name": "Solitaire 18k", "sku": "R-102"})
    assert r.json()["name"] == "Solitaire 18k"
    assert [x["name"] for x in client.get("/products", headers=guest).json()] == ["Solitaire 18k"]
    assert client.delete(f"/products/{p['id']}", headers=guest).status_code == 204
    assert client.get(f"/products/{p['id']}", headers=guest).status_code == 404


def test_one_image_per_generation_cost_shown_first(client, guest):
    pid = make_product(client, guest)
    assert client.get(f"/products/{pid}", headers=guest).json()["metal"] == "yellow_gold"  # detected
    q = client.get(f"/products/{pid}/quote", headers=guest).json()
    assert q == {"cost": 1, "additional": False, "balance": 3, "enough": True}

    # Must confirm the cost the user was shown
    r = client.post(f"/products/{pid}/generations", headers=guest, json={"preset": "marble", "confirm_cost": 5})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "cost_changed"

    r = generate(client, guest, pid)
    assert r.status_code == 202
    g = client.get(f"/generations/{r.json()['id']}", headers=guest).json()
    assert g["status"] == "done" and g["width"] == 3840 and all(s["done"] for s in g["steps"])
    assert "check the details" in g["notice"]
    assert client.get("/me", headers=guest).json()["credits"] == 2
    assert client.get(f"/products/{pid}/quote", headers=guest).json()["additional"] is True

    detail = client.get(f"/products/{pid}", headers=guest).json()
    assert detail["image_count"] == 1 and len(detail["images"]) == 1


def test_guest_can_review_but_not_save(client, guest):
    pid = make_product(client, guest)
    gid = generate(client, guest, pid).json()["id"]
    assert client.get(f"/generations/{gid}/preview", headers=guest).status_code == 200  # watermarked
    assert client.get(f"/generations/{gid}/original", headers=guest).status_code == 200
    for r in (client.get(f"/generations/{gid}/download", headers=guest),
              client.post(f"/generations/{gid}/accept", headers=guest),
              client.post("/payments/orders", headers=guest, json={"pack": "shop"})):
        assert r.status_code == 403 and r.json()["detail"]["code"] == "sign_in_required"


def test_signed_in_download_is_free_and_full_size(client, member):
    pid = make_product(client, member)
    gid = generate(client, member, pid, preset="white", aspect="16:9").json()["id"]
    before = client.get("/me", headers=member).json()["credits"]
    r = client.get(f"/generations/{gid}/download", headers=member)
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content))
    assert img.size == (3840, 2160) and img.getpixel((5, 5)) == (255, 255, 255)
    assert float(r.headers["x-pixel-match"]) >= 0.995
    assert client.get("/me", headers=member).json()["credits"] == before
    assert client.post(f"/generations/{gid}/accept", headers=member).json()["review"] == "accepted"


def test_out_of_credits_and_idempotent_retries(client, guest):
    pid = make_product(client, guest)
    headers = {**guest, "Idempotency-Key": "tap-1"}
    first = client.post(f"/products/{pid}/generations", headers=headers, json={"preset": "grey", "confirm_cost": 1})
    retry = client.post(f"/products/{pid}/generations", headers=headers, json={"preset": "grey", "confirm_cost": 1})
    assert retry.status_code == 200 and retry.json()["id"] == first.json()["id"]
    assert client.get("/me", headers=guest).json()["credits"] == 2  # charged once
    generate(client, guest, pid)
    generate(client, guest, pid)
    r = generate(client, guest, pid)
    assert r.status_code == 402
    d = r.json()["detail"]
    assert d["code"] == "needs_credits" and d["needed"] == 1 and d["sign_in_required_to_buy"] is True


def test_v1_scope_presets(client, guest):
    pid = make_product(client, guest)
    r = generate(client, guest, pid, preset="festive")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "preset_unavailable"
    r = generate(client, guest, pid, output="marketplace", marketplace_preset="anything")
    assert r.json()["detail"]["code"] == "marketplace_unavailable"  # nothing verified yet
    cat = client.get("/catalog").json()
    assert [p["id"] for p in cat["presets"] if p["available"]] == ["white", "grey", "beige", "marble"]
    assert cat["outputs"][1] == {"id": "marketplace", "available": False}
    assert cat["categories"][0]["label_hi"]


def test_photo_tips_not_rejections(client, guest):
    p = client.post("/products", headers=guest, json={"category": "pendant"}).json()
    small = Image.new("RGB", (900, 700), (240, 240, 240))
    buf = io.BytesIO(); small.save(buf, "JPEG")
    r = client.post(f"/products/{p['id']}/photos", headers=guest,
                    files=[("files", ("small.jpg", buf.getvalue(), "image/jpeg")),
                           ("files", ("broken.png", b"nope", "image/png"))])
    assert r.status_code == 201
    assert "small" in r.json()["photos"][0]["hints"][0]
    assert any("couldn't open" in n for n in r.json()["notices"])


def test_other_users_cannot_see_anything(client, guest):
    pid = make_product(client, guest)
    gid = generate(client, guest, pid).json()["id"]
    other = {"Authorization": "Bearer " + client.post("/auth/start").json()["token"]}
    for url in (f"/products/{pid}", f"/generations/{gid}", f"/generations/{gid}/preview"):
        assert client.get(url, headers=other).status_code == 404
