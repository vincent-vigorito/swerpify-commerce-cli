---
name: swerpicommerce-ops
description: Guida operativa per agenti che gestiscono un sito SwerpiCommerce (piattaforma e-commerce Swerpify) via API v2/CLI — workflow completi (catalogo, pagine SWCSS, blog, mailing, carrelli abbandonati, punti fedeltà, codici sconto, design), quirk dell'API e setup multi-tenant. Usare per qualsiasi operazione su un tenant SwerpiCommerce — creazione/modifica di prodotti, pagine, articoli, campagne email, immagini, CSS/JS del tema.
---

# SwerpiCommerce Ops — guida operativa per agenti

Conoscenza operativa per lavorare sull'API v2 di SwerpiCommerce (81 path, 142
operazioni al 07/07/2026 — la superficie evolve spesso, anche in giornata:
in caso di dubbio ricontrolla `GET <base_url>/openapi.json`). Complementare
alla skill `pp-swerpicommerce` (riferimento comandi del CLI generato): qui ci
sono i **flussi giusti e gli errori già fatti**.

Approfondimenti in questa skill (leggili quando servono):
- **`references/swcss-design-system.md`** — il design system SWCSS completo:
  layer, regole, breakpoint, tree-shaking, animazioni pure-CSS, errori tipici.
  Da leggere PRIMA di creare o modificare pagine/CSS.
- **`references/cli-and-api.md`** — primer d'uso: flag globali del CLI, pattern
  con jq/heredoc, API raw con curl, forme di risposta, filtri di lista.

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
- Pattern robusto: `jq '(.results.data // .results)'` per le letture,
  `jq '(.data.data // .data)'` per le scritture.

## Quirk dell'API (verificati sul campo)

| Quirk | Dettaglio |
|---|---|
| Placeholder email | **Graffa singola** `{nome}`, NON `{{nome}}` (le description dello spec sbagliano). Risolti da `variabili` + dati cliente (`nome`, `cognome`, `email`); quelli senza valore restano intatti |
| Booleani sui codici sconto | `attivo`/`cumulativo` sono **interi 0/1** (gli articoli invece usano `true/false`) |
| Date codici sconto | `data_scadenza` solo `YYYY-MM-DD` |
| Campi sconosciuti | PUT su prodotti/pagine li **ignora in silenzio** (200 senza salvare — verifica sempre in rilettura); PUT su clienti/discount-codes/endpoint recenti valida strict (400) |
| Punti fedeltà | `punti_totali` segue anche i delta negativi (non è "totale storico maturato") |
| Email cliente | `null` nella lista; c'è solo nel **dettaglio** (`customers get`) — arriva dall'account di login |
| Variazioni prodotto | Padre `tipo_prodotto: "variabile"`; figlie con `prod_principale_id` + `valori_attributi: [{"attributo":"Colore","valore":"Rosso"}]`. Niente filtro per padre: lista con `--include-variants=true` e filtra client-side |
| Stato articoli | enum `bozza\|pubblicato\|archiviato`; ordini: stringa libera, default `in_attesa_pagamento` |
| Immagini | base64, max 10 MB, jpg/png/webp/gif/avif. Upload prodotto con `tipo: main` **sostituisce ed elimina** la main precedente. L'upload media restituisce `valore_campo` da usare nei campi immagine (es. `immagine_evidenza`) |

## ⭐ La regola d'oro del design: COMPILE

**Nulla di pagine/CSS va live finché non esegui `design compile`** (~1.3s,
tree-shaking sulle classi usate nei template). Vale per: contenuto pagine
nuovo E aggiornato, file CSS. NON serve per: il JS per-pagina (live subito) e
i dati (prodotti, articoli, ordini...).

```bash
swerpicommerce-pp-cli design compile --agent   # sempre, dopo modifiche design
```

## Workflow: pagina nuova con stile dedicato

```
1. pages create --stdin            # title obbligatorio; il content può stare già qui
2. pages content page-update <id>  # solo l'interno del {% block content %}
3. PUT /design/css/cms/<slug>.css  # via curl (bug 2-path-param) — un file per pagina
4. design js-put <slug>.js         # opzionale: autoload per slug, defer, no compile
5. design compile                  # ← senza questo non esiste
6. curl https://<tenant>/<slug>/   # verifica pubblica
```

- **Leggi prima di scrivere**: `GET /design/swcss-guide` (guida ufficiale del
  design system), `design css-list --section cms`, `GET /page-templates`
  (template e preset disponibili), e il contenuto della homepage
  (`pages content page-get <id>`) come catalogo dei componenti `sw-*` esistenti.
- Classi nuove prefissate `sw-<slug>-*`; variabili `var(--sw-..., fallback)`;
  breakpoint `@media (--mb|--sm|--md|--lg|--xl)` mobile-first.
- Animazioni allo scroll in puro CSS: `animation-timeline: view()` dentro
  `@supports` (senza supporto il contenuto resta visibile). Il tree-shaker non
  vede le classi aggiunte da JS a runtime: dichiarale in un commento del template.
- Il layer `base/` del design system non è esposto e non si tocca.
- Pagine di sistema e homepage sono protette (delete → 400 SYSTEM_PAGE).

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
   (globale+header_footer+cms+custom): le classi `sw-sv-*`/`sw-wrap` ci sono
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

## Verifiche d'abitudine

- Dopo ogni scrittura: **rileggi** (`get --no-cache`) — vedi quirk dei campi ignorati.
- `doctor` a inizio sessione e dopo cambi di config/tenant.
- Dopo modifiche design: compile + verifica della pagina pubblica (200 + contenuto).
- Per i test su dati reali: entità con prefisso riconoscibile (es. `ZZTEST`) e
  **cleanup completo** a fine giro; non toccare i dati del cliente senza richiesta.

## Cosa NON si può fare via API (verificare a ogni evoluzione)

- Configurare SMTP Marketing, permessi delle chiavi, definizioni attributi
  (`/attributes` è sola lettura) → pannello.
- Tracking aperture/click delle campagne; webhook outbound (es. `cart.abandoned`).
- Annullamento/eliminazione ordini; creazione metodi di pagamento/spedizione.
- Modificare il layer CSS `base/` del design system.
