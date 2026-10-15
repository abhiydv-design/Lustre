# Lustre

Studio-quality 4K photos of a jeweller's own pieces, from a phone photo. The jewellery is never redrawn by AI: only the scene around it is generated, and the original product pixels are pasted back on top.

- `backend/`: FastAPI API and image pipeline (cut-out, scene, shadow, 4K). See `backend/README.md`.
- `design/prototype/`: clickable phone prototype, one `.dc.html` file per screen, laid out by `canvas.json`. Live canvas: https://claude.ai/artifact/DNzXPxPCjmw7cqvjcExrem

## The flow

Open app → add photos → see photos → tap download. Everything else is optional or automatic: guest start, metal detection, generation starting on upload, 4K pre-rendered, one-tap "download all", and buy-then-deliver when credits run out. Details in `backend/README.md`.

## Run

```bash
cd backend && pip install -r requirements.txt && cp .env.example .env
uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest -q
```
