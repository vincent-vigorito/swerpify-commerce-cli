---
name: swerpicommerce-ops
description: Guida operativa per agenti che gestiscono un sito SwerpiCommerce (piattaforma e-commerce Swerpify) via API v2/CLI — workflow completi (catalogo, pagine SWCSS, blog, mailing, carrelli abbandonati, punti fedeltà, codici sconto, design), quirk dell'API e setup multi-tenant. Usare per qualsiasi operazione su un tenant SwerpiCommerce — creazione/modifica di prodotti, pagine, articoli, campagne email, immagini, CSS/JS del tema.
---

# SwerpiCommerce Ops — guida operativa per agenti

Conoscenza operativa per lavorare sull'API v2 di SwerpiCommerce (119 path, 214
operazioni al 31/08/2026, piattaforma 2.70.6 — la superficie evolve spesso, anche in giornata:
in caso di dubbio ricontrolla `GET <base_url>/openapi.json`). Complementare
alla skill `pp-swerpicommerce` (riferimento comandi del CLI generato): qui ci
sono i **flussi giusti e gli errori già fatti**.

Approfondimenti in questa skill (leggili quando servono):
- **`references/swcss-design-system.md`** — il design system SWCSS completo:
  layer, regole, breakpoint, tree-shaking, animazioni pure-CSS, errori tipici.
  Da leggere PRIMA di creare o modificare pagine/CSS.
- **`references/cli-and-api.md`** — primer d'uso: flag globali del CLI, pattern
  con jq/heredoc, API raw con curl, forme di risposta, filtri di lista.

**Guide LIVE del tenant (markdown) — `GET` PRIMA di operare in quell'area.** Lo
schema OpenAPI descrive le *operation*, non il *funzionamento del tema*: saltare la
guida porta a **diagnosi sbagliate** (es. scambiare un problema di config per un bug
di template non risolvibile). Falle sempre prima di scrivere o diagnosticare:
- **`GET /design/templates-guide`** — HTML del tema (header, header sticky, footer,
  breadcrumbs, pagine di sistema): fork vs upstream, cascata degli slot, hook JS
  load-bearing. Vedi la sezione "Template del tema" più sotto.
- **`GET /design/swcss-guide`** — CSS/SWCSS (+ `references/swcss-design-system.md`).
- **`GET /forms-guide`** — form. ⚠️ Dal 28/08/2026 il record Form ha `azioni[]`, `destinatari[]`
  e allegati, e ha PERSO `action`/`custom_app_*` → vedi «Record Form» più sotto. Consenso iubenda (dal 15/07/2026): non più i
  campi piatti `iubenda_campo_email`/`iubenda_campo_nome` ma l'oggetto
  `iubenda_mapping` (`subject`: email/first_name/last_name/full_name → id campo;
  `preferences`: array `{key, campo}`); nel CLI i flag `--iubenda-mapping-subject-*`
  e `--iubenda-mapping-preferences`.
- **`GET /custom-apps-guide`** — custom app Django (+ contratto `<sw-select>`, il dropdown
  del checkout: NON la select dei form CMS, che è quella di `/forms-guide`).

## Stack di esecuzione

1. **CLI `swerpicommerce-pp-cli`** (primario): auth gestita, `--agent` per JSON,
   `--stdin` per i body JSON.
2. **curl** (fallback): SOLO per le route con **due path-param** — il CLI vi
   costruisce URL errati (bug noto del generatore). Route note:
   `GET/PUT/DELETE /design/css/{section}/{filename}`, `GET/PUT/DELETE /media/{folder}/{filename}`.
3. **Server MCP** (bundle `.mcpb`): stesso binario per host senza shell
   (Claude Desktop); all'installazione chiede base URL del tenant e Bearer token.

⚠️ Bug noto: molti comandi risorsa (`products`, `orders`, `customers`, `pages`,
`carts`, `email-lists`, `media`, ...) **non compaiono in `--help`** ma
funzionano. Elenco completo: `swerpicommerce-pp-cli api`.

## Setup, auth e multi-tenant

Ogni tenant ha la sua base URL (`https://<tenant>/api/v2`) e le sue chiavi API
(`api_id` + `api_secret`, dal pannello). Lo schema OpenAPI live è sempre su
`GET <base_url>/openapi.json` (pubblico): se la superficie cambia, rigenerare
il CLI da quello schema con la CLI Printing Press.

```bash
# base URL: env var, oppure base_url nel config, oppure --config <file>
export SWERPICOMMERCE_BASE_URL="https://<tenant>/api/v2"

# token (NON scade; revocabile con swerpicommerce-auth token-revoke <id>)
swerpicommerce-pp-cli swerpicommerce-auth token --api-id <ID> --api-secret <SECRET> --agent
# il token è in .data.data.token — salvalo:
swerpicommerce-pp-cli auth set-token <TOKEN>
# verifica senza effetti collaterali (chiave e permessi):
swerpicommerce-pp-cli swerpicommerce-auth me --agent
```

- Il body del token vuole **`api_id`** (non `api_key`).
- Config: `~/.config/swerpicommerce-pp-cli/config.toml` (token nel campo
  `access_token`). **Multi-tenant**: un file config per tenant (dentro:
  `base_url = '...'` + token) e `--config <file>` su qualunque comando.
- `doctor` mostra base URL attiva e stato auth: usalo a inizio sessione.

## Envelope di output del CLI (fonte classica di errori jq)

- **Letture** (GET): `.results.data` (liste con `.results.meta`); alcune
  risorse rispondono `.results` nudo.
- **Scritture** (POST/PUT/DELETE): `.data.data`.
  ⚠️ Eccezione: `vat-validations` (POST) risponde come una lettura → `.results.data`
  (verificato 25/08/2026).
- Pattern robusto: `jq '(.results.data // .results)'` per le letture,
  `jq '(.data.data // .data)'` per le scritture.
- ⚠️ **Le liste tornano max 100 record**: il default è `limit: 100` e **non c'è
  alcun avviso di troncamento** — la lista "sembra" completa. Confronta SEMPRE
  con `.results.meta.total` prima di trarre conclusioni, e passa `--limit` alto
  quando censisci. Costa caro negli audit: su String Project (191 pagine) una
  scansione senza `--limit` vedeva **1 pagina con form su 19**, e le altre 18
  risultavano "non trovate" — che in un ciclo di shell si legge come «nessun
  problema» invece che «non controllato». Se uno script risolve le pagine per
  id/slug da una lista, deve chiedere `--limit 1000` (corretto in
  `check_page.py`: `resolve_page`).
  ⭐ Regola generale: **un controllo che non ha potuto girare non è un controllo
  passato** — fai emergere il fallimento, non contarlo come zero.

## ⛔ Gli UPDATE non sono PATCH: il CLI reinvia i default (verificato 12/08/2026)

> ✅ **RISOLTO A MONTE il 20/08/2026 (B67)**: lo schema a 111 path ha rimosso i `default`
> JSON-Schema da tutti gli Input/UpdateInput (ora sono description «Default in creazione»),
> e il CLI rigenerato da quello schema **non reinvia più alcun default** — verificato con
> dry-run: `articles update <id> --meta-title X` manda solo `{"meta_title"}`. La sezione
> resta come storia e come difesa sui CLI più vecchi di quella data; `--stdin` e `--dry-run`
> restano comunque buone pratiche.

**Il rischio più serio di tutta la skill (sui CLI generati da schemi pre-20/08).** Il CLI generato mette nel body **anche i
default dello schema dei campi che NON hai passato**. Un "update di un solo campo" non
esiste: stai riscrivendo anche tutto ciò che ha un default *truthy*.

```bash
# quello che credi di fare            → quello che il CLI invia davvero
swc articles update 83 --meta-title X → {meta_title, autore:"Admin", stato:"bozza",
                                          index:true, follow:true, lang:"it"}
swc products update 34 --meta-title X → {meta_title, tipo_prodotto:"semplice",
                                          tipologia:"prodotto", um:"pezzi", stato:1, …}
```

**⭐ La difesa vera: negli update usa `--stdin`, non i flag.** Con `--stdin` il CLI manda
**esattamente e solo i campi che scrivi**, senza aggiungere un singolo default (verificato
12/08 con dry-run a confronto). È la differenza fra un update chirurgico e una riscrittura:

```bash
# ✅ update chirurgico: nel body finisce solo meta_title
echo '{"meta_title":"..."}' | swc products update 34 --stdin
# ❌ stesso intento, coi flag: parte anche tipo_prodotto:"semplice" e altri 6 campi
swc products update 34 --meta-title "..."
```

Quando i flag servono comunque, **`--dry-run` prima e leggi il body**: è l'unico modo di
vedere cosa stai per sovrascrivere, e ha già evitato di spubblicare articoli e di
degradare una variante.

Danni concreti osservati (dry-run reali):
- **`articles update`** → `stato: "bozza"` **spubblica un articolo live** e
  `autore: "Admin"` **cancella la firma**. Passa SEMPRE `--stato pubblicato --autore "<nome>"`.
- **`products update`** → `tipo_prodotto: "semplice"` **degrada una variante a prodotto
  semplice**, la scollega dal padre e riapre il 500 di B60 (vedi riga Variazioni).
  Passa SEMPRE `--tipo-prodotto variante` (o `variabile`) sugli update di catalogo.
- **`index: true` / `follow: true`** vengono rimessi su qualunque record: un contenuto
  messo a `noindex` **torna indicizzabile al primo update successivo**. È la spiegazione
  del vecchio sintomo «`--index=false` non attecchisce»: attecchisce, poi un update lo annulla.

**Quali default partono e quali no**: il CLI **omette i default falsy** (`false`, `0`) e
**invia quelli truthy** (stringhe non vuote, `true`, interi ≥ 1). Quindi `attivo: false`
di payment/shipping-methods NON parte (verificato), ma `nazione: "IT"` sì.

Difese, in ordine: **`--stdin` per ogni update** → `--dry-run` quando i flag sono
inevitabili → **rilettura con `--no-cache`** dopo la scrittura. Riferimento: report **B67**.

⚠️ **Convertire un prodotto a `variante` richiede di ripassare `valori_attributi`**, anche
se il prodotto li ha già: `{"tipo_prodotto":"variante"}` da solo → **400** «valori_attributi
obbligatorio per le varianti». Leggi le coppie dal record e rimandale insieme al tipo.

**Controllo di integrità del catalogo** (utile dopo ogni import, trova i residui della
vecchia ricetta pre-B60): cerca i prodotti che hanno `prod_principale_id` ma
`tipo_prodotto != "variante"` — sono figlie mai promosse, che restano fuori dalla macchina
delle varianti. Non inquinano le liste (l'esclusione guarda `prod_principale_id`, non il
tipo), quindi il difetto è invisibile finché non apri la scheda del padre.

```bash
swc products list --limit 500 --all --include-variants --agent \
  | jq '[.results.data[] | select(.prod_principale_id and .tipo_prodotto != "variante")
        | {id, tipo_prodotto, padre: .prod_principale_id}]'
```

## Quirk dell'API (verificati sul campo)

| Quirk | Dettaglio |
|---|---|
| ⚠️ `tipologia` ≠ `tipo_prodotto` | **Due campi diversi che in italiano si chiamano quasi uguale**, ed è la confusione che fa sbagliare gli import. **`tipo_prodotto`** = struttura del prodotto (`semplice\|variabile\|variante\|kit\|custom_box`), con enum e validazione. **`tipologia`** = natura merceologica, quella che nel pannello è «tipo prodotto» → il valore giusto è **`bene`** (o `servizio`), NON `prodotto`. ⛔ Lo schema però dichiara **`default: "prodotto"`**, che è un valore **che nessun catalogo reale usa**: verificato su due tenant con cataloghi importati e funzionanti (detergenzaprofessionale e spnew) → `tipologia: "bene"` su **200/200 prodotti** in entrambi. Chi crea prodotti senza passare `--tipologia bene` si ritrova `prodotto`, e nel pannello il campo risulta **non valorizzato** («il sistema non inserisce il tipo prodotto»). Peggiora col quirk dei default (vedi sezione UPDATE): il valore parte **anche quando non lo passi**. ✅ **Risolto il 20/08/2026 (B68)**: il campo ora ha `enum: [bene, servizio, spedizione]`, nessun default nello schema e description che lo distingue da `tipo_prodotto` — i valori sbagliati vengono respinti con 400. Resta la regola pratica: **passa sempre `--tipologia bene`** sui create. Report **B68** |
| Firma degli articoli | Il default `Admin` di `autore` è ora solo **server-side alla creazione** (dal 20/08 lo schema non ha più `default` e il CLI non lo reinvia negli update — B67); dal 20/08 c'è anche **`GET /articles/authors`** (gli autori del select del pannello: il `nome` è il valore da passare) e il campo `mostra_autore` per la byline. Se il blog ha una firma editoriale, `--autore "<nome>"` va passato **a ogni create** (altrimenti l'articolo nasce firmato «Admin»). La firma compare nella **lista** del blog (`.sw-blog-autore`), non nella scheda: verificala lì. Se il tema usa JSON-LD, allinea anche `author` nei `markups` — il markup e la firma visibile devono dire la stessa cosa |
| Placeholder email | **Graffa singola** `{nome}`, NON `{{nome}}` (le description dello spec sbagliano). Risolti da `variabili` + dati cliente (`nome`, `cognome`, `email`); quelli senza valore restano intatti |
| Booleani sui codici sconto | `attivo`/`cumulativo` sono **interi 0/1** (gli articoli invece usano `true/false`) |
| Date codici sconto | `data_scadenza` solo `YYYY-MM-DD` |
| Campi sconosciuti | ✅ **Validazione strict ovunque (retest 11/08/2026, B9 risolta)**: un campo non previsto → **400 VALIDATION_ERROR** «Additional properties are not allowed». Non esiste più il fallimento silenzioso; la rilettura post-scrittura resta comunque buona pratica |
| Punti fedeltà | `punti_totali` segue anche i delta negativi (non è "totale storico maturato") |
| Email cliente | `null` nella lista; c'è solo nel **dettaglio** (`customers get`) — arriva dall'account di login |
| Indirizzo cliente | Dal 25/08/2026 c'è `indirizzo_2` (interno, scala…) su `Customer`, `customers create/update` (flag `--indirizzo-2`, CLI regen 25/08) e sugli item di `indirizzi_spedizione` — verificato live in create/update |
| Variazioni prodotto | ✅ **Creabili via API dall'11/08/2026** (fix B60): padre `tipo_prodotto: "variabile"`, figlie `tipo_prodotto: "variante"` + `prod_principale_id` + `valori_attributi: [{"attributo":"Formato","valore":"5 L"}]` — le coppie sono **risolte contro il registro attributi** (`GET /attributes`, match esatto **case-sensitive**; valore inesistente → 400 con l'elenco degli ammessi). Il registro si gestisce anche via API dal 20/08/2026 (`POST /attributes`, `POST /attributes/{id}/values`, PUT/DELETE; delete → 409 se in uso, niente cascata). Le varianti nascono con lo **slug del padre** (nessuna pagina autonoma). Sugli altri tipi gli stessi `valori_attributi` sono descrittivi e alimentano i filtri di categoria; l'array **sostituisce integralmente** il set precedente (in un update parziale, ometterlo per non perderlo). ⚠️ Il **padre senza `prezzi` manda la sua scheda in 500**: valorizza sempre il prezzo anche sul padre. Lista: `--include-variants=true` (di default le variazioni sono escluse) |
| Stato articoli | enum `bozza\|pubblicato\|archiviato`; ordini: stringa libera, default `in_attesa_pagamento` |
| Immagini e documenti | base64, **senza limite applicativo di dimensione** dal 01/09/2026 (2.71.0; verificato: PDF da 24,7 MB → 201 — prima 10 MB decodificati / body 16 MiB → 400 `IMAGE_TOO_LARGE` / 413 `PAYLOAD_TOO_LARGE`, B78); sui file grandi alzare il timeout del client (`--timeout 300s`); jpg/png/webp/gif/avif; svg/ico nella cartella `custom` (il tema — ex `logos`, alias ancora attivo); pdf/doc/docx/xls/xlsx nella cartella `media` (serviti da `/uploads/media/` con `Accept-Ranges`). Upload prodotto con `tipo: main` **sostituisce ed elimina** la main precedente. L'upload media restituisce `valore_campo` da usare nei campi immagine (es. `immagine_evidenza`) |
| Import da gestionale: `id` esplicito | Dal 28/08 (2.70) `POST /products`, `/customers`, `/orders` (e le righe `prodotti[]`) accettano un **`id`** opzionale usato come chiave primaria (flag `--id`): occupato → **409** `PRODUCT_ID_TAKEN` / `CUSTOMER_ID_TAKEN` / `ORDER_ID_TAKEN` / `ORDER_LINE_ID_TAKEN`, nessun record creato; dopo la creazione la sequence viene riallineata. **Guard anti-duplicato**: `sku` già presente nella stessa `lang` → **409 `PRODUCT_DUPLICATE_SKU`** (con l'id esistente: usa `PUT`), stesso `sku` su lingue diverse ok; combinazione di variante già esistente → 409 `PRODUCT_DUPLICATE_VARIANT`. L'ordine dei valori di un attributo nell'anagrafica comanda anche selettori e filtri (2.70) |
| Scorrimento laterale su mobile nella scheda prodotto | Colpa del **tooltip dei punti fedeltà** (preset `prodotto/componenti.css`): box da 16rem centrato su un wrapper a ridosso del bordo destro → sporge di ~60 px anche a `opacity:0` e allarga il documento. Diagnosi in 1 riga nel browser a 390 px: elementi con `right > clientWidth` NON dentro contenitori `fixed`/`overflow:hidden` (minicart e `sr-only` sono falsi positivi). ✅ **Risolto a monte in 2.66.5 (26/08 sera)**: il preset ha ora `@media (--mb) { .sw-prod-points-wrap .sw-tooltip { left:auto; right:0; transform:none } }`; il file tenant `zz-tooltip-mobile.css` usato come workaround su cosicome è stato rimosso (retest 375/375). Su un tenant fermo a una versione precedente, quel file resta la pezza. Report **B77** |

## ⭐ La regola d'oro del design: COMPILE

**Nulla di pagine/CSS va live finché non esegui `design compile`** (~1.3s,
tree-shaking sulle classi usate nei template). Vale per: contenuto pagine
nuovo E aggiornato, file CSS. NON serve per: il JS per-pagina (live subito) e
i dati (prodotti, articoli, ordini...).

```bash
swerpicommerce-pp-cli design compile --agent   # sempre, dopo modifiche design
```

⚠️ **Un prodotto/articolo NUOVO non ha bisogno di `compile`, ma la sua scheda risponde
404 finché non esegui `cache flush`** (la cache del negozio non conosce ancora quello
slug). Sintomo tipico: il prodotto compare nella pagina categoria ma il link dà 404 →
non è un dato sbagliato, è la cache. Chiudi sempre l'inserimento con:

```bash
swerpicommerce-pp-cli cache flush --agent && curl -so /dev/null -w '%{http_code}\n' <url-scheda>
```

## ⭐ Asset e CDN: prefisso `{{ STATIC_WEB_URL }}` (obbligo, dal 30/07/2026)

Ogni URL asset — `/static/...` E `/uploads/...` — in **template fork e contenuti
pagina** va scritto col prefisso `{{ STATIC_WEB_URL }}`:

```html
<img src="{{ STATIC_WEB_URL }}/static/img/uploads/foto.webp" alt="...">
<a href="{{ STATIC_WEB_URL }}/uploads/blog/scheda.pdf">Scheda tecnica</a>
```

- È la variabile di contesto del **CDN**: risolve nel dominio CDN del tenant quando
  la CDN è attiva, **stringa vuota quando è off** (path relativi identici) → il
  prefisso è SEMPRE sicuro, mettilo a prescindere dallo stato della CDN.
- Vale anche per gli **URL assoluti** col dominio del tenant
  (`https://<dominio>/static/...` → `{{ STATIC_WEB_URL }}/static/...`), tipici di
  PDF e link copiati.
- Config per-tenant: `cache get` → `config.cdn_url`/`cdn_cache`; attivazione con
  `cache config` (decisione del cliente/team, non attivarla di tua iniziativa).
- **Se ne occupa la piattaforma** (non toccare): asset del layout base
  (cms.css/JS/favicon), pagine di sistema, immagini prodotto, `url()` nei CSS
  (seguono l'origine del file CSS).
- **NON usarlo dove non risolve** (non è markup templato): corpo degli **articoli
  blog** (`{{ articolo.contenuto|safe }}`) e **file JS** per-pagina — lì i path
  restano relativi all'origine (funzionano, semplicemente non passano dalla CDN).
- Il Cancello 1 (`check_page.py`) lo verifica: asset nudo nel contenuto = ❌.

## ⭐ Il cancello pre-publish: conformità SWCSS · SEO · EEAT · a11y

Ogni pagina che pubblichi deve passare due cancelli, **prima** di considerarla
fatta. La skill *insegna* queste regole, ma un modello può leggerle e non
seguirle: la garanzia è il **check deterministico**, non la buona volontà.

**Cancello 1 — statico (deterministico, model-agnostico).** Dopo aver scritto
contenuto + CSS (anche prima di `compile`), da una cartella-sito:

```bash
python <skill>/scripts/check_page.py <id-o-slug>   # 0 bloccanti = passa
```

Scansiona record+contenuto+CSS e blocca (❌) o segnala (⚠️) su 4 dimensioni:

- **Conformità SWCSS** — ❌ hex cablati (colori SOLO `var(--sw-*)`; tinta nuova →
  `POST /design/colors`), ❌ `<style>`/`<script>`/`style=` con property reali
  inline (ok solo `style="--var: valore"` per passare un DATO a barre/meter),
  ❌ URL asset `/static/`//`uploads/` senza prefisso `{{ STATIC_WEB_URL }}`
  (vedi sezione Asset e CDN; ⚠️ se assoluti col dominio),
  ❌ larghezza del sito reimplementata (wrapper generico `*-wrap`/`*-container`/
  `*-inner`, token `--x-wrap` o `max-width` ~80rem/1280px + `margin auto`: solo
  `.sw-container`, regola 2 dal 2.73; un `max-width` di componente più stretto
  passa), ⚠️ contenuto senza alcun `.sw-container`,
  ⚠️ `font-size` in px (usa `var(--text-*)`), ⚠️ `!important`, ⚠️ shorthand
  `padding: v 0 v` che azzera il gutter.
- **SEO** — ❌ `meta_title`/`description` assenti (lunghezze ~30–60 / ~120–160),
  ❌ `<h1>` non unico, ⚠️ gerarchia heading con salti, ⚠️ `llms_description`/
  `llms_section` vuote, ⚠️ index/sitemap incoerenti (es. noindex nel sitemap).
- **EEAT** — ⚠️ dato strutturato JSON-LD assente (`markups`: schema pertinente
  Organization/Product/FAQPage/BreadcrumbList). Il resto dell'EEAT (esperienza
  reale, fonti, firma/autore, dati verificabili) è **giudizio di contenuto**, non
  lint-abile: curalo a mano.
- **Accessibilità** — ❌ `<img>` senza `alt`, ⚠️ testo-link generico
  ("clicca qui"), ⚠️ input senza `<label for>`/`aria-label`, ⚠️ `<a>`/`<button>`
  vuoti.

**Cancello 2 — renderizzato (browser, sulla pagina LIVE dopo `compile`).** Ciò
che lo statico non può vedere. Incolla `scripts/a11y_audit.js` in
`browser_evaluate` (audit strutturale + contrasto) e verifica anche gli stili
calcolati — nessun link più grande del testo che lo contiene, contenuto che non
tocca i bordi su mobile (misura `getComputedStyle`, non "sembra ok").
- **`contrasto_fail`** = veri (testo su sfondo SOLIDO sotto 4.5:1 / 3:1 large): correggi.
- **`contrasto_da_rivedere`** = testo su GRADIENTE/immagine: il colore di sfondo
  effettivo non è calcolabile in JS → **non sono fail automatici**, guardali a
  occhio (è il motivo dei falsi "bianco su bianco 1:1"). Non inseguirli come bug.
- **`id_duplicati` con `cart_el`** = header default della piattaforma (report **B53**),
  non è un difetto della pagina → ignoralo nell'audit per-pagina.
- **`link_inline_solo_colore`** = link dentro un paragrafo che si distingue dal testo
  **solo per colore**, con contrasto link↔testo < 3:1 (WCAG 1.4.1): sono fail veri,
  vedi la regola sulla sottolineatura qui sotto. Menu, card, bottoni e CTA sono esclusi
  dal controllo (il contesto li rende già riconoscibili).

Regola: **una pagina è "fatta" solo dopo Cancello 1 (0 ❌) + Cancello 2 (axe 0).**

## Costruzione dei link `<a>` (design · a11y · SEO)

- **Sottolineatura**: di default **senza underline** (il link si distingue per colore/peso,
  coerente col design system) — **ma la regola ha un'eccezione che NON è opzionale**, ed è
  il caso più frequente sui form.
  ⚠️ WCAG 1.4.1 *Uso del colore*: un link **inline nel testo corrente** che contrasta col
  testo circostante **meno di 3:1** deve avere un secondo segnale — `text-decoration:
  underline` oppure un `font-weight` più pesante di almeno 200 — **nello stato di riposo**.
  L'`:hover`/`:focus` **non basta**: non è percepibile senza interazione, e chi non usa il
  mouse non lo incontra mai. Misura il rapporto, non fidarti dell'occhio: il caso tipico
  (link scuro su testo grigio) sembra distinguibile e sta a **1.77:1**.
  Nei menu/card/bottoni/CTA la sottolineatura non serve (già distinti dal contesto).
  → Verificato dal Cancello 2 (`link_inline_solo_colore`). **Il link all'informativa
  privacy nel consenso del form è l'esempio da manuale**: è inline in un paragrafo, quindi
  se il contrasto col testo è basso **va sottolineato**, e toglierlo è una regressione a11y,
  non una pulizia stilistica.
- **`target`**:
  - Link **interni** (stesso sito) → **stessa scheda, mai `_blank`**.
  - Link **esterni** → `target="_blank"` solo se vuoi la nuova scheda, e **sempre** con
    `rel="noopener"` (sicurezza: blocca l'accesso a `window.opener`); aggiungi `noreferrer`
    se non vuoi passare il referrer.
- **`rel` per la SEO**:
  - **Interni** → **nessun `rel`** (MAI `nofollow` sugli interni: l'equity deve fluire).
  - **Esterni editoriali/di fiducia** (fonti citate, partner reali) → **followed**, cioè
    **nessun `nofollow`** → positivo per l'EEAT (dimostra che citi fonti reali); solo
    `rel="noopener"` se in `_blank`.
  - **Esterni sponsorizzati/affiliati/pubblicitari** → `rel="sponsored"`.
  - **Esterni da contenuti utente** (commenti/UGC) → `rel="ugc"`.
  - **Esterni non fidati / da non avallare** → `rel="nofollow"`.
  - Combinabili: link affiliato in nuova scheda → `rel="sponsored noopener"`.

```html
<a href="/servizi/siti-web/">Interno</a>                                    <!-- niente target, niente rel -->
<a href="https://fonte-autorevole.it/studio" target="_blank" rel="noopener">Fonte esterna</a>
<a href="https://affiliato.example/x" target="_blank" rel="sponsored noopener">Affiliato</a>
```
Il **testo** del link resta sempre descrittivo (mai "clicca qui" — già bloccato dal Cancello 1 a11y).

## Workflow: pagina nuova con stile dedicato

```
1. pages create --stdin            # title obbligatorio; il content può stare già qui
2. pages content page-update <id>  # solo l'interno del {% block content %}
3. PUT /design/css/cms/<slug>.css  # via curl (bug 2-path-param) — un file per pagina
4. design js-put <slug>.js         # opzionale: autoload per slug, defer, no compile
5. check_page.py <id/slug>         # ← Cancello 1: 0 bloccanti prima di procedere
6. design compile                  # ← senza questo non esiste
7. curl https://<tenant>/<slug>/   # verifica pubblica
8. axe + stili calcolati (browser) # ← Cancello 2 sulla pagina live: axe 0, nessun bug di layout
```

- **Leggi prima di scrivere**: `GET /design/swcss-guide` (guida ufficiale del
  design system), `design css-list --section cms`, `GET /page-templates`
  (template e preset disponibili), e il contenuto della homepage
  (`pages content page-get <id>`) come catalogo dei componenti `sw-*` esistenti.
- Classi nuove prefissate `sw-<slug>-*`; variabili `var(--sw-..., fallback)`;
  breakpoint `@media (--mb|--sm|--md|--lg|--xl)` mobile-first.
- **Larghezza del sito: solo `.sw-container`** (layer globale; token `--sw-container`
  80rem + `--sw-container-pad`; `.sw-container-narrow` 48rem per i testi lunghi).
  Sezione full-bleed fuori per lo sfondo, `.sw-container` dentro per il contenuto.
  Mai reimplementarla: niente `.sw-<slug>-wrap`/`-inner`, token `--x-wrap` o
  `max-width` da 80rem/1280px tuoi (regola 2 della guida, dal 2.73 del 02/09/2026;
  `.sw-wrap` è l'alias legacy delle home storefront, non per pagine nuove). Un
  componente può avere il suo `max-width` più stretto (step 52rem, form 36rem),
  dentro il `.sw-container`.
- Animazioni allo scroll in puro CSS: `animation-timeline: view()` dentro
  `@supports` (senza supporto il contenuto resta visibile). Il tree-shaker non
  vede le classi aggiunte da JS a runtime: dichiarale in un commento del template.
- Il layer `base/` del design system non è esposto e non si tocca.
- Pagine di sistema e homepage sono protette (delete → 400 SYSTEM_PAGE).

## Template del tema (header/footer/partial + pagine di sistema) — `GET /design/templates-guide`

Gli HTML del tema si editano via API (`/design/templates/{area}/{file}`, area
`partials`|`pagine_sistema`; route a 2 path-param → **curl**), poi `compile`. Leggi
la guida live prima; qui i punti che fanno sbagliare (imparati sul campo).

- **Fork, non `*_base`.** Gli upstream (`header_base.html`, `footer_base.html`,
  `negozio.html`…) sono READ-ONLY (`PUT`/`DELETE` → **403 UPSTREAM_TEMPLATE**):
  leggili come riferimento (`GET`, `include_upstream=true` nel list) e crea/edita il
  **fork col nome canonico** (`header.html`, `header_sticky.html`, `footer.html`;
  per le pagine di sistema una variante tipo `negozio-miosito.html`). `base.html`
  (layout master) non è mai esposto: **non toccarlo**.
- **Gli slot si scelgono per CONFIG, non per nome fisso** (cascata): campi pagina
  `page.header_name`/`header_sticky_name`/`footer_name`/`breadcrumbs_name` (override
  puntuale) → record **`Header_Footer`** (default globale **per lingua**). Sticky
  vuoto ⇒ eredita il globale; vuoto anche lì ⇒ niente sticky (è dentro `{% if %}`).
  ⚠️ Perciò un header/sticky "che non va" è di norma **config, NON un bug** del tema.
  Il mega-menu è **markup a mano** nel partial header → si edita (non è auto-generato).
  ⚠️ Lo sticky (`id=menu_sticky`) usa il pattern **headroom** (nascondi scrollando
  giù / rivela scrollando su): in cima e scrollando GIÙ è `translateY(-altezza)`
  (fuori schermo, `top` negativo); scrollando SU torna a `top:0`. **NON diagnosticare
  "non si aggancia" testando solo lo scroll in giù** — verifica anche lo scroll su.
- **Fallback header per lingua**: la view fa `Header_Footer.filter(lang=X).first()`;
  se manca il record per una lingua ripiega sulla default → sintomo "pagine `ar` con
  header IT". Fix alla radice: **`PUT /header-footer/{lang}`** (upsert, vale per tutte
  le pagine di quella lingua); `page.header_name` è solo override puntuale, non per
  rattoppare un'intera lingua. `GET /header-footer` mostra le lingue senza record.
- **Hook JS load-bearing** — se li ometti il template *si vede* ma carrello, menu
  mobile e selettore lingua restano **morti** (fallimento silenzioso): root
  `id="header_basic"` (guardia di init), sticky `id="menu_sticky"`, bottoni
  `data-sw-side-lpanel`/`-rpanel` coi pannelli dagli `id` corrispondenti,
  `minicart.html` incluso **una sola volta** (solo header principale, mai nello
  sticky), selettore lingua **server-side** (`{% for lingua in lingue_data %}` +
  `onclick="…change_lang('{{ lingua.slug }}')"`, `src` reale). **Niente Vue**
  (`v-if`/`v-for`/`:src` sono inerti) **né Tailwind** (utility morte): tutto SSR
  con `{% %}`/`{{ }}`. Parti sempre da una copia del `_base`.
- **Pagine di sistema**: non modificare il default (403); crea la variante fork e
  **assegnala** → `PUT /page-templates/{tipo} {"nome_file":"<file>.html"}` (il file
  deve già esistere, altrimenti **404**; il mapping tipo→file lo leggi da
  `GET /page-templates`). Le variabili di context della view non si cambiano via API.
- **i18n**: stringhe traducibili con `{% custom_trans "id" %}` + `custom.po` (fork,
  read/write) di OGNI lingua + `bash app/compila_locales.sh` (il `django.po` upstream
  non si tocca).
- Dopo OGNI modifica: **`POST /design/compile`** (tree-shake: un template non
  collegato ad alcuna pagina/tipo non viene scansionato → le sue classi restano senza
  stile). Poi verifica pubblica.

### ⛔ Prima del PUT: controlla il bilanciamento dei blocchi

Un template Django con `{% if %}`/`{% for %}`/`{% block %}` sbilanciati **non degrada:
manda in 500 TUTTE le pagine di quel tipo**, e la risposta non dice quale file né quale
riga. L'API accetta il PUT senza fiatare — la validazione non guarda la sintassi dei tag.

Sintomo tipico e fuorviante: *«un articolo del blog dà 500»* → in realtà li danno **tutti**,
mentre l'indice risponde 200 perché usa un file diverso. **Verifica sempre l'intero tipo di
pagina, non l'URL che ti hanno segnalato**: è la differenza fra cercare il bug nel contenuto
(dove non c'è) e nel template (dove sta).

Causa più frequente sul campo: **codice residuo di un merge** — si incolla la nuova versione
di un blocco e resta la coda della vecchia, con chiusure che non aprono nulla. Occhio a
`{% endfor %}`/`{% endif %}` di troppo.

**Controllo obbligatorio prima del `PUT`** — `scripts/check_template.py` (accanto agli
altri due cancelli): segnala tag orfani e blocchi mai chiusi con la riga esatta, ed esce
con codice 1 così lo puoi incatenare al caricamento.

```bash
python <skill>/scripts/check_template.py <file.html> && <PUT del template>
```

Collaudato sul caso reale che l'ha motivato: sul file rotto indica
`riga 96: 'endfor' ma il blocco aperto è 'block' (riga 9)`, sul file corretto passa.

Regola: **`GET` del template → salva una copia di backup → modifica → controllo →
`PUT` → verifica pubblica su più URL dello stesso tipo.** Il backup è ciò che ti permette
di tornare indietro senza ricostruire a memoria un file di centinaia di righe.

## Loghi, favicon e icone del tema — cartella media `custom` + `GET/PUT /design/logos`

Slot del tema: `logo_black`/`logo_white` (desktop sfondo chiaro/scuro),
`logo_mobile_black`/`logo_mobile_white`, `logo_email` (PNG consigliato),
`favicon` (ico o png). Stessa operazione del pannello **Grafica → Loghi**. Flusso:

```
1. media upload --folder custom     # la cartella del tema ('logos' resta come alias): anche svg/ico
2. design logos-update --stdin '{"favicon":"favicon.ico"}'   # assegna il nome allo slot
3. design compile && cache flush     # poi verifica /static/img/uploads/<file> -> 200
```

- `design logos-get` mostra ogni slot con `nome`, `url` (`/static/img/uploads/…`) e
  **`esiste`** = `false` quando lo slot punta a un default mai caricato (il sito serve
  un **404** su quel path). Su un tenant nuovo favicon/logo_white/logo_email sono a `false`.
- `logos-update` fa un merge: i campi non citati restano invariati.
- Errori: file non in libreria → 400 `MEDIA_NOT_FOUND`; `media delete custom/<file>` su un
  file ancora assegnato a uno slot → 400 `LOGO_IN_USE`.
- **Classificazione (dal 31/08, 2.70.11)**: nella cartella `custom` convivono loghi, favicon e
  icone; la lista espone `slots` (gli slot che puntano al file), `categoria` (dichiarata in
  upload/update: `logo`|`icona`|`altro`, solo qui — altrove 400) e `uso` (etichetta risultante,
  precedenza **slots > categoria**). Per sapere se un file è in uso guarda `slots`, non
  `categoria` (è una dichiarazione, può invecchiare). `PUT /media/custom/<file>` con `nome`
  rinomina aggiornando anche gli slot che lo puntano.
- ⚠️ **Gli slot valgono solo se un template li usa via `<img src=".../logo_*.svg">`.**
  Un header custom che disegna il logo come **testo/wordmark** (es. `header_cha.html`
  con `&Lambda;LT&Lambda;VILL&Lambda;`) NON legge lo slot → lì il logo si cambia nel
  template, non con `logos-update`. Lo slot che conta comunque è `logo_email` (le email).
- Nei partial il `src` del logo si compone da slot + prefisso CDN:
  `src="{{ STATIC_WEB_URL }}/static/img/uploads/{{ logo_black }}"` (vedi sezione
  Asset e CDN e la tabella variabili in `GET /design/templates-guide`).

## Tab extra della scheda prodotto — `/extra-tabs` (dal 26/08/2026, piattaforma 2.66)

Tab aggiuntivi della vetrina prodotto (pannello Marketing & SEO → Tab Extra). Due tipi:
**`generale`** = un solo `html_content` su tutti i prodotti dell'ambito; **`specifico`** =
il tab compare vuoto nella scheda admin dei prodotti dell'ambito e **ogni prodotto scrive il
suo HTML** — in vetrina compare solo dove è compilato. L'**ambito** ha lo schema degli sconti
quantità: `target_prodotti` (`tutti`|`categorie`|`prodotti`) + liste `prodotti`/`categorie`
di `{id, escluso}`; sottocategorie comprese, le varianti ereditano dal padre; nell'update
le liste **sostituiscono** per intero l'ambito.

```bash
# tab generale su una categoria (slug omesso → dal nome; unico per lingua, 409 EXTRA_TAB_DUPLICATE_SLUG)
echo '{"nome":"Scheda tecnica","tipo":"generale","lang":"it","target_prodotti":"categorie",
       "categorie":[{"id":12}],"html_content":"<p class=\"sw-prod-text\">…</p>"}' | swc extra-tabs create --stdin --agent
# tab specifico: prima il tab, poi il contenuto PRODOTTO PER PRODOTTO (upsert per tab_id)
echo '{"tab_extra":[{"tab_id":1,"html_content":"<p>…</p>"}]}' | swc products update 29 --stdin --agent
swc products get 29 --agent | jq '.results.data.tab_extra'   # elenca anche i specifici ancora vuoti (per sapere i tab_id)
```

- **`nome_interno`** (dal 26/08 sera, 2.66.5): nome per il pannello, per distinguere tab con lo stesso
  titolo in vetrina (`nome`); se dato, **lo slug nasce da lui** alla creazione e poi resta stabile
  (cambiarlo in update NON cambia lo slug → id DOM invariato; verificato). ⚠️ `--attivo=false` dai
  flag **non parte** (il CLI omette i falsy): per creare un tab sospeso usa `--stdin` con `"attivo":false`.
- `html_content: ""` su un prodotto **toglie** il tab da quel prodotto; i `tab_id` non citati
  restano; un `tab_id` di tipo `generale` → **400 EXTRA_TAB_NOT_SPECIFIC** (il suo HTML si
  scrive su `extra-tabs update`). `delete` di un tab specifico cancella anche i contenuti
  per-prodotto (`deleted_contenuti`). I prodotti espongono anche `rating` (recensioni approvate).
- Id DOM in vetrina: `tab-extra-<slug>`. HTML con le stesse regole della descrizione prodotto
  (classi `sw-*`, niente stile inline).
- ⛔ **La vetrina mostra il tab solo se il template prodotto IN USO contiene i blocchi
  `{% for tab in tab_extra %}`** — l'upstream `prodotto-singolo.html` li ha dal 26/08 (7 punti:
  sezioni espandibili mobile, nav desktop `data-sw-tab="tab-extra-{{ tab.slug }}"`, pannelli
  `id="tab-extra-{{ tab.slug }}"` con `{{ tab.html|safe }}`, layout a pagina singola), **i fork
  creati prima NO** (es. `prodotto-singolo-cosicome.html`: verificato 26/08 — tab attivo,
  prodotto nell'ambito, `products get` lo espone, DOM vuoto; `cache flush` e `design compile`
  non c'entrano). Stesso discorso per le recensioni (`recensioni_attive`/`tab-recensioni`).
  Diagnosi: `GET /design/templates/pagine_sistema/<fork>.html | grep -c tab_extra` → 0 = da
  portare dall'upstream (backup → `check_template.py` → PUT → compile → verifica DOM).
  **Fatto su cosicome il 26/08**: i 7 blocchi si innestano subito dopo i 7 blocchi «Spedizione e
  Resi» del fork (sezione espandibile mobile, nav+pannelli `tabs_integrated_tabs`, stacked
  integrato, nav+pannelli `tabs_separate_tabs` con suffisso `-separate`, stacked separato) —
  ancoraggi univoci a stringa, verificato con Cancello 2 desktop (1440) e mobile (390:
  griglie del kit a 1 colonna, gutter 24 px). Un tab `generale` scritto col kit delle
  descrizioni (`sw-cc-scheda`/`sw-cc-lux-sezioni`/`sw-cc-punti`/`sw-cc-nutri-nota`) rende
  identico alla descrizione, senza CSS nuovo.
- Dal 26/08 anche: **`reviews`** (`list/get/update/delete`, `meta.recensioni_attive` nella lista,
  `stato: approvata` pubblica e aggiorna il rating) + **`review-requests`** (coda inviti, `send`);
  **`vat-groups list`** (codici `@UE`, `@AFRICA`, … usabili come `codice_nazione` in `vat-rates`)
  e **`vat-rules get/update`** (regime IVA internazionale, VIES); `applica_custom_box` sugli
  sconti quantità; cartella media **`media`** (dal 26/08 sera: cartella libera, immagini E documenti
  pdf/doc/docx/xls/xlsx da linkare nelle pagine — la `documenti` del mattino non esiste più).

## Icona carrello e area account (2.70, 28/08/2026)

- **Icona carrello: il tag `{% cart_icon %}`, mai `<img>` né data-URI** (dal 31/08, 2.70.6 —
  sostituisce la regola «SVG inline a mano» del 28/08). Un solo file per-istanza,
  `/static/img/uploads/cart-icon.svg` (seminato dall'hook 2.70.2; se manca il tag ricade sul
  default tracciato), che il tag **inlinea nel DOM** con la classe che gli passi:
  ```django
  {% load icone %}
  {% cart_icon class="sw-cart-icon" %}                                   {# header: decorativa #}
  {% cart_icon class="sw-checkout-cart-icon" label=_("Icona Carrello") %} {# checkout: nome proprio #}
  ```
  Perché inline: il disegno usa `stroke="currentColor"` e il colore lo dà il CSS
  (`#header_basic .sw-cart-icon { color: var(--sw-titoli) }`, bianco su header trasparente) —
  dentro un `<img>` o un `url("data:…")` l'SVG è un documento a sé, `currentColor` diventa nero
  e su header trasparente l'icona sparisce (il data-URI in CSS resta ok solo per icone a
  **colore costante**: chevron delle select, spunte). Due argomenti con un motivo non ovvio:
  `class="…"` **letterale** (il tree-shake estrae le classi dal sorgente cercando `class="…"`:
  con un altro nome o posizionale la classe sparisce dal bundle); `label` vuota = decorativa
  (`aria-hidden`), valorizzata = `role="img"` con quel nome (dove l'icona è l'unico contenuto
  del link). Per cambiare disegno si **sostituisce il file**, non i template: sta nella libreria
  media, cartella `custom` (`media upload --folder custom --filename cart-icon.svg`, servito da
  `/static/img/uploads/cart-icon.svg`); **non è uno slot** di `design logos-get/update`. Deve
  restare `stroke`/`fill="currentColor"`, altrimenti il tema non lo colora. I fork
  header con l'SVG scritto a mano (fresenium) **continuano a funzionare**: migrarli al tag quando
  si tocca l'header, così header e checkout leggono lo stesso file. **Fatto su cosicome il 31/08**
  (ricetta): il disegno del fork (carrello pieno, viewBox 446) caricato come file unico —
  `media delete custom/cart-icon.svg` **prima** dell'upload (lo storage rinomina in caso di
  omonimia), file senza `class`/`<title>` (il tag riscrive `class`/`role`/`aria-*`, il `<title>`
  farebbe tooltip e doppio nome) — poi nei partial `{% load icone %}` in testa e
  `{% cart_icon class="sw-cart-icon" %}` al posto dell'`<svg>`, `check_template.py`, PUT, compile.
  Il file va in `custom` (`categoria: icona` per documentarlo); dal 31/08 la ricetta è anche
  nella description dello schema (`GET /openapi.json`, sezione icone).
- **Restyle dell'area account** (`default/mio-account/*`: stati ordine sui token della palette,
  componenti/tabs rivisti) è **solo nel default**: i tenant già provisionati tengono i preset vecchi
  (verificato su cosicome: per-istanza = default pre-restyle, bundle `account.css` invariato).
  Report **B80**. Finché non c'è un hook, l'unica via su un tenant esistente è ricopiare i 5 file
  (`componenti`, `ordini`, `recensioni`, `tabs`, `variabili`) dal default via
  `fork file-get --path src/swcss/default/mio-account/<file>` → `PUT /design/css/mio_account/<file>`
  + compile — fatto su cosicome il 29/08 (i file restano `predefinito: true`; prima verifica con
  md5 che il per-istanza sia il default vecchio e non una personalizzazione del tenant).

## Automazioni e tag cliente — `/automations`, `/customer-tags` (dal 03/09/2026, piattaforma 2.73)

Il motore «Mailing → Automazioni» del pannello, via API: un'automazione è
`trigger_evento` (+ `trigger_filtri[]` sul payload dell'evento) → `flusso.nodi[]`
in catena, nodi di tipo `azione` | `attesa` | `condizione` (rami `si`/`no`) |
`fine` (implicito).

```bash
swc automations lookups-get --json        # PRIMA di scrivere: eventi (coi campi filtrabili), tipi di
                                          # azione/condizione, operatori, unità di attesa, campi cliente
                                          # aggiornabili, template email, tag, listini, liste, lingue,
                                          # segnaposto {chiave} — sono le select dell'editor del pannello
swc automations list [--stato attiva] [--trigger-evento order.confirmed]   # contatori + `riassunto` (chip)
swc automations get <id>                  # dettaglio col grafo `flusso`
swc automations create --stdin <<'JSON'   # nasce in `bozza`; grafo validato → 400 INVALID_FLOW col motivo
{"nome": "Benvenuto IT", "trigger_evento": "customer.created",
 "trigger_filtri": [{"campo": "lang", "operatore": "=", "valore": "it"}],
 "flusso": {"nodi": [
   {"id": "n1", "tipo": "attesa",  "config": {"quantita": 1, "unita": "giorni"}},
   {"id": "n2", "tipo": "azione",  "config": {"tipo_azione": "invia_email", "template_id": 12}},
   {"id": "n3", "tipo": "azione",  "config": {"tipo_azione": "aggiungi_tag", "tag": "benvenuto"}}]}}
JSON
swc automations update <id> --stato attiva       # richiede ≥ 1 nodo; `in_pausa` ferma i nuovi avvii (le attese
                                                 # pendenti si annullano al risveglio); `flusso` SOSTITUISCE il grafo
swc automations test automation <id> --email tu@dominio.it   # il tasto «Test»: email vere ma solo a quell'indirizzo,
                                                 # webhook/tag/campi simulati, attese saltate, condizioni sull'email
                                                 # → ramo SI, `test: true` fuori dalle statistiche; --stdin flusso
                                                 # per provare un grafo non ancora salvato
swc automations run automation <id> --cliente-id 7           # esecuzione REALE (attese reali); in alternativa
                                                 # --payload '{…}' nella forma dell'evento (GET /webhook/openapi);
                                                 # filtri del trigger non passati → 200 con data: null
swc automations executions automation-list <id> [--stato errore]   # log dal più recente: entità, stato,
                                                 # errore, `passi[]` nodo per nodo (esito + dettaglio)
swc automation-settings get / update --retention-giorni 90   # pulizia esecuzioni chiuse (0 = mai)
swc automations delete <id>                      # via anche il log e le email tracciate collegate
```

- **Eventi**: i 6 dei webhook (`customer.created/updated`, `order.created/updated`,
  `cart.abandoned`, `form.submitted` — stesso payload di `GET /webhook/openapi`) più il
  ciclo di vita ordine (`order.pending_payment/confirmed/processing/shipped/cancelled/
  refunded/failed`), `cart.recovered`, `customer.birthday`, `newsletter.subscribed/
  unsubscribed`, `list.subscribed`, `points.credited/expiring`, `product.back_in_stock`,
  `review.created/requested/rewarded`.
- **Stati**: `bozza` → `attiva` ↔ `in_pausa`; `errore` = attiva ma ultima esecuzione
  fallita (`ultimo_errore`). Esecuzione: `in_corso` / `in_attesa` (`riprendi_alle`) /
  `completata` / `errore` / `annullata`; `durata_ms` esclude le attese.
- **Azioni** (`config.tipo_azione`): `invia_email` (`template_id`, `destinatario` default
  `{email}`, `oggetto` override), `aggiorna_campo` (`campo` ∈ lang/tipo/listino_id/
  lista_email_id/nazione/provincia/citta/telefono + `valore`), `webhook` (`url`,
  `secret`), `aggiungi_tag`/`rimuovi_tag` (`tag`). I testi accettano i segnaposto
  `{chiave}` di `lookups-get`. Il dettaglio completo dei `config` per tipo di nodo è
  nella description dello schema `AutomationNode` (`swc automations create --help`).
- I flag `--stato`/`--trigger-evento` mostrano il primo valore dell'enum come
  placeholder in `--help`, ma **non** vengono reinviati se non li passi (verificato
  in `--dry-run` il 03/09): `update --nome X` manda solo `nome`.
- Al 03/09/2026 nessun tenant (cosicome, spnew, detergenza) ha automazioni: comandi
  verificati in lettura (200, elenco vuoto), `lookups-get` e `--dry-run`; nessun
  giro di scrittura reale ancora fatto.

**Tag cliente** — catalogo condiviso (`nome` case-insensitive, normalizzato in
minuscolo; `colore` = variante badge del pannello: neutral/primary/success/warning/
danger/info/purple/rose/amber/cyan):

```bash
swc customer-tags list                                   # ogni tag col numero di clienti
swc customer-tags create --nome vip [--colore amber]     # esiste già → 200 col tag esistente
swc customers tags customer-add <id> --nome vip          # idempotente, crea il tag se manca
swc customers tags customer-remove <id> vip              # il tag resta nel catalogo
swc customer-tags delete <tag-id>                        # lo toglie a TUTTI i clienti
swc customers update <id> --tags '["vip","b2b"]'         # SOSTITUISCE l'insieme; il flag è un JSON array
                                                         # ("vip,b2b" → errore di parsing); tag mancanti creati
```

`customers get` espone `tags[]` (nomi); le automazioni li leggono/scrivono con
`aggiungi_tag`/`rimuovi_tag` e `lookups-get` li elenca.

## Catalogo vetrina — `/vetrina/*` (dal 03/09/2026, piattaforma 2.75)

Modulo **vetrina** = catalogo di prodotti **consultabili ma non acquistabili** (schede con
foto, caratteristiche e PDF, categorie a più livelli). Non cambia `tipo_sito` (il sito resta
istituzionale): `site-info` lo espone in `moduli.vetrina`, le pagine di sistema sono
`vetrina` (`/catalogo/`), `vetrina-categoria`, `vetrina-prodotto` (enum `SystemPageType`).
Cartelle media dedicate: `vetrina_prodotti` (foto), `vetrina_categorie` (immagini
categoria), `vetrina_schede` (solo PDF). Gli endpoint rispondono 200 anche a modulo spento
(verificato su cosicome: `moduli.vetrina: false`, elenchi vuoti); si attiva dal pannello.

```bash
swc vetrina categories-list [--categoria-padre-id 0] [--lang it]   # 0 = solo primo livello; ogni voce ha
                                                                    # percorso (detergenti/autovetture), url, immagine_url
swc vetrina category-create --nome "Detergenti" [--categoria-padre-id 3] [--immagine f.jpg] [--descrizione-breve …]
swc vetrina category-update <id> --stdin           # parziale; slug omesso = invariato; padre = sé/discendente → 400 INVALID_PARENT
swc vetrina category-delete <id>                   # sottocategorie in cascata, i prodotti restano (categoria_id null)
swc vetrina products-list [--q lucida] [--categoria-id 3 --include-sottocategorie] [--in-evidenza] [--sort -ultima_modifica]
swc vetrina product-create --nome "…" --codice 0107004 --sottotitolo "…" --categoria-id 3 \
    --caratteristiche '[{"nome":"pH","valore":"7"},{"nome":"Confezione","valore":"1 L"}]'   # JSON array (sostituisce tutto)
swc vetrina products-batch --stdin                 # {"items":[VetrinaProductInput…]} → errors[] per item con index e nome
swc vetrina product-update <id> --stdin            # parziale (verificato in --dry-run: manda solo i campi passati)
swc vetrina product-image-upload <id> --source-folder media --source-nome foto.jpg --principale   # file già in libreria
swc vetrina product-image-upload <id> --filename foto.jpg --content "$(base64 -i foto.jpg)" --alt "…"   # upload diretto
swc vetrina product-images-list <id> · product-image-update <id> <image_id> --posizione 0 · product-image-delete <id> <image_id>
swc vetrina product-datasheet-upload <id> --source-folder vetrina_schede --source-nome scheda.pdf   # o --filename/--content
swc vetrina product-datasheet-delete <id>          # senza scheda → 404 DATASHEET_NOT_FOUND
swc vetrina product-delete <id>                    # i file restano in libreria (DELETE /media per toglierli)
```

- `slug` generato dal nome se assente, unico per lingua (categorie: per padre+lingua),
  suffisso `-2`/`-3` sui conflitti; in update **omesso = invariato**.
- Ogni traduzione è un record separato (`lang`); `in_evidenza` = radice del catalogo,
  max 8 per `ordinamento`; `attivo: false` = bozza (404 sul sito).
- `descrizione` (prodotto e categoria) è HTML: indentato, un tag per riga, e vale il
  cancello (niente stili inline, classi `sw-*`).
- `source: {folder, nome}` referenzia il file così com'è se è già in `vetrina_prodotti`/
  `vetrina_schede`, altrimenti lo **copia** in `/uploads/vetrina/…`; con `source`, `alt`
  omesso eredita quello della libreria.
- Al 03/09/2026 nessun tenant ha il modulo attivo: comandi verificati solo in lettura e
  `--dry-run`.

## Redirect 301/302 — `/redirects` (dal 16/07/2026)

Motore di redirect gestito (pannello Impostazioni → Redirect). Utile alle
**migrazioni** (URL vecchi di un altro CMS → nuovi percorsi) per non perdere SEO.
`redirects list/create/get/update/delete`. Campi del `create`:

- `--nome` (obbl.): etichetta descrittiva.
- `--origine` (obbl.): path da reindirizzare (`/vecchio-url/`) **oppure URL
  assoluto** (`https://dominio/path`) per redirect da un dominio esterno.
- `--destinazione` (obbl.): path relativo o URL assoluto.
- `--origine-tipo`: `Inizia con` (**default**) · `Finisce con` · `Contiene` ·
  `Regex`. ⚠️ Non c'è "esatto": per un match esatto usa `Regex` con `^…$`, o
  affidati a `Inizia con` sul path completo se gli slug non sono prefissi l'uno
  dell'altro. Un blanket-regex sui path di root è pericoloso sul nuovo dominio
  (reindirizzerebbe anche `/servizi/`, `/contatti/`…): meglio regole esplicite.
- `--status-code`: `301` (**default**, permanente/SEO) · `302`/`307` (temporaneo).

⚠️ **Ogni mutazione rigenera e ricarica la config nginx**: per un import massivo
(es. 64 articoli blog) mandare i `create` **in sequenza, non in parallelo**.

## Workflow: recupero carrelli abbandonati

```
1. carts list --abbandonato=true --older-than=24 --agent   # flag marcato da un job server
2. per ogni carrello con email:
   discount-codes create --stdin    # codice monouso: max_utilizzo_per_utente=1, scadenza breve
3. emails send --cliente-id <id> --template-id <tpl> --variabili '{"codice_sconto":"..."}'
   # transazionale sincrono via SMTP Marketing (richiede SMTP configurato nel pannello)
4. ai run successivi: carts list --recuperato=true per misurare il recupero
```

## Workflow: campagna mailing

```
1. email-templates create --stdin   # nome, oggetto, contenuto_html (placeholder {nome})
2. email-lists create + subscribers add (idempotente; remove = soft-delete, conserva i consensi)
3. campaigns create --stdin         # liste_ids multiple; il template viene COPIATO alla creazione
   # → modifiche successive vanno fatte sulla campagna (titolo/testo), non sul template
4. campaigns send campaign <id>     # costruisce la coda e invia
5. campaigns stats campaign <id>    # totale/inviate/errori/in_coda (aperture/click NON tracciati)
```

HTML email: stili **inline** (i client di posta non caricano i CSS del sito),
tabelle, max-width 600px, versione testo in `contenuto_testo`.


## Dati azienda: `GET /site-info` + variabili `dati_azienda` (08/07/2026)

`GET /site-info` (read-only) ritorna i dati aziendali del tenant: ragione_sociale,
indirizzo/citta/provincia/cap/nazione, partita_iva, codice_fiscale, telefono,
email, rea, nome_sito, url_sito. Gli stessi valori sono variabili di contesto
globali nei template: `{{ dati_azienda.ragione_sociale }}` ecc. — usale nei
partial footer così i dati si aggiornano da soli dal pannello.
**Natura del sito (dal 21/07/2026)**: `site-info` espone anche `tipo_sito` +
`moduli` → usali per capire *che tipo di tenant* stai per lavorare, prima di decidere
strategia contenuti/UX. `tipo_sito` = una sola etichetta derivata dai moduli attivi:
`istituzionale` | `ecommerce` | `concessionaria` (`concessionaria` prevale su
`ecommerce` se attivi entrambi). `moduli` = flag booleani `ecommerce`/`concessionaria`/
`blog`/`crm`; il **blog è trasversale** (può stare su qualsiasi `tipo_sito`, non è un
tipo a sé). Es. String Project → `tipo_sito:"ecommerce"`, `moduli:{ecommerce,blog,crm=true, concessionaria=false}`.
Le variabili risolvono OVUNQUE: partial E template-contenuto delle pagine
(fix 08/07 — prima nei contenuti rendevano vuoto). Nei `tel:`/`wa.me` href usare
comunque il numero normalizzato hardcoded (la variabile contiene spazi e +39);
la variabile va bene per l'etichetta visibile e per `mailto:`.
⚠️ Cloudflare offusca le email nell'HTML (`/cdn-cgi/l/email-protection`): con curl
non si vedono, nel browser sì — non è un bug.

## Campi form: la select standard e le classi (verificato 12/08, aggiornato 26/08/2026)

**La select dei form CMS è la `<select>` nativa con `sw-form-select`** — è quella di
`GET /forms-guide` e del preset `cms/form.css` (freccia SVG, `appearance:none`, stessa
base degli altri campi). ⛔ **`<sw-select>` NON è la select dei form**: è il web
component del checkout (`pagamento.html`: nazione/provincia) e delle custom app; in un
form CMS rende **con la grafica del checkout** (icona di ricerca, input readonly,
dropdown appeso al body), non con quella standard — vedi la sezione dedicata più sotto.

**Storia delle classi (per leggere i form vecchi).** Fino a metà agosto, sulle istanze
già provisionate, la base del campo (`width:100%`, padding, bordo, radius) stava **solo**
in `.sw-form-field` e `.sw-form-select` era un puro modificatore: una `<select>` con la
sola `sw-form-select` usciva a **252px, senza padding né radius** (misurato 12/08, B63).
Da lì la regola «entrambe le classi». Dal preset **2.61.18** (hook piattaforma
`update_hooks/2.61.18__css_form_base_campi_in_place.py`, seconda metà del fix B63) la
base è **condivisa** da `.sw-form-field, .sw-form-select, .sw-form-date, .sw-form-file`
→ `sw-form-select` da sola è autosufficiente, come dice oggi la `forms-guide`.

| Classi sulla `<select>` | Oggi (preset ≥ 2.61.18) | Preset vecchio |
|---|---|---|
| `sw-form-select` | ✅ corretto | ❌ 252px, padding 0, radius 0 |
| `sw-form-field sw-form-select` | ✅ corretto (dichiarazioni identiche, innocuo) | ✅ corretto |
| solo `sw-form-field` | ⚠️ `appearance:auto`: **freccia nativa del browser**, incoerente col preset | ⚠️ idem |
| `<sw-select>` | ⚠️ grafica del **checkout**, non del form | ⚠️ idem |

Difesa: il **Cancello 1** (`check_page.py`, dimensione `FORM`) legge il preset
`cms/form.css` del tenant e blocca `sw-form-select` orfana **solo** se la base non è
ancora condivisa (preset vecchio o riscritto a mano); avvisa su `sw-form-field` senza
freccia e su `<sw-select>` dentro un form. Blocca sempre i campi **senza `id`** (il JS
`sw_form_swcss.js` indicizza per `id`: senza, il valore non viene inviato) e avvisa sulla
select `sw-required` la cui prima `<option>` non ha `value=""` (la validazione controlla
`value.length` → non blocca mai l'invio). Non fidarti della rilettura a occhio: esegui
il check.

### Asterisco dei campi obbligatori (dal 2.70, 28/08/2026): lo mette il CSS, non il testo

Il layer base ha `.sw-label-required::after { content: "\00a0*" }` (NBSP: non va a capo da
solo). I web component (`sw-input`, `sw-select`, `sw-phone`) aggiungono la classe alla propria
label **da soli** quando `custom` contiene `sw-required` — verificato su cosicome 2.70.2
(`/mio-account/`): label «Nome» + `::after " *"`. Quindi:
- in `<sw-select label="…">` **niente `*` nel testo** della label: dal 2.70 uscirebbe doppio
  (`Categoria di interesse * *`) — è il caso di leicacampania `/usato-demo/`, oggi a 2.63.8;
- nei form classici, al posto dell'asterisco letterale usa `<label for="…"
  class="sw-label-required">Nome</label>`: stesso segno ovunque e niente `*` orfano a capo.
Il Cancello 1 avvisa in entrambi i casi.

### ⛔ Tre cose che l'esempio di `GET /forms-guide` NON ha (e che vanno messe comunque)

L'esempio della guida è **minimo funzionante**, non conforme: chi lo copia tale e quale
produce ogni volta gli stessi tre difetti (riscontrati su tenant diversi e operatori
diversi). Il markup canonico resta quello della guida per il *contratto JS* — trigger
`.sw-form`, `data-sw-*`, un `id` per campo — ma va completato:

1. **`<label for="<id>">` su ogni campo.** L'esempio scrive `<label>Nome</label>` nuda:
   senza `for` il click sull'etichetta non focalizza il campo e lo screen reader non lo
   annuncia (WCAG 1.3.1/4.1.2). **Eccezione**: la label del consenso privacy **avvolge**
   il checkbox, e lì il `for` non serve.
2. **Link all'informativa nel consenso.** L'esempio ha solo «Accetto il trattamento dei
   dati». Serve il link a `/privacy-policy/` (GDPR art. 13-14: informativa accessibile
   *prima* del conferimento) — `target="_blank" rel="noopener"`, e **sottolineato** se
   contrasta col testo meno di 3:1 (vedi la regola sui link `<a>`).
3. **Il bottone usa la CTA del sito, non `sw-button`.** L'unica classe obbligatoria è
   **`sw-form`** (è il trigger JS): tutto il resto è vestizione. `sw-button` è il default
   generico del preset e su un tenant con design system proprio **stona** — misurato su
   Così Com'è: bottone del form **46px** di altezza e font **16px**, CTA del sito
   (`sw-cta--solid`) **38.4px** e **14px**, stesso colore ma forma diversa, in un sito
   dove le CTA compaiono 14 volte e il form era l'unico `sw-button`. Guarda come sono
   fatti gli altri bottoni **del sito** e usa quelle classi + `sw-form`.

I punti 1-3 sono tutti verificati dal Cancello 1 (❌ i primi due, ⚠️ il terzo).

**Altezze disallineate nei form misti.** I campi del preset hanno `line-height: 1.2` e
`min-height: calc(1.2em + 1.5rem + 2px)` (~45px), ma il widget nativo di
**`input[type=date]`** ha un'altezza intrinseca maggiore e non scende sotto la propria:
in un form con testo + email + select + data i campi risultano di altezze diverse.
L'entità dipende dal motore di rendering — **misurato +2px su Chromium** (47.2 contro
45.2), **~+5px su WebKit/Safari** (~50 contro ~45, dove il widget vale ~1.5em): su
Safari lo scalino è vistoso, su Chromium è un'imprecisione che si nota nei form lunghi.

Ricetta: nel CSS del tenant (layer `cms/<file-stile>.css`) allinea tutti i single-line
**alla quota del campo date**, invece di inseguire il valore più basso:

```css
/* Campi form single-line tutti della stessa altezza (riferimento: widget input date) */
.sw-form-group .sw-form-field,
.sw-form-group .sw-form-select {
    height: calc(1.5em + 1.5rem + 2px);
    min-height: calc(1.5em + 1.5rem + 2px);
    line-height: 1.5;
}
```

Serve **`height` oltre a `min-height`**: il solo `min-height` non impedisce al date di
crescere. Le `textarea` (`.sw-textarea`) non sono toccate e restano ad altezza libera.
È un difetto del preset (report **B63**): finché non è corretto a monte, la regola va
ripetuta su ogni tenant con form.

## Record Form: azioni, destinatari, allegati (dal 28/08/2026, piattaforma 2.67)

Il record `Form` (`POST/PUT /forms`, CLI `forms create/update --stdin`) **non ha più**
`action`, `custom_app_name`, `custom_app_fx` (inviarli → 400 «Additional properties») e
`email` **non è più obbligatoria**. Verificato 28/08 su cosicome 2.67.2 con form ZZTEST:

- **`azioni`** — array eseguito in ordine; default `[{"tipo":"email"}]`; `[]` = la submission
  viene solo registrata. `{"tipo":"email"}` notifica; `{"tipo":"lista","lista_id":N}` iscrive
  il campo **`id="email"`** del form alla lista newsletter N (id inesistente → 400 «Lista
  inesistente»); `{"tipo":"custom_app","app":"<modulo>","fx":"<fn>"}` chiama
  `<app>.api.<fx>(inputs)` (se ritorna `success:false` il visitatore riceve 400).
- **`destinatari`** — `[{etichetta, email}]`: il destinatario lo **sceglie il visitatore**
  («A chi vuoi inviare?»); più indirizzi per voce separati da virgola. È **alternativo a
  `email`**: insieme → **400** «Usa 'email' oppure 'destinatari', mai entrambi» (la guida
  dice 422: è 400), e in PUT valorizzarne uno **azzera l'altro**. Markup: una `<select
  id="destinatario" class="sw-form-select sw-required">` con la **sola `<option value="">`
  segnaposto** — le voci le riempie la piattaforma da `GET /api/get_form_destinatari?form_id=N`
  (solo etichette, gli indirizzi non lasciano il server; option scritte a mano vengono
  sostituite). `sw-required` **non è opzionale**: senza scelta non c'è ripiego, la notifica
  non parte e la submission resta nel log con `esito: error`. Instrada solo l'azione `email`;
  nell'email `{destinatario}` = etichetta scelta.
- **Allegati** — `allegati_attivi: true` (default `false`: gli invii con file → 400) +
  `allegati_max_mb` (default 10, minimo 1). Markup `<input type="file" id="…"
  class="sw-form-file">` (+ `accept`; `multiple` → il campo vale una **lista** di URL).
  Whitelist server: pdf/doc/docx/xls/xlsx + immagini (no svg, archivi, csv, html). Il file va
  in `/uploads/form/<form_id>/` con prefisso casuale; nella submission `inputs.<id>` è l'URL
  assoluto (nel `testo` `{allegato}` diventa il link) e il file è **allegato all'email**.
- **Submissions** (`GET /forms/{id}/submissions`): `esito`/`errore` della notifica; con
  `iubenda_attivo` anche `iubenda_esito` (`""` non richiesta · `pending` · `success` ·
  `error`) e `iubenda_errore` — è il modo per diagnosticare B58 senza il dashboard iubenda.
- Il Cancello 1 (`check_page.py`) **legge il record Form** dal `data-sw-custom-form` della pagina
  e verifica la coerenza: `destinatari` ↔ `select#destinatario` (❌ se manca uno dei due lati o
  manca `sw-required`; con `destinatari` vuoto le option scritte a mano restano ma non instradano —
  verificato 28/08 su cosicome `/contatti/`), campi file ↔ `allegati_attivi` (❌ se false: 400 a
  ogni invio), azione `lista` ↔ campo `id="email"`.
- Sul prodotto, `custom_box_alberi` (`solo_custombox`|`includi_prodotti`, Treenation) per ora
  è **solo in lettura** (schema `Product`, non negli Input).

## `<sw-select>` — dropdown ricercabile del checkout e delle custom app (NON la select standard dei form)

Web component in `swebby.js` (stili core `base/js_components.css` admin,
`base/componenti/sw-select.css` frontend), usato da `pagamento.html` (nazione/provincia)
e dalle custom app. `GET /custom-apps-guide` → `sw_select` lo chiama «modo canonico per
una select» **per quella superficie** (pannello, checkout, app); la `forms-guide` dei form
CMS dice invece `<select class="sw-form-select">`. ⚠️ **Errore già fatto (26/08/2026)**:
questa skill aveva promosso `<sw-select>` a select dei form mentre la nativa era rotta
(B63) → su leicacampania 2 pagine col dropdown del checkout e 3 varianti diverse di select
nativa nelle altre. Nei form CMS usalo **solo** per liste lunghe che richiedono ricerca
(nazioni, province) e solo se quel look è voluto; il Cancello 1 lo segnala.

```html
<sw-select id="servizio" label="Di cosa hai bisogno? *" placeholder="Scegli..."
           error-message="Campo obbligatorio" custom="sw-form-field sw-required"
           data='[{"value":"x","label":"X"}]'></sw-select>
```

Attributi: `id` (obbl.), `data` (JSON array value/label), `label`, `placeholder`,
`error-message`, `custom` (classi sull'input interno, default `sw-input`),
`custom-label`/`custom-dropdown`/`custom-dropdown-item`, `selected`, `show-icon`,
`server-search`.

- ⚠️ **Chiave form = `<id>-input`** (input readonly generato): nel `testo` del
  record Form usare `{servizio-input}`, non `{servizio}`. Il valore inviato è la
  label scelta.
- Le classi di `custom` vanno sull'input interno → `sw-required` valida gratis.
- **Box/hover/ombra del dropdown li dà il CORE** (selettori strutturali, a prova
  di tree-shake): NON scrivere fallback. Unica accortezza: se `custom` usa una
  classe con padding-left < del pl-10 del componente (es. `sw-form-field`),
  l'icona copre il testo → ripristinare `sw-select input[readonly]{padding-left:2.5rem}`.
- `data` in attributo single-quoted: niente apostrofi nelle label.


## Custom app Django via API (superuser — collaudato 07/07/2026)

`/custom-apps` deploya VERE Django app sull'istanza: modelli DB (migrate al
montaggio), pagine nel pannello, rotte pubbliche. POST scaffolda+valida+monta
(422 con traceback in `error.details[0].message` e revert atomico se fallisce);
PUT applica file/delete e rimonta (risposta con `reloaded: true`); GET
/custom-apps/{name} legge i file; GET .../errors il traceback di boot. Guida:
`GET /custom-apps-guide`.

Regole imparate sul campo (ordine di sanguinamento):

1. **Rotte SEMPRE con slash finale** (`path("x/")`): il proxy normalizza con
   301 e `path("x")` non matcha mai.
2. **`@login_required` su ogni view admin** anche se esiste il gate centrale
   (302→login sulle rotte matchate; le non matchate fanno 404).
3. **Template pannello**: `{% extends 'admin/partials/base.html' %}` +
   `{% block content %}`. CSS: file `styles.css` nella root app → compilato in
   coda a `static/css/admin.css` (INTERO, no tree-shake); prefisso `sw-app-<name>-*`.
4. **Template frontend**: `{% extends 'frontend/partials/base.html' %}` (NON
   `frontend/base.html`) + `{% block content %}`. Il base ESIGE il contesto
   delle view piattaforma: `header_name`, `header_sticky_name`, `footer_name`,
   `breadcrumbs_name` (dal modello Header_Footer, risolvibile con
   `django.apps.get_models()`), `lingue_data`, `lang`, `title`; opzionali
   `description` (meta) — senza `index` il robots esce `noindex,nofollow`.
5. **CSS frontend delle app**: il bundle servito sulle rotte app è `cms.css`
   (globale+header_footer+cms+custom): le classi `sw-sv-*`/`sw-container` ci sono
   già. Classi nuove → file in `custom/` MA i template delle custom app NON
   sono scansionati dal tree-shaker: dichiararle nello span nascosto di un
   partial header (con `style="display:none !important"` inline — una classe
   dichiarata che imposta `display` batterebbe l'attributo `hidden`).
6. **Seed dei dati = data migration**: la pipeline esegue `migrate` alla
   validazione, quindi la PUT che deposita `migrations/000X_seed.py`
   (RunPython + get_or_create idempotente) È l'insert. Niente endpoint da
   esporre, tutto versionato nell'app.
7. **Debug empirico dall'esterno** (i runtime error finiscono in GlitchTip,
   non nell'API): template standalone per isolare il base; nome del base in
   query param per provare candidati senza ri-PUT; try/except temporaneo nella
   view che ritorna `traceback.format_exc()`; view-inspector con `os.walk` sui
   `settings.TEMPLATES[0]['DIRS']` per mappare i template esistenti.
8. Un errore runtime in una view = 500 solo su quella richiesta; un errore di
   import/boot auto-disabilita SOLO l'app (safe-loader): il sito resta su.
9. Una rotta frontend `/<name>/` OSCURA l'eventuale pagina CMS con lo stesso
   slug (la rotta app vince): rimuovere la pagina per evitare fantasmi in
   sitemap.
10. **Multilingua** (guida: `GET /custom-apps-guide` → `multilingua`): il
    registry NON ha campo lingua e le rotte app sono montate SENZA segmento
    lingua (`/<name>/`, mai `/en/<name>/`) → **una custom app non partecipa al
    routing linguistico**. Pattern piattaforma = **una riga per lingua** (campo
    `lang` sul modello, come `Page`/`Prodotto`; consigliato
    `unique_together=('slug','lang')`) + **una pagina CMS per lingua**. NON
    esistono campi tradotti (`nome_it`/`nome_en`) né record padre con
    sotto-traduzioni: IT ed EN sono due record distinti. Passi:
    - **Modello**: `lang = CharField(max_length=2, default='it')` (i codici sono
      gli slug delle `Lingua` configurate: `it`, `en`, `de`…).
    - **Admin**: la UI del pannello resta in italiano (NON si traduce); serve
      solo un `<select>` Lingua nel form (lingue da
      `POST /sw-back/cms/get_lingue_configurate`). ⚠️ senza quel select tutti i
      record nascono nella lingua default e le pagine nelle altre lingue escono
      VUOTE.
    - **Frontend via context fx** (approccio raccomandato, NON le rotte proprie
      dell'app): `<app>/context.py` con una fx che riceve SOLO `request`,
      deduce la lingua dal **primo segmento del path** (la predefinita è senza
      prefisso, le altre hanno `/<slug>/`) e filtra per `lang`. NON usare
      `request.resolver_match` (il catch-all CMS chiama `page_view` diretto,
      senza kwarg `lang`). Esempio: `seg=request.path.strip('/').split('/'); lang=seg[0] if seg and seg[0] in cfg['lingue_slug'] else cfg['lingua_predefinita_slug']`
      con `cfg=site_config()` (da `app.context_processors`).
    - **Pagine**: una `POST /pages` per lingua, STESSO context
      (`contexts:[{nome,app,fx}]`), con `lang` giusto e slug tradotto. Content
      file: `<slug>.html` per la predefinita, `<slug>_<lang>.html` per le altre.
    - **Alternates/hreflang** (SOLO se servono switcher/hreflang, altrimenti
      FERMARSI al campo `lang`): tabella ponte `<Entity>AlternateLang` (3 campi
      SENZA FK: `<entity>_id`, `alternate_lang`, `alternate_<entity>_id` +
      `unique_together`) e riuso di `api_v2.alternates`
      (`read_alternates`/`sync_alternate_mesh`) — NON ricopiare la mesh. Per
      collegare le PAGINE CMS: `PUT /pages/{id}` con `alternates`.
    - ⚠️ Se l'app serve il frontend con **rotte proprie** (`frontend_urls`), quelle
      sono solo IT (`/<name>/`): per il multilingua vero va migrata a
      **pagina CMS + context fx** (vedi punto 9: rotta app oscura la pagina CMS
      omonima → togliere la rotta frontend prima di creare la pagina).

## Verifiche d'abitudine

- Dopo ogni scrittura: **rileggi** (`get --no-cache`) — vedi quirk dei campi ignorati.
- `doctor` a inizio sessione e dopo cambi di config/tenant.
- Dopo modifiche design: compile + verifica della pagina pubblica (200 + contenuto).
- Per i test su dati reali: entità con prefisso riconoscibile (es. `ZZTEST`) e
  **cleanup completo** a fine giro; non toccare i dati del cliente senza richiesta.

## Cosa NON si può fare via API (verificare a ogni evoluzione)

- Configurare SMTP Marketing, permessi delle chiavi → pannello. (Gli attributi
  NON sono più sola lettura dal 20/08/2026: CRUD completo su `/attributes` e
  `/attributes/{id}/values`; dal pannello restano badge, alternates e immagini
  dei valori tipo `immagine`.)
- Tracking aperture/click delle campagne; webhook outbound (es. `cart.abandoned`).
- Annullamento/eliminazione ordini; creazione metodi di pagamento/spedizione.
- Modificare il layer CSS `base/` del design system.
