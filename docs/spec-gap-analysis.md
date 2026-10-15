# Spec vs. current build

Compares `docs/product-spec.md` (the source of truth) with the code. Updated after the spec-alignment pass.

## Founder decisions that refine the spec

- **Sign-in:** guest first; phone sign-in at the first save, download or purchase. The spec said sign-in comes first. Everything made as a guest is kept on sign-in.
- **Credits:** per generation, one image at a time, cost shown and confirmed first (as in the spec). Downloads are free.

## Closed in this pass

| Spec | Now |
|---|---|
| §9.3 Catalogue: name, category, optional fields, rename, delete, image history | `/products` CRUD, suggested names, history per product |
| §9.4 One image by default, cost before generating, extra variations charged separately | `quote` + `confirm_cost`; separate first and additional costs |
| §9.5 Accept, report detail issue (8 categories), report quality issue (6 categories), stored for analysis | `/accept`, `/report`; reports keep a snapshot after image deletion |
| §12.3 Refund for reported detail errors, guarded against duplicates and abuse | Once per image, monthly auto-limit, then manual review |
| §9.7 / §19 No lost or duplicate charges on failure or interruption | Automatic technical refunds, restart recovery, `Idempotency-Key` |
| §9.7 Understandable transactions | `GET /me/credits` with notes |
| §9.8 / §14 Real deletion, documented | File deletion tested; `docs/data-retention.md` |
| §7 V1 = catalogue and marketplace only | Velvet, Silk, Festive and On-model switched off |
| §13.2 Only verified marketplace presets | Register in `marketplaces.py`; ships empty |
| §10.5–10.7, §11 Fidelity test design, severity, launch gate, dataset template, rights checks, regression comparison | `backend/evaluation/` harness: dataset CSV, runner, review page, gate report |
| §16 Metrics (usage, quality by category/material/photo condition/preset, business); §14 governed support access; manual review of refund claims (§18 #12 support process) | `/admin` console: report queue, metrics, audit log |
| §8 Core journey, §9.1 onboarding, §9.6 share, §15 English and Hindi | Mobile web app at `/app` |
| §4 Don't overclaim | API notice asks the user to check details; prototype copy softened |
| §15 Hindi | Labels for categories and presets are in `/catalog`. Full interface text belongs in the app |

## Still open

- **Marketplaces:** pick the first ones, verify their requirements, and add them to `marketplaces.py` (§13, §18 #2).
- **Export details:** exact sizes, file types and limits for catalogue exports; the current 4K ratios are working defaults (§9.6, §18 #3).
- **Fidelity evaluation:** the harness is built (`backend/evaluation/`). Still needed: the real 10–20 photo dataset with rights confirmed, the gate thresholds in `gate.toml`, and a reviewer procedure (who reviews, and whether two reviewers must agree).
- **Mobile app:** a working mobile web app now covers the full v1 journey in English and Hindi (`/app`). Still open:
  - native review of the Hindi text;
  - offline support (service worker) and app-store packaging, if you want them;
  - testing with real jewellers on their own phones (Phase 4).
- **Infrastructure:** an SMS gateway with DLT registration, a job queue, cloud storage, Postgres, and database migrations (Alembic).
- **Support process:** who works the report queue, how fast, and the written policy for staff access to images (§14, §18 #12). The console enforces and logs access, but the policy needs writing.
- **Retention decisions** listed in `docs/data-retention.md`.
- **Pricing:** trial size, pack sizes and prices in INR (§12.4).
