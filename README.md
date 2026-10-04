# devin-dream

Synthetic Devin sessions with a **known verdict** — regression and
adversarial test data for the `devin-*` catalog.

> Unofficial community project; not affiliated with or endorsed by
> Cognition AI. **[Português (BR)](README.pt-BR.md)** · English

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
devin-dream fleet  --out big/ --n 2000        # realistic mix, ~55% noise sessions
```

Each `unit` run writes `<out>/<defect>/sessions.db` — openable by any
catalog parser — and `expected.json` with the labeled verdicts. `inject`
adds a top-level scorecard (`expected_blocks` per defect). `fleet`
generates unlabeled sessions with realistic duration/model/subagent
distributions for benchmarks and demos.

All output is deterministic given `--seed`.

## What it does not do

- It does not run the verdicts — checking that tools actually reach the
  expected verdict is the catalog's job (e.g. `devin-evals` packs, manual
  `qa-pack`/`redact` runs against the generated DBs).
- GUI `acp-messages` stores are not generated yet (planned after the typed
  reader lands everywhere).
- `fleet` volume beyond a few thousand sessions is untested.

Requires Python ≥ 3.10, stdlib only beyond `devin-internals-spec`.
Read-only w.r.t. real Devin stores: it only writes its own output dir.
