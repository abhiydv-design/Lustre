"""Complete end-to-end check, as a jeweller (two phones, English and Hindi) and as the team.

Needs a running app with a fresh data folder and QUALITY_REFUND_AUTO_LIMIT=1 in backend/.env,
so the second reported detail lands in the review queue:

    pip install playwright && python -m playwright install chromium
    python start.py --no-browser          (with QUALITY_REFUND_AUTO_LIMIT=1 added to backend/.env)
    python backend/scripts/full_check.py  (in another window)

Prints PASS/FAIL for each of 28 checks; failure screenshots go to backend/scripts/check-shots/.
"""
import os, re, sys, time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright, expect

B = os.environ.get("APP_URL", "http://127.0.0.1:8000")
ENV = Path(__file__).resolve().parent.parent / ".env"
TOKEN = [l.split(":", 1)[1].split()[0] for l in open(ENV) if l.startswith("ADMIN_TOKENS=")][0]
SH = str(Path(__file__).resolve().parent / "check-shots")
Path(SH).mkdir(exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import io
from PIL import ImageFilter
from tests.conftest import ring_photo
open(f"{SH}/ring.jpg", "wb").write(ring_photo())
Image.open(io.BytesIO(ring_photo())).resize((900, 675)).point(lambda v: int(v * 0.25)).filter(ImageFilter.GaussianBlur(5)).save(f"{SH}/dark_blurry.jpg", quality=90)
Image.new("RGB", (1600, 1200), (244, 243, 240)).save(f"{SH}/no_jewellery.jpg", quality=90)
results, errors, PAGES = [], [], []
PHONE = "9123456780"

def check(name, fn):
    try:
        fn(); results.append(("PASS", name, ""))
    except Exception as e:
        try:
            for page in PAGES: page.screenshot(path=f"{SH}/FAIL_{len(results)}_{PAGES.index(page)}.png")
        except Exception: pass
        results.append(("FAIL", name, ((str(e) or repr(e)).splitlines() or [repr(e)])[0][:220]))

def ready(pg):
    pg.wait_for_function("() => !document.querySelector('#app').hasAttribute('aria-busy')", timeout=15000)

def shot(pg, n): pg.screenshot(path=f"{SH}/{n}.png")

def sign_in(pg):
    pg.wait_for_selector("input[type=tel]"); pg.fill("input[type=tel]", PHONE); pg.click("[data-send]")
    pg.wait_for_selector("[data-sent]:has-text('Test mode code')")
    pg.fill("[data-step=code] input", pg.inner_text("[data-sent]").split(":")[-1].strip()); pg.click("[data-verify]")

def credits(pg):
    return int(re.search(r"\d+", pg.inner_text(".bar .chip")).group())

def wait_credits(pg, n):
    expect(pg.locator(".bar .chip")).to_have_text(re.compile(rf"\b{n}\b"), timeout=8000)

def generate(pg, look="white", ratio="1:1"):
    pg.click("a.btn:has-text('Make an image'), a.btn:has-text('इमेज बनाएँ'), a:has-text('Make another')")
    pg.wait_for_selector(f"[data-look={look}]"); pg.click(f"[data-look={look}]"); pg.click(f"[data-ratio='{ratio}']")
    expect(pg.locator("[data-go]")).not_to_have_text("…")
    pg.click("[data-go]"); pg.wait_for_selector("[data-save], .note.warn", timeout=30000)

with sync_playwright() as p:
    b = p.chromium.launch()
    phone = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, accept_downloads=True)
    pg = phone.new_page(); PAGES.append(pg)
    pg.on("pageerror", lambda e: errors.append("jeweller: " + str(e)))
    pg.on("console", lambda m: errors.append("jeweller console: " + m.text) if m.type == "error" and "ERR_NAME_NOT_RESOLVED" not in m.text and "403" not in m.text and "402" not in m.text else None)

    # ---------------- Jeweller, English ----------------
    pg.goto(B + "/app/")
    check("Onboarding shows language choice, tips and Start", lambda: (pg.wait_for_selector("[data-start]"), expect(pg.locator("[data-lang=hi]")).to_be_visible(), shot(pg, "01_onboarding")))
    pg.click("[data-start]")
    def new_product():
        pg.wait_for_selector("[data-cat=ring]")
        expect(pg.locator("[data-pick]")).to_be_disabled()  # category first
        pg.click("[data-cat=ring]"); pg.fill("[data-name]", "Kundan ring")
        pg.set_input_files("[data-gallery]", f"{SH}/ring.jpg")
        pg.wait_for_selector(".bar h1:has-text('Kundan ring')"); pg.wait_for_selector(".thumb img")
    check("New product: category, name, photo upload", new_product)
    def metal():
        for _ in range(20):
            pg.reload(); pg.wait_for_selector(".thumb")
            if "Yellow gold" in pg.inner_text("main"): return
            time.sleep(0.5)
        raise AssertionError("metal not detected")
    check("Metal detected automatically (Yellow gold)", metal)
    def tips():
        pg.set_input_files("[data-gallery]", f"{SH}/dark_blurry.jpg")
        pg.wait_for_selector(".note.warn"); txt = pg.inner_text("main")
        assert "dark" in txt and ("blurry" in txt or "small" in txt), txt[:300]
        assert pg.locator(".grid3 .thumb img").count() == 2; shot(pg, "02_product_tips")
    check("Second angle added; dark/blurry photo gets friendly tips", tips)
    def rename():
        pg.click("[data-rename]"); pg.fill(".sheet input", "Kundan ring 22k"); pg.click("[data-ok]")
        pg.wait_for_selector(".bar h1:has-text('Kundan ring 22k')")
    check("Rename product", rename)
    def first_image():
        pg.click("a.btn:has-text('Make an image')"); pg.wait_for_selector("[data-look=white]")
        expect(pg.locator("[data-cost]")).to_have_text("This image costs 1 credit. You have 3."); shot(pg, "03_make")
        assert pg.locator("[data-look]").count() == 4, "expected 4 v1 looks"
        pg.click("[data-look=white]"); pg.click("[data-go]"); pg.wait_for_selector("[data-save]", timeout=30000)
        wait_credits(pg, 2); shot(pg, "04_result")
    check("Make image: cost shown first, 4 looks, result, credits 3 → 2", first_image)
    def compare():
        pg.click("[data-v=original]"); pg.wait_for_selector("[data-stage] img[src^=blob]"); pg.click("[data-v=result]")
    check("Compare with original", compare)
    def second_image():
        generate(pg, "marble", "4:5"); wait_credits(pg, 1)
    check("Make another (Marble, portrait) costs 1 more", second_image)
    def save_signin():
        pg.click("[data-save]"); sign_in(pg); pg.wait_for_selector("[data-save][disabled]:has-text('Saved')")
    check("Save asks for phone sign-in, then saves", save_signin)
    def download():
        with pg.expect_download() as d: pg.click("[data-dl]")
        size = Image.open(d.value.path()).size
        assert size == (3072, 3840), size; assert d.value.suggested_filename.startswith("kundan-ring-22k-marble")
    check("Download full-size portrait file 3072×3840 with product name", download)
    def share():
        pg.click("[data-share]"); pg.wait_for_selector(".toast:has-text('Sharing isn')")
    check("Share falls back politely where sharing isn't supported", share)
    def report_refund():
        pg.click("[data-report]"); pg.check("input[value=stones]"); pg.click("[data-send]")
        pg.wait_for_selector(".toast:has-text('credit has been returned')"); wait_credits(pg, 2)
    check("Report changed detail → credit returned (1 → 2)", report_refund)
    def report_review():
        generate(pg, "beige"); wait_credits(pg, 1)
        pg.click("[data-report]"); pg.check("input[value=setting]"); pg.fill(".sheet textarea", "Prong looks different"); pg.click("[data-send]")
        pg.wait_for_selector(".toast:has-text(\"We'll check this\")"); shot(pg, "05_under_review")
    check("Report beyond auto-limit → 'we'll check this'", report_review)
    def out_of_credits():
        generate(pg, "grey"); wait_credits(pg, 0)
        pg.click("a:has-text('Make another')"); pg.wait_for_selector("[data-go]:has-text('Not enough credits')")
        pg.click("[data-go]"); pg.click("[data-buy]"); pg.wait_for_selector("[data-pack=starter]")
        pg.click("[data-pack=starter]"); pg.wait_for_selector(".toast:has-text('Credits added')")
        expect(pg.locator(".card")).to_contain_text("10"); shot(pg, "06_credits")
    check("Out of credits → buy pack → 10 credits", out_of_credits)
    def history():
        txt = pg.inner_text(".list")
        for w in ("Free trial", "Image", "Refund: reported detail", "Bought credits"): assert w in txt, w
    check("Credit history readable", history)
    def failed_photo():
        pg.goto(B + "/app/#/new"); pg.click("[data-cat=pendant]"); pg.set_input_files("[data-gallery]", f"{SH}/no_jewellery.jpg")
        pg.wait_for_selector("a.btn:has-text('Make an image')"); before = None
        pg.click("a.btn:has-text('Make an image')"); pg.wait_for_selector("[data-go]:has-text('credit')"); pg.click("[data-go]")
        pg.wait_for_selector("text=credit has been returned", timeout=30000)
        pg.goto(B + "/app/#/credits"); expect(pg.locator(".card")).to_contain_text("10"); shot(pg, "07_after_failure")
    check("Photo with no jewellery → image fails → credit returned", failed_photo)
    def delete_image():
        pg.goto(B + "/app/#/"); pg.click("a.product:has-text('Kundan ring 22k')"); pg.wait_for_selector("a.product[href^='#/g/']")
        n = pg.locator("a.product[href^='#/g/']").count()
        pg.locator("a.product[href^='#/g/']").first.click(); pg.wait_for_selector("[data-dl]"); ready(pg); pg.click("[data-del]")
        expect(pg.locator(".sheet h2")).to_have_text("Delete this image?"); pg.click("[data-yes]")
        pg.wait_for_selector(".bar h1:has-text('Kundan ring 22k')"); ready(pg)
        assert pg.locator("a.product[href^='#/g/']").count() == n - 1
    check("Delete an image", delete_image)
    def stale_screen_guard():
        pg.goto(B + "/app/#/"); ready(pg); pg.click("a.product:has-text('Kundan ring 22k')"); pg.wait_for_selector("a.product[href^='#/g/']"); ready(pg)
        slow = lambda route: (time.sleep(2), route.continue_())
        pg.route("**/generations/*", slow)
        pg.locator("a.product[href^='#/g/']").first.click()
        try:
            pg.click(".bar [data-del]", timeout=900)  # old screen's delete-product button
            raise AssertionError("old screen accepted a tap while the next one was loading")
        except Exception as e:
            if "accepted a tap" in str(e): raise
        pg.unroute("**/generations/*"); pg.wait_for_selector("[data-dl]"); ready(pg)
        assert pg.locator(".sheet").count() == 0
    check("Slow network: the old screen ignores taps while the next one loads", stale_screen_guard)

    # ---------------- Jeweller, Hindi ----------------
    def hindi():
        pg.goto(B + "/app/#/settings"); pg.click("[data-lang=hi]")
        pages = {"#/": "आपके प्रोडक्ट", "#/credits": "क्रेडिट खरीदें"}
        for h, word in pages.items():
            pg.goto(B + "/app/" + h); pg.wait_for_selector(f"text={word}")
        pg.click("a.product >> nth=0") if False else None
        pg.goto(B + "/app/#/"); pg.click("a.product:has-text('Kundan')"); pg.wait_for_selector("text=इमेज बनाएँ")
        pg.click("a.btn:has-text('इमेज बनाएँ')"); pg.wait_for_selector("text=लुक चुनें")
        txt = pg.inner_text("body")
        leftovers = [w for w in ("Choose a look", "Make image", "This image costs", "Size", "Square") if w in txt]
        assert not leftovers, f"English left on Hindi screen: {leftovers}"
        shot(pg, "08_make_hindi")
        pg.click("[data-go]"); pg.wait_for_selector("text=नतीजा", timeout=30000); pg.wait_for_selector("[data-save]")
        txt = pg.inner_text("main")
        leftovers = [w for w in ("Check the details", "Save", "Download", "Report a problem") if w in txt]
        assert not leftovers, f"English left on Hindi result: {leftovers}"; shot(pg, "09_result_hindi")
    check("Hindi: home, credits, make, result fully in Hindi", hindi)
    pg.goto(B + "/app/#/settings"); pg.click("[data-lang=en]")

    # ---------------- Same jeweller, second phone ----------------
    def second_device():
        ctx2 = b.new_context(viewport={"width": 390, "height": 844}); p2 = ctx2.new_page()
        p2.on("pageerror", lambda e: errors.append("device2: " + str(e)))
        p2.goto(B + "/app/"); p2.click("[data-start]"); p2.click("[data-cat=earrings]")
        p2.set_input_files("[data-gallery]", f"{SH}/ring.jpg"); p2.wait_for_selector(".thumb img")
        p2.click("a.btn:has-text('Make an image')"); p2.wait_for_selector("[data-go]:has-text('credit')"); p2.click("[data-go]")
        p2.wait_for_selector("[data-save]", timeout=30000); p2.click("[data-save]"); sign_in(p2)
        p2.wait_for_selector("[data-save][disabled]")
        p2.goto(B + "/app/#/"); p2.wait_for_selector("a.product")
        names = p2.locator("a.product b").all_inner_texts()
        assert any("Kundan" in n for n in names) and any("Earrings" in n for n in names), names
        c = int(re.search(r"\d+", p2.inner_text(".bar .chip")).group())
        assert c == 9, f"credits after merge {c} (guest trial must not be added)"; ctx2.close()
    check("Second phone: guest work kept after signing in with same number; no extra trial", second_device)

    # ---------------- Team member, laptop ----------------
    lap = b.new_context(viewport={"width": 1280, "height": 900}); a = lap.new_page()
    a.on("pageerror", lambda e: errors.append("admin: " + str(e)))
    a.add_init_script(f"sessionStorage.setItem('adminToken', '{TOKEN}')")
    def admin_queue():
        a.goto(B + "/admin"); a.wait_for_selector(".queue")
        expect(a.locator(".queue h2")).to_have_text("1 waiting")
        a.wait_for_selector(".stage img"); assert a.locator(".stage img").count() == 2, "both images visible"
        expect(a.locator(".claim")).to_contain_text("Prong looks different"); a.screenshot(path=f"{SH}/10_admin_queue.png")
    check("Console: claim waiting with both images and the customer's note", admin_queue)
    def admin_decline_needs_reason():
        a.click("#decline"); a.wait_for_selector("#result .err")
    check("Console: declining without a message is blocked", admin_decline_needs_reason)
    def admin_approve():
        a.fill("#note", "Checked: left prong differs"); a.click("#approve")
        a.wait_for_selector("text=No reports here")
    check("Console: approve refund clears the queue", admin_approve)
    def customer_sees():
        pg.goto(B + "/app/#/credits"); ready(pg); pg.wait_for_selector("[data-pack]"); txt = pg.inner_text("main")
        assert "10" in pg.inner_text(".card"), pg.inner_text(".card")  # 9 after the Hindi image, +1 approved refund
        assert txt.count("Refund: reported detail") == 2, "second refund in history"
    check("Jeweller gets the credit back and sees it in history", customer_sees)
    def metrics():
        a.click("nav button[data-tab=metrics]"); a.wait_for_selector(".metrics")
        txt = a.inner_text(".metrics")
        assert "₹249" in txt, "revenue"; assert "Paying accounts\t1" in txt or "Paying accounts\n1" in txt or re.search(r"Paying accounts\s+1", txt)
        a.screenshot(path=f"{SH}/11_admin_metrics.png", full_page=True)
    check("Console metrics: revenue ₹249, 1 paying account", metrics)
    def audit():
        a.click("nav button[data-tab=audit]"); a.wait_for_selector("h2:has-text('Access log')")
        txt = a.inner_text("table")
        assert "Viewed a customer image" in txt and "Resolved a report" in txt
    check("Console access log records image views and the decision", audit)
    def bad_token():
        x = lap.new_page(); x.goto(B + "/admin"); x.fill("#token", "wrong"); x.dispatch_event("#token", "change")
        x.wait_for_selector("text=isn't valid")
    check("Console rejects a wrong token", bad_token)

    # ---------------- Account deletion ----------------
    def delete_account():
        pg.goto(B + "/app/#/settings"); pg.click("[data-delete]"); pg.click("[data-yes]")
        pg.wait_for_selector("[data-start]")
    check("Delete account returns to onboarding", delete_account)
    b.close()

for status, name, why in results:
    print(f"{status}  {name}" + (f"\n      → {why}" if why else ""))
print(f"\n{sum(r[0]=='PASS' for r in results)} passed, {sum(r[0]=='FAIL' for r in results)} failed")
print("JavaScript errors:", errors or "none")
sys.exit(1 if any(r[0] == "FAIL" for r in results) or errors else 0)
