# Swerpicommerce CLI

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

**IMPORTANTE — "committare/pushare" significa SEMPRE via API, MAI git
locale.** Il versionamento del sito vive sul suo server: o l'auto-commit
server-side a ogni scrittura, o `POST /fork/commit`. Se stai lavorando da
un ambiente locale (es. editor con file temporanei scaricati dal sito e
ricaricati via `PUT`), quei file sono solo appoggio: NON vanno mai
committati né pushati con git dalla macchina locale — nessun `git add`/
`git commit`/`git push` locale, in nessun caso. Flusso corretto, sempre:

1. upload via API (`PUT /design/...`, `PUT /pages/{id}/content`, ...)
2. commit di quello che è stato fatto: auto-commit ON lo fa da solo a ogni
   scrittura; con OFF si chiude con `POST /fork/commit`
3. aggiornamento versione: **sempre e solo quella fork**
   (`fork_version.json`, bumpata da `POST /fork/commit`) — MAI
   `version.json` globale, che è riservata all'upstream e non va toccata
4. **push sempre obbligatorio**: un commit non pushato non persiste (il
   prossimo update fa `git reset --hard origin/<branch>` e lo butta via).
   Gli endpoint pushano già da soli — è un altro motivo per cui il git
   locale è vietato: non passa dal push del server.

**Sbagliato qualcosa? La history git è consultabile via API**:
`GET /fork/log` (commit, filtrabili per file), `GET /fork/file` (contenuto
di un file a una revisione), `GET /fork/diff` (cosa è cambiato),
`GET /fork/search` (cerca nel contenuto dei sorgenti) e
`POST /fork/restore` (riporta uno o più file a una revisione precedente —
poi `POST /design/compile` se erano CSS/template).

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

- **Codici lingua** (`lang`): sono gli slug delle lingue configurate (es.
  `it`, `en`, `de`). Default = **lingua predefinita del sito** (tipicamente
  `it`). `GET /languages` li elenca; `POST /languages` crea/attiva una
  lingua nuova con il seed delle pagine di sistema.
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

## Install

The recommended path installs both the `swerpicommerce-pp-cli` binary and the `pp-swerpicommerce` agent skill in one shot:

```bash
npx -y @mvanhorn/printing-press install swerpicommerce
```

For CLI only (no skill):

```bash
npx -y @mvanhorn/printing-press install swerpicommerce --cli-only
```


### Without Node

The generated install path is category-agnostic until this CLI is published. If `npx` is not available before publish, install Node or use the category-specific Go fallback from the public-library entry after publish.

### Pre-built binary

Download a pre-built binary for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/swerpicommerce-current). On macOS, clear the Gatekeeper quarantine: `xattr -d com.apple.quarantine <binary>`. On Unix, mark it executable: `chmod +x <binary>`.

<!-- pp-hermes-install-anchor -->
## Install for Hermes

From the Hermes CLI:

```bash
hermes skills install mvanhorn/printing-press-library/cli-skills/pp-swerpicommerce --force
```

Inside a Hermes chat session:

```bash
/skills install mvanhorn/printing-press-library/cli-skills/pp-swerpicommerce --force
```

## Install for OpenClaw

Tell your OpenClaw agent (copy this):

```
Install the pp-swerpicommerce skill from https://github.com/mvanhorn/printing-press-library/tree/main/cli-skills/pp-swerpicommerce. The skill defines how its required CLI can be installed.
```

## Quick Start

### 1. Install

See [Install](#install) above.

### 2. Set Up Credentials

Get your access token from your API provider's developer portal, then store it:

```bash
swerpicommerce-pp-cli auth set-token YOUR_TOKEN_HERE
```

Or set it via environment variable:

```bash
export SWERPICOMMERCE_BEARER_AUTH="your-token-here"
```

### 3. Verify Setup

```bash
swerpicommerce-pp-cli doctor
```

This checks your configuration and credentials.

### 4. Try Your First Command

```bash
swerpicommerce-pp-cli article-categories list
```

## Usage

Run `swerpicommerce-pp-cli --help` for the full command reference and flag list.

## Commands

### article-categories

Manage article categories

- **`swerpicommerce-pp-cli article-categories article-category-create`** - Se `slug` manca viene generato dal nome (univoco per lingua).
- **`swerpicommerce-pp-cli article-categories article-category-delete`** - Gli articoli che la usano come principale restano (perdono il riferimento).
- **`swerpicommerce-pp-cli article-categories article-category-get`** - Dettaglio categoria articoli
- **`swerpicommerce-pp-cli article-categories article-category-update`** - Aggiorna una categoria articoli
- **`swerpicommerce-pp-cli article-categories list`** - Lista categorie articoli

### articles

Manage articles

- **`swerpicommerce-pp-cli articles authors-list`** - Gli stessi del select del pannello (utenti con ruolo + superuser). `Articolo.autore` e' una stringa: il valore da passare in POST/PUT /articles e' `nome`, cosi' come restituito qui.
- **`swerpicommerce-pp-cli articles create`** - Se `slug` manca viene generato dal titolo (univoco per lingua).
- **`swerpicommerce-pp-cli articles delete`** - Elimina un articolo
- **`swerpicommerce-pp-cli articles get`** - Dettaglio articolo
- **`swerpicommerce-pp-cli articles list`** - Lista articoli blog
- **`swerpicommerce-pp-cli articles update`** - Aggiorna un articolo

### attributes

Manage attributes

- **`swerpicommerce-pp-cli attributes create`** - Crea la definizione (nome, tipo, lingua, flag filtri) con eventuali
valori iniziali. `nome`+`lang` devono essere univoci (la risoluzione
dei `valori_attributi` in POST/PUT /products e' per nome esatto) ->
409 su duplicato. Badge, alternates multilingua e immagini dei valori
(tipo `immagine`) restano gestiti dal pannello.
- **`swerpicommerce-pp-cli attributes delete`** - Se l'attributo o un suo valore e' usato da prodotti/varianti risponde
**409 ATTRIBUTE_IN_USE** (a differenza del pannello, che cascata).
Per il tipo `immagine` elimina anche i file caricati.
- **`swerpicommerce-pp-cli attributes get`** - Dettaglio attributo con i suoi valori
- **`swerpicommerce-pp-cli attributes list`** - Definizioni di attributi e valori gestite dal pannello (es. Taglia:
S/M/L). I `valori_attributi` di POST/PUT /products vengono **risolti
contro questo registro** (match esatto case-sensitive su nome attributo
e valore): coppie non presenti nel registro -> 400 VALIDATION_ERROR.

I flag `attiva_filtri` / `separa_prodotti` configurano i filtri del
negozio e sono scrivibili con `PUT /attributes/{id}`. La configurazione
e' **globale per attributo**, non per categoria (il tab «Filtri» del
pannello sta sotto Dati e-commerce ma non esiste una configurazione
per-categoria). Nota frontend: la pagina categoria mostra prodotti e
filtri solo per le categorie **foglia** — una categoria con
sottocategorie rende l'elenco delle figlie.
- **`swerpicommerce-pp-cli attributes update`** - Aggiorna i campi passati: `attiva_filtri` (l'attributo appare nei
filtri di categoria/negozio, tab «Filtri» di Dati e-commerce),
`separa_prodotti` (le variazioni generano schede prodotto separate),
`nome`/`tipo`/`lang`. La configurazione filtri e' **globale per
attributo**, non per-categoria. Il rename dell'attributo non tocca i
nomi delle varianti (composti dai valori); `nome`+`lang` univoci ->
409 su duplicato. I valori si gestiscono con `/attributes/{id}/values`.

### brands

Manage brands

- **`swerpicommerce-pp-cli brands create`** - Il nome è trattato come chiave naturale: se esiste già un marchio con lo
stesso nome (case-insensitive) risponde **409** con l'id esistente,
così un sync ripetuto non genera duplicati.
- **`swerpicommerce-pp-cli brands delete`** - `Prodotto.marchio` è in CASCADE: se il marchio ha prodotti collegati la
cancellazione si porterebbe via anche quelli, quindi risponde **409**.
Riassegna prima i prodotti a un altro marchio.
- **`swerpicommerce-pp-cli brands get`** - Dettaglio marchio
- **`swerpicommerce-pp-cli brands list`** - Enumera i marchi referenziati da `ProductInput.marchio_id`. Filtra con
`?nome=` (match esatto, case-insensitive) per risolvere un marchio
dell'anagrafica esterna senza scorrere le pagine.
- **`swerpicommerce-pp-cli brands update`** - Rinomina un marchio

### cache

Manage cache

- **`swerpicommerce-pp-cli cache config-update`** - Aggiorna ConfigCache; i campi omessi restano invariati. Per disattivare
la cache pubblica delle pagine: `server_cache=false`. `cache_age` e la
durata in secondi dell'header `max-age`.
- **`swerpicommerce-pp-cli cache flush`** - `targets` (default `["pages","products"]`):
`pages` = reset del template loader + reload degli URL (pagine
nuove/rinominate/modificate live subito);
`products` = ricarica ProductDataCache (Redis);
`redis` = svuota l'intera cache Redis di Django (le sessioni sono su DB,
non vengono toccate).
- **`swerpicommerce-pp-cli cache get`** - `config` = impostazioni ConfigCache che governano gli header
Cache-Control delle pagine (browser/CDN): con `server_cache=false` la
cache pubblica e disattivata e le modifiche si vedono subito.
`product_cache` = stato della cache Redis di prezzi/quantita varianti.

### campaigns

Manage campaigns

- **`swerpicommerce-pp-cli campaigns create`** - `titolo` (oggetto email) e `testo` (HTML) possono arrivare da
`template_id`: il contenuto viene copiato alla creazione, modifiche
successive al template non toccano la campagna. `liste_ids` associa
le liste destinatarie.
- **`swerpicommerce-pp-cli campaigns delete`** - Coda email e associazioni liste eliminate in cascata; rifiutato mentre è in invio.
- **`swerpicommerce-pp-cli campaigns get`** - Dettaglio campagna
- **`swerpicommerce-pp-cli campaigns list`** - Campagne email
- **`swerpicommerce-pp-cli campaigns update`** - Rifiutato (400 CAMPAIGN_SENDING) mentre la campagna è in fase di invio.

### carts

Carrelli dello storefront (inclusi gli abbandonati, sola lettura)

- **`swerpicommerce-pp-cli carts get`** - Dettaglio carrello
- **`swerpicommerce-pp-cli carts list`** - Carrelli dello storefront, i più recenti per primi. `abbandonato` è
marcato dal job di schedulazione secondo la configurazione del modulo
carrello abbandonato; `recuperato` indica un carrello tornato attivo
dopo una mail di recupero. Per le automazioni di recupero esterne:
`?abbandonato=true&recuperato=false&older_than=<minuti>`.

### categories

Categorie prodotto

- **`swerpicommerce-pp-cli categories category-create`** - Se `slug` manca viene generato dal nome (con suffisso se non univoco).
- **`swerpicommerce-pp-cli categories category-delete`** - Come dal pannello: i prodotti che la referenziano mantengono l'id nel
campo `categorie`; le sottocategorie restano (perdono il padre).
- **`swerpicommerce-pp-cli categories category-get`** - Dettaglio categoria
- **`swerpicommerce-pp-cli categories category-update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.
- **`swerpicommerce-pp-cli categories list`** - Lista categorie prodotto

### config

Config per-istanza. `auto-commit` governa se le scritture API (pagine/CSS/JS/template) vengono committate+pushate automaticamente; con OFF si persiste/versiona via `POST /fork/commit`.

- **`swerpicommerce-pp-cli config autocommit-get`** - Stato dell'auto-commit delle scritture API
- **`swerpicommerce-pp-cli config autocommit-update`** - `autocommit=true` (default di fabbrica): ogni scrittura
(pagine/CSS/JS/template) viene committata+pushata su origin, cosi'
sopravvive al `reset --hard` dell'update. `autocommit=false`: le
scritture NON vengono committate -> per persisterle/versionarle si DEVE
chiamare `POST /fork/commit`.
- **`swerpicommerce-pp-cli config llms-get`** - Stato della generazione del file /llms.txt
- **`swerpicommerce-pp-cli config llms-update`** - Con `attiva_llms=true` il sito serve `/llms.txt`, generato dinamicamente dai campi `llms_index`/`llms_description`/`llms_section` di pagine, prodotti e articoli. Con `false` (default) `/llms.txt` risponde 404 anche se i campi sono compilati.

### custom-apps

Creazione e correzione di custom app Django montate nell'istanza (SOLO superuser/creatori). Queste operation sono visibili nello spec unicamente quando lo richiede una creator-key superuser. Vedi `GET /custom-apps-guide`.

- **`swerpicommerce-pp-cli custom-apps create`** - Scaffolda la app, la registra (INSTALLED_APPS + rotte + menu), la valida
con `check`+`makemigrations`+`migrate` in un subprocess isolato e la monta
via reload uwsgi. Se la validazione fallisce si fa revert e il sito live
resta intatto: risposta **422** con `error.details[0].message` = traceback.
Supporta modelli DB (le tabelle vengono create al montaggio).
**CSS**: includi un file `styles.css` nella root della app per stilizzarla —
viene pubblicato in `src/swcss_admin/custom_apps/<name>.css` e ricompilato in
`static/css/admin.css`. Dettagli in `GET /custom-apps-guide` → `css`.
- **`swerpicommerce-pp-cli custom-apps delete`** - Rimuove una custom app (superuser)
- **`swerpicommerce-pp-cli custom-apps get`** - Ritorna metadati + elenco file; con `include_content=true` (default) anche il contenuto di ogni file.
- **`swerpicommerce-pp-cli custom-apps list`** - Ritorna nome, label, stato (`active` / `disabled` se un errore di boot
l'ha auto-disabilitata) e sintesi errore. Solo per creator-key superuser.
- **`swerpicommerce-pp-cli custom-apps update`** - Applica i `files` forniti (create/overwrite) e gli eventuali `delete`,
poi rivalida e rimonta. **Atomico**: se la validazione fallisce la
versione live resta l'ultima funzionante e ricevi **422** col traceback.
È il passo di auto-correzione del loop.

### custom-apps-guide

Manage custom apps guide

- **`swerpicommerce-pp-cli custom-apps-guide custom_apps_guide`** - Guida al workflow create/correzione custom app (superuser)

### customers

Clienti e punti fedeltà

- **`swerpicommerce-pp-cli customers batch`** - Crea piu clienti
- **`swerpicommerce-pp-cli customers create`** - Crea un cliente
- **`swerpicommerce-pp-cli customers delete`** - Elimina cliente, account di login e indirizzi di spedizione. Se il cliente
ha ordini risponde 409: ripetere con `?force=true` per eliminarlo comunque
(gli ordini restano, scollegati dal cliente).
- **`swerpicommerce-pp-cli customers get`** - Cliente con email dell'account e indirizzi di spedizione.
- **`swerpicommerce-pp-cli customers list`** - `data_inizio` / `data_fine` filtrano sulla **data di registrazione**
(`data_creazione`), `modified_after` sull'**ultima modifica** —
quest'ultimo è il parametro per il polling incrementale.

`sort` default `-id`. L'ordinamento è sempre **deterministico** (`id`
come tiebreaker), quindi la paginazione a offset non salta né duplica
righe nemmeno durante un import di massa.
- **`swerpicommerce-pp-cli customers update`** - Aggiorna i campi indicati. `email` e `password` agiscono sull'account di
login collegato (l'email deve restare univoca). Campi non riconosciuti
-> 400 VALIDATION_ERROR.

### design

Sorgenti SWCSS del tema, loghi/favicon e compilazione bundle. Per comporre pagine via API: vedi la guida rapida nella descrizione dello schema (in alto) e la guida completa su `GET /design/swcss-guide`. Dopo ogni modifica a contenuti o CSS serve `POST /design/compile` perché vada live (i loghi fanno eccezione: non passano dal CSS).

- **`swerpicommerce-pp-cli design color-create`** - `valore` in hex (`#RGB` o `#RRGGBB`, normalizzato a `#rrggbb`). La
`classe_css` e' generata dal `nome` (slug `sw-<nome>`) e deve essere
univoca. Il colore nasce sempre non di sistema. Dopo la creazione
eseguire `POST /design/compile` perche' la variabile `--sw-<classe>`
vada live.
- **`swerpicommerce-pp-cli design color-delete`** - Rimuove il record. I colori di sistema non sono eliminabili (403). Dopo
la modifica eseguire `POST /design/compile`.
- **`swerpicommerce-pp-cli design color-get`** - Dettaglio di un colore
- **`swerpicommerce-pp-cli design color-update`** - Modifica `nome`/`valore`/`descrizione`/`attivo`. Cambiare `nome`
rigenera `classe_css`: sui colori di sistema e' vietato (403) perche'
romperebbe i riferimenti per slug in template ed email — di questi si
cambia solo il `valore`. Dopo la modifica eseguire `POST /design/compile`.
- **`swerpicommerce-pp-cli design colors-list`** - Tutti i record `CustomColor`. Ognuno espone `classe_css` (es.
`sw-primario`): usabile nei template come classe `.sw-primario` o come
variabile `var(--sw-primario)`. `sistema: true` marca i colori di base
referenziati per slug da template ed email (valore modificabile, slug no).
- **`swerpicommerce-pp-cli design compile`** - Rigenera i bundle statici (stessa compilazione del pannello Grafica)
con tree-shaking sulle classi usate nei template: va eseguita dopo
ogni modifica a contenuti pagina o sorgenti CSS perché le modifiche
vadano live. Operazione sincrona (alcuni secondi).
- **`swerpicommerce-pp-cli design css-delete`** - Rifiutato (400 DEFAULT_CSS_FILE) sui file del set predefinito della
sezione: il ripristino default li ricreerebbe — svuotali invece.
- **`swerpicommerce-pp-cli design css-get`** - Legge un sorgente CSS
- **`swerpicommerce-pp-cli design css-list`** - File CSS delle sezioni `pagine-sistema/*` (stesse del pannello
Grafica), del layer `globale` (fallback: default d'elemento validi su
tutto il sito, override dalle sezioni) e del layer globale `custom`
(componenti riusabili). Il layer `base/` (variabili, reset, utility)
non è scrivibile: è il framework (le sue variabili si leggono da
`GET /design/variables`). `predefinito: true` = fa parte del set base
della sezione (il ripristino default lo sovrascrive).

Il listing è **ricorsivo**: i file dentro sottocartelle compaiono col
loro path relativo nel campo `nome` (es. `header-trasparente/link.css`).
Una sezione può organizzare i file in sottocartelle a piacere — usa il
`nome` così com'è in `GET/PUT/DELETE /design/css/{section}/{nome}`.
- **`swerpicommerce-pp-cli design css-put`** - Sovrascrive l'intero file (201 se creato). Le modifiche NON vanno
live finché non si esegue `POST /design/compile`. Convenzioni: un
file per pagina/componente, classi prefissate `sw-*`, variabili e
breakpoint del sistema — vedi `GET /design/swcss-guide`.

Se il `filename` contiene sottocartelle (es.
`header-trasparente/link.css`) le cartelle intermedie vengono create
automaticamente: utile per organizzare il layer `custom`.
- **`swerpicommerce-pp-cli design guide`** - Markdown operativo: architettura dei layer, regole del design system,
flusso pagina+CSS+compilazione, utility disponibili, componenti
riutilizzabili (es. galleria immagini con lightbox `sw-gallery`),
errori tipici. Da leggere PRIMA di scrivere contenuti o CSS.
- **`swerpicommerce-pp-cli design js-delete`** - Elimina un file JS per-pagina
- **`swerpicommerce-pp-cli design js-get`** - Legge un file JS per-pagina
- **`swerpicommerce-pp-cli design js-list`** - JS per-istanza in `/static/js/custom/`: il file `<slug>.js` (o
`<slug>_<lang>.js` per le lingue non predefinite) viene caricato
**automaticamente** dalla pagina con quello slug, con `defer` e
cache-buster. Nessuna compilazione necessaria: il file è servito
così com'è, subito. Per JS condiviso tra più pagine usare un nome
non-slug e referenziarlo con un tag `<script src>` nel contenuto.
- **`swerpicommerce-pp-cli design js-put`** - Sovrascrive l'intero file (201 se creato) e va live subito — niente
compilazione, il cache-buster è sull'mtime. Vanilla JS consigliato;
eseguito con `defer` dopo il parse dell'HTML.
- **`swerpicommerce-pp-cli design logos-get`** - Gli slot del tema (`logo_black`, `logo_white`, `logo_mobile_black`,
`logo_mobile_white`, `logo_email`, `favicon`) con `nome` del file, `url`
pubblico (`/static/img/uploads/...`) e `esiste`, che è `false` quando lo
slot punta ancora a un default mai caricato su questa installazione (il
sito servirebbe un 404). In `opzioni` i flag di trasparenza usati dal tema.
- **`swerpicommerce-pp-cli design logos-update`** - Stessa operazione del pannello Grafica -> Loghi. Il file va caricato
prima in libreria con `POST /media` (`folder: logos`, ammette anche
svg/ico): qui si assegna il suo `nome` a uno slot, e i campi non citati
restano invariati. Un file inesistente in libreria dà 400
`MEDIA_NOT_FOUND`. Finché un file è assegnato a uno slot,
`DELETE /media/logos/{filename}` lo rifiuta con 400 `LOGO_IN_USE`.
Non serve `POST /design/compile`: i loghi non passano dal CSS.
- **`swerpicommerce-pp-cli design template-delete`** - 403 `UPSTREAM_TEMPLATE` se il file è upstream o `base.html` (sola lettura).
- **`swerpicommerce-pp-cli design template-get`** - Legge il sorgente di un template, anche upstream (sola lettura, come
riferimento per crearne uno tuo). `base.html` non è leggibile (404).
- **`swerpicommerce-pp-cli design template-put`** - Sovrascrive l'intero file (201 se creato). **403 `UPSTREAM_TEMPLATE`**
se il target è upstream o `base.html` (sola lettura): usa un nome diverso,
non-upstream. Non va live finché non esegui `POST /design/compile` (il
tree-shake CSS scansiona i template referenziati dalle pagine).
- **`swerpicommerce-pp-cli design templates-guide`** - Markdown operativo: cosa sono partial e pagine di sistema, come si creano
e si collegano (header_name / Header_Footer / nome_file), cosa è upstream
in sola lettura, flusso e compilazione. Da leggere PRIMA di creare template.
- **`swerpicommerce-pp-cli design templates-list`** - Elenca i template `.html` delle aree `partials`
(`templates/frontend/partials/`) e `pagine_sistema`
(`templates/frontend/pagine_sistema/`). Guida completa: `GET
/design/templates-guide`.

**Di default elenca solo i file editabili** (creati nel fork, per-istanza).
I file **upstream** (tutto ciò che arriva da SwerpiCommerce: tracciato in
git, più i `*_base*`) sono in **sola lettura** e nascosti dal list; passa
`include_upstream=true` per vederli (compaiono con `editabile: false`).
`base.html` (layout master) non è mai esposto. Ogni voce ha `upstream` e
`editabile`. Dopo aver creato/modificato un file editabile serve
`POST /design/compile`; per renderizzarlo, puntalo dai campi
`page.header_name`, `Header_Footer.*` o `PagineSistema.nome_file`.

**Multilingua — header/footer/menu per lingua.** Due leve, spesso da usare
insieme:

*(A) Stringhe traducibili (gettext + `.po`).* Testo dell'header/footer/menu
(topbar "Spedizione gratuita", voci di menu, CTA "Vai al negozio", slogan
mega-menu, minicart). Due cataloghi per lingua sotto
`locale/<lang>/LC_MESSAGES/`:
- **`django.po` — dominio `django`, SOLA LETTURA.** Arriva da upstream, lo
  usano i tag standard `{% trans %}` / `{% blocktrans %}` (es. il minicart).
  Il fork non lo modifica.
- **`custom.po` — dominio `custom`, LETTURA/SCRITTURA (per-istanza, untracked).**
  È la leva del fork. In template: `{% load custom_i18n %}` e poi
  `{% custom_trans "id" %}` oppure `{{ "id"|custom_gettext }}`
  (`frontend/templatetags/custom_i18n.py` carica `custom.mo`).

  Una stringa **letterale senza tag** (es. la topbar `Spedizione gratuita a
  partire da 50 €` in `header_base.html`) resta IT in ogni lingua: per
  tradurla wrappala in `custom_trans` e aggiungi il `msgstr` in `custom.po`
  di **ogni** lingua.

  **Compilazione `.mo` OBBLIGATORIA** dopo ogni modifica ai `.po`:
  `bash app/compila_locales.sh` (`manage.py compilemessages` per `django.po`
  + `msgfmt` per `custom.po`). Senza `.mo` aggiornato la traduzione non
  appare. Nota locale: la lingua `ar` ha `href=es-AR` → i suoi cataloghi
  stanno in `locale/es_AR/` (mappatura `to_locale`).

*(B) File template per lingua (differenze strutturali, non solo stringhe).*
La view sceglie il file con `Header_Footer.objects.filter(lang=<lingua>)` e,
se il record **manca**, fa fallback sulla lingua predefinita → header IT.
Quando ti basta tradurre stringhe usa (A) su un unico file condiviso; crea
file separati solo se cambia il markup:
1. `header_<lang>.html`, `header_sticky_<lang>.html`, `footer_<lang>.html`
   (e se serve `minicart_<lang>.html`, incluso dal rispettivo header — 1
   sola istanza di `#carrello` a runtime), con i **link localizzati** (es.
   `/chi-siamo/` → slug tradotto della pagina);
2. punta i partial di quella lingua col record `Header_Footer` **via API**:
   `PUT /header-footer/{lang}` `{ "header_name": "header_ar.html", ... }`
   (upsert; crea il record se manca — stessa cosa del pannello
   `/sw-back/setting/grafica`). `GET /header-footer` mostra
   `lingue_senza_record` = le lingue scoperte (fallback IT);
3. assicura **un record per OGNI lingua attiva** (crea `ar`); i record
   globali evitano di dover forzare `page.header_name` su ogni pagina.

> Un record `Header_Footer` mancante è la causa tipica di "le pagine di una
> lingua mostrano l'header della lingua default": la view fa
> `Header_Footer.filter(lang=<lingua>).first()` e, se vuoto, ripiega sulla
> predefinita. La fix alla radice è `PUT /header-footer/{lang}` (globale);
> `page.header_name` sulla singola pagina serve solo come override puntuale.

Dopo modifiche ai template: `POST /design/compile`. Dopo modifiche ai `.po`:
`app/compila_locales.sh`. Il 500 del blog invece NON è i18n: è un problema DB
(colonne `JSONField` da `text` a `jsonb` post-migrazione Postgres), risolto
upstream.
- **`swerpicommerce-pp-cli design variables-get`** - Riferimento in sola lettura per comporre CSS con `var(--...)`. Due gruppi:
- `sistema` (`base/variabili_sistema.css`): token immutabili del framework
  — scala tipografica (`--text-*`, `--lh-*`), `--radius-*`, `--font-*`,
  più i `breakpoints` (`--mb`, `--sm`, … usati come `@media (--sm)`).
  Fanno parte di `base/`, NON si modificano.
- `colori` (`base/variabili.css`): le custom property `--sw-*` generate
  dalla palette. Sono un file **derivato**: per modificarle usa
  `/design/colors` (poi `POST /design/compile` rigenera questo file).
Ogni gruppo espone `tokens` (mappa nome→valore, pronta all'uso) e `raw`
(il CSS sorgente). Nessun PUT/DELETE: le variabili non si scrivono qui.

### discount-codes

Codici sconto

- **`swerpicommerce-pp-cli discount-codes create`** - `codice` duplicato -> 400 CODE_IN_USE (il checkout cerca per codice).
- **`swerpicommerce-pp-cli discount-codes delete`** - Gli ordini che lo hanno usato conservano lo storico in `OrdineCodiciSconto`.
- **`swerpicommerce-pp-cli discount-codes get`** - Dettaglio codice sconto
- **`swerpicommerce-pp-cli discount-codes list`** - Lista codici sconto
- **`swerpicommerce-pp-cli discount-codes update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.

### email-lists

Manage email lists

- **`swerpicommerce-pp-cli email-lists create`** - Crea una lista email
- **`swerpicommerce-pp-cli email-lists delete`** - Le iscrizioni vengono eliminate in cascata; i clienti che la avevano
come lista principale ripiegano sulla lista di default.
- **`swerpicommerce-pp-cli email-lists get`** - Dettaglio lista email
- **`swerpicommerce-pp-cli email-lists list`** - Liste email
- **`swerpicommerce-pp-cli email-lists update`** - Aggiorna una lista email

### email-templates

Manage email templates

- **`swerpicommerce-pp-cli email-templates create`** - Nei contenuti si possono usare placeholder `{chiave}`: vengono
risolti all'invio transazionale (POST /emails/send) da `variabili`
più i dati del cliente (`nome`, `cognome`, `email`).
- **`swerpicommerce-pp-cli email-templates delete`** - Le campagne create dal template non vengono toccate (il contenuto è copiato alla creazione).
- **`swerpicommerce-pp-cli email-templates get`** - Dettaglio template email
- **`swerpicommerce-pp-cli email-templates list`** - Template email
- **`swerpicommerce-pp-cli email-templates update`** - Aggiorna un template email

### emails

Manage emails

- **`swerpicommerce-pp-cli emails send`** - Invio sincrono via SMTP Marketing a `cliente_id` (email dell'account)
oppure `email` diretta. Contenuto diretto (`oggetto` +
`contenuto_html`) o da `template_id`. I placeholder `{chiave}`
vengono risolti da `variabili` più i dati cliente (`nome`, `cognome`,
`email`); quelli senza valore restano intatti. È il mattone per le
automazioni esterne (es. recupero carrelli abbandonati via GET /carts).

### extra-tabs

Tab aggiuntivi della scheda prodotto (pannello Marketing & SEO -> Tab Extra). Un tab `generale` porta un HTML unico su tutti i prodotti del suo ambito; un tab `specifico` compare vuoto nella scheda admin dei prodotti dell'ambito e ogni prodotto scrive il proprio HTML (campo `tab_extra` di `PUT /products/{id}`); in vetrina compare solo dove e' compilato. L'ambito ha lo stesso schema degli sconti quantita': `target_prodotti` + liste `prodotti`/`categorie` con `escluso`.

- **`swerpicommerce-pp-cli extra-tabs create`** - `slug` omesso -> ricavato dal `nome`; deve essere unico per lingua (409 EXTRA_TAB_DUPLICATE_SLUG). Per un tab `specifico` il contenuto si scrive poi prodotto per prodotto con `PUT /products/{id}` (`tab_extra`).
- **`swerpicommerce-pp-cli extra-tabs delete`** - Per un tab `specifico` cancella anche i contenuti scritti nei singoli prodotti.
- **`swerpicommerce-pp-cli extra-tabs get`** - Dettaglio tab extra
- **`swerpicommerce-pp-cli extra-tabs list`** - Lista tab extra
- **`swerpicommerce-pp-cli extra-tabs update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR. `prodotti` e `categorie`, se passati, **sostituiscono** per intero l'ambito.

### fonts

Font personalizzati (woff2) e assegnazione ai campi tipografici (dove applicarli)

- **`swerpicommerce-pp-cli fonts assignments-get`** - Restituisce `assignments` (chiave `font_<campo>_id` -> id del font
assegnato) e `campi_disponibili` (l'elenco COMPLETO dei campi
assegnabili, anche quelli senza assegnazione). E' il "dove": il
prefisso del campo indica la sezione (`cms_`, `categoria_prodotto_`,
`prodotto_`, `carrello_`, `checkout_`, `blog_`, `mio_account_`,
`minicart_`, `header_footer_`; nessun prefisso = ecommerce generale).
- **`swerpicommerce-pp-cli fonts assignments-update`** - Fa merge della mappa `assignments` in `font_fields`: valore = id font
(deve esistere) per assegnare, `null` per rimuovere (il campo torna al
font di default). I campi non citati restano invariati. Chiavi fuori
dall'elenco `campi_disponibili` di GET /fonts/assignments -> 400. Esempio: Poppins
ovunque tranne checkout = assegnare i campi delle sezioni volute e
azzerare/lasciare quelli con prefisso `checkout_`. Dopo la modifica
eseguire `POST /design/compile`.
- **`swerpicommerce-pp-cli fonts create`** - Contenuto base64 nel body JSON (solo `.woff2`, max 5 MB decodificati).
Servito da `/static/fonts/{nome}.woff2`. Per piu' pesi della stessa
famiglia usare `nome` diversi (es. Poppins-Regular, Poppins-Bold) e la
STESSA `famiglia` ("Poppins"). Dopo l'upload eseguire `POST /design/compile`
perche' la @font-face vada live.
- **`swerpicommerce-pp-cli fonts delete`** - Rimuove record + associazioni e, se nessun altro record usa lo stesso
file, il woff2 da /static/fonts/. I campi tipografici che lo riferivano
vanno riassegnati. Dopo la modifica eseguire `POST /design/compile`.
- **`swerpicommerce-pp-cli fonts get`** - Dettaglio di un font
- **`swerpicommerce-pp-cli fonts list`** - Tutti i record `Fonts`. `src` e' l'URL pubblico del woff2 servito dal
dominio del sito (`/static/fonts/...`), quindi locale e cacheabile (no
base64 inline nel CSS). Una famiglia puo' avere piu' record (uno per
peso/stile) che condividono `famiglia`: la regola @font-face li unisce.
- **`swerpicommerce-pp-cli fonts update`** - Modifica famiglia/weight/style/display/attivo. Il file woff2 non si
sostituisce (per cambiarlo: elimina e ricarica). Dopo la modifica
eseguire `POST /design/compile`.

### fork

Versione dell'ambiente fork, commit del working tree e history git — tutto **sul server del sito**: "committare/pushare" si fa SEMPRE con questi endpoint (o con l'auto-commit server-side), MAI con git da un ambiente locale. Eventuali copie locali dei file (scaricate per editing e ricaricate via PUT) non vanno mai committate localmente. Operation disponibili: log dei commit (`/fork/log`), lettura di un file a una revisione (`/fork/file`), diff (`/fork/diff`), ricerca nei sorgenti (`/fork/search`) e rollback di file (`/fork/restore`). `version.json` resta riservato all'upstream; `fork_version.json` (intero, baseline 100) traccia le release del fork — patch +1, major +10, minor +100.

- **`swerpicommerce-pp-cli fork commit`** - Stagea l'INTERO working tree (`git add -A`), bumpa `fork_version.json`
(la versione fork: MAI toccare `version.json` globale, riservata
all'upstream) e crea un commit con la `description` (obbligatoria, deve
descrivere cosa e' stato fatto), poi pusha su origin/<branch corrente>
— il push e' parte del flusso, sempre obbligatorio: cosi' l'update
(`git reset --hard origin/<branch>`) ripristina le modifiche invece di
cancellarle. Incremento per `level`: `minor` +100 (default), `major` +10,
`patch` +1.

`force=true` (DISTRUTTIVO): push con `--force`, sovrascrive la history
remota — usare solo per sbloccare una divergenza facendo prevalere il fork.
- **`swerpicommerce-pp-cli fork diff`** - Diff unificato da `from` (default `HEAD`) a `to`. Con `to` omesso
confronta contro il **working tree**: mostra le modifiche non ancora
committate (utile con auto-commit OFF, prima di `POST /fork/commit`).
Per "cosa e' cambiato nell'ultimo commit": `from=HEAD~1`. `path` limita
il diff a un file o directory. Output tagliato a ~200KB
(`truncated: true`): su repo grossi restringere sempre con `path`.
- **`swerpicommerce-pp-cli fork file-get`** - Legge un file com'era in una revisione, senza toccare il working tree.
`rev` accetta uno sha di `GET /fork/log` (anche abbreviato) o un ref
relativo (`HEAD~2`); default `HEAD` = ultimo commit. Solo file di testo
UTF-8: i binari danno 400. Risposta: `path`, `rev` (sha risolto pieno),
`size` (byte) e `content`. Per rimettere in opera una vecchia versione
usare `POST /fork/restore` (o riscrivere il contenuto coi normali PUT).
- **`swerpicommerce-pp-cli fork log`** - Commit del branch corrente, dal piu' recente. Ogni voce: `sha` (pieno),
`short` (abbreviato), `date` (ISO 8601), `author`, `message` e `files`
toccati. Con `path` filtra la history di un singolo file o directory —
e' il modo per trovare la revisione "buona" da cui leggere
(`GET /fork/file`) o ripristinare (`POST /fork/restore`).
- **`swerpicommerce-pp-cli fork restore`** - `git checkout <rev> -- <paths>`: riporta i file elencati al contenuto
che avevano nella revisione `rev`. Flusso tipico di rollback:
`GET /fork/log?path=...` per trovare la revisione buona ->
`GET /fork/file` o `GET /fork/diff` per verificarne il contenuto ->
`POST /fork/restore`. **Sovrascrive** il contenuto corrente dei file.

Con auto-commit ON il ripristino viene anche committato+pushato
(`committed: true` nella risposta); con OFF resta nel working tree e va
persistito via `POST /fork/commit`. Dopo il restore di CSS o template
serve `POST /design/compile` perche' vada live.

Nessun limite di area: puo' ripristinare qualunque file del repo —
usare path mirati (i file toccati dall'errore), mai directory larghe.
- **`swerpicommerce-pp-cli fork search`** - Cerca `q` nel **contenuto** dei file del repo (template, CSS, JS,
contenuti pagina, custom app...) — complementare alle list di
`/design/*`, che elencano solo i nomi. Default: ricerca **letterale**
nel working tree, inclusi i file nuovi non ancora committati;
`regex=true` interpreta `q` come regex POSIX estesa; con `rev` cerca
nello snapshot di quella revisione (es. per ritrovare codice cancellato).
`path` limita a un file o directory. Ogni match: `file`, `line`, `text`.
Massimo `limit` match (`meta.truncated=true` se ce n'erano altri);
i file binari sono esclusi.
- **`swerpicommerce-pp-cli fork version-get`** - Legge `fork_version.json`: `version` (intero), `release_date` dell'ultimo
commit fork e `description` di cosa conteneva. In upstream resta al
baseline 100 (non e' un fork).

### forms

Form personalizzati (contatti, richieste info): il record Form via API contiene destinatario/oggetto/template email/azione/config iubenda; i CAMPI compilabili (inclusa la checkbox privacy, obbligatoria) vivono nel markup della pagina, non nel record. Il captcha (reCAPTCHA/hCaptcha), se attivo, è gestito in automatico dal JS di pagina: il widget si aggancia al bottone `.sw-form`, nessun placeholder o classe dedicata nel markup. Campi allegato (`input type=file`, classe `sw-form-file`): il file va in `/uploads/form/<form_id>/` e nella submission il campo vale l'URL; il file è anche allegato all'email di notifica. Consenso privacy, allegati e registrazione nella Consent Database iubenda (`iubenda_attivo` + `iubenda_mapping`) sono documentati in `GET /forms-guide`.

- **`swerpicommerce-pp-cli forms create`** - Crea un form
- **`swerpicommerce-pp-cli forms delete`** - Elimina un form (e le sue submission)
- **`swerpicommerce-pp-cli forms get`** - Dettaglio di un form
- **`swerpicommerce-pp-cli forms list`** - Elenca i record Form (destinatario, azione, corpo email). Usa l'`id`
come `data-sw-custom-form` nel markup del form in pagina. Guida completa
su `GET /forms-guide`.
- **`swerpicommerce-pp-cli forms update`** - Modifica un form (campi omessi invariati)

### forms-guide

Manage forms guide

- **`swerpicommerce-pp-cli forms-guide forms_guide`** - Markdown operativo: record Form + markup SWCSS + contratto di
sw_form.js + **consenso privacy** (checkbox `sw-required`, obbligatoria
per l'invio) e integrazione **Consent Database iubenda** (per-form:
`iubenda_attivo` + `iubenda_mapping`, registrazione server-side alla
submit). Da leggere PRIMA di comporre una pagina con un form.

### header-footer

Manage header footer

- **`swerpicommerce-pp-cli header-footer list`** - `Header_Footer` mappa, **per lingua**, i partial di default
`header_name` / `header_sticky_name` / `footer_name` / `breadcrumbs_name`
(usati quando la pagina non forza il proprio, cioè `page.header_name`
vuoto). Se manca il record per una lingua, la view fa **fallback alla lingua
predefinita**: `lingue_senza_record` elenca le lingue scoperte (tipico
sintomo: pagine di quella lingua che mostrano header/menu nella lingua
default). Correggi con `PUT /header-footer/{lang}`.
- **`swerpicommerce-pp-cli header-footer set`** - Upsert del record `Header_Footer` di `{lang}` (stessa cosa del pannello
`/sw-back/setting/grafica`, ora via API). **Fix alla radice** del caso
"le pagine di una lingua cadono sull'header della lingua default": imposta
i partial di quella lingua a livello **globale**, invece di forzare
`page.header_name` su ogni singola pagina. Aggiorna **solo** i campi
presenti nel body (gli altri, alla creazione, prendono il default del
modello). Ogni file indicato deve **già esistere** in `partials` (crealo
prima con `PUT /design/templates/partials/...`), altrimenti `404`.
`201` se il record viene creato, `200` se aggiornato. Lingua inesistente → `404`.

### languages

Manage languages

- **`swerpicommerce-pp-cli languages create`** - Equivalente al pannello: crea la lingua e fa il seed delle pagine di sistema e dei messaggi email per la nuova lingua (le traduzioni di sistema esistono per it/en/fr/es/de; per altre lingue gli slug delle pagine di sistema nascono nella lingua di fallback). `predefinita=true` toglie il flag alle altre. Dopo la creazione la lingua e' subito navigabile; header/footer per-lingua vanno configurati con `PUT /header-footer/{lang}`. Modifica/rinomina/eliminazione restano operazioni da pannello.
- **`swerpicommerce-pp-cli languages list`** - I valori validi dei campi `lang`. `ha_header_footer=false` indica che header/footer per quella lingua non sono ancora configurati (il rendering usa i fallback): completare con `PUT /header-footer/{lang}`.

### media

Libreria media globale (immagini di prodotti, categorie, blog e loghi). La cartella `logos` contiene i file di loghi e favicon, serviti da `/static/img/uploads/`: caricato il file qui, si assegna a uno slot con `PUT /design/logos`.

- **`swerpicommerce-pp-cli media delete`** - Rimuove il file dallo storage e azzera i riferimenti diretti nel
database (record FotoProdotto per product_images; campi `immagine` /
`immagine_evidenza` per le altre cartelle). I riferimenti dentro
l'HTML dei contenuti (articoli, pagine) non vengono toccati.

**400 `LOGO_IN_USE`** se il file è nella cartella `logos` ed è ancora
assegnato a uno slot: gli slot non sono annullabili e il sito servirebbe
un 404. Assegna prima un altro file allo slot con `PUT /design/logos`.
- **`swerpicommerce-pp-cli media get`** - Dettaglio di un file della libreria
- **`swerpicommerce-pp-cli media list`** - File immagine delle cartelle gestite (foto prodotto, immagini categorie
prodotto, articoli blog, categorie blog, loghi, cartelle delle custom
app `<app>.<tipo>`), i più recenti per primi.
Ogni file include `alt` (testo alternativo della libreria, gestibile
via PUT) e `valore_campo`, il valore pronto da scrivere nel campo
collegato della risorsa: `immagine` della categoria (cat_images),
`immagine_evidenza` dell'articolo (blog), `immagine` della categoria
blog (blog_cat_images), lo slot di `PUT /design/logos` (logos), il
campo immagine del modello custom app (cartelle `<app>.<tipo>`, che
salvano il solo filename). Per le foto prodotto (`product_images`,
valore_campo null) l'associazione passa da /products/{id}/images, che
con `source: {folder, nome}` copia un file della libreria.
- **`swerpicommerce-pp-cli media update`** - `alt` viene salvato in libreria e propagato agli usi correnti del file
(foto prodotto, `immagine_alt` delle categorie). `nome` rinomina il
file nello storage (stessa estensione) aggiornando i riferimenti
diretti nel database: dopo la rinomina fa fede `nome` nella risposta.
Rinominare un file della cartella `logos` aggiorna anche gli slot di
`/design/logos` che lo puntano, quindi il sito continua a servirlo.
- **`swerpicommerce-pp-cli media upload`** - Contenuto base64 nel body JSON (max 10 MB decodificati; il body JSON
complessivo, base64 ≈ ×1,33, è limitato a 16 MiB: oltre risponde 413
`PAYLOAD_TOO_LARGE`; estensioni jpg/jpeg/png/webp/gif/avif, più
svg/ico nella sola cartella `logos`).
Gli SVG con contenuto attivo (`<script>`, `javascript:`, handler `on*=`)
sono rifiutati con 400 `INVALID_IMAGE`. In caso di nome file già
esistente lo storage lo rinomina: fa fede `nome` nella risposta.
L'upload non collega il file a nessuna risorsa: scrivere `valore_campo`
nel campo della risorsa di destinazione (es. PUT /categories/{id} con
`immagine`); per la cartella `logos` l'assegnazione allo slot passa da
`PUT /design/logos`. Le foto prodotto si caricano da /products/{id}/images.
Le immagini delle custom app si caricano qui con folder `<app>.<tipo>`
(finiscono in /uploads/<app>/<tipo>_img/): nel record del modello
dell'app si salva `valore_campo` (il filename).

### orders

Ordini

- **`swerpicommerce-pp-cli orders batch`** - Crea piu ordini
- **`swerpicommerce-pp-cli orders create`** - Crea un ordine
- **`swerpicommerce-pp-cli orders get`** - Dettaglio ordine
- **`swerpicommerce-pp-cli orders list`** - **Paginata e filtrabile**: pensata per il polling incrementale, non per
riscaricare lo storico a ogni ciclo.

- `data_inizio` / `data_fine` filtrano sulla **data di creazione**
  (`ordine.data`) e sono **inclusivi**. Accettano una data secca
  (`2026-08-03`) o un date-time ISO 8601: la data secca come `data_fine`
  copre l'intera giornata.
- `modified_after` filtra sull'**ultima modifica** (`ordine.ultima_modifica`):
  e questo il parametro per il polling incrementale, perche intercetta i
  cambi di stato/tracking di ordini creati settimane prima.
- `stato` accetta piu valori separati da virgola
  (`?stato=completato,spedito`).
- `sort` default `-id`. L'ordinamento e sempre **deterministico** (`id`
  come tiebreaker), quindi la paginazione a offset non salta ne duplica
  righe nemmeno durante un import di massa.
- **`swerpicommerce-pp-cli orders update`** - Aggiorna i campi indicati dell'ordine. L'annullamento e un update di stato:
`{"stato": "annullato"}`. Gli ordini non si eliminano (la storia vendite
resta integra). Campi non riconosciuti -> 400 VALIDATION_ERROR.

### page-templates

Manage page templates

- **`swerpicommerce-pp-cli page-templates assign`** - Scrive `PagineSistema.nome_file` (stessa cosa del pannello
/sw-back/setting/grafica). I file di sistema di default sono upstream/
read-only e **non vanno modificati**: per personalizzare una pagina si crea
una **variante del fork** (es. `negozio-miosito.html`) con
`PUT /design/templates/pagine_sistema/<file>` e la si assegna qui.
Il file deve **già esistere** nell'area `pagine_sistema`, altrimenti `404`
(l'assegnazione non crea il file).
- **`swerpicommerce-pp-cli page-templates list`** - `presets` = template di partenza per le pagine nuove;
`pagine_sistema` = elenco `{tipo, nome_file}` delle pagine di sistema (i
`tipo` sono quelli di `SystemPageType`, incluse le sotto-pagine del blog:
`blog-articolo`, `blog-categoria`, `blog-tag`, `blog-search`). Il
`template_name` delle pagine normali è gestito dal sistema: ogni pagina ha
il suo file contenuto per slug.

### pages

Pagine CMS

- **`swerpicommerce-pp-cli pages create`** - Come dal pannello: crea il record e il file contenuto
`templates/frontend/<slug>[_<lang>].html` (dal preset blank, o da
`content` se fornito). Se `slug` manca viene generato dal titolo
(univoco per lingua); slug esplicito duplicato -> 400 SLUG_IN_USE.
- **`swerpicommerce-pp-cli pages delete`** - Rimuove record e file contenuto, come dal pannello. Pagine di sistema
-> 400 SYSTEM_PAGE; homepage -> 400 HOMEPAGE_PROTECTED.
- **`swerpicommerce-pp-cli pages get`** - Dettaglio pagina CMS
- **`swerpicommerce-pp-cli pages list`** - Le pagine sono template-driven: il contenuto HTML non e un campo del
modello ma un template Django per-istanza, gestibile via
`/pages/{id}/content`. Le pagine di sistema (negozio, carrello, ...)
renderizzano dai template del tema e via API si gestiscono solo i metadati.
- **`swerpicommerce-pp-cli pages update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.

### payment-methods

Manage payment methods

- **`swerpicommerce-pp-cli payment-methods create`** - `attivo` e' false se non indicato: il metodo non compare al checkout finche' non viene attivato. Se `ordinamento` e' omesso il metodo va in coda. Per `tipo` stripe/paypal, salvando credenziali valide il webhook di conferma pagamento viene registrato in automatico presso il gateway (best-effort: se il gateway non risponde il metodo resta salvato e la registrazione si ritenta al salvataggio successivo).
- **`swerpicommerce-pp-cli payment-methods delete`** - Elimina il metodo e le sue traduzioni. Gli ordini gia' registrati con questo metodo restano, con il riferimento al metodo azzerato.
- **`swerpicommerce-pp-cli payment-methods get`** - Dettaglio metodo di pagamento
- **`swerpicommerce-pp-cli payment-methods list`** - Di default elenca solo i metodi attivi (comportamento storico della v2): per la gestione passare `include_inactive=true`. I segreti (`api_secret`, `webhook_secret`) non sono mai restituiti — al loro posto i booleani `api_secret_set` / `webhook_secret_set`.
- **`swerpicommerce-pp-cli payment-methods update`** - Aggiornamento parziale: valgono solo i campi presenti nel body, campi non riconosciuti -> 400 VALIDATION_ERROR. Se `nomi` e' presente sostituisce integralmente le traduzioni esistenti; se e' assente le lascia intatte.

### price-lists

Manage price lists

- **`swerpicommerce-pp-cli price-lists get`** - Dettaglio listino
- **`swerpicommerce-pp-cli price-lists list`** - Enumera i listini referenziati da `ProductPriceInput.listino_id` e
`CustomerInput.listino_id`. Read-only: i listini si creano dal pannello.

### products

Prodotti e giacenze

- **`swerpicommerce-pp-cli products batch`** - Crea piu prodotti
- **`swerpicommerce-pp-cli products create`** - **Guard anti-duplicato:** se il body ha un `sku` non vuoto e esiste già un
prodotto con lo stesso `sku` nella stessa `lang`, risponde **409
`PRODUCT_DUPLICATE_SKU`** (con l'`id` esistente) invece di creare un
doppione — usa `PUT /products/{id}` per aggiornarlo. Lo stesso `sku` su
lingue diverse è invece consentito (ogni traduzione è un prodotto separato).

**Variazioni prodotto:** prima crea (o assicura) gli attributi e i valori
nel registro dal pannello (`GET /attributes` per enumerarli), poi crea il
padre con `tipo_prodotto: variabile` e infine una variazione per
combinazione con `tipo_prodotto: variante`, `prod_principale_id` del padre
e `valori_attributi` (es. `[{"attributo": "Taglia", "valore": "S"}]`,
risolti contro il registro — match esatto case-sensitive, coppie non
risolvibili -> **400 `VALIDATION_ERROR`**). La variante eredita lo slug
del padre (niente scheda autonoma) e compare nel selettore della scheda
del padre; una combinazione già esistente sullo stesso padre risponde
**409 `PRODUCT_DUPLICATE_VARIANT`**.
- **`swerpicommerce-pp-cli products delete`** - Elimina un prodotto
- **`swerpicommerce-pp-cli products get`** - Oltre ai campi del prodotto restituisce `tab_extra`: i tab aggiuntivi della scheda (risorsa `/extra-tabs`) che coprono questo prodotto, con l'HTML gia' scritto — per i tab `specifico` anche quelli vuoti, cosi' si sa quali `tab_id` compilare con `PUT`.
- **`swerpicommerce-pp-cli products list`** - Di default le variazioni (prodotti con `prod_principale_id`) sono
escluse: `include_variants=true` le include piatte accanto ai padri;
`prod_principale_id=<id>` restituisce SOLO le variazioni di quel padre.

**Paginata: NON è il catalogo completo.** `limit` default **100**; la
risposta porta `meta.total`/`limit`/`offset`. Per enumerare TUTTO itera
con `offset += limit` fino a `offset >= meta.total` (ordinamento sempre
deterministico: `sort` ha `id` come tiebreaker), oppure alza `limit`. **Non dedurre
l'esistenza di un prodotto dalla prima pagina**: prima di crearne uno
cerca per chiave naturale con **`?sku=<sku>`** (ed eventualmente `&lang=`)
— così eviti di creare duplicati per prodotti che sono solo oltre la prima
pagina o sono variazioni escluse di default. In creazione c'è comunque un
guard: `POST /products` con un `sku`+`lang` già presente risponde **409**.

**Polling incrementale**: `modified_after` filtra su `ultima_modifica`,
che si muove su creazione, modifica del prodotto (pannello o
`PUT /products/{id}`) e cambio di disponibilità (esaurito ↔ disponibile).
**Non** si muove per il solo `PUT /products/{id}/stock`: la giacenza
spinta dall'ERP non torna indietro come "prodotto modificato" (e non
sporca il `lastmod` della sitemap). Per riconciliare le giacenze usa la
lista completa o `GET /products/{id}/stock`.

`data_inizio` / `data_fine` delimitano una finestra (inclusiva) sullo
stesso `ultima_modifica`, non su una data di creazione: il prodotto non
ne ha una separata. Sono la versione "a intervallo" di `modified_after`,
utili per gli import a blocchi.
- **`swerpicommerce-pp-cli products update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.
Se `quantita` passa da 0 a un valore positivo, chi si e' iscritto alla lista
d'attesa del prodotto ("Avvisami quando torna disponibile") riceve la mail
"Prodotto di nuovo disponibile" (messaggio email tipo 18, configurabile nel pannello).
Con `tab_extra` si scrive il contenuto di questo prodotto per i tab extra
di tipo `specifico` (vedi `/extra-tabs`): upsert per `tab_id`, HTML vuoto
toglie il tab dalla vetrina del prodotto.

### quantity-discounts

Sconti quantità: regole a scaglioni che abbassano il prezzo unitario al superare di una soglia di pezzi. La quantità si conta sulla singola riga di carrello e ogni variante fa scaglione per conto proprio; il prezzo così ottenuto è quello che il checkout ricalcola e fa pagare.

- **`swerpicommerce-pp-cli quantity-discounts create`** - Serve almeno uno scaglione. Gli id di prodotti, categorie, listini, clienti e liste devono esistere, altrimenti 400 con il codice della risorsa mancante.
- **`swerpicommerce-pp-cli quantity-discounts delete`** - Gli ordini già chiusi conservano i prezzi che hanno pagato.
- **`swerpicommerce-pp-cli quantity-discounts get`** - Dettaglio regola di sconto quantità
- **`swerpicommerce-pp-cli quantity-discounts list`** - Lista regole di sconto quantità
- **`swerpicommerce-pp-cli quantity-discounts update`** - Update parziale sui campi semplici. Le liste (scaglioni, prodotti, categorie, listini, clienti, liste) si riscrivono per intero quando sono presenti nel body: inviare `"scaglioni": [...]` sostituisce tutti gli scaglioni, ometterlo li lascia invariati.

### redirects

Regole di redirect 301/302 (pannello Impostazioni -> Redirect). Ogni mutazione rigenera la configurazione nginx e la ricarica, quindi le regole sono attive subito. `origine` path (es. `/vecchio-url/`) agisce sul dominio del sito; un URL assoluto crea un blocco server per quel dominio esterno.

- **`swerpicommerce-pp-cli redirects create`** - La regola e' attiva subito (rigenera e ricarica nginx). Per import massivi inviare le richieste in sequenza, non in parallelo.
- **`swerpicommerce-pp-cli redirects delete`** - Elimina una regola di redirect
- **`swerpicommerce-pp-cli redirects get`** - Dettaglio regola di redirect
- **`swerpicommerce-pp-cli redirects list`** - In `meta.nginx_local_include_attivo` la lista espone la diagnostica del motore: `true` = la conf nginx dell'istanza include i redirect locali (le regole sono davvero attive), `false` = include mancante (le regole si salvano ma restano inerti: serve l'update dell'istanza, che la aggancia automaticamente), `null` = conf non leggibile.
- **`swerpicommerce-pp-cli redirects update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.

### review-requests

Manage review requests

- **`swerpicommerce-pp-cli review-requests list`** - Un invito per ordine completato: `in_attesa` (parte a `data_prevista`), `inviata`, `recensito` (il cliente ha lasciato almeno una recensione), `annullata` (ordine tornato indietro o annullato dal pannello), `errore` (SMTP fallito, si ritenta fino a 3 volte).

### reviews

Recensioni prodotto con acquisto verificato (pannello Marketing & SEO -> Recensioni). Le scrivono i clienti dall'area account, solo per prodotti di ordini completati e una per prodotto; nascono `da_approvare` (salvo approvazione automatica) e all'approvazione parte il premio configurato (punti o coupon), una sola volta. Via API si leggono, si moderano e si eliminano; `/review-requests` e' la coda degli inviti via email (uno per ordine completato). I prodotti espongono `rating` (media e conteggio delle recensioni approvate).

- **`swerpicommerce-pp-cli reviews delete`** - Il cliente potra' recensire di nuovo il prodotto; un premio gia' erogato non viene stornato.
- **`swerpicommerce-pp-cli reviews get`** - Dettaglio recensione
- **`swerpicommerce-pp-cli reviews list`** - In `meta.recensioni_attive` se il modulo e' acceso nel pannello.
- **`swerpicommerce-pp-cli reviews update`** - `stato: approvata` pubblica la recensione, aggiorna il rating del prodotto ed eroga il premio (se configurato e non gia' dato); `rifiutata` la toglie dalla vetrina; `da_approvare` la rimette in coda. Il testo non si modifica via API: e' del cliente.

### shipping-methods

Manage shipping methods

- **`swerpicommerce-pp-cli shipping-methods create`** - `attivo` e' false se non indicato: il metodo non compare al checkout finche' non viene attivato. Attenzione al significato di `costo`, che dipende da `tipo`.
- **`swerpicommerce-pp-cli shipping-methods delete`** - Elimina il metodo e le sue traduzioni. Gli ordini gia' registrati con questo metodo restano, con il riferimento al metodo azzerato.
- **`swerpicommerce-pp-cli shipping-methods get`** - Dettaglio metodo di spedizione
- **`swerpicommerce-pp-cli shipping-methods list`** - Di default elenca tutti i metodi, attivi e non (comportamento storico della v2): passare `include_inactive=false` per i soli attivi.
- **`swerpicommerce-pp-cli shipping-methods update`** - Aggiornamento parziale: valgono solo i campi presenti nel body, campi non riconosciuti -> 400 VALIDATION_ERROR. Se `nomi` e' presente sostituisce integralmente le traduzioni esistenti; se e' assente le lascia intatte.

### site-info

Manage site info

- **`swerpicommerce-pp-cli site-info site_info`** - Il "chi sono" dell'istanza: **chiamalo per PRIMO**, prima di progettare
pagine, menu, template o contenuti. Oltre all'anagrafica, ritorna:

- `tipo_sito` — che sito stai costruendo:
  - `istituzionale`: vetrina aziendale, nessuna vendita online. Pagine
    di presentazione (chi siamo, servizi, contatti, ...), niente
    negozio/carrello/account.
  - `ecommerce`: negozio online. Esistono le pagine di sistema negozio,
    carrello, pagamento, account; header con minicart; prodotti via
    `/products`.
  - `concessionaria`: sito di veicoli. Esistono parco-auto e
    auto-singola; l'inventario sono i veicoli (se anche
    `moduli.ecommerce` è true, il sito vende pure online).
- `moduli` — il dettaglio: `ecommerce`, `concessionaria`, `blog`, `crm`, `recensioni`.
  Il **blog è trasversale**: se `moduli.blog` è true va curato per
  qualunque `tipo_sito` (articoli via `/articles`, pagina `/blog/`).

I dati `DatiAzienda` (ragione sociale, P.IVA, indirizzo, contatti, REA,
nome e URL sito) sono mostrati nei footer del tema. Read-only (la
modifica resta nel pannello). Gli stessi valori sono anche variabili di
contesto globali nei template (`{{ dati_azienda.<campo> }}`), quindi i
footer si aggiornano da soli.

### swerpicommerce-auth

Manage swerpicommerce auth

- **`swerpicommerce-pp-cli swerpicommerce-auth me`** - Endpoint senza effetti collaterali per validare un Bearer Token: restituisce
la chiave associata, la scadenza e i permessi concessi. Utile per i `doctor`
dei client e per scoprire i permessi disponibili senza tentare chiamate.
- **`swerpicommerce-pp-cli swerpicommerce-auth token`** - Riceve `api_id` e `api_secret` e restituisce un Bearer Token senza scadenza.
I token emessi da questo endpoint funzionano anche sulla API v1.
- **`swerpicommerce-pp-cli swerpicommerce-auth token-revoke`** - Effetto immediato. Lo scoping e per chiave: i token delle altre chiavi
non sono visibili ne revocabili (404). Si puo revocare anche il token
in uso (`was_current: true` nella risposta).
- **`swerpicommerce-pp-cli swerpicommerce-auth tokens-list`** - Metadati dei token della chiave del chiamante (client, IP, creazione,
ultimo uso, `current` per quello in uso). Il valore del token non
viene mai riesposto dopo l'emissione. I token non scadono: questa
lista, con la revoca, e lo strumento per governarli.

### update

Stato/esito dell'ultimo aggiornamento dell'istanza, leggibile dal sito live anche dopo il riavvio dell'update agent (es. per capire perche' un update e' stato annullato dal gate).

- **`swerpicommerce-pp-cli update status`** - `last` = esito persistito dell'ultimo update (sopravvive al riavvio
dell'agent): `state` (`running`/`success`/`error`/`blocked`), `error`
(motivo, es. gate coi commit non pushati), `steps` recenti, timestamp.
`live` = stato in tempo reale dell'agent se raggiungibile, altrimenti
`null` (agent in riavvio).

### vat-groups

Manage vat groups

- **`swerpicommerce-pp-cli vat-groups list`** - I gruppi di nazioni che `VatRate.valori[].codice_nazione` accetta al
posto di un ISO. L'ordine della risposta è la priorità di risoluzione:
vince il primo gruppo che contiene la nazione (`@UE` prima dei
continenti, così uno stato membro non finisce mai in una regola
geografica). Non esiste un gruppo "Europa": i paesi europei extra-UE
(CH, GB, NO, TR…) vanno per nazione o al wildcard `*`. `@UE` è il
territorio IVA: 27 stati membri + Monaco; Åland, DOM francesi,
Groenlandia, Fær Øer, Isola di Man restano fuori pur avendo un ISO.

### vat-rates

Manage vat rates

- **`swerpicommerce-pp-cli vat-rates get`** - Dettaglio aliquota IVA
- **`swerpicommerce-pp-cli vat-rates list`** - Enumera le aliquote referenziate da `ProductInput.iva_id`.
`valore_default` è la percentuale applicata quando la nazione del
cliente non è nota; `percentuale` è il valore con
`codice_nazione: '*'`, usato per le nazioni note senza una riga
dedicata; `valori` riporta le aliquote per nazione.

**Quale indirizzo risolve `codice_nazione`**: quello di
**spedizione**. L'aliquota segue la nazione di consegna
(`OrderInput.nazione_spedizione` nel checkout, `dati_form.nazione`);
`nazione_fatturazione` non la sposta mai. `codice_nazione` accetta
anche un gruppo fiscale con prefisso `@` (`@UE` e i continenti) e il
wildcard `*`, cercati in quest'ordine: nazione, gruppo, wildcard.

Sopra all'aliquota c'è il **regime** dell'operazione, che decide se
l'imposta è dovuta: vedi `OrderHeader.regime_iva` e
`POST /vat-validations`.

Non riguarda gli ordini: in `OrderProductInput.iva` si passa
direttamente la percentuale, non un id.

### vat-rules

Manage vat rules

- **`swerpicommerce-pp-cli vat-rules get`** - Configurazione, riga unica, di ciò che decide **se** l'imposta è
dovuta — le aliquote (`GET /vat-rates`) dicono solo **quanta**. È
quella che il checkout usa per assegnare `OrderHeader.regime_iva`
e che `POST /vat-validations` applica. Con `attive=false` non esiste
nessun regime: valgono le sole aliquote per nazione.
- **`swerpicommerce-pp-cli vat-rules update`** - I campi omessi restano invariati. Stesse regole del pannello:
`nazione_azienda` normalizzata a 2 lettere maiuscole;
`reverse_charge_attivo` richiede `vies_attivo`, altrimenti viene
salvato `false` (senza verifica sarebbe un'esenzione a chi digita un
numero qualsiasi). Il `vies_operativo` restituito è `attive AND
vies_attivo`.

### vat-validations

Manage vat validations

- **`swerpicommerce-pp-cli vat-validations create`** - Interroga il servizio VIES della Commissione europea e dice se
l'operazione è imponibile.

Il `numero_consultazione` (`requestIdentifier`) è **l'unica prova
documentale opponibile** in caso di verifica fiscale: va archiviato per
**operazione**, non per cliente — le partite IVA vengono cessate e
quello che conta è lo stato alla data della cessione. Viene rilasciato
solo se la partita IVA del venditore configurata in Dati azienda è
comunitaria e valida.

`regime_iva` risponde alla domanda pratica: con questa partita IVA e
questa destinazione, si fattura con o senza imposta. Richiede
`nazione_spedizione` — è la **consegna** a spostare l'imposta, non la
fatturazione: una partita IVA tedesca valida con consegna in Italia
resta imponibile.

Se il servizio non risponde l'esito è `non_disponibile`: mai `valido`.
Il regime segue in quel caso il fallback configurato nel pannello
(default: applica l'IVA).

### webhooks

Registrazione degli endpoint a cui il sito invia gli eventi, con il relativo secret e il log delle consegne. Il payload e l'envelope di ogni evento sono descritti nello schema dedicato, `GET /api/v2/webhook/openapi`.

- **`swerpicommerce-pp-cli webhooks create`** - `secret` è opzionale: se omesso ne viene generato uno e restituito nella
risposta (resta comunque leggibile dalle GET successive).
- **`swerpicommerce-pp-cli webhooks delete`** - Elimina anche il log delle consegne collegate.
- **`swerpicommerce-pp-cli webhooks get`** - Dettaglio webhook
- **`swerpicommerce-pp-cli webhooks list`** - Include il `secret` di ogni webhook: è il valore che arriva nell'header
`X-Webhook-Secret` di ogni consegna e che il consumer deve confrontare.
- **`swerpicommerce-pp-cli webhooks update`** - Aggiorna un webhook

### well-known

File serviti sotto `/.well-known/` del sito (pannello Impostazioni -> File .well-known). Servono alle verifiche di proprieta' del dominio richieste dai provider esterni: Apple Pay via Stripe, altri gateway di pagamento, `security.txt`. Ogni file risponde 200 sul path esatto e senza redirect, condizione che Apple impone per validare il dominio.

- **`swerpicommerce-pp-cli well-known create`** - Il file e' servito subito su `/.well-known/<nome>`. Il nome deve essere identico a quello indicato dal provider (per Apple Pay: `apple-developer-merchantid-domain-association`, senza estensione). Se il nome esiste gia' la risposta e' 409: aggiornarlo con PUT.
- **`swerpicommerce-pp-cli well-known delete`** - La verifica del dominio presso il provider smette di funzionare: Apple ricontrolla il file periodicamente.
- **`swerpicommerce-pp-cli well-known get`** - Dettaglio di un file .well-known
- **`swerpicommerce-pp-cli well-known list`** - Lista dei file .well-known
- **`swerpicommerce-pp-cli well-known update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.


## Output Formats

```bash
# Human-readable table (default in terminal, JSON when piped)
swerpicommerce-pp-cli article-categories list

# JSON for scripting and agents
swerpicommerce-pp-cli article-categories list --json

# Filter to specific fields
swerpicommerce-pp-cli article-categories list --json --select id,name,status

# Dry run — show the request without sending
swerpicommerce-pp-cli article-categories list --dry-run

# Agent mode — JSON + compact + no prompts in one flag
swerpicommerce-pp-cli article-categories list --agent
```

## Agent Usage

This CLI is designed for AI agent consumption:

- **Non-interactive** - never prompts, every input is a flag
- **Pipeable** - `--json` output to stdout, errors to stderr
- **Filterable** - `--select id,name` returns only fields you need
- **Previewable** - `--dry-run` shows the request without sending
- **Explicit retries** - add `--idempotent` to create retries and `--ignore-missing` to delete retries when a no-op success is acceptable
- **Confirmable** - `--yes` for explicit confirmation of destructive actions
- **Piped input** - write commands can accept structured input when their help lists `--stdin`
- **Offline-friendly** - sync/search commands can use the local SQLite store when available
- **Agent-safe by default** - no colors or formatting unless `--human-friendly` is set

Exit codes: `0` success, `2` usage error, `3` not found, `4` auth error, `5` API error, `7` rate limited, `10` config error.

## Use with Claude Code

Install the focused skill — it auto-installs the CLI on first invocation:

```bash
npx skills add mvanhorn/printing-press-library/cli-skills/pp-swerpicommerce -g
```

Then invoke `/pp-swerpicommerce <query>` in Claude Code. The skill is the most efficient path — Claude Code drives the CLI directly without an MCP server in the middle.

<details>
<summary>Use as an MCP server in Claude Code (advanced)</summary>

If you'd rather register this CLI as an MCP server in Claude Code, install the MCP binary first:


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Then register it:

```bash
claude mcp add swerpicommerce swerpicommerce-pp-mcp -e SWERPICOMMERCE_BEARER_AUTH=<your-token>
```

</details>

## Use with Claude Desktop

This CLI ships an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle — Claude Desktop's standard format for one-click MCP extension installs (no JSON config required).

To install:

1. Download the `.mcpb` for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/swerpicommerce-current).
2. Double-click the `.mcpb` file. Claude Desktop opens and walks you through the install.
3. Fill in `SWERPICOMMERCE_BEARER_AUTH` when Claude Desktop prompts you.

Requires Claude Desktop 1.0.0 or later. Pre-built bundles ship for macOS Apple Silicon (`darwin-arm64`) and Windows (`amd64`, `arm64`); for other platforms, use the manual config below.

<details>
<summary>Manual JSON config (advanced)</summary>

If you can't use the MCPB bundle (older Claude Desktop, unsupported platform), install the MCP binary and configure it manually.


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "swerpicommerce": {
      "command": "swerpicommerce-pp-mcp",
      "env": {
        "SWERPICOMMERCE_BEARER_AUTH": "<your-key>"
      }
    }
  }
}
```

</details>

## Health Check

```bash
swerpicommerce-pp-cli doctor
```

Verifies configuration, credentials, and connectivity to the API.

## Configuration

Config file: `~/.config/swerpicommerce-pp-cli/config.toml`

Static request headers can be configured under `headers`; per-command header overrides take precedence.

Environment variables:

| Name | Kind | Required | Description |
| --- | --- | --- | --- |
| `SWERPICOMMERCE_BEARER_AUTH` | per_call | Yes | Set to your API credential. |

## Troubleshooting
**Authentication errors (exit code 4)**
- Run `swerpicommerce-pp-cli doctor` to check credentials
- Verify the environment variable is set: `echo $SWERPICOMMERCE_BEARER_AUTH`
**Not found errors (exit code 3)**
- Check the resource ID is correct
- Run the `list` command to see available items

---

Generated by [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)
