---
name: pp-swerpicommerce
description: "Printing Press CLI for Swerpicommerce. REST API v2 schema-first per la gestione di ordini, clienti, prodotti, pagine CMS e configurazioni e-commerce. Tutti..."
author: "Vincenzo Vigorito"
license: "Apache-2.0"
argument-hint: "<command> [args] | install cli|mcp"
allowed-tools: "Read Bash"
metadata:
  openclaw:
    requires:
      bins:
        - swerpicommerce-pp-cli
---

# Swerpicommerce — Printing Press CLI

## Prerequisites: Install the CLI

This skill drives the `swerpicommerce-pp-cli` binary. **You must verify the CLI is installed before invoking any command from this skill.** If it is missing, install it first:

1. Install via the Printing Press installer:
   ```bash
   npx -y @mvanhorn/printing-press install swerpicommerce --cli-only
   ```
2. Verify: `swerpicommerce-pp-cli --version`
3. Ensure `$GOPATH/bin` (or `$HOME/go/bin`) is on `$PATH`.

If the `npx` install fails before this CLI has a public-library category, install Node or use the category-specific Go fallback after publish.

If `--version` reports "command not found" after install, the install step did not put the binary on `$PATH`. Do not proceed with skill commands until verification succeeds.

REST API v2 schema-first per la gestione di ordini, clienti, prodotti, pagine CMS
e configurazioni e-commerce.

Tutti gli endpoint (eccetto `/auth/token`) richiedono un Bearer Token ottenuto
tramite `POST /auth/token`. **Scelta consapevole**: il token non scade
(`expires_at: null`) ed e condiviso con la v1; in compenso e revocabile in
ogni momento via `DELETE /auth/tokens/{id}` (o eliminando la chiave API dal
pannello) e `GET /auth/tokens` elenca i token emessi per la propria chiave.
Per verificare un token senza effetti collaterali usare `GET /auth/me`.

Questo schema (`/openapi.json`) e **pubblico per scelta**: descrive la
superficie comune del prodotto e non contiene segreti ne dati del tenant.

### Guide operative — LEGGILE PRIMA di operare sull'area

Lo schema descrive le *operation*, non il *funzionamento* del tema. Prima di
scrivere/diagnosticare in una delle aree qui sotto, fai la GET della guida
relativa (markdown): spiega il meccanismo, la precedenza, gli id che il JS
cerca e gli errori tipici. **Saltarle porta a diagnosi sbagliate** (es.
concludere che un problema di config sia un bug di template non risolvibile).

- **Template del tema** (header, header sticky, footer, breadcrumbs, pagine
  di sistema): `GET /design/templates-guide`. Include il meccanismo degli
  slot `header_name`/`header_sticky_name`/`footer_name`/`breadcrumbs_name`
  (precedenza pagina→globale, include condizionale, id `menu_sticky`/
  `header_basic` richiesti dal JS), cosa è upstream read-only e cosa è
  editabile per-istanza.
- **Comporre pagine / CSS / SWCSS**: `GET /design/swcss-guide` (dettaglio
  nella sezione qui sotto).
- **Form**: `GET /forms-guide`.
- **Custom app**: `GET /custom-apps-guide`.

### Loghi e favicon — non hardcodarli nei template

Loghi e favicon hanno slot dedicati: **non** incollare `<img>`/`<link>` con
path fissi (né data-URI) dentro header/footer. Due passi:

1. `POST /media` con `folder: logos` -> carica il file (ammette anche
   svg/ico); nella risposta `nome` è il nome effettivo salvato.
2. `PUT /design/logos` -> assegna quel `nome` allo slot (`logo_black`,
   `logo_white`, `logo_mobile_black`, `logo_mobile_white`, `logo_email`,
   `favicon`).

`GET /design/logos` mostra gli slot correnti e, per ognuno, `esiste`: se è
`false` lo slot punta a un default mai caricato su questa installazione ed
il sito serve un 404 — è la causa tipica di "logo/favicon mancanti". I file
stanno su `/static/img/uploads/` e i template li leggono dal context
(`{{ logo_black }}`, `{{ logo_white }}`); nessun `POST /design/compile`.

### Comporre pagine via API (SWCSS) — guida rapida per agenti

Il tema usa SWCSS, design system CSS con **tree-shaking per pagina**:
i bundle includono solo le classi realmente usate nei template.
Tutti i path qui sotto sono relativi al server dell'API (`/api/v2`,
come ogni altra operation dello schema). Flusso:

1. `POST /pages` -> crea la pagina (slug, SEO)
2. `PUT /pages/{id}/content` -> HTML del solo block content, classi `sw-*`
3. `PUT /design/css/cms/<slug>.css` -> regole CSS della pagina (se servono)
4. `PUT /design/js/<slug>.js` -> JS della pagina (se serve; autoload
   per slug, live subito senza compilazione)
5. `POST /design/compile` -> SOLO ora le modifiche CSS vanno live
6. `GET /<slug>/` -> verifica pubblica
7. `POST /fork/commit` -> **committa e versiona le modifiche** (con
   `description` di cosa è stato fatto). Passo necessario per persistere:
   senza commit, il prossimo update (`git reset --hard`) sovrascrive i file
   modificati. *(Se l'auto-commit è attivo — `GET /config/autocommit`,
   default ON — i passi 1-4 sono già committati a ogni scrittura e questo
   passo serve solo a marcare la release; con auto-commit OFF è obbligatorio.)*

**Regola ferma: niente CSS né JS inline nel contenuto pagina** — no
blocchi `<style>`/`<script>`, no `style="..."` per il layout: stili e
script hanno i loro file (`/design/css`, `/design/js`). La compilazione
serve SOLO per il CSS; il JS va live al PUT.

**L'ordine conta** (prima il contenuto, poi il CSS, poi la compilazione:
una classe mai usata nei template viene tree-shakerata). Regole d'oro:
se esiste un componente `sw-*` usalo; utility (`flex`, `p-4`, `grid-2`)
solo per micro-aggiustamenti; mai ridefinire il layer base; classi nuove
prefissate `sw-<contesto>-`; un file CSS per pagina/componente; variabili
`var(--sw-...)` e breakpoint `@custom-media` (`--mb` `--sm` `--md` `--lg`
`--xl`). Scoperta: leggi i sorgenti reali con `GET /design/css` prima di
scrivere. Le immagini passano dalla libreria `/media` (usa `url` e `alt`).

**Colori e variabili**: la palette `--sw-*` si gestisce via `/design/colors`
(CRUD; i colori `sistema` cambiano solo di valore); i token immutabili del
framework (`--text-*`, `--lh-*`, `--radius-*`, `--font-*`, breakpoint) e i
colori correnti si leggono da `GET /design/variables` (sola lettura). Il
layer **`globale`** (`section=globale` di `/design/css`) contiene i default
d'elemento validi su tutto il sito: incluso PRIMA delle sezioni, che lo
sovrascrivono — metti lì ciò che è comune, nelle sezioni solo gli override.

**Guida completa** (architettura, esempi, errori tipici):
`GET /design/swcss-guide` (markdown).

### Componenti riutilizzabili pronti all'uso

Componenti pubblici che puoi incollare **in qualsiasi pagina** (contenuto
CMS, descrizione prodotto, articolo blog). Sono opt-in: CSS e JS si caricano
**solo dove usi il markup**, niente da scrivere a parte l'HTML.

**Galleria immagini con lightbox (`sw-gallery`)** — griglia di miniature che
aprono una lightbox (zoom, frecce, swipe). L'unico requisito funzionale è la
classe `.glightbox` sul link (`href` = immagine grande); `sw-gallery*` è solo
il layout (2 colonne mobile, 4 da `--lg`). Le immagini passano da `/media`;
valorizza gli `alt`. Per più gallerie separate nella stessa pagina aggiungi
`data-gallery="nome"` sui link dello stesso gruppo. Markup:

```html
<div class="sw-gallery">
  <div class="sw-gallery-grid">
    <a class="sw-gallery-thumb glightbox" href="/uploads/blog/foto1.jpg">
      <img src="/uploads/blog/foto1.jpg" alt="Descrizione foto 1">
    </a>
    <a class="sw-gallery-thumb glightbox" href="/uploads/blog/foto2.jpg">
      <img src="/uploads/blog/foto2.jpg" alt="Descrizione foto 2">
    </a>
  </div>
</div>
```

Su una pagina nuova serve `POST /design/compile` solo perché il tree-shake
includa `sw-gallery-*` nel bundle; la lightbox (lib GLightbox: JS + CSS) si
inietta e si attiva da sola dove trova `.glightbox`. Nessun file JS da creare,
nessun `<script>`/`<style>` inline.

### Multilingua

Il contenuto multilingua è modellato **per record**: ogni traduzione di un
prodotto, pagina, articolo o categoria è una **riga separata** con un campo
`lang`. Non esiste un record "padre" con sotto-traduzioni: la versione IT e
la versione EN dello stesso prodotto sono due record distinti, ciascuno col
proprio id, slug e contenuti.

- **Codici lingua** (`lang`): sono gli slug delle lingue configurate nel
  pannello (es. `it`, `en`, `de`). Default = **lingua predefinita del sito**
  (tipicamente `it`). Non c'è un endpoint per elencarli via API: vanno
  conosciuti dalla configurazione del tenant.
- **Slug univoco per lingua** (pagine, articoli, categorie articoli): lo
  stesso slug in lingue diverse identifica record diversi; uno slug
  esplicito già usato **nella stessa lingua** → `400 SLUG_IN_USE`. Se lo
  slug è omesso viene generato dal titolo, garantito univoco per quella
  lingua. *Eccezione:* le **categorie prodotto** (`/categories`) hanno slug
  **globale** (non per lingua).
- **Lettura per lingua**: il query param `?lang=<codice>` su `/products`,
  `/pages`, `/articles`, `/categories`, `/article-categories`, `/attributes`
  **filtra in modo esatto** (`WHERE lang = <codice>`), **senza fallback**
  alla lingua predefinita. Omesso → ritorna i record di **tutte** le lingue.
- **Collegare le traduzioni tra loro**: pagine, prodotti, categorie prodotto,
  articoli e categorie articoli espongono il campo `alternates`, impostabile
  **solo in update** (`PUT`, non in `POST`) e restituito in lettura quando
  `include_alternates=true` (default). È un array di `{alternate_lang,
  alternate_<risorsa>_id}` (es. `alternate_page_id`, `alternate_product_id`,
  `alternate_category_id`, `alternate_articolo_id`, `alternate_categoria_id`).
  La scrittura **sostituisce integralmente** il set e costruisce, come dal
  pannello, una **mesh bidirezionale completa** tra le traduzioni: collegando
  IT→EN viene creato anche EN→IT, e se IT ha EN e FR vengono collegati anche
  EN↔FR. Ometterlo lascia i collegamenti invariati, `[]` li rimuove.
  Per le pagine il file contenuto resta per-lingua:
  `templates/frontend/<slug>.html` per la lingua predefinita,
  `templates/frontend/<slug>_<lang>.html` per le altre.
- **Campagne email**: il campo `lang` della campagna **filtra i destinatari**
  ai soli clienti con quella lingua (`null` = tutte le lingue).
- **Custom app**: il registry delle custom app **non ha un campo lingua** e le
  rotte dell'app sono montate **senza segmento lingua** (`/<name>/`, mai
  `/en/<name>/`): una custom app non partecipa al routing linguistico. Si fa
  multilingua con lo stesso pattern di cui sopra — campo `lang` sul suo
  modello + **una pagina CMS per lingua** (`POST /pages` con `lang`) che punta
  allo **stesso** context. La funzione in `<app>/context.py` riceve la
  `request`, deduce la lingua dal **primo segmento del path** (la predefinita è
  senza prefisso, le altre hanno `/<slug>/`) e filtra per `lang`. Pattern
  completo e codice in `GET /custom-apps-guide` → `multilingua`.

Convenzioni v2:
  - Response di successo sempre nella forma `{"data": ...}` (le liste aggiungono `meta`).
  - Errori nella forma `{"error": {"code", "message", "details"}}`.
  - Creazioni multiple via endpoint dedicato `/<risorsa>/batch` (body `{"items": [...]}`).
  - I nomi dei campi di dominio sono quelli del modello (italiano), come in v1.

## Command Reference

**article-categories** — Manage article categories

- `swerpicommerce-pp-cli article-categories article-category-create` — Se `slug` manca viene generato dal nome (univoco per lingua).
- `swerpicommerce-pp-cli article-categories article-category-delete` — Gli articoli che la usano come principale restano (perdono il riferimento).
- `swerpicommerce-pp-cli article-categories article-category-get` — Dettaglio categoria articoli
- `swerpicommerce-pp-cli article-categories article-category-update` — Aggiorna una categoria articoli
- `swerpicommerce-pp-cli article-categories list` — Lista categorie articoli

**articles** — Manage articles

- `swerpicommerce-pp-cli articles create` — Se `slug` manca viene generato dal titolo (univoco per lingua).
- `swerpicommerce-pp-cli articles delete` — Elimina un articolo
- `swerpicommerce-pp-cli articles get` — Dettaglio articolo
- `swerpicommerce-pp-cli articles list` — Lista articoli blog
- `swerpicommerce-pp-cli articles update` — Aggiorna un articolo

**attributes** — Manage attributes

- `swerpicommerce-pp-cli attributes get` — Dettaglio attributo con i suoi valori
- `swerpicommerce-pp-cli attributes list` — Definizioni di attributi e valori gestite dal pannello (es. Taglia: S/M/L). Le variazioni prodotto via API usano...

**cache** — Manage cache

- `swerpicommerce-pp-cli cache config-update` — Aggiorna ConfigCache; i campi omessi restano invariati. Per disattivare la cache pubblica delle pagine:...
- `swerpicommerce-pp-cli cache flush` — `targets` (default `['pages','products']`): `pages` = reset del template loader + reload degli URL (pagine...
- `swerpicommerce-pp-cli cache get` — `config` = impostazioni ConfigCache che governano gli header Cache-Control delle pagine (browser/CDN): con...

**campaigns** — Manage campaigns

- `swerpicommerce-pp-cli campaigns create` — `titolo` (oggetto email) e `testo` (HTML) possono arrivare da `template_id`: il contenuto viene copiato alla...
- `swerpicommerce-pp-cli campaigns delete` — Coda email e associazioni liste eliminate in cascata; rifiutato mentre è in invio.
- `swerpicommerce-pp-cli campaigns get` — Dettaglio campagna
- `swerpicommerce-pp-cli campaigns list` — Campagne email
- `swerpicommerce-pp-cli campaigns update` — Rifiutato (400 CAMPAIGN_SENDING) mentre la campagna è in fase di invio.

**carts** — Carrelli dello storefront (inclusi gli abbandonati, sola lettura)

- `swerpicommerce-pp-cli carts get` — Dettaglio carrello
- `swerpicommerce-pp-cli carts list` — Carrelli dello storefront, i più recenti per primi. `abbandonato` è marcato dal job di schedulazione secondo la...

**categories** — Categorie prodotto

- `swerpicommerce-pp-cli categories category-create` — Se `slug` manca viene generato dal nome (con suffisso se non univoco).
- `swerpicommerce-pp-cli categories category-delete` — Come dal pannello: i prodotti che la referenziano mantengono l'id nel campo `categorie`; le sottocategorie restano...
- `swerpicommerce-pp-cli categories category-get` — Dettaglio categoria
- `swerpicommerce-pp-cli categories category-update` — Campi non riconosciuti -> 400 VALIDATION_ERROR.
- `swerpicommerce-pp-cli categories list` — Lista categorie prodotto

**config** — Config per-istanza. `auto-commit` governa se le scritture API (pagine/CSS/JS/template) vengono committate+pushate automaticamente; con OFF si persiste/versiona via `POST /fork/commit`.

- `swerpicommerce-pp-cli config autocommit-get` — Stato dell'auto-commit delle scritture API
- `swerpicommerce-pp-cli config autocommit-update` — `autocommit=true` (default di fabbrica): ogni scrittura (pagine/CSS/JS/template) viene committata+pushata su origin,...

**custom-apps** — Creazione e correzione di custom app Django montate nell'istanza (SOLO superuser/creatori). Queste operation sono visibili nello spec unicamente quando lo richiede una creator-key superuser. Vedi `GET /custom-apps-guide`.

- `swerpicommerce-pp-cli custom-apps create` — Scaffolda la app, la registra (INSTALLED_APPS + rotte + menu), la valida con `check`+`makemigrations`+`migrate` in...
- `swerpicommerce-pp-cli custom-apps delete` — Rimuove una custom app (superuser)
- `swerpicommerce-pp-cli custom-apps get` — Ritorna metadati + elenco file; con `include_content=true` (default) anche il contenuto di ogni file.
- `swerpicommerce-pp-cli custom-apps list` — Ritorna nome, label, stato (`active` / `disabled` se un errore di boot l'ha auto-disabilitata) e sintesi errore....
- `swerpicommerce-pp-cli custom-apps update` — Applica i `files` forniti (create/overwrite) e gli eventuali `delete`, poi rivalida e rimonta. **Atomico**: se la...

**custom-apps-guide** — Manage custom apps guide

- `swerpicommerce-pp-cli custom-apps-guide` — Guida al workflow create/correzione custom app (superuser)

**customers** — Clienti e punti fedeltà

- `swerpicommerce-pp-cli customers batch` — Crea piu clienti
- `swerpicommerce-pp-cli customers create` — Crea un cliente
- `swerpicommerce-pp-cli customers delete` — Elimina cliente, account di login e indirizzi di spedizione. Se il cliente ha ordini risponde 409: ripetere con...
- `swerpicommerce-pp-cli customers get` — Cliente con email dell'account e indirizzi di spedizione.
- `swerpicommerce-pp-cli customers list` — Lista clienti
- `swerpicommerce-pp-cli customers update` — Aggiorna i campi indicati. `email` e `password` agiscono sull'account di login collegato (l'email deve restare...

**design** — Sorgenti SWCSS del tema, loghi/favicon e compilazione bundle. Per comporre pagine via API: vedi la guida rapida nella descrizione dello schema (in alto) e la guida completa su `GET /design/swcss-guide`. Dopo ogni modifica a contenuti o CSS serve `POST /design/compile` perché vada live (i loghi fanno eccezione: non passano dal CSS).

- `swerpicommerce-pp-cli design color-create` — `valore` in hex (`#RGB` o `#RRGGBB`, normalizzato a `#rrggbb`). La `classe_css` e' generata dal `nome` (slug...
- `swerpicommerce-pp-cli design color-delete` — Rimuove il record. I colori di sistema non sono eliminabili (403). Dopo la modifica eseguire `POST /design/compile`.
- `swerpicommerce-pp-cli design color-get` — Dettaglio di un colore
- `swerpicommerce-pp-cli design color-update` — Modifica `nome`/`valore`/`descrizione`/`attivo`. Cambiare `nome` rigenera `classe_css`: sui colori di sistema e'...
- `swerpicommerce-pp-cli design colors-list` — Tutti i record `CustomColor`. Ognuno espone `classe_css` (es. `sw-primario`): usabile nei template come classe...
- `swerpicommerce-pp-cli design compile` — Rigenera i bundle statici (stessa compilazione del pannello Grafica) con tree-shaking sulle classi usate nei...
- `swerpicommerce-pp-cli design css-delete` — Rifiutato (400 DEFAULT_CSS_FILE) sui file del set predefinito della sezione: il ripristino default li ricreerebbe...
- `swerpicommerce-pp-cli design css-get` — Legge un sorgente CSS
- `swerpicommerce-pp-cli design css-list` — File CSS delle sezioni `pagine-sistema/*` (stesse del pannello Grafica), del layer `globale` (fallback: default...
- `swerpicommerce-pp-cli design css-put` — Sovrascrive l'intero file (201 se creato). Le modifiche NON vanno live finché non si esegue `POST /design/compile`....
- `swerpicommerce-pp-cli design guide` — Markdown operativo: architettura dei layer, regole del design system, flusso pagina+CSS+compilazione, utility...
- `swerpicommerce-pp-cli design js-delete` — Elimina un file JS per-pagina
- `swerpicommerce-pp-cli design js-get` — Legge un file JS per-pagina
- `swerpicommerce-pp-cli design js-list` — JS per-istanza in `/static/js/custom/`: il file `<slug>.js` (o `<slug>_<lang>.js` per le lingue non predefinite)...
- `swerpicommerce-pp-cli design js-put` — Sovrascrive l'intero file (201 se creato) e va live subito — niente compilazione, il cache-buster è sull'mtime....
- `swerpicommerce-pp-cli design logos-get` — Gli slot del tema (`logo_black`, `logo_white`, `logo_mobile_black`, `logo_mobile_white`, `logo_email`, `favicon`)...
- `swerpicommerce-pp-cli design logos-update` — Stessa operazione del pannello Grafica -> Loghi. Il file va caricato prima in libreria con `POST /media` (`folder:...
- `swerpicommerce-pp-cli design template-delete` — 403 `UPSTREAM_TEMPLATE` se il file è upstream o `base.html` (sola lettura).
- `swerpicommerce-pp-cli design template-get` — Legge il sorgente di un template, anche upstream (sola lettura, come riferimento per crearne uno tuo). `base.html`...
- `swerpicommerce-pp-cli design template-put` — Sovrascrive l'intero file (201 se creato). **403 `UPSTREAM_TEMPLATE`** se il target è upstream o `base.html` (sola...
- `swerpicommerce-pp-cli design templates-guide` — Markdown operativo: cosa sono partial e pagine di sistema, come si creano e si collegano (header_name /...
- `swerpicommerce-pp-cli design templates-list` — Elenca i template `.html` delle aree `partials` (`templates/frontend/partials/`) e `pagine_sistema`...
- `swerpicommerce-pp-cli design variables-get` — Riferimento in sola lettura per comporre CSS con `var(--...)`. Due gruppi: - `sistema`...

**discount-codes** — Codici sconto

- `swerpicommerce-pp-cli discount-codes create` — `codice` duplicato -> 400 CODE_IN_USE (il checkout cerca per codice).
- `swerpicommerce-pp-cli discount-codes delete` — Gli ordini che lo hanno usato conservano lo storico in `OrdineCodiciSconto`.
- `swerpicommerce-pp-cli discount-codes get` — Dettaglio codice sconto
- `swerpicommerce-pp-cli discount-codes list` — Lista codici sconto
- `swerpicommerce-pp-cli discount-codes update` — Campi non riconosciuti -> 400 VALIDATION_ERROR.

**email-lists** — Manage email lists

- `swerpicommerce-pp-cli email-lists create` — Crea una lista email
- `swerpicommerce-pp-cli email-lists delete` — Le iscrizioni vengono eliminate in cascata; i clienti che la avevano come lista principale ripiegano sulla lista di...
- `swerpicommerce-pp-cli email-lists get` — Dettaglio lista email
- `swerpicommerce-pp-cli email-lists list` — Liste email
- `swerpicommerce-pp-cli email-lists update` — Aggiorna una lista email

**email-templates** — Manage email templates

- `swerpicommerce-pp-cli email-templates create` — Nei contenuti si possono usare placeholder `{chiave}`: vengono risolti all'invio transazionale (POST /emails/send)...
- `swerpicommerce-pp-cli email-templates delete` — Le campagne create dal template non vengono toccate (il contenuto è copiato alla creazione).
- `swerpicommerce-pp-cli email-templates get` — Dettaglio template email
- `swerpicommerce-pp-cli email-templates list` — Template email
- `swerpicommerce-pp-cli email-templates update` — Aggiorna un template email

**emails** — Manage emails

- `swerpicommerce-pp-cli emails` — Invio sincrono via SMTP Marketing a `cliente_id` (email dell'account) oppure `email` diretta. Contenuto diretto...

**fonts** — Font personalizzati (woff2) e assegnazione ai campi tipografici (dove applicarli)

- `swerpicommerce-pp-cli fonts assignments-get` — Restituisce `font_fields` (chiave `font_<campo>_id` -> id del font). E' il 'dove': il prefisso del campo indica la...
- `swerpicommerce-pp-cli fonts assignments-update` — Fa merge della mappa `assignments` in `font_fields`: valore = id font (deve esistere) per assegnare, `null` per...
- `swerpicommerce-pp-cli fonts create` — Contenuto base64 nel body JSON (solo `.woff2`, max 5 MB decodificati). Servito da `/static/fonts/{nome}.woff2`. Per...
- `swerpicommerce-pp-cli fonts delete` — Rimuove record + associazioni e, se nessun altro record usa lo stesso file, il woff2 da /static/fonts/. I campi...
- `swerpicommerce-pp-cli fonts get` — Dettaglio di un font
- `swerpicommerce-pp-cli fonts list` — Tutti i record `Fonts`. `src` e' l'URL pubblico del woff2 servito dal dominio del sito (`/static/fonts/...`), quindi...
- `swerpicommerce-pp-cli fonts update` — Modifica famiglia/weight/style/display/attivo. Il file woff2 non si sostituisce (per cambiarlo: elimina e ricarica)....

**fork** — Versione dell'ambiente fork e commit del working tree. `version.json` resta riservato all'upstream; `fork_version.json` (intero, baseline 100) traccia le release del fork — patch +1, major +10, minor +100.

- `swerpicommerce-pp-cli fork commit` — Stagea l'INTERO working tree (`git add -A`), bumpa `fork_version.json` e crea un commit con la `description`...
- `swerpicommerce-pp-cli fork version-get` — Legge `fork_version.json`: `version` (intero), `release_date` dell'ultimo commit fork e `description` di cosa...

**forms** — Articoli del blog e loro categorie

- `swerpicommerce-pp-cli forms create` — Crea un form
- `swerpicommerce-pp-cli forms delete` — Elimina un form (e le sue submission)
- `swerpicommerce-pp-cli forms get` — Dettaglio di un form
- `swerpicommerce-pp-cli forms list` — Elenca i record Form (destinatario, azione, corpo email). Usa l'`id` come `data-sw-custom-form` nel markup del form...
- `swerpicommerce-pp-cli forms update` — Modifica un form (campi omessi invariati)

**forms-guide** — Manage forms guide

- `swerpicommerce-pp-cli forms-guide` — Markdown operativo: record Form + markup SWCSS + contratto di sw_form.js. Da leggere PRIMA di comporre una pagina...

**header-footer** — Manage header footer

- `swerpicommerce-pp-cli header-footer list` — `Header_Footer` mappa, **per lingua**, i partial di default `header_name` / `header_sticky_name` / `footer_name` /...
- `swerpicommerce-pp-cli header-footer set` — Upsert del record `Header_Footer` di `{lang}` (stessa cosa del pannello `/sw-back/setting/grafica`, ora via API)....

**media** — Libreria media globale (immagini di prodotti, categorie, blog e loghi). La cartella `logos` contiene i file di loghi e favicon, serviti da `/static/img/uploads/`: caricato il file qui, si assegna a uno slot con `PUT /design/logos`.

- `swerpicommerce-pp-cli media delete` — Rimuove il file dallo storage e azzera i riferimenti diretti nel database (record FotoProdotto per product_images;...
- `swerpicommerce-pp-cli media get` — Dettaglio di un file della libreria
- `swerpicommerce-pp-cli media list` — File immagine delle cartelle gestite (foto prodotto, immagini categorie prodotto, articoli blog, categorie blog,...
- `swerpicommerce-pp-cli media update` — `alt` viene salvato in libreria e propagato agli usi correnti del file (foto prodotto, `immagine_alt` delle...
- `swerpicommerce-pp-cli media upload` — Contenuto base64 nel body JSON (max 10 MB decodificati; estensioni jpg/jpeg/png/webp/gif/avif, più svg/ico nella...

**orders** — Ordini

- `swerpicommerce-pp-cli orders batch` — Crea piu ordini
- `swerpicommerce-pp-cli orders create` — Crea un ordine
- `swerpicommerce-pp-cli orders get` — Dettaglio ordine
- `swerpicommerce-pp-cli orders list` — Lista ordini
- `swerpicommerce-pp-cli orders update` — Aggiorna i campi indicati dell'ordine. L'annullamento e un update di stato: `{'stato': 'annullato'}`. Gli ordini non...

**page-templates** — Manage page templates

- `swerpicommerce-pp-cli page-templates assign` — Scrive `PagineSistema.nome_file` (stessa cosa del pannello /sw-back/setting/grafica). I file di sistema di default...
- `swerpicommerce-pp-cli page-templates list` — `presets` = template di partenza per le pagine nuove; `pagine_sistema` = elenco `{tipo, nome_file}` delle pagine di...

**pages** — Pagine CMS

- `swerpicommerce-pp-cli pages create` — Come dal pannello: crea il record e il file contenuto `templates/frontend/<slug>[_<lang>].html` (dal preset blank, o...
- `swerpicommerce-pp-cli pages delete` — Rimuove record e file contenuto, come dal pannello. Pagine di sistema -> 400 SYSTEM_PAGE; homepage -> 400...
- `swerpicommerce-pp-cli pages get` — Dettaglio pagina CMS
- `swerpicommerce-pp-cli pages list` — Le pagine sono template-driven: il contenuto HTML non e un campo del modello ma un template Django per-istanza,...
- `swerpicommerce-pp-cli pages update` — Campi non riconosciuti -> 400 VALIDATION_ERROR.

**payment-methods** — Manage payment methods

- `swerpicommerce-pp-cli payment-methods` — Lista metodi di pagamento attivi

**products** — Prodotti e giacenze

- `swerpicommerce-pp-cli products batch` — Crea piu prodotti
- `swerpicommerce-pp-cli products create` — **Guard anti-duplicato:** se il body ha un `sku` non vuoto e esiste già un prodotto con lo stesso `sku` nella...
- `swerpicommerce-pp-cli products delete` — Elimina un prodotto
- `swerpicommerce-pp-cli products get` — Dettaglio prodotto
- `swerpicommerce-pp-cli products list` — Di default le variazioni (prodotti con `prod_principale_id`) sono escluse: `include_variants=true` le include piatte...
- `swerpicommerce-pp-cli products update` — Campi non riconosciuti -> 400 VALIDATION_ERROR.

**shipping-methods** — Manage shipping methods

- `swerpicommerce-pp-cli shipping-methods` — Lista metodi di spedizione

**site-info** — Manage site info

- `swerpicommerce-pp-cli site-info` — Ritorna i dati del `DatiAzienda` mostrati nei footer del tema: ragione sociale, P.IVA, codice fiscale, indirizzo...

**swerpicommerce-auth** — Manage swerpicommerce auth

- `swerpicommerce-pp-cli swerpicommerce-auth me` — Endpoint senza effetti collaterali per validare un Bearer Token: restituisce la chiave associata, la scadenza e i...
- `swerpicommerce-pp-cli swerpicommerce-auth token` — Riceve `api_id` e `api_secret` e restituisce un Bearer Token senza scadenza. I token emessi da questo endpoint...
- `swerpicommerce-pp-cli swerpicommerce-auth token-revoke` — Effetto immediato. Lo scoping e per chiave: i token delle altre chiavi non sono visibili ne revocabili (404). Si puo...
- `swerpicommerce-pp-cli swerpicommerce-auth tokens-list` — Metadati dei token della chiave del chiamante (client, IP, creazione, ultimo uso, `current` per quello in uso). Il...

**update** — Stato/esito dell'ultimo aggiornamento dell'istanza, leggibile dal sito live anche dopo il riavvio dell'update agent (es. per capire perche' un update e' stato annullato dal gate).

- `swerpicommerce-pp-cli update` — `last` = esito persistito dell'ultimo update (sopravvive al riavvio dell'agent): `state`...


### Finding the right command

When you know what you want to do but not which command does it, ask the CLI directly:

```bash
swerpicommerce-pp-cli which "<capability in your own words>"
```

`which` resolves a natural-language capability query to the best matching command from this CLI's curated feature index. Exit code `0` means at least one match; exit code `2` means no confident match — fall back to `--help` or use a narrower query.

## Auth Setup

Run `swerpicommerce-pp-cli auth setup` for the URL and steps to obtain a token (add `--launch` to open the URL). Then store it:

```bash
swerpicommerce-pp-cli auth set-token YOUR_TOKEN_HERE
```

Or set `SWERPICOMMERCE_BEARER_AUTH` as an environment variable.

Run `swerpicommerce-pp-cli doctor` to verify setup.

## Agent Mode

Add `--agent` to any command. Expands to: `--json --compact --no-input --no-color --yes`.

- **Pipeable** — JSON on stdout, errors on stderr
- **Filterable** — `--select` keeps a subset of fields. Dotted paths descend into nested structures; arrays traverse element-wise. Critical for keeping context small on verbose APIs:

  ```bash
  swerpicommerce-pp-cli article-categories list --agent --select id,name,status
  ```
- **Previewable** — `--dry-run` shows the request without sending
- **Offline-friendly** — sync/search commands can use the local SQLite store when available
- **Non-interactive** — never prompts, every input is a flag
- **Explicit retries** — use `--idempotent` only when an already-existing create should count as success, and `--ignore-missing` only when a missing delete target should count as success

### Response envelope

Commands that read from the local store or the API wrap output in a provenance envelope:

```json
{
  "meta": {"source": "live" | "local", "synced_at": "...", "reason": "..."},
  "results": <data>
}
```

Parse `.results` for data and `.meta.source` to know whether it's live or local. A human-readable `N results (live)` summary is printed to stderr only when stdout is a terminal AND no machine-format flag (`--json`, `--csv`, `--compact`, `--quiet`, `--plain`, `--select`) is set — piped/agent consumers and explicit-format runs get pure JSON on stdout.

## Agent Feedback

When you (or the agent) notice something off about this CLI, record it:

```
swerpicommerce-pp-cli feedback "the --since flag is inclusive but docs say exclusive"
swerpicommerce-pp-cli feedback --stdin < notes.txt
swerpicommerce-pp-cli feedback list --json --limit 10
```

Entries are stored locally at `~/.swerpicommerce-pp-cli/feedback.jsonl`. They are never POSTed unless `SWERPICOMMERCE_FEEDBACK_ENDPOINT` is set AND either `--send` is passed or `SWERPICOMMERCE_FEEDBACK_AUTO_SEND=true`. Default behavior is local-only.

Write what *surprised* you, not a bug report. Short, specific, one line: that is the part that compounds.

## Output Delivery

Every command accepts `--deliver <sink>`. The output goes to the named sink in addition to (or instead of) stdout, so agents can route command results without hand-piping. Three sinks are supported:

| Sink | Effect |
|------|--------|
| `stdout` | Default; write to stdout only |
| `file:<path>` | Atomically write output to `<path>` (tmp + rename) |
| `webhook:<url>` | POST the output body to the URL (`application/json` or `application/x-ndjson` when `--compact`) |

Unknown schemes are refused with a structured error naming the supported set. Webhook failures return non-zero and log the URL + HTTP status on stderr.

## Named Profiles

A profile is a saved set of flag values, reused across invocations. Use it when a scheduled agent calls the same command every run with the same configuration - HeyGen's "Beacon" pattern.

```
swerpicommerce-pp-cli profile save briefing --json
swerpicommerce-pp-cli --profile briefing article-categories list
swerpicommerce-pp-cli profile list --json
swerpicommerce-pp-cli profile show briefing
swerpicommerce-pp-cli profile delete briefing --yes
```

Explicit flags always win over profile values; profile values win over defaults. `agent-context` lists all available profiles under `available_profiles` so introspecting agents discover them at runtime.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error (wrong arguments) |
| 3 | Resource not found |
| 4 | Authentication required |
| 5 | API error (upstream issue) |
| 7 | Rate limited (wait and retry) |
| 10 | Config error |

## Argument Parsing

Parse `$ARGUMENTS`:

1. **Empty, `help`, or `--help`** → show `swerpicommerce-pp-cli --help` output
2. **Starts with `install`** → ends with `mcp` → MCP installation; otherwise → see Prerequisites above
3. **Anything else** → Direct Use (execute as CLI command with `--agent`)

## MCP Server Installation

Install the MCP binary from this CLI's published public-library entry or pre-built release, then register it:

```bash
claude mcp add swerpicommerce-pp-mcp -- swerpicommerce-pp-mcp
```

Verify: `claude mcp list`

## Direct Use

1. Check if installed: `which swerpicommerce-pp-cli`
   If not found, offer to install (see Prerequisites at the top of this skill).
2. Match the user query to the best command from the Unique Capabilities and Command Reference above.
3. Execute with the `--agent` flag:
   ```bash
   swerpicommerce-pp-cli <command> [subcommand] [args] --agent
   ```
4. If ambiguous, drill into subcommand help: `swerpicommerce-pp-cli <command> --help`.
