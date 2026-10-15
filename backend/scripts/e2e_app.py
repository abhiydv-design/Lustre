"""Walk through the jeweller app in a phone-sized headless browser (Playwright).

    pip install playwright && python -m playwright install chromium
    DEV_MODE=1 SCENE_PROVIDER=mock UPSCALE_PROVIDER=lanczos CUTOUT_PROVIDER=threshold \
      PACK_SHOP_PRICE_INR=999 PACK_STARTER_PRICE_INR=249 uvicorn app.main:app --port 8820 &
    python scripts/e2e_app.py            # screenshots go to scripts/e2e-shots/

Covers: first open, new product + upload, make an image, compare, sign-in on Save,
download, report, buying credits (test mode), Hindi. Fails on any JavaScript error
other than offline fonts and the expected sign-in 403.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.conftest import ring_photo  # noqa: E402

BASE = os.environ.get("APP_URL", "http://127.0.0.1:8820")
OUT = Path(__file__).parent / "e2e-shots"
OUT.mkdir(exist_ok=True)
PHOTO = OUT / "ring.jpg"
PHOTO.write_bytes(ring_photo())
from playwright.sync_api import sync_playwright, expect
errors = []
def shot(pg, name): pg.screenshot(path=fstr(OUT) + "/{name}.png")
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="en-IN", accept_downloads=True)
    pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/")
    pg.wait_for_selector("[data-start]"); shot(pg, "01_onboarding")
    pg.click("[data-start]")
    pg.wait_for_selector("[data-cat=ring]"); pg.click("[data-cat=ring]")
    pg.fill("[data-name]", "Sapphire solitaire")
    shot(pg, "02_new_product")
    pg.set_input_files("[data-gallery]", str(PHOTO))
    pg.wait_for_selector("text=Make an image"); pg.wait_for_timeout(800); shot(pg, "03_product")
    pg.click("text=Make an image")
    pg.wait_for_selector("[data-look=marble]"); pg.click("[data-look=marble]")
    expect(pg.locator("[data-go]")).to_contain_text("1 credit"); shot(pg, "04_make")
    pg.click("[data-go]")
    pg.wait_for_selector("[data-save]", timeout=30000); pg.wait_for_timeout(600); shot(pg, "05_result")
    assert "2 credits" in pg.inner_text(".bar .chip"), pg.inner_text(".bar .chip"); print("credit chip updated: ok")
    pg.click("[data-v=original]"); pg.wait_for_timeout(500); shot(pg, "06_compare_original"); pg.click("[data-v=result]")
    # Save needs sign-in: sheet appears, then the save completes by itself
    pg.click("[data-save]")
    pg.wait_for_selector("input[type=tel]"); pg.fill("input[type=tel]", "98765 43210"); shot(pg, "07_signin")
    pg.click("[data-send]")
    pg.wait_for_selector("[data-sent]:has-text('Test mode code')")
    code = pg.inner_text("[data-sent]").split(":")[-1].strip()
    pg.fill("[data-step=code] input", code); pg.click("[data-verify]")
    pg.wait_for_selector("[data-save][disabled]"); print("saved after sign-in: ok")
    with pg.expect_download() as d:
        pg.click("[data-dl]")
    print("download:", d.value.suggested_filename)
    pg.click("[data-report]"); pg.wait_for_selector("input[value=stones]")
    pg.check("input[value=stones]"); pg.fill(".sheet textarea", "one stone looks smaller"); shot(pg, "08_report")
    pg.click("[data-send]"); pg.wait_for_selector(".toast"); print("report toast:", pg.inner_text(".toast"))
    pg.goto(BASE + "/app/#/credits"); pg.wait_for_selector("[data-pack=shop]"); shot(pg, "09_credits")
    before = pg.inner_text(".card")
    pg.click("[data-pack=shop]"); pg.wait_for_selector(".toast:has-text('Credits added')"); print("bought credits: ok")
    pg.goto(BASE + "/app/#/settings"); pg.wait_for_selector("[data-lang=hi]"); pg.click("[data-lang=hi]")
    pg.wait_for_timeout(300); shot(pg, "10_settings_hi")
    pg.goto(BASE + "/app/#/"); pg.wait_for_selector(".product"); pg.wait_for_timeout(600); shot(pg, "11_home_hi")
    pg.click(".product"); pg.wait_for_selector(".thumb"); pg.click("a.product"); pg.wait_for_selector("[data-report]"); pg.wait_for_timeout(500)
    shot(pg, "12_result_hi")
    b.close()
real = [e for e in errors if "ERR_NAME_NOT_RESOLVED" not in e and "403" not in e]
print("JS errors:", real or "none")
sys.exit(1 if real else 0)
