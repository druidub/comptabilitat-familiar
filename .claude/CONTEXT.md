# Família Finances — Context del Projecte

> Llegeix aquest fitxer al començament de cada sessió per tenir el context essencial.

## Què és aquesta app

Una aplicació de comptabilitat familiar feta amb **Streamlit** que utilitza **Google Sheets** com a base de dades i **Gemini** per processar text i tiquets en imatges. Versió actual: `v2.8`.

L'app és **personal i privada** (no s'oferirà a clients). Serveix per gestionar les finances de la família Jose Manuel + Alba.

## Context familiar

- **Jose Manuel**: a punt de donar-se d'alta com a autònom (serveis web, SEO, edició). Ingressos actuals 800–1.000€/mes amb previsió creixent. Desenvolupador del projecte.
- **Alba**: nòmina d'aproximadament 1.300€/mes.
- **Lloguer rebut**: 550€/mes (ingrés extra recurrent).
- **Localització**: Calders, Bages, Catalunya.
- **Idioma de la UI i del codi**: català (cap de variable, ni a comentaris, ni en text d'usuari posis castellà o anglès).

## Objectius del projecte

1. **Visibilitat real** de l'estat econòmic mensual i la tendència.
2. **Provisió fiscal** per a la transició a autònom (quotes SS, IRPF, IVA).
3. **Pressupostos i alertes** per categoria.
4. **Previsió de cash flow** dels propers 30/60 dies.
5. **Detecció d'anomalies** amb IA.

## Stack tècnic

| Capa | Tecnologia |
|------|-----------|
| Frontend | Streamlit |
| Base de dades | Google Sheets (via `streamlit-gsheets`) |
| IA | Gemini (`gemini-2.5-flash`) per processar text i imatges |
| Gràfics | Plotly |
| Imatges | Pillow |
| Hosting | Streamlit Community Cloud |
| Seguretat | Contrasenya simple via `st.secrets` |

## Estructura objectiu (refactor pendent)

```
finances/
├── app.py                  # entrada Streamlit, només UI
├── core/
│   ├── data.py             # carregar/guardar, models Pydantic
│   ├── recurrents.py       # lògica de freqüències i avisos
│   ├── ia.py               # wrappers de Gemini, prompts
│   ├── analytics.py        # càlculs (saldo, previsions, anomalies)
│   └── autonom.py          # càlculs fiscals d'autònom
├── ui/
│   ├── dashboard.py
│   ├── input_panel.py
│   ├── advisor.py
│   └── components.py       # cards, pills, helpers visuals
├── config.py               # constants, prompts, categories
├── tests/                  # pytest per al core (sense Streamlit)
└── .claude/
    ├── CONTEXT.md          # aquest fitxer
    ├── ROADMAP.md          # pla per fases
    └── skills/
        ├── streamlit-component/
        ├── financial-prompt/
        └── autonom-fiscal/
```

## Convencions

### Codi
- **Llengua**: català per a noms de variables i funcions on tingui sentit (`carregar_dades`, `guardar_recurrents`...). Acceptable barrejar-ho amb anglès quan la convenció tècnica ho demani (`df`, `id_grup`).
- **Type hints** sempre que sigui possible al `core/`.
- **Pydantic** per validar moviments abans de guardar.
- **Logging** amb el mòdul `logging`, mai `print` en producció.

### Diners i signes
- **Ingressos: positius**. **Despeses: negatives**. Mai al revés.
- Sempre passar per `corregir_signe(quantitat, tipus)` abans de guardar.
- Conjunt `PARAULES_INGRES` per detectar el tipus si arriba ambigu.

### Dates
- Format ISO `YYYY-MM-DD` a Sheets i internament.
- Avui: `date.today()` — mai `datetime.now().date()` quan no calgui hora.

### Categories oficials
Despeses: `Llar`, `Subscripcions`, `Alimentació`, `Restauració`, `Transport`, `Salut`, `Oci`, `Roba`, `Deute`, `Altres`.
Ingressos: `Nòmina`, `Lloguer_Ingrés`, `Freelance`, `Bizum`, `Devolució`, `Altres_Ingrés`.

> Si el codi necessita una categoria nova, afegeix-la aquí abans i a la `Recurrents`.

### Sheets
- Pestanya principal: dades transaccionals. Columnes: `data, concepte, establiment, quantitat, categoria, tipus, es_periodic, id_grup`.
- Pestanya `Recurrents`: configuració. Columnes: `concepte, quantitat, categoria, tipus, dia, frequencia`.
- **No** trenquis l'esquema sense actualitzar `carregar_dades()` i `carregar_recurrents()`.

### Gemini
- `GEMINI_MODEL = "gemini-2.5-flash"` (econòmic, suficient).
- Sempre via `amb_reintents()` — té backoff exponencial per 429/quota/timeout.
- Prompts curts, específics, amb format de sortida exigit. Mai assumeixis que retornarà JSON net: passa per `parsejar_json_ia()`.
- Skill rellevant: `financial-prompt`.

## Coses a NO fer

- ❌ No introduir `accept_multiple_files=True` sense bucle de processament — l'app es trenca.
- ❌ No canviar l'esquema de Google Sheets sense migració.
- ❌ No barrejar `streamlit.cache_data` amb operacions d'escriptura sense `cache_data.clear()`.
- ❌ No usar `st.experimental_*` ni APIs deprecades.
- ❌ No introduir dependències pesades (sklearn, tensorflow). La màgia ha de venir de Gemini.
- ❌ No mostrar dades sensibles en logs ni capturar contrasenyes.

## Decisions de disseny preses

- **Per què Streamlit i no Astro/React?** Pepe vol velocitat de desenvolupament en eina pròpia, no llançar producte. Streamlit dóna dashboard amb molt poc codi.
- **Per què Google Sheets i no SQLite/Postgres?** Permet edició manual des del mòbil i no requereix infraestructura. La família també hi pot mirar.
- **Per què Plotly i no Altair?** Plotly fa millor mòbil i el `st.plotly_chart` és estable.
- **Per què Gemini Flash i no GPT-4?** Cost. Flash és prou bo per OCR de tiquets i resums financers.
