import io
import os
import tempfile

import pytest
from PIL import Image, ImageDraw

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATA_DIR": _tmp, "DATABASE_URL": f"sqlite:///{_tmp}/test.db", "DEV_MODE": "1",
    "CUTOUT_PROVIDER": "threshold", "SCENE_PROVIDER": "mock", "UPSCALE_PROVIDER": "lanczos",
    "FREE_CREDITS": "3", "AUTO_JOBS": "", "PRERENDER_PER_JOB": "0", "PACK_SHOP_PRICE_INR": "999", "RAZORPAY_WEBHOOK_SECRET": "whsec_test",
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


@pytest.fixture
def auth(client):
    token = client.post("/auth/start").json()["token"]
    return {"Authorization": f"Bearer {token}"}
