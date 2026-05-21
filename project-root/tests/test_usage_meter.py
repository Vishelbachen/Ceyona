"""
Tests for payments/usage_meter.py.

Key scenarios:
  1. Normal record — all core fields written
  2. Extended fields (audio_seconds, tts_characters) — included only when non-zero
  3. PGRST204 fallback — retries with core fields only
  4. Core retry also fails — returns False
  5. Unrelated exception — returns False immediately
"""
from unittest.mock import MagicMock

import pytest
from payments.usage_meter import UsageEntry, UsageMeter

# ─── fixtures ─────────────────────────────────────────────────────────────────

def _base_entry(**kwargs) -> UsageEntry:
    defaults = dict(
        user_id=12345,
        input_tokens=500,
        output_tokens=900,
        embedding_tokens=0,
        rerank_tokens=0,
        tier="general",
        embedding_type="large",
        raw_cost_usd=0.001,
        billed_cost_usd=0.00125,
        model="llama-3.3-70b-versatile",
        intent="QUESTION",
        lang="ru",
        audio_seconds=0.0,
        tts_characters=0,
        tool_calls=0,
    )
    defaults.update(kwargs)
    return UsageEntry(**defaults)


def _make_meter(supabase_mock=None):
    if supabase_mock is None:
        supabase_mock = MagicMock()
    return UsageMeter(supabase=supabase_mock), supabase_mock


# ─── happy path ───────────────────────────────────────────────────────────────

class TestUsageMeterRecord:
    @pytest.mark.asyncio
    async def test_record_returns_true_on_success(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        result = await meter.record(_base_entry())
        assert result is True

    @pytest.mark.asyncio
    async def test_record_calls_supabase_insert(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry())
        db.table.assert_called_with("usage_log")
        db.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_core_fields_always_present(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry())

        inserted_payload = db.table.return_value.insert.call_args[0][0]
        for field in ("user_id", "input_tokens", "output_tokens", "tier",
                      "raw_cost_usd", "billed_cost_usd", "model", "lang"):
            assert field in inserted_payload, f"Core field '{field}' missing from INSERT"


# ─── extended fields (non-zero only) ─────────────────────────────────────────

class TestExtendedFields:
    @pytest.mark.asyncio
    async def test_zero_audio_seconds_not_in_payload(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry(audio_seconds=0.0))

        payload = db.table.return_value.insert.call_args[0][0]
        assert "audio_seconds" not in payload

    @pytest.mark.asyncio
    async def test_nonzero_audio_seconds_in_payload(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry(audio_seconds=12.5))

        payload = db.table.return_value.insert.call_args[0][0]
        assert "audio_seconds" in payload
        assert payload["audio_seconds"] == 12.5

    @pytest.mark.asyncio
    async def test_zero_tts_characters_not_in_payload(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry(tts_characters=0))

        payload = db.table.return_value.insert.call_args[0][0]
        assert "tts_characters" not in payload

    @pytest.mark.asyncio
    async def test_nonzero_tts_characters_in_payload(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry(tts_characters=1500))

        payload = db.table.return_value.insert.call_args[0][0]
        assert "tts_characters" in payload
        assert payload["tts_characters"] == 1500

    @pytest.mark.asyncio
    async def test_zero_tool_calls_not_in_payload(self):
        meter, db = _make_meter()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        await meter.record(_base_entry(tool_calls=0))

        payload = db.table.return_value.insert.call_args[0][0]
        assert "tool_calls" not in payload


# ─── PGRST204 fallback ────────────────────────────────────────────────────────

class TestPGRST204Fallback:
    @pytest.mark.asyncio
    async def test_pgrst204_triggers_core_only_retry(self):
        """PGRST204 with extended fields → retry with core-only payload."""
        meter, db = _make_meter()

        # First call raises PGRST204, second succeeds
        execute_mock = MagicMock()
        execute_mock.side_effect = [
            Exception("PGRST204: column 'audio_seconds' not found"),
            MagicMock(),  # core-only retry succeeds
        ]
        db.table.return_value.insert.return_value.execute = execute_mock

        result = await meter.record(_base_entry(audio_seconds=5.0))
        assert result is True
        assert execute_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_pgrst204_retry_uses_core_fields_only(self):
        """On PGRST204 retry: extended fields must NOT be in the payload."""
        meter, db = _make_meter()

        insert_mock = MagicMock()
        insert_mock.return_value.execute.side_effect = [
            Exception("PGRST204: column 'audio_seconds' missing"),
            MagicMock(),
        ]
        db.table.return_value.insert = insert_mock

        await meter.record(_base_entry(audio_seconds=5.0))

        # Second insert call (retry) should have core fields only
        retry_payload = insert_mock.call_args_list[1][0][0]
        assert "audio_seconds" not in retry_payload
        assert "user_id" in retry_payload

    @pytest.mark.asyncio
    async def test_pgrst204_no_extended_fields_no_retry(self):
        """PGRST204 but no extended fields → do NOT retry (nothing to strip)."""
        meter, db = _make_meter()

        execute_mock = MagicMock()
        execute_mock.side_effect = Exception("PGRST204: some column missing")
        db.table.return_value.insert.return_value.execute = execute_mock

        # No extended fields (all zero) → single attempt → False
        result = await meter.record(_base_entry())  # all zeros
        assert result is False
        assert execute_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_pgrst204_core_retry_fails_returns_false(self):
        """PGRST204 → retry → retry also fails → returns False."""
        meter, db = _make_meter()

        execute_mock = MagicMock()
        execute_mock.side_effect = [
            Exception("PGRST204: column missing"),
            Exception("Connection timeout"),
        ]
        db.table.return_value.insert.return_value.execute = execute_mock

        result = await meter.record(_base_entry(audio_seconds=5.0))
        assert result is False

    @pytest.mark.asyncio
    async def test_unrelated_exception_returns_false(self):
        """Non-PGRST204 exception → return False immediately (no retry)."""
        meter, db = _make_meter()

        execute_mock = MagicMock()
        execute_mock.side_effect = Exception("Connection refused")
        db.table.return_value.insert.return_value.execute = execute_mock

        result = await meter.record(_base_entry())
        assert result is False
        assert execute_mock.call_count == 1


# ─── compute_billed ───────────────────────────────────────────────────────────

class TestComputeBilled:
    def test_compute_billed_applies_margin(self):
        meter, _ = _make_meter()
        raw = 0.001
        billed = meter.compute_billed(raw)
        # Margin should make billed >= raw
        assert billed >= raw

    def test_compute_billed_zero(self):
        meter, _ = _make_meter()
        assert meter.compute_billed(0.0) == 0.0