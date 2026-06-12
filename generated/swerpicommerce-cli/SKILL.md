---
name: pp-swerpicommerce
description: "Printing Press CLI for Swerpicommerce. REST API v2 schema-first per la gestione di ordini, clienti, prodotti, pagine CMS e configurazioni e-commerce. Tutti..."
author: "user"
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

**Guida completa** (architettura, esempi, errori tipici):
`GET /design/swcss-guide` (markdown).

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

**customers** — Clienti e punti fedeltà

- `swerpicommerce-pp-cli customers batch` — Crea piu clienti
- `swerpicommerce-pp-cli customers create` — Crea un cliente
- `swerpicommerce-pp-cli customers delete` — Elimina cliente, account di login e indirizzi di spedizione. Se il cliente ha ordini risponde 409: ripetere con...
- `swerpicommerce-pp-cli customers get` — Cliente con email dell'account e indirizzi di spedizione.
- `swerpicommerce-pp-cli customers list` — Lista clienti
- `swerpicommerce-pp-cli customers update` — Aggiorna i campi indicati. `email` e `password` agiscono sull'account di login collegato (l'email deve restare...

**design** — Sorgenti SWCSS del tema e compilazione bundle. Per comporre pagine via API: vedi la guida rapida nella descrizione dello schema (in alto) e la guida completa su `GET /design/swcss-guide`. Dopo ogni modifica a contenuti o CSS serve `POST /design/compile` perché vada live.

- `swerpicommerce-pp-cli design compile` — Rigenera i bundle statici (stessa compilazione del pannello Grafica) con tree-shaking sulle classi usate nei...
- `swerpicommerce-pp-cli design css-delete` — Rifiutato (400 DEFAULT_CSS_FILE) sui file del set predefinito della sezione: il ripristino default li ricreerebbe...
- `swerpicommerce-pp-cli design css-get` — Legge un sorgente CSS
- `swerpicommerce-pp-cli design css-list` — File CSS delle sezioni `pagine-sistema/*` (stesse del pannello Grafica) e del layer globale `custom`. Il layer...
- `swerpicommerce-pp-cli design css-put` — Sovrascrive l'intero file (201 se creato). Le modifiche NON vanno live finché non si esegue `POST /design/compile`....
- `swerpicommerce-pp-cli design guide` — Markdown operativo: architettura dei layer, regole del design system, flusso pagina+CSS+compilazione, utility...
- `swerpicommerce-pp-cli design js-delete` — Elimina un file JS per-pagina
- `swerpicommerce-pp-cli design js-get` — Legge un file JS per-pagina
- `swerpicommerce-pp-cli design js-list` — JS per-istanza in `/static/js/custom/`: il file `<slug>.js` (o `<slug>_<lang>.js` per le lingue non predefinite)...
- `swerpicommerce-pp-cli design js-put` — Sovrascrive l'intero file (201 se creato) e va live subito — niente compilazione, il cache-buster è sull'mtime....

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

**media** — Libreria media globale (immagini di prodotti, categorie e blog)

- `swerpicommerce-pp-cli media delete` — Rimuove il file dallo storage e azzera i riferimenti diretti nel database (record FotoProdotto per product_images;...
- `swerpicommerce-pp-cli media get` — Dettaglio di un file della libreria
- `swerpicommerce-pp-cli media list` — File immagine delle cartelle gestite (foto prodotto, immagini categorie prodotto, articoli blog, categorie blog), i...
- `swerpicommerce-pp-cli media update` — `alt` viene salvato in libreria e propagato agli usi correnti del file (foto prodotto, `immagine_alt` delle...
- `swerpicommerce-pp-cli media upload` — Contenuto base64 nel body JSON (max 10 MB decodificati; estensioni jpg/jpeg/png/webp/gif/avif). In caso di nome file...

**orders** — Ordini

- `swerpicommerce-pp-cli orders batch` — Crea piu ordini
- `swerpicommerce-pp-cli orders create` — Crea un ordine
- `swerpicommerce-pp-cli orders get` — Dettaglio ordine
- `swerpicommerce-pp-cli orders list` — Lista ordini
- `swerpicommerce-pp-cli orders update` — Aggiorna i campi indicati dell'ordine. L'annullamento e un update di stato: `{'stato': 'annullato'}`. Gli ordini non...

**page-templates** — Manage page templates

- `swerpicommerce-pp-cli page-templates` — `presets` = template di partenza per le pagine nuove; `pagine_sistema` = mappa tipo -> file template delle pagine di...

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
- `swerpicommerce-pp-cli products create` — Crea un prodotto
- `swerpicommerce-pp-cli products delete` — Elimina un prodotto
- `swerpicommerce-pp-cli products get` — Dettaglio prodotto
- `swerpicommerce-pp-cli products list` — Di default le variazioni (prodotti con `prod_principale_id`) sono escluse: `include_variants=true` le include piatte...
- `swerpicommerce-pp-cli products update` — Campi non riconosciuti -> 400 VALIDATION_ERROR.

**shipping-methods** — Manage shipping methods

- `swerpicommerce-pp-cli shipping-methods` — Lista metodi di spedizione

**swerpicommerce-auth** — Manage swerpicommerce auth

- `swerpicommerce-pp-cli swerpicommerce-auth me` — Endpoint senza effetti collaterali per validare un Bearer Token: restituisce la chiave associata, la scadenza e i...
- `swerpicommerce-pp-cli swerpicommerce-auth token` — Riceve `api_id` e `api_secret` e restituisce un Bearer Token senza scadenza. I token emessi da questo endpoint...
- `swerpicommerce-pp-cli swerpicommerce-auth token-revoke` — Effetto immediato. Lo scoping e per chiave: i token delle altre chiavi non sono visibili ne revocabili (404). Si puo...
- `swerpicommerce-pp-cli swerpicommerce-auth tokens-list` — Metadati dei token della chiave del chiamante (client, IP, creazione, ultimo uso, `current` per quello in uso). Il...


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
