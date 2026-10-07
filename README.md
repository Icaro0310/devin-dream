<div align="center">

# devin-dream — MOVED

**This repository was absorbed into
[`devin-evals`](https://github.com/Icaro0310/devin-evals).**

The code now lives at `src/devin_evals/dream/` and the CLI moved to
`devin-evals dream {unit,inject,fleet}` — same commands, same defect
catalogue (D01–D09), one package instead of two.

```bash
# before
devin-dream unit --out out/ --defect D01 D03

# after
devin-evals dream unit --out out/ --defect D01 D03
```

The repository is archived; open issues were migrated to devin-evals.
History remains readable here for reference.

</div>

---

<details>
<summary>Original README (pre-archive)</summary>

<div align="center">

<a href="https://github.com/Icaro0310/devin-dream/actions/workflows/ci.yml"><img src="https://github.com/Icaro0310/devin-dream/actions/workflows/ci.yml/badge.svg" alt="ci"/></a>

<a href="https://scorecard.dev/viewer/?uri=github.com/Icaro0310/devin-dream"><img src="https://api.scorecard.dev/projects/github.com/Icaro0310/devin-dream/badge" alt="OpenSSF Scorecard"/></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT"/></a>
<a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"/></a>
<a href="https://github.com/Icaro0310/devin-dream"><img src="https://img.shields.io/github/stars/Icaro0310/devin-dream" alt="GitHub stars"/></a>
<a href="https://github.com/Icaro0310/devin-dream/commits/main"><img src="https://img.shields.io/github/last-commit/Icaro0310/devin-dream" alt="Last commit"/></a>
<a href="https://github.com/Icaro0310/awesome-devin"><img src="https://img.shields.io/badge/part%20of-devin--*-ecosystem-7c3aed" alt="devin-* ecosystem"/></a>
<a href="https://github.com/Icaro0310/devin-dream/issues"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome"/></a>
</div>

# devin-dream

Synthetic Devin sessions with a **known verdict** — regression and
adversarial test data for the `devin-*` catalog.

> Unofficial community project; not affiliated with or endorsed by
**[Linux](README.linux.md)** · **[Personal Windows](README.windows.md)** · **[Corporate Windows](README.corporate-windows.md)**

Part of the [awesome-devin](https://github.com/Icaro0310/awesome-devin) ecosystem: the curated hub for the devin-* tools.

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

## Install

<!-- DIST-STATUS:BEGIN — generated from devin-powerups/registry.json -->
> **Source-only distribution.** This tool is not yet published to PyPI.
> Install from source:
>
> ```bash
> pipx install git+https://github.com/Icaro0310/devin-dream.git
> # or
> uv tool install git+https://github.com/Icaro0310/devin-dream.git
> ```
<!-- DIST-STATUS:END -->

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


</details>
