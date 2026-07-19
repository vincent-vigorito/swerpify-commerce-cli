/* =====================================================================
   Cancello 2 — audit a11y RENDERIZZATO (da incollare in browser_evaluate,
   sulla pagina LIVE dopo `design compile`). Complementa check_page.py, che è
   statico e NON vede gli stili calcolati.

   USO: naviga la pagina, poi `browser_evaluate` con il corpo di window.__a11y.
   Ritorna un oggetto con le violazioni per categoria.

   ⚠️ LIMITE NOTO DEL CONTRASTO (perché non tutti i "fail" sono veri):
   il ratio si calcola solo quando si trova un background-color SOLIDO
   risalendo gli antenati. Se il testo sta su un GRADIENTE o un'IMMAGINE
   (background-image), il colore di sfondo effettivo non è calcolabile in JS
   → quei casi finiscono in `contrasto_da_rivedere` (NON in `contrasto_fail`)
   e vanno guardati a occhio. I `contrasto_fail` (sfondo solido) sono invece
   affidabili. Questo evita i falsi positivi "testo bianco su bianco (1:1)"
   che in realtà sono testo bianco su sezione scura a gradiente.
   ===================================================================== */
window.__a11y = () => {
  const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && cs.visibility !== "hidden" && cs.display !== "none"; };
  const parse = s => { const m = String(s).match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(",").map(x => parseFloat(x)); return { rgb: [p[0], p[1], p[2]], a: p[3] === undefined ? 1 : p[3] }; };
  const lum = c => { const [r, g, b] = c.map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }); return .2126 * r + .7152 * g + .0722 * b; };
  const ratio = (f, b) => { const L1 = lum(f), L2 = lum(b), hi = Math.max(L1, L2), lo = Math.min(L1, L2); return (hi + .05) / (lo + .05); };
  // risale finché trova un bg-color OPACO; ritorna null se non c'è (gradiente/img)
  const solidBg = el => { let e = el; while (e) { const cs = getComputedStyle(e); const p = parse(cs.backgroundColor);
    if (p && p.a >= .95) return p.rgb;
    if (cs.backgroundImage && cs.backgroundImage !== "none") return null; // gradiente/img → non calcolabile
    e = e.parentElement; } return [255, 255, 255]; };
  const accName = el => (el.textContent || "").trim() || el.getAttribute("aria-label") || el.getAttribute("title") ||
    [...el.querySelectorAll("img[alt]")].map(i => i.alt).join("").trim();

  const root = document.querySelector("#main_content") || document.body;
  const o = { struttura: {}, contrasto_fail: [], contrasto_da_rivedere: 0 };

  // ---- struttura (deterministica, affidabile) ----
  const imgs = [...document.querySelectorAll("img")];
  o.struttura.img_senza_alt = imgs.filter(i => !i.hasAttribute("alt")).length;
  o.struttura.link_button_senza_nome = [...document.querySelectorAll("a[href],button")].filter(vis).filter(el => !accName(el)).length;
  const fields = [...document.querySelectorAll("input:not([type=hidden]),select,textarea")].filter(vis);
  const labelFor = new Set([...document.querySelectorAll("label[for]")].map(l => l.getAttribute("for")));
  o.struttura.form_senza_label = fields.filter(f => !(f.id && labelFor.has(f.id)) && !f.getAttribute("aria-label") && !f.closest("label")).length;
  const hs = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(vis);
  o.struttura.h1_count = hs.filter(h => h.tagName === "H1").length;
  let prev = 0, skips = 0; hs.forEach(h => { const lv = +h.tagName[1]; if (prev && lv > prev + 1) skips++; prev = lv; });
  o.struttura.heading_salti = skips;
  o.struttura.landmark_mancanti = ["main,[role=main]", "nav,[role=navigation]", "header,[role=banner]", "footer,[role=contentinfo]"]
    .filter(sel => !document.querySelector(sel)).map(s => s.split(",")[0]);
  o.struttura.html_lang = document.documentElement.getAttribute("lang") || "(assente)";
  const ids = {}; document.querySelectorAll("[id]").forEach(e => ids[e.id] = (ids[e.id] || 0) + 1);
  o.struttura.id_duplicati = Object.entries(ids).filter(([, n]) => n > 1).map(([k]) => k);
  o.struttura.tabindex_positivo = [...document.querySelectorAll("[tabindex]")].filter(e => +e.getAttribute("tabindex") > 0).length;

  // ---- contrasto (fail solo su sfondo solido; gradiente → da rivedere) ----
  for (const el of root.querySelectorAll("p,span,a,li,h1,h2,h3,h4,h5,h6,button,label,dt,dd,small")) {
    if (!vis(el)) continue;
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(el); const fg = parse(cs.color); if (!fg) continue;
    const bg = solidBg(el);
    if (bg === null) { o.contrasto_da_rivedere++; continue; }   // gradiente/img: NON è un fail
    const size = parseFloat(cs.fontSize), large = size >= 24 || (size >= 18.66 && +cs.fontWeight >= 700);
    const min = large ? 3 : 4.5, r = ratio(fg.rgb, bg);
    if (r < min) o.contrasto_fail.push({ txt: el.textContent.trim().slice(0, 30), ratio: +r.toFixed(2), min, size: Math.round(size), cls: (el.className || "").toString().slice(0, 30) });
  }
  const seen = new Set(); o.contrasto_fail = o.contrasto_fail.filter(f => { const k = f.cls + f.ratio; if (seen.has(k)) return false; seen.add(k); return true; });
  return o;
};
window.__a11y();
