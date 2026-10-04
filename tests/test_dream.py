"""devin-dream: generated DBs must parse + carry the labeled verdict."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from devin_dream.cli import main
from devin_dream.defects import DEFECTS, UNIT_IDS
from devin_internals.parsers import SessionsStore
from devin_internals.schema import SchemaError


def test_unit_generates_all_and_parses(tmp_path):
    out = tmp_path / "u"
    assert main(["unit", "--out", str(out)]) == 0
    for did in UNIT_IDS:
        if did == "D06":
            continue  # drift canary is intentionally unparseable
        db = out / did.lower() / "sessions.db"
        assert db.is_file()
        exp = json.loads((db.parent / "expected.json").read_text())
        assert exp["defect"] == did and exp["expected"]
        with SessionsStore(db) as st:
            assert len(st.sessions()) == 1
            assert st.sessions()[0].id == exp["session_id"]
            assert st.message_nodes()


def test_d06_fails_schema_detection_loudly(tmp_path):
    out = tmp_path / "u"
    assert main(["unit", "--out", str(out), "--defect", "D06"]) == 0
    with pytest.raises(SchemaError):
        SessionsStore(out / "d06" / "sessions.db")


def test_d04_carries_fake_secret_in_tool_output(tmp_path):
    out = tmp_path / "u"
    main(["unit", "--out", str(out), "--defect", "D04"])
    with SessionsStore(out / "d04" / "sessions.db") as st:
        tcs = st.tool_call_state()
    blob = tcs[0].tool_call_update_json
    assert "AKIAIOSFODNN7EXAMPLE" in blob


def test_d09_splits_secret_across_calls(tmp_path):
    from devin_dream.defects import FAKE_AWS_KEY
    out = tmp_path / "u"
    main(["unit", "--out", str(out), "--defect", "D09"])
    with SessionsStore(out / "d09" / "sessions.db") as st:
        joined = "".join(
            tc.tool_call_update_json or "" for tc in st.tool_call_state())
    # neither payload alone is a full key; together they form one
    assert joined.count("AKIAIOSFOD") == 1
    assert FAKE_AWS_KEY[:10] in joined and FAKE_AWS_KEY[10:] in joined


def test_unknown_defect_is_usage_error(tmp_path):
    assert main(["unit", "--out", str(tmp_path), "--defect", "D99"]) == 2


def test_inject_scorecard(tmp_path):
    out = tmp_path / "i"
    assert main(["inject", "--out", str(out), "--n", "3"]) == 0
    card = json.loads((out / "expected.json").read_text())
    assert card["sessions"] == 6
    assert card["expected_blocks"] == {"D07": 3, "D08": 3}
    with SessionsStore(out / "sessions.db") as st:
        assert len(st.sessions()) == 6


def test_fleet_noise_mix_and_parse(tmp_path):
    out = tmp_path / "f"
    assert main(["fleet", "--out", str(out), "--n", "200"]) == 0
    with SessionsStore(out / "sessions.db") as st:
        sessions = st.sessions()
    assert len(sessions) == 200
    noise = sum(
        1 for s in sessions
        if "noise:" in (json.loads(s.metadata or "{}").get("labels") or [""])[1]
    )
    assert 80 < noise < 160  # ~55% of 200, wide band


def test_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    main(["unit", "--out", str(a), "--defect", "D01"])
    main(["unit", "--out", str(b), "--defect", "D01"])
    assert (a / "d01" / "sessions.db").read_bytes() == (
        b / "d01" / "sessions.db").read_bytes()
