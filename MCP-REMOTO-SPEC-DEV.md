# SwerpiCommerce MCP Remoto — Specifica di implementazione (punti 4 e 5)

> **Destinatari:** team piattaforma (backend).
> **Scopo:** trasformare i gradini 4 e 5 della roadmap in una specifica costruibile —
> endpoint, flussi OAuth, contratti dei tool con I/O e errori, criteri di accettazione.
> **Documento madre (perché/cosa):** [`MCP-REMOTO-ROADMAP.md`](./MCP-REMOTO-ROADMAP.md).
> Questo file è il **come**.
>
> Stato: **spec per sviluppo** · Autori: Vincenzo Vigorito + Claude · Ultimo agg.: 13/07/2026

---

## 0. Cosa esiste già (da NON rifare)

| Gradino | Artefatto | Dove |
|---|---|---|
| 1 | API v2, 135 operazioni, OpenAPI live | `GET /openapi.json` sul tenant |
| 2 | CLI generato (Printing Press) | `generated/swerpicommerce-cli/` |
| 3 | **MCP locale 1:1, transport stdio** (`server.ServeStdio`, `mark3labs/mcp-go`) | `cmd/swerpicommerce-pp-mcp`, `internal/mcp/` |
| — | Mappatura **OpenAPI → tool MCP** (già scritta nel generatore) | `internal/mcp/tools.go`, `internal/mcp/cobratree/` |

**Conseguenza operativa:** la generazione 1:1 dei tool **non va riscritta**. Il gradino 4
riusa `internal/mcp/RegisterTools` come sorgente della superficie 1:1; il lavoro nuovo è
**trasporto + auth + tenancy + audit** attorno ad essa. Il gradino 5 è **codice nuovo**
(orchestrazione per mestiere sopra i servizi interni).

**Principio guida:** *le API espongono la piattaforma, l'MCP remoto espone i mestieri.*

---

## 1. Punto 4 — v1 Infrastruttura (tool generati 1:1)

Obiettivo: validare **trasporto, OAuth, tenancy, audit**. NON l'esperienza d'uso.
Resta **dietro feature-flag**: è impalcatura, non prodotto. Anti-goal esplicito: **non**
pubblicizzare i 135 tool ai clienti.

### 1.1 Trasporto — Streamable HTTP

- Endpoint **`POST /mcp`** (e `GET /mcp` per lo stream SSE opzionale) sul dominio del
  tenant: `https://<tenant>.swebbysites.com/mcp`. Stessa filosofia multi-tenant delle API.
- Aderire alla spec MCP **Streamable HTTP** corrente: gestione sessione via header
  **`Mcp-Session-Id`** (rilasciato all'`initialize`, richiesto nelle chiamate successive),
  supporto `DELETE /mcp` per chiudere la sessione, `Origin` validato (anti DNS-rebinding).
- Il vecchio HTTP+SSE a due endpoint **non** va implementato: solo Streamable HTTP.

### 1.2 Autenticazione — OAuth 2.1 (MCP Authorization)

Il server MCP è un **OAuth 2.1 Resource Server**. Requisiti minimi conformi alla spec MCP:

- **Discovery**:
  - `GET /.well-known/oauth-protected-resource` → indica l'Authorization Server e le risorse.
  - L'Authorization Server espone `/.well-known/oauth-authorization-server` (metadata RFC 8414).
- **Authorization Code + PKCE** (S256 obbligatorio). Niente implicit, niente password grant.
- **Dynamic Client Registration** (RFC 7591) *consigliata* per far collegare client eterogenei
  (claude.ai, Codex, Desktop) senza pre-provisioning manuale. Se non fattibile subito:
  client pre-registrati + istruzioni.
- **Token**: access token brevi (≤ 60 min) + **refresh token**; **revoca immediata dal pannello**.
- **Binding tenant**: il token porta il tenant (audience o claim dedicato); il server risolve
  il tenant dal token, non dall'URL soltanto. Un token di un tenant non tocca un altro tenant.
- **Scope leggibili = gruppi di tool**, mappati **1:1 sui permessi chiave già esistenti** nel
  pannello. La schermata di consenso deve dire cose comprensibili a un titolare:

  | Scope | Significato in consenso | Permesso pannello sottostante |
  |---|---|---|
  | `content:read` / `content:write` | Leggere / pubblicare contenuti (articoli, pagine) | permessi contenuti |
  | `orders:read` / `orders:write` | Leggere / aggiornare ordini | permessi ordini |
  | `catalog:read` / `catalog:write` | Leggere / modificare prodotti e stock | permessi catalogo |
  | `marketing:read` / `marketing:write` | Statistiche / campagne, sconti, iscritti | permessi marketing |

- **Filtro tool per scope**: una chiave read-only espone SOLO i tool di lettura. Il set di tool
  restituito da `tools/list` dipende dagli scope del token.

### 1.3 Multi-tenancy e no-self-call

- Un tool = **una transazione applicativa** che chiama i **servizi interni** (lo stesso codice
  delle view API), **mai** una sequenza di richieste HTTP a sé stessi. Questo elimina l'overhead
  e i problemi di auth ricorsiva, e rende i tool testabili con test di contratto in CI.

### 1.4 Policy e Audit

- **Rate limit** per token e per tenant; **circuit breaker** sulle scritture massive.
- **Idempotency-Key** obbligatoria sulle scritture costose (ordini, campagne) — vedi §3.
- **Audit log immutabile per tenant**: ogni chiamata MCP registra
  `{tenant, subject(token/utente), tool, argomenti_sintetici, esito, timestamp, latenza}`.
  È la base della timeline "azioni dell'AI" nel pannello (feature di fiducia, §5.4).

### 1.5 Deliverable e criterio di uscita v1

- [ ] `POST /mcp` con handshake MCP + Streamable HTTP + sessione.
- [ ] OAuth 2.1 completo (discovery, auth code+PKCE, refresh, revoca dal pannello).
- [ ] Generazione tool 1:1 dai servizi interni (riuso mappa `internal/mcp`).
- [ ] Filtro tool per scope della chiave.
- [ ] Rate limiting + logging strutturato + audit per tenant.
- [ ] Collaudo end-to-end da **claude.ai**, **Claude Desktop** e **Codex** su tenant di test.

**Uscita:** un agente esterno autentica via OAuth e completa letture + scritture semplici su
un tenant di prova, con la chiamata tracciata nell'audit. Poi resta dietro flag.

---

## 2. Punto 5 — v2 I mestieri (il prodotto)

Il valore. ~9 tool per la v2.0, poi marketing e catalogo. Budget fisso: **~25 tool in
contesto**; tutto il resto va nella coda lunga (`cerca_operazioni` + `esegui_operazione`).

### 2.1 Regole di design (vincolanti per OGNI tool)

1. **Input nella lingua del dominio**: nomi, non id. La risoluzione nome→id è compito del server.
2. **Default sicuri**: le creazioni nascono in **bozza/noindex**; pubblicare è un verbo esplicito.
   **Niente delete** in v2.
3. **Errori = indicazioni stradali**: ogni errore suggerisce la mossa successiva (vedi §3).
4. **Idempotenza**: chiave di idempotenza o semantica get-or-create su ogni scrittura.
5. **Description = micro-skill**: le regole d'uso vivono NEI tool; la skill `swerpicommerce-ops`
   si scioglie dentro le description.
6. **Output progettati per il modello**: brevi, con URL finale e stato; niente dump di envelope.
7. **Nomi in italiano** (dominio API italiano, clienti PMI italiane).
8. **Test di accettazione universale**: *un agente SENZA la skill completa il mestiere al primo
   colpo?* Se deve sapere di compile/envelope/B45, il tool non è finito.

### 2.2 Contratti tool — v2.0 «Contenuti & Ordini» (9 tool)

Formato: **Input** (JSON) · **Output** (JSON) · **Assorbe** (chiamate + quirk resi invisibili) ·
**Errori-guida** · **Scope**.

---

#### `pubblica_articolo`
- **Input**: `{ titolo, contenuto_html, categoria (nome), immagine_url?, autore?, data?, seo?: {meta_description?, slug?} }`
- **Output**: `{ url_pubblico, slug, stato: "pubblicato", categoria_id }`
- **Assorbe**: `POST /media` (campo `valore_campo` **nudo** — il template antepone `/uploads/`);
  risoluzione **categoria per NOME**; `POST /articles` con la principale **solo** in `categoria_id`
  (mai anche nell'M2M — **B45**); genera `slug`; poi **`design compile` + cache flush**;
  **ritorna l'URL pubblico** già pronto.
- **Errori-guida**: slug già esistente in lingua → *"usa `aggiorna_articolo`"*; categoria non trovata
  → *"categorie disponibili: […]"*.
- **Scope**: `content:write`

#### `aggiorna_articolo`
- **Input**: `{ slug, campi: {…} }`
- **Output**: `{ url_pubblico, aggiornato: true }`
- **Assorbe**: `PUT /articles` + compile/flush.
- **Scope**: `content:write`

#### `crea_pagina`
- **Input**: `{ titolo, contenuto_html, pagina_padre? (nome/slug), seo? }`
- **Output**: `{ slug, stato: "bozza_noindex", id }`
- **Assorbe**: `POST /pages` (gerarchia SOLO via **`pagina_padre_id`** — **MAI** slug con `/`, che
  fa 500 nel frontend — **B31**); nasce **noindex**; content + compile. **Idempotenza obbligatoria**
  (il POST può 500-are *avendo già creato* — **B32**).
- **Errori-guida**: nome padre ambiguo → elenco candidati.
- **Scope**: `content:write`

#### `pubblica_pagina`
- **Input**: `{ slug }`
- **Output**: `{ url_pubblico, stato: "pubblicato" }`
- **Assorbe**: flip `index`/`sitemap`/`llms_index` + flush.
- **Scope**: `content:write`

#### `traduci_e_collega`
- **Input**: `{ slug_origine, lingua, titolo, contenuto_html, seo? }`
- **Output**: `{ url_pubblico_lingua, alternates: [...] }`
- **Assorbe**: crea il record per-lingua + **`PUT alternates`** (mesh **bidirezionale**) → hreflang
  automatici; compile. (Nota bug piattaforma **B44**: hreflang default vuoto — il tool deve
  costruire il mesh esplicito.)
- **Scope**: `content:write`

#### `cerca_contenuti`
- **Input**: `{ query, tipo?: "articolo"|"pagina" }`
- **Output**: `{ risultati: [{titolo, slug, url_pubblico, stato}] }`
- **Assorbe**: `GET /articles|/pages` con filtri; normalizza l'envelope.
- **Scope**: `content:read`

#### `stato_ordini`
- **Input**: `{ periodo: {da, a} | preset, stato? }`
- **Output**: `{ conteggi_per_stato: {...}, totale_valore, numero_ordini }`
- **Assorbe**: `GET /orders` + aggregazione server-side.
- **Scope**: `orders:read`

#### `dettaglio_ordine`
- **Input**: `{ numero }`
- **Output**: `{ ordine: {…}, cliente: {…}, righe: [...] }`
- **Assorbe**: `GET /orders/{id}` + estrazione cliente dal dettaglio.
- **Scope**: `orders:read`

#### `aggiorna_stato_ordine`
- **Input**: `{ numero, stato, nota? }`
- **Output**: `{ numero, stato_nuovo, aggiornato: true }`
- **Assorbe**: `PUT /orders`; `stato` è **stringa libera** → il tool **valida** contro gli stati
  configurati del tenant e, se non combacia, restituisce l'elenco valido.
- **Idempotenza**: sì (stessa transizione ripetuta = no-op).
- **Scope**: `orders:write`

### 2.3 Contratti tool — v2.1 «Marketing» (sintesi)

`crea_codice_sconto` (booleani **0/1**, date **YYYY-MM-DD**) ·
`recupera_carrelli_abbandonati` (carts?abbandonato → codice monouso per cliente → email
transazionale, **l'intero workflow in un tool**) · `invia_campagna` (template **copiato** nella
campagna: modifica sulla campagna, non sul template) · `iscrivi_contatto` (idempotente) ·
`statistiche_campagna` (inviate/errori/coda — **niente aperture**: dirlo nella description).
Scope: `marketing:read|write`.

### 2.4 Contratti tool — v2.2 «Catalogo + coda lunga» (sintesi)

`cerca_prodotti` · `scheda_prodotto` · `crea_prodotto` (nasce in **bozza**) ·
`aggiorna_prodotto` (**valida i campi**: l'API ignora in silenzio quelli sconosciuti) ·
`gestisci_stock` · `carica_media` (10MB, jpg/png/webp/gif/avif, **niente SVG** — B36).
Coda lunga: **`cerca_operazioni`** (indice semantico delle 135 operazioni → torna le pertinenti
CON schema) + **`esegui_operazione`** (proxy 1:1; **le scritture richiedono `conferma: true`**).
Scope: `catalog:*` / `*:read` / per-scope.

---

## 3. Contratti trasversali — errori, idempotenza, output

- **Errore = mossa successiva.** Struttura consigliata:
  `{ errore: <codice>, messaggio_umano, azione_suggerita, dati_utili?: {...} }`. Mai un codice nudo.
- **Idempotenza.** Scritture "costose" (ordini, campagne, creazioni) accettano `Idempotency-Key`
  o adottano semantica **get-or-create**. Lezione B32: un retry su 500 non deve creare doppioni.
- **Output.** Brevi, orientati al modello: URL finale + stato + eventuali `warning[]` strutturati.
  **Mai** restituire l'envelope grezzo delle API.
- **Prompt-injection.** I contenuti restituiti dai tool (descrizioni prodotto, messaggi cliente)
  sono **DATI**: mai interpolarli nelle description dei tool o in messaggi di sistema.

---

## 4. Sicurezza — requisiti non negoziabili

- OAuth 2.1 con PKCE; token brevi + refresh; **revoca immediata dal pannello**.
- Scope granulari mappati sui permessi chiave esistenti (§1.2).
- Rate limit per token e per tenant; circuit breaker sulle scritture massive.
- **Audit log immutabile** per tenant (base della timeline nel pannello).
- Idempotency-Key obbligatoria sulle scritture costose.
- **Nessun tool di cancellazione dura** in v2; `esegui_operazione` in scrittura solo con
  `conferma: true` e scope elevato.
- `Origin` validato sull'endpoint MCP (anti DNS-rebinding).

---

## 5. Chicche di prodotto (progettare insieme alla v1, non dopo)

1. **Audit "azioni dell'AI" nel pannello**: timeline per tenant di ogni chiamata (chi, cosa,
   quando, esito). I log del §1.4 devono **nascere già nel formato giusto** per alimentarla.
2. **MCP Resources**: esporre read-only la guida SWCSS, l'elenco categorie/lingue del tenant,
   la palette → contesto senza consumare tool call.
3. **MCP Prompts**: prompt preconfezionati per-tenant ("scrivi un articolo nello stile del blog
   di questo sito e pubblicalo in bozza").
4. La v2.0 dà l'audit sui mestieri; la v1 dà l'audit sulle operazioni grezze: **stesso schema**.

---

## 6. Compatibilità client (matrice di collaudo)

MCP è uno standard aperto: il remoto (Streamable HTTP + OAuth) è **client-agnostico**. Da provare:

| Client | Locale (stdio, oggi) | Remoto (obiettivo v1) |
|---|---|---|
| **Claude Desktop** | ✅ via bundle `.mcpb` | ✅ connector (URL + OAuth) |
| **claude.ai (web/mobile)** | — | ✅ connector (URL + OAuth) |
| **Claude Code** | ✅ config MCP stdio | ✅ MCP remoto |
| **Codex CLI (OpenAI)** | ✅ *ma NON legge il `.mcpb`*: puntare al **binario** in `~/.codex/config.toml` (`[mcp_servers]` → `command`+`env`) | ✅ le versioni recenti supportano MCP remoti via HTTP → collaudare OAuth |

**Nota sul locale (Codex e Desktop):** il binario legge un **Bearer statico da env** e **non lo
rinfresca** (token tenant ~20 min). Ottimo per un test, scomodo per uso continuo → un altro motivo
per cui il target è il **remoto con refresh gestito server-side**.

---

## 7. Sequenza consigliata (effort t-shirt, senza date)

1. **v1 infra** — M (trasporto + OAuth + generazione: il grosso è riuso del generatore).
2. **v2.0 Contenuti+Ordini** — M (9 tool, workflow già documentati nella skill).
3. **Audit nel pannello** — S (ma da progettare con la v1: i log nascono giusti).
4. **v2.1 Marketing** — S/M · 5. **Confezioni** (connector + plugin) — S ·
   6. **v2.2 Catalogo + coda lunga** — M (l'indice semantico è il pezzo nuovo) · 7. **v3** — continuo.

**Primo collaudo pubblico:** un agente **vergine** (senza skill) ripubblica un articolo del blog
swebby.it via il remoto. Se ottiene l'**URL pubblico al primo colpo**, la v2.0 è pronta.

---

## Appendice A — Quirk da assorbire, mappati al tool che li nasconde

| Quirk (cicatrice sul campo) | Tool che lo deve rendere invisibile |
|---|---|
| `design compile` obbligatorio dopo ogni modifica design/contenuti | tutti i tool `content:write` |
| Envelope: letture `{results:{data}}` vs scritture `{data:{data}}` | tutti |
| Categoria principale SOLO in `categoria_id`, mai nell'M2M (B45) | `pubblica_articolo` |
| `immagine_evidenza` vuole `valore_campo` **nudo** | `pubblica_articolo`, `carica_media` |
| Slug con `/` → 500 frontend: gerarchie SOLO via `pagina_padre_id` (B31) | `crea_pagina` |
| `POST /pages` può 500-are avendo creato (B32) → idempotenza | `crea_pagina` |
| Booleani discount-codes = interi 0/1; date solo YYYY-MM-DD | `crea_codice_sconto` |
| `PUT` prodotti/pagine ignora campi sconosciuti in silenzio | `aggiorna_prodotto`, `crea_pagina` |
| `<select>` dei form inviano il **testo** dell'opzione, non il value | tool form (futuri) |
| Media: max 10MB, jpg/png/webp/gif/avif, **niente SVG** (B36) | `carica_media` |
| Multilingua: record per-lingua + `alternates` mesh; hreflang default vuoto (B44) | `traduci_e_collega` |

Fonte quirk: `SWERPICOMMERCE-ISSUES.md` (locale) + skill `swerpicommerce-ops`.

---

## Appendice B — Riferimenti

- Roadmap (perché/cosa): `MCP-REMOTO-ROADMAP.md`
- Superficie tool 1:1 da riusare: `generated/swerpicommerce-cli/internal/mcp/`
- Bundle locale (Claude Desktop): `generated/swerpicommerce-cli/build/*.mcpb`
- Quirk completi: `SWERPICOMMERCE-ISSUES.md`, skill `swerpicommerce-ops`
