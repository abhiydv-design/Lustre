# Fidelity evaluation harness

Spec §10.5–10.7 and §11: before launch, prove on a documented test set that the app keeps the jewellery's details. Repeat the check after every pipeline or provider change.

**Results describe the test set, not every future image.** Don't claim perfect preservation from a handful of good samples (§10.7).

## The loop

```bash
cd backend
python -m evaluation init datasets/v1          # empty dataset: items.csv + COLUMNS.md + images/
# put phone photos in datasets/v1/images and fill items.csv (Excel or Google Sheets is fine)
python -m evaluation validate datasets/v1
python -m evaluation run datasets/v1 --name baseline --presets white,marble --repeats 2
python -m evaluation review evaluation/runs/baseline    # opens a review page at http://127.0.0.1:8765
python -m evaluation report evaluation/runs/baseline    # verdict + report.md
```

To learn the tool before real photos exist, run `python -m evaluation demo datasets/demo` (synthetic drawings, not real jewellery).

## 1. Build the dataset (§11.2, §11.3)

- **Size:** start with 10–20 real phone photos; that's what the gate expects by default.
- **One row per example** in `items.csv`. The columns follow the spec's record template; `COLUMNS.md` explains each one.
- **`must_keep`:** the most important column. List the details reviewers must check, separated by `;`, for example `5 stones in a row; 4 prongs per stone; milgrain edge`.
- **`rights`:** must be `owned` or `permission` before images go to an external AI provider (§11.4). The run refuses otherwise.
- **`split`:**
  - `evaluation` rows count toward the launch gate.
  - `development` rows are for experimenting and are excluded from the gate. If you ever train or tune on an image, it must not stay in `evaluation` (§11.5).
- **Coverage tags:** `reflective_metal`, `transparent_stone`, `fine_chain`, `dark`, `blurry` and others (see `COLUMNS.md`). The report checks that the set covers what §10.5 asks for.

Real customer photos may be confidential: keep `datasets/` and `runs/` out of git (they're in `.gitignore`) and off shared drives.

## 2. Run

`run` puts each example through the **same pipeline the app uses**, with whatever providers `.env` selects. For each output it records:
- time taken
- provider calls, and estimated cost if `EVAL_SCENE_COST_USD` and `EVAL_UPSCALE_COST_USD` are set
- pixel-match check and quality warnings
- the review image and the full-size file

The record also notes the code version and provider settings.

- **Use `--repeats 2` or more:** AI backgrounds vary between generations, and one lucky image proves little.
- **Comparing providers or settings** (the Phase 3 bake-off): do one run per configuration on the same dataset, then use `report --compare`.

## 3. Review (§10.5, §10.6)

The review page shows the original photo, the output (click to zoom to full size) and the `must_keep` list. For each output the reviewer answers:

- **Usable?** Visually good enough to sell with.
- **Did a product detail change?** If yes, mark the severity and pick what changed:
  - **Critical:** a materially different item, such as a changed stone count, a major setting change, an altered silhouette, or an invented component.
  - **Major:** a defining feature changes enough to misrepresent the product.
  - **Minor:** a small discrepancy that doesn't change the item's identity.
  - **No change:** recorded as *presentation only*.

Reviews save as you click, into `reviews.json` in the run folder.

## 4. Report and gate (§10.7)

`report` writes `report.md` and `summary.json`:
- outcome counts and rates
- results by category
- the most common kinds of change
- coverage gaps

It then gives a verdict:

- **PASS**: every threshold in `gate.toml` is met.
- **INCOMPLETE**: some outputs aren't reviewed yet.
- **FAIL**: lists every reason.

**The numbers in `gate.toml` are placeholders.** Deciding them is a founder decision the spec leaves open (§10.6, §10.7). Commit the file so every run is judged by the same rules.

`report <new> --compare <old>` lists regressions and improvements per example and preset (the worst outcome across repeats). Run it after every pipeline change, before shipping.

## What it has already found

On its first run, the demo's white-gold ring (D002, on a cream backdrop) came out tinted blue. Full white-balance correction mistook the cream backdrop for warm lighting. The correction is now partial and configurable (`WHITE_BALANCE_STRENGTH`, default 0.5). Use real photos and `--compare` to choose the value. Try runs at 0, 0.5 and 1.
