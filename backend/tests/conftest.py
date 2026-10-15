import io
import os
import tempfile

import pytest
from PIL import Image, ImageDraw

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATA_DIR": _tmp, "DATABASE_URL": f"sqlite:///{_tmp}/test.db", "DEV_MODE": "1",
    "CUTOUT_PROVIDER": "threshold", "SCENE_PROVIDER": "mock", "UPSCALE_PROVIDER": "lanczos",
    "TRIAL_CREDITS": "3", "INITIAL_GENERATION_COST": "1", "ADDITIONAL_GENERATION_COST": "1",
    "QUALITY_REFUND_AUTO_LIMIT": "2", "ADMIN_TOKENS": "priya:tok-priya,rahul:tok-rahul", "COST_PER_SCENE_INR": "2.5", "COST_PER_UPSCALE_INR": "1.5", "PACK_SHOP_PRICE_INR": "999", "RAZORPAY_WEBHOOK_SECRET": "whsec_test",
})


def ring_photo(size=(2400, 1800), background=(238, 229, 212)) -> bytes:
    """A 'phone photo': gold ring with a blue gem on a slightly warm lightbox."""
    image = Image.new("RGB", size, background)
    d = ImageDraw.Draw(image)
    cx, cy, r = size[0] // 2, size[1] // 2 + 120, 360
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(196, 150, 60), width=90)
    d.polygon([(cx - 170, cy - r - 40), (cx - 80, cy - r - 190), (cx + 80, cy - r - 190),
               (cx + 170, cy - r - 40), (cx, cy - r + 110)], fill=(40, 90, 170), outline=(20, 50, 110))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def new_phone() -> str:
    import secrets
    return str(9_000_000_000 + secrets.randbelow(999_999_999))


@pytest.fixture
def guest(client):
    return {"Authorization": "Bearer " + client.post("/auth/start").json()["token"]}


def sign_in(client, headers=None, phone=None):
    phone = phone or new_phone()
    code = client.post("/auth/otp/request", json={"phone": phone}).json()["dev_code"]
    r = client.post("/auth/otp/verify", json={"phone": phone, "code": code}, headers=headers or {})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}, phone


@pytest.fixture
def member(client):
    return sign_in(client)[0]


def make_product(client, auth, category="ring", photos=1):
    p = client.post("/products", headers=auth, json={"category": category}).json()
    files = [("files", (f"p{i}.jpg", ring_photo(), "image/jpeg")) for i in range(photos)]
    r = client.post(f"/products/{p['id']}/photos", headers=auth, files=files)
    assert r.status_code == 201, r.text
    return p["id"]


def generate(client, auth, product_id, preset="marble", aspect="1:1", **extra):
    cost = client.get(f"/products/{product_id}/quote", headers=auth).json()["cost"]
    r = client.post(f"/products/{product_id}/generations", headers=auth,
                    json={"preset": preset, "aspect_ratio": aspect, "confirm_cost": cost, **extra})
    return r
