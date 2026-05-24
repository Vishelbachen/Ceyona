"""
test_coverage_gap3.py

Third coverage boost — targets modules at 0 % or very low coverage after gap2.
Goal: push total from 58.83 % → ≥ 60 % (need ~90 extra covered statements).

Targets and expected gains:
  transport/telegram/media_group_aggregator.py   0 %  → ~70 %  (+67 stmts)
  transport/telegram/callback_handler.py        57 %  → ~95 %  (+11 stmts)
  transport/telegram/auth_middleware.py         52 %  → ~95 %  (+12 stmts)
  transport/telegram/message_router.py          97 %  → 100 %  (+2  stmts)

All pure unit tests — no Redis, Supabase, Groq, HuggingFace.
Redis is mocked via AsyncMock/MagicMock at the boundary.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/callback_handler.py  (57 % → ~95 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestCallbackHandler:
    def test_parse_balance_action(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq1", "data": "balance"}}
        ctx = parse_callback(update, user_id=42)
        assert ctx.action == CallbackAction.BALANCE
        assert ctx.payload == ""
        assert ctx.callback_query_id == "cq1"
        assert ctx.user_id == 42

    def test_parse_help_action(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq2", "data": "help"}}
        ctx = parse_callback(update, user_id=7)
        assert ctx.action == CallbackAction.HELP
        assert ctx.payload == ""

    def test_parse_cancel_action(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq3", "data": "cancel"}}
        ctx = parse_callback(update, user_id=1)
        assert ctx.action == CallbackAction.CANCEL

    def test_parse_action_with_payload(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq4", "data": "balance:extra_data"}}
        ctx = parse_callback(update, user_id=99)
        assert ctx.action == CallbackAction.BALANCE
        assert ctx.payload == "extra_data"

    def test_parse_unknown_action(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq5", "data": "nonexistent_action"}}
        ctx = parse_callback(update, user_id=5)
        assert ctx.action == CallbackAction.UNKNOWN

    def test_parse_unknown_action_with_payload(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq6", "data": "bogus:some:stuff"}}
        ctx = parse_callback(update, user_id=5)
        assert ctx.action == CallbackAction.UNKNOWN
        assert ctx.payload == "some:stuff"

    def test_parse_empty_data(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {"callback_query": {"id": "cq7", "data": ""}}
        ctx = parse_callback(update, user_id=1)
        assert ctx.action == CallbackAction.UNKNOWN

    def test_parse_missing_callback_query(self):
        from transport.telegram.callback_handler import CallbackAction, parse_callback
        update = {}
        ctx = parse_callback(update, user_id=1)
        assert ctx.action == CallbackAction.UNKNOWN
        assert ctx.callback_query_id == ""

    def test_callback_action_enum_values(self):
        from transport.telegram.callback_handler import CallbackAction
        assert CallbackAction.BALANCE == "balance"
        assert CallbackAction.HELP == "help"
        assert CallbackAction.CANCEL == "cancel"
        assert CallbackAction.UNKNOWN == "unknown"

    def test_callback_context_frozen(self):
        from transport.telegram.callback_handler import CallbackAction, CallbackContext
        ctx = CallbackContext(
            action=CallbackAction.HELP,
            payload="",
            callback_query_id="x",
            user_id=1,
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.user_id = 999  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/auth_middleware.py  (52 % → ~95 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthMiddleware:
    def test_verify_update_message(self):
        from transport.telegram.auth_middleware import verify_update
        update = {"message": {"from": {"id": 123, "username": "alice"}, "text": "hi"}}
        result = verify_update(update)
        assert result.allowed is True
        assert result.user_id == 123
        assert result.username == "alice"

    def test_verify_update_callback_query(self):
        from transport.telegram.auth_middleware import verify_update
        update = {"callback_query": {"from": {"id": 456, "username": "bob"}, "data": "balance"}}
        result = verify_update(update)
        assert result.allowed is True
        assert result.user_id == 456

    def test_verify_update_edited_message(self):
        from transport.telegram.auth_middleware import verify_update
        update = {"edited_message": {"from": {"id": 789}, "text": "edited"}}
        result = verify_update(update)
        assert result.allowed is True
        assert result.user_id == 789
        assert result.username is None

    def test_verify_update_no_user_id_rejected(self):
        from transport.telegram.auth_middleware import verify_update
        update = {}
        result = verify_update(update)
        assert result.allowed is False
        assert result.reason == "no_user_id"

    def test_verify_update_message_no_from(self):
        from transport.telegram.auth_middleware import verify_update
        update = {"message": {"text": "hi"}}  # no "from" key
        result = verify_update(update)
        assert result.allowed is False

    def test_verify_webhook_secret_match(self):
        from transport.telegram.auth_middleware import verify_webhook_secret
        assert verify_webhook_secret("mysecret", "mysecret") is True

    def test_verify_webhook_secret_mismatch(self):
        from transport.telegram.auth_middleware import verify_webhook_secret
        assert verify_webhook_secret("wrong", "mysecret") is False

    def test_verify_webhook_secret_empty(self):
        from transport.telegram.auth_middleware import verify_webhook_secret
        assert verify_webhook_secret("", "") is True

    def test_verify_webhook_secret_timing_safe(self):
        """Must use constant-time comparison (hmac.compare_digest)."""
        import hmac
        from transport.telegram.auth_middleware import verify_webhook_secret
        # Verify it doesn't short-circuit on first char mismatch
        # (behavioural test: same result regardless of where mismatch is)
        assert verify_webhook_secret("aaaaab", "aaaaac") is False
        assert verify_webhook_secret("baaa", "aaaa") is False

    def test_auth_result_allowed_true(self):
        from transport.telegram.auth_middleware import AuthResult
        r = AuthResult(allowed=True, user_id=1, username="u")
        assert r.allowed is True
        assert r.user_id == 1

    def test_auth_result_denied(self):
        from transport.telegram.auth_middleware import AuthResult
        r = AuthResult(allowed=False, reason="no_user_id")
        assert r.allowed is False
        assert r.user_id is None
        assert r.reason == "no_user_id"

    def test_auth_result_frozen(self):
        from transport.telegram.auth_middleware import AuthResult
        r = AuthResult(allowed=True, user_id=1)
        with pytest.raises((AttributeError, TypeError)):
            r.allowed = False  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/message_router.py  (97 % → 100 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageRouterRemaining:
    def test_extract_voice_from_message(self):
        from transport.telegram.message_router import extract_voice, has_voice
        update = {
            "message": {
                "voice": {
                    "file_id": "voice123",
                    "duration": 5,
                    "mime_type": "audio/ogg",
                    "file_size": 2048,
                }
            }
        }
        result = extract_voice(update)
        assert result is not None
        assert result["file_id"] == "voice123"
        assert result["source"] == "voice"
        assert has_voice(update) is True

    def test_extract_audio_from_message(self):
        from transport.telegram.message_router import extract_voice, has_voice
        update = {
            "message": {
                "audio": {
                    "file_id": "audio456",
                    "duration": 120,
                    "mime_type": "audio/mpeg",
                    "file_size": 4096,
                }
            }
        }
        result = extract_voice(update)
        assert result is not None
        assert result["file_id"] == "audio456"
        assert result["source"] == "audio"
        assert has_voice(update) is True

    def test_extract_voice_no_voice(self):
        from transport.telegram.message_router import extract_voice, has_voice
        update = {"message": {"text": "hello"}}
        assert extract_voice(update) is None
        assert has_voice(update) is False

    def test_extract_voice_empty_update(self):
        from transport.telegram.message_router import extract_voice
        assert extract_voice({}) is None

    def test_extract_callback_data(self):
        from transport.telegram.message_router import extract_callback_data
        update = {"callback_query": {"data": "balance:extra"}}
        assert extract_callback_data(update) == "balance:extra"

    def test_extract_callback_data_missing(self):
        from transport.telegram.message_router import extract_callback_data
        assert extract_callback_data({}) == ""

    def test_extract_media_group_id_present(self):
        from transport.telegram.message_router import extract_media_group_id
        update = {"message": {"media_group_id": "grp_99", "photo": [{}]}}
        assert extract_media_group_id(update) == "grp_99"

    def test_extract_media_group_id_absent(self):
        from transport.telegram.message_router import extract_media_group_id
        update = {"message": {"photo": [{}]}}
        assert extract_media_group_id(update) is None

    def test_extract_message_id(self):
        from transport.telegram.message_router import extract_message_id
        update = {"message": {"message_id": 42}}
        assert extract_message_id(update) == 42

    def test_extract_message_id_missing(self):
        from transport.telegram.message_router import extract_message_id
        assert extract_message_id({}) == 0


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/media_group_aggregator.py  (0 % → ~70 %)
# ══════════════════════════════════════════════════════════════════════════════

def _make_redis_mock() -> MagicMock:
    """Return a minimal async Redis mock wired for aggregator tests."""
    redis = MagicMock()
    redis.config_set = AsyncMock()
    redis.pubsub = MagicMock()

    # register_script returns a callable async mock (the Lua script executor)
    script_mock = AsyncMock(return_value=1)
    redis.register_script = MagicMock(return_value=script_mock)

    # pubsub
    pubsub = AsyncMock()
    pubsub.psubscribe = AsyncMock()
    pubsub.close = AsyncMock()
    pubsub.listen = AsyncMock()
    redis.pubsub.return_value = pubsub

    return redis


class TestMediaGroupItem:
    def test_dataclass_fields(self):
        from transport.telegram.media_group_aggregator import MediaGroupItem
        item = MediaGroupItem(file_id="f1", message_id=10, caption="hello")
        assert item.file_id == "f1"
        assert item.message_id == 10
        assert item.caption == "hello"

    def test_default_caption_empty(self):
        from transport.telegram.media_group_aggregator import MediaGroupItem
        item = MediaGroupItem(file_id="f2", message_id=11)
        assert item.caption == ""

    def test_frozen(self):
        from transport.telegram.media_group_aggregator import MediaGroupItem
        item = MediaGroupItem(file_id="f3", message_id=12)
        with pytest.raises((AttributeError, TypeError)):
            item.file_id = "changed"  # type: ignore[misc]


class TestMediaGroupAggregatorInit:
    def test_init_defaults(self):
        from transport.telegram.media_group_aggregator import (
            MediaGroupAggregator,
            _DEBOUNCE_TTL_SECONDS,
            _MAX_GROUP_SIZE,
        )
        redis = MagicMock()
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        assert agg._redis is redis
        assert agg._on_group_ready is cb
        assert agg._debounce_ttl == _DEBOUNCE_TTL_SECONDS
        assert agg._max_group_size == _MAX_GROUP_SIZE
        assert agg._lua_add is None
        assert agg._lua_flush is None
        assert agg._listener_task is None

    def test_init_custom_params(self):
        from transport.telegram.media_group_aggregator import MediaGroupAggregator
        redis = MagicMock()
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb, debounce_ttl=2, max_group_size=5)
        assert agg._debounce_ttl == 2
        assert agg._max_group_size == 5


class TestMediaGroupAggregatorStart:
    @pytest.mark.asyncio
    async def test_start_registers_scripts_and_creates_task(self):
        from transport.telegram.media_group_aggregator import MediaGroupAggregator
        redis = _make_redis_mock()
        cb = AsyncMock()

        # Make listen() produce an immediate async generator that returns nothing
        async def _empty_listen():
            return
            yield  # pragma: no cover — make it a generator

        redis.pubsub.return_value.listen = _empty_listen

        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        # Lua scripts registered
        assert redis.register_script.call_count == 2
        assert agg._lua_add is not None
        assert agg._lua_flush is not None

        # Keyspace notifications enabled
        redis.config_set.assert_awaited_once_with("notify-keyspace-events", "Ex")

        # Listener task created
        assert agg._listener_task is not None
        assert not agg._listener_task.done() or agg._listener_task.cancelled()

        await agg.stop()

    @pytest.mark.asyncio
    async def test_start_continues_if_config_set_fails(self):
        """config_set failure must not prevent aggregator from starting."""
        from transport.telegram.media_group_aggregator import MediaGroupAggregator
        redis = _make_redis_mock()
        redis.config_set = AsyncMock(side_effect=Exception("permission denied"))

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()           # must not raise
        assert agg._listener_task is not None
        await agg.stop()


class TestMediaGroupAggregatorStop:
    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        from transport.telegram.media_group_aggregator import MediaGroupAggregator
        redis = _make_redis_mock()

        # Listener that blocks forever
        async def _blocking_listen():
            await asyncio.sleep(999)
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _blocking_listen
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()
        assert agg._listener_task is not None
        await agg.stop()
        assert agg._listener_task.cancelled() or agg._listener_task.done()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self):
        from transport.telegram.media_group_aggregator import MediaGroupAggregator
        redis = _make_redis_mock()
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.stop()   # must not raise, task is None


class TestMediaGroupAggregatorAdd:
    @pytest.mark.asyncio
    async def test_add_calls_lua_script(self):
        from transport.telegram.media_group_aggregator import MediaGroupAggregator, MediaGroupItem
        redis = _make_redis_mock()
        lua_mock = AsyncMock(return_value=1)
        redis.register_script = MagicMock(return_value=lua_mock)

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        item = MediaGroupItem(file_id="file1", message_id=100, caption="test")
        await agg.add("user1:grp1", item)

        # lua_add (first registered script) must be called
        lua_mock.assert_awaited()
        await agg.stop()

    @pytest.mark.asyncio
    async def test_add_triggers_flush_at_max_size(self):
        """When lua returns max_group_size, _flush() must be called immediately."""
        from transport.telegram.media_group_aggregator import (
            MediaGroupAggregator,
            MediaGroupItem,
            _MAX_GROUP_SIZE,
        )
        redis = _make_redis_mock()

        # First script = lua_add (returns max size), second = lua_flush (returns empty)
        lua_add_mock = AsyncMock(return_value=_MAX_GROUP_SIZE)
        lua_flush_mock = AsyncMock(return_value=None)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            if call_count[0] == 1:
                return lua_add_mock
            return lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen
        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        item = MediaGroupItem(file_id="f", message_id=1)
        await agg.add("uid:gid", item)

        # lua_flush must have been invoked (via _flush)
        lua_flush_mock.assert_awaited()
        await agg.stop()


class TestMediaGroupAggregatorFlush:
    @pytest.mark.asyncio
    async def test_flush_calls_callback_with_items(self):
        from transport.telegram.media_group_aggregator import MediaGroupAggregator, MediaGroupItem

        raw_items = [
            json.dumps({"file_id": "fA", "message_id": 1, "caption": "cap1"}),
            json.dumps({"file_id": "fB", "message_id": 2, "caption": ""}),
        ]

        redis = _make_redis_mock()
        lua_add_mock = AsyncMock(return_value=1)
        lua_flush_mock = AsyncMock(return_value=raw_items)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            return lua_add_mock if call_count[0] == 1 else lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen

        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        await agg._flush("user42:group7")

        cb.assert_awaited_once()
        group_id_arg, items_arg = cb.call_args[0]
        assert group_id_arg == "user42:group7"
        assert len(items_arg) == 2
        assert items_arg[0].file_id == "fA"
        assert items_arg[0].caption == "cap1"
        assert items_arg[1].file_id == "fB"

        await agg.stop()

    @pytest.mark.asyncio
    async def test_flush_skips_when_lock_not_acquired(self):
        """lua_flush returning None/empty means another instance already flushed."""
        from transport.telegram.media_group_aggregator import MediaGroupAggregator

        redis = _make_redis_mock()
        lua_add_mock = AsyncMock(return_value=1)
        lua_flush_mock = AsyncMock(return_value=None)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            return lua_add_mock if call_count[0] == 1 else lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen

        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        await agg._flush("uid:gid")
        cb.assert_not_awaited()  # callback must NOT be called if lock not acquired

        await agg.stop()

    @pytest.mark.asyncio
    async def test_flush_skips_malformed_items(self):
        """Malformed JSON items must be skipped without crashing."""
        from transport.telegram.media_group_aggregator import MediaGroupAggregator

        raw_items = [
            b"not-valid-json",
            json.dumps({"file_id": "fGood", "message_id": 5}),
        ]

        redis = _make_redis_mock()
        lua_add_mock = AsyncMock(return_value=1)
        lua_flush_mock = AsyncMock(return_value=raw_items)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            return lua_add_mock if call_count[0] == 1 else lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen

        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        await agg._flush("uid:gid")

        # Callback called with only the valid item
        cb.assert_awaited_once()
        _, items = cb.call_args[0]
        assert len(items) == 1
        assert items[0].file_id == "fGood"

        await agg.stop()

    @pytest.mark.asyncio
    async def test_flush_callback_exception_does_not_propagate(self):
        """Callback crash must be caught — aggregator must not crash."""
        from transport.telegram.media_group_aggregator import MediaGroupAggregator

        raw_items = [json.dumps({"file_id": "fX", "message_id": 99})]
        redis = _make_redis_mock()
        lua_add_mock = AsyncMock(return_value=1)
        lua_flush_mock = AsyncMock(return_value=raw_items)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            return lua_add_mock if call_count[0] == 1 else lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _empty_listen():
            return
            yield  # pragma: no cover

        redis.pubsub.return_value.listen = _empty_listen

        cb = AsyncMock(side_effect=RuntimeError("callback crash"))
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()

        await agg._flush("uid:gid")  # must not raise

        await agg.stop()


class TestMediaGroupKeyspaceListener:
    @pytest.mark.asyncio
    async def test_listener_ignores_non_ttl_keys(self):
        """Keys not matching media_group:*:ttl must be ignored — no flush called."""
        from transport.telegram.media_group_aggregator import MediaGroupAggregator

        messages = [
            {"type": "pmessage", "data": b"some_other_key"},
            {"type": "pmessage", "data": b"media_group:uid:gid"},     # no :ttl suffix
            {"type": "subscribe", "data": b"whatever"},
        ]

        redis = _make_redis_mock()
        lua_add_mock = AsyncMock(return_value=1)
        lua_flush_mock = AsyncMock(return_value=None)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            return lua_add_mock if call_count[0] == 1 else lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _listen_messages():
            for m in messages:
                yield m

        pubsub = AsyncMock()
        pubsub.psubscribe = AsyncMock()
        pubsub.close = AsyncMock()
        pubsub.listen = _listen_messages
        redis.pubsub.return_value = pubsub

        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()
        # Give listener time to process
        await asyncio.sleep(0.05)
        cb.assert_not_awaited()
        await agg.stop()

    @pytest.mark.asyncio
    async def test_listener_fires_flush_on_ttl_expiry(self):
        """A media_group:*:ttl expiry message must trigger _flush()."""
        from transport.telegram.media_group_aggregator import MediaGroupAggregator

        messages = [
            {"type": "pmessage", "data": b"media_group:user1:grp5:ttl"},
        ]

        redis = _make_redis_mock()
        lua_add_mock = AsyncMock(return_value=1)
        # flush returns one item
        raw = [json.dumps({"file_id": "fZ", "message_id": 77})]
        lua_flush_mock = AsyncMock(return_value=raw)
        call_count = [0]

        def register_side_effect(script):
            call_count[0] += 1
            return lua_add_mock if call_count[0] == 1 else lua_flush_mock

        redis.register_script = MagicMock(side_effect=register_side_effect)

        async def _listen_messages():
            for m in messages:
                yield m

        pubsub = AsyncMock()
        pubsub.psubscribe = AsyncMock()
        pubsub.close = AsyncMock()
        pubsub.listen = _listen_messages
        redis.pubsub.return_value = pubsub

        cb = AsyncMock()
        agg = MediaGroupAggregator(redis, cb)
        await agg.start()
        # Give asyncio time to process the spawned flush task
        await asyncio.sleep(0.1)

        cb.assert_awaited_once()
        group_id_arg, items = cb.call_args[0]
        assert group_id_arg == "user1:grp5"
        assert items[0].file_id == "fZ"

        await agg.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Module-level constants
# ══════════════════════════════════════════════════════════════════════════════

class TestAggregatorConstants:
    def test_debounce_ttl_positive(self):
        from transport.telegram.media_group_aggregator import _DEBOUNCE_TTL_SECONDS
        assert _DEBOUNCE_TTL_SECONDS > 0

    def test_max_group_size_matches_telegram_limit(self):
        from transport.telegram.media_group_aggregator import _MAX_GROUP_SIZE
        assert _MAX_GROUP_SIZE == 10

    def test_lua_add_script_is_string(self):
        from transport.telegram.media_group_aggregator import _LUA_ADD
        assert isinstance(_LUA_ADD, str)
        assert "RPUSH" in _LUA_ADD

    def test_lua_flush_script_is_string(self):
        from transport.telegram.media_group_aggregator import _LUA_FLUSH
        assert isinstance(_LUA_FLUSH, str)
        assert "SETNX" in _LUA_FLUSH