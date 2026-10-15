# Jewellery Image Studio — backend

API and image pipeline for the mobile app. Requirements come from `../docs/product-spec.md`; open gaps are tracked in `../docs/spec-gap-analysis.md`.

## How an image is made

**The jewellery is never generated.** AI makes only the background around the piece; the jeweller's real product pixels are pasted back on top. A pixel check (`X-Pixel-Match` ≥ 0.995) confirms the pasted pixels are untouched. It can't catch a bad cut-out, such as a clear stone dropped from the mask, so every image still goes to the user for review (spec §9.5).

```
photo upload ─► cut-out (BiRefNet) + metal detection + white balance   (in the background, right after upload)
generate     ─► background around the masked product (FLUX Fill, or a flat colour for White/Grey)
             ─► contact shadow ─► paste ORIGINAL product ─► upscale background to full size
             ─► re-paste product from the full-resolution photo ─► pixel check ─► preview + full file
```

## Product rules implemented

| Rule | Spec |
|---|---|
| **One image per request.** The cost is quoted first (`GET /products/{id}/quote`) and the request must echo it (`confirm_cost`), so nobody is charged an amount they didn't see. | §4.5, §9.4, §9.7 |
| **Credits are spent per generation.** First image and additional variations have separate costs (`INITIAL_GENERATION_COST`, `ADDITIONAL_GENERATION_COST`). Downloads are free. | §12.2 |
| **Technical failures refund automatically**, including generations interrupted by a crash or restart. | §9.7, §19 |
| **Reported detail errors refund automatically**, once per image, up to `QUALITY_REFUND_AUTO_LIMIT` per 30 days; beyond that the report goes to manual review. Visual-quality reports are recorded, not refunded. | §12.3 |
| **Retries never double-charge:** send an `Idempotency-Key` header with each Generate tap. | §19 |
| **Guest first.** Guests can create products, generate and review (previews carry a "Sign in to save" mark). Saving, downloading and buying need phone sign-in; signing in keeps everything they made. | founder decision |
| **Trial credits once per phone number**, even if the account is deleted and recreated. | §12.4 |
| **V1 looks only:** White, Soft grey, Warm beige, Marble. Velvet, Silk, Festive and On-model are defined but switched off. | §7 |
| **Marketplace presets** appear only once verified, with a source and date, in `app/pipeline/marketplaces.py`. None are verified yet. | §13.2 |
| **Deletion removes files**, not just database rows. See `../docs/data-retention.md`. | §9.8, §14 |

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in, then export (or use direnv)
uvicorn app.main:app --reload   # API docs at http://localhost:8000/docs
pytest -q                       # 34 tests (API, app, operations console, evaluation harness), offline with mock providers
```

No API keys needed to try it: `SCENE_PROVIDER=mock UPSCALE_PROVIDER=lanczos CUTOUT_PROVIDER=threshold`. With `DEV_MODE=1`, sign-in codes are returned in the API response.

## The jeweller app (`/app`)

A mobile web app in `app/web/`: plain HTML, CSS and JavaScript, with no build step. It's served from the same origin as the API.

**What it covers:**
- **Getting started:** onboarding with photo tips and language choice, then guest start.
- **Catalogue:** products and photos, plus a second angle from the gallery.
- **Making an image:** choose a look and size with the cost shown first; live progress; compare with the original.
- **After the image:** save, download, share (the phone's share sheet, for WhatsApp and Instagram), report a problem, and delete.
- **Account:** credits and history, buying credits, phone sign-in when needed, language switch, and account deletion.

**How it behaves:**
- **English and Hindi:** all text is in `app/web/i18n.js`, and the test suite checks both languages have every key. Have the Hindi reviewed by a native speaker from your audience before launch.
- **Signing in:** when the server answers `sign_in_required` or `needs_credits`, the app shows sign-in or the credit packs, then finishes what the jeweller was doing.
- **Payments:** with Razorpay keys set, it opens Razorpay Checkout and waits for the webhook to add credits. Without keys (test mode), payment completes instantly.
- **Browser check:** `scripts/e2e_app.py` walks the whole journey in a headless phone browser.

## Operations console (`/admin`)

For the team, not jewellers. Set `ADMIN_TOKENS=name:long-random-token,...` and open `/admin`.

- **Reports:**
  - Detail claims beyond the automatic refund limit wait here.
  - Staff compare the original and the output (hover to magnify), see the customer's history, then approve or decline. Declining requires a message to the customer.
  - The customer sees the outcome on the image, and approved refunds appear in their credit history.
- **Metrics:** every spec §16 usage, quality and business measure, for 7, 30, 90 or 365 days. Quality is also broken down by category, metal, look and photo condition. Set `COST_PER_SCENE_INR` and `COST_PER_UPSCALE_INR` so the cost per image is filled in.
- **Access log:** every action, and every time staff open a customer image.
- **Access to customer images (spec §14):**
  - Staff can only open images through a report.
  - Phone numbers are never shown; customers appear by a short id.
  - Without `ADMIN_TOKENS`, `/admin` doesn't exist.

The app should send share events with `POST /generations/{id}/events` `{"type": "share", "channel": "whatsapp"}`, so the share rate is measured.

## Fidelity evaluation

The launch quality gate (spec §10.5–10.7) has its own tool in `evaluation/`. See `evaluation/README.md`.

## Endpoints, by screen

| Screen | Endpoint |
|---|---|
| First open | `POST /auth/start` → guest token + trial credits |
| Sign in (at first save or purchase) | `POST /auth/otp/request` `{phone}` → `POST /auth/otp/verify` `{phone, code}`; send the guest token to keep their work |
| Catalogue | `GET /products`, `POST /products` `{category, name?, sku?, metal?, stone?, collection?, notes?}`, `GET/PATCH/DELETE /products/{id}` |
| Add photos | `POST /products/{id}/photos` (multipart `files`), `GET/DELETE /photos/{id}` |
| Choose a look | `GET /catalog` (categories, presets, ratios, costs and report categories, with Hindi labels), `GET /products/{id}/quote` |
| Generate | `POST /products/{id}/generations` `{preset, aspect_ratio, confirm_cost, photo_id?}` + `Idempotency-Key` header |
| Progress | `GET /generations/{id}`: poll every 1–2 s |
| Review | `GET /generations/{id}/preview`, `GET /generations/{id}/original` (side by side), `POST /generations/{id}/accept`, `POST /generations/{id}/report` `{kind, category, note}` |
| Download / share | `GET /generations/{id}/download` (signed in; free) |
| Delete | `DELETE /generations/{id}`, `DELETE /photos/{id}`, `DELETE /products/{id}`, `DELETE /me` |
| Credits | `GET /me/credits` (balance + history), `GET /credits/packs`, `POST /payments/orders` (signed in), `POST /payments/webhook` |

Errors the app should handle by `detail.code`:
- `sign_in_required` (403): show the phone sign-in screen.
- `needs_credits` (402): show the packs. If `sign_in_required_to_buy` is true, sign in first.
- `cost_changed` (409): show the new cost and ask again.
- `preset_unavailable` / `marketplace_unavailable` (422): the look or preset isn't offered yet.
- Failed generations carry a plain-language `message` that already says the credit was returned.

## Before launch

- **Verify model inputs.** Check the Replicate model names and input fields against each model's page, and pin versions. All model calls live in `app/pipeline/providers.py`.
- **Add an SMS gateway** in `app/sms.py`. Indian SMS needs a DLT-registered sender ID and template.
- **Set real prices** and `SECRET_KEY`, and turn `DEV_MODE=0`. The app refuses to start without a real key in production.
- **Database migrations:** add Alembic before the first production deploy. New columns, like the ones the console added, don't apply to an existing database automatically.
- **Infrastructure:** a real job queue instead of `BackgroundTasks`, S3 or R2 storage, and Postgres.
- **Fill in marketplace presets** once their requirements are verified.
