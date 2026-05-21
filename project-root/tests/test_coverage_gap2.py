"""
test_coverage_gap2.py

Second coverage boost — targets modules still under-covered after
test_transport_and_retrieval.py brought total from 41% → 57%.

Targets:
  payments/pricing_engine.py          40% → ~90%
  retrieval/fusion/hybrid_scorer.py    0% → 100%
  retrieval/sparse/bm25_engine.py      0% → ~90%
  retrieval/reranker/cross_encoder.py 38% → ~85%
  retrieval/cache/embedding_cache.py   0% → ~85%
  retrieval/cache/query_cache.py       0% → ~85%
  retrieval/cache/rerank_cache.py      0% → ~85%
  retrieval/cache/ttl_policy.py        0% → 100%
  transport/telegram/webhook.py       24% → ~55%

All pure unit tests — no real I/O, no Groq, Supabase, Redis, HuggingFace.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# payments/pricing_engine.py
# ══════════════════════════════════════════════════════════════════════════════

class TestPricingEngine:
    def test_nano_to_ton(self):
        from payments.pricing_engine import nano_to_ton
        assert nano_to_ton(1_000_000_000) == pytest.approx(1.0)
        assert nano_to_ton(500_000_000) == pytest.approx(0.5)
        assert nano_to_ton(0) == 0.0

    def test_ton_to_nano(self):
        from payments.pricing_engine import ton_to_nano
        assert ton_to_nano(1.0) == 1_000_000_000
        assert ton_to_nano(0.5) == 500_000_000
        assert ton_to_nano(0.0) == 0

    def test_apply_margin_default(self):
        from payments.pricing_engine import apply_margin
        assert apply_margin(1.0) == pytest.approx(1.3)
        assert apply_margin(0.0) == 0.0

    def test_apply_margin_custom(self):
        from payments.pricing_engine import apply_margin
        assert apply_margin(2.0, margin=1.5) == pytest.approx(3.0)

    def test_roundtrip_ton_nano(self):
        from payments.pricing_engine import nano_to_ton, ton_to_nano
        original = 2_500_000_000
        assert ton_to_nano(nano_to_ton(original)) == original

    @pytest.mark.asyncio
    async def test_get_ton_price_usd_success(self):
        from payments.pricing_engine import get_ton_price_usd

        mock_data = {"the-open-network": {"usd": 5.42}}
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=mock_data)

        with patch("payments.pricing_engine.httpx.AsyncClient") as mock_client:
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.get = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_cm

            price = await get_ton_price_usd()

        assert price == pytest.approx(5.42)

    @pytest.mark.asyncio
    async def test_get_ton_price_usd_fallback_on_error(self):
        from payments.pricing_engine import _FALLBACK_TON_USD, get_ton_price_usd

        with patch("payments.pricing_engine.httpx.AsyncClient") as mock_client:
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.get = AsyncMock(side_effect=Exception("network error"))
            mock_client.return_value = mock_cm

            price = await get_ton_price_usd()

        assert price == _FALLBACK_TON_USD

    @pytest.mark.asyncio
    async def test_nano_to_usd(self):
        from payments.pricing_engine import nano_to_usd

        with patch("payments.pricing_engine.get_ton_price_usd",
                   new_callable=AsyncMock, return_value=4.0):
            result = await nano_to_usd(1_000_000_000)  # 1 TON at $4 = $4

        assert result == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_usd_to_nano(self):
        from payments.pricing_engine import usd_to_nano

        with patch("payments.pricing_engine.get_ton_price_usd",
                   new_callable=AsyncMock, return_value=4.0):
            result = await usd_to_nano(4.0)  # $4 at $4/TON = 1 TON = 1e9 nano

        assert result == 1_000_000_000

    @pytest.mark.asyncio
    async def test_usd_to_nano_zero_price_returns_zero(self):
        from payments.pricing_engine import usd_to_nano

        with patch("payments.pricing_engine.get_ton_price_usd",
                   new_callable=AsyncMock, return_value=0.0):
            result = await usd_to_nano(1.0)

        assert result == 0


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/cache/ttl_policy.py
# ══════════════════════════════════════════════════════════════════════════════

class TestTTLPolicy:
    def test_constants_are_positive(self):
        from retrieval.cache.ttl_policy import (
            EMBEDDING_CACHE_TTL,
            QUERY_CACHE_TTL,
            RERANK_CACHE_TTL,
        )
        assert QUERY_CACHE_TTL > 0
        assert EMBEDDING_CACHE_TTL > 0
        assert RERANK_CACHE_TTL > 0

    def test_embedding_ttl_longer_than_rerank(self):
        from retrieval.cache.ttl_policy import EMBEDDING_CACHE_TTL, RERANK_CACHE_TTL
        assert EMBEDDING_CACHE_TTL > RERANK_CACHE_TTL


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/cache/embedding_cache.py
# ══════════════════════════════════════════════════════════════════════════════

class TestEmbeddingCache:
    def _make_redis(self):
        r = AsyncMock()
        r.get = AsyncMock()
        r.setex = AsyncMock()
        return r

    def test_key_is_deterministic(self):
        from retrieval.cache.embedding_cache import EmbeddingCache
        redis = self._make_redis()
        c = EmbeddingCache(redis)
        k1 = c._key("hello", "model-a")
        k2 = c._key("hello", "model-a")
        assert k1 == k2
        assert k1.startswith("emb:")

    def test_key_differs_for_different_inputs(self):
        from retrieval.cache.embedding_cache import EmbeddingCache
        redis = self._make_redis()
        c = EmbeddingCache(redis)
        assert c._key("hello", "model-a") != c._key("world", "model-a")
        assert c._key("hello", "model-a") != c._key("hello", "model-b")

    @pytest.mark.asyncio
    async def test_get_returns_none_on_cache_miss(self):
        from retrieval.cache.embedding_cache import EmbeddingCache
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=None)
        c = EmbeddingCache(redis)
        result = await c.get("query", "model")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_vector_on_hit(self):
        import json

        from retrieval.cache.embedding_cache import EmbeddingCache
        vector = [0.1, 0.2, 0.3]
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=json.dumps(vector).encode())
        c = EmbeddingCache(redis)
        result = await c.get("query", "model")
        assert result == vector

    @pytest.mark.asyncio
    async def test_get_returns_none_on_exception(self):
        from retrieval.cache.embedding_cache import EmbeddingCache
        redis = self._make_redis()
        redis.get = AsyncMock(side_effect=Exception("redis down"))
        c = EmbeddingCache(redis)
        result = await c.get("query", "model")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_calls_setex(self):
        from retrieval.cache.embedding_cache import EmbeddingCache
        redis = self._make_redis()
        c = EmbeddingCache(redis)
        await c.set("query", "model", [0.1, 0.2])
        redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_silently_handles_exception(self):
        from retrieval.cache.embedding_cache import EmbeddingCache
        redis = self._make_redis()
        redis.setex = AsyncMock(side_effect=Exception("write error"))
        c = EmbeddingCache(redis)
        await c.set("query", "model", [0.1])  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/cache/query_cache.py
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryCache:
    def _make_redis(self):
        r = AsyncMock()
        r.get = AsyncMock()
        r.setex = AsyncMock()
        return r

    def test_key_deterministic(self):
        from retrieval.cache.query_cache import QueryCache
        c = QueryCache(self._make_redis())
        assert c._key("q", "u1") == c._key("q", "u1")
        assert c._key("q", "u1").startswith("qcache:")

    def test_key_differs_by_user(self):
        from retrieval.cache.query_cache import QueryCache
        c = QueryCache(self._make_redis())
        assert c._key("q", "u1") != c._key("q", "u2")

    @pytest.mark.asyncio
    async def test_get_miss_returns_none(self):
        from retrieval.cache.query_cache import QueryCache
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=None)
        c = QueryCache(redis)
        assert await c.get("query", "user") is None

    @pytest.mark.asyncio
    async def test_get_hit_returns_data(self):
        import json

        from retrieval.cache.query_cache import QueryCache
        data = [{"content": "doc1", "score": 0.9}]
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=json.dumps(data).encode())
        c = QueryCache(redis)
        result = await c.get("query", "user")
        assert result == data

    @pytest.mark.asyncio
    async def test_get_exception_returns_none(self):
        from retrieval.cache.query_cache import QueryCache
        redis = self._make_redis()
        redis.get = AsyncMock(side_effect=Exception("boom"))
        c = QueryCache(redis)
        assert await c.get("q", "u") is None

    @pytest.mark.asyncio
    async def test_set_calls_setex(self):
        from retrieval.cache.query_cache import QueryCache
        redis = self._make_redis()
        c = QueryCache(redis)
        await c.set("q", "u", [{"content": "x", "score": 1.0}])
        redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_exception_silent(self):
        from retrieval.cache.query_cache import QueryCache
        redis = self._make_redis()
        redis.setex = AsyncMock(side_effect=Exception("write error"))
        c = QueryCache(redis)
        await c.set("q", "u", [])  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/cache/rerank_cache.py
# ══════════════════════════════════════════════════════════════════════════════

class TestRerankCache:
    def _make_redis(self):
        r = AsyncMock()
        r.get = AsyncMock()
        r.setex = AsyncMock()
        return r

    @pytest.mark.asyncio
    async def test_get_miss_returns_none(self):
        from retrieval.cache.rerank_cache import RerankCache
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=None)
        c = RerankCache(redis)
        result = await c.get("query", ["doc1", "doc2"])
        assert result is None

    @pytest.mark.asyncio
    async def test_get_hit_returns_tuples(self):
        import json

        from retrieval.cache.rerank_cache import RerankCache
        data = [{"content": "doc1", "score": 0.9}, {"content": "doc2", "score": 0.5}]
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=json.dumps(data).encode())
        c = RerankCache(redis)
        result = await c.get("query", ["doc1", "doc2"])
        assert result is not None
        assert result[0] == ("doc1", 0.9)
        assert result[1] == ("doc2", 0.5)

    @pytest.mark.asyncio
    async def test_get_exception_returns_none(self):
        from retrieval.cache.rerank_cache import RerankCache
        redis = self._make_redis()
        redis.get = AsyncMock(side_effect=Exception("redis error"))
        c = RerankCache(redis)
        assert await c.get("q", ["a"]) is None

    @pytest.mark.asyncio
    async def test_set_calls_setex(self):
        from retrieval.cache.rerank_cache import RerankCache
        redis = self._make_redis()
        c = RerankCache(redis)
        await c.set("query", ["doc1"], [("doc1", 0.9)])
        redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_exception_silent(self):
        from retrieval.cache.rerank_cache import RerankCache
        redis = self._make_redis()
        redis.setex = AsyncMock(side_effect=Exception("write error"))
        c = RerankCache(redis)
        await c.set("q", ["doc1"], [("doc1", 0.9)])  # must not raise

    def test_key_format(self):
        from retrieval.cache.rerank_cache import RerankCache
        c = RerankCache(MagicMock())
        key = c._key("my query", "abc123")
        assert key.startswith("rerank:")


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/fusion/hybrid_scorer.py
# ══════════════════════════════════════════════════════════════════════════════

class TestHybridScorer:
    def test_empty_inputs_return_empty(self):
        from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
        result = reciprocal_rank_fusion([], [])
        assert result == []

    def test_dense_only(self):
        from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
        dense = [("doc_a", 0.9), ("doc_b", 0.7)]
        result = reciprocal_rank_fusion([], dense)
        assert len(result) == 2
        contents = [r.content for r in result]
        assert "doc_a" in contents
        assert "doc_b" in contents

    def test_sparse_only(self):
        from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
        sparse = [("doc_x", 1.0), ("doc_y", 0.5)]
        result = reciprocal_rank_fusion(sparse, [])
        assert len(result) == 2

    def test_fusion_combines_results(self):
        from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
        sparse = [("shared_doc", 1.0), ("sparse_only", 0.5)]
        dense  = [("shared_doc", 0.9), ("dense_only", 0.4)]
        result = reciprocal_rank_fusion(sparse, dense)
        contents = [r.content for r in result]
        # shared_doc appears in both — should rank first due to double contribution
        assert contents[0] == "shared_doc"
        assert len(result) == 3

    def test_results_sorted_descending(self):
        from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
        sparse = [("a", 1.0), ("b", 0.5), ("c", 0.1)]
        dense  = [("b", 0.9), ("a", 0.6), ("d", 0.3)]
        result = reciprocal_rank_fusion(sparse, dense)
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_dense_weight_higher_means_dense_preferred(self):
        from retrieval.fusion.hybrid_scorer import reciprocal_rank_fusion
        sparse = [("sparse_top", 1.0)]
        dense  = [("dense_top", 1.0)]
        result = reciprocal_rank_fusion(
            sparse, dense, sparse_weight=0.1, dense_weight=0.9
        )
        assert result[0].content == "dense_top"

    def test_fused_result_has_score_field(self):
        from retrieval.fusion.hybrid_scorer import FusedResult, reciprocal_rank_fusion
        result = reciprocal_rank_fusion([("doc", 1.0)], [])
        assert isinstance(result[0], FusedResult)
        assert result[0].score > 0


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/sparse/bm25_engine.py
# ══════════════════════════════════════════════════════════════════════════════

class TestBM25Engine:
    def test_empty_corpus_returns_empty(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine()
        assert engine.search("query") == []

    def test_index_and_search_basic(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine()
        docs = [
            "the quick brown fox jumps over the lazy dog",
            "python programming language tutorial",
            "machine learning deep learning neural networks",
        ]
        engine.index(docs)
        results = engine.search("python programming", top_k=3)
        assert len(results) >= 1
        assert results[0].content == "python programming language tutorial"

    def test_search_returns_top_k(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine()
        docs = [f"document number {i} with some text" for i in range(20)]
        engine.index(docs)
        results = engine.search("document text", top_k=5)
        assert len(results) <= 5

    def test_search_no_match_returns_empty(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine()
        engine.index(["hello world", "foo bar"])
        results = engine.search("zzzznonexistentterm")
        assert results == []

    def test_scores_descending(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine()
        engine.index([
            "python python python",
            "python",
            "java programming",
        ])
        results = engine.search("python")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_reindex_replaces_corpus(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine()
        engine.index(["old document content"])
        engine.index(["brand new corpus entry"])
        results = engine.search("brand new corpus")
        assert len(results) == 1
        assert "brand new" in results[0].content

    def test_bm25_result_has_content_and_score(self):
        from retrieval.sparse.bm25_engine import BM25Engine, BM25Result
        engine = BM25Engine()
        engine.index(["test document"])
        results = engine.search("test")
        assert isinstance(results[0], BM25Result)
        assert isinstance(results[0].score, float)
        assert results[0].score > 0

    def test_custom_k1_b_params(self):
        from retrieval.sparse.bm25_engine import BM25Engine
        engine = BM25Engine(k1=1.2, b=0.5)
        assert engine.k1 == 1.2
        assert engine.b == 0.5
        engine.index(["hello world"])
        results = engine.search("hello")
        assert len(results) == 1


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/reranker/cross_encoder.py
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossEncoder:
    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty(self):
        from retrieval.reranker.cross_encoder import CrossEncoder
        enc = CrossEncoder()
        result = await enc.rerank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_returns_sorted_by_score(self):
        from retrieval.reranker.cross_encoder import CrossEncoder
        enc = CrossEncoder()
        candidates = ["doc_low", "doc_high", "doc_mid"]
        scores = [0.2, 0.9, 0.5]

        with patch("retrieval.reranker.cross_encoder.hf_client") as mock_hf:
            mock_hf.rerank = AsyncMock(return_value=scores)
            result = await enc.rerank("query", candidates)

        assert result[0][0] == "doc_high"
        assert result[0][1] == pytest.approx(0.9)
        assert result[-1][0] == "doc_low"

    @pytest.mark.asyncio
    async def test_rerank_fallback_on_error(self):
        """On HF client error, returns candidates with score 0.0."""
        from retrieval.reranker.cross_encoder import CrossEncoder
        enc = CrossEncoder()
        candidates = ["doc_a", "doc_b"]

        with patch("retrieval.reranker.cross_encoder.hf_client") as mock_hf:
            mock_hf.rerank = AsyncMock(side_effect=Exception("HF timeout"))
            result = await enc.rerank("query", candidates)

        assert len(result) == 2
        for content, score in result:
            assert content in candidates
            assert score == 0.0

    @pytest.mark.asyncio
    async def test_rerank_single_candidate(self):
        from retrieval.reranker.cross_encoder import CrossEncoder
        enc = CrossEncoder()

        with patch("retrieval.reranker.cross_encoder.hf_client") as mock_hf:
            mock_hf.rerank = AsyncMock(return_value=[0.75])
            result = await enc.rerank("query", ["only doc"])

        assert len(result) == 1
        assert result[0] == ("only doc", 0.75)


# ══════════════════════════════════════════════════════════════════════════════
# transport/telegram/webhook.py — internal helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestWebhookHelpers:
    @pytest.mark.asyncio
    async def test_send_message_empty_text_skips(self):
        """_send_message with empty text must not make HTTP call."""
        from transport.telegram.webhook import _send_message
        with patch("transport.telegram.webhook.httpx.AsyncClient") as mock_client:
            await _send_message(chat_id=1, text="")
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_makes_post(self):
        from transport.telegram.webhook import _send_message
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.post = AsyncMock()
        with patch("transport.telegram.webhook.httpx.AsyncClient", return_value=mock_cm):
            await _send_message(chat_id=123, text="hello")
        mock_cm.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_with_topup_empty_skips(self):
        from transport.telegram.webhook import _send_message_with_topup
        with patch("transport.telegram.webhook.httpx.AsyncClient") as mock_client:
            await _send_message_with_topup(chat_id=1, text="")
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_with_topup_sends_keyboard(self):
        from transport.telegram.webhook import _send_message_with_topup
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.post = AsyncMock()
        with patch("transport.telegram.webhook.httpx.AsyncClient", return_value=mock_cm):
            await _send_message_with_topup(chat_id=1, text="Low balance", lang="en")
        call_kwargs = mock_cm.post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json") or call_kwargs[0][1]
        assert "reply_markup" in body

    @pytest.mark.asyncio
    async def test_send_voice_returns_false_on_exception(self):
        from transport.telegram.webhook import _send_voice
        with patch("transport.telegram.webhook.httpx.AsyncClient") as mock_client:
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_cm.post = AsyncMock(side_effect=Exception("network error"))
            mock_client.return_value = mock_cm
            result = await _send_voice(chat_id=1, audio_bytes=b"audio")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_voice_returns_true_on_200(self):
        from transport.telegram.webhook import _send_voice
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.post = AsyncMock(return_value=mock_resp)
        with patch("transport.telegram.webhook.httpx.AsyncClient", return_value=mock_cm):
            result = await _send_voice(chat_id=1, audio_bytes=b"audio")
        assert result is True

    @pytest.mark.asyncio
    async def test_answer_callback_makes_post(self):
        from transport.telegram.webhook import _answer_callback
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_cm.post = AsyncMock()
        with patch("transport.telegram.webhook.httpx.AsyncClient", return_value=mock_cm):
            await _answer_callback(callback_query_id="cq123", text="ok")
        mock_cm.post.assert_awaited_once()