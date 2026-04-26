# Setup `.claude/` — Família Finances

Aquest paquet conté els fitxers fundacionals per integrar l'IA assistida (Claude Code) al projecte de finances familiars.

## Què hi ha aquí

```
finances-claude-setup/
├── .claude/
│   ├── CONTEXT.md                    # context familiar + tècnic del projecte
│   ├── ROADMAP.md                    # pla per fases amb checkboxes
│   └── skills/
│       ├── streamlit-component/
│       │   └── SKILL.md              # sistema de disseny UI
│       ├── financial-prompt/
│       │   └── SKILL.md              # convencions per a Gemini
│       └── autonom-fiscal/
│           └── SKILL.md              # regles fiscals 2026 d'autònom
├── PROMPT_FASE_0.md                  # prompt llest per pegar a Claude Code
└── README.md                         # aquest fitxer
```

## Instal·lació (1 minut)

1. Descomprimir aquest paquet **a l'arrel del repositori** del projecte de finances. Hauria de quedar:
   ```
   finances/
   ├── app.py
   ├── requirements.txt
   ├── .claude/                       # ← nou
   │   ├── CONTEXT.md
   │   ├── ROADMAP.md
   │   └── skills/
   │       ├── streamlit-component/SKILL.md
   │       ├── financial-prompt/SKILL.md
   │       └── autonom-fiscal/SKILL.md
   └── ...
   ```

2. A VS Code, obrir el projecte i el panell de Claude Code.

3. Executar `/skills` per refrescar el llistat. Han de sortir les 3 skills noves a banda de la global `ui-ux-pro-max`.

4. Si alguna no apareix, comprovar que el `SKILL.md` està al subdirectori correcte i que el frontmatter YAML és vàlid (delimitat per `---` a inici i fi, amb `name` i `description`).

## Com s'activen les skills

Les skills no estan "sempre actives". Es carreguen automàticament quan la teva petició encaixa amb el camp `description`. Per això:

- Si demanes "millora la UI del dashboard" → s'activa `streamlit-component`.
- Si demanes "afegeix un nou prompt per a una funcionalitat IA" → s'activa `financial-prompt`.
- Si demanes "calcula què he d'apartar de la factura" → s'activa `autonom-fiscal`.

No has de fer res manualment. Si veus que Claude Code no està seguint convencions, recorda-li explícitament que llegeixi la skill rellevant.

## Workflow recomanat per fase

1. Obrir `.claude/ROADMAP.md` i mirar quina és la propera tasca pendent.
2. Demanar a la conversa de claude.ai (la "general") un prompt específic per a aquesta tasca.
3. Pegar el prompt a Claude Code (Sonnet) a VS Code.
4. Revisar el diff abans d'aprovar.
5. Commit + push.
6. Marcar la casella al ROADMAP.

## Per a la Fase 0 (fixes urgents)

Tens el prompt llest a `PROMPT_FASE_0.md`. Copia'l sencer a Claude Code i deixa que treballi.
