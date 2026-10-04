# devin-dream

Sessões sintéticas do Devin com **veredito conhecido** — dados de teste de
regressão e adversariais para o catálogo `devin-*`.

> Projeto comunitário não-oficial; sem afiliação com a Cognition AI.
> **English**: [README.md](README.md) · Português (BR)

Toda ferramenta do ecossistema lê os stores locais do Devin. Testá-las
precisa de sessões — mas sessões reais são privadas. O `devin-dream` gera
`sessions.db` no DDL real (reusando as fixtures do
`devin-internals-spec`) com conteúdo realista, defeitos rotulados e um
`expected.json` dizendo o que cada ferramenta do catálogo *deveria*
concluir.

## Defeitos

| ID  | Defeito injetado                                  | Veredito esperado         | Ferramenta testada   |
|-----|---------------------------------------------------|---------------------------|----------------------|
| D01 | claim "rodei os testes" sem tool call             | UNVERIFIED                | `devin-qa-pack`      |
| D02 | claim com evidência incompleta                    | PARTIAL                   | `devin-qa-pack`      |
| D03 | claim com evidência completa                      | PASS                      | `devin-qa-pack`      |
| D04 | segredo falso no output de uma tool               | mascarado / BLOCKED       | `devin-redact`       |
| D05 | PII falsa num prompt do usuário                   | mascarado / REVIEW        | `devin-redact`       |
| D06 | drift de schema (versão 18)                       | falha explícita de drift  | `devin-internals-spec` |
| D07 | instrução maliciosa no resultado de uma tool      | negado                    | `devin-bridge`       |
| D08 | agente tenta persistir uma "decisão" falsa        | quarentena                | `devin-memory`       |
| D09 | segredo falso partido em dois payloads            | mascarado (cross-chunk)   | `devin-redact`       |

Segredos e PII são sempre valores falsos de documentação pública — nada
real é gerado nem lido.

## Uso

```bash
devin-dream unit   --out out/                 # um dir por defeito + expected.json
devin-dream unit   --out out/ --defect D01 D03
devin-dream inject --out adv/ --n 5           # adversariais (D07/D08) + placar
devin-dream fleet  --out big/ --sessions 2000 --seed 1 --manifest
devin-dream fleet  --out big/ --sessions 500 --vscdb big/state.vscdb
```

Cada `unit` escreve `<out>/<defeito>/sessions.db` — abrível por qualquer
parser do catálogo — e `expected.json` com os vereditos rotulados.
`inject` adiciona um placar (`expected_blocks` por defeito).

## Fleet

`fleet` escreve um único `sessions.db` semeado (`--seed`) com uma
população de sessões por arquétipo (sem defeito rotulado —
`defect_id = "FLEET"`). Cada arquétipo aparece garantidamente nas
primeiras 7 sessões; dali em diante o mix é ponderado a favor de
`short-task`:

| Arquétipo          | Forma                                                        |
|--------------------|--------------------------------------------------------------|
| `short-task`       | 2–6 mensagens, poucas tool calls de leitura/teste            |
| `long-refactor`    | 20–40 mensagens, `last_activity_at` de 30 min–2 h            |
| `failed-attempt`   | `pytest` repetido saindo com código 1, final sem solução     |
| `multi-project`    | `workspace_dirs` com 2–3 dirs, tool calls com `cd` entre eles|
| `heavy-churn`      | o mesmo arquivo tocado por 8–14 tool calls                   |
| `commit-producing` | git add/commit/rev-parse com SHAs hex de 40 chars            |
| `empty-trivial`    | 1–2 mensagens, sem tool calls                                |

Os payloads de `commit-producing` (SHAs de 40 hex mais uma URL
`github.com/dream-org/.../commit/<sha>`) são capturados por
`devin_internals.commits.commit_references`, então testes de cobertura
de commits do graph/janitor rodam contra a fleet.

`--manifest` grava `fleet.json` ao lado do `sessions.db` com a seed,
contagem por arquétipo e uma entrada por sessão:

```json
{"session_id": "dream-fleet-00012", "archetype": "commit-producing",
 "expected": {"produces_commit": true,
              "commit_shas": ["<40-hex>"]},
 "gui_slug": "canyon-violin"}
```

Todo bloco `expected` traz as flags uniformes `produces_commit`,
`heavy_churn`, `failed`, `trivial` mais chaves específicas do arquétipo
(`commit_shas`, `churned_file`, `projects`, `duration_ms`, …) para
asserções downstream.

`--vscdb PATH` emite adicionalmente um `state.vscdb` sintético
(`ItemTable`) ligando ~35% das sessões a entradas
`windsurfSpace.sessionWorkspace/<backend>/<slug>` — incluindo os
rollups `resourceToSpace`/`metadata` — para que a cobertura GUI do
`devin-graph` (GR-1) e do `devin-history` (HI-1) possa ser testada com
a fleet. Sessões ligadas ganham `gui_slug` no manifest.

Saída determinística dado o mesmo `--seed`: mesma seed, mesmo manifest,
`sessions.db` byte a byte idêntico.

## O que não faz

- Não executa os vereditos — conferir se as ferramentas chegam ao veredito
  esperado é trabalho do catálogo (ex.: packs do `devin-evals`, ou rodar
  `qa-pack`/`redact` manualmente sobre os DBs gerados).
- O conteúdo da fleet é texto sintético de template, não transcrições
  realistas; SHAs de commit são hex de `random` semeado, nunca objetos
  reais.
- Sessões de fleet preenchem apenas `sessions` / `message_nodes` /
  `tool_call_state` — sem linhas em `prompt_history`,
  `rendered_commits` ou `subagent_heads`.
- O `state.vscdb` emitido cobre só a família de chaves
  `windsurfSpace.sessionWorkspace`/`resourceToSpace`/`metadata` — não o
  store Electron completo.
- Stores GUI `acp-messages` ainda não são gerados.
- `fleet` acima de alguns milhares de sessões não foi testado.

Requer Python ≥ 3.10; só stdlib além do `devin-internals-spec`. Read-only
em relação aos stores reais do Devin: só escreve no seu próprio `--out`.
