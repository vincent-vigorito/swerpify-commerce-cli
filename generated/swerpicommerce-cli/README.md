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

- **`swerpicommerce-pp-cli articles create`** - Se `slug` manca viene generato dal titolo (univoco per lingua).
- **`swerpicommerce-pp-cli articles delete`** - Elimina un articolo
- **`swerpicommerce-pp-cli articles get`** - Dettaglio articolo
- **`swerpicommerce-pp-cli articles list`** - Lista articoli blog
- **`swerpicommerce-pp-cli articles update`** - Aggiorna un articolo

### attributes

Manage attributes

- **`swerpicommerce-pp-cli attributes get`** - Dettaglio attributo con i suoi valori
- **`swerpicommerce-pp-cli attributes list`** - Definizioni di attributi e valori gestite dal pannello (es. Taglia:
S/M/L). Le variazioni prodotto via API usano `valori_attributi` con
testo libero: questo registro è il riferimento per usare nomi e
valori coerenti ed evitare divergenze tipo "Rosso"/"rosso".

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

### customers

Clienti e punti fedeltà

- **`swerpicommerce-pp-cli customers batch`** - Crea piu clienti
- **`swerpicommerce-pp-cli customers create`** - Crea un cliente
- **`swerpicommerce-pp-cli customers delete`** - Elimina cliente, account di login e indirizzi di spedizione. Se il cliente
ha ordini risponde 409: ripetere con `?force=true` per eliminarlo comunque
(gli ordini restano, scollegati dal cliente).
- **`swerpicommerce-pp-cli customers get`** - Cliente con email dell'account e indirizzi di spedizione.
- **`swerpicommerce-pp-cli customers list`** - Lista clienti
- **`swerpicommerce-pp-cli customers update`** - Aggiorna i campi indicati. `email` e `password` agiscono sull'account di
login collegato (l'email deve restare univoca). Campi non riconosciuti
-> 400 VALIDATION_ERROR.

### design

Sorgenti SWCSS del tema e compilazione bundle. Per comporre pagine via API: vedi la guida rapida nella descrizione dello schema (in alto) e la guida completa su `GET /design/swcss-guide`. Dopo ogni modifica a contenuti o CSS serve `POST /design/compile` perché vada live.

- **`swerpicommerce-pp-cli design compile`** - Rigenera i bundle statici (stessa compilazione del pannello Grafica)
con tree-shaking sulle classi usate nei template: va eseguita dopo
ogni modifica a contenuti pagina o sorgenti CSS perché le modifiche
vadano live. Operazione sincrona (alcuni secondi).
- **`swerpicommerce-pp-cli design css-delete`** - Rifiutato (400 DEFAULT_CSS_FILE) sui file del set predefinito della
sezione: il ripristino default li ricreerebbe — svuotali invece.
- **`swerpicommerce-pp-cli design css-get`** - Legge un sorgente CSS
- **`swerpicommerce-pp-cli design css-list`** - File CSS delle sezioni `pagine-sistema/*` (stesse del pannello
Grafica) e del layer globale `custom`. Il layer `base/` (variabili,
reset, utility) non è esposto: è il framework e non si modifica.
`predefinito: true` = fa parte del set base della sezione (il
ripristino default lo sovrascrive).
- **`swerpicommerce-pp-cli design css-put`** - Sovrascrive l'intero file (201 se creato). Le modifiche NON vanno
live finché non si esegue `POST /design/compile`. Convenzioni: un
file per pagina/componente, classi prefissate `sw-*`, variabili e
breakpoint del sistema — vedi `GET /design/swcss-guide`.
- **`swerpicommerce-pp-cli design guide`** - Markdown operativo: architettura dei layer, regole del design system,
flusso pagina+CSS+compilazione, utility disponibili, errori tipici.
Da leggere PRIMA di scrivere contenuti o CSS.
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

### media

Libreria media globale (immagini di prodotti, categorie e blog)

- **`swerpicommerce-pp-cli media delete`** - Rimuove il file dallo storage e azzera i riferimenti diretti nel
database (record FotoProdotto per product_images; campi `immagine` /
`immagine_evidenza` per le altre cartelle). I riferimenti dentro
l'HTML dei contenuti (articoli, pagine) non vengono toccati.
- **`swerpicommerce-pp-cli media get`** - Dettaglio di un file della libreria
- **`swerpicommerce-pp-cli media list`** - File immagine delle cartelle gestite (foto prodotto, immagini categorie
prodotto, articoli blog, categorie blog), i più recenti per primi.
Ogni file include `alt` (testo alternativo della libreria, gestibile
via PUT) e `valore_campo`, il valore pronto da scrivere nel campo
collegato della risorsa: `immagine` della categoria (cat_images),
`immagine_evidenza` dell'articolo (blog), `immagine` della categoria
blog (blog_cat_images). Per le foto prodotto (`product_images`,
valore_campo null) l'associazione passa da /products/{id}/images,
che con `source: {folder, nome}` copia un file della libreria.
- **`swerpicommerce-pp-cli media update`** - `alt` viene salvato in libreria e propagato agli usi correnti del file
(foto prodotto, `immagine_alt` delle categorie). `nome` rinomina il
file nello storage (stessa estensione) aggiornando i riferimenti
diretti nel database: dopo la rinomina fa fede `nome` nella risposta.
- **`swerpicommerce-pp-cli media upload`** - Contenuto base64 nel body JSON (max 10 MB decodificati; estensioni
jpg/jpeg/png/webp/gif/avif). In caso di nome file già esistente lo
storage lo rinomina: fa fede `nome` nella risposta. L'upload non
collega il file a nessuna risorsa: scrivere `valore_campo` nel campo
della risorsa di destinazione (es. PUT /categories/{id} con
`immagine`). Le foto prodotto si caricano da /products/{id}/images.

### orders

Ordini

- **`swerpicommerce-pp-cli orders batch`** - Crea piu ordini
- **`swerpicommerce-pp-cli orders create`** - Crea un ordine
- **`swerpicommerce-pp-cli orders get`** - Dettaglio ordine
- **`swerpicommerce-pp-cli orders list`** - Lista ordini
- **`swerpicommerce-pp-cli orders update`** - Aggiorna i campi indicati dell'ordine. L'annullamento e un update di stato:
`{"stato": "annullato"}`. Gli ordini non si eliminano (la storia vendite
resta integra). Campi non riconosciuti -> 400 VALIDATION_ERROR.

### page-templates

Manage page templates

- **`swerpicommerce-pp-cli page-templates list`** - `presets` = template di partenza per le pagine nuove;
`pagine_sistema` = mappa tipo -> file template delle pagine di sistema
(il `template_name` delle pagine normali è gestito dal sistema:
ogni pagina ha il suo file contenuto per slug).

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

- **`swerpicommerce-pp-cli payment-methods list`** - Lista metodi di pagamento attivi

### products

Prodotti e giacenze

- **`swerpicommerce-pp-cli products batch`** - Crea piu prodotti
- **`swerpicommerce-pp-cli products create`** - Crea un prodotto
- **`swerpicommerce-pp-cli products delete`** - Elimina un prodotto
- **`swerpicommerce-pp-cli products get`** - Dettaglio prodotto
- **`swerpicommerce-pp-cli products list`** - Di default le variazioni (prodotti con `prod_principale_id`) sono
escluse: `include_variants=true` le include piatte accanto ai padri;
`prod_principale_id=<id>` restituisce SOLO le variazioni di quel padre.
- **`swerpicommerce-pp-cli products update`** - Campi non riconosciuti -> 400 VALIDATION_ERROR.

### shipping-methods

Manage shipping methods

- **`swerpicommerce-pp-cli shipping-methods list`** - Lista metodi di spedizione

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
