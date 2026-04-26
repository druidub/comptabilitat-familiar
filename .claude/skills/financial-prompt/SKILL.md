---
name: financial-prompt
description: Convencions per construir prompts de Gemini al projecte Família Finances. Activa aquesta skill sempre que es creï, modifiqui o ampliï qualsevol prompt enviat a `model.generate_content()`, qualsevol funció que processi text o imatges per extreure moviments financers, l'assessor IA, la detecció d'anomalies, o qualsevol crida a `genai`. Inclou estructura JSON exigida, regles de signe, gestió de dates relatives ("ahir", "el mes passat"), categories vàlides, prevenció d'al·lucinacions, parsing robust i prompts del rol d'assessor amb context familiar. Fes-la servir TAMBÉ quan l'usuari només digui "millora la IA", "afegeix una funció amb IA", "fes que detecti X", encara que no anomeni Gemini explícitament.
---

# Financial Prompt — Convencions IA

Aquesta skill defineix com s'escriuen els prompts de Gemini en aquest projecte. Cada prompt nou ha de seguir aquestes regles, i tota crida ha de passar per la pipeline de validació.

## Pipeline obligatòria

Tota crida a Gemini ha de seguir aquest patró:

```python
res = amb_reintents(model.generate_content, [prompt, contingut_usuari])
dades = parsejar_json_ia(res.text)  # tolerant amb ```json wrappers
validats = [validar_moviment(d) for d in dades]  # Pydantic o validació manual
```

**Per què**: Gemini de tant en tant retorna text amb wrappers de markdown, retorna `dict` quan demanes `list`, o inventa camps. La pipeline neutralitza els 3 problemes.

## Estructura JSON canònica per a moviments

Aquesta és l'única estructura que Gemini ha de retornar quan extreu moviments:

```json
[
  {
    "data": "2026-04-26",
    "concepte": "Compra setmanal",
    "establiment": "Mercadona",
    "quantitat": 47.32,
    "categoria": "Alimentació",
    "tipus": "Despesa",
    "es_periodic": false
  }
]
```

**Sempre llista, fins i tot per a un sol element.** Si el model retorna un dict, `parsejar_json_ia()` el converteix a llista d'un element.

### Regles de cada camp

| Camp | Tipus | Regla |
|------|-------|-------|
| `data` | `str` (ISO `YYYY-MM-DD`) | Si l'usuari diu "avui" → data actual; "ahir" → -1 dia; "el dilluns" → últim dilluns. Si no hi ha indicació → avui. |
| `concepte` | `str` | Curt (≤40 chars). Mai inventar — si no se sap, usar "Despesa varia" o "Tiquet". |
| `establiment` | `str` | Lloc/comerç. Pot estar buit (`""`). |
| `quantitat` | `float` | Sempre **positiu en valor absolut**. El signe el corregeix `corregir_signe()` segons `tipus`. |
| `categoria` | `str` | **D'una llista tancada** (vegeu sota). Mai inventar categories. |
| `tipus` | `str` | `"Despesa"` o `"Ingrés"`. Cap altra. |
| `es_periodic` | `bool` | `true` només si l'usuari ho indica explícitament o és un cas obvi (lloguer, nòmina). |

### Categories vàlides (tancades)

Despeses: `Llar`, `Subscripcions`, `Alimentació`, `Restauració`, `Transport`, `Salut`, `Oci`, `Roba`, `Deute`, `Altres`.
Ingressos: `Nòmina`, `Lloguer_Ingrés`, `Freelance`, `Bizum`, `Devolució`, `Ajut_Públic`, `Altres_Ingrés`.

**Sempre incloure-les explícitament al prompt.** Gemini tendeix a improvisar ("Comestibles" en lloc d'"Alimentació") si no es força.

## Plantilles de prompt

### Extracció des de text

```python
def prompt_text(text_usuari: str) -> str:
    return f"""AVUI ÉS: {date.today().isoformat()} (format ISO YYYY-MM-DD).

Tasca: Extreure moviments financers del text de l'usuari.
Retorna NOMÉS un array JSON. Sense text addicional, sense markdown wrappers.

Schema per moviment:
{{
  "data": "YYYY-MM-DD",
  "concepte": "string ≤40 chars",
  "establiment": "string (pot ser buit)",
  "quantitat": número positiu (mai negatiu),
  "categoria": una de [Llar, Subscripcions, Alimentació, Restauració,
                       Transport, Salut, Oci, Roba, Deute, Altres,
                       Nòmina, Lloguer_Ingrés, Freelance, Bizum,
                       Devolució, Altres_Ingrés],
  "tipus": "Despesa" o "Ingrés",
  "es_periodic": true/false
}}

Regles:
- "Ahir" → resta 1 dia a {date.today().isoformat()}.
- "El dilluns" → últim dilluns passat.
- Si no hi ha data clara → avui.
- "47€ Mercadona" → categoria Alimentació, tipus Despesa.
- "Cobrat 200 Bizum" → categoria Bizum, tipus Ingrés.
- "Quota gym mensual 30€" → categoria Subscripcions, es_periodic true.

Si hi ha múltiples moviments al text, retorna múltiples elements.

Text de l'usuari:
\"\"\"{text_usuari}\"\"\"
"""
```

### Extracció des d'imatge (tiquet)

```python
def prompt_tiquet() -> str:
    return f"""AVUI ÉS: {date.today().isoformat()}.

Tasca: Llegir un tiquet de compra (foto). Extreure cada producte com un moviment separat.
O, si el tiquet és global (sense desglossament), un sol moviment amb el total.

Retorna NOMÉS un array JSON. Mateix schema que la pipeline d'extracció de text.

Categories vàlides: Llar, Subscripcions, Alimentació, Restauració, Transport,
Salut, Oci, Roba, Deute, Altres.

Regles especials:
- Establiment: extreure'l de la capçalera del tiquet.
- Data: la del tiquet, no avui. Si no es veu, posar avui.
- Tipus: sempre "Despesa" (els tiquets són despeses).
- es_periodic: sempre false.
- Si la foto és il·legible, retorna [].
"""
```

### Assessor financer

```python
def prompt_assessor(ingr: float, desp: float, resum_categories: str) -> str:
    return f"""Actua com un assessor financer expert per a una família catalana
(Jose Manuel i Alba) en transició cap a autònom.

CONTEXT:
- Jose Manuel: a punt de ser autònom (web/SEO/edició).
  Ingressos actuals 800–1.000€/mes amb previsió creixent.
  Tarifa plana 80€/mes el primer any (real ~88,64€ amb MEI 0,9%).
  Provisió necessària: ~20% IRPF + IVA si factura amb IVA.
- Alba: nòmina ~1.300€/mes (estable).
- Ingrés extra: lloguer 550€/mes (recurrent).
- Localització: Calders, Bages, Catalunya.

DADES DEL PERÍODE:
- Ingressos totals: {ingr:.2f}€
- Despeses totals: {desp:.2f}€
- Saldo: {ingr + desp:.2f}€
- Desglossament per categoria:
{resum_categories}

TASCA: Generar exactament 3 consells:
1) Un de provisió fiscal (autònom).
2) Un de fons d'emergència o estalvi (objectiu 3–6 mesos despeses fixes).
3) Un d'optimització de despesa concreta detectada al desglossament.

FORMAT:
- Markdown amb capçaleres ##.
- To proper, en català, sense paternalisme.
- Cada consell amb: 1 frase de diagnòstic + 1 frase d'acció concreta.
- Inclou xifres concretes, no generalitats.
- Màxim 200 paraules totals.

NO incloguis: introduccions, salutacions, disclaimers, "espero que t'ajudi".
"""
```

### Detecció d'anomalies (futur)

```python
def prompt_anomalies(df_actual: str, df_historic: str) -> str:
    return f"""Compara les despeses d'aquest mes amb els 3 mesos previs.

DADES MES ACTUAL (CSV):
{df_actual}

MESOS PREVIS (CSV):
{df_historic}

Detecta:
1) Categories amb variació > 30% respecte a la mitjana.
2) Despeses individuals > 2x la mediana de la seva categoria.
3) Categories noves que no apareixien abans.

Retorna NOMÉS un array JSON:
[
  {{
    "tipus": "categoria_alta" | "despesa_individual" | "categoria_nova",
    "categoria": "string",
    "missatge": "string ≤100 chars en català",
    "variacio_pct": número (signed),
    "valor": número
  }}
]

Si no detectes res, retorna [].
"""
```

## Parsing robust

`parsejar_json_ia()` ha de:
1. Eliminar wrappers ` ```json ... ``` ` i ` ``` ... ``` `.
2. Eliminar text abans del primer `[` o `{`.
3. Eliminar text després de l'últim `]` o `}`.
4. Convertir `dict` → `[dict]` per uniformitat.
5. Si tot falla, raise `json.JSONDecodeError` amb missatge clar.

```python
def parsejar_json_ia(text: str) -> list[dict]:
    txt = text.strip()
    # 1. Remove markdown wrappers
    for wrapper in ["```json", "```JSON", "```"]:
        txt = txt.replace(wrapper, "")
    txt = txt.strip()
    # 2. Find first JSON token
    inici_arr, inici_obj = txt.find("["), txt.find("{")
    candidats = [i for i in [inici_arr, inici_obj] if i >= 0]
    if not candidats:
        raise json.JSONDecodeError("Cap estructura JSON trobada", txt, 0)
    inici = min(candidats)
    # 3. Find last closing token
    fi_arr, fi_obj = txt.rfind("]"), txt.rfind("}")
    fi = max(fi_arr, fi_obj) + 1
    txt = txt[inici:fi]
    # 4. Parse
    dades = json.loads(txt)
    # 5. Normalitzar a llista
    if isinstance(dades, dict):
        dades = [dades]
    return dades
```

## Validació posterior (Pydantic recomanat)

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date

CATEGORIES_VALIDES = {
    "Llar", "Subscripcions", "Alimentació", "Restauració", "Transport",
    "Salut", "Oci", "Roba", "Deute", "Altres",
    "Nòmina", "Lloguer_Ingrés", "Freelance", "Bizum", "Devolució",
    "Ajut_Públic", "Altres_Ingrés",
}

class Moviment(BaseModel):
    data: date
    concepte: str = Field(max_length=80)
    establiment: str = ""
    quantitat: float
    categoria: str
    tipus: str
    es_periodic: bool = False

    @field_validator("categoria")
    @classmethod
    def categoria_valida(cls, v: str) -> str:
        if v not in CATEGORIES_VALIDES:
            return "Altres"  # fallback silent
        return v

    @field_validator("tipus")
    @classmethod
    def tipus_valid(cls, v: str) -> str:
        if v.strip().lower() in {"ingrés", "ingres", "income"}:
            return "Ingrés"
        return "Despesa"

    @field_validator("quantitat")
    @classmethod
    def quantitat_absoluta(cls, v: float) -> float:
        return abs(float(v))  # el signe es posa després segons tipus
```

## Què no fer

- ❌ No demanar al model que retorni text formatat per humans + JSON. Una sola cosa.
- ❌ No incloure exemples de JSON dins del prompt si no són literals — el model els pot copiar.
- ❌ No fer prompts amb >5 instruccions seguides — Gemini en falla d'una.
- ❌ No assumir que el `tipus` arribarà ben capitalitzat (`"Ingrés"` vs `"INGRES"` vs `"income"`). Sempre normalitzar.
- ❌ No deixar `data` sense format — sempre exigir ISO.
- ❌ No deixar categories obertes — sempre llista tancada al prompt.
- ❌ No oblidar que `model.generate_content` pot fallar per quota — sempre via `amb_reintents()`.

## Quan ampliar la skill

Si afegeixes un cas d'ús nou (per exemple, "categoritzador automàtic basat en historial"), afegeix la plantilla aquí i les seves regles. Manté l'esquema JSON consistent o documenta clarament quan canvia.
