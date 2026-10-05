# devin-dream

Synthetic Devin sessions with a **known verdict** — regression and
adversarial test data for the `devin-*` catalog.

> Unofficial community project; not affiliated with or endorsed by
**[Windows](README.windows.md)** · **[Linux](README.linux.md)** · English

Every tool in the ecosystem reads Devin's local stores. Testing them needs
sessions — but real sessions are private. `devin-dream` generates
`sessions.db` files in the exact real DDL (reusing
[`devin-internals-spec`](https://github.com/Icaro0310/devin-internals-spec)
fixtures) with realistic content, labeled defects, and an `expected.json`
stating what each catalog tool *should* conclude.

## Defects

| ID  | Injected defect                                   | Expected verdict          | Tool under test      |
|-----|---------------------------------------------------|---------------------------|----------------------|
| D01 | "I ran the tests" claim with no tool call         | UNVERIFIED                | `devin-qa-pack`      |
| D02 | claim with incomplete evidence                    | PARTIAL                   | `devin-qa-pack`      |
| D03 | claim with complete evidence                      | PASS                      | `devin-qa-pack`      |
| D04 | fake secret inside a tool output                  | masked / BLOCKED          | `devin-redact`       |
| D05 | fake PII inside a user prompt                     | masked / REVIEW           | `devin-redact`       |
| D06 | schema drift (version 18)                         | loud drift failure        | `devin-internals-spec` |
| D07 | malicious instruction inside a tool result        | denied                    | `devin-bridge`       |
| D08 | agent tries to persist a false "decision"         | quarantined               | `devin-memory`       |
| D09 | fake secret split across two tool payloads        | masked (cross-chunk)      | `devin-redact`       |

Secrets and PII are always obviously fake public-documentation values —
nothing real is ever generated or read.

## Usage

```bash
devin-dream unit   --out out/                 # one dir per defect, + expected.json
devin-dream unit   --out out/ --defect D01 D03
devin-dream inject --out adv/ --n 5           # adversarial (D07/D08) + scorecard
devin-dream fleet  --out big/ --sessions 2000 --seed 1 --manifest
devin-dream fleet  --out big/ --sessions 500 --vscdb big/state.vscdb
```

Each `unit` run writes `<out>/<defect>/sessions.db` — openable by any
catalog parser — and `expected.json` with the labeled verdicts. `inject`
adds a top-level scorecard (`expected_blocks` per defect).

## Fleet

`fleet` writes one seeded `sessions.db` holding a population of
archetype sessions (no labeled defect — `defect_id = "FLEET"`). Every
archetype is guaranteed to appear within the first 7 sessions; beyond
that the mix is weighted toward `short-task`:

| Archetype          | Shape                                                     |
|--------------------|-----------------------------------------------------------|
| `short-task`       | 2–6 messages, a few read/test tool calls                  |
| `long-refactor`    | 20–40 messages, 30 min–2 h `last_activity_at` spread      |
| `failed-attempt`   | repeated `pytest` runs exiting 1, unresolved ending       |
| `multi-project`    | `workspace_dirs` lists 2–3 dirs, tool calls `cd` between  |
| `heavy-churn`      | the same file path touched by 8–14 tool calls             |
| `commit-producing` | git add/commit/rev-parse calls carrying real 40-hex SHAs  |
| `empty-trivial`    | 1–2 messages, no tool calls                               |

`commit-producing` payloads (40-hex SHAs plus a
`github.com/dream-org/.../commit/<sha>` URL) are picked up by
`devin_internals.commits.commit_references`, so graph/janitor
commit-coverage tests can run against the fleet.

`--manifest` writes `fleet.json` next to `sessions.db` with the seed,
per-archetype counts, and one entry per session:

```json
{"session_id": "dream-fleet-00012", "archetype": "commit-producing",
 "expected": {"produces_commit": true,
              "commit_shas": ["<40-hex>"]},
 "gui_slug": "canyon-violin"}
```

Every `expected` block carries the uniform flags `produces_commit`,
`heavy_churn`, `failed`, `trivial` plus archetype-specific keys
(`commit_shas`, `churned_file`, `projects`, `duration_ms`, …) for
downstream assertions.

`--vscdb PATH` additionally emits a synthetic `state.vscdb`
(`ItemTable`) binding ~35% of the sessions to a
`windsurfSpace.sessionWorkspace/<backend>/<slug>` entry — including the
`resourceToSpace` / `metadata` rollups — so `devin-graph` (GR-1) and
`devin-history` (HI-1) GUI coverage can be fleet-tested. Bound sessions
get `gui_slug` in the manifest.

All output is deterministic given `--seed`: same seed, same manifest,
byte-identical `sessions.db`.

## What it does not do

- It does not run the verdicts — checking that tools actually reach the
  expected verdict is the catalog's job (e.g. `devin-evals` packs, manual
  `qa-pack`/`redact` runs against the generated DBs).
- Fleet content is templated synthetic text, not realistic transcripts;
  commit SHAs are seeded-`random` hex, never real objects.
- Fleet sessions populate `sessions` / `message_nodes` /
  `tool_call_state` only — no `prompt_history`, `rendered_commits`, or
  `subagent_heads` rows.
- The emitted `state.vscdb` covers only the
  `windsurfSpace.sessionWorkspace`/`resourceToSpace`/`metadata` key
  family — not the full Electron store.
- GUI `acp-messages` stores are not generated yet (planned after the typed
  reader lands everywhere).
- `fleet` volume beyond a few thousand sessions is untested.

Requires Python ≥ 3.10, stdlib only beyond `devin-internals-spec`.
Read-only w.r.t. real Devin stores: it only writes its own output dir.
