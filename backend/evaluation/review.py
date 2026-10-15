"""Local review page for a run (§10.5: reviewer decision and notes; §10.6 severity).

    python -m evaluation review <run_dir>      → http://127.0.0.1:8765

Reviews save to <run_dir>/reviews.json as you click, so several sessions can share one run folder.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

SEVERITIES = ["presentation_only", "minor", "major", "critical"]
CHANGE_TYPES = {
    "stones": "Stones added, removed or moved",
    "stone_look": "Stone shape or colour changed",
    "setting": "Prongs, bezel or setting changed",
    "metal": "Metal colour or finish changed",
    "chain_clasp": "Chain links or clasp changed",
    "shape": "Silhouette or proportions changed",
    "marking": "Engraving, logo or mark changed",
    "invented": "Detail invented that isn't in the photo",
    "substituted": "Looks like a different item",
    "cropped": "Required detail cut off by framing",
    "edge": "Cut-out edge problem (missing or extra bits)",
    "other": "Other product detail",
}


class ReviewIn(BaseModel):
    usable: bool | None = None            # visually usable for selling?
    detail_changed: bool | None = None
    change_types: list[str] = Field(default_factory=list)
    severity: str | None = None
    notes: str = Field("", max_length=2000)
    reviewer: str = Field("", max_length=60)


def validate(r: ReviewIn) -> dict:
    if r.severity and r.severity not in SEVERITIES:
        raise HTTPException(422, f"severity must be one of {SEVERITIES}")
    bad = [c for c in r.change_types if c not in CHANGE_TYPES]
    if bad:
        raise HTTPException(422, f"unknown change types {bad}")
    data = r.model_dump()
    if r.detail_changed is False:
        data.update(severity="presentation_only", change_types=[])
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    return data


def create_review_app(run_dir: Path) -> FastAPI:
    run_dir = Path(run_dir)
    lock = threading.Lock()
    app = FastAPI(title=f"Review {run_dir.name}")

    def read(name: str):
        return json.loads((run_dir / name).read_text(encoding="utf-8"))

    @app.get("/", response_class=HTMLResponse)
    def page():
        return PAGE

    @app.get("/api/run")
    def data():
        return {"run": read("run.json"), "results": read("results.json"), "reviews": read("reviews.json"),
                "severities": SEVERITIES, "change_types": CHANGE_TYPES}

    @app.post("/api/reviews/{output_id}")
    def save(output_id: str, body: ReviewIn):
        if output_id not in {r["output_id"] for r in read("results.json")}:
            raise HTTPException(404, "unknown output")
        entry = validate(body)
        with lock:
            reviews = read("reviews.json")
            reviews[output_id] = entry
            tmp = run_dir / "reviews.json.tmp"
            tmp.write_text(json.dumps(reviews, indent=2), encoding="utf-8")
            tmp.replace(run_dir / "reviews.json")
        return entry

    @app.get("/images/{name}")
    def image(name: str):
        path = (run_dir / "images" / name).resolve()
        if path.parent != (run_dir / "images").resolve() or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    return app


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fidelity review</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1b20;--muted:#5d5866;--line:#dcd8d2;--accent:#8a6a1f;--ok:#1f6b3a;--bad:#a1261b;--warn:#8a5a00;--chip:#efece6}
@media (prefers-color-scheme: dark){:root{--bg:#141217;--card:#1d1a21;--ink:#f1ece6;--muted:#b4abb9;--line:#3a3440;--accent:#d4b26a;--ok:#8fd0a5;--bad:#f0998f;--warn:#e7b65c;--chip:#2a262f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
h1{font-size:18px;margin:0 12px 0 0}
.progress{color:var(--muted)}
label.inline{display:flex;gap:6px;align-items:center;color:var(--muted)}
input[type=text],textarea{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px}
main{max-width:1200px;margin:0 auto;padding:20px;display:flex;flex-direction:column;gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) 320px;gap:16px}
@media (max-width:980px){.card{grid-template-columns:1fr 1fr}.form{grid-column:1/-1}}
@media (max-width:600px){.card{grid-template-columns:1fr}}
figure{margin:0;display:flex;flex-direction:column;gap:6px}
figure img{width:100%;border-radius:10px;border:1px solid var(--line);background:#fff;cursor:zoom-in}
figcaption{font-size:13px;color:var(--muted)}
.meta{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
.meta b{font-size:16px}.chip{background:var(--chip);border-radius:999px;padding:2px 10px;font-size:12px;color:var(--muted)}
.keep{grid-column:1/-1;font-size:14px}.keep ul{margin:4px 0 0 18px;padding:0}
.form{display:flex;flex-direction:column;gap:12px}
fieldset{border:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
legend{font-weight:600;margin-bottom:4px}
.seg{display:flex;flex-wrap:wrap;gap:6px}
.seg button,.types label{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;cursor:pointer;min-height:36px}
.seg button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.types{display:flex;flex-direction:column;gap:4px}.types label{border-radius:8px;display:flex;gap:8px;align-items:center}
.status{font-size:13px;color:var(--muted)}.done{color:var(--ok)}.failed{color:var(--bad)}.warn{color:var(--warn)}
dialog{border:none;padding:0;background:transparent;max-width:96vw;max-height:96vh}dialog img{max-width:96vw;max-height:92vh;display:block}
dialog::backdrop{background:#000c}
</style>
</head>
<body>
<header>
  <h1 id="title">Fidelity review</h1>
  <span class="progress" id="progress"></span>
  <label class="inline">Reviewer <input type="text" id="reviewer" size="12" placeholder="your name"></label>
  <label class="inline"><input type="checkbox" id="todo"> Only unreviewed</label>
</header>
<main id="list"><p>Loading…</p></main>
<dialog id="zoom"><img alt="Zoomed image" id="zoomimg"></dialog>
<script>
let DATA, REVIEWS;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const SEV = {presentation_only:"Presentation only", minor:"Minor", major:"Major", critical:"Critical"};
try { $("#reviewer").value = localStorage.getItem("reviewer") || ""; } catch (e) {}
$("#reviewer").addEventListener("change", e => { try { localStorage.setItem("reviewer", e.target.value); } catch (err) {} });
$("#todo").addEventListener("change", render);

async function load() {
  DATA = await (await fetch("/api/run")).json();
  REVIEWS = DATA.reviews;
  $("#title").textContent = "Fidelity review · " + DATA.run.name;
  render();
}
function complete(r){ return r && r.usable !== null && r.detail_changed !== null && (r.detail_changed === false || r.severity); }
function progress(){
  const ok = DATA.results.filter(r => r.status === "ok");
  const n = ok.filter(r => complete(REVIEWS[r.output_id])).length;
  $("#progress").textContent = `${n} of ${ok.length} reviewed`;
}
function render(){
  progress();
  const items = Object.fromEntries(DATA.run.items.map(i => [i.example_id, i]));
  const list = DATA.results.filter(r => !$("#todo").checked || (r.status === "ok" && !complete(REVIEWS[r.output_id])));
  $("#list").innerHTML = list.length ? "" : "<p>Nothing left to review.</p>";
  for (const r of list) $("#list").appendChild(card(r, items[r.example_id], REVIEWS[r.output_id] || {}));
}
function img(name, cap){ return name ? `<figure><img src="/images/${esc(name)}" alt="${esc(cap)}" data-full="${esc(name)}"><figcaption>${esc(cap)}</figcaption></figure>` : ""; }
function card(r, item, rv){
  const el = document.createElement("section"); el.className = "card"; el.id = r.output_id;
  const failed = r.status !== "ok";
  el.innerHTML = `
    <div class="meta"><b>${esc(r.example_id)}</b><span class="chip">${esc(r.category)}</span><span class="chip">${esc(r.preset)} · ${esc(r.aspect)} · run ${r.repeat}</span>
      ${(r.tags||[]).map(t=>`<span class="chip">${esc(t)}</span>`).join("")}
      ${failed ? `<span class="failed">Technical failure: ${esc(r.error)}</span>` : `<span class="status">pixel match ${r.pixel_match} · ${r.seconds}s</span>`}
      ${r.warning ? `<span class="warn">${esc(r.warning)}</span>` : ""}</div>
    <div class="keep"><b>Must not change:</b> ${item.must_keep.length ? "<ul>"+item.must_keep.map(k=>`<li>${esc(k)}</li>`).join("")+"</ul>" : "<em>not listed in the dataset</em>"}
      ${item.limitations ? `<div class="status">Photo limitations: ${esc(item.limitations)}</div>` : ""}</div>
    ${img(r.files.original, "Original phone photo")}
    ${failed ? "<div></div>" : `<figure><img src="/images/${esc(r.files.output)}" alt="Generated output" data-full="${esc(r.files.full)}"><figcaption>Output (click to see full size)</figcaption></figure>`}
    ${failed ? "<div class='form status'>Counted as a technical failure; nothing to review.</div>" : `
    <div class="form">
      <fieldset><legend>Visually usable for selling?</legend><div class="seg" data-k="usable">
        <button type="button" data-v="true">Yes</button><button type="button" data-v="false">No</button></div></fieldset>
      <fieldset><legend>Did any product detail change?</legend><div class="seg" data-k="detail_changed">
        <button type="button" data-v="false">No change</button><button type="button" data-v="true">Yes, changed</button></div></fieldset>
      <fieldset class="changed"><legend>Severity</legend><div class="seg" data-k="severity">
        ${["minor","major","critical"].map(s=>`<button type="button" data-v="${s}">${SEV[s]}</button>`).join("")}</div></fieldset>
      <fieldset class="changed"><legend>What changed?</legend><div class="types">
        ${Object.entries(DATA.change_types).map(([k,v])=>`<label><input type="checkbox" value="${k}"> ${esc(v)}</label>`).join("")}</div></fieldset>
      <textarea rows="2" placeholder="Notes" aria-label="Notes"></textarea>
      <div class="status" aria-live="polite"></div>
    </div>`}`;
  if (failed) return el;
  const state = {usable: rv.usable ?? null, detail_changed: rv.detail_changed ?? null, severity: rv.severity ?? null,
                 change_types: rv.change_types || [], notes: rv.notes || ""};
  const sync = () => {
    el.querySelectorAll(".seg").forEach(seg => seg.querySelectorAll("button").forEach(b => {
      b.setAttribute("aria-pressed", String(String(state[seg.dataset.k]) === b.dataset.v)); }));
    el.querySelectorAll(".changed").forEach(f => f.style.display = state.detail_changed === true ? "" : "none");
    el.querySelectorAll(".types input").forEach(i => i.checked = state.change_types.includes(i.value));
    el.querySelector("textarea").value = state.notes;
    const s = el.querySelector(".form .status");
    s.textContent = complete(REVIEWS[r.output_id]) ? "Saved ✓" : "Not complete yet";
    s.className = "status" + (complete(REVIEWS[r.output_id]) ? " done" : "");
  };
  const save = async () => {
    const body = {...state, reviewer: $("#reviewer").value};
    const res = await fetch(`/api/reviews/${encodeURIComponent(r.output_id)}`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
    if (res.ok) { REVIEWS[r.output_id] = await res.json(); Object.assign(state, {severity: REVIEWS[r.output_id].severity, change_types: REVIEWS[r.output_id].change_types}); }
    sync(); progress();
  };
  el.querySelectorAll(".seg").forEach(seg => seg.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    const v = b.dataset.v; state[seg.dataset.k] = v === "true" ? true : v === "false" ? false : v; save(); }));
  el.querySelectorAll(".types input").forEach(i => i.addEventListener("change", () => {
    state.change_types = [...el.querySelectorAll(".types input:checked")].map(x => x.value); save(); }));
  el.querySelector("textarea").addEventListener("change", e => { state.notes = e.target.value; save(); });
  sync();
  return el;
}
document.addEventListener("click", e => {
  const i = e.target.closest("img[data-full]"); if (!i) return;
  $("#zoomimg").src = "/images/" + i.dataset.full; $("#zoom").showModal(); });
$("#zoom").addEventListener("click", () => $("#zoom").close());
load();
</script>
</body>
</html>
"""
