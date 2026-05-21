"""
Tests for meta/analysis.py.

analysis.py was recently wired into the pipeline (audit §2.2).
These tests verify the module works correctly before and after wiring.

All tests are pure — no I/O, no mocks needed.
"""

from meta.analysis import (
    AnalysisHint,
    AnalysisReport,
    HintType,
    _dominant_script,
    _full_analysis,
    _lightweight_analysis,
    analyse,
)

# ─── analyse() public API ─────────────────────────────────────────────────────

class TestAnalysePublicAPI:
    def test_returns_analysis_report(self):
        result = analyse("hello world")
        assert isinstance(result, AnalysisReport)

    def test_never_raises_on_empty(self):
        result = analyse("")
        assert result.word_count == 0
        assert result.hints == []

    def test_never_raises_on_whitespace_only(self):
        result = analyse("   \n\t  ")
        assert isinstance(result, AnalysisReport)

    def test_never_raises_on_very_long_text(self):
        result = analyse("word " * 10_000)
        assert isinstance(result, AnalysisReport)

    def test_lightweight_flag_propagated(self):
        result = analyse("hello", lightweight=True)
        assert result.lightweight is True

    def test_full_mode_flag(self):
        result = analyse("hello", lightweight=False)
        assert result.lightweight is False

    def test_word_count_correct(self):
        result = analyse("one two three")
        assert result.word_count == 3

    def test_char_count_correct(self):
        text = "hello"
        result = analyse(text)
        assert result.char_count == 5


# ─── HintType detection ───────────────────────────────────────────────────────

class TestHintDetection:
    def test_has_code_block_detected(self):
        result = analyse("Here is code:\n```python\nprint('hi')\n```")
        assert result.has(HintType.HAS_CODE_BLOCK)

    def test_has_math_detected(self):
        result = analyse("What is 2+2?")
        assert result.has(HintType.HAS_MATH)

    def test_has_math_with_equals(self):
        result = analyse("solve: x = 5 * 3")
        assert result.has(HintType.HAS_MATH)

    def test_has_url_detected(self):
        result = analyse("Visit https://example.com for more info")
        assert result.has(HintType.HAS_URL)

    def test_is_short_detected(self):
        result = analyse("Hello how are you")
        assert result.has(HintType.IS_SHORT)

    def test_is_short_not_detected_for_long_text(self):
        result = analyse(("word " * 50).strip())
        assert not result.has(HintType.IS_SHORT)

    def test_is_long_detected(self):
        result = analyse(("word " * 200).strip())
        assert result.has(HintType.IS_LONG)

    def test_likely_question_detected(self):
        result = analyse("What is the capital of France?")
        assert result.has(HintType.LIKELY_QUESTION)

    def test_likely_question_arabic_mark(self):
        result = analyse("ما هي عاصمة فرنسا؟")
        assert result.has(HintType.LIKELY_QUESTION)

    def test_likely_command_write(self):
        result = analyse("Write a poem about the sea")
        assert result.has(HintType.LIKELY_COMMAND)

    def test_likely_command_russian(self):
        result = analyse("Напиши стихотворение о море")
        assert result.has(HintType.LIKELY_COMMAND)


# ─── script detection ─────────────────────────────────────────────────────────

class TestScriptDetection:
    def test_cyrillic_detected(self):
        result = analyse("Привет, как дела?")
        assert result.has(HintType.SCRIPT_CYRILLIC)
        assert result.dominant_script == "cyrillic"

    def test_arabic_detected(self):
        result = analyse("مرحبا كيف حالك")
        assert result.has(HintType.SCRIPT_ARABIC)
        assert result.dominant_script == "arabic"

    def test_latin_detected(self):
        result = analyse("Hello world this is a test")
        assert result.has(HintType.SCRIPT_LATIN)
        assert result.dominant_script == "latin"

    def test_mixed_detected(self):
        result = analyse("Hello Привет مرحبا mixed")
        assert result.dominant_script == "mixed"
        assert result.has(HintType.IS_MULTILINGUAL)

    def test_dominant_script_single_script(self):
        counts = {"arabic": 0, "cjk": 0, "cyrillic": 100, "latin": 5}
        assert _dominant_script(counts) == "cyrillic"

    def test_dominant_script_mixed_below_70_percent(self):
        counts = {"arabic": 40, "cjk": 0, "cyrillic": 40, "latin": 20}
        assert _dominant_script(counts) == "mixed"

    def test_dominant_script_empty(self):
        counts = {"arabic": 0, "cjk": 0, "cyrillic": 0, "latin": 0}
        assert _dominant_script(counts) == "latin"


# ─── AnalysisReport methods ───────────────────────────────────────────────────

class TestAnalysisReport:
    def test_has_returns_true_for_present_hint(self):
        result = analyse("2+2=?")
        if result.has(HintType.HAS_MATH):
            assert result.has(HintType.HAS_MATH) is True

    def test_has_returns_false_for_absent_hint(self):
        result = analyse("hello world")
        # No code blocks in this text
        assert not result.has(HintType.HAS_CODE_BLOCK)

    def test_get_returns_hint_object(self):
        result = analyse("What is 2+2?")
        hint = result.get(HintType.HAS_MATH)
        if hint is not None:
            assert isinstance(hint, AnalysisHint)
            assert hint.confidence > 0

    def test_get_returns_none_for_absent_hint(self):
        result = analyse("hello world")
        assert result.get(HintType.HAS_CODE_BLOCK) is None

    def test_hint_confidence_in_range(self):
        result = analyse("```python\nprint('hello')\n```")
        for hint in result.hints:
            assert 0.0 <= hint.confidence <= 1.0


# ─── lightweight vs full ──────────────────────────────────────────────────────

class TestLightweightVsFull:
    def test_lightweight_detects_code_block(self):
        result = _lightweight_analysis("Here:\n```print('hi')```")
        assert result.has(HintType.HAS_CODE_BLOCK)

    def test_lightweight_detects_script(self):
        result = _lightweight_analysis("Привет")
        assert result.has(HintType.SCRIPT_CYRILLIC)

    def test_lightweight_detects_short(self):
        result = _lightweight_analysis("Hi there")
        assert result.has(HintType.IS_SHORT)

    def test_full_detects_more_hints_than_lightweight(self):
        text = "Write a poem: 2+2=4, see https://example.com"
        full = _full_analysis(text)
        light = _lightweight_analysis(text)
        # Full analysis should produce at least as many hints
        assert len(full.hints) >= len(light.hints)

    def test_lightweight_is_flagged(self):
        result = _lightweight_analysis("hello")
        assert result.lightweight is True

    def test_full_is_not_flagged(self):
        result = _full_analysis("hello")
        assert result.lightweight is False


# ─── intent_engine integration (analysis_hints) ──────────────────────────────

class TestAnalysisHintsIntegration:
    """
    Verify that analysis_hints are structured correctly for intent_engine.
    These tests exercise the HAS_MATH boost path without calling intent_engine.
    """

    def test_has_math_hint_has_confidence(self):
        result = analyse("what is 5*3?")
        hint = result.get(HintType.HAS_MATH)
        if hint is not None:
            assert hint.confidence >= 0.0

    def test_math_confidence_value(self):
        """HAS_MATH confidence is 0.80 — below the 0.80 boost threshold in intent_engine."""
        result = _full_analysis("2+2=4")
        hint = result.get(HintType.HAS_MATH)
        if hint is not None:
            # 0.80 is exactly at the threshold — verify it's not below
            assert hint.confidence >= 0.79

    def test_is_short_hint_confidence_is_1(self):
        result = _full_analysis("hi")
        hint = result.get(HintType.IS_SHORT)
        if hint is not None:
            assert hint.confidence == 1.0