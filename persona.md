# CEYONA — PERSONA DESIGN
Version: 1.0
Status: Pre-implementation planning document

This document defines:
- the character goal and what "personality" means in this system
- what each model can and cannot hold tonally
- where persona lives in code and what to test before writing it
- what is already architecturally handled vs what needs prompt work

This document MUST NOT define: routing, model selection, EPK policy, execution DAG.
Those live in architecture.md and models.md.

---

## 1. WHAT PERSONA MEANS HERE

Persona is not a name or a backstory. It is a consistent **tone and response style**
that the user experiences across different intents, tiers, and languages.

A well-designed persona has three properties:
- **Stable** — does not drift between FAST and GENERAL tier responses
- **Tier-transparent** — user cannot tell which model answered
- **Intent-agnostic** — same warmth in a weather reply as in a factual question

Persona is NOT responsible for:
- factual accuracy (TruthMode + retrieval handles this)
- language correctness (multilingual_preprocessor + output_normalizer handles this)
- response length (FORMAT_RULES + synthesizer pipeline handles this)

---

## 2. WHAT IS ALREADY HANDLED BY ARCHITECTURE

Before writing any persona prompt, understand what the system already does:

| Problem | Already solved by |
|---|---|
| Preamble openers ("Конечно!", "Sure!") | `correction.py` — strips them at synthesizer step 5 |
| Markdown/headers in output | `FORMAT_RULES` in `prompt_policy.py` |
| English terms leaking into RU/DE/etc | `output_normalizer.py` leak maps |
| Vision meta openers ("I see that...") | `output_normalizer.py` — strips at synthesizer step 6 |
| Repetitive sentence openings | `VARIATION_RULE` in `prompt_policy.py` |
| Carrying over irrelevant history | `NO_CARRYOVER_RULE` in `prompt_policy.py` |
| Hallucinated facts | `VERIFIED_FACTS_RULE` + `TruthMode.STRICT` |

**Persona prompt should not try to solve any of the above.**
Adding tone instructions that duplicate existing rules creates contradictions
and wastes context window on every request.

---

## 3. MODEL CAPABILITIES — WHAT TO TEST BEFORE WRITING PERSONA

Each tier uses a different model. The same persona text produces different
results on different models. Test each one in isolation before writing
tier-specific variations.

### 3.1 FAST tier — `llama-3.1-8b-instant`

**Known characteristics:**
- Very low latency (840 TPS), short context window effective range
- Tends toward flat, terse responses — minimal spontaneous warmth
- Holds simple tone instructions reliably; complex persona prompts degrade quickly
- Poor at maintaining multi-sentence stylistic consistency

**What to test:**
- Can it hold a warm but brief tone on 1-sentence factual replies?
- Does persona text survive when system prompt is long (history + rules + persona)?
- Does it start hallucinating warmth markers ("Отличный вопрос!") under persona pressure?

**Expected approach:** minimal persona text — 1-2 sentences max.
FAST tier answers quick questions; warmth comes from brevity and directness,
not from stylistic elaboration.

---

### 3.2 GENERAL tier — `llama-3.3-70b-versatile` (primary)

**Known characteristics:**
- Much more expressive than 8b — spontaneously varies sentence structure
- Can hold multi-property tone (warm + concise + direct) simultaneously
- Risk: over-elaborates under persona pressure — adds unnecessary empathy markers
- Risk: in non-English responses, persona bleeds English phrasing patterns

**What to test:**
- Does warmth stay proportional to the question, or does it inflate?
- Does tone stay consistent when the response is 3 sentences vs 10 sentences?
- Does it avoid sounding like a customer service script?
- Non-English: does it echo English persona terms mid-sentence?

**Expected approach:** fuller persona text is viable here. Can include
tone adjectives, rhythm notes, and what to avoid. Still keep it under
5-6 sentences — anything longer competes with rules for context budget.

---

### 3.3 HEAVY tier — `openai/gpt-oss-120b` (primary)

**Known characteristics:**
- Best reasoning and coherence, but used only for HEAVY_REQUIRED requests
- Long, complex inputs — persona must survive alongside large retrieved context
- Tends toward formal/neutral by default without persona instruction
- Risk: on very long outputs, tone shifts mid-response as model "forgets" persona

**What to test:**
- Does persona hold through a 600-token response?
- Does it avoid academic/corporate register on casual questions that happen to be complex?
- Does warmth survive when input context is 4000+ tokens?

**Expected approach:** same persona text as GENERAL, but test specifically
that it doesn't collapse on long outputs.

---

### 3.4 compound (`groq/compound` / `groq/compound-mini`) — synthesizer role

**Note:** compound is used as a synthesizer, not an autonomous agent (architecture.md §40).
It receives fully assembled context and produces the response.

**Known characteristics:**
- Optimized for tool-use synthesis — tends toward structured, list-heavy output
- Less natural in conversational tone than llama-3.3-70b
- `output_normalizer.py` and `correction.py` clean its output post-synthesis

**What to test:**
- Does it avoid bullet-list responses when FORMAT_RULES prohibit them?
- Can persona text counteract its structural bias toward enumeration?
- Does it maintain persona in search/weather/maps results (most common compound use case)?

**Expected approach:** persona here competes with tool result formatting.
Keep persona minimal and focus FORMAT_RULES on suppressing list structure.

---

## 4. WHAT "SCATTERING ACROSS MODELS" DOES AND DOESN'T FIX

The system already uses multiple models in sequence — this is structural, not persona design.

**What the chain already fixes:**
- `analysis.py` → pre-reasoning hints reduce intent misclassification
- `correction.py` → removes opener artifacts regardless of which model produced them
- `output_normalizer.py` → removes language leaks regardless of which model produced them
- `history_filter.py` → reduces context contamination before any model sees it
- `safety_agent` → post-reasoning semantic validation

**What the chain does NOT fix:**
- A factual hallucination produced by one model is accepted as context by the next.
  Models do not correct each other's facts — they inherit them.
  Factual accuracy requires retrieval and TruthMode, not more models.
- Tone inconsistency between tiers. If FAST tier sounds cold and GENERAL sounds warm,
  the user experiences an inconsistent bot — not a blended one.
  Fix: tune each tier's persona separately so they converge on the same feel.

**Conclusion:** persona must be designed per-tier, tested per-tier, and written once
into `prompt_policy.py` as a PERSONA_RULE constant. The chain handles artifacts.
The chain does not handle character.

---

## 5. WHERE PERSONA LIVES IN CODE

```
llm/prompt_policy.py         → PERSONA_RULE constant (to be written)
llm/prompt_engine.py         → build_system_prompt(persona=PERSONA_RULE, rules=[...])
                                slot already exists, currently empty string
```

`build_system_prompt()` accepts `persona` as the first argument — it is prepended
before rules, so the model sees character before constraints. This is intentional:
rules that follow a persona frame are better obeyed than rules alone.

**Tier-specific variations (if needed after testing):**
```python
# prompt_policy.py
PERSONA_RULE_FAST    = "..."   # minimal — 1-2 sentences
PERSONA_RULE_GENERAL = "..."   # fuller — up to 5-6 sentences
PERSONA_RULE_HEAVY   = "..."   # same as GENERAL unless testing shows drift
```

If all tiers hold the same persona text reliably → single `PERSONA_RULE` constant.
Only split into tier variants if testing shows meaningful difference.

---

## 6. TESTING PROTOCOL (before committing persona to code)

For each model / tier:

1. **Baseline** — send 10 varied messages with NO persona text. Note default tone.
2. **Persona candidate** — add PERSONA_RULE to system prompt. Same 10 messages.
3. **Stress** — long context (4000+ token history), voice input (transcript), non-Latin language.
4. **Edge cases** — very short replies (1 sentence), error/fallback responses, DEGRADED_MODE.

Pass criteria:
- Tone consistent across all 10 test cases
- No hallucinated warmth markers ("Отличный вопрос!", "Great question!")
- No persona text leaking into output ("As a helpful assistant, I...")
- Non-English responses: no English persona terms mid-sentence
- Short replies: persona doesn't inflate them

Only after all tiers pass → write PERSONA_RULE into `prompt_policy.py`.

---

## 7. OPEN QUESTIONS (decide before writing persona text)

- [ ] Does Ceyona have a name it uses? Or is it nameless in responses?
- [ ] Formality level per language — Russian "ты" or "вы"? Arabic formal or colloquial?
- [ ] Should tone change by intent? (warmer on EMOTIONAL, more direct on SEARCH)
      or flat consistent tone across all intents?
- [ ] Voice responses (TTS) — should persona be slightly different for spoken output?
      (shorter sentences, no parenthetical asides — they sound odd when read aloud)
- [ ] What is the one thing Ceyona should never sound like?
      (pick one: corporate helpdesk / cheerful chatbot / academic / cold assistant)
