# Jewellery Image Studio

A mobile app for Indian jewellery sellers: turn an ordinary phone photo into a professional catalogue image of the **actual** piece. AI builds only the background; the jeweller's real product pixels are kept and pasted back on top.

- `docs/product-spec.md`: **source of truth** for scope and requirements (v1.0).
- `docs/spec-gap-analysis.md`: what's built vs. the spec, and what's still open.
- `docs/data-retention.md`: what is stored and what deletion does.
- `backend/`: FastAPI API and image pipeline. See `backend/README.md`.
- `backend/app/routes/admin.py`: operations console at `/admin` (report review, §16 metrics, access log).
- `backend/evaluation/`: fidelity evaluation harness and launch quality gate. See `backend/evaluation/README.md`.
- `backend/app/web/`: **the jeweller app**, a mobile web app in English and Hindi, served at `/app` and wired to the real API. Open it on any phone browser; it can be added to the home screen.
- `design/prototype/`: the original clickable prototype (canvas: https://claude.ai/artifact/DNzXPxPCjmw7cqvjcExrem). Superseded by the real app; kept for reference.

## The flow (v1)

Open app as a guest → create a product (category; name suggested) → add a photo → pick a catalogue look and ratio → see the credit cost → generate **one** image → compare with the original → accept, report an issue, or generate another → sign in with phone to save, download or buy credits.

## Run

```bash
git clone https://github.com/abhiydv-design/Lustre.git
cd Lustre
python start.py           # or: python start.py --phone   to open it on your phone
```

Everything else (phone links, real AI, Docker, hosting online) is in **[RUN.md](RUN.md)**.
