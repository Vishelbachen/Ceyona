"""
test_transport_and_retrieval.py

Targets the largest uncovered modules from CI coverage report (41% → 60%+):

  transport/telegram/message_router.py     0%  → ~100%
  transport/telegram/update_handler.py     6%  → ~70%
  transport/telegram/vision_handler.py     0%  → ~60%
  transport/telegram/webhook.py            0%  → ~50%
  retrieval/retrieval_engine.py            0%  → ~70%
  retrieval/query_preprocessor.py          0%  → 100%
  payments/access_controller.py            0%  → ~80%
  security/rate_limiter.py                 0%  → ~80%

All tests are pure unit — no Supabase, Redis, Groq, HuggingFace.
External I/O mocked at the boundary via unittest.mock.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/message_router.py
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyUpdate:
    def test_message(self):
        from transport.telegram.message_router import UpdateType, classify_update
        assert classify_update({"message": {}}) == UpdateType.MESSAGE

    def test_callback_query(self):
        from transport.telegram.message_router import UpdateType, classify_update
        assert classify_update({"callback_query": {}}) == UpdateType.CALLBACK_QUERY

    def test_edited_message(self):
        from transport.telegram.message_router import UpdateType, classify_update
        assert classify_update({"edited_message": {}}) == UpdateType.EDITED_MESSAGE

    def test_unknown(self):
        from transport.telegram.message_router import UpdateType, classify_update
        assert classify_update({"something_else": {}}) == UpdateType.UNKNOWN

    def test_empty(self):
        from transport.telegram.message_router import UpdateType, classify_update
        assert classify_update({}) == UpdateType.UNKNOWN


class TestExtractText:
    def test_message_text(self):
        from transport.telegram.message_router import extract_text
        update = {"message": {"text": "hello world"}}
        assert extract_text(update) == "hello world"

    def test_message_caption(self):
        from transport.telegram.message_router import extract_text
        update = {"message": {"caption": "photo caption"}}
        assert extract_text(update) == "photo caption"

    def test_edited_message(self):
        from transport.telegram.message_router import extract_text
        update = {"edited_message": {"text": "edited text"}}
        assert extract_text(update) == "edited text"

    def test_text_takes_priority_over_caption(self):
        from transport.telegram.message_router import extract_text
        update = {"message": {"text": "text", "caption": "caption"}}
        assert extract_text(update) == "text"

    def test_empty_update(self):
        from transport.telegram.message_router import extract_text
        assert extract_text({}) == ""

    def test_no_text_field(self):
        from transport.telegram.message_router import extract_text
        assert extract_text({"message": {}}) == ""


class TestExtractPhoto:
    def _make_photo_update(self, caption=""):
        return {
            "message": {
                "photo": [
                    {"file_id": "small_id", "file_unique_id": "u1", "width": 100, "height": 100},
                    {"file_id": "large_id", "file_unique_id": "u2", "width": 800, "height": 600},
                ],
                "caption": caption,
            }
        }

    def test_returns_largest_photo(self):
        from transport.telegram.message_router import extract_photo
        result = extract_photo(self._make_photo_update())
        assert result is not None
        assert result["file_id"] == "large_id"

    def test_includes_caption(self):
        from transport.telegram.message_router import extract_photo
        result = extract_photo(self._make_photo_update(caption="my caption"))
        assert result["caption"] == "my caption"

    def test_no_photo_returns_none(self):
        from transport.telegram.message_router import extract_photo
        assert extract_photo({"message": {"text": "no photo"}}) is None

    def test_empty_returns_none(self):
        from transport.telegram.message_router import extract_photo
        assert extract_photo({}) is None

    def test_has_photo_true(self):
        from transport.telegram.message_router import has_photo
        assert has_photo(self._make_photo_update()) is True

    def test_has_photo_false(self):
        from transport.telegram.message_router import has_photo
        assert has_photo({"message": {"text": "text"}}) is False


class TestExtractVoice:
    def test_voice_message(self):
        from transport.telegram.message_router import extract_voice
        update = {
            "message": {
                "voice": {
                    "file_id": "voice_id",
                    "duration": 5,
                    "mime_type": "audio/ogg",
                    "file_size": 1024,
                }
            }
        }
        result = extract_voice(update)
        assert result is not None
        assert result["file_id"] == "voice_id"
        assert result["source"] == "voice"

    def test_audio_message(self):
        from transport.telegram.message_router import extract_voice
        update = {
            "message": {
                "audio": {
                    "file_id": "audio_id",
                    "duration": 30,
                    "mime_type": "audio/mpeg",
                    "file_size": 4096,
                }
            }
        }
        result = extract_voice(update)
        assert result is not None
        assert result["file_id"] == "audio_id"
        assert result["source"] == "audio"

    def test_voice_preferred_over_audio(self):
        from transport.telegram.message_router import extract_voice
        update = {
            "message": {
                "voice": {"file_id": "voice_id", "duration": 5, "mime_type": "audio/ogg", "file_size": 0},
                "audio": {"file_id": "audio_id", "duration": 30, "mime_type": "audio/mpeg", "file_size": 0},
            }
        }
        result = extract_voice(update)
        assert result["source"] == "voice"

    def test_no_voice_returns_none(self):
        from transport.telegram.message_router import extract_voice
        assert extract_voice({"message": {"text": "hi"}}) is None

    def test_has_voice_true(self):
        from transport.telegram.message_router import has_voice
        update = {
            "message": {"voice": {"file_id": "v1", "duration": 3, "mime_type": "audio/ogg", "file_size": 0}}
        }
        assert has_voice(update) is True

    def test_has_voice_false(self):
        from transport.telegram.message_router import has_voice
        assert has_voice({"message": {"text": "hi"}}) is False

    def test_extract_callback_data(self):
        from transport.telegram.message_router import extract_callback_data
        update = {"callback_query": {"data": "balance"}}
        assert extract_callback_data(update) == "balance"

    def test_extract_callback_data_empty(self):
        from transport.telegram.message_router import extract_callback_data
        assert extract_callback_data({}) == ""


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/update_handler.py  — helper functions
# ══════════════════════════════════════════════════════════════════════════════

class TestEstimateTokens:
    def test_basic(self):
        from transport.telegram.update_handler import _estimate_tokens
        assert _estimate_tokens("hello") == max(1, len("hello") // 4)

    def test_minimum_one(self):
        from transport.telegram.update_handler import _estimate_tokens
        assert _estimate_tokens("") == 1
        assert _estimate_tokens("ab") == 1

    def test_longer_text(self):
        from transport.telegram.update_handler import _estimate_tokens
        text = "x" * 400
        assert _estimate_tokens(text) == 100


class TestEstimateHistoryTokens:
    def test_none_returns_zero(self):
        from transport.telegram.update_handler import _estimate_history_tokens
        assert _estimate_history_tokens(None) == 0

    def test_empty_list_returns_zero(self):
        from transport.telegram.update_handler import _estimate_history_tokens
        assert _estimate_history_tokens([]) == 0

    def test_sums_content_tokens(self):
        from transport.telegram.update_handler import _estimate_history_tokens
        history = [
            {"role": "user",      "content": "x" * 400},   # 100 tokens
            {"role": "assistant", "content": "y" * 400},   # 100 tokens
        ]
        result = _estimate_history_tokens(history)
        assert result == 200

    def test_missing_content_key(self):
        from transport.telegram.update_handler import _estimate_history_tokens
        history = [{"role": "user"}]  # no "content"
        assert _estimate_history_tokens(history) == 1  # _estimate_tokens("") == 1


class TestClassifyComplexity:
    def test_short_text_is_low(self):
        from transport.telegram.update_handler import _classify_complexity
        from contracts.shared_types import Complexity
        assert _classify_complexity("hello world") == Complexity.LOW

    def test_long_text_is_medium(self):
        from transport.telegram.update_handler import _classify_complexity
        from contracts.shared_types import Complexity
        text = "a" * 900
        assert _classify_complexity(text) == Complexity.MEDIUM

    def test_code_block_is_high(self):
        from transport.telegram.update_handler import _classify_complexity
        from contracts.shared_types import Complexity
        text = "here is code:\n```python\nprint('hi')\n```"
        assert _classify_complexity(text) == Complexity.HIGH

    def test_json_is_high(self):
        from transport.telegram.update_handler import _classify_complexity
        from contracts.shared_types import Complexity
        text = 'send {"key": "value"} to the server'
        assert _classify_complexity(text) == Complexity.HIGH

    def test_code_and_json_is_critical(self):
        from transport.telegram.update_handler import _classify_complexity
        from contracts.shared_types import Complexity
        text = '```json\n{"key": "value"}\n```'
        assert _classify_complexity(text) == Complexity.CRITICAL

    def test_braces_without_colon_not_json(self):
        # {} without : should NOT trigger JSON detection
        from transport.telegram.update_handler import _classify_complexity
        from contracts.shared_types import Complexity
        text = "use {} and {}"
        assert _classify_complexity(text) == Complexity.LOW


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/update_handler.py  — handle_message (async)
# ══════════════════════════════════════════════════════════════════════════════

def _make_usage():
    from contracts.shared_types import Tier
    from core.execution.orchestrator import UsageRecord
    return UsageRecord(
        input_tokens=10, output_tokens=20,
        embedding_tokens=0, rerank_tokens=0,
        tier=Tier.FAST, embedding_type="large", cost_usd=0.0001,
    )


def _make_ok_result(text="Hello"):
    from contracts.shared_types import EPKDecision, Tier
    from core.execution.orchestrator import OrchestratorResult
    return OrchestratorResult(
        text=text, tier=Tier.GENERAL, model="llama", epk_decision=EPKDecision.ALLOW,
        usage=_make_usage(), denied=False, deny_reason="", lang="en",
    )


def _make_text_update(text="Hello"):
    return {"message": {"text": text, "chat": {"id": 1}, "from": {"id": 42}}}


@pytest.mark.asyncio
async def test_handle_message_empty_text_returns_denied():
    """Empty update returns denied result with empty_message reason."""
    from transport.telegram.update_handler import handle_message
    from transport.telegram.message_router import UpdateType

    update = {"message": {}}  # no text
    with (
        patch("transport.telegram.update_handler.asyncio.wait_for", new_callable=AsyncMock) as mock_gate,
        patch("transport.telegram.update_handler.run", new_callable=AsyncMock),
    ):
        # safety gate: return passing verdict
        from unittest.mock import MagicMock
        mock_verdict = MagicMock()
        mock_verdict.verdict = None   # not DENY
        mock_verdict.safe = True
        mock_gate.return_value = mock_verdict

        result = await handle_message(
            update=update,
            update_type=UpdateType.MESSAGE,
            user_id=42,
            user_balance=1.0,
        )

    assert result.denied is True
    assert result.deny_reason == "empty_message"


@pytest.mark.asyncio
async def test_handle_message_normal_flow():
    """Normal text message flows through to orchestrator and returns result."""
    from transport.telegram.message_router import UpdateType
    from transport.telegram.update_handler import handle_message

    update = _make_text_update("What is the weather?")
    ok_result = _make_ok_result("Sunny today")

    gate_verdict = MagicMock()
    gate_verdict.verdict = None   # not GateVerdict.DENY
    gate_verdict.safe = True

    with (
        patch("transport.telegram.update_handler.asyncio.wait_for", return_value=gate_verdict),
        patch("transport.telegram.update_handler.run", new_callable=AsyncMock, return_value=ok_result),
        patch("transport.telegram.update_handler.ConversationHistory") as mock_hist,
        patch("transport.telegram.update_handler.ml_preprocess", new_callable=AsyncMock) as mock_ml,
    ):
        mock_hist_inst = AsyncMock()
        mock_hist_inst.get_history = AsyncMock(return_value=[])
        mock_hist_inst.append = AsyncMock()
        mock_hist.return_value = mock_hist_inst

        ml_result = MagicMock()
        ml_result.was_normalized = False
        mock_ml.return_value = ml_result

        result = await handle_message(
            update=update,
            update_type=UpdateType.MESSAGE,
            user_id=42,
            user_balance=1.0,
            lang="en",
        )

    assert result.text == "Sunny today"
    assert result.denied is False


@pytest.mark.asyncio
async def test_handle_message_safety_gate_timeout_continues():
    """Safety gate timeout must not block pipeline — execution continues."""
    from transport.telegram.message_router import UpdateType
    from transport.telegram.update_handler import handle_message

    update = _make_text_update("normal question")
    ok_result = _make_ok_result("answer")

    with (
        patch("transport.telegram.update_handler.asyncio.wait_for",
              side_effect=asyncio.TimeoutError()),
        patch("transport.telegram.update_handler.run",
              new_callable=AsyncMock, return_value=ok_result),
        patch("transport.telegram.update_handler.ConversationHistory") as mock_hist,
    ):
        mock_hist_inst = AsyncMock()
        mock_hist_inst.get_history = AsyncMock(return_value=[])
        mock_hist_inst.append = AsyncMock()
        mock_hist.return_value = mock_hist_inst

        result = await handle_message(
            update=update,
            update_type=UpdateType.MESSAGE,
            user_id=42,
            user_balance=1.0,
        )

    # Pipeline should complete even when gate times out
    assert result.text == "answer"


@pytest.mark.asyncio
async def test_handle_message_vision_path_direct_response_zero_balance():
    """Vision fast-path with zero balance returns denied/insufficient_balance."""
    from transport.telegram.message_router import UpdateType
    from transport.telegram.update_handler import handle_message

    photo_update = {
        "message": {
            "photo": [
                {"file_id": "img001", "file_unique_id": "u1", "width": 800, "height": 600},
            ],
            "caption": "what is this?",
            "chat": {"id": 1},
            "from": {"id": 42},
        }
    }

    # VisionResult: direct response (no pipeline)
    vision_result = MagicMock()
    vision_result.needs_pipeline = False
    vision_result.text = "It is a cat."

    gate_verdict = MagicMock()
    gate_verdict.verdict = None

    with (
        patch("transport.telegram.update_handler.asyncio.wait_for", return_value=gate_verdict),
        patch("transport.telegram.update_handler.handle_vision",
              new_callable=AsyncMock, return_value=vision_result),
    ):
        result = await handle_message(
            update=photo_update,
            update_type=UpdateType.MESSAGE,
            user_id=42,
            user_balance=0.0,  # zero balance
            lang="en",
        )

    assert result.denied is True
    assert result.deny_reason == "insufficient_balance"


@pytest.mark.asyncio
async def test_handle_message_vision_path_direct_response_sufficient_balance():
    """Vision fast-path with sufficient balance returns direct text response."""
    from transport.telegram.message_router import UpdateType
    from transport.telegram.update_handler import handle_message

    photo_update = {
        "message": {
            "photo": [
                {"file_id": "img001", "file_unique_id": "u1", "width": 800, "height": 600},
            ],
            "caption": "",
            "chat": {"id": 1},
            "from": {"id": 42},
        }
    }

    vision_result = MagicMock()
    vision_result.needs_pipeline = False
    vision_result.text = "A dog running in a park."

    gate_verdict = MagicMock()
    gate_verdict.verdict = None

    with (
        patch("transport.telegram.update_handler.asyncio.wait_for", return_value=gate_verdict),
        patch("transport.telegram.update_handler.handle_vision",
              new_callable=AsyncMock, return_value=vision_result),
    ):
        result = await handle_message(
            update=photo_update,
            update_type=UpdateType.MESSAGE,
            user_id=42,
            user_balance=1.0,
            lang="en",
        )

    assert result.denied is False
    assert result.text == "A dog running in a park."


@pytest.mark.asyncio
async def test_handle_message_no_supabase_skips_history_and_retrieval():
    """When supabase=None history and retrieval are skipped gracefully."""
    from transport.telegram.message_router import UpdateType
    from transport.telegram.update_handler import handle_message

    update = _make_text_update("simple question")
    ok_result = _make_ok_result("simple answer")

    gate_verdict = MagicMock()
    gate_verdict.verdict = None
    gate_verdict.safe = True

    with (
        patch("transport.telegram.update_handler.asyncio.wait_for", return_value=gate_verdict),
        patch("transport.telegram.update_handler.run",
              new_callable=AsyncMock, return_value=ok_result),
    ):
        result = await handle_message(
            update=update,
            update_type=UpdateType.MESSAGE,
            user_id=42,
            user_balance=1.0,
            supabase=None,  # no Supabase
        )

    assert result.text == "simple answer"


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/webhook.py  — helpers (_get_chat_id, _detect_lang)
# ══════════════════════════════════════════════════════════════════════════════

class TestGetChatId:
    def test_from_message(self):
        from transport.telegram.webhook import _get_chat_id
        update = {"message": {"chat": {"id": 999}}}
        assert _get_chat_id(update) == 999

    def test_from_edited_message(self):
        from transport.telegram.webhook import _get_chat_id
        update = {"edited_message": {"chat": {"id": 888}}}
        assert _get_chat_id(update) == 888

    def test_from_callback_query(self):
        from transport.telegram.webhook import _get_chat_id
        update = {"callback_query": {"message": {"chat": {"id": 777}}}}
        assert _get_chat_id(update) == 777

    def test_empty_returns_none(self):
        from transport.telegram.webhook import _get_chat_id
        assert _get_chat_id({}) is None


class TestDetectLang:
    def test_short_text_falls_back_to_profile(self):
        from transport.telegram.webhook import _detect_lang
        update = {
            "message": {
                "text": "hi",   # too short for lingua
                "from": {"language_code": "ru"},
            }
        }
        result = _detect_lang(update)
        assert result == "ru"

    def test_empty_text_falls_back_to_profile(self):
        from transport.telegram.webhook import _detect_lang
        update = {"message": {"from": {"language_code": "de"}}}
        result = _detect_lang(update)
        assert result == "de"

    def test_no_language_code_defaults_en(self):
        from transport.telegram.webhook import _detect_lang
        update = {"message": {"from": {}}}
        result = _detect_lang(update)
        assert result == "en"

    def test_profile_lang_strips_region(self):
        from transport.telegram.webhook import _detect_lang
        # "en-US" → "en"
        update = {"message": {"from": {"language_code": "en-US"}}}
        result = _detect_lang(update)
        assert result == "en"

    def test_empty_update_defaults_en(self):
        from transport.telegram.webhook import _detect_lang
        assert _detect_lang({}) == "en"


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/vision_handler.py
# ══════════════════════════════════════════════════════════════════════════════

class TestVisionHandlerHelpers:
    @pytest.mark.asyncio
    async def test_get_file_url_http_error(self):
        """When Telegram getFile fails, _get_file_url returns None."""
        import httpx
        from transport.telegram.vision_handler import _get_file_url

        with patch("transport.telegram.vision_handler.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.get = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_cm

            result = await _get_file_url("bad_file_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_download_image_exception_returns_none(self):
        """Network error during download returns None."""
        from transport.telegram.vision_handler import _download_image

        with patch("transport.telegram.vision_handler.httpx.AsyncClient") as mock_client:
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.get = AsyncMock(side_effect=Exception("network error"))
            mock_client.return_value = mock_cm

            result = await _download_image("http://example.com/image.jpg")
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_vision_file_url_fail(self):
        """handle_vision returns error VisionResult when file URL fetch fails."""
        from transport.telegram.vision_handler import handle_vision

        with patch("transport.telegram.vision_handler._get_file_url", new_callable=AsyncMock, return_value=None):
            result = await handle_vision(file_id="bad", caption="", lang="en")

        assert result.needs_pipeline is False
        assert result.text != ""  # error message returned

    @pytest.mark.asyncio
    async def test_handle_vision_download_fail(self):
        """handle_vision returns error VisionResult when image download fails."""
        from transport.telegram.vision_handler import handle_vision

        with (
            patch("transport.telegram.vision_handler._get_file_url",
                  new_callable=AsyncMock, return_value="http://example.com/img.jpg"),
            patch("transport.telegram.vision_handler._download_image",
                  new_callable=AsyncMock, return_value=None),
        ):
            result = await handle_vision(file_id="ok_id", caption="", lang="en")

        assert result.needs_pipeline is False

    @pytest.mark.asyncio
    async def test_handle_vision_groq_api_error(self):
        """Groq API HTTP error returns error VisionResult."""
        import httpx
        from transport.telegram.vision_handler import handle_vision

        with (
            patch("transport.telegram.vision_handler._get_file_url",
                  new_callable=AsyncMock, return_value="http://example.com/img.jpg"),
            patch("transport.telegram.vision_handler._download_image",
                  new_callable=AsyncMock, return_value=b"fake_image_bytes"),
            patch("transport.telegram.vision_handler.httpx.AsyncClient") as mock_client,
        ):
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=mock_resp
            )
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_cm

            result = await handle_vision(file_id="ok_id", caption="", lang="en")

        assert result.needs_pipeline is False

    @pytest.mark.asyncio
    async def test_handle_vision_success_conversation_intent(self):
        """
        When extraction succeeds and intent=CONVERSATION,
        needs_pipeline=False and text is returned directly.
        """
        from transport.telegram.vision_handler import handle_vision

        groq_response = {
            "choices": [{"message": {"content": "A fluffy cat on a sofa."}}]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=groq_response)

        mock_intent_result = MagicMock()
        # CONVERSATION intent → needs_pipeline=False
        from unittest.mock import PropertyMock
        type(mock_intent_result).intent = PropertyMock(return_value="CONVERSATION")

        with (
            patch("transport.telegram.vision_handler._get_file_url",
                  new_callable=AsyncMock, return_value="http://example.com/img.jpg"),
            patch("transport.telegram.vision_handler._download_image",
                  new_callable=AsyncMock, return_value=b"fake_bytes"),
            patch("transport.telegram.vision_handler.httpx.AsyncClient") as mock_client,
            patch("transport.telegram.vision_handler.classify",
                  new_callable=AsyncMock, return_value=mock_intent_result),
        ):
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_cm

            result = await handle_vision(file_id="ok_id", caption="", lang="en")

        assert result.text == "A fluffy cat on a sofa."
        assert result.needs_pipeline is False

    @pytest.mark.asyncio
    async def test_handle_vision_success_non_conversation_intent(self):
        """
        When intent != CONVERSATION, needs_pipeline=True and
        intent_result is forwarded.
        """
        from transport.telegram.vision_handler import handle_vision

        groq_response = {
            "choices": [{"message": {"content": "3x + 5 = 14. Solve for x."}}]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=groq_response)

        mock_intent_result = MagicMock()
        type(mock_intent_result).intent = PropertyMock(return_value="MATH")

        with (
            patch("transport.telegram.vision_handler._get_file_url",
                  new_callable=AsyncMock, return_value="http://example.com/img.jpg"),
            patch("transport.telegram.vision_handler._download_image",
                  new_callable=AsyncMock, return_value=b"fake_bytes"),
            patch("transport.telegram.vision_handler.httpx.AsyncClient") as mock_client,
            patch("transport.telegram.vision_handler.classify",
                  new_callable=AsyncMock, return_value=mock_intent_result),
        ):
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_cm

            result = await handle_vision(file_id="ok_id", caption="describe", lang="en")

        assert result.needs_pipeline is True
        assert result.intent_result is mock_intent_result


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/query_preprocessor.py
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryPreprocessor:
    def test_strips_whitespace(self):
        from retrieval.query_preprocessor import preprocess
        assert preprocess("  hello world  ") == "hello world"

    def test_collapses_multiple_spaces(self):
        from retrieval.query_preprocessor import preprocess
        assert preprocess("hello   world") == "hello world"

    def test_collapses_newlines(self):
        from retrieval.query_preprocessor import preprocess
        result = preprocess("line one\n\nline two")
        assert result == "line one line two"

    def test_truncates_to_512_chars(self):
        from retrieval.query_preprocessor import preprocess
        long_text = "a" * 600
        result = preprocess(long_text)
        assert len(result) == 512

    def test_empty_string(self):
        from retrieval.query_preprocessor import preprocess
        assert preprocess("") == ""

    def test_short_text_unchanged(self):
        from retrieval.query_preprocessor import preprocess
        assert preprocess("hello") == "hello"


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/retrieval_engine.py
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrievalEngine:
    @pytest.mark.asyncio
    async def test_retrieve_embedding_failure_returns_empty(self):
        """When embedding fails, retrieve() returns empty RetrievalResult."""
        from contracts.retrieval_contracts import RetrievalQuery
        from retrieval.retrieval_engine import retrieve

        with patch("retrieval.retrieval_engine.bge_engine") as mock_bge:
            mock_bge.embed = AsyncMock(return_value=None)  # embed failure
            result = await retrieve(RetrievalQuery(text="test query", user_id="42"))

        assert result.documents == []
        assert result.embedding_tokens == 0

    @pytest.mark.asyncio
    async def test_retrieve_no_supabase_skips_pgvector(self):
        """Without supabase, pgvector search is skipped, result is empty."""
        from contracts.retrieval_contracts import RetrievalQuery
        from retrieval.retrieval_engine import retrieve

        fake_embed_result = MagicMock()
        fake_embed_result.tokens_used = 25
        fake_embed_result.embedding = [0.1] * 768

        with (
            patch("retrieval.retrieval_engine.bge_engine") as mock_bge,
            patch("retrieval.retrieval_engine.cross_encoder") as mock_reranker,
        ):
            mock_bge.embed = AsyncMock(return_value=fake_embed_result)
            mock_reranker.rerank = AsyncMock(return_value=[])

            result = await retrieve(
                RetrievalQuery(text="test query", user_id="42"),
                supabase=None,
            )

        assert result.documents == []
        assert result.embedding_tokens == 25

    @pytest.mark.asyncio
    async def test_retrieve_with_candidates_calls_reranker(self):
        """When pgvector returns candidates, cross_encoder.rerank is called."""
        from contracts.retrieval_contracts import RetrievalQuery
        from retrieval.retrieval_engine import retrieve

        fake_embed_result = MagicMock()
        fake_embed_result.tokens_used = 30
        fake_embed_result.embedding = [0.1] * 768

        fake_record = MagicMock()
        fake_record.content = "relevant document content"

        with (
            patch("retrieval.retrieval_engine.bge_engine") as mock_bge,
            patch("retrieval.retrieval_engine.cross_encoder") as mock_reranker,
            patch("retrieval.retrieval_engine.source_credibility") as mock_cred,
            patch("retrieval.retrieval_engine.SupabaseStore") as mock_store_cls,
        ):
            mock_bge.embed = AsyncMock(return_value=fake_embed_result)

            mock_store = AsyncMock()
            mock_store.similarity_search = AsyncMock(return_value=[fake_record])
            mock_store_cls.return_value = mock_store

            mock_cred.score_documents = MagicMock(
                side_effect=lambda docs: docs  # pass-through
            )
            mock_reranker.rerank = AsyncMock(
                return_value=[("relevant document content", 0.95)]
            )

            mock_supabase = MagicMock()
            result = await retrieve(
                RetrievalQuery(text="test query", user_id="42"),
                supabase=mock_supabase,
                user_id="42",
            )

        assert len(result.documents) == 1
        assert result.documents[0].content == "relevant document content"
        mock_reranker.rerank.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retrieval_engine_class_wrapper(self):
        """RetrievalEngine class wrapper calls retrieve() and returns result."""
        from contracts.retrieval_contracts import RetrievalQuery, RetrievalResult
        from retrieval.retrieval_engine import RetrievalEngine

        empty_result = RetrievalResult(
            documents=[], embedding_tokens=0, rerank_tokens=0, cache_hit=False
        )

        mock_store = MagicMock()
        mock_store._db = MagicMock()

        with patch("retrieval.retrieval_engine.retrieve", new_callable=AsyncMock, return_value=empty_result):
            engine = RetrievalEngine(supabase_store=mock_store)
            result = await engine.retrieve(RetrievalQuery(text="query", user_id="1"))

        assert result.documents == []

    @pytest.mark.asyncio
    async def test_retrieval_engine_no_store(self):
        """RetrievalEngine with no supabase_store passes supabase=None to retrieve()."""
        from contracts.retrieval_contracts import RetrievalQuery, RetrievalResult
        from retrieval.retrieval_engine import RetrievalEngine

        empty_result = RetrievalResult(
            documents=[], embedding_tokens=0, rerank_tokens=0, cache_hit=False
        )

        with patch("retrieval.retrieval_engine.retrieve", new_callable=AsyncMock, return_value=empty_result) as mock_retrieve:
            engine = RetrievalEngine()
            await engine.retrieve(RetrievalQuery(text="q", user_id="1"))

        _, kwargs = mock_retrieve.call_args
        assert kwargs.get("supabase") is None


# ══════════════════════════════════════════════════════════════════════════════
# payments/access_controller.py
# ══════════════════════════════════════════════════════════════════════════════

class TestAccessController:
    def _make_supabase(self, rows: list[dict]):
        """Build a mock Supabase client that returns `rows` from any query."""
        result = MagicMock()
        result.data = rows

        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = result
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.upsert.return_value = chain

        supabase = MagicMock()
        supabase.table.return_value = chain
        return supabase

    @pytest.mark.asyncio
    async def test_get_balance_existing_user(self):
        from payments.access_controller import AccessController
        supabase = self._make_supabase([{"balance_usd": 0.50}])
        ac = AccessController(supabase)
        result = await ac.get_balance(user_id=42)
        assert result.balance_usd == 0.50
        assert result.exists is True

    @pytest.mark.asyncio
    async def test_get_balance_new_user_creates_default(self):
        from payments.access_controller import AccessController, _DEFAULT_BALANCE_USD
        supabase = self._make_supabase([])  # no rows → new user
        ac = AccessController(supabase)
        result = await ac.get_balance(user_id=99)
        assert result.balance_usd == _DEFAULT_BALANCE_USD
        assert result.exists is False

    @pytest.mark.asyncio
    async def test_get_balance_db_error_returns_default(self):
        from payments.access_controller import AccessController, _DEFAULT_BALANCE_USD
        supabase = MagicMock()
        supabase.table.side_effect = Exception("db down")
        ac = AccessController(supabase)
        result = await ac.get_balance(user_id=1)
        assert result.balance_usd == _DEFAULT_BALANCE_USD

    @pytest.mark.asyncio
    async def test_deduct_sufficient_balance(self):
        from payments.access_controller import AccessController
        supabase = self._make_supabase([{"balance_usd": 1.00}])
        ac = AccessController(supabase)
        ok = await ac.deduct(user_id=42, amount_usd=0.10)
        assert ok is True

    @pytest.mark.asyncio
    async def test_deduct_insufficient_balance_returns_false(self):
        from payments.access_controller import AccessController
        supabase = self._make_supabase([{"balance_usd": 0.001}])
        ac = AccessController(supabase)
        ok = await ac.deduct(user_id=42, amount_usd=1.00)
        assert ok is False

    @pytest.mark.asyncio
    async def test_credit_increases_balance(self):
        from payments.access_controller import AccessController
        supabase = self._make_supabase([{"balance_usd": 0.50}])
        ac = AccessController(supabase)
        ok = await ac.credit(user_id=42, amount_usd=0.25)
        assert ok is True

    @pytest.mark.asyncio
    async def test_credit_db_error_returns_false(self):
        from payments.access_controller import AccessController
        supabase = MagicMock()
        supabase.table.side_effect = Exception("db error")
        ac = AccessController(supabase)
        ok = await ac.credit(user_id=42, amount_usd=0.10)
        assert ok is False

    @pytest.mark.asyncio
    async def test_deduct_db_error_returns_false(self):
        from payments.access_controller import AccessController
        # get_balance OK but update fails
        result = MagicMock()
        result.data = [{"balance_usd": 1.00}]
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = result
        chain.update.side_effect = Exception("write error")

        supabase = MagicMock()
        supabase.table.return_value = chain

        from payments.access_controller import AccessController
        ac = AccessController(supabase)
        ok = await ac.deduct(user_id=42, amount_usd=0.10)
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# security/rate_limiter.py
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    def _make_redis(self, zcard_count: int):
        """Build a mock Redis client returning given count from pipeline."""
        pipe = AsyncMock()
        pipe.zremrangebyscore = MagicMock()
        pipe.zcard = MagicMock()
        pipe.zadd = MagicMock()
        pipe.expire = MagicMock()
        # results: [zremrangebyscore, zcard, zadd, expire]
        pipe.execute = AsyncMock(return_value=[None, zcard_count, None, None])

        redis = MagicMock()
        redis.pipeline.return_value = pipe
        return redis

    @pytest.mark.asyncio
    async def test_allowed_under_limit(self):
        from security.rate_limiter import RateLimiter
        redis = self._make_redis(zcard_count=5)  # 5 requests, limit=30
        limiter = RateLimiter(redis, rpm=30)
        assert await limiter.is_allowed(user_id=42) is True

    @pytest.mark.asyncio
    async def test_denied_at_limit(self):
        from security.rate_limiter import RateLimiter
        redis = self._make_redis(zcard_count=30)  # exactly at limit
        limiter = RateLimiter(redis, rpm=30)
        assert await limiter.is_allowed(user_id=42) is False

    @pytest.mark.asyncio
    async def test_denied_over_limit(self):
        from security.rate_limiter import RateLimiter
        redis = self._make_redis(zcard_count=50)
        limiter = RateLimiter(redis, rpm=30)
        assert await limiter.is_allowed(user_id=1) is False

    @pytest.mark.asyncio
    async def test_redis_error_fails_open(self):
        """On Redis error, rate limiter must fail open (return True)."""
        from security.rate_limiter import RateLimiter
        redis = MagicMock()
        redis.pipeline.side_effect = Exception("Redis down")
        limiter = RateLimiter(redis, rpm=30)
        assert await limiter.is_allowed(user_id=42) is True

    def test_get_rate_limiter_returns_none_when_not_init(self):
        import security.rate_limiter as rl_module
        rl_module._instance = None
        from security.rate_limiter import get_rate_limiter
        assert get_rate_limiter() is None

    def test_init_rate_limiter_sets_instance(self):
        from security.rate_limiter import RateLimiter, init_rate_limiter, get_rate_limiter
        fake_redis = MagicMock()
        limiter = init_rate_limiter(fake_redis, rpm=20)
        assert isinstance(limiter, RateLimiter)
        assert get_rate_limiter() is limiter

    @pytest.mark.asyncio
    async def test_custom_rpm_respected(self):
        from security.rate_limiter import RateLimiter
        # count=3, rpm=3 → denied (3 >= 3)
        redis = self._make_redis(zcard_count=3)
        limiter = RateLimiter(redis, rpm=3)
        assert await limiter.is_allowed(user_id=1) is False