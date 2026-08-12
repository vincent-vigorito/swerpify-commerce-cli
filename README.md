# swerpify-commerce-cli

CLI, server MCP e skill per agenti che lavorano su **SwerpiCommerce**, la piattaforma
e-commerce di Swerpify (API v2). Generato da uno schema OpenAPI neutro con
[CLI Printing Press](https://github.com/mvanhorn/cli-printing-press) → binario CLI Go +
bundle MCP + skill operativa.

> Repo gemello: il CLI **Swerpify ERP** (gestionale) è in
> [vincent-vigorito/swerpify-cli](https://github.com/vincent-vigorito/swerpify-cli).

## Cosa contiene

| Cartella / file | Cosa è |
|---|---|
| [`generated/swerpicommerce-cli/`](generated/swerpicommerce-cli/) | CLI Go generato (**183 operazioni su 103 path**) + server MCP + `SKILL.md`/`AGENTS.md` (riferimento comandi) + `Makefile` |
| [`sites/`](sites/) | Gestione **multi-sito**: wrapper `swc` + una sottocartella per sito con `credentials.env` (vedi sotto) |
| [`skills/swerpicommerce-ops/`](skills/swerpicommerce-ops/) | Skill operativa per agenti (workflow, quirk dell'API, design system SWCSS) + gli script dei due cancelli di conformità |
| [`SWERPICOMMERCE-ISSUES.md`](SWERPICOMMERCE-ISSUES.md) | Report dei problemi di piattaforma trovati sul campo: riproduzione, workaround, richiesta di fix, retest. È il canale di feedback verso il team dell'API |
| [`MCP-REMOTO-ROADMAP.md`](MCP-REMOTO-ROADMAP.md) | Progetto del server MCP remoto: da mirror 1:1 degli endpoint a tool curati per mestiere |
| `swerpicommerce-v2-openapi-neutral.json` | Schema OpenAPI v2 neutralizzato (server = placeholder `YOUR-TENANT`) |

Cronologia versioni in [`CHANGELOG.md`](CHANGELOG.md).

## Cosa puoi farci

Le aree coperte dalla CLI, per capire in un colpo d'occhio se ti serve:

- **Catalogo** — prodotti (semplici, variabili con **variazioni**, kit, custom box),
  categorie, attributi, listini, aliquote IVA, giacenze, immagini.
- **Contenuti** — pagine CMS, blog e categorie, media, form e loro submission,
  redirect 301/302, file `.well-known`.
- **Design** — CSS per layer, template del tema (header/footer/pagine di sistema), colori e
  token, loghi e favicon, JS per pagina, compilazione dei bundle.
- **Vendite** — ordini, carrelli (inclusi gli abbandonati), codici sconto, punti fedeltà,
  metodi di spedizione e pagamento.
- **Marketing** — liste, template ed email, campagne con statistiche di invio.
- **Integrazioni** — webhook in uscita (`order.created`, `order.updated`, `form.submitted`,
  `cart.abandoned`), custom app Django, fork/versionamento del tenant, cache e CDN.

L'elenco completo dei comandi: `swerpicommerce-pp-cli api`.

---

## Installazione (da GitHub)

### Prerequisiti
- **Go ≥ 1.26** per compilare la CLI (il toolchain esatto si scarica da solo grazie al
  pin `toolchain` nel `go.mod`).
- **Accesso al repo** (è privato): chiave SSH abilitata sul repo, oppure *Download ZIP*
  dalla pagina GitHub.
- *(opzionale, solo per il bundle MCP o per rigenerare)* la
  [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press) in `~/go/bin`.
- *(opzionale, per la skill)* [Claude Code](https://claude.com/claude-code).

### 1. Clona il repo
```bash
git clone git@github.com:vincent-vigorito/swerpify-commerce-cli.git
cd swerpify-commerce-cli
```
> Repo privato → serve accesso SSH. In alternativa: pagina GitHub → **Code → Download ZIP**.

### 2. Compila e installa la CLI
```bash
cd generated/swerpicommerce-cli

make install          # compila e installa `swerpicommerce-pp-cli` in $(go env GOPATH)/bin
#   — in alternativa, solo build locale:
make build            # produce ./bin/swerpicommerce-pp-cli
```
Assicurati che `$(go env GOPATH)/bin` sia nel `PATH` (dopo `make install`). Se la build
locale non risulta eseguibile: `chmod +x bin/swerpicommerce-pp-cli`.

### 3. Configura e autenticati
```bash
export SWERPICOMMERCE_BASE_URL="https://<il-tuo-tenant>/api/v2"

swerpicommerce-pp-cli swerpicommerce-auth token --api-id <ID> --api-secret <SECRET> --agent
swerpicommerce-pp-cli auth set-token <TOKEN>
swerpicommerce-pp-cli doctor          # verde = pronto
```
Base URL del tenant via env `SWERPICOMMERCE_BASE_URL`, `base_url` nel `config.toml`,
oppure `--config <file>`. Con l'auth "manuale" il token NON si rinnova da solo alla
scadenza → per gestire più siti con refresh automatico usa il wrapper `swc` (sotto).

### 3b. Gestione multi-sito con `swc` (consigliato per più tenant)
Invece di file sparsi in `~/.config`, ogni sito è una sottocartella di [`sites/`](sites/)
con un solo `credentials.env`. Il wrapper [`sites/swc`](sites/swc) rileva il sito, rigenera
e cachea da solo il token Bearer (auto-refresh su scadenza) e invoca il CLI — senza toccare
il binario generato.
```bash
cd sites
mkdir site1
cp _template/credentials.env.example site1/credentials.env   # incolla api_id, api_secret, base_url
cd site1
../swc pages list --agent            # opera su site1; il sito è la cartella corrente
../swc --which                       # sito/base_url attivi
```
Le cartelle-sito con le credenziali sono escluse dal versionamento da un `.gitignore` a
whitelist. Dettagli in [`sites/README.md`](sites/README.md).

### 4. Server MCP (Claude Desktop) — opzionale
```bash
make build-mcp                        # binario server MCP in ./bin/
printing-press bundle .               # crea il bundle .mcpb (richiede ~/go/bin/printing-press)
```
Apri il file `.mcpb` con Claude Desktop: all'installazione chiede **base URL** del tenant
e **Bearer token**. *(Quando pubblicati, il `.mcpb` sarà scaricabile dalle
[Releases](../../releases) senza clonare nulla.)*

### 5. Skill per agenti (Claude Code) — opzionale
```bash
cp -r skills/swerpicommerce-ops ~/.claude/skills/
```
Guida operativa completa (workflow pagine/CSS/JS, regola d'oro `design compile`, quirk
dell'API, design system SWCSS). Il riferimento comandi è in
`generated/swerpicommerce-cli/SKILL.md`.

---

## Aggiornare / rigenerare (quando l'API evolve)
```bash
# 1. scarica lo schema live (GET <base_url>/openapi.json) e neutralizzalo:
#      server URL → placeholder YOUR-TENANT · title → "SwerpiCommerce API"
#      ⚠️ RIMUOVI il campo top-level "x-api-id": gli export dal pannello incorporano
#         l'api_id REALE della chiave che li ha generati
# 2. rigenera:
~/go/bin/printing-press generate --spec <schema-neutro> \
  --output generated/swerpicommerce-cli --force --validate=false
# 3. due passi manuali dopo OGNI regen:
#    a. ri-pin del toolchain nel go.mod  (go 1.26.x → + "toolchain go1.26.4")
#    b. ri-patch di manifest.json: aggiungere swerpicommerce_base_url al user_config,
#       mappata su env SWERPICOMMERCE_BASE_URL (il generatore non la emette)
# 4. make build (+ chmod +x se serve) · 5. printing-press bundle .
```

Due insidie note, entrambe da gestire a mano:

- I **4 path `custom-apps`** compaiono SOLO negli export dal pannello: rigenerando dallo
  schema pubblico vanno innestati dal neutral precedente, altrimenti spariscono.
- L'exporter del pannello **spezza le description che contengono una virgola** in una
  chiave JSON spuria con valore `null` (issue B59) → va corretta nel neutral a ogni export.

## Note operative

Quirk del CLI generato, verificati sul campo:

- Route con **2 path-param** (es. `/design/css/{sezione}/{file}`, `/media/{cartella}/{file}`):
  URL costruito male dal generatore → workaround con `curl` + Bearer token.
- Alcuni comandi-risorsa sono `Hidden: true` — invisibili in `--help` ma funzionanti:
  l'elenco vero è `swerpicommerce-pp-cli api`.
- **Envelope diversi**: letture in `.results.data` (liste con `.results.meta`), scritture in
  `.data.data`. Pattern robusto per jq: `(.results.data // .results)`.
- **Response cache stale** dopo scritture fatte fuori dal CLI (es. `curl`): `--data-source live`
  NON la bypassa (`meta.source` dice "live" ma il body è la copia) → serve **`--no-cache`**.
- I **warning runtime** vengono stampati su stdout *prima* del JSON: sporcano l'output
  `--json` nelle pipe.
- L'envelope delle liste tiene solo `items`: eventuali chiavi sorelle della risposta vengono
  scartate (workaround: `curl`).
- **Nulla di ciò che riguarda design e pagine va live senza `design compile`** (il JS per
  pagina è l'eccezione: è immediato). Dopo aver modificato i **template del tema** serve
  anche `cache flush`.

## Licenza
Apache-2.0 (vedi `generated/swerpicommerce-cli/LICENSE`).
