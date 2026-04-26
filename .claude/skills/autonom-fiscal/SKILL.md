---
name: autonom-fiscal
description: Càlculs fiscals i de Seguretat Social per a autònoms a Espanya, vigents el 2026. Activa aquesta skill SEMPRE que es treballi amb quotes d'autònom, RETA, tarifa plana, IRPF d'autònom (Modelo 130), IVA (Modelo 303), trams de cotització per rendiments nets, regularitzacions de la SS, MEI, o qualsevol provisió fiscal del mòdul "Autònom" de l'app. Inclou la taula completa de 15 trams 2026 (congelats segons RDL 16/2025), tarifa plana 80€ (88,64€ amb MEI), tipus de cotització total 31,4%, regla del 7% de despeses de difícil justificació, i fórmules per a Modelo 130 i 303. Fes-la servir TAMBÉ quan l'usuari només digui "calcula què haig de pagar", "afegeix funcionalitat fiscal", "què he d'apartar aquest mes", encara que no anomeni explícitament autònom.
---

# Autònom Fiscal — Regles 2026 (Espanya)

> **Avís**: Aquesta skill conté les regles vigents quan es va escriure (gener 2026, RDL 16/2025). El sistema fiscal espanyol pot canviar a meitat d'any. Si detectes que han passat més de 6 mesos des de l'última actualització, recomana a l'usuari verificar a la Seguretat Social i AEAT abans de prendre decisions importants.
>
> **Pepe especialment**: aquesta skill és informativa. Per qualsevol decisió real (registre, presentació de models, regularitzacions), confirma amb un gestor o assessor fiscal.

## Marc legal vigent

- **RDL 16/2025**: prorroga les quotes 2025 per a tot 2026.
- **Sistema des de 2023**: cotització segons rendiments nets reals (15 trams).
- **MEI 2026**: 0,9% (puja del 0,8% al 0,9%, anirà fins a l'1,2% el 2029).
- **Tipus total de cotització 2026**: 31,4% (inclou contingències comunes, professionals, cessament d'activitat, formació i MEI).

## Taula de cotització 2026 (15 trams)

Quotes mínimes mensuals corresponents a la base mínima de cada tram. Si l'autònom tria una base més alta, la quota augmenta proporcionalment.

### Taula reducida (rendiments nets ≤ 1.700€/mes)

| Tram | Rendiment net mensual | Base mínima | Quota mínima 2026 |
|------|----------------------|-------------|-------------------|
| 1 | ≤ 670€ | 653,59€ | **200€** |
| 2 | 670 – 900€ | 718,95€ | **220€** |
| 3 | 900 – 1.166,70€ | 849,67€ | **260€** |
| 4 | 1.166,70 – 1.300€ | 950,98€ | ~291€ |
| 5 | 1.300 – 1.500€ | 960,78€ | ~294€ |
| 6 | 1.500 – 1.700€ | 960,78€ | ~302€ |

### Taula general (rendiments nets > 1.700€/mes)

| Tram | Rendiment net mensual | Base mínima | Quota mínima 2026 |
|------|----------------------|-------------|-------------------|
| 7 | 1.700 – 1.850€ | 1.143,79€ | ~350€ |
| 8 | 1.850 – 2.030€ | 1.209,15€ | ~370€ |
| 9 | 2.030 – 2.330€ | 1.272,87€ | ~390€ |
| 10 | 2.330 – 2.760€ | 1.382,17€ | ~423€ |
| 11 | 2.760 – 3.190€ | 1.441,75€ | ~441€ |
| 12 | 3.190 – 3.620€ | 1.532,21€ | ~469€ |
| 13 | 3.620 – 4.050€ | 1.633,99€ | ~500€ |
| 14 | 4.050 – 6.000€ | 1.836,76€ | ~562€ |
| 15 | > 6.000€ | 1.928,10€ | **590€** |

> Les xifres exactes són les publicades a l'Ordre Ministerial; aquestes són aproximacions útils per a càlculs orientatius. Per a càlculs definitius, l'usuari ha de consultar el [simulador oficial de la SS](https://portal.seg-social.gob.es/wps/portal/importass/importass/tramites/simuladorRETAPublico).

## Tarifa plana

- **Primer any (12 mesos)**: 80€/mes nominal. Amb MEI 0,9% real: **~88,64€/mes**.
- **Aplicabilitat**: nous autònoms o que no han estat al RETA en els 2 anys anteriors (3 si ja s'havia gaudit abans).
- **Pròrroga 2n any**: 80€/mes durant 12 mesos més, **només si** els rendiments nets del primer any han estat per sota del SMI (2026: ~1.184€/mes brut, ~14.000€/any).
- **Col·lectius especials** (discapacitat, víctimes violència gènere, terrorisme): 24 mesos inicials, prorrogables 36 més si rendiments < SMI.
- **Catalunya** (cas de Pepe): no té quota zero general. Sí que hi ha algunes ajudes puntuals al SOC, consultables.

## Càlcul del rendiment net (clau per al tram)

Aquesta és la fórmula que la Seguretat Social usa per assignar tram:

```
rendiment_net_anual = ingressos_bruts_anuals
                    − despeses_deduïbles_anuals
                    − cuotes_RETA_pagades_any
                    − 7%_de_la_diferència_anterior  (estimació directa simplificada)

rendiment_net_mensual = rendiment_net_anual / 12
```

> Els autònoms societaris apliquen 3% en lloc de 7%.

### Exemple Pepe (estimat)

Si Pepe factura 1.000€/mes durant un any, té 100€/mes de despeses deduïbles, i paga 88,64€ de quota:
```
ingressos_bruts: 12.000€
despeses_deduïbles: 1.200€
cuotes_RETA: 88,64 × 12 = 1.063,68€
diferència: 12.000 − 1.200 − 1.063,68 = 9.736,32€
deducció 7%: 681,54€
rendiment_net_anual: 9.054,78€
rendiment_net_mensual: ~754€
→ TRAM 1 (≤670 a una mica superat) o TRAM 2 (670–900€) → quota mínima 200€ o 220€/mes (sense tarifa plana)
```

Així que quan a Pepe se li acabi la tarifa plana al cap d'un any, la quota saltarà de ~89€ a ~220€/mes (assumint el mateix nivell d'ingressos). **Aquesta és informació crítica per planificar.**

## Buffer fiscal (què s'ha d'apartar de cada cobrament)

Aquest és el càlcul que el mòdul "Autònom" de l'app ha de fer:

### Si Pepe factura SENSE retenció (factura a particulars)

```
buffer_irpf = ingres_brut × 20%   # estimació conservadora del Modelo 130
buffer_iva  = ingres_brut × 21%   # si factura amb IVA (la majoria de serveis)
buffer_ss   = quota_mensual / nombre_factures_mes  # provisió de la cuota
```

### Si Pepe factura AMB retenció (factura a empreses)

```
retencio_aplicada = ingres_brut × 15%    # o 7% els primers 3 anys (nous autònoms)
                                          # → la paga el client a Hisenda en nom seu
buffer_irpf       = 0    # ja s'ha retingut, no cal apartar més
                          # (excepció: si guanya molt, pot haver de complementar)
buffer_iva        = ingres_brut × 21%
buffer_ss         = quota_mensual / nombre_factures_mes
```

### Funció Python recomanada

```python
from dataclasses import dataclass

@dataclass
class ProvisioFiscal:
    ingres_brut: float
    iva_repercutit: float       # → guardar
    irpf_provisio: float         # → guardar (si no hi ha retenció)
    cuota_ss_provisio: float     # → guardar (proporcional)
    net_disponible: float        # → el que realment es pot gastar

def calcular_provisio(
    ingres_brut: float,
    *,
    aplica_iva: bool = True,
    retencio_irpf_pct: float = 0.0,    # 0.0, 0.07 o 0.15
    cuota_ss_mensual: float = 88.64,   # tarifa plana per defecte
    factures_aprox_mes: int = 4,
) -> ProvisioFiscal:
    iva = ingres_brut * 0.21 if aplica_iva else 0.0
    ja_retingut = ingres_brut * retencio_irpf_pct
    # IRPF a apartar = el que falta fins al 20% (estimació prudent)
    irpf_objectiu = ingres_brut * 0.20
    irpf_a_apartar = max(0.0, irpf_objectiu - ja_retingut)
    ss_proporcional = cuota_ss_mensual / max(factures_aprox_mes, 1)
    net = ingres_brut - iva - irpf_a_apartar - ss_proporcional
    return ProvisioFiscal(
        ingres_brut=ingres_brut,
        iva_repercutit=iva,
        irpf_provisio=irpf_a_apartar,
        cuota_ss_provisio=ss_proporcional,
        net_disponible=net,
    )
```

## Models trimestrals i anuals

| Model | Periodicitat | Què és | Termini |
|-------|--------------|--------|---------|
| **Modelo 130** | Trimestral | Pagament fraccionat IRPF (estimació directa). 20% del rendiment net acumulat de l'any menys el ja pagat. | 1–20 abril, juliol, octubre / 1–30 gener |
| **Modelo 303** | Trimestral | Liquidació IVA. IVA repercutit − IVA suportat. | Mateixos terminis |
| **Modelo 390** | Anual | Resum anual IVA. | 1–30 gener |
| **Modelo 100** | Anual | Declaració de la renda (IRPF). | Abril–juny |
| **Modelo 111** | Trimestral | Si Pepe té treballadors o paga professionals amb retenció. | Mateixos terminis |
| **Modelo 347** | Anual | Operacions amb tercers > 3.005,06€/any. | Febrer |

> No tothom presenta els 6: només els obligatoris segons activitat. Per a Pepe (autònom individual de serveis web sense treballadors), els crítics són **130, 303 i 390**, més la **declaració de la renda**.

## Regularització anual

- La SS compara cada any les cotitzacions provisionals (segons previsió) amb les cotitzacions reals (segons rendiments declarats a Hisenda).
- Si has cotitzat **de menys**: t'envien complement a pagar. Es pot fraccionar.
- Si has cotitzat **de més**: te'n retornen la diferència d'ofici.
- Es pot **canviar de tram fins a 6 vegades l'any** (efectes bimestrals).

## Què ha de tenir el mòdul "Autònom" de l'app

Estructura proposada per a la pestanya:

```
[Estat actual]
- Tarifa plana: activa | mesos restants: 8/12
- Tram actual estimat: 2 (rendiments 670–900€/mes)
- Cuota mensual aplicada: 88,64€

[Buffers acumulats]
- Apartat per IRPF: 245,80€ (objectiu trimestre: 320€) [▮▮▮▮▮▮▯▯ 76%]
- Apartat per IVA: 412,30€ (objectiu trimestre: 500€) [▮▮▮▮▮▮▮▯ 82%]
- Apartat per SS: 350€ (objectiu trimestre: 265,92€) [✓ cobert]

[Pròxims venciments]
- Modelo 303 (IVA Q1): venc 20 abril → estimat 412€
- Modelo 130 (IRPF Q1): venc 20 abril → estimat 245€

[Avisos]
🟡 Has facturat 3.200€ aquest mes. Si mantens aquest ritme, el tram t'apujarà
   a 5 (294€/mes) un cop acabi la tarifa plana.
```

## Què no fer

- ❌ No assumir que la quota és fixa — depèn del tram, que depèn dels rendiments.
- ❌ No oblidar el MEI quan calcules quotes — afegeix 6–24€/mes.
- ❌ No assumir 21% d'IVA per a tots els serveis — alguns són exempts (formació reglada, sanitari) o reduïts.
- ❌ No mostrar xifres exactes sense disclaimer — sempre recordar que cal validar amb gestor.
- ❌ No oblidar que la **regularització** pot fer pagar diners extra l'any següent — el buffer SS hauria de ser conservador.
- ❌ No assumir que tothom pot accedir a la tarifa plana — té requisits.

## Recursos per verificar

- [Simulador oficial cuotas RETA](https://portal.seg-social.gob.es/wps/portal/importass/importass/tramites/simuladorRETAPublico)
- [AEAT — Modelo 130](https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G601.shtml)
- [AEAT — Modelo 303](https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G414.shtml)
- [Infoautónomos](https://www.infoautonomos.com/)

> Quan l'usuari demani una xifra concreta i sigui per a una decisió real, recomana sempre contrastar amb un gestor.
