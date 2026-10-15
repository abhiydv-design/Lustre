# Jewellery Image Studio

A mobile app for Indian jewellery sellers: turn an ordinary phone photo into a professional catalogue image of the **actual** piece. AI builds only the background; the jeweller's real product pixels are kept and pasted back on top.

- `docs/product-spec.md`: **source of truth** for scope and requirements (v1.0).
- `docs/spec-gap-analysis.md`: what's built vs. the spec, and what's still open.
- `docs/data-retention.md`: what is stored and what deletion does.
- `backend/`: FastAPI API and image pipeline. See `backend/README.md`.
- `backend/app/routes/admin.py`: operations console at `/admin` (report review, §16 metrics, access log).
- `backend/evaluation/`: fidelity evaluation harness and launch quality gate. See `backend/evaluation/README.md`.
- `design/prototype/`: clickable phone prototype, one `.dc.html` file per screen. Live canvas: https://claude.ai/artifact/DNzXPxPCjmw7cqvjcExrem (its flow predates the per-generation credit model and needs a pass).

## The flow (v1)

Open app as a guest → create a product (category; name suggested) → add a photo → pick a catalogue look and ratio → see the credit cost → generate **one** image → compare with the original → accept, report an issue, or generate another → sign in with phone to save, download or buy credits.

## Run

```bash
cd backend && pip install -r requirements.txt && cp .env.example .env
uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest -q                       # 31 tests
```
