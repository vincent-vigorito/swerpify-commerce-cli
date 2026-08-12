# Changelog

Tutte le modifiche rilevanti a questo repo. Formato
[Keep a Changelog](https://keepachangelog.com/it/1.1.0/), versionamento
[SemVer](https://semver.org/lang/it/).

> Nota: la versione qui sotto è quella del **repo** (CLI + wrapper + skill). Il bundle MCP
> (`generated/swerpicommerce-cli/manifest.json`) ha un suo numero, ereditato dal generatore
> (attuale **4.6.1**), che non segue questo changelog.

## [1.4.0] - 2026-08-11

Sei rigenerazioni del CLI da luglio a oggi (da 129 a **183 operazioni su 103 path**), più
l'evoluzione della skill operativa e del report issue. Raggruppate qui perché nessuna era
stata registrata singolarmente.

### ⚠️ Modifiche al comportamento (chi usa il CLI le noterà)

- **Variazioni prodotto — si creano di nuovo via API** (rigen 11/08, fix della issue B60).
  `tipo_prodotto` ha il nuovo valore **`variante`** e `valori_attributi` viene **risolto
  contro il registro attributi** (`GET /attributes`) con match esatto *case-sensitive*:
  una coppia non risolvibile ora dà **400** con l'elenco dei valori ammessi, invece di
  essere salvata come testo inerte.
  - Padre `variabile` + figlie `variante` (con `prod_principale_id`); le figlie nascono
    con lo **slug del padre** → nessuna pagina autonoma duplicata.
  - `valori_attributi` **sostituisce integralmente** il set: negli update parziali va
    omesso, altrimenti si perde il collegamento.
  - ⚠️ Il padre **deve avere un prezzo di listino**, altrimenti la sua scheda risponde 500
    (residuo noto, tracciato in B60).
  - Sugli altri tipi di prodotto gli stessi `valori_attributi` sono **descrittivi** e
    alimentano i filtri di categoria.
- **Validazione strict ovunque** (issue B9, verificata l'11/08): un campo non previsto nel
  body dà **400 VALIDATION_ERROR**. Prima veniva ignorato in silenzio con un 200.
- **`pages update` non accetta `content`**: record e contenuto viaggiano su endpoint
  separati (`pages content page-update`).
- **`MediaFolder` da enum a pattern** (rigen 30/07): le cartelle delle custom app
  (`<app>.<tipo>`) non vengono più bloccate dalla validazione client-side.

### Aggiunto — nuove aree API

- **Webhook** (rigen 05/08): CRUD `/webhooks` con eventi `order.created`, `order.updated`,
  `form.submitted`, `cart.abandoned`, secret opzionale e log delle consegne
  (`/webhooks/{id}/deliveries`).
- **CRUD checkout** (rigen 05/08): metodi di **spedizione** e **pagamento** ora creabili e
  modificabili (prima sola lettura), con nomi multilingua e credenziali gateway; in lettura
  anche **listini** (`/price-lists`) e **aliquote IVA** (`/vat-rates`).
- **Filtri di sincronizzazione** (rigen 05/08) su `customers`/`orders`/`products`:
  `data_inizio`/`data_fine`, **`ModifiedAfter`**, `sort` (+ `stato` sugli ordini) e
  risposte tipizzate; `include_inactive` sui metodi di checkout.
- **Well-known** (rigen 04/08): CRUD `/well-known` per servire file su `/.well-known/<nome>`
  — caso d'uso principale la verifica dominio **Apple Pay**.
- **Fork del tenant** (rigen 22/07): ispezione e ripristino (`fork log/file-get/diff/restore`)
  + `site-info` con `tipo_sito` e `moduli`.
- **Redirect 301/302** (rigen 16/07): risorsa `/redirects` — motore di redirect gestito,
  utile alle migrazioni. ⚠️ Le mutazioni rigenerano la conf nginx: inviarle **in sequenza**,
  mai in parallelo.
- **Form**: `iubenda_mapping` per la Consent Database e destinatari multipli separati da
  virgola; componente `sw-gallery` con lightbox.
- **Loghi del tema**: `GET/PUT /design/logos` (slot logo/favicon/email).

### Cambiato

- **Skill `swerpicommerce-ops`** allineata a ogni rigenerazione: ricetta corretta delle
  variazioni prodotto, obbligo del prefisso CDN **`{{ STATIC_WEB_URL }}`** su ogni asset,
  convenzioni per i link `<a>` (underline, `_blank` solo esterni, `rel` per la SEO),
  sezione custom app Django e contratto `<sw-select>`.
- **Cancelli di conformità**: `scripts/check_page.py` (statico) e `scripts/a11y_audit.js`
  (renderizzato) — nessuna pagina si considera pubblicabile senza. Il checker passa sempre
  `--no-cache` (la response cache restava stale dopo scritture esterne).
- **Report issue** (`SWERPICOMMERCE-ISSUES.md`): da 49 a **61 voci**, con retest completo
  dell'11/08 che ne ha chiuse 10 in un giro (B9, B23, B25, B33, B36, B41, B42, B44, B49,
  B53). Aperte al momento: 13.

### Sicurezza

- La procedura di neutralizzazione dello schema rimuove sempre **`x-api-id`** (l'export dal
  pannello incorpora l'ID reale della chiave che l'ha generato): gli export grezzi non vanno
  mai committati.

### Note per chi rigenera

- I **4 path `custom-apps`** compaiono solo negli export dal pannello: rigenerando dallo
  schema pubblico vanno innestati dal neutral precedente.
- Bug noto dell'exporter (issue B59): una description contenente una virgola non quotata
  viene spezzata in una **chiave JSON spuria con valore `null`** → va corretta a mano nel
  neutral a ogni export.

## [1.3.1] - 2026-07-02
### Sicurezza
- **Rimosso `x-api-id`** (identificativo della chiave API reale, incorporato dall'export
  del pannello) dallo schema neutro e da `spec.json`. Solo l'ID era esposto (non il
  secret); il repo è privato. La procedura di neutralizzazione ora lo elimina sempre.
- `swc`: il token viene scritto con `umask 077` (nessuna finestra con permessi larghi).

### Corretto
- `swc`: **stdout e stderr non vengono più fusi** — il JSON in stdout resta puro per
  `swc … --agent | jq`; gli errori vanno su stderr; exit code preservato. Il retry
  automatico su 401 ora ispeziona entrambi gli stream (verificato end-to-end).
- `swc`: il body di `POST /auth/token` è costruito da python con escaping JSON corretto
  (credenziali con caratteri speciali non rompono più la richiesta).

## [1.3.0] - 2026-07-02
### Aggiunto
- CLI **rigenerato** dallo schema aggiornato: da 127 a **129 endpoint**. Nuova risorsa
  **`header-footer`** (`header-footer list` → `GET /header-footer`; `header-footer set`
  → `PUT /header-footer/{lang}`) per gestire via API i record `Header_Footer` per lingua —
  **fix "alla radice"** del caso "le pagine di una lingua cadono sull'header della lingua
  default" (imposta i partial header/footer per lingua a livello globale).

### Modificato
- Schema neutro `swerpicommerce-v2-openapi-neutral.json` aggiornato a **129 methods**.
- Ripetuti i due passi manuali post-regen: ri-pin `toolchain go1.26.4` in `go.mod`,
  ri-patch `manifest.json` (`swerpicommerce_base_url` → env `SWERPICOMMERCE_BASE_URL`).

## [1.2.0] - 2026-07-01
### Aggiunto
- **Gestione multi-sito** (`sites/`) tramite il wrapper [`swc`](sites/swc): ogni sito è una
  sottocartella con un solo `credentials.env` (`api_id`/`api_secret`/`base_url`). Il wrapper
  rileva il sito dalla cartella corrente (o `--site`), rigenera/riusa il **token Bearer**
  (cache `.token.json`, TTL 20 min, **auto-refresh su 401**) e passa tutto al CLI via env —
  senza toccare il binario generato. Aggiungere un sito = creare una cartella + `.env`.
- Template `sites/_template/credentials.env.example` e `sites/README.md`.
- Flag del wrapper: `swc --which` (sito/base_url attivi), `swc --refresh`, `swc --site <n>`.

### Sicurezza
- `sites/.gitignore` a **whitelist**: ignora tutto per default e sblocca solo i file
  "codice" (`swc`, `README.md`, `_template/`). Le cartelle-sito con `credentials.env` e
  `.token.json` non entrano **mai** nel repo. Verificato con un `git add` reale.

## [1.1.0] - 2026-07-01
### Modificato
- CLI **rigenerato** dallo schema v2 definitivo: da 99 a **127 endpoint** (nuove risorse
  API coperte). Schema neutro aggiornato (`swerpicommerce-v2-openapi-neutral.json`).
- Ri-pin del `toolchain go1.26.4` in `go.mod` e ri-patch di `manifest.json`
  (`swerpicommerce_base_url` → env `SWERPICOMMERCE_BASE_URL`), i due passi manuali post-regen.

## [1.0.0] - 2026-06-14
### Aggiunto
- Primo rilascio del repo dedicato `swerpify-commerce-cli`: **CLI Go** (99 operazioni),
  **server MCP** + bundle `.mcpb`, **skill** `swerpicommerce-ops` per agenti, schema OpenAPI
  v2 neutralizzato. Generato da OpenAPI con CLI Printing Press.
- README con guida di installazione da GitHub; `.gitignore` dedicato (ignora `bin/`, `*.mcpb`).
