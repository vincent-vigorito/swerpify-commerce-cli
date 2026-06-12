# SWCSS — il design system di SwerpiCommerce, per agenti

Fonte autorevole e sempre aggiornata: `GET /design/swcss-guide` (markdown servito
dall'API del tenant). Questo file è la versione distillata + pratica appresa.

## Cos'è (e cosa non è)

SWCSS è il sistema di classi CSS del tema (`sw-hero`, `sw-wrap`, `sw-section`,
`sw-cta`, ...): CSS puro con custom properties e `@custom-media`, nessun
preprocessore, build con **tree-shaking per pagina**. Non è un endpoint o un
"metodo" API: si usa scrivendo markup nel contenuto delle pagine e regole nei
file CSS, poi si compila.

## Il flusso completo (l'ordine conta)

```
1. POST /pages                      → crea la pagina (title, slug, SEO)
2. PUT  /pages/{id}/content         → HTML (solo l'interno del {% block content %})
3. PUT  /design/css/cms/<slug>.css  → regole CSS della pagina (se servono)
4. POST /design/compile             → SOLO ora va tutto live (~1.3s)
5. GET  https://<tenant>/<slug>/    → verifica pubblica
```

Il compilatore estrae le classi **usate nei template** e scarta il resto:
- classe definita nel CSS ma mai usata nell'HTML → eliminata dal bundle
- classe usata nell'HTML ma definita da nessuna parte → senza stile
- classi aggiunte **da JavaScript a runtime** → invisibili al tree-shaker:
  dichiarale nel template, anche in un commento HTML

## Architettura dei layer

| Layer | Sezione API | Scrivibile | Scopo |
|---|---|---|---|
| `base/` | non esposto | ❌ mai | il framework: variabili, reset, utility, componenti base |
| `pagine-sistema/<sezione>/` | `cms`, `prodotto`, `carrello`, `checkout`, `categoria_prodotto`, `mio_account`, `minicart`, `header_footer`, `blog` | ✅ | CSS delle pagine di quella sezione |
| `custom/` | `custom` | ✅ | componenti riusabili tra più pagine |

- Le pagine CMS create via API compilano nel bundle **`cms`**: il CSS di una
  pagina nuova va in `PUT /design/css/cms/<slug>.css` (un file per pagina).
- `GET /design/css?section=...` elenca i file; `GET /design/css/{section}/{file}`
  legge il sorgente. **Leggi prima di scrivere**: i sorgenti reali sono il modo
  migliore di scoprire componenti, variabili e convenzioni del tema.
- I file con `predefinito: true` sono il set base della sezione: non eliminarli,
  modificali con cautela (il ripristino default del pannello li sovrascrive).

## Regole del design system

1. **Se esiste un componente `sw-*`, usalo** (il contenuto della homepage è il
   catalogo vivente: `pages content page-get <id homepage>`). Le utility
   (`flex`, `p-4`, `grid-2`, ...) sono per micro-aggiustamenti, non per layout
   che il design system già copre.
2. **Mai toccare o ridefinire il layer `base/`.**
3. **Niente utility di spacing verticale tra fratelli**: usa il pattern
   `.sw-mio-comp > * + * { margin-top: ...; }` nel componente.
4. **Variabili, non valori**: `var(--sw-..., fallback)` per colori e soglie
   (i token stanno nel layer base non esposto → metti sempre il fallback).
5. **Breakpoint con `@custom-media`**, mobile-first:
   `(--mb)` <640 · `(--sm)` ≥640 · `(--md)` ≥768 · `(--lg)` ≥1024 · `(--xl)` ≥1280.
   In compilazione diventano media query reali (`width >= 640px`, ...).
6. **Prefissa le classi nuove** con `sw-<slug>-` (es. `sw-promo-hero`): niente
   collisioni e tree-shake prevedibile. Un file CSS per pagina/componente.

## Contenuto pagina

- `PUT /pages/{id}/content` scrive **solo l'interno** del `{% block content %}`:
  wrapper, header, footer, menu e font arrivano dal layout base.
- È un template Django: tag e variabili sono disponibili, ma per pagine
  statiche basta HTML con classi SWCSS.
- Immagini dalla libreria media (`POST /media` → usa l'`url` restituito e
  valorizza gli `alt`).

## JavaScript per-pagina

`PUT /design/js/<slug>.js`: il file viene caricato **automaticamente** dalla
pagina con quello slug (`defer`, cache-buster su mtime), **senza compile** —
live subito. Per JS condiviso: nome non-slug + `<script src>` nel contenuto.
Vanilla JS consigliato.

## Animazioni: puro CSS prima di tutto

- Entrate a cascata: `animation` + `animation-delay` scaglionati.
- **Reveal allo scroll senza JS**: scroll-driven animations —
  ```css
  @supports (animation-timeline: view()) {
    .sw-x-reveal { animation: sw-x-up linear both;
                   animation-timeline: view();
                   animation-range: entry 5% entry 45%; }
  }
  ```
  Dentro `@supports`: senza supporto il contenuto resta visibile (mai
  `opacity: 0` fuori dal guard). Bonus: è reversibile (segue lo scroll).
- Cascata tra card della stessa riga: varia `animation-range` per `nth-child`.
- Sempre `@media (prefers-reduced-motion: reduce)` per spegnere le animazioni.
- Grafici statici: SVG inline nel contenuto (niente librerie JS).

## Errori tipici

| Sintomo | Causa |
|---|---|
| Modifica non visibile sul sito | manca `POST /design/compile` |
| Classe senza stile | definita in una sezione che la pagina non usa, o mai usata nell'HTML alla compilazione (tree-shake) |
| Stile che rompe altre pagine | modificata una classe globale (`custom` o file `predefinito`) per un problema locale: usa una classe nuova prefissata |
| Reveal che non parte | classe aggiunta da JS non dichiarata nel template |
