// Jewellery Image Studio — mobile web app. Vanilla JS, no build step; talks to the same-origin API.
(() => {
  "use strict";

  // ---------- state, text, storage ----------
  const store = {
    get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* private mode */ } },
  };
  const S = {
    token: store.get("token"),
    lang: store.get("lang") || ((navigator.language || "").toLowerCase().startsWith("hi") ? "hi" : "en"),
    me: null, catalog: null, seq: 0, images: new Map(),
  };
  const t = (k, ...a) => {
    const v = (I18N[S.lang] || I18N.en)[k] ?? I18N.en[k] ?? k;
    return typeof v === "function" ? v(...a) : v;
  };
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const app = $("#app");

  const METALS = {
    en: { yellow_gold: "Yellow gold", rose_gold: "Rose gold", white_gold: "White gold", silver: "Silver", platinum: "Platinum", white_metal: "White gold / silver", other: "Other" },
    hi: { yellow_gold: "पीला सोना", rose_gold: "रोज़ गोल्ड", white_gold: "व्हाइट गोल्ड", silver: "चाँदी", platinum: "प्लैटिनम", white_metal: "व्हाइट गोल्ड / चाँदी", other: "अन्य" },
  };
  const SWATCH = {
    white: "#ffffff", grey: "#ececec",
    beige: "linear-gradient(135deg,#f2eade,#e4d8c6)",
    marble: "linear-gradient(135deg,#f4f2ee 0%,#e3ded7 42%,#f7f5f1 58%,#d9d3ca 100%)",
  };
  const RING = `<svg viewBox="0 0 96 96" width="56%" aria-hidden="true" fill="none"><circle cx="48" cy="57" r="22" stroke="#c9a04e" stroke-width="7"/><path d="M36 30 42 22h12l6 8-12 12z" fill="#eef4f8" stroke="#9fb3c2" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  const ICON = {
    back: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>`,
    gear: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>`,
    gem: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#d4b26a" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h12l4 6-10 12L2 9z"/><path d="M2 9h20"/></svg>`,
    trash: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>`,
    check: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>`,
    info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" style="flex:0 0 auto;margin-top:2px"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
  };

  // ---------- API ----------
  class ApiError extends Error {
    constructor(status, detail) {
      super(typeof detail === "string" ? detail : (detail && detail.message) || "error");
      this.status = status; this.detail = detail || {};
    }
    get code() { return this.detail && this.detail.code; }
  }
  async function api(path, { method = "GET", body, form, headers = {}, raw = false } = {}) {
    const h = { ...headers };
    if (S.token) h.Authorization = "Bearer " + S.token;
    if (body !== undefined) h["Content-Type"] = "application/json";
    let res;
    try {
      res = await fetch(path, { method, headers: h, body: form || (body !== undefined ? JSON.stringify(body) : undefined) });
    } catch (e) {
      throw new ApiError(0, { code: "offline", message: t("offline") });
    }
    if (raw && res.ok) return res;
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* not JSON */ }
    if (!res.ok) throw new ApiError(res.status, data && data.detail);
    return data;
  }
  async function image(url) {
    if (!url) return null;
    if (S.images.has(url)) return S.images.get(url);
    try {
      const blob = await (await api(url, { raw: true })).blob();
      const u = URL.createObjectURL(blob);
      S.images.set(url, u);
      return u;
    } catch (e) { return null; }
  }
  async function fillImages(root) {
    await Promise.all($$("img[data-src]", root).map(async img => {
      const u = await image(img.dataset.src);
      if (u) img.src = u; else img.replaceWith(Object.assign(document.createElement("div"), { innerHTML: RING, className: "ph" }));
    }));
  }
  async function refreshMe() { S.me = await api("/me"); return S.me; }
  async function catalog() { return S.catalog || (S.catalog = await api("/catalog")); }

  // ---------- small UI helpers ----------
  function toast(msg, ms = 2800) {
    $$(".toast").forEach(x => x.remove());  // one message at a time
    const el = Object.assign(document.createElement("div"), { className: "toast", role: "status", textContent: msg });
    document.body.appendChild(el); setTimeout(() => el.remove(), ms);
  }
  function sheet(html, onMount) {
    return new Promise(resolve => {
      const scrim = document.createElement("div");
      scrim.className = "scrim";
      scrim.innerHTML = `<div class="sheet" role="dialog" aria-modal="true">${html}</div>`;
      const close = v => { scrim.remove(); document.removeEventListener("keydown", onKey); resolve(v); };
      const onKey = e => { if (e.key === "Escape") close(undefined); };
      scrim.addEventListener("click", e => { if (e.target === scrim) close(undefined); });
      document.addEventListener("keydown", onKey);
      document.body.appendChild(scrim);
      onMount && onMount($(".sheet", scrim), close);
      const first = $("input,button,textarea", scrim); first && first.focus();
    });
  }
  const confirmSheet = (text, label) => sheet(`<h2>${esc(text)}</h2>
    <button class="btn" data-yes>${esc(label)}</button><button class="btn secondary" data-no>${t("cancel")}</button>`,
    (el, close) => { $("[data-yes]", el).onclick = () => close(true); $("[data-no]", el).onclick = () => close(false); });
  function hintText(h) {
    const s = h.toLowerCase();
    if (s.includes("couldn't find")) return t("hint_notfound");
    if (s.includes("in the frame")) return t("hint_frame");
    if (s.includes("edge")) return t("hint_edge");
    if (s.includes("dark")) return t("hint_dark");
    if (s.includes("blurry")) return t("hint_blurry");
    if (s.includes("small")) return t("hint_small");
    return h;
  }
  const label = obj => (S.lang === "hi" && obj.label_hi) || obj.label;
  const bar = (title, back, extra = "") => `<header class="bar">
    ${back ? `<a class="icon-btn" href="${back}" aria-label="${t("back")}">${ICON.back}</a>` : ""}
    <h1 class="${back ? "" : "brand"}">${esc(title)}</h1>${extra}</header>`;
  const creditChip = () => `<a class="chip" href="#/credits">${ICON.gem} ${t("credits_n", S.me ? S.me.credits : 0)}</a>`;
  function errorToast(e) { toast(e instanceof ApiError && e.status === 0 ? t("offline") : t("error")); console.error(e); }

  // Saving, downloading and buying need a phone sign-in; credits can run out. Handle both, then retry.
  async function guarded(fn) {
    for (let attempt = 0; attempt < 3; attempt++) {
      try { return await fn(); } catch (e) {
        if (!(e instanceof ApiError)) throw e;
        if (e.code === "sign_in_required") { if (!(await signIn())) return undefined; continue; }
        if (e.code === "needs_credits") { await needsCredits(e.detail); return undefined; }
        throw e;
      }
    }
  }

  // ---------- sign in ----------
  function signIn() {
    return sheet(`<h2>${t("signin_title")}</h2><p class="lead">${t("signin_body")}</p>
      <div data-step="phone" style="display:flex;flex-direction:column;gap:12px">
        <label class="field">${t("phone")}<input class="text" type="tel" inputmode="numeric" autocomplete="tel" placeholder="98765 43210" maxlength="16"></label>
        <button class="btn" data-send>${t("send_code")}</button></div>
      <div data-step="code" hidden style="display:flex;flex-direction:column;gap:12px">
        <p class="muted small" data-sent></p>
        <label class="field">${t("code")}<input class="text" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="••••••"></label>
        <button class="btn" data-verify>${t("verify")}</button>
        <button class="btn ghost" data-change>${t("change_number")}</button></div>
      <p class="small" data-err role="alert" style="color:var(--bad);margin:0"></p>
      <button class="btn secondary" data-cancel>${t("cancel")}</button>`,
      (el, close) => {
        const phoneIn = $("[data-step=phone] input", el), codeIn = $("[data-step=code] input", el), err = $("[data-err]", el);
        let phone = "";
        const show = step => { $("[data-step=phone]", el).hidden = step !== "phone"; $("[data-step=code]", el).hidden = step !== "code"; err.textContent = ""; };
        const fail = e => { err.textContent = (e.detail && e.detail.message) || t("error"); };
        $("[data-send]", el).onclick = async () => {
          try {
            const r = await api("/auth/otp/request", { method: "POST", body: { phone: phoneIn.value } });
            phone = r.phone;
            $("[data-sent]", el).textContent = t("code_sent", r.phone) + (r.dev_code ? " · " + t("dev_code", r.dev_code) : "");
            show("code"); codeIn.focus();
          } catch (e) { fail(e); }
        };
        $("[data-verify]", el).onclick = async () => {
          try {
            const r = await api("/auth/otp/verify", { method: "POST", body: { phone, code: codeIn.value } });
            S.token = r.token; store.set("token", r.token); S.images.clear();
            await refreshMe(); close(true);
          } catch (e) { fail(e); }
        };
        $("[data-change]", el).onclick = () => show("phone");
        $("[data-cancel]", el).onclick = () => close(false);
      }).then(v => !!v);
  }

  async function needsCredits(detail) {
    const go = await sheet(`<h2>${t("needs_credits", detail.needed || 1)}</h2>
      <button class="btn" data-buy>${t("buy")}</button><button class="btn secondary" data-no>${t("close")}</button>`,
      (el, close) => { $("[data-buy]", el).onclick = () => close(true); $("[data-no]", el).onclick = () => close(false); });
    if (go) location.hash = "#/credits";
  }

  // ---------- views ----------
  function onboarding() {
    const trial = 3;
    app.innerHTML = `<div class="view" style="justify-content:center;padding-top:40px">
      <div class="lang" role="group" aria-label="${t("choose_language")}">
        <button class="pill" data-lang="en" aria-pressed="${S.lang === "en"}">English</button>
        <button class="pill" data-lang="hi" aria-pressed="${S.lang === "hi"}">हिन्दी</button></div>
      <div style="display:flex;justify-content:center"><div class="stage" style="width:60%">${RING}</div></div>
      <h1 class="title">${t("ob_title")}</h1>
      <p class="lead">${t("ob_body")}</p>
      <div class="card list small">${["ob_tip1", "ob_tip2", "ob_tip3"].map(k => `<div><span>${t(k)}</span></div>`).join("")}</div>
      <p class="lead">${t("ob_trial", trial)}</p>
      <button class="btn" data-start>${t("ob_start")}</button></div>`;
    $$("[data-lang]").forEach(b => b.onclick = () => { setLang(b.dataset.lang); onboarding(); });
    $("[data-start]").onclick = async e => {
      e.target.disabled = true;
      try {
        const r = await api("/auth/start", { method: "POST" });
        S.token = r.token; store.set("token", r.token);
        await refreshMe(); location.hash = "#/new"; route();
      } catch (err) { e.target.disabled = false; errorToast(err); }
    };
  }

  async function home() {
    const [products] = await Promise.all([api("/products"), refreshMe()]);
    app.innerHTML = bar(t("brand"), null, `${creditChip()}<a class="icon-btn" href="#/settings" aria-label="${t("settings")}">${ICON.gear}</a>`) +
      `<main class="view"><h2 class="title">${t("catalogue")}</h2>
      ${products.length ? `<div class="grid2">${products.map(p => `
        <a class="product" href="#/p/${p.id}">
          <div class="thumb">${p.cover_url ? `<img data-src="${p.cover_url}" alt="">` : `<div style="display:grid;place-items:center;height:100%">${RING}</div>`}</div>
          <b>${esc(p.name)}</b><span>${p.image_count ? t("images_n", p.image_count) : t("no_images")}</span></a>`).join("")}</div>`
        : `<div class="empty card">${t("empty_catalogue")}</div>`}
      </main><div class="footer"><a class="btn" href="#/new">${t("new_product")}</a></div>`;
    fillImages(app);
  }

  function photoInputs(multiple) {
    return `<input type="file" accept="image/*" capture="environment" data-camera hidden>
      <input type="file" accept="image/*" ${multiple ? "multiple" : ""} data-gallery hidden>`;
  }

  async function newProduct() {
    const cat = await catalog();
    let category = null;
    app.innerHTML = bar(t("new_product"), "#/") + `<main class="view">
      <section style="display:flex;flex-direction:column;gap:10px"><h2 class="title" style="font-size:26px">${t("what_is_it")}</h2>
        <div class="pills" role="group">${cat.categories.map(c => `<button class="pill" data-cat="${c.id}" aria-pressed="false">${esc(label(c))}</button>`).join("")}</div></section>
      <label class="field">${t("name_optional")}<input class="text" data-name maxlength="120" placeholder="${t("name_hint")}"></label>
      <section style="display:flex;flex-direction:column;gap:10px"><b>${t("add_photo")}</b>
        <div class="row"><button class="btn" data-take disabled>${t("take_photo")}</button><button class="btn secondary" data-pick disabled>${t("from_gallery")}</button></div>
        <p class="muted small" style="margin:0">${t("one_photo_enough")}</p>${photoInputs(true)}</section>
      <p data-status class="muted" role="status"></p></main>`;
    $$("[data-cat]").forEach(b => b.onclick = () => {
      category = b.dataset.cat;
      $$("[data-cat]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
      $("[data-take]").disabled = $("[data-pick]").disabled = false;
    });
    $("[data-take]").onclick = () => $("[data-camera]").click();
    $("[data-pick]").onclick = () => $("[data-gallery]").click();
    const upload = async files => {
      if (!files.length) return;
      $("[data-status]").innerHTML = `<span class="spinner" style="display:inline-block;vertical-align:middle"></span> ${t("uploading")}`;
      $$("button").forEach(b => b.disabled = true);
      try {
        const p = await api("/products", { method: "POST", body: { category, name: $("[data-name]").value || null } });
        await uploadPhotos(p.id, files);
        location.hash = `#/p/${p.id}`;
      } catch (e) { $$("button").forEach(b => b.disabled = false); $("[data-status]").textContent = ""; errorToast(e); }
    };
    $("[data-camera]").onchange = e => upload([...e.target.files]);
    $("[data-gallery]").onchange = e => upload([...e.target.files]);
  }

  async function uploadPhotos(productId, files) {
    const form = new FormData();
    files.forEach(f => form.append("files", f, f.name || "photo.jpg"));
    const r = await api(`/products/${productId}/photos`, { method: "POST", form });
    if (r.notices && r.notices.length) toast(r.notices[0], 4000);
    return r;
  }

  async function product(id) {
    const p = await api(`/products/${id}`);
    const hints = [...new Set(p.photos.flatMap(ph => ph.hints))];
    const metalName = p.metal ? (METALS[S.lang][p.metal] || p.metal) : null;
    app.innerHTML = bar(p.name, "#/", `<button class="icon-btn" data-del aria-label="${t("delete_product")}">${ICON.trash}</button>`) + `<main class="view">
      <section style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;justify-content:space-between;align-items:baseline"><b>${t("photos")}</b>
          <button class="btn ghost" style="width:auto" data-rename>${t("rename")}</button></div>
        <div class="grid3">${p.photos.map(ph => `<div class="thumb"><img data-src="${ph.url}?w=400" alt=""></div>`).join("")}
          ${p.photos.length < 8 ? `<button class="thumb" data-add style="border-style:dashed;color:var(--muted);cursor:pointer;font-weight:700">+ ${t("add_angle")}</button>` : ""}</div>
        ${photoInputs(true)}
        ${hints.map(h => `<div class="note warn">${ICON.info}<span>${esc(hintText(h))}</span></div>`).join("")}
        ${metalName ? `<p class="muted small" style="margin:0">${t("metal")}: <b style="color:var(--text)">${esc(metalName)}</b>${p.metal_source === "detected" ? ` (${t("detected")})` : ""}</p>` : ""}
      </section>
      <section style="display:flex;flex-direction:column;gap:10px"><b>${t("images")}</b>
        ${p.images.length ? `<div class="grid2">${p.images.map(g => `<a class="product" href="#/g/${g.id}">
          <div class="thumb">${g.preview_url ? `<img data-src="${g.preview_url}" alt="">` : `<div style="display:grid;place-items:center;height:100%">${g.status === "failed" ? "—" : `<span class="spinner"></span>`}</div>`}
          ${g.review === "accepted" ? `<span class="badge">${t("saved")}</span>` : g.review === "reported" ? `<span class="badge">${t("reported")}</span>` : ""}</div></a>`).join("")}</div>`
          : `<p class="muted">${t("no_images")}</p>`}
      </section></main>
      <div class="footer"><a class="btn" href="#/p/${id}/make">${t("make_image")}</a></div>`;
    fillImages(app);
    const add = $("[data-add]");
    if (add) add.onclick = () => $("[data-gallery]").click();
    $("[data-gallery]").onchange = async e => {
      try { await uploadPhotos(id, [...e.target.files]); route(); } catch (err) { errorToast(err); }
    };
    $("[data-rename]").onclick = async () => {
      const name = await sheet(`<h2>${t("rename")}</h2><input class="text" maxlength="120" value="${esc(p.name)}">
        <button class="btn" data-ok>${t("done")}</button><button class="btn secondary" data-no>${t("cancel")}</button>`,
        (el, close) => { $("[data-ok]", el).onclick = () => close($("input", el).value.trim()); $("[data-no]", el).onclick = () => close(null); });
      if (name) { await api(`/products/${id}`, { method: "PATCH", body: { name } }); route(); }
    };
    $("[data-del]").onclick = async () => {
      if (await confirmSheet(t("delete_product_q"), t("delete"))) { await api(`/products/${id}`, { method: "DELETE" }); location.hash = "#/"; }
    };
  }

  async function make(id) {
    const [cat, p] = await Promise.all([catalog(), api(`/products/${id}`)]);
    const looks = cat.presets.filter(x => x.available);
    let look = looks[0].id, ratio = "1:1";
    const ratioKey = r => "ratio_" + r.replace(":", "_");
    app.innerHTML = bar(p.name, `#/p/${id}`) + `<main class="view">
      <h2 class="title">${t("choose_look")}</h2>
      <div class="grid2">${looks.map(l => `<button class="look" data-look="${l.id}" aria-pressed="${l.id === look}">
        <div class="sw" style="background:${SWATCH[l.id] || "#ddd"};display:grid;place-items:center">${RING}</div><b>${esc(label(l))}</b></button>`).join("")}</div>
      <section style="display:flex;flex-direction:column;gap:10px"><b>${t("size")}</b>
        <div class="pills">${cat.aspect_ratios.map(r => `<button class="pill" data-ratio="${r.id}" aria-pressed="${r.id === ratio}">${t(ratioKey(r.id))} ${r.id}</button>`).join("")}</div></section>
    </main><div class="footer"><p class="muted small" data-cost style="margin:0;text-align:center"></p><button class="btn" data-go disabled>…</button></div>`;
    $$("[data-look]").forEach(b => b.onclick = () => { look = b.dataset.look; $$("[data-look]").forEach(x => x.setAttribute("aria-pressed", String(x === b))); });
    $$("[data-ratio]").forEach(b => b.onclick = () => { ratio = b.dataset.ratio; $$("[data-ratio]").forEach(x => x.setAttribute("aria-pressed", String(x === b))); });
    let q = await api(`/products/${id}/quote`);
    const showQuote = () => {
      $("[data-cost]").textContent = (q.additional ? t("cost_more", q.cost) : t("cost_first", q.cost)) + " " + t("balance", q.balance);
      $("[data-go]").disabled = false;
      $("[data-go]").textContent = q.enough ? t("generate", q.cost) : t("not_enough");
    };
    showQuote();
    $("[data-go]").onclick = async () => {
      if (!q.enough) return needsCredits({ needed: q.cost - q.balance });
      $("[data-go]").disabled = true;
      const key = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()) + Math.random();
      try {
        const g = await api(`/products/${id}/generations`, { method: "POST", headers: { "Idempotency-Key": key },
          body: { preset: look, aspect_ratio: ratio, confirm_cost: q.cost } });
        location.hash = `#/g/${g.id}`;
      } catch (e) {
        if (e.code === "cost_changed" || e.code === "needs_credits") { q = await api(`/products/${id}/quote`); showQuote(); if (e.code === "needs_credits") needsCredits(e.detail); return; }
        $("[data-go]").disabled = false; errorToast(e);
      }
    };
  }

  async function generation(id, seq) {
    const g = await api(`/generations/${id}`);
    if (seq !== S.seq) return;
    if (g.status === "done" || g.status === "failed") await refreshMe();
    if (g.status === "queued" || g.status === "running") {
      app.innerHTML = bar(t("making"), `#/p/${g.product_id}`) + `<main class="view">
        <div class="stage"><span class="spinner"></span></div>
        <ol class="steps" aria-live="polite">${g.steps.filter(s => s.id !== "ready").map(s =>
          `<li class="${s.done ? "done" : s.active ? "on" : ""}"><span class="dot">${s.done ? ICON.check : ""}</span>${t("step_" + s.id)}</li>`).join("")}</ol></main>`;
      setTimeout(() => { if (seq === S.seq) generation(id, seq).catch(errorToast); }, 1500);
      return;
    }
    if (g.status === "failed") {
      app.innerHTML = bar(t("result"), `#/p/${g.product_id}`) + `<main class="view">
        <div class="note warn">${ICON.info}<span>${esc(S.lang === "en" && g.message ? g.message : t("failed"))}</span></div>
        <a class="btn" href="#/p/${g.product_id}/make">${t("try_again")}</a></main>`;
      return;
    }
    const lastReport = g.reports[g.reports.length - 1];
    let view = "result";
    app.innerHTML = bar(t("result"), `#/p/${g.product_id}`, creditChip()) + `<main class="view">
      <div class="seg" role="group"><button data-v="result" aria-pressed="true">${t("result")}</button><button data-v="original" aria-pressed="false">${t("original")}</button></div>
      <div class="stage" data-stage><img data-src="${g.preview_url}" alt="${t("result")}"></div>
      <div class="note warn">${ICON.info}<span>${t("check_details")}</span></div>
      ${g.warning ? `<div class="note warn">${ICON.info}<span>${t("soft_warning")}</span></div>` : ""}
      ${lastReport ? `<div class="note ok">${ICON.info}<span>${esc(lastReport.message && S.lang === "en" ? lastReport.message : t("rep_" + lastReport.refund))}</span></div>` : ""}
      <div class="row"><button class="btn" data-save ${g.review === "accepted" ? "disabled" : ""}>${g.review === "accepted" ? t("saved") : t("save")}</button>
        <button class="btn secondary" data-dl>${t("download")}</button></div>
      <div class="row"><button class="btn secondary" data-share>${t("share")}</button>
        <button class="btn secondary" data-report>${t("report")}</button></div>
      <a class="btn ghost" href="#/p/${g.product_id}/make">${t("another")}</a>
      <button class="btn ghost" style="color:var(--bad)" data-del>${t("delete_image")}</button></main>`;
    fillImages(app);
    $$("[data-v]").forEach(b => b.onclick = async () => {
      view = b.dataset.v;
      $$("[data-v]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
      const stage = $("[data-stage]");
      if (view === "original" && g.original_deleted) { stage.innerHTML = `<p class="muted" style="padding:24px;text-align:center">${t("original_deleted")}</p>`; return; }
      stage.innerHTML = `<img data-src="${view === "result" ? g.preview_url : g.original_url}" alt="${t(view)}">`;
      fillImages(stage);
    });
    $("[data-save]").onclick = () => guarded(async () => {
      await api(`/generations/${id}/accept`, { method: "POST" });
      toast(t("saved")); route();
    }).catch(errorToast);
    const fullFile = async () => {
      const res = await api(`/generations/${id}/download`, { raw: true });
      const name = ((res.headers.get("Content-Disposition") || "").match(/filename="?([^";]+)"?/) || [])[1] || "jewellery.png";
      const blob = await res.blob();
      return new File([blob], name, { type: blob.type || "image/png" });
    };
    $("[data-dl]").onclick = () => guarded(async () => {
      const f = await fullFile();
      const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(f), download: f.name });
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 10000);
      toast(t("downloaded"));
    }).catch(errorToast);
    $("[data-share]").onclick = () => guarded(async () => {
      const f = await fullFile();
      if (!(navigator.canShare && navigator.canShare({ files: [f] }))) { toast(t("share_unsupported"), 4500); return; }
      try {
        await navigator.share({ files: [f] });
        api(`/generations/${id}/events`, { method: "POST", body: { type: "share", channel: "share_sheet" } }).catch(() => {});
      } catch (e) { /* user closed the share sheet */ }
    }).catch(errorToast);
    $("[data-report]").onclick = () => report(g);
    $("[data-del]").onclick = async () => {
      if (await confirmSheet(t("delete_image_q"), t("delete"))) { await api(`/generations/${id}`, { method: "DELETE" }); location.hash = `#/p/${g.product_id}`; }
    };
  }

  async function report(g) {
    const cat = await catalog();
    let kind = "product_detail";
    const list = k => Object.keys(cat.report_categories[k]).map(id =>
      `<label class="radio"><input type="radio" name="rc" value="${id}"> ${t("rc_" + id)}</label>`).join("");
    const r = await sheet(`<h2>${t("report_title")}</h2>
      <div class="seg" role="group"><button data-k="product_detail" aria-pressed="true">${t("report_detail")}</button>
        <button data-k="visual_quality" aria-pressed="false">${t("report_quality")}</button></div>
      <div data-list>${list(kind)}</div>
      <label class="field">${t("report_note")}<textarea class="text" rows="2" maxlength="1000" style="padding:12px;min-height:0"></textarea></label>
      <button class="btn" data-send disabled>${t("send_report")}</button><button class="btn secondary" data-no>${t("cancel")}</button>`,
      (el, close) => {
        const sync = () => { $("[data-send]", el).disabled = !$("input[name=rc]:checked", el); };
        $$("[data-k]", el).forEach(b => b.onclick = () => {
          kind = b.dataset.k; $$("[data-k]", el).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
          $("[data-list]", el).innerHTML = list(kind); $$("input[name=rc]", el).forEach(i => i.onchange = sync); sync();
        });
        $$("input[name=rc]", el).forEach(i => i.onchange = sync);
        $("[data-send]", el).onclick = () => close({ kind, category: $("input[name=rc]:checked", el).value, note: $("textarea", el).value });
        $("[data-no]", el).onclick = () => close(null);
      });
    if (!r) return;
    try {
      const res = await api(`/generations/${g.id}/report`, { method: "POST", body: r });
      toast(t("rep_" + res.refund), 4500); route();
    } catch (e) { errorToast(e); }
  }

  async function credits() {
    const [hist, packs] = await Promise.all([api("/me/credits"), api("/credits/packs"), refreshMe()]);
    app.innerHTML = bar(t("credits"), "#/") + `<main class="view">
      <div class="card" style="display:flex;flex-direction:column;gap:4px"><span class="muted small">${t("credits")}</span>
        <span style="font-family:var(--display);font-size:52px;line-height:1;color:var(--gold)">${hist.balance}</span></div>
      <section style="display:flex;flex-direction:column;gap:10px"><b>${t("buy")}</b>
        ${packs.map(p => `<button class="btn ${p.id === "shop" ? "" : "secondary"}" data-pack="${p.id}" ${p.price_inr ? "" : "disabled"}>
          ${t("pack_credits", p.credits)} · ${p.price_inr ? "₹" + p.price_inr.toLocaleString("en-IN") : t("price_tbd")}</button>`).join("")}</section>
      <section><b>${t("history")}</b><div class="list">${hist.transactions.map(x => `<div>
        <span>${t("reason_" + x.reason)}<br><span class="muted small">${new Date(x.at).toLocaleDateString(S.lang === "hi" ? "hi-IN" : "en-IN")}</span></span>
        <b style="color:${x.delta > 0 ? "var(--ok)" : "var(--text)"}">${x.delta > 0 ? "+" : ""}${x.delta}</b></div>`).join("")}</div></section></main>`;
    $$("[data-pack]").forEach(b => b.onclick = () => guarded(() => buy(b.dataset.pack)).catch(errorToast));
  }

  async function buy(pack) {
    const before = (await refreshMe()).credits;
    const order = await api("/payments/orders", { method: "POST", body: { pack } });
    if (order.key_id) {
      await loadScript("https://checkout.razorpay.com/v1/checkout.js");
      await new Promise((resolve, reject) => {
        const rz = new window.Razorpay({ key: order.key_id, order_id: order.order_id, amount: order.amount, currency: order.currency,
          name: t("brand"), theme: { color: "#d4b26a" }, handler: resolve, modal: { ondismiss: () => reject(new Error("dismissed")) } });
        rz.open();
      }).catch(() => null);
      toast(t("paying"));
      for (let i = 0; i < 20; i++) {  // credits arrive through the server-side webhook
        await new Promise(r => setTimeout(r, 1500));
        if ((await refreshMe()).credits > before) break;
      }
    } else {
      await api(`/payments/mock-complete/${order.order_id}`, { method: "POST" });  // test mode only
    }
    if ((await refreshMe()).credits > before) toast(t("bought"));
    route();
  }
  const loadScript = src => new Promise((res, rej) => {
    if ($(`script[src="${src}"]`)) return res();
    document.head.appendChild(Object.assign(document.createElement("script"), { src, onload: res, onerror: rej }));
  });

  async function settings() {
    await refreshMe();
    app.innerHTML = bar(t("settings"), "#/") + `<main class="view">
      <section style="display:flex;flex-direction:column;gap:10px"><b>${t("choose_language")}</b>
        <div class="lang"><button class="pill" data-lang="en" aria-pressed="${S.lang === "en"}">English</button>
        <button class="pill" data-lang="hi" aria-pressed="${S.lang === "hi"}">हिन्दी</button></div></section>
      <div class="card" style="display:flex;flex-direction:column;gap:12px">
        <span>${S.me.guest ? t("guest_mode") : t("signed_in_as", esc(S.me.phone))}</span>
        ${S.me.guest ? `<button class="btn" data-signin>${t("sign_in")}</button>` : ""}</div>
      <p class="muted small">${t("privacy_note")}</p>
      <button class="btn danger" data-delete>${t("delete_account")}</button></main>`;
    $$("[data-lang]").forEach(b => b.onclick = () => { setLang(b.dataset.lang); route(); });
    const si = $("[data-signin]");
    if (si) si.onclick = async () => { if (await signIn()) route(); };
    $("[data-delete]").onclick = async () => {
      if (!(await confirmSheet(t("delete_account_q"), t("delete")))) return;
      await api("/me", { method: "DELETE" });
      S.token = null; store.set("token", null); S.images.clear(); location.hash = ""; onboarding();
    };
  }

  // ---------- routing ----------
  function setLang(l) { S.lang = l; store.set("lang", l); document.documentElement.lang = l; document.title = t("brand"); }
  const ROUTES = [
    [/^#?\/?$/, () => home()],
    [/^#\/new$/, () => newProduct()],
    [/^#\/p\/(\w+)$/, m => product(m[1])],
    [/^#\/p\/(\w+)\/make$/, m => make(m[1])],
    [/^#\/g\/(\w+)$/, m => generation(m[1], S.seq)],
    [/^#\/credits$/, () => credits()],
    [/^#\/settings$/, () => settings()],
  ];
  async function route() {
    S.seq++;
    $$(".scrim").forEach(x => x.remove());
    if (!S.token) return onboarding();
    const h = location.hash || "#/";
    const hit = ROUTES.find(([re]) => re.test(h));
    try {
      await (hit ? hit[1](h.match(hit[0])) : home());
      window.scrollTo(0, 0);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) { S.token = null; store.set("token", null); return onboarding(); }
      if (e instanceof ApiError && e.status === 404) { location.hash = "#/"; return; }
      errorToast(e);
    }
  }
  setLang(S.lang);
  window.addEventListener("hashchange", () => { $$(".toast").forEach(x => x.remove()); route(); });
  route();
})();
