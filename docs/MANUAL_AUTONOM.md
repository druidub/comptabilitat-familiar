# 🧾 Pestanya Autònom — Manual d'ús

> Guia de la feature d'autònoms de **Família Finances v2.8**.
> Última actualització: abril 2026, basada en RDL 16/2025 (quotes 2026 prorrogades).

---

## Què fa aquesta feature

Acompanya el procés de fer-se autònom: simula què passarà abans de l'alta, calcula què cal apartar de cada factura un cop estiguis donat d'alta, fa seguiment del Tiquet Rural i recorda venciments trimestrals. **No** substitueix un gestor — és una eina d'autoconsciència fiscal.

## Els dos modes

L'app detecta automàticament en quin mode estàs segons un únic camp: **`data_alta_real`** a la configuració.

### 🔮 Mode preview *(actiu ara mateix)*

Mentre `data_alta_real` estigui buida, l'app entén que encara no s'ha donat d'alta i mostra simulacions. No es generen buffers ni venciments — tot és hipotètic.

**Què veuràs**:
- Header lila amb "Mode Preview" i la data prevista d'alta.
- Slider d'ingressos mensuals previstos (500–3.000€).
- 4 mètriques que canvien en temps real segons el slider:
  - **Tram estimat** (1–15) i interval mensual de rendiments.
  - **Quota amb tarifa plana** (88,64€/mes durant 12 mesos).
  - **Quota després de tarifa plana** (la del tram estimat).
  - **Net per factura**, descomptats IVA, IRPF i SS proporcional.
- Detall de provisió per a una factura mitjana.

**Per què serveix**: veure abans d'hora què guanyaràs realment al mes i quan saltarà la quota un cop acabi la tarifa plana. Si mous el slider a 1.500€ i veus que la quota saltarà a ~294€/mes, et serveix per planificar.

### 🟢 Mode operatiu *(quan ja siguis autònom)*

Quan omplis `data_alta_real`, l'app passa a operatiu:

**Què veuràs**:
- Header verd amb la data d'alta real.
- 4 mètriques amb dades reals:
  - **Tarifa plana**: mesos restants (X/12) o "Acabada".
  - **Tram actual**: calculat amb la mitjana dels últims 3 mesos de moviments amb categoria `Freelance`.
  - **Total apartat aquest trimestre**: suma d'IVA + IRPF + SS provisionats.
  - **Pròxim venciment**: quina data i quants dies queden.
- Buffers detallats amb 3 progress bars (IVA, IRPF, SS) i codi de colors verd/groc/vermell segons cobertura.

## La configuració, camp per camp

Pots editar-ho tot a l'expander **⚙️ Configuració d'autònom** dins de la pestanya.

| Camp | Què és | Per a què |
|------|--------|-----------|
| `data_alta_prevista` | Data en què preveus donar-te d'alta | Mostra la previsió al header del mode preview |
| `data_alta_real` | Data efectiva d'alta a la SS | **Determina el mode**: buida = preview, omplerta = operatiu |
| `tarifa_plana_prorrogada` | Si has obtingut la pròrroga del 2n any | Allarga la tarifa plana 12 mesos més |
| `iva_per_defecte` | Si les teves factures duen IVA per defecte | Marca el camp `aplica_iva` automàticament a cada nou ingrés |
| `factures_aprox_mes` | Quantes factures emets de mitjana al mes | Es divideix la quota mensual per saber quant apartar de cada factura |
| `retencio_irpf_pct` | 0%, 7% o 15% | Si factures a empreses (que retenen), aquí. Si factures a particulars, 0% |
| `tiquet_rural_estat` | sollicitat / concedit / denegat / pagat / no_aplica | Per al seguiment de l'ajut |
| `tiquet_rural_quantia` | Import del Tiquet Rural | Si es concedeix |
| `tiquet_rural_data_resolucio` | Quan vas saber/sabràs la resolució | Recordatori |

> **Important**: després d'editar i prémer "Desar configuració", l'app refresca tota la pestanya amb els nous valors.

## Com s'introdueixen els ingressos d'autònom

Quan facturis com a freelance, afegeix el moviment com sempre amb una particularitat:

- **Categoria**: ha de ser exactament `Freelance`. Si poses una altra categoria, l'app no ho comptarà com a ingrés d'autònom als càlculs de tram ni de buffers.
- **Camp `aplica_iva`**: marca `TRUE` si la factura porta IVA (la majoria de serveis web), `FALSE` si és exempta (per exemple, formació reglada, alguns serveis sanitaris).
- **Tipus**: `Ingrés`.

L'app processarà aquest moviment per:
1. Sumar-lo al càlcul del rendiment net mensual (i per tant, el tram).
2. Si `aplica_iva = TRUE`, apartar el 21% al buffer d'IVA.
3. Apartar el % corresponent al buffer d'IRPF segons `retencio_irpf_pct` configurat.
4. Apartar la part proporcional de la quota SS al buffer de SS.

> **No barregis** ingressos personals (Bizum, devolucions...) amb la categoria `Freelance`. Si fas una feina freelance i et paguen per Bizum, segueix sent `Freelance`, no `Bizum`.

## Els tres buffers explicats

Els buffers són "guardiols mentals". L'app no toca diners, només calcula què hauries d'haver apartat. La idea és que cada cop que cobres una factura, **transfereixes manualment** la part corresponent a un compte separat (el teu "compte d'autònom") perquè no et trobis al venciment trimestral sense liquiditat.

### 🟦 Buffer IVA (Modelo 303, trimestral)

- Cada factura amb IVA repercutit (21%) genera buffer.
- L'objectiu trimestral és la suma de tot l'IVA cobrat al trimestre.
- **Què hauràs de pagar**: aquesta xifra menys l'IVA suportat (el que has pagat tu en despeses deduïbles amb factura).
- **Quan es paga**: 1–20 d'abril, juliol, octubre / 1–30 de gener.

### 🟪 Buffer IRPF (Modelo 130, trimestral)

- Si NO factures amb retenció (clients particulars), apartes el 20% de cada cobrament.
- Si factures amb retenció (clients empreses, normalment 15% o 7% els primers 3 anys), el client ja paga aquesta part a Hisenda en nom teu — el buffer és menor o zero.
- L'objectiu trimestral és el 20% del rendiment net acumulat menys el ja pagat per retencions.
- **Quan es paga**: mateixos terminis que l'IVA.

### 🟧 Buffer SS (cuota mensual)

- És l'estimació de quant has de pagar a la Seguretat Social cada mes.
- Mentre tinguis tarifa plana: 88,64€/mes.
- Quan acabi: la del tram corresponent als teus rendiments reals.
- L'app reparteix proporcionalment la quota mensual entre les factures previstes.
- **Quan es paga**: mensualment, càrrec automàtic a finals de mes.

### El codi de colors

| Color | Llindar | Què vol dir |
|-------|---------|-------------|
| 🟢 Verd | ≥ 100% | Cobert. Quan arribi el venciment tens els diners |
| 🟡 Groc | 70–99% | Atenció. Probablement t'arribarà just |
| 🔴 Vermell | < 70% | Risc. Has gastat el que havies de provisionar |

## Tiquet Rural

L'ajut Leader del Departament d'Agricultura per crear microempreses no agràries en zones rurals (Calders compleix). Fins a 35.000€ a tant alçat.

**Particularitat fiscal important**:

> El Tiquet Rural tributa com a **guany patrimonial** a l'IRPF, no com a rendiment d'activitat. Per això **no s'inclou** al càlcul del tram ni dels buffers de l'app. Quan el rebis, tractar com a ingrés extraordinari amb categoria `Ajut_Públic`.

L'app fa seguiment de l'estat sense fer-ne càlculs:
- **Sol·licitat**: card neutra amb data prevista de resolució.
- **Concedit / Pagat**: card verda amb la quantia + avís fiscal.
- **Denegat**: card neutra amb missatge per a la propera convocatòria.
- **No aplica**: la secció no es mostra.

> **Compromisos del Tiquet Rural**: 5 anys mantenint l'activitat com a principal. Si la deixes abans, has de retornar l'ajut.

## El moment crític: quan acaba la tarifa plana

Aquest és el risc principal de la transició. Després de 12 mesos (24 si has sol·licitat la pròrroga i compleixes requisits — rendiments < SMI), la quota deixa de ser ~89€/mes i passa a ser la del teu tram real.

**Exemple amb les xifres actuals previstes**:

| Ingressos bruts/mes | Rendiment net mensual aprox. | Tram | Quota SS sense tarifa plana |
|---------------------|------------------------------|------|----------------------------|
| 800€ | ~600€ | 1 | **200€/mes** |
| 1.000€ | ~755€ | 2 | **220€/mes** |
| 1.500€ | ~1.150€ | 4 | **~291€/mes** |
| 2.000€ | ~1.530€ | 7 | **~350€/mes** |

> El salt va de 89€ a 200–350€ segons els ingressos. **Aprofita el primer any per crear coixí**: si pots, aparta cada mes la diferència entre la quota futura i la tarifa plana actual. Et trobaràs preparat quan arribi el canvi.

L'app t'avisarà al header quan quedin **menys de 3 mesos** de tarifa plana per recordar-ho.

## Calendari fiscal a recordar

| Període | Models a presentar |
|---------|-------------------|
| 1–20 abril | Modelo 130 (IRPF Q1) i 303 (IVA Q1) |
| 1–20 juliol | Modelo 130 i 303 (Q2) |
| 1–20 octubre | Modelo 130 i 303 (Q3) |
| 1–30 gener (any següent) | Modelo 130 i 303 (Q4) + Modelo 390 (resum anual IVA) |
| Abril–juny | Declaració de la renda (Modelo 100) |

L'app t'avisa al pròxim venciment automàticament a la mètrica corresponent.

## Què NO fa l'app *(i per què)*

- **No presenta models per tu**. Els hauràs de presentar a la seu electrònica de l'AEAT o a través de gestor.
- **No transfereix diners als buffers**. Els càlculs són mentals — has de moure els diners tu manualment a un compte separat.
- **No detecta IVA suportat automàticament**. Si vols rebaixar el buffer IVA segons les teves despeses deduïbles, anota-les al sistema com a despeses i el càlcul ho contemplarà (Fase 3+).
- **No substitueix un gestor fiscal**. Per al primer any com a autònom és molt recomanable tenir-ne un, almenys per a la presentació de models i la declaració de la renda. Cost típic: 30–60€/mes.
- **No reflecteix canvis legals posteriors a abril 2026**. Si Hisenda o la SS canvien quotes/trams a meitat d'any, els valors poden quedar desfasats. La skill `autonom-fiscal` del projecte caldria actualitzar-la.

## Flux típic recomanat

### Abans de l'alta *(fase actual)*

1. Mantenir `tiquet_rural_estat = "sollicitat"` mentre esperes resolució (setembre).
2. Anar movent el slider del simulador a mesura que tens previsions més clares d'ingressos.
3. Quan sàpigues la resolució del Tiquet Rural, actualitzar l'estat i la quantia.

### El dia de l'alta

1. Anar a Configuració d'autònom i omplir **`data_alta_real`** amb la data efectiva.
2. Confirmar `factures_aprox_mes` i `retencio_irpf_pct` segons com facturis.
3. L'app passa automàticament a mode operatiu.

### Cada cop que cobres una factura

1. Afegir moviment amb categoria `Freelance` i `aplica_iva` correcte.
2. Mirar a la pestanya Autònom el nou estat dels buffers.
3. Transferir manualment al compte d'estalvi d'autònom: IVA + IRPF + SS proporcional.

### Cada inici de trimestre

1. Mirar el "Pròxim venciment" a la mètrica.
2. Validar amb el gestor (o tu mateix amb l'AEAT) les xifres a presentar.
3. Pagar models 130 i 303.

### Cada any al gener

1. Modelo 390 (resum anual IVA).
2. Revisar la regularització de la SS (poden tornar diners o demanar-ne, segons rendiments reals).
3. Preparar documentació per a la declaració de la renda d'abril.

## Recursos externs

- [Simulador oficial cuotas RETA](https://portal.seg-social.gob.es/wps/portal/importass/importass/tramites/simuladorRETAPublico)
- [AEAT — Modelo 130](https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G601.shtml)
- [AEAT — Modelo 303](https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G414.shtml)
- [Tiquet Rural — Generalitat](https://desenvolupamentrural.gencat.cat)
- [Infoautónomos](https://www.infoautonomos.com/) — articles divulgatius

---

*Aquest manual viu al projecte i s'ha d'actualitzar quan canviïn les regles fiscals o s'afegeixin funcionalitats. La font de veritat tècnica és la skill `autonom-fiscal` a `.claude/skills/`.*
