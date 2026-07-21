# SwerpiCommerce v2 — Report problemi (API, spec, tenant demo, CLI)

**Data:** 2026-06-11
**Tenant demo:** `https://122-h000722.swebbysites.com` (MaoDemo, dietro Cloudflare)
**API live:** "SwerpiCommerce API v2" — 14 path / 22 operazioni, Bearer token
**Contesto:** analisi del file `maodemo-openapi-2.json` fornito + rigenerazione di `swerpicommerce-pp-cli` dallo schema live (`swerpicommerce/swerpicommerce-v2-live-openapi.json`)

Legenda severità: 🔴 critico · 🟡 medio · 🟢 minore

---

## TL;DR

1. 🔴 Il file **`maodemo-openapi-2.json` non corrisponde all'API deployata** — è la vecchia superficie v1 rietichettata "2.0.0". Tutte le sue 18 chiamate danno 404.
2. 🔴 Lo stesso file **contiene credenziali live in chiaro** (api_key, api_secret e valore Basic precomputato).
3. 🟡 L'API v2 reale funziona, ma ha **CRUD incompleti** (clienti senza dettaglio/modifica/elimina), **token 1h senza refresh**, **404 in HTML** invece che JSON e **server URL relativo** nello schema.
4. 🟡 Lato nostro: bug della Printing Press (comandi principali nascosti nell'help) e Go di sistema da aggiornare a ≥1.26.4.

---

## ⚡ Aggiornamento 11/06/2026 pomeriggio — riverifica dopo il nuovo export (`maodemo-openapi-3.json`)

Il team Swerpify ha rilasciato un nuovo export e aggiornato l'API. Riverificato tutto live:

**Risolti ✅:** A1 (l'export ora coincide con lo schema live, salvo il titolo personalizzato per tenant), A2 (niente più credenziali: resta solo `x-api-id`, che è il solo identificativo pubblico, senza secret), A3 (`api_id` e bearerAuth corretti), B1 (server URL assoluto sia nell'export sia nello schema live), B4 (i 404 API ora rispondono `application/json`), B5 (envelope `{data}` uniforme anche su payment/shipping-methods), B7 (**aggiunto `GET /auth/me`**: restituisce api_id, key_name e l'elenco permessi — testato, funziona).

**B3 in gran parte risolto ✅:** aggiunti e già deployati `GET/PUT/DELETE /customers/{id}` (GET testato live con esito 200). Restano assenti create/delete pagine e delete ordini (possibilmente voluti).

**B2 cambiato ⚠️:** i token emessi ora hanno `expires_at: null` — sembrano **non scadere più**. Sparisce il problema del refresh orario (e la necessità del comando di auto-refresh D3), ma un bearer senza scadenza è un trade-off di sicurezza da confermare come scelta consapevole (non c'è ancora revoca/lista token via API).

**Nuovo 🟡 → ✅ risolto in giornata:** la chiave demo `test-vincent` inizialmente non aveva i permessi `clienti.cliente.update` e `clienti.cliente.delete`; alla riverifica delle ~12:30 i permessi sono saliti da 14 a 16 e ora include entrambi.

**Ancora aperti:** B6 (openapi.json pubblico senza auth — riverificato, ancora così), C1 (dati demo quasi vuoti), D1, D2, D4, D5 (lato nostro).

**CLI rigenerato (11/06 ~12:30):** `swerpicommerce-pp-cli` ora espone i 4 endpoint nuovi (`customers get/update/delete`, `swerpicommerce-auth me`) — collaudati live con esito positivo (`auth me` → key test-vincent, `customers get 1` → 200). Gate verdi (vet, build, govulncheck col pin toolchain go1.26.4 rimesso), bundle MCP ricompilato. Il bug D1 (`Hidden: true`) è ripresentato come previsto: è nel generatore.

---

## A. File spec consegnato (`maodemo-openapi-2.json`)

### A1. 🔴 Lo spec descrive un'API che non esiste su quel server

Il file è **byte-per-byte la superficie v1** (stesse 18 operazioni di `dev/swcommerce.json`: path italiani `/catalogo/prodotti`, `/vendite/ordini`, `/clienti/clienti`, `/cms/pagine`, auth BasicAuth) con cambiati solo titolo ("MaoDemo — API"), etichetta versione ("2.0.0"), server URL e credenziali.

L'API realmente deployata su `/api/v2` è tutta un'altra cosa: path REST inglesi (`/products`, `/orders`, `/customers`, `/pages`, ...), Bearer token, endpoint batch.

**Verificato:** ogni path del file → HTTP 404 sul server live.
**Causa probabile:** il pannello di export dello schema ha esportato la definizione v1 etichettandola v2.
**Fix:** correggere l'export nel pannello; nel frattempo usare lo schema servito dall'API stessa (`GET /api/v2/openapi.json`), che è corretto.

### A2. 🔴 Credenziali live in chiaro dentro il file

Il file contiene:
- `x-api-credentials` a livello root con `api_key` e `api_secret` in chiaro;
- il valore `Basic base64(...)` **precomputato** dentro la descrizione del securityScheme.

Chiunque riceva il file ha accesso completo al tenant. Nota positiva: l'`openapi.json` pubblico del server **non** contiene le credenziali — il problema è solo nel flusso di export.

**Fix:** rimuovere le credenziali dall'export (o renderle opzionali con un avviso esplicito). Ruotare le credenziali del tenant MaoDemo se il file è già circolato. Non committare il file in repository.

### A3. 🟡 Naming e auth incoerenti col server

- Il file chiama il campo **`api_key`**, ma `POST /auth/token` richiede **`api_id`** (con `api_key` risponde `400 VALIDATION_ERROR: 'api_id' is a required property`).
- Il file dichiara **BasicAuth**, l'API v2 usa **Bearer token**.

**Fix:** allineare l'export e la documentazione al contratto reale (`TokenRequest = {api_id, api_secret, client_name?}`).

---

## B. API live SwerpiCommerce v2

### B1. 🟡 `servers` relativo nello schema live

`GET /api/v2/openapi.json` dichiara `servers: [{url: "/api/v2"}]`. Un client che scarica lo schema non può ricavare il base URL assoluto; per generare il CLI è stato necessario patchare a mano il server URL.

**Fix:** servire l'URL assoluto del tenant (es. `https://122-h000722.swebbysites.com/api/v2`).

### B2. 🟡 Token a scadenza 1h senza meccanismo di refresh

`POST /auth/token` emette un token valido 1 ora. Non esistono refresh token, endpoint di rinnovo, né (a quanto visibile dallo schema) endpoint per elencare/revocare i token emessi. Ogni client deve rifare l'exchange con le credenziali complete a ogni scadenza.

**Fix suggerito:** TTL configurabile o endpoint di refresh; in subordine, documentare chiaramente il giro di re-exchange.

### B3. 🟡 CRUD incompleti su clienti, pagine e ordini

| Risorsa | Presente | Mancante |
|---|---|---|
| **products** | list, get, create, update, delete, batch, stock get/update | — (completo ✅) |
| **customers** | list, create, batch | 🔴 **get dettaglio**, **update**, **delete** |
| **pages** | list, get, update | create, delete |
| **orders** | list, get, create, update, batch | delete (voluto? manca un'azione di annullamento esplicita) |
| **payment/shipping-methods** | list | — (solo lettura, ok) |

Il gap clienti è il più pesante: senza `GET /customers/{id}` né update, un integratore può solo creare e rileggere l'intera lista.

### B4. 🟡 404 API in HTML invece che JSON

Su path API inesistenti (es. `/api/v2/nonexiste`) il server risponde **404 `text/html`** con la pagina dello storefront, mentre per 400/401 usa il corretto envelope JSON `{"error": {"code", "message", "details"}}`. Un client API che sbaglia path riceve HTML inaspettato. Vale anche per la radice `/api/v2/` (404 HTML).

**Fix:** instradare tutto `/api/*` verso handler JSON, anche per route non trovate.

### B5. 🟢 Envelope di risposta incoerente tra endpoint

`/products`, `/orders`, `/customers` rispondono `{data: [...], meta: {total, limit, offset}}`; `/payment-methods` e `/shipping-methods` rispondono con un **array nudo** senza meta. Minore (sono endpoint di configurazione), ma uniformare semplifica i client.

### B6. 🟢 `openapi.json` pubblico senza autenticazione

`GET /api/v2/openapi.json` risponde 200 **senza credenziali**. È un miglioramento rispetto all'ambiente DEV (dov'era dietro login web), ma espone l'intera superficie API del tenant a chiunque conosca l'URL. Decidere se è una scelta consapevole; in caso contrario, richiedere il Bearer come per gli altri endpoint.

### B7. 🟢 Manca un endpoint di verifica credenziali ("whoami")

Non esiste un endpoint senza effetti per validare un token (es. `GET /auth/me`). Il `doctor` del CLI può solo dire "credenziali presenti, non verificate". Utile anche per gli integratori.

### B8. 🟡 I prodotti non hanno campi meta/SEO (le pagine sì) — test dell'11/06 pomeriggio

Test live di gestione meta su entrambe le risorse (entità `ZZTEST-CLAUDE`, originali ripristinati, cleanup completo):

- **Pagine ✅** — l'oggetto pagina espone un blocco SEO ricco: `meta_title`, `description`, `keywords`, `index`, `follow`, `sitemap`, `alternates`, `breadcrumbs_name` e perfino `llms_description` / `llms_index` / `llms_section`. Testato `PUT /pages/{id}` su `meta_title`, `description`, `keywords`, `llms_description`: tutti aggiornati e persistiti; accetta anche `null` espliciti per svuotare i campi.
- **Prodotti ❌** — l'oggetto prodotto non ha alcun campo meta/SEO (solo `descrizione`, `descrizione_breve`, `slug`). Per un e-commerce è un gap rilevante: niente title/description personalizzati per le schede prodotto.

**Fix suggerito:** aggiungere ai prodotti lo stesso blocco SEO delle pagine (incluse le proprietà `llms_*`).

### B9. 🟡 `PUT` ignora silenziosamente i campi sconosciuti

Inviando `meta_title`/`description`/`keywords` a `PUT /products/{id}` la risposta è **200 success**, ma i campi non vengono né salvati né rifiutati. Un integratore crede di aver scritto i meta e invece no — stesso pattern dei "filtri silenziosi" già segnalato sull'API progetti in produzione. Con `MutableObject` (`additionalProperties: true`) il contratto non protegge da typo nei nomi campo.

**Fix suggerito:** rispondere `400 VALIDATION_ERROR` sui campi non riconosciuti (come già fa `/auth/token`), o almeno elencare i campi ignorati nella risposta.

### B8-bis. ✅ Novità 11/06 ~15:00 — aggiunte le categorie, con blocco SEO completo

Il quarto export (`maodemo-openapi-4.json`, identico al live: ora 18 path) aggiunge **`/categories` con CRUD completo**, e `CategoryInput` include tutto il blocco SEO delle pagine: `meta_title`, `description`, `keywords`, `index`, `follow`, `llms_description`, `llms_index`, più `categoria_google` (mapping Google Shopping), `markups` e `template_name`. Permessi `catalogo.categoria.*` già attivi sulla chiave (ora 20).

**Testato live l'intero ciclo** (categoria `ZZTEST-CLAUDE`, poi eliminata): create con meta → tutti persistiti; update parziale (`meta_title`, `index`, `llms_index`) → aggiornati senza toccare gli altri campi; delete → ok, cleanup confermato.

Resta aperto B8 per i **prodotti**, che continuano a non avere campi meta — ora sono l'unica risorsa di catalogo senza blocco SEO (pagine ✅, categorie ✅, prodotti ❌).

**Aggiornamento ~16:40 — B8 risolto ✅:** `ProductInput` ha guadagnato il blocco SEO completo (`meta_title`, `description`, `keywords`, `index`, `follow`, `llms_description`, `llms_index`, `markups`). Testato live sul Prodotto Demo (id 2): tutti i campi impostati e persistiti — lo stesso PUT che al mattino veniva ignorato in silenzio ora salva. **Tutte le risorse di contenuto hanno ora SEO gestibile via API: pagine, categorie, articoli, categorie articoli e prodotti.** B9 (campi sconosciuti ignorati) resta aperto come comportamento generale.

### B10-bis. ✅ Novità 11/06 ~16:30 — aggiunti articoli e categorie articoli, con blocco SEO completo

Il quinto export (`maodemo-openapi-5.json`, identico al live: ora **22 path**) chiude B10: **`/articles` e `/article-categories` con CRUD completo**. `ArticleInput` ha tutto: contenuto (`titolo`, `contenuto`, `descrizione_breve`, `autore`, `data_pubblicazione`, `stato` bozza/pubblicato/archiviato, `in_evidenza`, `immagine_evidenza`) e blocco SEO (`meta_title`, `meta_description`, `keywords`, `index`, `follow`, `llms_description`, `llms_index`, `markups`). Idem `ArticleCategoryInput`. Permessi `cms.articolo.*` e `cms.categoria_articolo.*` già attivi (chiave a 28).

**Testato live:** creati "Categoria Articoli Demo" (id 1) e "Articolo Demo" (id 1, pubblicato, collegato, tutti i meta persistiti); update parziale dei meta verificato e funzionante. Nota di naming: gli articoli usano `meta_description`, le pagine `description` — piccola incoerenza fra risorse.

⚠️ Il **frontend pubblico del blog resta 404** (`/blog/`, `/blog/articolo-demo/`) anche con articolo pubblicato → vedi C2: la parte mancante ora è solo lato storefront/configurazione tenant.

### B10. 🟡 Gli articoli del blog non sono esposti dall'API *(superato — vedi B10-bis)*

Richiesta del test: gestire i meta anche sugli articoli del blog. Esito: **impossibile, la risorsa non esiste nell'API v2**.

Verificato l'11/06 pomeriggio:
- Lo schema live (riscaricato) ha sempre e solo 16 path: nessun endpoint blog/articoli.
- Probe diretti con Bearer valido: `/articles`, `/blog`, `/blog/`, `/posts`, `/blog/articles`, `/cms/articles`, `/articoli`, `/news` → tutti **404**.
- Gli articoli non passano nemmeno da `/pages`: le 9 pagine CMS del tenant sono home, pagine di sistema shop e policy (template `page.html`/`*-swcss.html`), nessun articolo.

Eppure il blog come funzionalità esiste: il menu del tema linka `/blog/`.

**Fix suggerito:** esporre una risorsa `/articles` (CRUD + lo stesso blocco SEO delle pagine, `meta_title`, `description`, `keywords`, `llms_*` — per contenuti blog i meta sono il punto centrale) con relativo permesso `cms.articolo.*`.

### B11. Check capacità completo (11/06 ~17:00) — cosa si può fare via API e cosa manca

Verificato live su tutta la superficie (22 path, 28 permessi):

| Area | Si può ✅ | Non si può ❌ |
|---|---|---|
| **Prodotti** | CRUD + batch, SEO completo, giacenze (`quantita`/`impegnata`/`ordinata`), prezzi multi-listino, varianti (`prod_principale_id`, `valori_attributi`), filtri (sku, stato, categoria, lang, include_variants/prices) | upload immagini (`foto` sola lettura), definizioni attributi, gestione listini, gestione marchi (solo `marchio_id` di riferimento) |
| **Categorie** | CRUD + SEO + `categoria_google`; campo `immagine` presente in input (formato non documentato) | — |
| **Clienti** | CRUD, indirizzi spedizione, dati fiscali (CF, P.IVA, PEC, SDI), assegnazione `listino_id`, password account. Nota: il PUT **valida in modo stretto** (400 sui campi sconosciuti — meglio di prodotti/pagine, cfr. B9) | **punti fedeltà in sola lettura** (`punti`, `punti_totali`, `punti_first_date` esposti in GET; scrittura → 400). Filtro lista solo per `email` |
| **Ordini** | crea/modifica/batch, righe prodotto, **sconti ad-hoc per ordine** (`sconti: [{tipo: percentuale\|monetario, valore}]`), flag `pagato` + `id_transazione`, metodi pagamento/spedizione | niente DELETE/annullamento esplicito, `stato` è stringa libera non documentata (default `in_attesa_pagamento`), niente rimborsi/spedizioni/tracking, nessun filtro lista |
| **Blog** | CRUD articoli **con HTML** (`contenuto`), categorie articoli, SEO completo, stati editoriali, `in_evidenza`, `immagine_evidenza` | frontend pubblico 404 (C2) |
| **Pagine CMS** | leggere; aggiornare SEO/meta, `title`, `slug`, JSON-LD (`markup_type`/`markups`), `llms_*` | **creare/eliminare pagine; modificare l'HTML**: le pagine non hanno campo contenuto, sono template-driven (`template_name`) — l'unico HTML scrivibile via API è il `contenuto` degli articoli |
| **Config** | leggere metodi di pagamento e spedizione | crearli/modificarli (`config.metodo.view` only) |
| **Assenti del tutto** (probe 404) | — | **codici sconto/coupon**, scrittura punti fedeltà, recensioni, wishlist, newsletter, media/upload, marchi, attributi, listini, movimenti magazzino, webhook outbound |

Gap principali da roadmap: **B12** codici sconto (oggi solo sconto ad-hoc per ordine, niente entità coupon riusabile), **B13** punti fedeltà in sola lettura (serve `POST /customers/{id}/points` o campo scrivibile con audit), **B14** pagine senza create/contenuto (se voluto — template-driven — va documentato), **B15** upload media assente (immagini prodotto/categoria/articolo gestibili solo da pannello).

### B12-B15. Aggiornamento 11/06 ~18:30 — sesto export: codici sconto, pagine complete, immagini prodotto

Il sesto export (`maodemo-openapi-6.json`, = live, **27 path**, permessi a 34) chiude quasi tutti i gap del check B11. Tutto testato live:

- **B12 ✅ Codici sconto** — `/discount-codes` CRUD completo. Creato `DEMO10` (id 1, 10%, scadenza 31/12/2026, max 100 usi / 1 per utente, contatore `usato`). Quirk di design: `attivo`/`cumulativo` sono **interi 0/1** (gli articoli usano booleani veri); `data_scadenza` è `date` YYYY-MM-DD. Errori di validazione chiari (400 con dettaglio campo).
- **B14 ✅ Pagine complete** — `POST /pages` (crea anche il file template `templates/frontend/<slug>.html`), `DELETE` (protetto: pagine di sistema/homepage → 400 SYSTEM_PAGE), e `GET/PUT /pages/{id}/content` che gestisce **solo l'interno del `{% block content %}`** del template per-istanza. Creata "Pagina Demo" (id 10) con HTML via API: **pubblica e visibile** su `/pagina-demo/` (200) ✅.
- **B15 ⚠️ Immagini prodotto: API ok, serving rotto** — `/products/{id}/images` upload base64 (max 10 MB, jpg/png/webp/gif/avif, `tipo: main|gallery`, promozione a main automatica). Upload testato sul Prodotto Demo: 201, `foto_principale` impostata, la scheda pubblica referenzia l'immagine… **ma `/uploads/catalogo/product_images/...` risponde 404**: il file non viene servito (storage o route nginx). 🆕 **C4**. Categorie e articoli restano senza endpoint upload dedicato (campi `immagine`/`immagine_evidenza` stringa).
- **B9 in miglioramento** — i nuovi endpoint validano strict ("Campi non riconosciuti → 400 VALIDATION_ERROR").
- **C3 in miglioramento + diagnosi** — `/negozio/` e la pagina categoria sono tornati **200**; restano 500 le tre policy. Indizio forte: quelle pagine hanno `content: null` (file contenuto per-istanza mancante), mentre la Pagina Demo appena creata col suo file funziona → probabile crash del template su file mancante. **Non ho toccato le 3 pagine** per non distruggere il caso di riproduzione.
- Scheda prodotto pubblica: pattern URL `/negozio/<categoria-slug>/<prodotto-slug>/` → 200 col Prodotto Demo. Nota: il tema del tenant contiene link hardcoded di un sito di corde da tennis (chi-siamo, contatti, prodotti String Project) che non esistono come pagine → 404 sparsi da tema, non da API.

### C4/B16. Ricontrollo immagini 11/06 ~18:50 — serving ancora rotto + PUT/DELETE non implementati

**C4 confermato e circoscritto.** Tutte le immagini del tema sono servite da `/static/` (verificato: `/static/img/uploads/logo_black.svg` → 200), mentre **nessuna route serve `/uploads/`**: l'immagine caricata via API dà 404 sia sull'URL dichiarato sia sulle varianti (`/media/...`, `/static/uploads/...`). Anche un **upload fresco** (`prodotto-demo-gallery.png`, 201 OK) risponde 404 immediato → la location nginx per `/uploads/` manca, o i file non vengono scritti nello storage servito.

**B16 🆕: `PUT`/`DELETE /products/{id}/images/{image_id}` dichiarati ma non implementati.** Risposta **405 Method Not Allowed**; `OPTIONS` conferma: `allow: HEAD, GET, OPTIONS`. In più la 405 esce come **pagina HTML** (default Flask/Werkzeug), non con l'envelope JSON `{error}` degli altri errori. Quindi oggi: upload ✅ e lista ✅, ma niente riordino/promozione/eliminazione → l'immagine diagnostica di galleria (id 2) non è eliminabile via API e resta sul Prodotto Demo.

### B17/B18. 🟡 Mailing e carrelli abbandonati non esposti dall'API (check 12/06)

Richiesta: gestire mailing/newsletter e carrelli abbandonati via API. Esito: **nessuna delle due aree esiste** (schema a 27 path invariato; probe con Bearer valido tutti 404: `newsletters`, `mailing`, `mailing-lists`, `email-lists`, `liste-email`, `campaigns`, `campagne`, `carts`, `carrelli`, `carrelli-abbandonati`, `abandoned-carts`, `subscribers`, `iscritti`, `marketing`).

- **B17 Mailing** — il modello dati però lo prevede già: il cliente espone `lista_email_id` in lettura (e non è nemmeno assegnabile: manca da `CustomerUpdateInput`). Servirebbero: CRUD liste email, gestione iscritti (+ stato consenso/GDPR), e idealmente campagne/invii. Anche solo liste+iscritti abiliterebbe automazioni esterne (l'invio può farlo un servizio terzo).
- **B18 Carrelli abbandonati** — nessuna risorsa carrello. Nota: non sono approssimabili con gli ordini `in_attesa_pagamento` (il carrello abbandonato muore prima del checkout e non diventa mai ordine; inoltre `/orders` non ha filtri). Servirebbe `GET /carts?abandoned=true&older_than=...` con prodotti, cliente/email se noto, e timestamp ultimo aggiornamento — è il dato chiave per le automazioni di recupero (mail "hai dimenticato qualcosa"), una delle leve e-commerce a ROI più alto.

### B13/B17/B18 + media. ✅ Settimo export 12/06 ~13:50 — punti, mailing, carrelli e libreria media

Il settimo export (= live, **36 path**, 17 operazioni nuove) chiude tutti i gap funzionali aperti. Tutto testato live:

- **B13 ✅ Punti fedeltà** — `GET/POST /customers/{id}/points` con delta ± e `motivo` (audit). Testato sul Cliente Demo: +100 ("Bonus benvenuto demo") → saldo 100; −20 ("Riscatto parziale demo") → saldo 80; **storico completo** con timestamp e campi `order_id`/`coupon_id`/`scadenza` predisposti. ⚠️ Nota semantica: `punti_totali` segue anche i delta negativi — se era inteso come totale storico maturato (per i tier) è da rivedere.
- **B17 ✅ Mailing** — `/email-lists` CRUD + `subscribers` (add/list/remove). Liste predefinite "clienti" e "newsletter"; creata "Lista Demo" (id 3) e iscritto il Cliente Demo. Design curato: add **idempotente** (riattiva iscrizioni disattivate), remove **soft-delete** per conservare lo storico consensi (GDPR), contatore `iscritti_attivi`. Manca (per ora) solo la parte campagne/invii: con liste+iscritti l'invio si può delegare a un servizio esterno.
- **B18 ✅ Carrelli** — `GET /carts` + dettaglio, con i filtri richiesti: `abbandonato`, `recuperato`, `email`, `older_than`. Il flag `abbandonato` è marcato da un job schedulato. Oggi 0 carrelli (arrivano dalle sessioni storefront) — filtri verificati (200).
- **Media ✅ (completa B15)** — `/media` con 4 cartelle gestite (`product_images`, `cat_images`, `blog`, `blog_cat_images`): list, upload base64 con `alt`, update (alt propagato agli usi correnti), delete (azzera i riferimenti). L'upload restituisce `valore_campo` da usare nei campi immagine: testato caricando `blog/articolo-demo.png` e impostandolo come `immagine_evidenza` dell'Articolo Demo ✅. Ora anche categorie e blog hanno la filiera immagini via API.
- **C4 ancora aperto 🔴** — ritestato: `/uploads/` continua a non essere servito (404 anche sui file appena caricati). Resta l'unico blocco della filiera immagini.
- **D6 🆕 (Printing Press, lato nostro)** — sulle route con **due path-param** (`/media/{folder}/{filename}`) il CLI generato mappa un solo argomento e costruisce l'URL sbagliato (`/media/product_images/product_images`). Via curl l'API funziona. Da segnalare upstream insieme a D1.

### B19. 🟡 Mancano template email, campagne e invio (verificato 12/06 ~14:15)

Con B17 risolto l'API copre il livello **dati** del mailing (liste + iscritti), ma manca tutto il livello **operativo**. Verificato live: schema a 36 path senza nulla in merito; probe con Bearer valido su `campaigns`, `campagne`, `templates`, `email-templates`, `mailings`, `invii`, `sends` → tutti 404.

Cosa manca, in concreto:

1. **Template email** — nessuna entità. Servirebbe CRUD `/email-templates`: `{nome, oggetto, contenuto_html, contenuto_testo, variabili}` con placeholder (es. `{{nome}}`, `{{prodotti_carrello}}`, `{{codice_sconto}}`) — stessa filosofia del `contenuto` HTML degli articoli.
2. **Campagne** — nessuna entità. Servirebbe CRUD `/campaigns`: `{nome, lista_id, template_id, oggetto, stato: bozza|programmata|inviata, data_invio}`.
3. **Invio** — nessun motore: né `POST /campaigns/{id}/send` (campagna a una lista) né un transazionale `POST /emails/send` (singolo destinatario — il pezzo che serve per il recupero carrello: template + cliente + variabili).
4. **Statistiche** — `GET /campaigns/{id}/stats`: inviate, aperture, click, bounce, disiscrizioni. Senza, il ROI delle campagne non si misura.
5. **Automazioni/trigger** — regola "carrello abbandonato da N ore → invia template X" lato server, **oppure** (più semplice e già in roadmap agente AI) webhook outbound `cart.abandoned` per orchestrare l'invio dall'esterno.

Priorità suggerita: 1 + 3-transazionale bastano per il recupero carrelli (la leva a ROI più alto); 2+4 per le newsletter; 5 elimina il polling. Nel frattempo il flusso è costruibile esternamente: dati da `/carts` e `/email-lists`, codice sconto monouso da `/discount-codes`, invio delegato a un provider (SMTP/Resend/SendGrid).

### B19-bis. ✅ Ottavo export 12/06 ~15:30 — motore mailing completo + gestione token

L'ottavo export (= live, **45 path**, 15 operazioni nuove) implementa B19 quasi per intero, più un bonus. Testato live:

- **Template ✅** — `/email-templates` CRUD (`nome`, `oggetto`, `contenuto_html` obbligatori + `contenuto_testo`), placeholder `{{chiave}}`. Creato "Recupero Carrello Demo" (id 1) con `{{nome}}`, `{{prodotti_carrello}}`, `{{codice_sconto}}`, `{{link_carrello}}`.
- **Transazionale ✅ (API) / ⚠️ SMTP** — `POST /emails/send`: destinatario per `cliente_id` o `email`, contenuto da `template_id`+`variabili` o diretto. Invio sincrono via "SMTP Marketing". L'endpoint valida e funziona, ma sul tenant demo risponde `400 SEND_FAILED: Nessuna configurazione SMTP Marketing` → 🆕 **C5: configurare l'SMTP Marketing del tenant** (da pannello).
- **Campagne ✅** — `/campaigns` CRUD: `liste_ids` multiple, contenuto copiato dal `template_id` alla creazione, stati `bozza→inviando→…`, update/delete rifiutati durante l'invio. Creata "Campagna Demo" (id 1) su Lista Demo e lanciato l'invio: coda costruita (`totale: 1, in_coda: 1`).
- **Stats ✅ (parziali)** — `GET /campaigns/{id}/stats`: `totale`, `inviate`, `errori`, `in_coda`, stato e data invio. **Aperture e click non tracciati** (dichiarato): per il ROI completo servirebbe il tracking — resto di B19 insieme ai trigger/webhook `cart.abandoned`.
- **Bonus: gestione token ✅** — `GET /auth/tokens` (metadati: client, IP, creazione, ultimo uso, flag `current`) e `DELETE /auth/tokens/{id}` (revoca immediata, scopata per chiave). Chiude la riserva di B2 sulla non-revocabilità: testato revocando i 16 token accumulati nei test (ne resta 1, quello attivo).
- ⚠️ Nota dal test: la coda della campagna resta `in_coda: 1, inviate: 0` per la stessa ragione di C5 (niente SMTP) — da rifare il giro quando configurato.

### SWCSS + C6. Pagine HTML in stile SWCSS via API: si può — ma gli update non vanno live (12/06 ~15:40)

**SWCSS non è un "metodo" dell'API** (zero riferimenti nello schema; `template_name` è una stringa libera, default `page.html`): è il sistema di classi CSS del tema (`sw-hero`, `sw-wrap`, `sw-eyebrow`, `sw-section`, `sw-cta`… — 44 classi distinte nella homepage), definito in `/static/css/cms.css`, **caricato anche dalle pagine create via API**. Quindi le pagine SWCSS si creano via API scrivendo il markup giusto nel `content`. **Dimostrato**: pagina di test creata con hero SWCSS → renderizzata subito correttamente sul pubblico (poi rimossa).

**C6 🆕 🟡 — gli update al contenuto di pagine esistenti non vanno live.** `PUT /pages/{id}/content` salva (l'API rilegge il contenuto nuovo) ma il pubblico continua a servire la versione precedente: classico **template loader cached di Django** che non viene invalidato. Le pagine nuove invece compilano fresco al primo render. Fix lato Swerpify: invalidare la cache template sull'update del content (o disattivare il cached loader per i template per-istanza).

**Manca inoltre (nice-to-have per agenti):** un endpoint `GET /page-templates` che elenchi i template disponibili (oggi `template_name` è alla cieca) e una documentazione/catalogo delle classi SWCSS — senza, un agente può solo copiare i pattern dalla homepage.

### B21. Variazioni prodotto: funzionano via API ma il modello non è documentato (test 12/06 ~16:40)

**Test completo riuscito** (entità ZZTEST, cleanup totale): il modello variazioni c'è e funziona, ma lo spec non lo documenta — l'ho ricavato empiricamente:

- **Padre**: `tipo_prodotto: "variabile"` (enum NON documentato nello spec v2 — il v1 diceva `semplice | variabile | custom_box`; v2 ha solo `default: "semplice"`).
- **Variazione**: prodotto figlio con `prod_principale_id: <id padre>` e `valori_attributi: [{"attributo": "Colore", "valore": "Rosso"}, ...]` — accettato e persistito al primo colpo, con prezzi e giacenze propri. Il `tipo_prodotto` della variazione resta `semplice`.
- **Attributi liberi**: nomi/valori arbitrari, nessun registro attributi via API (probe `attributes`/`attributi`/`variants` → 404).
- **Semantica `include_variants`**: di default le variazioni sono **escluse** dalla lista (catalogo pulito); con `include_variants=true` appaiono **piatte** accanto ai padri.

**Gap da segnalare:**
1. Lo spec v2 non documenta né l'enum di `tipo_prodotto` né la forma di `valori_attributi` (`items: {}`) — senza il nostro test, impossibile usarli.
2. **Manca il modo di ottenere le variazioni di un padre**: il dettaglio padre non ha campo `variazioni`, e non esiste filtro `?prod_principale_id=` sulla lista → oggi bisogna scaricare tutto con `include_variants=true` e filtrare client-side. Servirebbe il filtro o un campo annidato nel dettaglio.
3. Nessun endpoint per il registro attributi (definizioni condivise tipo "Taglia: S/M/L") — con attributi liberi si rischiano incoerenze ("Rosso" vs "rosso").

### Nono export 12/06 ~16:40 — layer design completo. E con il compile si chiudono C2, C3, C4 e C6 ✅

Il nono export (= live, **52 path**) espone il layer design/grafica e i cataloghi mancanti. Testato tutto:

- **`GET /design/swcss-guide`** — guida markdown operativa per agenti: flusso completo pagina+CSS+compile, architettura layer (base non toccabile / `pagine-sistema/*` / `custom`), regole del design system, utility disponibili, breakpoint, errori tipici. Esattamente il "catalogo documentato SWCSS" chiesto nella sezione SWCSS/C6.
- **`GET /page-templates`** — 9 template di sistema + 3 preset (`blank1`, `blank2`, `home_base-swcss`). Chiude il "template_name alla cieca".
- **`/design/css`** — list/get/put/delete dei sorgenti CSS per sezione (con protezione dei file `predefinito`); **`POST /design/compile`** rigenera i bundle con tree-shaking (1,4s, stessa compilazione del pannello Grafica).
- **`GET /attributes`** — registro attributi (sola lettura, oggi vuoto sul tenant): chiude parte di B21; restano filtro `prod_principale_id` e doc del modello variazioni.
- **🔑 La scoperta che chiude tutto: le modifiche vanno live solo dopo `POST /design/compile`.** Eseguito il compile: la Pagina Demo è uscita in versione SWCSS (C6 ✅ — non era un bug ma un passo non documentato, ora documentato nella guida), le tre policy sono tornate **200** (C3 ✅), il **blog è live** con l'Articolo Demo renderizzato su `/blog/categoria-articoli-demo/articolo-demo/` (C2 ✅), e **`/uploads/` è servito**: immagine articolo e immagine prodotto rispondono 200 image/png (C4 ✅).

Stato storefront dopo il compile: homepage, shop, scheda prodotto, categoria, blog, articolo, policy, pagina demo SWCSS — **tutto 200**. 

### Decimo export 12/06 ~17:30 — gestione JavaScript per-pagina ✅

`/design/js` (list/get/put/delete, = live, **54 path**): file JS per-istanza in `/static/js/custom/` — `<slug>.js` viene **caricato automaticamente** dalla pagina con quello slug, con `defer` e cache-buster su mtime, **senza compilazione** (live subito, a differenza del CSS). Per JS condiviso: nome non-slug + `<script src>` nel contenuto.

**Testato:** spostato il click-to-copy della landing `/scopri-prodotto-demo/` dallo script inline a `design js-put scopri-prodotto-demo.js` → la pagina lo carica da sola (`<script src=".../scopri-prodotto-demo.js?v=..." defer>`), file servito 200. La risposta del PUT include `autoload_slug` — ottimo per gli agenti. Con questo il layer design è completo: pagine + contenuto + CSS + JS + media + compile, tutto via API.

---

### B26. 🟡 Il tree-shaking del bundle `prodotto` non vede le descrizioni → impossibile stilare le schede prodotto via design CSS (14/06)

**Contesto.** Abbiamo un componente CSS condiviso che stila il campo `descrizione` dei prodotti-corda (lead, card "punti di forza", badge, griglia specifiche) con tema-colore per prodotto, sulla falsariga delle landing CMS. Sulle **pagine CMS funziona** perché il compile del bundle `cms` scansiona il `content` della pagina (le classi usate lì vengono conservate). Sulle **schede prodotto NO**.

**Comportamento osservato** (tenant Gevi, prodotto `string-project-armour` id 103, file `PUT /design/css/prodotto/corde-descrizione.css` + `POST /design/compile`):
- La scheda prodotto carica **solo `/static/css/prodotto.css`** (non `cms.css`), quindi il CSS deve stare nella sezione `prodotto`.
- Il tree-shaker del bundle `prodotto` **non scansiona il campo `descrizione`** del prodotto (né, presumibilmente, quello delle categorie). Nel CSS compilato sopravvivono **solo** le regole la cui chiave (selettore più a destra) è un **elemento semantico** — es. `.sw-cdesc h2`, `p.sw-cdesc__lead`, `article.sw-cdesc__card`, `.sw-cdesc__card p`, `.sw-cdesc__badge svg`. Vengono **eliminate**:
  - i selettori di **sola classe** (`.sw-cdesc__grid`, `.sw-cdesc__specs`, `.sw-cdesc__spec`),
  - le regole con chiave su `div`/`dl`/`dt`/`dd`,
  - **il blocco tema-colore** (`.sw-cdesc--<corda> { --acc: … }` / `div.sw-cdesc--<corda>`), che è il pezzo cruciale: senza, nessuna variabile colore viene impostata.

**Verifiche fatte** (per escludere cause banali):
1. Ancorare ogni regola a un elemento (`div.sw-cdesc__grid`, `dl.sw-cdesc__spec-grid`) **non basta**: `div`/`dl` vengono scartati comunque; solo alcuni elementi (h2/h3/p/article/svg) sopravvivono.
2. Ri-salvare la `descrizione` **prima** del `compile` non cambia nulla → non è un problema di ordine/timing, è proprio che le descrizioni prodotto non sono nel set scansionato.
3. La sorgente del file (`GET /design/css/prodotto/<file>`) è completa: è il **compile** che pota.

**Impatto.** Non è possibile applicare un componente di design (classi custom + variabili tema) alle schede prodotto via il layer design, restando dentro le regole (niente `<style>`/`style=` inline nel contenuto). Blocca la riprogettazione delle 8 schede corda in stile coerente con le landing.

**Richieste (una qualsiasi sblocca):**
- **(preferita)** includere il campo `descrizione` di prodotti/categorie nel set di HTML scansionato dal tree-shaking del bundle `prodotto` (come già si fa col `content` delle pagine nel `cms`); **oppure**
- una **safelist** esplicita (file/sezione o direttiva-commento) per classi da non potare; **oppure**
- una **sezione CSS non-purgata** caricata sulle schede prodotto.

**Nota collaterale (positiva):** `ProductUpdateInput` è un update **parziale** sicuro (nessun campo `required`, `additionalProperties:false`): `PUT /products/{id}` con solo `{descrizione, lang}` aggiorna quel campo senza azzerare gli altri (verificato e poi ripristinato l'originale).

---

## C. Tenant demo MaoDemo

### C2. 🟢 Link `/blog/` morto nel menu del tenant demo

Il menu di navigazione dello storefront MaoDemo linka `/blog/`, ma la pagina risponde 404 (esce la pagina di errore del sito). O il blog del tenant non è stato configurato, o il modulo è disattivo: in entrambi i casi il link nel menu non dovrebbe comparire.

### C3. 🔴 Storefront: 500 Server Error su shop, pagina categoria e pagine `page.html` (11/06 ~15:30)

Rilevato durante il seeding dei dati demo. Pagine pubbliche del tenant MaoDemo:

| URL | Esito |
|---|---|
| `/` (homepage), `/carrello/`, `/mio-account/` | 200 ✅ |
| `/negozio/` (shop) | **500** |
| `/negozio/categoria-ecommerce-demo/` (categoria esistente) | **500** |
| `/negozio/slug-inesistente/` | 404 (routing corretto) |
| `/privacy-policy/`, `/termini-e-condizioni/`, `/cookie-policy/` (template `page.html`) | **500 tutte e tre** |

**Non dipende dai dati creati via API**: privacy e termini non sono mai stati toccati e danno comunque 500; nascondere il prodotto demo (`stato: 0`) non cambia l'esito di `/negozio/`. Il pattern (route corrette, crash in render su più template) punta a una regressione dei template lato server — plausibilmente legata ai deploy multipli di oggi. Ipotesi alternativa solo per lo shop: il template potrebbe non gestire categoria/prodotto senza immagine (creati via API, dove peraltro non esiste un modo per caricare immagini — `foto` è solo in lettura su ProductInput).

**Da investigare lato Swerpify** (i log server diranno subito quale eccezione è).

### C1. 🟡 Dati demo quasi vuoti

Censimento live: **0 prodotti, 0 ordini, 2 clienti**, pagine CMS non censite. Impossibile collaudare a fondo update/delete/batch, paginazione e ricerca senza prima fare seeding.

**Fix:** popolare il tenant con un set di dati demo (anche via i comandi `batch` del CLI appena generato).

**Seeding avviato l'11/06 ~15:30** (entità persistenti, verificate via API):
- Categoria id 2 "Categoria Ecommerce Demo" (slug `categoria-ecommerce-demo`, blocco SEO completo impostato)
- Prodotto id 2 "Prodotto Demo" (SKU `DEMO-001`, qty 10, prezzo 19,90 € su listino 1 "default", collegato alla categoria 2 come principale)

Non creabili via API (endpoint assenti, B10): articolo demo e categoria articoli — `POST /articles` → 404. Da creare dal pannello.

---

## D. Lato nostro — CLI generato e toolchain

### D1. 🟡 Bug Printing Press: comandi principali nascosti nell'help

Il generatore (printing-press 4.6.1) ha emesso i 4 comandi risorsa principali con `Hidden: true` (`internal/cli/products.go:14`, e lo stesso in `orders.go`, `customers.go`, `pages.go`). Risultato: **`products`, `orders`, `customers`, `pages` non compaiono in `--help`**, pur funzionando se digitati (e sono elencati da `swerpicommerce-pp-cli api`). Nei CLI stampati in precedenza (es. `swdev`) le risorse sono regolarmente visibili.

**Fix:** bug da segnalare upstream alla Printing Press (è una modifica "machine", non del singolo CLI). Workaround locale possibile (togliere `Hidden: true` dai 4 file), ma sono file `DO NOT EDIT` e un regen li sovrascrive.

### D2. 🟡 Go di sistema 1.26.3 con 2 vulnerabilità stdlib

Il gate `govulncheck` fallisce col Go di sistema: **GO-2026-5039** (net/textproto) e **GO-2026-5037** (crypto/x509), corrette in go1.26.4.

**Workaround applicato:** pin `toolchain go1.26.4` nel `go.mod` del CLI (Go scarica il toolchain da solo). ⚠️ Un futuro `generate --force` **rimuove il pin**: va rimesso.
**Fix definitivo:** aggiornare il Go di sistema a ≥1.26.4.

### D3. 🟢 Il CLI non rinnova il token da solo

Alla scadenza (1h) va rifatto a mano:

```bash
./swerpicommerce-pp-cli swerpicommerce-auth --api-id <KEY> --api-secret <SECRET> --agent
./swerpicommerce-pp-cli auth set-token <token>
```

Candidato naturale a un comando novel di auto-refresh (legge api_id/api_secret da env, rinnova e salva). Dipende anche da B2.

### D4. 🟢 Attribuzione del generatore vuota

`git config user.name` e `github.user` non sono impostati: il generatore ha emesso copyright "user" e nessuna attribuzione printer (solo warning, nessun impatto funzionale).

### D5. 🟢 Vecchio `swerpify-commerce-cli` obsoleto

`dev/generated/swerpify-commerce-cli` (e il binario `dev/swcommerce`) puntano alla superficie v1 che su questo tenant non esiste. Da archiviare o eliminare per evitare usi per errore.

---

## Riepilogo priorità

| # | Problema | Severità | Di chi | Stato (11/06 pom.) |
|---|---|---|---|---|
| A1 | Export spec v1 etichettato v2 (file inutilizzabile) | 🔴 | Swerpify (pannello export) | ✅ risolto |
| A2 | Credenziali in chiaro nell'export (+ rotazione consigliata) | 🔴 | Swerpify + noi | ✅ risolto (resta solo x-api-id, non segreto) |
| B3 | CRUD clienti incompleto (no get/update/delete) | 🟡 | Swerpify (API) | ✅ risolto (restano pages create/delete, orders delete) |
| B2 | Token 1h senza refresh | 🟡 | Swerpify (API) | ⚠️ cambiato: ora i token non scadono (`expires_at: null`) — confermare che sia voluto |
| B1 | Server URL relativo nello schema | 🟡 | Swerpify (API) | ✅ risolto |
| B4 | 404 API in HTML | 🟡 | Swerpify (API) | ✅ risolto (ora JSON) |
| A3 | `api_key` vs `api_id`, Basic vs Bearer | 🟡 | Swerpify (export/doc) | ✅ risolto |
| — | Chiave demo senza permessi `clienti.cliente.update/delete` | 🟡 | Swerpify (pannello) | ✅ risolto in giornata |
| C1 | Tenant demo vuoto | 🟡 | noi/Swerpify (seeding) | aperto |
| D1 | Comandi nascosti nell'help del CLI | 🟡 | Printing Press (upstream) | aperto |
| D2 | Go di sistema vulnerabile, pin toolchain fragile | 🟡 | noi (aggiornare Go) | aperto |
| B8 | Prodotti senza campi meta/SEO (pagine e categorie ok) | 🟡 | Swerpify (API) | ✅ risolto ~16:40 (blocco SEO aggiunto a ProductInput, testato live sul Prodotto Demo) |
| B9 | PUT ignora silenziosamente i campi sconosciuti | 🟡 | Swerpify (API) | 🆕 aperto (test 11/06 pom.) |
| B10 | Articoli blog non esposti dall'API (meta non gestibili) | 🟡 | Swerpify (API) | ✅ risolto ~16:30 (CRUD + SEO completi, testati) |
| C2 | Link `/blog/` morto nel menu; frontend blog 404 anche con articolo pubblicato | 🟢→🟡 | Swerpify (tenant/storefront) | ✅ risolto 12/06 ~16:50 (blog live, articolo renderizzato) |
| C3 | Storefront 500 su shop, pagina categoria e pagine `page.html` | 🔴 | Swerpify (server/template) | ✅ risolto 12/06 ~16:50 (tutte 200 dopo compile/fix team) |
| — | Niente upload immagini prodotto/categoria via API (`foto` solo lettura) | 🟢 | Swerpify (API) | 🆕 aperto |
| B5 | Envelope risposte incoerente | 🟢 | Swerpify (API) | ✅ risolto |
| B6 | openapi.json pubblico senza auth | 🟢 | Swerpify (decidere) | aperto |
| B7 | Manca endpoint whoami/verify | 🟢 | Swerpify (API) | ✅ risolto (`GET /auth/me`) |
| B12 | Niente codici sconto/coupon (solo sconto ad-hoc per ordine) | 🟡 | Swerpify (API) | ✅ risolto ~18:30 (CRUD testato, DEMO10 creato) |
| B13 | Punti fedeltà in sola lettura via API | 🟡 | Swerpify (API) | ✅ risolto 12/06 (adjust ± con motivo e storico, testato) |
| B14 | Pagine CMS: no create/delete, HTML non gestibile (template-driven) | 🟡 | Swerpify (API/doc) | ✅ risolto ~18:30 (create+content testati, pagina pubblica ok) |
| B15 | Upload media assente (immagini solo da pannello) | 🟡 | Swerpify (API) | ✅ prodotti / ⚠️ serving rotto (C4); categorie/articoli ancora senza |
| C4 | File immagine caricati via API non serviti (404 su `/uploads/...`) | 🔴 | Swerpify (storage/nginx) | ✅ risolto 12/06 ~16:50 (immagini servite 200 image/png) |
| B16 | PUT/DELETE immagine dichiarati nello spec ma 405 (route solo GET); errore in HTML non JSON | 🟡 | Swerpify (API) | ✅ risolto ~19:10 (PUT e DELETE funzionano, errori in JSON; upload `main` sostituisce e ripulisce la precedente) |
| B17 | Mailing/newsletter non esposti (liste email, iscritti, campagne) | 🟡 | Swerpify (API) | ✅ risolto 12/06 (liste+iscritti testati; mancano solo campagne/invii) |
| B18 | Carrelli (e carrelli abbandonati) non esposti | 🟡 | Swerpify (API) | ✅ risolto 12/06 (lettura con filtri abbandonato/recuperato/email/older_than) |
| B19 | Mancano template email, campagne, invio (+ stats e trigger) | 🟡 | Swerpify (API) | ✅ quasi tutto risolto ~15:30 (template, transazionale, campagne, stats parziali, revoca token); restano tracking aperture/click e trigger `cart.abandoned` |
| C5 | SMTP Marketing non configurato sul tenant demo (invii falliscono) | 🟡 | Swerpify (pannello tenant) | 🆕 aperto (15:30) |
| C6 | Update content pagine non va live (cache template Django non invalidata) | 🟡 | Swerpify (backend) | ✅ chiarito 12/06: by design — serve `POST /design/compile`, ora documentato nella swcss-guide |
| B20 | Doc spec errata: placeholder documentati come `{{chiave}}` ma il motore usa `{chiave}` | 🟢 | Swerpify (spec/doc) | 🆕 aperto (12/06 ~16:15) — in ≥5 punti: descrizione `/emails/send`, `variabili`, campi oggetto/contenuto_html dei template |
| B21 | Variazioni: modello non documentato (enum tipo_prodotto, forma valori_attributi); manca filtro `prod_principale_id` e registro attributi | 🟡 | Swerpify (API/doc) | parz. risolto: `GET /attributes` aggiunto (vuoto sul tenant); restano doc modello e filtro padre |
| D6 | CLI: route con 2 path-param costruiscono URL errato (`/media/{folder}/{filename}`) | 🟡 | Printing Press (upstream) | 🆕 aperto (12/06) — workaround: curl |
| D3 | No auto-refresh token nel CLI | 🟢 | noi (comando novel) | superato da B2 (token senza scadenza) |
| D4 | Attribuzione generatore vuota | 🟢 | noi (git config) | aperto |
| D5 | Vecchio CLI commerce obsoleto | 🟢 | noi (pulizia) | aperto |

---

*Tutti i punti sono stati verificati live l'11/06/2026 con chiamate reali al tenant MaoDemo (sole letture + emissione token; nessuna scrittura sui dati).*

## Osservazioni dal tenant Gevi/String Project (12/06 sera — creazione pagina v2 via API)

| ID | Problema | Gravità | Di chi | Stato |
|---|---|---|---|---|
| B22 | Template tag custom (`{% get_recensioni %}`) → 500 su pagine create via API anche dopo `PUT pages/{id}` con `contexts` identici alla pagina originale + re-PUT del content + compile. Funziona solo rimuovendo il tag dal content. Da chiarire col team come attivare i contexts sulle pagine nuove. | 🟡 | Swerpify (backend) | 🆕 aperto (12/06 ~21:50) |
| B23 | Routing pagine legato a `sitemap`: con `sitemap:false` la pagina creata via API non è raggiungibile (404). Impossibile avere una pagina di test/preview non in sitemap. Workaround: `sitemap:true` + `index:false`. | 🟡 | Swerpify (backend) | 🆕 aperto (12/06 ~21:40) |
| B24 | Propagazione lenta e incoerente dopo create/compile: per minuti lo stesso URL alterna 200/404/500 a seconda del worker che risponde (URLconf/template non ricaricati in modo atomico su tutti i worker). | 🟡 | Swerpify (infra) | 🆕 aperto (12/06 ~21:50) |

Contesto: pagina di confronto `string-project-magic-v2` (id 254, `index:false`,
`sitemap:true` forzato per il routing B23, `no_cache:true`) creata per i fix
dell'audit accessibilità — vedi `spnew-cli/AUDIT-PAGINA-MAGIC-IT.md`.

## Cache pagine vs API (13/06 — iterazione design v2 Gevi)

| ID | Problema | Gravità | Di chi | Stato |
|---|---|---|---|---|
| B25 | Con `no_cache:false` la pagina è cachata lato app con `max-age=84600` (~23,5h) e `POST /design/compile` NON invalida questa cache (rigenera solo i bundle CSS/design): dopo `pages content update` + compile la pagina continua a servire la versione precedente. Né un PUT sul record pagina né un query-param bustano la cache. Manca nell'API un endpoint di **purge/invalidate cache** (o un flag su compile) per singola pagina. Unica leva via API: toggle `no_cache` true→compile→false (durante `true` la entry è bypassata, tornando a `false` si ricrea fresca) — ma `no_cache:true` causa i 404 ballerini (B24). Il "compila dal backend" del pannello evidentemente fa anche un purge che l'API non espone. | 🟡 | Swerpify (API) | 🆕 aperto (13/06) |

## Tree-shaking design su schede prodotto (14/06 — restyle descrizione corde Gevi)

| ID | Problema | Gravità | Di chi | Stato |
|---|---|---|---|---|
| B26 | Il tree-shaking del bundle `prodotto` **non scansiona il campo `descrizione`** dei prodotti (il `cms` invece scansiona il `content` delle pagine): un CSS custom in `prodotto/` viene potato di tutte le regole che non hanno per chiave un **elemento semantico** (h2/h3/p/article/svg). Vengono eliminati selettori di sola classe, regole su `div`/`dl`/`dt`/`dd` e — soprattutto — i blocchi **tema-colore** (`.sw-cdesc--<corda>{--acc:…}`), rendendo impossibile stilare le schede prodotto via il layer design senza ricorrere a stile inline (vietato). La scheda carica solo `prodotto.css`. Verificato: ancorare i selettori agli elementi non basta (div/dl scartati comunque); ri-salvare la descrizione prima del compile non cambia nulla (non è timing). **Richiesta:** scansionare le descrizioni prodotto/categoria nel tree-shake, **oppure** safelist, **oppure** sezione CSS non-purgata sulle schede. Dettaglio completo: sezione **B26** sopra. | 🟡 | Swerpify (design build) | ✅ risolto (verificato 24/06 su Armour id 103: il tree-shaker `prodotto` ora scansiona la `descrizione`, sopravvivono sola-classe + blocchi tema-colore) |

## Multilingua — documentazione API (re-check 30/06, schema Gevi v2 `gevi-srl-openapi (2).json`)

Lo schema ora espone una sezione `### Multilingua` dedicata in `info.description` + descrizioni complete sui campi. Modello confermato: **per-record** (ogni traduzione = riga separata con `lang`; nessun record padre/figli). Slug **univoco per lingua** per pagine/articoli/categorie-articoli; **eccezione**: categorie prodotto = slug **globale**.

| ID | Punto | Stato |
|---|---|---|
| B27 | **Documentazione `lang` / `?lang`** — il campo `lang` (Product/Page/Article/ArticleCategory Input) ha ora descrizione (es. `it`/`en`, default = lingua predefinita del sito); il query param `?lang` su `/products`,`/pages`,`/articles`,`/categories`,`/article-categories`,`/attributes` è documentato: **filtro esatto, nessun fallback**, omesso = tutte le lingue. Prima erano entrambi senza descrizione. | ✅ risolto (30/06) |
| B28 | **Collegamento traduzioni — PAGINE CMS** — campo `alternates` (`[{alternate_lang, alternate_page_id}]`), impostabile **solo in `PUT /pages/{id}`** (non in POST), semantica PUT (l'array sostituisce tutto; `[]` rimuove; omesso = invariato), restituito in lettura con `?include_alternates=true`. File contenuto per-lingua: `<slug>.html` (default) / `<slug>_<lang>.html`. | ✅ risolto (30/06) |
| B29 | **Collegamento traduzioni — PRODOTTI, ARTICOLI, CATEGORIE** — `alternates` ora esposto **su tutte le risorse**: `ProductUpdateInput` (`alternate_product_id`), `CategoryUpdateInput` (`alternate_category_id`), `ArticleUpdateInput` (`alternate_articolo_id`), `ArticleCategoryUpdateInput` (`alternate_categoria_id`), oltre a `PageUpdateInput` (`alternate_page_id`). Solo in `PUT` (non POST), letto con `?include_alternates=true` (default). La scrittura costruisce una **mesh bidirezionale completa** (IT→EN crea anche EN→IT; con IT↔EN↔FR vengono collegati tutti tra loro). | ✅ risolto (schema 3, 30/06) |
| B30 | **Codici lingua** — i campi `lang` restano **senza `enum`** e non c'è un endpoint dedicato per elencare le lingue configurate del tenant. **Re-check 04/07**: `GET /header-footer` ora restituisce di fatto l'elenco (`lingue: [{slug, predefinita}]` + `lingue_senza_record`) — utilizzabile come workaround di lettura, ma è un posto non ovvio. **Richiesta (minore, ancora valida):** `enum` sui campi `lang` o un `GET /languages` esplicito. | 🟡 aperto (re-check 04/07) |

## Slug annidati e POST /pages — test 03/07 su tenant swebby-new (122-h000726)

| # | Problema | Stato |
|---|---|---|
| B31 | **Slug con `/` accettati dall'API ma rotti sul frontend** — `POST /pages` accetta slug contenenti `/` (es. `zztest-parent/zztest-child`), la pagina viene creata e listata con lo slug intatto, ma l'URL pubblico risponde **500** dopo il compile (anche se esiste una pagina con lo slug del segmento padre; una pagina piatta identica → 200). Il modo giusto di fare gerarchie è **`pagina_padre_id`** (vedi B33): l'API dovrebbe quindi **rifiutare con 400 gli slug con `/`** invece di creare pagine irraggiungibili. Il campo `pagina_padre_id` è inoltre **senza description** nello schema. | 🔴 aperto (03/07) |
| B32 | **`POST /pages` può rispondere 500 avendo però creato la pagina** — primo tentativo → HTTP 500, ma la pagina risulta creata (il retry automatico del CLI fallisce con `SLUG_IN_USE`). Errore non idempotente: chi fa retry su 500 (il CLI lo fa di default) produce falsi negativi. Riprodotto 2/2 con slug contenenti `/` (mai visto con slug piatti). | 🟡 aperto (03/07) |
| B33 | **Gerarchie pagine: funzionano via `pagina_padre_id`, ma l'URL piatto resta attivo senza canonical** — creando la figlia con slug piatto + `pagina_padre_id` del padre, l'URL annidato `/padre/figlia/` risponde 200 e la **sitemap emette quello come ufficiale** ✅. Però la stessa pagina risponde 200 **anche** su `/figlia/` (l'alias piatto non redirige) e le pagine non emettono `<link rel="canonical">` → contenuto duplicato agli occhi dei motori. **Richiesta:** 301 dall'alias piatto all'URL annidato, oppure canonical. | 🟡 aperto (03/07) |
| B34 | **A11y dei template tema (header/nav)** — axe 4.12 (WCAG 2.1 AA + best-practice) su una pagina CMS pulita segnala 4 violazioni tutte del tema, nessuna del contenuto: `landmark-no-duplicate-banner` (`#header_basic`), `landmark-unique` (nav principale duplicata), `list` (il selettore lingua `.sw-mobile-nav-list` ha figli non-`li` dentro `<ul>`), `region` (skip-link fuori dai landmark). Inoltre il tema referenzia `/static/img/uploads/favicon.ico` che è 404 su tenant nuovo (errore console su ogni pagina). | 🟡 aperto (03/07) |
| B35 | **Impostazioni grafiche (colori del tema) non esposte via API** — i token del layer base erano scrivibili solo dal pannello. **Risolto in giornata**: aggiunti `GET/POST /design/colors` + `GET/PUT/DELETE /design/colors/{id}` (sui colori `sistema: true` solo il `valore` è modificabile, slug protetto — semantica giusta) e `GET /design/variables` (token di sistema in sola lettura: scala tipografica, pesi, raggi, breakpoint estesi fino a `--4xl`). Documentazione degli endpoint ottima. Verificato live su swebby-new: palette brand impostata via API + compile → token nel bundle. Bonus dello stesso rilascio: nuova sezione CSS **`globale/`** (fallback sito-intero, cascata base→globale→sezione→custom) e guida SWCSS aggiornata (215→264 righe). NB: il CLI generato è ora indietro di questi endpoint → serve una regen. | ✅ risolto (03/07 pomeriggio) |
| B36 | **Logo non gestibile via API** — il logo del tema è un file statico `/static/img/uploads/logo_black.svg` cablato nei template header (caricabile solo dal pannello); l'API media non lo raggiunge (`folder` limitato a `cat_images`/`blog`/`blog_cat_images`) e **non accetta SVG**. Workaround: template header custom con logo inline. **Richiesta:** endpoint per gli asset del tema (logo/favicon — il favicon peraltro è 404 su tenant nuovi, vedi B34) e supporto SVG nell'upload media. | 🟡 aperto (03/07) |
| B34-bis | **Follow-up a11y (03/07 sera)**: con header custom (swebby-new) 3 delle 4 violazioni sono eliminabili lato template — sticky senza `role="banner"` duplicato (basta un landmark `navigation`), nav sticky con `aria-label` distinto, selettore lingua rimosso (il `<ul>` con figli non-`li` è nel markup del selettore). Resta solo `region` sullo **skip-link in `base.html`** (sola lettura upstream): andrebbe spostato dentro un landmark o marcato diversamente. I template base upstream (`header_base`, `header_sticky_base`) contengono ancora i 4 difetti + alt "Logo nero String Project" nello sticky (refuso da fork). | 🟡 aperto (03/07) |
| B37 | **`PUT /fonts/assignments` non valida le chiavi** — una chiave inventata (`font_pippo_id`) viene accettata e persistita senza errore (merge cieco); inoltre i nomi dei campi tipografici validi non sono documentati da nessuna parte (la description elenca solo i prefissi-sezione) né enumerabili via API quando la mappa è vuota. Scoperti per tentativi: `font_titoli_id`/`font_testo_id` (globali, riscrivono `--font-sans` alla compilazione). **Richiesta:** validazione 400 su chiavi sconosciute + `GET` che restituisca l'elenco completo dei campi (anche non assegnati). | 🟡 aperto (04/07) |
| B39 | **Lingue del sito non creabili/attivabili via API** — la doc «Multilingua» dello schema conferma che i codici `lang` "sono gli slug delle lingue configurate nel pannello": tutta la filiera contenuti multilingua è via API (record per-lingua, `alternates` con mesh bidirezionale, `PUT /header-footer/{lang}`, `?lang=` sulle letture), ma il primo passo — attivare una nuova lingua sul sito — si fa solo dal pannello. Per un agente che deve costruire un sito multilingua end-to-end è l'unico anello mancante. **Richiesta:** `POST /languages` (o equivalente nelle impostazioni) per creare/attivare lingue, con flag `predefinita`. | 🟡 aperto (04/07) |
| B40 | **Blog: autore = tendina nel pannello ma stringa libera via API; byline assente nella pagina articolo** — il pannello articolo ha un **select Autore** (popolato presumibilmente dagli utenti del pannello), ma l'API espone `autore` come **stringa libera senza id/FK** (accetta qualunque testo, es. nomi inventati) e non c'è alcun endpoint per elencare gli utenti/autori disponibili. Il tema renderizza l'autore **solo nelle card della lista /blog/** ("Autore / data"); la **pagina articolo non lo mostra da nessuna parte** (né visibile, né `meta author`, né JSON-LD — il tema emette solo BreadcrumbList). Per l'EEAT la firma in pagina va aggiunta a mano (JSON-LD `NewsArticle.author` via `markups` + eventuale byline nel `contenuto`). **Richieste (enhancement):** endpoint per elencare gli autori selezionabili (allineare API e pannello, ed evitare stringhe non corrispondenti a utenti reali); autore visibile anche nel template articolo; in prospettiva anagrafica autori (bio, foto, pagina profilo). Test 05/07 su swebby-new (ZZTEST creato/verificato/eliminato). | 🟡 aperto (05/07) |
| B46 | **Pagine categoria blog: meta description del record non emessa** — le categorie articoli hanno `meta_description` (impostata via API), il `<title>` la usa (`meta_title` ✓), ma nell'head della pagina categoria la `<meta name="description">` è assente. Il campo esiste e il template non c'entra (l'head è di base.html): manca il passaggio dalla view. Nota positiva scoperta forkando: il contesto del template categoria espone l'oggetto **`categoria`** completo (usato per mostrare `categoria.descrizione` in banda). | 🟢 minore (06/07) |
| B44 | **hreflang vuoto per la lingua predefinita** — con le traduzioni collegate via `alternates`, il frontend emette i `<link rel="alternate">`: quello della lingua secondaria è corretto (`hreflang="fr"`) e c'è l'`x-default`, ma il link della lingua predefinita esce con **`hreflang=""`** (stringa vuota → attributo invalido, Google lo scarta). Atteso: `hreflang="it"`. Rilevato su swebby-new con coppia IT/FR (pagine 20↔65). | 🟡 aperto (05/07) |
| B45 | **`num_articoli` delle categorie blog conta doppio la categoria principale** — il contatore (sidebar blog, `GET /article-categories`) somma la FK `categoria_id` E la riga M2M `categorie`: un articolo con la principale in entrambe (che è ciò che si ottiene passando `categoria_id` + `categorie` completo al POST) viene contato 2 volte (verificato: sidebar a 26/42/32/14/16/4 contro 13/23/16/9/7/2 reali; la matematica FK+M2M coincide esattamente). La pagina categoria invece deduplica (l'articolo compare una volta sola e basta la FK). **Workaround applicato**: passare in `categorie` SOLO le secondarie. **Richiesta:** contare articoli distinti (FK ∪ M2M). | 🟡 aperto (06/07) |
| B47 | **Dati azienda del tenant non esposti via API** — il pannello conosce ragione sociale/denominazione del tenant (su swebby-new compariva come title di default "Vige SRL") ma non c'è NESSUN modo di leggerli via API: niente endpoint impostazioni negli 81 path, nessuna variabile di contesto nei partial (footer upstream usa solo slug_negozio/slug_account), template di sistema senza dati azienda, pagine legali preset vuote sul tenant nuovo. Sono dati che servono di continuo agli agenti: footer, JSON-LD Organization, pagine legali, email. **Richiesta:** `GET /site-info` (o /settings/azienda) read-only con ragione sociale, P.IVA, indirizzo, contatti, +eventuale set via PUT; bonus: esporli anche come variabili di contesto nei template (es. `{{ azienda.ragione_sociale }}`) così i partial li usano nativamente. Verificato 07/07 su tenant 122-h000732. **RISOLTA 08/07**: aggiunto `GET /site-info` (schema SiteInfo: ragione_sociale, indirizzo completo, P.IVA, CF, telefono, email, REA, nome/url sito — read-only, modifica dal pannello) E le variabili di contesto globali `{{ dati_azienda.<campo> }}` nei template. Nota d'uso: dall'08/07 le variabili risolvono OVUNQUE (partial E template-contenuto delle pagine — il limite iniziale sui contenuti è stato fixato in giornata). | ✅ risolta (08/07) |
| B41 | **Nessun motore di redirect (301) gestibile** — né via API né (a quanto risulta) dal pannello. Caso concreto: migrazione blog swebby.it → piattaforma, 64 articoli che passano da `dominio/<slug>/` (WordPress, root) a `/blog/<slug>/`: al cambio dominio senza 301 si perde l'equity SEO accumulata. Vale per qualunque migrazione da altri CMS. **Richiesta:** risorsa `/redirects` (from, to, code 301/302) applicata dal router del frontend prima del 404. | 🔴 aperto (05/07) |
| B42 | **Template articolo blog: forkabile ma NON attivabile** — ⬆️ *aggiornamento 06/07*: la piattaforma ora espone l'area **`pagine_sistema`** in `/design/templates` (+`GET /page-templates` e `PUT /page-templates/{tipo}`, +`templates-guide`) — ottimo. Il fork funziona: `PUT .../pagine_sistema/blog-articolo-swebby.html` → 201. **Ma il render dell'articolo non passa dal record `PagineSistema`**: nessun tipo valido per assegnare la variante (provati `blog-articolo`, `articolo`, `blog_articolo`, `blog-singolo`, `articolo-blog` → tutti 404 NOT_FOUND; il tipo `blog` governa solo la LISTA/blog-home.html). Quindi il template articolo resta di fatto immutabile anche dal pannello (stessa tabella). Restano i difetti upstream: card lista senza immagine evidenza, niente byline autore (B40), contenuto avvolto in un `<p>` (invalido coi block: il browser lo spezza). **Richiesta:** aggiungere il tipo `blog-articolo` a PagineSistema (una variante è già pronta sul tenant swebby-new: `blog-articolo-swebby.html` con autore in testata e wrapper corretto). | 🟡 aperto (agg. 06/07) |
| B43 | **`<link rel="canonical">` e Open Graph assenti su tutto il frontend** — nessuna pagina (CMS, articoli, prodotti) emette canonical né meta `og:*`/`twitter:*`. Il canonical pesa doppio dove esistono alias (vedi B33: la pagina figlia risponde sia su URL annidato che piatto); gli OG mancanti degradano ogni condivisione social (niente titolo/immagine card). Gli articoli blog con `url_diretto` invece hanno un solo URL (il percorso con categoria fa 404 — ✅ niente alias). **Richiesta:** canonical automatico sull'URL primario + og:title/description/image/type (+ twitter:card) da meta e immagine in evidenza. ⬆️ **RISOLTO (verificato 20/07 sera)**: sul tenant String Project (122-h000672, dominio di lavoro `122-h000672.swebbysites.com`) tutte le pagine emettono ora `<link rel="canonical">` self-ref + Open Graph (`og:title`/`og:locale`); verificato **60/60** pagine top-level. | 🟢 risolto (20/07) |
| B38 | **`font-display` ignorato nell'upload font** — `POST /fonts` accetta `display: "swap"` ma la `@font-face` compilata esce con `font-display:block`. Minore (block = FOIT breve), ma il campo dichiarato non ha effetto. | 🟢 minore (04/07) |
| B48 | **Slot loghi del tema non impostabili via API — `/design/logos` 404** — la CLI espone `design logos-get`/`logos-update` (slot `logo_black`/`logo_white`/`logo_mobile_black`/`logo_mobile_white`/`logo_email`/`favicon`, "stessa operazione del pannello Grafica → Loghi") ma su swebby-new (122-h000726) sia `GET` sia `PUT /design/logos` rispondono **404 NOT_FOUND** (la CLI è autenticata; confronto diagnostico: `/design/colors` non autenticato → 401, `/design/logos` → 404, quindi la rotta non è deployata, non è un problema di auth). Nessun endpoint alternativo (`config` = solo autocommit; `header-footer` = solo partial). Conseguenza: gli slot loghi restano vuoti → email/pannello/base.html senza logo, e il default `<link rel="shortcut icon" href="/static/img/uploads/favicon.ico">` di base.html resta rotto (aggirato iniettando i PNG `<link rel=icon>` nell'header custom). ⚠️ Vincolo correlato: `POST /media` accetta solo folder `cat_images/blog/blog_cat_images` e rifiuta gli SVG (INVALID_IMAGE) — i loghi vanno quindi caricati come PNG/webp in `blog/` (fatto: `/uploads/blog/swebby-logo-black.png` viola trasparente, `-white.png` bianco trasparente, `-email.png` viola su bianco; favicon `-192.png`, tutti 200). **Richiesta:** deployare/abilitare `GET`+`PUT /design/logos` sull'istanza (upsert che crea il record se assente), così `logos-update` funziona; il comando è pronto con i path già caricati. **RISOLTA 15/07**: la piattaforma ha abilitato `GET/PUT /design/logos` E l'upload SVG/ico nella cartella media `logos`. ⚠️ **Uso corretto scoperto**: (1) `POST /media --folder logos` (ora accetta svg/ico/png) salva in `/static/img/uploads/<nome>` e restituisce `valore_campo` = **nome file nudo**; (2) `logos-update` vuole nel body i **valore_campo (bare filename)**, NON i path `/uploads/...` (con quelli dà **500 INTERNAL_ERROR**). `logos-get` ritorna `slots.{slot}.{nome,url,esiste}` + `opzioni.logo_is_trasparente`. ⚠️ residuo minore: `--idempotent` NON deduplica gli upload media (crea copie con suffisso random `_XXXXXXX`); e il default `<link rel="shortcut icon" href="/static/img/uploads/favicon.ico">` di base.html è hardcoded → per farlo risolvere serve un file chiamato esattamente `favicon.ico` in `logos` (fatto). Slot Swebby impostati: logo_black/mobile_black=swebby-logo-black.svg (viola), logo_white/mobile_white=swebby-logo-white.svg (bianco), logo_email=swebby-logo-email.png, favicon=swebby-favicon.png, trasparenza on. | ✅ risolta (15/07) |
| B49 | **Doc custom-apps contraddittoria sul CSS admin → app con look diverso dal pannello nativo** — la `custom-apps-guide` dà due indicazioni OPPOSTE per lo stile del pannello admin di una custom app: (a) `template_admin.content` dice *«{% block content %}: SOLO classi design system sw-* (sw-page-header, sw-page-body, sw-table-toolbar, sw-mobile-grid card + sw-table desktop, sw-btn-dots/sw-action-dropdown, slideout, modali). Pulsanti azione LINK-STYLED. Niente utility.»* → usa i componenti nativi; (b) `css_admin.classi` dice *«i componenti core sw-* NON sono garantiti nel bundle (tree-shakati sull'uso del core), definisci TUTTE le classi con prefisso .sw-app-<name>-*»* → rifatti lo stile a mano. Seguendo (b) l'app `progetti` di swebby è stata stilizzata con `sw-app-progetti-*` e risulta **graficamente diversa** dalle pagine di sistema (es. «Pagine CMS»: header a banda, stat card, tabella con badge/azioni dropdown). **Realtà (verificata):** `admin.css` live (220KB, `/static/css/admin.css`) **contiene** tutte le classi del design system admin perché il CORE le usa — `.sw-table`×40, `.sw-page-header`, `.sw-page-body`, `.sw-table-toolbar`×5, `.sw-mobile-grid`, `.sw-btn-dots`, `.sw-action-dropdown`×10 — quindi una custom app che le usa **eredita il look nativo gratis** (coerente con `swcss.tree_shake`: sopravvivono le classi usate in `templates/admin/**`). Il warning di `css_admin.classi` è quindi fuorviante: i componenti-layout del design system sono stabili e presenti; `sw-app-<name>-*` va usato SOLO per pezzi app-specifici non coperti dal design system. **Richiesta:** riconciliare la doc — `template_admin` e `css_admin` devono dire la stessa cosa (usa i componenti design-system nativi per header/tabella/toolbar/azioni; custom prefissato solo per gli extra), possibilmente con uno snippet di markup di riferimento (es. come è fatta «Pagine CMS»). **Confermato 15/07**: riscritta la lista admin dell'app `progetti` usando SOLO i componenti nativi (`sw-page-body`/`sw-table-toolbar`/`sw-table`/`sw-cell(-header)`/`sw-entity-info>sw-entity-title+sw-entity-detail`/`sw-badge-success`/`sw-btn-primary`/`[data-sw-actions]`+`sw-table-actions-btn`+`sw-action-dropdown`) → look **identico** alle pagine di sistema, e il dropdown azioni funziona SENZA JS custom (le funzioni globali `showActionDropdown/toggleDropdown` di swebby.js gestiscono `[data-sw-actions]`). Due accortezze pratiche per la doc: la `.sw-table` core è `display:none` <1024px (serve override scoped o il layout `sw-mobile-grid`), e i valori `nowrap` lunghi (es. slug in `sw-entity-detail`) vanno cappati per non sforare il viewport. | 🟡 aperto — doc (15/07) |
| B50 | **Tipografia di default: `<a>` ha un font-size ASSOLUTO invece di ereditare → i link escono più grandi del testo che li contiene** — `<a>` è un elemento **inline** (vive DENTRO il testo di un altro elemento), ma nei `tipografia.css` di default è trattato come un elemento di blocco, con la stessa identica forma di `p`/`li`: `a { font-size: var(--text-base) }` + bump `@media { font-size: var(--text-lg) }`. Funziona solo finché il link sta in un testo che è esattamente `--text-base`/`--text-lg`; appena finisce dentro un testo con classe più piccola (card, didascalie, badge) resta 16/18px e **si vede più grande del suo testo**. Riscontrato su **2 tenant indipendenti**, segnalato dal cliente entrambe le volte: swebby-new (122-h000726) e Gevi/String Project (122-h000672 — es. link 18px dentro paragrafo da 14px, card rassegna stampa `.78–1.05rem`). **Non è un caso isolato**: (a) la regola è nel set `predefinito: true` → arriva a OGNI tenant; (b) è **replicata in ogni sezione** — `globale/tipografia.css` (`a`) e `<sezione>/tipografia.css` (`:where(#main_content) a`, con `:where()` a specificità 0 → vince per ordine) per prodotto/categoria_prodotto/carrello/checkout/blog/mio_account; (c) era **già stata rattoppata ad-hoc per-componente** (nel CSS Gevi c'è già `.sw-cs-crumb a { font-size:inherit; font-weight:inherit; line-height:inherit }`) — la firma classica di un default sbagliato che si continua a ri-patchare. ⚠️ **I `tipografia.css` di sezione sono marcati «Generato automaticamente - Non modificare manualmente»** → il tenant NON può correggerli in modo durevole: il fix deve venire dal **generatore**. **Fix proposto**: `a { font-size: inherit; line-height: inherit; }` + il link possiede solo colore/peso/decorazione; togliere `a` dai bump `@media` (la scala 16→18px raggiunge già il link ATTRAVERSO il `<p>`/`<li>` che lo contiene). Risultato: link in paragrafo identico a oggi, link in card che si adegua, zero pezze per-componente. **Doc**: la guida design codifica lo stesso modello — «`globale/`: default d'elemento (`h1`/`p`/`a`/bottoni)» mette `a` nello stesso paniere dei blocchi, e in 15KB di guida `inherit` e `tipografia` compaiono **0 volte**. Workaround applicato su 122-h000672: `inherit` in `globale/` + `cms/` (le uniche editabili). ⬆️ **RISOLTO upstream (verificato 17/07, v2.31.22)**: l'update esegue `patch_swcss_link_inheritance` che strippa `font-size/line-height/font-weight/letter-spacing` dalle regole `a`/`:where(#main_content) a` (bump `@media` inclusi) in TUTTI i `tipografia.css` per-istanza + ricompila. Verificato via API su swebby (122-h000726): globale/cms/prodotto/categoria/carrello/checkout/blog/mio_account tutte PULITE; bundle cms.css compilato senza `a{font-size}`; browser (computed styles, articolo+servizio): 0 link più grandi del testo, `.sw-sv-inlink` 16/16. Su SP (122-h000672) le sezioni auto-gen sono strippate dalla patch; globale/cms restano i miei edit `inherit` (la patch li salta perché personalizzati — comportamento atteso da handoff, e `inherit` è comunque corretto). | 🟢 risolto upstream (17/07) |
| B51 | **`/redirects`: le regole si salvano ma nginx non le applica MAI → il motore di B41 non funziona end-to-end** — la risorsa `/redirects` accetta e persiste correttamente le regole, ma **nessun redirect scatta sul sito servito**. Repro su swebby-new: `POST /redirects` con `origine:"/mcp-per-la-seo/"`, `origine_tipo:"Inizia con"`, `destinazione:"/blog/mcp-per-la-seo/"`, `status_code:301` → creata, presente in `GET /redirects` coi campi giusti (`redirect_type:"local"`); ma `GET https://swebby.it/mcp-per-la-seo/` → **404 invece di 301** (destinazione verificata esistente: `/blog/mcp-per-la-seo/` → 200). **Testato senza successo**: tutti i match-type (`Inizia con`, `Regex` `^/mcp-per-la-seo/$`, `Contiene`); sia sul dominio preview `122-h000726.swebbysites.com` sia sul dominio reale `swebby.it` dopo lo switch; dopo `cache flush`; e dopo aver forzato la rigenerazione con una mutazione (`PUT /redirects/{id}`), che da doc «rigenera la configurazione nginx e la ricarica». L'unico 301 osservato è la normalizzazione trailing-slash della piattaforma (`/slug` → `/slug/`), che poi finisce in 404. Sembra che la config nginx generata non venga inclusa/ricaricata nel server block che serve il sito. **Impatto**: 71 regole già caricate e pronte (65 articoli blog + 6 categorie, `/<slug>/` → `/blog/<slug>/`) ma inerti; i vecchi URL WordPress fanno 404 e si perde l'equity SEO della migrazione — esattamente ciò che B41 doveva evitare. ⬆️ **RISOLTO (verificato 17/07 pomeriggio)**: dopo l'intervento del team i 301 scattano su tutte le regole (65 articoli + 6 categorie verificati live su swebby.it). Residuo tracciato separatamente come **B52** (downgrade http). | 🟢 risolto (17/07) |
| B52 | **Redirect: la destinazione esce in `http://` → hop extra in chiaro** — con `destinazione` impostata come path **relativo** (`/blog/<slug>/`), il motore emette un `Location` **assoluto con schema `http://`** invece di `https://`. Risultato su swebby.it: `https://swebby.it/mcp-per-la-seo/` → 301 → `http://swebby.it/blog/mcp-per-la-seo/` → 301 (redirect HTTPS del server) → `https://swebby.it/blog/mcp-per-la-seo/` → 200. Atterra corretto ma con **2 hop invece di 1** e **un passaggio in plaintext HTTP** (l'URL viaggia in chiaro; su un visitatore senza HSTS è una richiesta non cifrata reale). Impatta TUTTE le regole di una migrazione (qui 71). **Fix proposto**: emettere il `Location` **relativo** così com'è configurato (il browser conserva lo schema), oppure costruire l'assoluto con lo **schema della richiesta** (`https` quando la richiesta è https) invece di cablare `http://`. ⬆️ **Repro isolato (17/07)**: il difetto è nella conversione **relativo→assoluto**, non nel motore in generale. Stessa regola, solo la `destinazione` cambia: `destinazione: "/blog/mcp-per-la-seo/"` (relativa) → `Location: http://…` = 2 hop; `destinazione: "https://swebby.it/blog/mcp-per-la-seo/"` (assoluta https) → `Location: https://…` = **1 hop, corretto**. Quindi quando la destinazione è già assoluta il valore viene passato intatto; quando è relativa il prefisso viene ricostruito cablando `http://`. **Workaround applicato su swebby.it**: convertite tutte e 71 le regole a destinazione assoluta `https://swebby.it/blog/<slug>/` → verificate live 71/71 a 1 hop + 200. Resta da sistemare perché la destinazione relativa è la forma naturale/documentata (`destinazione`: «path relativo o URL assoluto») e chi la usa subisce l'hop in chiaro. ⬆️ **RISOLTO upstream (verificato 17/07, v2.31.22)**: fix `write_to_nginx_conf` con `absolute_redirect off;` nei conf generati. Per-istanza serve rigenerare la conf (ri-salvare una regola / `PUT redirects` = trigger). Fatto: workaround assoluto rimosso, 71 regole riportate a destinazione **relativa** (`/blog/<slug>/`); verificate live 71/71 → **1 hop, `Location` relativo, 200**. | 🟢 risolto upstream (17/07) |
| B53 | **Header di default: `id="cart_el"` duplicato tra header e sticky-header → ID duplicato nel DOM** — i template stock `header.html` E `header_sticky.html` (e `header_trasparente.html`) contengono entrambi `<div class="sw-header-actions-col" id="cart_el">`: quando la pagina rende header + sticky insieme, l'`id` compare **2 volte** nel DOM. Impatto: (a) accessibilità — ID non univoco (storicamente WCAG 4.1.1); (b) **funzionale** — se il JS del tema aggiorna il carrello con `getElementById('cart_el')`, colpisce solo il PRIMO nodo → il badge carrello nello sticky rischia di non aggiornarsi. **Non è specifico del tenant**: è la struttura stock del tema. Riscontrato su Gevi/String Project (122-h000672) su tutte e 3 le varianti header; per contro un header **forkato custom** (swebby-new `header_swebby.html`) che NON include `cart_el` non ha il problema → conferma che nasce dal default seminato. I template sono `upstream: False` (copia per-tenant), quindi ogni tenant che usa l'header stock eredita il duplicato e un fix locale verrebbe perso a un eventuale ripristino default. **Fix proposto (a monte)**: nel template default dare all'azione carrello un id univoco per contesto (es. `cart_el` nell'header, `cart_el_sticky` nello sticky) **oppure** far targetizzare il carrello dal JS via **classe** (`.js-cart-el`) invece che per id, aggiornando tutti i nodi. | 🟡 aperto (19/07) |
| B54 | **`llms.txt` non generato/servito nonostante i campi `llms_*` valorizzati** — le pagine/prodotti espongono `llms_index` (schema: «Includi nel file llms.txt»), `llms_description` («Testo per il file llms.txt») e `llms_section`, ma **`/llms.txt` non esiste**: 404 su tutti i path provati (`/llms.txt`, `/.well-known/llms.txt`, `/static/llms.txt`) su DUE tenant — incluso **swebby.it (LIVE)** dove **60 pagine** hanno `llms_index=true` E `llms_description` compilata. Idem `/llms-full.txt` e le versioni `.md` per-pagina (404). La feature è quindi a metà: i dati si raccolgono via API ma l'endpoint che li espone non c'è → riempire i campi non produce alcun effetto visibile. **Richiesta**: generare e servire `/llms.txt` come indice markdown per standard llmstxt.org — raggruppato per `llms_section` (`## Sezione`), una riga `- [title](url): llms_description` per ogni pagina con `llms_index=true`, `# <nome sito>` + blurb in testa. Opzionali (standard esteso, non obbligatori): `/llms-full.txt` e una `.md` pulita per pagina. Da chiarire anche se serve un flag globale di attivazione (nessun endpoint per abilitarlo). | 🟡 aperto (19/07) |
| B55 | **`<html lang>` usa il «Codice (slug)» invece del tag locale BCP-47 già presente nella config** — il pannello Impostazioni→Lingue ha **3 campi** per locale: **Codice (slug)** (es. `ar`), **Path URL** (es. `es-AR`) e **Codice bandiera** (es. `ar`, ISO 2 lettere). Verificato live 19/07 su String Project (122-h000672) come vengono usati DAVVERO: il **segmento URL** usa il *Codice* (`/ar/jugadores…` = 200; `/es-AR/jugadores…` = **404**); le **hreflang** usano il *Path URL* (`<link hreflang="es-AR" href="…/ar/…">`, `hreflang="en-GB" href="…/en/…">`) → **corrette BCP-47**; ma **`<html lang>` usa il *Codice*** → `<html lang="ar">` sul contenuto **spagnolo** dell'Argentina (e `<html lang="en">` per l'inglese, dove il Path URL sarebbe `en-GB`). `ar` è l'ISO 639 dell'**arabo** → screen reader e Google leggono "arabo" su testo spagnolo; niente `dir="rtl"`. **Nodo**: la piattaforma **HA GIÀ** il tag corretto (`es-AR`, nel campo Path URL che alimenta le hreflang) ma NON lo usa per l'attributo `lang`. **Fix (piccolo e preciso)**: far leggere a `<html lang>` lo **stesso campo delle hreflang** (Path URL / tag locale), non il Codice. **Beneficio collaterale importante**: così il *Codice/segmento URL* diventa libero di essere uno **slug leggibile per-mercato** (`/argentina/`, `/usa/`, `/cina/`) senza sporcare `lang`/hreflang → abilita il modello **ibrido lingua+nazione** (locale per lingua `it`/`fr`/`es` + locale per nazione con Path URL `es-AR`/`en-US`/`zh-CN`). Oggi invece un Codice non-BCP-47 (es. `argentina`) finirebbe in `<html lang="argentina">` = invalido. **Correlato**: senza canonical (B43) l'`/ar/`=es-AR rischia di essere visto come duplicato di `/es/` — il lang errato peggiora la disambiguazione. **Niente workaround via API pulito**: cambiare `pagina.lang` da `ar` a `es-AR` **rinomina il file contenuto** (per `--lang`) e romperebbe routing `/ar/` + alternates già indicizzati → il fix va fatto a monte nel tema. ⬆️ **RISOLTO (verificato 20/07 sera)**: il team ha applicato il fix a monte. Ora `<html lang>` segue il tag BCP-47 (Path URL): Argentina → `<html lang="es-AR">` con `og:locale=es_AR`; it/en/es/fr coerenti. Inoltre è stato adottato il modello URL ibrido: il segmento Argentina è passato da `/ar/` a **`/argentina/`** (200; `/ar/`→404), come previsto dal beneficio collaterale. | 🟢 risolto (20/07) |
| B56 | **La cache-pagina non si invalida all'update → le modifiche SEO/contenuto NON arrivano al sito live senza un `cache flush` globale** — aggiornare `meta_title`/`description`/`index`/contenuto di una pagina via API o pannello **persiste nel DB** ma **non rigenera l'HTML pubblicato** (servito da cache). Verificato 19/07 su String Project (122-h000672): ri-salvando il contenuto di `sostenibilita-string-project` (`pages content page-update`, no-op) la `<meta name="description">` live resta **assente** pur essendo valorizzata nel record; idem dopo `pages update` sui campi SEO. Conseguenza: **16 pagine su 36 (sitemap IT)** servono un render congelato **senza** `<meta name="description">` mentre il record ce l'ha (es. `/es/cuerdas-de-tenis/string-project-magic/` = 0 description servita, record OK). L'unico modo per pubblicare è **`cache flush`** (target `pages` = "reset template loader + reload URL"), che è **globale**: non esiste invalidazione/re-render per singola pagina, e l'update non ne innesca uno. **Impatto operativo**: gli editor modificano la SEO e non la vedono mai online (fallimento silenzioso); il workaround è un flush dell'intero sito — brutale, perché rigenera anche pagine in stato incompleto (es. i 3 finder SP la cui migrazione SWCSS è a metà → romperebbe le card). È lo stesso comportamento noto come 'C6' ("l'update non ri-renderizza, serve ricreare la pagina"). **Richiesta**: alla modifica di un record pagina/prodotto o del suo contenuto, **invalidare + rigenerare automaticamente la cache di QUELLA pagina** (API e pannello); in subordine, esporre un endpoint di **re-render/invalidazione per singola pagina** (così si evita il flush globale). ⚠️ **RITIRATO / non confermato (20/07 sera)**: la diagnosi era **viziata da un errore di dominio**. Le verifiche "il render non si aggiorna / il flush non pubblica" erano fatte su **`stringproject.com`**, che NON è il tenant di lavoro ma un **deployment separato e datato** (bundle `sw_front.min.js` 265 KB vs 970 KB, routing `/ar/` vecchio, cutover futuro). Sul **dominio di lavoro `122-h000672.swebbysites.com`** le modifiche di record/contenuto SI pubblicano: SEO live verificata **60/60** (title=record, description, canonical, og). Nessun "publishing rotto" da correggere. (Se esisteva un reale nodo di cache-pagina, è comunque non più riproducibile sul tenant.) | ⚪ ritirato (20/07) |
