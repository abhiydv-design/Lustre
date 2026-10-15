"""The jeweller-facing web app is served, and the endpoints it relies on behave as it expects."""
import io
import re
from pathlib import Path

from PIL import Image

from tests.conftest import generate, make_product

WEB = Path(__file__).parent.parent / "app" / "web"


def test_app_is_served(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/app/"
    page = client.get("/app/")
    assert page.status_code == 200 and 'src="app.js"' in page.text
    for f in ("app.js", "i18n.js", "manifest.webmanifest", "icon.svg"):
        assert client.get(f"/app/{f}").status_code == 200


def test_every_text_key_exists_in_english_and_hindi():
    src = (WEB / "i18n.js").read_text(encoding="utf-8")
    en, hi = src.split("\n  hi: {")
    keys = lambda block: set(re.findall(r"^\s{4}(\w+):", block, re.M)) | set(re.findall(r",\s(\w+):", block))
    assert keys(en) == keys(hi)
    used = {k for k in re.findall(r'\bt\("(\w+)"', (WEB / "app.js").read_text(encoding="utf-8")) if not k.endswith("_")}
    assert not used - keys(en), f"missing text keys: {used - keys(en)}"
    # Keys the app builds from values the server returns
    from app.routes.generations import DETAIL_ISSUES, QUALITY_ISSUES, STAGES
    dynamic = {f"rc_{c}" for c in {**DETAIL_ISSUES, **QUALITY_ISSUES}}
    dynamic |= {f"step_{s}" for s, _ in STAGES}
    dynamic |= {f"rep_{r}" for r in ("refunded", "duplicate", "under_review", "not_eligible", "declined")}
    dynamic |= {f"reason_{r}" for r in ("trial", "generation", "refund_technical", "refund_quality", "purchase", "trial_reused")}
    assert not dynamic - keys(en), f"missing dynamic keys: {dynamic - keys(en)}"


def test_photo_thumbnails_and_product_link(client, guest):
    pid = make_product(client, guest)
    photo = client.get(f"/products/{pid}", headers=guest).json()["photos"][0]
    thumb = client.get(f"{photo['url']}?w=400", headers=guest)
    assert thumb.headers["content-type"] == "image/jpeg"
    assert max(Image.open(io.BytesIO(thumb.content)).size) <= 400
    gid = generate(client, guest, pid).json()["id"]
    assert client.get(f"/generations/{gid}", headers=guest).json()["product_id"] == pid
