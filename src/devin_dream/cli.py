"""devin-dream CLI: unit | inject | fleet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from devin_dream.defects import ADVERSARIAL, DEFECTS, UNIT_IDS
from devin_dream.generate import (
    fleet_specs,
    write_expected,
    write_sessions_db,
)


def _cmd_unit(args: argparse.Namespace) -> int:
    ids = list(UNIT_IDS) if args.defect == ["all"] else args.defect
    unknown = [d for d in ids if d not in DEFECTS]
    if unknown:
        print(f"error: unknown defect(s): {', '.join(unknown)}",
              file=sys.stderr)
        return 2
    out = Path(args.out)
    for did in ids:
        spec = DEFECTS[did]()
        ddir = out / did.lower()
        write_sessions_db(ddir / "sessions.db", [spec],
                          schema_version=args.schema_version, seed=args.seed)
        ep = write_expected(ddir, spec)
        print(f"{did}: {ddir / 'sessions.db'} (+ {ep.name})")
    return 0


def _cmd_inject(args: argparse.Namespace) -> int:
    """Adversarial sessions (D07/D08) + the expected block/pass scorecard."""
    out = Path(args.out)
    specs = [DEFECTS[d]() for d in ADVERSARIAL for _ in range(args.n)]
    # unique session ids per copy
    seen: dict[str, int] = {}
    final = []
    for s in specs:
        seen[s.session_id] = seen.get(s.session_id, 0) + 1
        suffix = seen[s.session_id]
        import dataclasses
        final.append(dataclasses.replace(
            s, session_id=f"{s.session_id}-{suffix:03d}"))
    write_sessions_db(out / "sessions.db", final, seed=args.seed)
    scorecard = {
        "mode": "inject",
        "sessions": len(final),
        "expected_blocks": {d: args.n for d in ADVERSARIAL},
        "note": "each session must be denied/quarantined by the target "
                "tool; a pass is a hole in the policy",
    }
    (out / "expected.json").write_text(
        json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    for s in final:
        write_expected(out / s.session_id, s)
    print(f"inject: {len(final)} adversarial session(s) -> "
          f"{out / 'sessions.db'}")
    return 0


def _cmd_fleet(args: argparse.Namespace) -> int:
    out = Path(args.out)
    specs = fleet_specs(args.n, seed=args.seed)
    write_sessions_db(out / "sessions.db", specs, seed=args.seed)
    noise = sum(1 for s in specs if any(l.startswith("noise") for l in s.labels))
    print(f"fleet: {len(specs)} sessions ({noise} noise) -> "
          f"{out / 'sessions.db'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="devin-dream",
        description="Synthetic Devin sessions with known verdicts — "
        "regression and adversarial test data for the catalog.")
    sub = p.add_subparsers(dest="command", required=True)

    u = sub.add_parser("unit", help="one sessions.db + expected.json per defect")
    u.add_argument("--out", required=True)
    u.add_argument("--defect", nargs="+", default=["all"],
                   help="defect ids or 'all' (unit covers D01-D06 + D09)")
    u.add_argument("--schema-version", type=int, default=None)
    u.add_argument("--seed", type=int, default=0xDEE4)
    u.set_defaults(func=_cmd_unit)

    i = sub.add_parser("inject",
                       help="adversarial sessions + expected scorecard")
    i.add_argument("--out", required=True)
    i.add_argument("--n", type=int, default=1,
                   help="copies per adversarial defect (D07, D08)")
    i.add_argument("--seed", type=int, default=0xDEE4)
    i.set_defaults(func=_cmd_inject)

    f = sub.add_parser("fleet",
                       help="bulk sessions with realistic noise mix")
    f.add_argument("--out", required=True)
    f.add_argument("--n", type=int, default=1000)
    f.add_argument("--seed", type=int, default=0)
    f.set_defaults(func=_cmd_fleet)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
