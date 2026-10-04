"""Write labeled synthetic sessions into a real-shape ``sessions.db``.

Reuses the verified DDL from ``devin_internals.fixtures`` (the migration
ledger + table layout), but inserts dream content: realistic messages,
tool calls, and the per-defect ``expected.json`` verdict file.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from pathlib import Path

from devin_internals.fixtures import (
    _BASE_TS_MS,
    _FUTURE_MIGRATION_DATE,
    _MIGRATION_APPLIED_ON,
    SESSIONS_DB_DDL_V17,
    LATEST_KNOWN_SCHEMA,
)

from devin_dream.defects import SessionSpec, _exec_call

DREAM_SEED_TAG = "devin-dream"


def _checksum(seed: int, version: int) -> str:
    return hashlib.sha256(
        f"{DREAM_SEED_TAG}:{seed}:{version}".encode()).hexdigest()


def write_sessions_db(
    path: str | Path,
    specs: list[SessionSpec],
    *,
    schema_version: int | None = None,
    seed: int = 0xDEE4,
) -> Path:
    """Create a ``sessions.db`` holding the given session specs.

    ``schema_version`` defaults to the latest known (17); a spec with
    ``schema_version_override`` forces the whole DB to that version (D06
    uses it — one drifted DB per defect dir).
    """
    path = Path(path)
    if specs and specs[0].schema_version_override:
        schema_version = specs[0].schema_version_override
    version = schema_version or LATEST_KNOWN_SCHEMA

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    con = sqlite3.connect(path)
    with con:
        con.executescript(SESSIONS_DB_DDL_V17)
        for v in range(1, version + 1):
            con.execute(
                "INSERT INTO refinery_schema_history(version, name,"
                " applied_on, checksum) VALUES (?, ?, ?, ?)",
                (v, f"dream_migration_{v:02d}",
                 _MIGRATION_APPLIED_ON.get(v, _FUTURE_MIGRATION_DATE),
                 _checksum(seed, v)),
            )
        con.execute(
            "INSERT INTO app_state(key, value) VALUES (?, ?)",
            ("schema_compat_version", str(version)))
        for i, spec in enumerate(specs):
            _insert_spec(con, spec, i)
    con.close()
    return path


def _insert_spec(con: sqlite3.Connection, spec: SessionSpec, i: int) -> None:
    created = _BASE_TS_MS + i * 3_600_000
    con.execute(
        "INSERT INTO sessions(id, working_directory, backend_type, model,"
        " agent_mode, created_at, last_activity_at, title, main_chain_id,"
        " shell_last_seen_index, cogs_json, workspace_dirs, hidden, metadata)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            spec.session_id,
            spec.working_directory,
            "dream-backend",
            spec.model,
            spec.agent_mode,
            created,
            created + 120_000,
            spec.title,
            1,
            0,
            json.dumps({"synthetic": True}),
            json.dumps([spec.working_directory]),
            0,
            json.dumps({"synthetic": True, "labels": list(spec.labels),
                        "defect": spec.defect_id}),
        ),
    )
    for node_id, (role, blob) in enumerate(spec.messages, start=1):
        con.execute(
            "INSERT INTO message_nodes(session_id, node_id, parent_node_id,"
            " chat_message, created_at, metadata)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (spec.session_id, node_id, None if node_id == 1 else node_id - 1,
             blob, created + node_id * 10_000,
             json.dumps({"synthetic": True})),
        )
    for tc in spec.tool_calls:
        con.execute(
            "INSERT INTO tool_call_state(session_id, tool_call_id,"
            " tool_call_json, tool_call_update_json) VALUES (?, ?, ?, ?)",
            (spec.session_id, tc.tool_call_id, json.dumps(tc.call),
             json.dumps(tc.update) if tc.update is not None else None),
        )


def write_expected(out_dir: str | Path, spec: SessionSpec) -> Path:
    """``expected.json`` next to the generated DB — the known verdicts."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    p = Path(out_dir) / "expected.json"
    p.write_text(
        json.dumps({
            "defect": spec.defect_id,
            "session_id": spec.session_id,
            "title": spec.title,
            "labels": list(spec.labels),
            "expected": spec.expected,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# fleet mode — realistic distributions, no labeled defect
# ---------------------------------------------------------------------------

_FLEET_MODELS = ("swe-1.6", "swe-1.5", "gpt-5-codex", "claude-sonnet")
_FLEET_MODES = ("interactive", "plan", "exec")
_FLEET_NOISE_KINDS = ("judge", "probe", "heartbeat")
_NOISE_FRACTION = 0.55  # matches the janitor README's observed share


def fleet_specs(n: int, *, seed: int = 0) -> list[SessionSpec]:
    """``n`` generic sessions with realistic duration/model/noise mix.

    ~55% are labeled noise sessions (judge probes, heartbeats) so
    benchmarks for janitor/search/graph see a realistic distribution.
    """
    rng = random.Random(seed)
    specs: list[SessionSpec] = []
    for i in range(n):
        noise = rng.random() < _NOISE_FRACTION
        kind = rng.choice(_FLEET_NOISE_KINDS) if noise else "task"
        n_msgs = rng.randint(2, 6) if noise else rng.randint(4, 24)
        sid = f"dream-fleet-{i:05d}"
        labels = ("synthetic", f"noise:{kind}" if noise else "task")
        msgs = tuple(
            _msg("user" if j % 2 == 0 else "assistant",
                 f"fleet {kind} message {j}", j)
            for j in range(n_msgs)
        )
        specs.append(SessionSpec(
            defect_id="FLEET",
            session_id=sid,
            title=f"Fleet {kind} session {i}",
            working_directory=f"/dream/fleet/proj-{rng.randint(0, 9)}",
            model=rng.choice(_FLEET_MODELS),
            agent_mode=rng.choice(_FLEET_MODES),
            messages=msgs,
            tool_calls=tuple(
                _exec_call(f"call_{sid}_{t}", f"cmd-{t}", f"out {t}")
                for t in range(rng.randint(0, 4))
            ),
            expected={},
            labels=labels,
        ))
    return specs


def _msg(role: str, content: str, n: int) -> tuple[str, str]:
    return (role, json.dumps({
        "message_id": f"dream-fleet-{role}-{n:05d}",
        "role": role,
        "content": content,
        "metadata": {},
    }))
