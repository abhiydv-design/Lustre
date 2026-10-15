# Lustre backend

API and image pipeline for the jeweller photo app (prototype screens: Home → Upload → Choose a look → Generating → Results → Credits).

## The one rule

**The jewellery is never generated.** AI makes only the scene *around* the piece; the jeweller's real product pixels are pasted back on top at the end, and every output is checked against the source (`fidelity` ≥ 0.995, or the job fails rather than ship an altered piece).

```
upload ─► cut-out (BiRefNet) ─► white balance from the photo's own background
       ─► scene inpainted around a masked product (FLUX Fill) ─► soft contact shadow
       ─► paste ORIGINAL product ─► fidelity check ─► free watermarked 1024px preview

download (1 credit) ─► upscale the SCENE ONLY to 4K (Real-ESRGAN)
                    ─► paste product from the full-resolution source ─► check ─► 4K PNG
```

Why previews first, 4K on download: the expensive upscaling only runs for photos someone pays for, which matches "pay only for downloads" in the app. "White catalog" uses no AI at all (pure #FFFFFF + shadow), so it costs nothing to produce.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill it in; export it or use a tool like direnv
uvicorn app.main:app --reload # API docs at http://localhost:8000/docs
pytest -q                     # 7 end-to-end tests, run fully offline with mock providers
```

To try it without any API keys, set `SCENE_PROVIDER=mock`, `UPSCALE_PROVIDER=lanczos`, `CUTOUT_PROVIDER=threshold`.

## Endpoints, by screen

| Screen | Endpoint |
|---|---|
| Login (dev only) | `POST /auth/dev-login` → bearer token |
| Home | `GET /me` (credits), `GET /shoots` (recent shoots) |
| Upload / Choose a look | `GET /catalog`, `POST /shoots` (multipart: `jewellery_type`, `metal`, 1–4 `files`) |
| Generate | `POST /shoots/{id}/jobs` `{style, format, count}` |
| Generating | `GET /jobs/{id}`: poll every 1–2 s; `steps` mirrors the progress list |
| Results | `GET /variations/{id}/preview`, `GET /variations/{id}/original` (compare) |
| Download 4K | `POST /variations/{id}/download` (charges once), then poll `GET` until 200 |
| Credits | `GET /credits/packs`, `POST /payments/orders`, `POST /payments/webhook` |

The 4K response carries `X-Fidelity` and, when the source photo was too small, `X-Quality-Warning` (show it to the jeweller).

## Things to verify before going live

- **Model inputs.** I wrote the Replicate model names and input fields (`image`, `mask`, `prompt`, `seed`, `output_format` for FLUX Fill; `image`, `scale`, `face_enhance` for Real-ESRGAN) from memory. Check them against each model's page on replicate.com, and pin exact versions (`owner/name:version`). All model calls live in `app/pipeline/providers.py`, so switching to fal.ai or a self-hosted model is one class.
- **Prices.** Pack prices are blank in `.env.example` on purpose; ordering refuses until they're set.
- **Razorpay.** Credits are only added by the signed webhook (`order.paid` / `payment.captured`), idempotently. Confirm the event names you enable in the Razorpay dashboard match.

## Before real customers

- Replace dev login with phone OTP.
- Move `BackgroundTasks` to a real queue (RQ, Celery or Arq) and run workers separately; a 4K render takes 10–30 s with hosted models.
- Swap local disk (`app/storage.py`) for S3 or Cloudflare R2, and serve images via signed URLs.
- SQLite → Postgres (just change `DATABASE_URL`).
- Shadows are a simple silhouette shadow; reflections on glossy surfaces (marble, mirror) are the next quality upgrade.
- "On model" is disabled (`available=False`) until there's pose-aware placement and occlusion.

## Layout

```
app/
  main.py, config.py, db.py, deps.py, credits.py, storage.py
  routes/   account.py · studio.py · payments.py
  pipeline/ run.py (orchestrator) · cutout.py · prepare.py · geometry.py
            providers.py (AI models) · composite.py (shadow, paste, fidelity) · styles.py (prompts)
tests/      end-to-end flow with a synthetic ring photo
```
