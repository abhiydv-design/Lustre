"""The /admin page: report review with a loupe, §16 metrics, audit log. One self-contained file."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Studio operations</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{
  --ground:#eef0f2; --surface:#fbfbfa; --ink:#1c2126; --muted:#56606b; --line:#d5dae0;
  --sapphire:#23468c; --sapphire-ink:#fff; --approve:#1e6b46; --decline:#9b2c2c; --flag:#8a5300;
  color-scheme: light;
}
@media (prefers-color-scheme: dark){:root{
  --ground:#15181c; --surface:#1e2228; --ink:#e8ebee; --muted:#a2acb7; --line:#343a42;
  --sapphire:#8fa9e6; --sapphire-ink:#10141a; --approve:#7fcca3; --decline:#f09b9b; --flag:#e6b45e;
  color-scheme: dark;
}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--ground);color:var(--ink)}
body{font:16px/1.5 "Atkinson Hyperlegible",system-ui,-apple-system,"Segoe UI",sans-serif;font-variant-numeric:tabular-nums}
button,input,textarea,select{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--sapphire);outline-offset:2px}
.top{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;padding:14px 24px;border-bottom:1px solid var(--line);background:var(--surface)}
.top h1{font-size:19px;margin:0}
nav{display:flex;gap:4px}
nav button{border:none;background:none;padding:8px 14px;border-radius:8px;cursor:pointer;color:var(--muted);font-weight:700}
nav button[aria-current=page]{background:var(--ground);color:var(--ink)}
.who{margin-left:auto;display:flex;gap:8px;align-items:center;color:var(--muted);font-size:14px}
.who input{width:220px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--ground)}
main{padding:24px;max-width:1400px;margin:0 auto}
.empty{max-width:60ch;color:var(--muted)}
.err{color:var(--decline);font-weight:700}

/* Review */
.review{display:grid;grid-template-columns:280px minmax(0,1fr);gap:24px;align-items:start}
@media (max-width:900px){.review{grid-template-columns:1fr}}
.queue{display:flex;flex-direction:column;gap:2px;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:6px;position:sticky;top:16px}
.queue h2{font-size:15px;margin:8px 10px;color:var(--muted)}
.queue select{margin:0 10px 8px;padding:6px;border:1px solid var(--line);border-radius:8px;background:var(--ground)}
.queue button{display:block;width:100%;text-align:left;border:none;background:none;padding:10px;border-radius:8px;cursor:pointer}
.queue button[aria-current=true]{background:var(--ground)}
.queue .what{font-weight:700;display:block}
.queue .when{font-size:13px;color:var(--muted)}
.case{display:flex;flex-direction:column;gap:20px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:640px){.pair{grid-template-columns:1fr}}
figure{margin:0;display:flex;flex-direction:column;gap:8px}
.stage{position:relative;border-radius:10px;overflow:hidden;background:var(--ground);border:1px solid var(--line);cursor:crosshair;aspect-ratio:1/1;display:flex;align-items:center;justify-content:center}
.stage img{max-width:100%;max-height:100%;display:block}
.stage .gone{color:var(--muted);padding:24px;text-align:center}
.lens{position:absolute;width:220px;height:220px;border-radius:50%;pointer-events:none;border:3px solid var(--sapphire);box-shadow:0 0 0 1px #fff8;background-repeat:no-repeat;display:none}
figcaption{font-size:14px;color:var(--muted)}
.claim{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:24px}
@media (max-width:760px){.claim{grid-template-columns:1fr}}
.claim h2{font-size:22px;margin:0 0 4px}
.claim .note{margin:10px 0 0;padding-left:14px;border-left:3px solid var(--line);max-width:60ch}
dl.signals{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;margin:0}
dl.signals dt{color:var(--muted)}
dl.signals dd{margin:0;font-weight:700}
.flag{color:var(--flag)}
.decide{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;display:flex;flex-direction:column;gap:12px}
.decide label{display:flex;flex-direction:column;gap:6px;font-weight:700}
.decide textarea{border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--ground);font-weight:400;resize:vertical}
.decide .hint{font-weight:400;color:var(--muted);font-size:14px}
.actions{display:flex;flex-wrap:wrap;gap:10px}
.actions button{border:none;border-radius:10px;padding:12px 20px;font-weight:700;cursor:pointer;min-height:48px}
.approve{background:var(--approve);color:var(--surface)}
.decline{background:none;border:2px solid var(--decline) !important;color:var(--decline)}
.done{font-weight:700}
#result:empty{display:none}
.decide .hint{display:block}

/* Metrics */
.window{display:flex;gap:8px;align-items:center;margin-bottom:20px}
.window select{padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px;align-items:start}
section.block{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 20px}
section.block h2{font-size:18px;margin:0 0 10px}
table{width:100%;border-collapse:collapse}
td,th{padding:7px 0;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
td.n,th.n{text-align:right;padding-left:12px}
tr:last-child td{border-bottom:none}
.wide{grid-column:1/-1;overflow-x:auto}
.wide table{width:auto;min-width:min(640px,100%)}
.wide td.n,.wide th.n{padding-left:40px}
.foot{font-size:14px;color:var(--muted);margin-top:8px}
@media (prefers-reduced-motion: no-preference){.lens{transition:opacity .1s}}
</style>
</head>
<body>
<header class="top">
  <h1>Studio operations</h1>
  <nav aria-label="Sections">
    <button data-tab="review" aria-current="page">Reports</button>
    <button data-tab="metrics">Metrics</button>
    <button data-tab="audit">Access log</button>
  </nav>
  <div class="who"><label for="token">Admin token</label><input id="token" type="password" autocomplete="off"></div>
</header>
<main id="main"><p class="empty">Enter your admin token to start.</p></main>

<script>
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct = x => x === null || x === undefined ? "—" : (x * 100).toFixed(1) + "%";
const num = x => x === null || x === undefined ? "—" : x;
let tab = "review", status = "under_review", current = null, reports = [], blobs = [];
try { $("#token").value = sessionStorage.getItem("adminToken") || ""; } catch (e) {}
$("#token").addEventListener("change", e => { try { sessionStorage.setItem("adminToken", e.target.value); } catch (err) {} show(); });
document.querySelectorAll("nav button").forEach(b => b.addEventListener("click", () => {
  tab = b.dataset.tab;
  document.querySelectorAll("nav button").forEach(x => x.toggleAttribute("aria-current", x === b));
  document.querySelectorAll("nav button[aria-current]").forEach(x => x.setAttribute("aria-current", "page"));
  show();
}));

async function api(path, opts = {}) {
  const res = await fetch(path, {...opts, headers: {...(opts.headers || {}), Authorization: "Bearer " + $("#token").value}});
  if (res.status === 401) throw new Error("That admin token isn't valid.");
  if (!res.ok) { let d = ""; try { d = (await res.json()).detail; } catch (e) {} throw new Error(d || ("Request failed: " + res.status)); }
  return res;
}
function fail(e) { $("#main").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
function show() {
  if (!$("#token").value) { $("#main").innerHTML = '<p class="empty">Enter your admin token to start.</p>'; return; }
  ({review: showReview, metrics: showMetrics, audit: showAudit})[tab]().catch(fail);
}

/* ---------- Reports ---------- */
const STATUS = {under_review: "Waiting for review", refunded: "Refunded", declined: "Declined", all: "All reports"};
async function showReview() {
  reports = await (await api(`/admin/api/reports?status=${status}`)).json();
  if (!reports.find(r => r.id === current)) current = reports[0]?.id || null;
  $("#main").innerHTML = `<div class="review">
    <aside class="queue" aria-label="Reports">
      <h2>${reports.length} ${status === "under_review" ? "waiting" : "shown"}</h2>
      <select id="status" aria-label="Show">${Object.entries(STATUS).map(([k,v]) => `<option value="${k}" ${k===status?"selected":""}>${v}</option>`).join("")}</select>
      ${reports.map(r => `<button data-id="${r.id}" aria-current="${r.id === current}">
        <span class="what">${esc(r.category_label)}</span>
        <span class="when">${esc(r.product_category)}, ${esc(r.preset)}, ${new Date(r.created_at).toLocaleDateString()}</span></button>`).join("")}
    </aside>
    <div id="case" class="case">${reports.length ? "" : '<p class="empty">No reports here. New claims beyond the automatic refund limit will appear in this list.</p>'}</div>
  </div>`;
  $("#status").addEventListener("change", e => { status = e.target.value; current = null; show(); });
  document.querySelectorAll(".queue button").forEach(b => b.addEventListener("click", () => { current = b.dataset.id; showReview().catch(fail); }));
  if (current) await showCase(reports.find(r => r.id === current));
}

async function imageFor(r, which, available) {
  if (!available) return null;
  try { const url = URL.createObjectURL(await (await api(`/admin/api/reports/${r.id}/image/${which}`)).blob()); blobs.push(url); return url; }
  catch (e) { return null; }
}
function stage(url, label) {
  return `<figure><div class="stage" tabindex="0" aria-label="${esc(label)}. Hover to magnify.">
      ${url ? `<img src="${url}" alt="${esc(label)}"><div class="lens"></div>` : `<p class="gone">The customer deleted this image.</p>`}
    </div><figcaption>${esc(label)}</figcaption></figure>`;
}
function loupe(el) {
  const img = el.querySelector("img"), lens = el.querySelector(".lens"); if (!img) return;
  const Z = 3;
  const move = e => {
    const r = img.getBoundingClientRect(), box = el.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    if (x < 0 || y < 0 || x > r.width || y > r.height) { lens.style.display = "none"; return; }
    lens.style.display = "block";
    lens.style.left = (e.clientX - box.left - 110) + "px"; lens.style.top = (e.clientY - box.top - 110) + "px";
    lens.style.backgroundImage = `url(${img.src})`;
    lens.style.backgroundSize = `${r.width * Z}px ${r.height * Z}px`;
    lens.style.backgroundPosition = `${-(x * Z - 110)}px ${-(y * Z - 110)}px`;
  };
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerleave", () => lens.style.display = "none");
}
async function showCase(r) {
  blobs.forEach(URL.revokeObjectURL); blobs = [];
  const [orig, out] = await Promise.all([imageFor(r, "original", r.original_available), imageFor(r, "output", r.image_available)]);
  const s = r.signals;
  const heavy = s.detail_reports_30d >= 3 || (s.images_made && s.detail_reports_30d / s.images_made > 0.5);
  const open = r.status === "under_review";
  $("#case").innerHTML = `
    <div class="pair">${stage(orig, "Customer's original photo")}${stage(out, "Generated image")}</div>
    <div class="claim">
      <div>
        <h2>${esc(r.category_label)}</h2>
        <div>${esc(r.product_category)} on ${esc(r.preset)}. Reported ${new Date(r.created_at).toLocaleString()}.
          ${r.pixel_match ? `Pixel check passed (${r.pixel_match.toFixed(4)}). It only confirms the cut-out was pasted unchanged; it can't catch a stone or prong lost during the cut-out, so judge by the images.` : ""}</div>
        ${r.note ? `<p class="note">${esc(r.note)}</p>` : `<p class="note">No note from the customer.</p>`}
      </div>
      <dl class="signals" aria-label="Customer history">
        <dt>Customer</dt><dd>${esc(s.customer)}${s.signed_in ? "" : " (guest)"}</dd>
        <dt>Account age</dt><dd>${s.account_age_days} days</dd>
        <dt>Images made</dt><dd>${s.images_made} (${s.images_accepted} accepted)</dd>
        <dt>Detail reports, 30 days</dt><dd class="${heavy ? "flag" : ""}">${s.detail_reports_30d}${heavy ? ", unusually high" : ""}</dd>
        <dt>Quality refunds, 30 days</dt><dd>${s.quality_refunds_30d}</dd>
        <dt>Credits bought</dt><dd>${s.credits_bought}</dd>
      </dl>
    </div>
    <div class="decide">
      ${open ? `
      <label>Message to the customer
        <span class="hint">Required when declining. Say what you checked.</span>
        <textarea id="msg" rows="2" maxlength="500"></textarea></label>
      <label>Internal note <span class="hint">Only the team sees this.</span>
        <textarea id="note" rows="2" maxlength="1000"></textarea></label>
      <div class="actions">
        <button class="approve" id="approve">Approve refund</button>
        <button class="decline" id="decline">Decline</button>
      </div><p id="result" role="status"></p>` : `
      <p class="done">${esc(STATUS[r.status] || r.status)}${r.resolved_by ? ` by ${esc(r.resolved_by)} on ${new Date(r.resolved_at).toLocaleString()}` : ""}.</p>
      ${r.user_message ? `<p>Customer was told: “${esc(r.user_message)}”</p>` : ""}
      ${r.internal_note ? `<p class="hint">Internal note: ${esc(r.internal_note)}</p>` : ""}`}
    </div>`;
  document.querySelectorAll(".stage").forEach(loupe);
  if (open) for (const d of ["approve", "decline"]) $("#" + d).addEventListener("click", async () => {
    try {
      await api(`/admin/api/reports/${r.id}/resolve`, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({decision: d, user_message: $("#msg").value, internal_note: $("#note").value})});
      current = null; await showReview();
    } catch (e) { $("#result").innerHTML = `<span class="err">${esc(e.message)}</span>`; }
  });
}

/* ---------- Metrics ---------- */
let days = 30;
function rows(list) { return `<table>${list.map(([k, v]) => `<tr><td>${k}</td><td class="n">${v}</td></tr>`).join("")}</table>`; }
function breakdown(title, data) {
  const keys = Object.keys(data || {});
  return `<section class="block wide"><h2>${title}</h2>${keys.length ? `<table>
    <tr><th></th><th class="n">Images</th><th class="n">Accepted</th><th class="n">Detail complaints</th><th class="n">Technical failures</th></tr>
    ${keys.map(k => { const r = data[k]; return `<tr><td>${esc(k.replaceAll("_", " "))}</td><td class="n">${r.generations}</td>
      <td class="n">${pct(r.accepted_rate)}</td><td class="n">${pct(r.detail_complaint_rate)}</td><td class="n">${pct(r.technical_failure_rate)}</td></tr>`; }).join("")}
  </table>` : '<p class="empty">No images in this period.</p>'}</section>`;
}
async function showMetrics() {
  const m = await (await api(`/admin/api/metrics?days=${days}`)).json();
  const u = m.usage, q = m.quality, b = m.business;
  $("#main").innerHTML = `<div class="window"><label for="days">Period</label>
    <select id="days">${[7, 30, 90, 365].map(d => `<option value="${d}" ${d===days?"selected":""}>Last ${d} days</option>`).join("")}</select></div>
    <div class="metrics">
    <section class="block"><h2>Usage</h2>${rows([
      ["New accounts", u.new_accounts],
      ["Median time to first upload", u.median_minutes_account_to_first_upload === null ? "—" : u.median_minutes_account_to_first_upload + " min"],
      ["Median time to first result", u.median_minutes_to_first_result === null ? "—" : u.median_minutes_to_first_result + " min"],
      ["Products with photos that got an image", pct(u.upload_to_generation_conversion)],
      ["Images accepted", pct(u.accepted_image_rate)],
      ["Images downloaded", pct(u.download_rate)],
      ["Images shared", pct(u.share_rate)],
      ["Products with more than one image", pct(u.repeat_generation_rate)],
      ["Products used again on another day", pct(u.products_reused_on_another_day)],
      ["Products per active user", num(u.products_per_active_user)],
      ["Accepted images per active user", num(u.accepted_images_per_active_user)]])}
      ${Object.keys(u.shares_by_channel).length ? `<p class="foot">Shares: ${Object.entries(u.shares_by_channel).map(([k,v]) => `${esc(k)} ${v}`).join(", ")}</p>` : ""}</section>
    <section class="block"><h2>Quality</h2>${rows([
      ["Images made", `${q.done} of ${q.generations}`],
      ["Product-detail complaints", pct(q.product_detail_complaint_rate)],
      ["Visual-quality complaints", pct(q.visual_quality_complaint_rate)],
      ["Technical failures", pct(q.technical_failure_rate)],
      ["Quality refunds", pct(q.quality_refund_rate)],
      ["Judged usable by the customer", pct(q.user_judged_usable_rate)],
      ["Reports waiting for review", q.reports_waiting_for_review]])}
      <p class="foot">Critical and major error rates come from the evaluation harness, where people review every image.</p></section>
    <section class="block"><h2>Business</h2>${rows([
      ["Trial accounts that made an image", pct(b.trial_activation_rate)],
      ["Of those, bought credits", pct(b.trial_to_purchase_conversion)],
      ["Paying accounts", b.paying_accounts],
      ["Bought more than once", pct(b.repeat_purchase_rate)],
      ["Revenue", "₹" + b.revenue_inr.toLocaleString("en-IN")],
      ["Revenue per paying account", b.revenue_per_paying_account_inr === null ? "—" : "₹" + b.revenue_per_paying_account_inr],
      ["Estimated provider cost", "₹" + b.estimated_provider_cost_inr],
      ["Cost per image made", b.cost_per_generated_image_inr === null ? "—" : "₹" + b.cost_per_generated_image_inr],
      ["Cost per accepted image", b.cost_per_accepted_image_inr === null ? "—" : "₹" + b.cost_per_accepted_image_inr]])}
      <p class="foot">${esc(b.cost_note)}</p></section>
    ${breakdown("Quality by category", q.by_category)}
    ${breakdown("Quality by metal", q.by_material)}
    ${breakdown("Quality by look", q.by_preset)}
    ${breakdown("Quality by photo condition", q.by_photo_condition)}
    </div>`;
  $("#days").addEventListener("change", e => { days = +e.target.value; show(); });
}

/* ---------- Access log ---------- */
const ACTION = {view_image: "Viewed a customer image", resolve_report: "Resolved a report", view_queue: "Opened the report list", view_metrics: "Opened metrics"};
async function showAudit() {
  const a = await (await api("/admin/api/audit?limit=200")).json();
  $("#main").innerHTML = `<section class="block wide"><h2>Access log</h2>
    <p class="foot">Every team action and every look at a customer image, newest first.</p>
    ${a.length ? `<table><tr><th>When</th><th>Who</th><th>What</th><th>Detail</th></tr>
    ${a.map(x => `<tr><td>${new Date(x.at).toLocaleString()}</td><td>${esc(x.admin)}</td><td>${esc(ACTION[x.action] || x.action)}</td>
      <td>${esc([x.target && "report " + x.target.slice(0, 8), x.detail].filter(Boolean).join(", "))}</td></tr>`).join("")}</table>`
    : '<p class="empty">Nothing yet.</p>'}</section>`;
}
show();
</script>
</body>
</html>
"""
