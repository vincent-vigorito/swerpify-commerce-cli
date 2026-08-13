#!/usr/bin/env python3
"""Conformance checker per pagine SwerpiCommerce — deterministico, model-agnostico.

Verifica una pagina su 4 dimensioni: CONFORMITÀ SWCSS · SEO · EEAT · ACCESSIBILITÀ.
È il "cancello" oggettivo che la skill (istruzioni) da sola non può garantire:
gira uguale a prescindere dal modello che ha costruito la pagina.

USO (dalla cartella di un sito, es. sites/spnew):
    python /percorso/check_page.py <page-id-o-slug> [--swc ../swc]

Legge il record pagina, il contenuto, il CSS di pagina (cms/<slug>.css) via il
wrapper `swc` e stampa un report. Exit code 1 se ci sono errori BLOCCANTI (❌).

NB: è la META metà statica. La metà "renderizzata" (axe a11y = 0, contrasto reale,
stili calcolati come dimensione link/gutter) va fatta sul browser sulla pagina live
— vedi la checklist nella skill. Questo script NON la sostituisce.
"""
import json, re, subprocess, sys, argparse, html

BLOCK, WARN, OK = "❌", "⚠️ ", "✓"

def swc(swc_path, *args):
    r = subprocess.run([swc_path, *args, "--json", "--no-cache"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None
    data = d.get("results", d)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    return data

def resolve_page(swc_path, ref):
    rows = swc(swc_path, "pages", "list") or []
    if isinstance(rows, dict):
        rows = rows.get("data", rows)
    if ref.isdigit():
        for r in rows:
            if str(r.get("id")) == ref:
                return r
    for r in rows:
        if (r.get("slug") or "") == ref:
            return r
    return None

def get_content(swc_path, pid):
    d = swc(swc_path, "pages", "content", "page-get", str(pid)) or {}
    return d.get("content") or ""

def get_css(swc_path, slug):
    d = swc(swc_path, "design", "css-get", f"{slug}.css", "--section", "cms")
    if not d:
        return None
    return d.get("contenuto") or d.get("content") or ""

class Report:
    def __init__(self):
        self.rows = []
        self.block = 0
        self.warn = 0
    def add(self, dim, level, msg):
        self.rows.append((dim, level, msg))
        if level == BLOCK: self.block += 1
        elif level == WARN: self.warn += 1
    def ok(self, dim, msg):
        self.rows.append((dim, OK, msg))
    def dump(self):
        cur = None
        for dim, level, msg in self.rows:
            if dim != cur:
                print(f"\n── {dim} ──"); cur = dim
            print(f"  {level} {msg}")
        print(f"\n{'='*50}")
        verdict = "FAIL" if self.block else ("PASS con avvisi" if self.warn else "PASS pulito")
        print(f"  {verdict}  —  bloccanti: {self.block} · avvisi: {self.warn}")
        return 1 if self.block else 0

# ---------- CHECK: CONFORMITÀ SWCSS ----------
def check_swcss(rep, content, css):
    # inline vietati (regola 0)
    if re.search(r"<style[\s>]", content, re.I): rep.add("SWCSS", BLOCK, "<style> inline nel contenuto (regola 0)")
    if re.search(r"<script[\s>]", content, re.I): rep.add("SWCSS", BLOCK, "<script> inline nel contenuto (regola 0)")
    # style="..." è violazione SOLO se imposta property CSS di DESIGN. Whitelist:
    #  - custom property (es. style="--v: 80%"): passa un VALORE-dato a barre/meter
    #    (lo styling resta nel CSS che legge var(--v));
    #  - display:none (± !important): nasconde elementi (progressive-disclosure via
    #    JS) e lo span-safelist per le classi generate a runtime — pattern legittimi.
    bad_inline = 0
    for m in re.finditer(r'\sstyle\s*=\s*["\']([^"\']*)["\']', content):
        val = re.sub(r"--[a-z0-9-]+\s*:[^;]*;?", "", m.group(1), flags=re.I)
        val = re.sub(r"display\s*:\s*none\s*(!important)?\s*;?", "", val, flags=re.I)
        if val.strip(" ;"): bad_inline += 1
    if bad_inline: rep.add("SWCSS", BLOCK, f'{bad_inline} style="..." inline con property CSS di design (regola 0; ok solo --custom-prop e display:none)')
    # asset senza prefisso CDN (obbligo {{ STATIC_WEB_URL }}, dal 30/07/2026).
    # Il contenuto pagina È un template Django: la variabile risolve (vuota se CDN
    # off → path relativi identici, quindi il prefisso è SEMPRE sicuro).
    nudi = re.findall(r'["\'(]/(?:static|uploads)/', content)
    if nudi:
        rep.add("SWCSS", BLOCK, f"{len(nudi)} URL asset senza prefisso CDN: anteponi {{{{ STATIC_WEB_URL }}}} a /static/ e /uploads/ (risolve vuoto se la CDN è off: sempre sicuro)")
    assoluti = re.findall(r'https?://[a-z0-9.-]+/(?:static|uploads)/', content, re.I)
    if assoluti:
        rep.add("SWCSS", WARN, f"{len(assoluti)} URL asset assoluti con dominio (es. {assoluti[0]}…): se è il dominio del tenant sostituisci l'intera base con {{{{ STATIC_WEB_URL }}}}")
    pref = content.count("{{ STATIC_WEB_URL }}")
    if pref and not nudi:
        rep.ok("SWCSS", f"asset col prefisso CDN {{{{ STATIC_WEB_URL }}}} ({pref} usi), 0 nudi")
    if css is None:
        rep.add("SWCSS", WARN, "nessun CSS di pagina (cms/<slug>.css) — ok se usa solo componenti esistenti")
        return
    # hex cablati vs var(--sw-*) (regola 4)
    hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
    varsw = re.findall(r"var\(--sw-[a-z0-9-]+\)", css)
    if hexes:
        lvl = BLOCK if len(hexes) > 6 else WARN
        rep.add("SWCSS", lvl, f"{len(hexes)} colori hex cablati (usa var(--sw-*); creali con /design/colors). Es: {sorted(set(hexes))[:6]}")
    else:
        rep.ok("SWCSS", f"colori via var(--sw-*) ({len(varsw)} usi), 0 hex cablati")
    # font-size in px (regola 4: scala tipografica)
    pxfs = re.findall(r"font-size:\s*\d+px", css)
    if pxfs: rep.add("SWCSS", WARN, f"{len(pxfs)} font-size in px (usa var(--text-*))")
    # !important
    imp = css.count("!important")
    if imp: rep.add("SWCSS", WARN, f"{imp} !important (odore di specificità; preferisci cascata/scoping)")
    # gutter-killer: padding shorthand 'v 0 v' su una classe wrapper (padding-inline)
    if re.search(r"padding:\s*[\d.]+[a-z%]* 0 ", css) and "padding-inline" in css:
        rep.add("SWCSS", WARN, "shorthand 'padding: v 0 v' + padding-inline nello stesso file: rischio gutter azzerato su mobile (usa padding-block)")

# ---------- CHECK: SEO ----------
def check_seo(rep, page, content):
    mt = (page.get("meta_title") or page.get("title") or "").strip()
    if not mt: rep.add("SEO", BLOCK, "meta_title assente")
    elif not (25 <= len(mt) <= 65): rep.add("SEO", WARN, f"meta_title {len(mt)} char (ideale ~30–60): {mt[:50]!r}")
    else: rep.ok("SEO", f"meta_title ok ({len(mt)} char)")
    desc = (page.get("description") or page.get("meta_description") or "").strip()
    if not desc: rep.add("SEO", BLOCK, "meta description assente")
    elif not (100 <= len(desc) <= 170): rep.add("SEO", WARN, f"meta description {len(desc)} char (ideale ~120–160)")
    else: rep.ok("SEO", f"meta description ok ({len(desc)} char)")
    # H1 unico. Sulle pagine di SISTEMA (blog, categorie…) l'H1 lo fornisce il
    # template di sistema, non il block content → "nessun <h1>" NON è bloccante:
    # va verificato sul render live. Su pagine CMS normali resta bloccante.
    h1 = re.findall(r"<h1\b", content, re.I)
    sistema = page.get("pagina_sistema")
    if len(h1) == 0:
        if sistema:
            rep.add("SEO", WARN, f"nessun <h1> nel contenuto — pagina di sistema ({sistema}): l'H1 di norma lo mette il template, verifica sul render live")
        else:
            rep.add("SEO", BLOCK, "nessun <h1> nel contenuto")
    elif len(h1) > 1: rep.add("SEO", BLOCK, f"{len(h1)} <h1> (deve essere UNO)")
    else: rep.ok("SEO", "un solo <h1>")
    # gerarchia heading (no salti)
    levels = [int(m) for m in re.findall(r"<h([1-6])\b", content, re.I)]
    prev = 0; skip = False
    for lv in levels:
        if prev and lv > prev + 1: skip = True
        prev = lv
    if skip: rep.add("SEO", WARN, "gerarchia heading con salti (es. h2→h4): usa livelli consecutivi")
    # campi llms (SEO/AI del tema)
    if not (page.get("llms_description") or "").strip(): rep.add("SEO", WARN, "llms_description vuota (indicizzazione AI)")
    if not (page.get("llms_section") or "").strip(): rep.add("SEO", WARN, "llms_section vuota")
    # coerenza index/sitemap
    idx, sm = page.get("index"), page.get("sitemap")
    if idx is False and sm is True: rep.add("SEO", WARN, "index=false ma sitemap=true (incoerenza: noindex nel sitemap)")
    if idx is True and sm is False: rep.add("SEO", WARN, "index=true ma sitemap=false (indicizzabile ma fuori dal sitemap)")

# ---------- CHECK: EEAT ----------
def check_eeat(rep, page, content):
    markups = page.get("markups")
    has_ld = bool(markups) or bool(re.search(r'type="application/ld\+json"', content, re.I))
    if not has_ld:
        rep.add("EEAT", WARN, "nessun dato strutturato JSON-LD (markups vuoti): aggiungi schema pertinente (Organization/Product/FAQPage/BreadcrumbList)")
    else:
        rep.ok("EEAT", "dato strutturato JSON-LD presente")
    # promessa: la fiducia è per lo più giudizio di CONTENUTO (fonti, esperienza
    # reale, autore, dati verificabili) che un linter non può valutare. Qui solo
    # il segnale MECCANICO (JSON-LD sopra) + un promemoria, senza rumore per-pagina.
    rep.add("EEAT", WARN, "EEAT sostanziale = giudizio di contenuto (esperienza reale, fonti, autore/firma, dati verificabili): non lint-abile, verifica a mano vs la checklist")

# ---------- CHECK: ACCESSIBILITÀ (statica) ----------
def check_a11y(rep, content):
    imgs = re.findall(r"<img\b[^>]*>", content, re.I)
    noalt = [i for i in imgs if not re.search(r'\balt\s*=', i, re.I)]
    if noalt: rep.add("A11Y", BLOCK, f"{len(noalt)}/{len(imgs)} <img> senza attributo alt")
    elif imgs: rep.ok("A11Y", f"tutte le {len(imgs)} <img> hanno alt")
    # testo-link generico
    generic = re.findall(r">\s*(clicca qui|click here|qui|leggi|leggi di più|read more|scopri)\s*<", content, re.I)
    if generic: rep.add("A11Y", WARN, f"{len(generic)} link con testo generico ({set(g.lower() for g in generic)}): usa testo descrittivo")
    # input senza label (se ci sono form)
    inputs = re.findall(r"<(input|textarea|select)\b[^>]*>", content, re.I)
    ids = re.findall(r'<(?:input|textarea|select)\b[^>]*\bid\s*=\s*["\']([^"\']+)', content, re.I)
    labelled = set(re.findall(r'<label\b[^>]*\bfor\s*=\s*["\']([^"\']+)', content, re.I))
    aria = len(re.findall(r'aria-label\s*=', content, re.I))
    if inputs:
        unl = [i for i in ids if i not in labelled]
        if unl and aria < len(inputs): rep.add("A11Y", WARN, f"input senza <label for> o aria-label: {unl[:4]}")
    # link/button senza testo discernibile
    empty = re.findall(r"<a\b[^>]*>\s*</a>|<button\b[^>]*>\s*</button>", content, re.I)
    if empty: rep.add("A11Y", WARN, f"{len(empty)} <a>/<button> senza testo (aggiungi aria-label se icona)")
    rep.add("A11Y", WARN, "gate finale a11y = axe sulla pagina LIVE (target 0 violazioni) + contrasto reale: eseguilo nel browser")

def check_form(rep, content):
    """Campi form: errori che il browser NON segnala e che si vedono solo a
    form inviato (o non si vedono affatto). Il JS di piattaforma
    (sw_form_swcss.js) indicizza i campi per `id` e per le select prende
    `options[selectedIndex].text`."""
    campi = re.findall(r"<(select|input|textarea)\b([^>]*)>", content, re.I)
    if not campi:
        return

    # 1. sw-form-select da sola: la base del campo (width/padding/radius) sta
    #    in .sw-form-field, non in .sw-form-select -> campo stretto e squadrato
    orfane = [a for t, a in campi
              if re.search(r"\bsw-form-select\b", a) and not re.search(r"\bsw-form-field\b", a)]
    if orfane:
        rep.add("FORM", BLOCK, f"{len(orfane)} campo/i con `sw-form-select` senza `sw-form-field`: "
                               "serve `class=\"sw-form-field sw-form-select\"` (da sola: larghezza ~252px, padding 0, radius 0)")

    # 2. campo senza id: il JS indicizza per id -> il valore non arriva
    #    (checkbox e radio fanno eccezione: usano `name`)
    senza_id = []
    for tag, attr in campi:
        if re.search(r'\bid\s*=\s*["\']', attr):
            continue
        if re.search(r'type\s*=\s*["\'](checkbox|radio|submit|button|hidden)', attr, re.I):
            continue
        senza_id.append(f"<{tag}>")
    if senza_id:
        rep.add("FORM", BLOCK, f"{len(senza_id)} campo/i senza `id` ({', '.join(senza_id[:4])}): "
                               "il JS indicizza per id, il valore non viene inviato")

    # 3. select required la cui prima option ha gia' un value: la validazione
    #    controlla value.length, quindi non scatta mai
    for m in re.finditer(r"<select\b([^>]*)>(.*?)</select>", content, re.I | re.S):
        attr, corpo = m.group(1), m.group(2)
        if not re.search(r"\bsw-required\b", attr):
            continue
        prima = re.search(r"<option\b([^>]*)>", corpo, re.I)
        if prima and not re.search(r'value\s*=\s*["\']["\']', prima.group(1)):
            sid = re.search(r'id\s*=\s*["\']([^"\']+)', attr)
            rep.add("FORM", WARN, f"select `{sid.group(1) if sid else '?'}` e' sw-required ma la prima "
                                  "<option> non ha `value=\"\"`: la validazione non blocca mai l'invio")

    # 4. <sw-select>: la chiave del form e' <id>-input, non <id>
    for sid in re.findall(r"<sw-select\b[^>]*\bid\s*=\s*[\"']([^\"']+)", content, re.I):
        rep.add("FORM", WARN, f"<sw-select id=\"{sid}\">: nel `testo` del record Form usa "
                              f"il placeholder {{{sid}-input}} (non {{{sid}}})")

    # 5. <label> senza `for`: l'esempio di GET /forms-guide le scrive cosi',
    #    quindi l'errore si propaga per copia. Fa eccezione la label del consenso,
    #    che AVVOLGE il checkbox (li' il `for` non serve).
    labels = re.findall(r"<label\b([^>]*)>", content, re.I)
    sfuse = [a for a in labels
             if not re.search(r"\bfor\s*=", a) and not re.search(r"sw-form-privacy", a)]
    if sfuse:
        rep.add("FORM", BLOCK, f"{len(sfuse)} <label> senza `for` (campo non associato: WCAG 1.3.1/4.1.2, "
                               "il click sull'etichetta non focalizza e lo screen reader non annuncia)")

    # 6. consenso privacy senza link all'informativa: obbligo GDPR art. 13-14
    #    (informativa accessibile prima del conferimento), e manca nell'esempio
    #    della guida
    cons = re.search(r"<label\b[^>]*sw-form-privacy[^>]*>(.*?)</label>", content, re.I | re.S)
    if cons and not re.search(r"<a\b[^>]*href", cons.group(1), re.I):
        rep.add("FORM", BLOCK, "consenso privacy senza link all'informativa: aggiungi "
                               "<a href=\"/privacy-policy/\" target=\"_blank\" rel=\"noopener\">")

    # 7. bottone di invio con la classe generica del preset invece della CTA del
    #    sito: funziona (il trigger e' `sw-form`) ma stona col design
    btn = re.search(r"<button\b[^>]*\bsw-form\b[^>]*>", content, re.I)
    if btn and re.search(r"\bsw-button\b", btn.group(0)):
        rep.add("FORM", WARN, "il bottone usa `sw-button` (classe generica del preset): se il sito ha "
                              "una CTA propria usa quella + `sw-form`, che e' l'unica classe obbligatoria")

    if not (orfane or senza_id or sfuse or (cons and not re.search(r"<a\b[^>]*href", cons.group(1), re.I))):
        rep.ok("FORM", f"{len(campi)} campi form: classi, id, label e consenso conformi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page", help="id o slug della pagina")
    ap.add_argument("--swc", default="../swc", help="percorso del wrapper swc (default ../swc, da una cartella-sito)")
    args = ap.parse_args()

    page = resolve_page(args.swc, args.page)
    if not page:
        print(f"Pagina '{args.page}' non trovata (id o slug).", file=sys.stderr); sys.exit(2)
    pid, slug = page.get("id"), page.get("slug")
    print(f"Pagina: [{pid}] {slug}  ({page.get('lang')})  — {page.get('title','')}")
    content = get_content(args.swc, pid)
    css = get_css(args.swc, slug)

    rep = Report()
    check_swcss(rep, content, css)
    check_seo(rep, page, content)
    check_eeat(rep, page, content)
    check_a11y(rep, content)
    check_form(rep, content)
    sys.exit(rep.dump())

if __name__ == "__main__":
    main()
