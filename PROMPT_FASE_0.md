# Prompt per a Claude Code — Fase 0 (fixes urgents)

> Copia tot el text de sota i pega'l a Claude Code (Sonnet) dins de VS Code,
> amb el projecte obert i les skills `streamlit-component`, `financial-prompt`
> i `autonom-fiscal` carregades a `.claude/skills/`.

---

Hola Claude. Vull aplicar la **Fase 0 del ROADMAP** al projecte. Llegeix primer aquests fitxers per tenir el context:

1. `.claude/CONTEXT.md` — context familiar i tècnic
2. `.claude/ROADMAP.md` — pla per fases
3. `.claude/skills/financial-prompt/SKILL.md` — convencions per a Gemini

Després, fes exactament aquests dos canvis a `app.py`:

## Canvi 1 — Bug de pujada múltiple d'imatges

A la pestanya `t1` (Afegir Moviment), dins del bloc `with col_foto:`, el `st.file_uploader` actual no accepta múltiples fitxers i el flux de processament només suporta una imatge a la vegada. Substitueix tot el bloc `with col_foto:` per aquesta versió que:

- Accepta múltiples imatges (`accept_multiple_files=True`).
- Mostra previsualització en miniatures (fins a 4 visibles) abans de processar.
- Processa totes les imatges en bucle amb una `st.progress` bar.
- Acumula els errors per mostrar-los al final sense aturar el procés.
- Manté la convenció `id_grup = "IMG_" + uuid` per agrupar moviments per tiquet.
- Conserva la validació de mida `MAX_IMG_BYTES`.

Implementa-ho seguint els patrons UI de la skill `streamlit-component` (botons amb `type="primary"`, missatges d'error consistents, espaiats correctes).

## Canvi 2 — Context de l'assessor IA

A la pestanya `t2` (Assessoria IA), el text d'`st.info` i el `prompt_advisor` contenen informació desfasada. Substitueix-ho seguint exactament la **plantilla `prompt_assessor`** de la skill `financial-prompt` (la que ja inclou el context correcte: Jose autònom imminent 800–1.000€, Alba 1.300€, lloguer 550€, sense referències a atur ni a BBVA).

El text de l'`st.info` ha de ser coherent amb el nou context (informació de Jose com a autònom imminent, lloguer 550€, sou Alba 1.300€).

## Requisits de qualitat

- Abans de fer els canvis, **llegeix `app.py` complet** per assegurar-te que entens l'estat actual.
- Mantingues la resta del fitxer **intacte**. No facis "millores no demanades" en aquesta fase.
- Conserva tots els comentaris existents que continuïn sent vàlids.
- Després dels canvis, fes una verificació mental: el flux de `corregir_signe`, `parsejar_json_ia` i `amb_reintents` ha de continuar funcionant igual.
- Comprova que els `import` necessaris ja existeixen (`uuid`, `Image`, etc.).

## Després dels canvis

Mostra'm un diff resumit (només els blocs modificats) abans de donar per acabat. Si hi ha algun dubte sobre alguna decisió (p.ex. on col·locar la previsualització), pregunta-m'ho.

Quan estigui aprovat, suggereix un missatge de commit en català amb format `fix(fase-0): ...`.

---

> Aquest prompt cobreix només la Fase 0. Quan acabem, et passaré el prompt
> de la Fase 1 (UI moderna i responsive).
