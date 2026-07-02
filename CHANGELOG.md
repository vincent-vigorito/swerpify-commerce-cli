# Changelog

Tutte le modifiche rilevanti a questo repo. Formato
[Keep a Changelog](https://keepachangelog.com/it/1.1.0/), versionamento
[SemVer](https://semver.org/lang/it/).

> Nota: la versione qui sotto è quella del **repo** (CLI + wrapper + skill). Il bundle MCP
> (`generated/swerpicommerce-cli/manifest.json`) ha un suo numero, ereditato dal generatore
> (attuale **4.6.1**), che non segue questo changelog.

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
