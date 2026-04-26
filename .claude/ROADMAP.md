# Família Finances — ROADMAP

> Pla d'evolució per fases. Marca les caselles a mesura que es completen.
> Quan acabis una fase, fes commit amb missatge `feat(fase-X): descripció`.

---

## Fase 0 — Fixes urgents ⚡ *(1 sessió)*

Coses que avui no funcionen bé i que es resolen en una sola sessió.

- [ ] **Bug imatges múltiples**: el `file_uploader` ha d'acceptar múltiples fitxers (`accept_multiple_files=True`), processar-los en bucle amb `progress bar`, i mostrar previsualització abans de processar.
- [ ] **Actualitzar context de l'assessor IA**: treure referència a "Jose a l'atur", treure reclamació BBVA, posar context d'autònom imminent (800–1.000€) i la xifra correcta del lloguer (550€, no 850€).
- [ ] **Verificar** que els imports `Plotly`, `PIL` i `uuid` segueixen funcionant després dels canvis.

---

## Fase 1 — UI moderna i responsive 🎨 *(1 setmana)*

L'app ha de ser agradable d'usar al mòbil. Streamlit té limitacions, però amb CSS i bona estructura es fa molt.

- [ ] **CSS amb variables i mode fosc nadiu** (`@media (prefers-color-scheme: dark)`).
- [ ] **Tipografia**: stack del sistema (`-apple-system, "Segoe UI", "Inter"...`).
- [ ] **Mètriques amb hover i transició suau** (`transform: translateY(-2px)`).
- [ ] **Mòbil**: les 3 mètriques en mode 2x2 o stack vertical sota 640px.
- [ ] **Hero card** del saldo amb delta vs mes anterior (% i €).
- [ ] **Mètriques redissenyades**: ingressos, despeses, taxa d'estalvi (%), dies fins a final de mes.
- [ ] **Selectors com a pills, no `st.radio`**: més modern visualment.
- [ ] **Ordre de pestanyes revisat**: la més usada (afegir moviment) la primera.
- [ ] **Empty states** decents quan no hi ha dades del període.

---

## Fase 2 — Provisió fiscal d'autònom 🧾 *(1 setmana)*

Mòdul crític. Cada vegada que s'afegeix un ingrés freelance, l'app calcula buffers fiscals.

> Skill rellevant: `autonom-fiscal`

- [ ] Al `core/`, mòdul `autonom.py` amb:
    - [ ] `calcular_quota_ss(rendiment_net_mensual, tarifa_plana_activa, mes_alta)` → quota de la SS.
    - [ ] `calcular_irpf_provisio(ingres_brut, retencio_aplicada=0.15)` → quants € s'han d'apartar per IRPF.
    - [ ] `calcular_iva(ingres_brut)` → IVA repercutit a apartar.
    - [ ] `tram_actual(rendiment_net_anual)` → retorna el tram (1–15) i la cuota corresponent.
- [ ] Pestanya nova **"Autònom"** al sidebar amb:
    - [ ] Comptador "Estalviat per Hisenda" i "Estalviat per Seguretat Social".
    - [ ] Previsió de pagament del proper trimestre (Modelo 130 i 303).
    - [ ] Estat de la tarifa plana (mesos restants).
- [ ] Camp opcional `aplica_iva` als moviments d'ingrés perquè l'usuari marqui si la factura porta IVA.

---

## Fase 3 — Pressupostos amb alertes 💰 *(3-4 dies)*

- [ ] Nova pestanya `Recurrents` o secció dins, per definir pressupost mensual per categoria.
- [ ] Al dashboard, secció "Estat dels pressupostos" amb `progress bar` per categoria:
    - 🟢 < 70% → verd
    - 🟡 70–90% → groc
    - 🔴 > 90% → vermell
- [ ] Si una categoria supera el pressupost, avís a la barra lateral.

---

## Fase 4 — Previsió de cash flow 🔮 *(2-3 dies)*

- [ ] A `analytics.py`, funció `projectar_saldo(df, df_recurrents, dies=60)`.
- [ ] Gràfic Plotly amb la corba de saldo previst per als propers 30/60/90 dies.
- [ ] Marcadors de pagaments grans previstos (amb tooltip).
- [ ] Avís si el saldo previst baixa de cert llindar (ex: 500€).

---

## Fase 5 — Detecció d'anomalies 🚨 *(2-3 dies)*

> Skill rellevant: `financial-prompt`

- [ ] Funció setmanal `detectar_anomalies(df_actual, df_historic)`:
    - Variacions > 30% per categoria respecte a la mitjana dels 3 mesos anteriors.
    - Despeses individuals > 2x la mediana de la categoria.
- [ ] Botó "Generar resum setmanal" que crida Gemini amb les anomalies detectades.
- [ ] Pestanya "Insights" amb història d'anomalies prèvies.

---

## Fase 6 — Refactor i robustesa 🛡️ *(1 setmana)*

- [ ] Migració a estructura modular (`core/`, `ui/`, `tests/`).
- [ ] Models Pydantic per `Movement` i `RecurrentConfig`.
- [ ] Logging estructurat (substituir tots els `st.error/warning` pel patró logger + ui).
- [ ] Tests unitaris per a `core/recurrents.py`, `core/autonom.py`, `core/analytics.py`.
- [ ] CI bàsic amb GitHub Actions (lint + tests).
- [ ] `requirements.txt` amb versions fixades + `requirements-dev.txt`.

---

## Fase 7 — Quality of life 🌟 *(quan tinguis temps)*

- [ ] Exportació a Excel/PDF dels moviments del trimestre (per a la declaració d'autònom).
- [ ] Comparativa anual: gener-actual vs gener-mateix-mes-any-anterior.
- [ ] Categorització automàtica basada en historial (`establiment` → suggerència de `categoria`).
- [ ] Mode "només lectura" per a l'Alba per evitar edicions accidentals.
- [ ] Backups automàtics (snapshot setmanal del Sheet a Drive).
- [ ] Notificacions push via Telegram quan superes pressupost o entren ingressos.

---

## Idees aparcades 💭

- Multi-usuari amb autenticació Google.
- Integració amb extracte bancari (BBVA API si és possible).
- App nativa amb Flet o Reflex.
