# 🏦 Família Finances — Manual general

> Guia per a tu i l'Alba per aprofitar totes les funcions de l'app.
> Versió actual: **v3.0 — Insights Edition** *(suggeriment de bump)*.
> Última actualització: abril 2026.

---

## Què és aquesta app

És el vostre tauler de control financer. Centralitza tres coses:

- **El que entra i surt** cada mes (ingressos, despeses, recurrents).
- **El que ve** (pressupostos, previsió de saldo, venciments fiscals).
- **El que crida l'atenció** (anomalies detectades, alertes, suggeriments amb IA).

Les dades viuen a Google Sheets, així que també les podeu consultar i editar des del mòbil directament al Sheet si convé.

## Com accedir-hi

- **Local** (Pepe): `streamlit run app.py` al projecte.
- **Web** (tots dos): URL del deploy a Streamlit Cloud.
- **Contrasenya**: la teniu desada al gestor de contrasenyes habitual.

## L'estructura de l'app, d'una ullada

A la barra lateral (esquerra a desktop, plegable a mòbil):

- **Filtre de període**: Aquest Mes / Mes Anterior / Aquest Any / Tot al dia.
- **Alertes actives**: pressupostos en vermell, alertes de liquiditat, anomalies destacades.
- **Tancar sessió**.

Al cos central, **6 pestanyes**:

| Pestanya | Per a què |
|----------|-----------|
| ➕ **Afegir Moviment** | Introduir despeses i ingressos (text o foto de tiquet) |
| ✏️ **Editar Dades** | Modificar moviments existents, esborrar, corregir errors |
| 🧾 **Autònom** | Mòdul fiscal complet (preview ara, operatiu al setembre) |
| 🔍 **Insights** | Detecció d'anomalies i resum IA |
| 🧠 **Assessoria IA** | Consells generals sobre el mes filtrat |
| ⚙️ **Configurar Recurrents** | Recurrents, pressupostos, configuració general |

I al dashboard principal (sempre visible dalt):
- **Hero card** del saldo del període amb delta vs mes anterior.
- **4 mètriques**: Ingressos · Despeses · Taxa d'estalvi · Dies fins final de mes.
- **Gràfic** principal amb 3 vistes (Evolució saldo · Despeses per categoria · Detall ingressos).
- **Estat dels pressupostos** (només quan filtre = Aquest Mes).
- **Previsió de saldo** als propers 30/60/90 dies.

---

## Cas d'ús 1 — Apuntar despeses ràpid

### Per text
A "Afegir Moviment", camp de text. Frases naturals com:
- *"Ahir 45€ Mercadona"*
- *"30€ gasolina dimarts passat"*
- *"Cobrat 200 Bizum"*
- *"Quota gym mensual 30€"* *(activa el flag periòdic automàticament)*

L'IA processa la frase i genera el moviment amb categoria adequada. Reviseu el resultat al "Detall últim moviment".

### Per foto de tiquet
Penjar una o **diverses** fotos a la zona "Pujar Tiquets". L'app les processa totes amb una progress bar i extreu cada producte com un moviment separat (o un de global si el tiquet no té desglossament).

> **Truc**: si el tiquet és poc llegible (paper antic, foto amb reflexos), feu-ne dos clics: un de més proper i un de més general. L'IA prioritza el que veu millor.

### Si l'IA s'equivoca
Aneu a "Editar Dades", busqueu el moviment, corregiu o esborreu. La columna `categoria` és la que solucia el 80% dels casos.

---

## Cas d'ús 2 — Quant porto gastat aquest mes?

A primer cop d'ull al dashboard:
- **Hero card**: saldo del mes ara mateix.
- **Despeses**: total acumulat fins avui.
- **Taxa d'estalvi**: percentatge del que entra que NO s'ha gastat.
- **Dies fins final de mes**: per saber el marge.

I més avall, **estat dels pressupostos** (només si filtre = Aquest Mes):
- 🟢 Verd: vas per sota del ritme esperat.
- 🟡 Groc: vas al ritme just.
- 🔴 Vermell: vas per sobre del ritme i al final de mes superaràs el pressupost.

> **Important**: l'estat compara el % consumit amb el % esperat segons el dia del mes. Per exemple, dia 15 d'un mes de 30 dies → ritme esperat 50%. Si has gastat 60% → groc. Si 75% → vermell. No és el simple "has superat el límit", és "vas a temps?".

---

## Cas d'ús 3 — Definir pressupostos

Pestanya "Configurar Recurrents", al final, secció **💰 Pressupostos mensuals per categoria**.

Editeu directament els imports (taula). Posar 0 desactiva el seguiment d'aquella categoria — útil quan no tingueu límit clar (ex: Salut, Altres).

Suggeriment de pressupostos inicials per a la vostra situació *(ajusteu-los a mesura que tingueu dades reals)*:

| Categoria | Suggeriment |
|-----------|-------------|
| Alimentació | 350–450€ |
| Restauració | 100–150€ |
| Transport | 80–120€ |
| Subscripcions | 50–80€ |
| Llar | 100–150€ (a part del lloguer) |
| Oci | 80–120€ |

> Després d'1-2 mesos d'ús, el dashboard us dirà quins pressupostos són realistes i quins són massa optimistes.

---

## Cas d'ús 4 — Què passarà amb el saldo?

Secció **🔮 Previsió de saldo** al dashboard. Mostra una corba projectada del saldo basant-se en els recurrents configurats (lloguer, nòmina, subscripcions...).

Tres mètriques superiors:
1. **Saldo previst d'aquí a 30 dies**.
2. **Saldo mínim previst** (i quin dia es produeix).
3. **Pròxim moviment gran** (factura ≥200€ en horitzó).

El gràfic mostra:
- Línia de saldo dia a dia.
- **Línia vermella discontínua**: el llindar d'alerta (per defecte 500€, configurable).
- **Punts marcats**: dies amb moviments grans (lloguer cobrat, nòmina, etc.).

Sota, **alertes detectades**: períodes futurs on el saldo baixa del llindar.

> **Configurable**: a "Configuració general" podeu canviar el llindar (per exemple a 800€ si voleu més marge) i l'horitzó per defecte (30/60/90 dies).

---

## Cas d'ús 5 — Hi ha alguna cosa estranya?

Pestanya **🔍 Insights**. L'app analitza els últims 3 mesos i detecta:

**A) Variacions per categoria** — quan una categoria s'ha disparat o ha caigut més del 30% respecte a la mitjana habitual.

> Ex: *"Restauració aquest mes: 320€ (mitjana habitual: 180€) ↑ +77.8%"*

Útil per detectar si un mes us heu desviat (vacances, esdeveniments, despesa imprevista).

**B) Despeses individuals atípiques** — moviments puntuals més de 2× la mediana de la seva categoria.

> Ex: un sopar de 142€ quan la mediana de Restauració és 30€.

Útil per recordar grans despeses puntuals que potser no tenien justificació clara, o per validar que les que es detecten tenen sentit (un aniversari, una avaria del cotxe, etc.).

**C) Categories noves** — categories que apareixen aquest mes i no als mesos previs.

> Ex: *"✨ Roba — 3 moviments aquest mes · total 187€"*

Útil per veure si està apareixent un patró de despesa nou que conscientment voleu mantenir o tallar.

### Resum amb IA

Botó **🧠 Generar resum amb IA**. Genera 3–4 paràgrafs en prosa que contextualitzen les anomalies i donen 1–2 suggerències concretes. Bàsicament, fa de "fil narratiu" sobre les xifres seques.

Cau durant 1 hora — si el premeu múltiples vegades el mateix dia, no consumeix tokens addicionals.

> **Si l'app detecta massa coses**: a "Configuració general" podeu pujar els llindars (40% en lloc de 30%, factor 2.5× en lloc de 2×) per fer-la menys sensible.

> **Si encara no detecta res**: necessita almenys 4 mesos d'històric per fer comparatives fiables. Fins llavors, mostrarà missatge informatiu.

---

## Cas d'ús 6 — Què faria un assessor financer aquest mes?

Pestanya **🧠 Assessoria IA**. Diferent de la d'Insights:
- **Insights** = detecció + explicació de coses concretes.
- **Assessoria IA** = consell estratègic general sobre el període filtrat.

Genera 3 consells:
1. Provisió fiscal (autònom).
2. Fons d'emergència o estalvi.
3. Optimització d'una despesa concreta detectada.

Útil per a una "xerrada mensual de finances" entre tots dos: obriu la pestanya, llegiu els consells, decidiu què apliqueu.

---

## Cas d'ús 7 — Mòdul d'autònoms

Manual complet a part: **`docs/MANUAL_AUTONOM.md`** *(enllaçat des de la pròpia pestanya Autònom)*.

Resum molt breu:
- **Mode preview** ara: simulador per veure què passarà al setembre amb diferents nivells d'ingressos previstos.
- **Mode operatiu** quan Pepe es doni d'alta: buffers d'IVA / IRPF / SS automàtics, pròxim venciment, estat tarifa plana.
- **Tiquet Rural**: seguiment de l'ajut amb avís fiscal específic (tributa diferent dels rendiments d'activitat).

---

## Repartiment de feina suggerit

Funciona millor si entre tots dos us repartiu la càrrega.

### Tasques diàries / setmanals
- **Apuntar moviments**: qui els fa, els apunta al moment (foto del tiquet o text). Si no, al cap d'una setmana ja no hi ha qui ho recordi.
- **Revisar el dashboard**: qualsevol dels dos, 30 segons al matí o abans de dormir.

### Tasques mensuals (~15 minuts)
- **Última setmana del mes** (junts si pot ser):
  - Mirar dashboard del mes.
  - Generar resum a Insights.
  - Llegir consells a Assessoria IA.
  - Ajustar pressupostos del mes següent si cal.

### Tasques trimestrals (Pepe, després de l'alta)
- Revisar buffers a la pestanya Autònom.
- Pagar Modelo 130 i 303 abans del venciment.
- Validar amb gestor.

### Tasques anuals
- Revisar l'estructura de categories — afegir/eliminar segons el que ha aparegut.
- Pujar llindars d'anomalies si s'ha estabilitzat el ritme i hi ha massa soroll.

---

## Quan alguna cosa va malament

| Símptoma | Possible causa | Què fer |
|----------|----------------|---------|
| Moviment apuntat amb categoria errada | L'IA no ha encertat | Editar a "Editar Dades" |
| Alertes pressupost sempre en vermell | Pressupostos massa baixos | Ajustar a la realitat dels últims 2 mesos |
| Cap anomalia detectada mai | Falta històric (< 4 mesos) | Esperar més temps |
| L'app peta amb error 429 | Quota Google Sheets superada | Esperar 60 segons i recarregar |
| Foto de tiquet no es processa | Massa gran o il·legible | Mida < 20MB i tornar a fotografiar |
| El saldo previst sembla irreal | Recurrents desactualitzats | Anar a Configurar Recurrents i revisar |

Si surt un error que no entenem, fer captura i obrir un *issue* al GitHub del projecte.

---

## Privacitat i seguretat

- Les dades viuen al vostre Google Sheet privat. Ningú més hi té accés.
- L'app llegeix amb un compte de servei limitat al Sheet concret.
- Les imatges dels tiquets es processen amb Gemini i NO s'emmagatzemen permanentment — només s'envien per a l'extracció i es descarten.
- La contrasenya d'accés està al `secrets.toml` (només Pepe la pot canviar).

> **Si perdeu el mòbil**: les dades estan al Sheet, no al dispositiu. Tanqueu sessió a través del navegador (`https://myaccount.google.com/security`) i ja està.

---

## Què hi ha previst per al futur

Pendent al roadmap:
- **Fase 6**: refactor estructura modular + tests + CI (invisible per a l'usuari, millora la mantenibilitat).
- **Fase 7 (idees a explorar)**: exportació trimestral a Excel/PDF, comparativa anual, categorització automàtica per establiment, mode només-lectura per a l'Alba per evitar edicions accidentals, backups automàtics, notificacions Telegram.

Cap d'aquestes és urgent. Primer fem servir l'app **2-3 setmanes** com està i veiem què cal de veritat.

---

## Glossari ràpid

- **Recurrent**: moviment que es repeteix cada mes/trimestre/any (lloguer, nòmina, subscripcions). Es configuren a "Configurar Recurrents".
- **Buffer**: diners "mentalment apartats" per pagar venciments futurs (només a Autònom).
- **Tarifa plana**: quota reduïda d'autònoms el primer any (~89€/mes en lloc de 200€+).
- **Variació**: diferència entre el que has gastat aquest mes en una categoria vs la mitjana habitual.
- **Llindar**: valor mínim que dispara una alerta (saldo, % anomalia, etc.).
- **Mediana**: el valor del mig en una llista ordenada — més robust que la mitjana per detectar atípics.

---

*Aquest manual viu al projecte i s'actualitza quan apareixen funcionalitats noves o canvien comportaments. Si trobeu coses que no s'expliquen aquí o que estan obsoletes, anoteu-les i actualitzem el document.*
