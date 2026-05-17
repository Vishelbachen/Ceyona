馃 馃 SINGLE SOURCE OF TRUTH (FINAL v6.3 鈥� META LAYER SEALED)

鈿欙笍 5. LLM LAYER (GROQ + HF 鈥� ROLE-ISOLATED FABRIC v6.3)

馃洝 SAFETY LAYER (deterministic cascade 鈥� FIRST GATE)

meta-llama/llama-prompt-guard-2-22m    鈫� FAST REJECTION FILTER (first pass)
meta-llama/llama-prompt-guard-2-86m    鈫� DEEP CLASSIFICATION FILTER (second pass)
openai/gpt-oss-safeguard-20b 鈫� FINAL ENFORCEMENT MODEL (hard gate)

鉁� ROLE:
  constraint evaluation only
  NO generation role
  NO reasoning synthesis role
  22m EXECUTES BEFORE FEATURE EXTRACTION
  86m + safeguard-20b EXECUTE AFTER FEATURE EXTRACTION

鉁� UNAVAILABILITY RULE:
  Safety models unavailable 鈫� DENY by default
  NO fallback to ALLOW 鉂�
  NO partial execution 鉂�

鉁� CRITICAL DISTINCTION:
  Safety Layer 鈫� firewall 薪邪 胁褏芯写械
                 写械褌械褉屑懈薪懈褉芯胁邪薪薪褘泄
                 斜谢芯泻懈褉褍械褌 芯褔械胁懈写薪芯 胁褉械写薪褘泄 input
  safety_agent 鈫� 褋械屑邪薪褌懈褔械褋泻懈泄 胁邪谢懈写邪褌芯褉
                 锌芯褋谢械 reasoning
                 谢芯胁懈褌 unsafe emergent content
  袧袝 写褍斜谢懈褉芯胁邪薪懈械 鉁�

鉁� MODEL NOTES:
  meta-llama/llama-prompt-guard-2-22m / 86m 鈫� 褋锌械褑懈邪谢懈蟹懈褉芯胁邪薪褘 Meta
                              写谢褟 写械褌械泻褑懈懈 胁褉械写芯薪芯褋薪褘褏 锌褉芯屑锌褌芯胁
                              褉芯谢褜 褋芯胁锌邪写邪械褌 褋 薪邪蟹薪邪褔械薪懈械屑 褌芯褔薪芯
  openai/gpt-oss-safeguard-20b    鈫� safeguard 屑芯写械谢褜
                              褉芯谢褜 褋芯胁锌邪写邪械褌 褋 薪邪蟹薪邪褔械薪懈械屑 褌芯褔薪芯

馃煝 FAST TIER (inference 鈥� ALLOW / DEGRADED only)

llama-3.1-8b-instant 鈫� STRUCTURAL SIGNAL COMPRESSION / SHALLOW INFERENCE
allam-2-7b           鈫� MULTILINGUAL NLP NORMALIZATION (Arabic anchor)

鉁� ROLE:
  primary inference 锌褉懈 ALLOW / DEGRADED
  pre-EPK signal shaping
  low-cost transformation
  multilingual input normalization
  NO reasoning authority
  NO intent generation authority
  SKIP 锌褉懈 HEAVY_REQUIRED 鉂�
  SKIP 锌褉懈 DENY 鉂�

鉁� MODEL NOTES:
  llama-3.1-8b-instant 鈫� 褋邪屑邪褟 谢褢谐泻邪褟 懈 斜褘褋褌褉邪褟 屑芯写械谢褜 胁 褋锌懈褋泻械
                          褉芯谢褜 褋芯芯褌胁械褌褋褌胁褍械褌 褌芯褔薪芯
                          锌褉懈 HEAVY_REQUIRED 鈫�
                          懈褋锌芯谢褜蟹褍械褌褋褟 孝袨袥鞋袣袨 胁 heavy_input_shaper.py
                          袧袝 泻邪泻 Fast Tier 鉂�

  allam-2-7b           鈫� 褋芯蟹写邪薪邪 Saudi Aramco
                          褋锌械褑懈邪谢懈蟹邪褑懈褟: 邪褉邪斜褋泻懈泄 褟蟹褘泻
                          芯写薪邪 屑芯写械谢褜, 芯写懈薪 胁褘蟹芯胁 薪邪 胁褏芯写械 pipeline
                          懈褋锌芯谢褜蟹褍械褌褋褟 胁 褌褉褢褏 泻芯薪褌械泻褋褌邪褏:
                            Fast Tier 鈫� preprocessing
                            Specialized Layer 鈫� TTS pipeline
                            Multilingual Normalization 鈫� Arabic routing
                          袧袝 褌褉懈 芯褌写械谢褜薪褘褏 懈薪褋褌邪薪褋邪 鉁�
                          袧袝 芯锌褌懈屑懈蟹懈褉芯胁邪薪邪 写谢褟 写褉褍谐懈褏 褟蟹褘泻芯胁 鈿狅笍
                          芯褋褌邪谢褜薪褘械 褟蟹褘泻懈 鈫� llama-3.3-70b-versatile

馃數 GENERAL TIER (primary reasoning fabric)

llama-3.3-70b-versatile 鈫� PRIMARY REASONING CORE + CREATIVE ENGINE
qwen/qwen3-32b          鈫� STRUCTURED LOGIC / FORMATTING ENGINE
openai/gpt-oss-20b      鈫� CONSTRAINT-AWARE GENERAL INFERENCE

鉁� ROLE:
  unified reasoning space
  multi-model reasoning diversity
  creative synthesis (70b)
  structured output formatting (qwen)
  NO control authority
  NO policy influence
  SKIP 锌褉懈 HEAVY_REQUIRED 鉂�
  SKIP 锌褉懈 DEGRADED_MODE 鉂�
  SKIP 锌褉懈 DENY 鉂�

鉁� NOTE:
  FAST / GENERAL / HEAVY = 褌懈褉褘 屑芯褖薪芯褋褌懈 屑芯写械谢械泄
  褔邪褋褌褜 LLM Layer + EPK cost model
  袧袝 褋谢芯懈 谢芯谐懈泻懈 鉂�
  袧袝 泻芯谐薪懈褌懈胁薪褘械 褋谢芯懈 鉂�

鉁� MODEL NOTES:
  llama-3.3-70b-versatile 鈫� 谢褍褔褕邪褟 芯斜褖邪褟 屑芯写械谢褜 胁 褋锌懈褋泻械
                             褉芯谢褜 褋芯芯褌胁械褌褋褌胁褍械褌 褌芯褔薪芯
                             fallback 写谢褟 薪械-邪褉邪斜褋泻懈褏 褟蟹褘泻芯胁 鉁�

  qwen/qwen3-32b          鈫� reasoning 屑芯写械谢褜 褋 thinking mode
                             懈褋锌芯谢褜蟹褍械褌褋褟 写谢褟 褎芯褉屑邪褌懈褉芯胁邪薪懈褟
                             thinking mode 袛袨袥袞袝袧 斜褘褌褜 芯褌泻谢褞褔褢薪 褟胁薪芯:
                             "thinking": False 鈿狅笍

  openai/gpt-oss-20b      鈫� OpenAI open-source 屑芯写械谢褜 薪邪 Groq
                             褋锌械褑懈邪谢懈蟹邪褑懈褟 锌褍斜谢懈褔薪芯 薪械 蟹邪写芯泻褍屑械薪褌懈褉芯胁邪薪邪
                             褉芯谢褜 锌芯写芯斜褉邪薪邪 锌芯 褉邪蟹屑械褉褍 (褋褉械写薪懈泄 褋谢芯泄)
                             褉懈褋泻 薪懈蟹泻懈泄, 芯褋芯蟹薪邪薪薪褘泄 胁褘斜芯褉 鈿狅笍

馃敶 HEAVY TIER (capability decomposition 鈥� FINAL FORM)

openai/gpt-oss-120b            鈫� DEEP MULTI-STEP REASONING ENGINE
                                  PRIMARY: Heavy Tier reasoning
                                  SECONDARY: Consensus arbiter
                                  (褌芯谢褜泻芯 械褋谢懈 Heavy Tier 薪械 邪泻褌懈胁械薪)
                                  mutex: 薪懈泻芯谐写邪 薪械 邪泻褌懈胁械薪 胁 芯斜械懈褏 褉芯谢褟褏 鉂�
meta-llama/llama-4-scout-17b-16e-instruct 鈫� LONG-CONTEXT TRANSFORMATION ENGINE

鉁� ACTIVATION RULE:
  邪泻褌懈胁懈褉褍械褌褋褟 孝袨袥鞋袣袨 锌芯 褋懈谐薪邪谢褍 EPK = HEAVY_REQUIRED
  Orchestrator 懈褋锌芯谢薪褟械褌 褋懈谐薪邪谢, 薪械 谐械薪械褉懈褉褍械褌 械谐芯
  NO self-activation 鉂�
  NO agent-triggered activation 鉂�
  NO orchestrator-initiated activation 鉂�

鉁� OUTPUT RULE:
  Heavy Tier output 鈫� 薪邪锌褉褟屑褍褞 胁 Response Synthesizer
  Consensus SKIP (mutex)
  Response Synthesizer 邪谐褉械谐懈褉褍械褌 Heavy Tier output 鉁�

鉁� HARD INVARIANTS:
  each subsystem = isolated capability domain
  NO shared state
  NO hierarchical dominance
  NO cross-decision influence

鉁� MODEL NOTES:
  openai/gpt-oss-120b            鈫� 褋邪屑邪褟 褌褟卸褢谢邪褟 屑芯写械谢褜 胁 褋锌懈褋泻械
                                    褉芯谢褜 褋芯芯褌胁械褌褋褌胁褍械褌 褌芯褔薪芯
  meta-llama/llama-4-scout-17b-16e-instruct 鈫� 512K 泻芯薪褌械泻褋褌
                                    褋芯蟹写邪薪邪 懈屑械薪薪芯 写谢褟 long-context
                                    褉芯谢褜 褋芯芯褌胁械褌褋褌胁褍械褌 褌芯褔薪芯

馃洜 HEAVY INPUT SHAPER (self-gated utility 鈥� 薪械 褌懈褉)

llm/heavy_input_shaper.py

鉁� ROLE:
  锌芯写谐芯褌芯胁泻邪 胁褏芯写邪 写谢褟 Heavy Tier
  self-gated utility 鈥� 袧袝 褌懈褉 鉂�
  袧袝 邪谐械薪褌 鉂�
  袧袝 inference 褋谢芯泄 鉂�

鉁� ACTIVATION:
  ONLY when EPK = HEAVY_REQUIRED 鉁�
  SKIP on ALLOW 鉂�
  SKIP on DEGRADED_MODE 鉂�
  SKIP on DENY 鉂�

鉁� EXECUTION MODEL:
  ALWAYS CALLED on HEAVY_REQUIRED
  internal gating:
    if shaping needed 鈫� 胁褘锌芯谢薪褟械褌 芯锌械褉邪褑懈褞
    if shaping not needed 鈫� NO-OP (return input as-is)

鉁� DECISION FACTORS (internal):
  context_size
  retrieval structure
  token limits
  format complexity

鉁� OPERATIONS (褉械邪谢懈蟹邪褑懈褟 屑芯卸械褌 屑械薪褟褌褜褋褟):
  compression / chunking / summarization
  deduplication / ranking
  鈫� 薪邪蟹胁邪薪懈械 芯褌褉邪卸邪械褌 袪袨袥鞋, 薪械 褉械邪谢懈蟹邪褑懈褞 鉁�

鉁� CONSTRAINTS:
  NO reasoning 鉂�
  NO final output generation 鉂�
  uses llama-3.1-8b-instant (NOT as Fast Tier) 鉁�

馃 AGENT LAYER (tool-use execution fabric)

groq/compound      鈫� DEEP AGENT
groq/compound-mini 鈫� FAST AGENT

鉁� ROLE:
  compound      鈫� deep_agent.py
  compound-mini 鈫� fast_agent.py
  tool selection authority 鉁�
  multi-step execution 鉁�
  NO policy selection authority 鉂�
  NO system governance 鉂�
  NO Heavy Tier activation 鉂�

鈿栵笍 CONSENSUS LAYER

openai/gpt-oss-120b 鈫� CONSENSUS ARBITER
                      ACTIVE: 褌芯谢褜泻芯 械褋谢懈 Heavy Tier 薪械 邪泻褌懈胁械薪
                      SKIP 锌褉懈 HEAVY_REQUIRED (mutex) 鉁�
                      锌褉懈 HEAVY_REQUIRED 鈫�
                      Response Synthesizer 邪谐褉械谐懈褉褍械褌 薪邪锌褉褟屑褍褞 鉁�

馃帳 SPECIALIZED LAYER

whisper-large-v3       鈫� PRIMARY SPEECH-TO-TEXT
whisper-large-v3-turbo 鈫� FAST SPEECH-TO-TEXT
canopylabs/orpheus-v1-english     鈫� ENGLISH SPEECH SYNTHESIS
canopylabs/orpheus-arabic-saudi   鈫� ARABIC SPEECH SYNTHESIS
allam-2-7b             鈫� MULTILINGUAL NLP (Arabic anchor)

鉁� ACTIVATION RULE (orpheus):
  is_voice_input = true 鈫� 邪泻褌懈胁懈褉褍械褌褋褟 鉁�
  NO arbitrary activation 鉂�

馃 6. HF EMBEDDINGS + RETRIEVAL INTELLIGENCE LAYER (v6.3)

BAAI/bge-large-en-v1.5 鈫� PRIMARY EMBEDDING SPACE
BAAI/bge-small-en-v1.5 鈫� FAST EMBEDDING FALLBACK
BAAI/bge-reranker-large 鈫� CROSS-ENCODER RERANKING

馃毇 STRICT SEPARATION:
  bge-large / bge-small 鈫� ONLY generate vectors
  bge-reranker-large    鈫� ONLY reorders candidates
                          NEVER generates embeddings
                          NEVER influences EPK / agents / cognition

馃 7. FEATURE LAYER (v6.3)

features = {
    "token_count": int,
    "char_count": int,
    "newline_density": float,
    "has_code_block": bool,
    "has_json_shape": bool,
    "has_math_symbols": bool,
    "unicode_entropy": float,
    "is_voice_input": bool
}

鉁� 袩袨小袥袝 Safety Gate Pass 1 (22m)
鉁� 袛袨 Safety Gate Pass 2 (86m + safeguard)
鉁� 袛袨 Intent Engine
鉁� 袛袨 谢褞斜芯谐芯 LLM 褋谢芯褟

馃搹 8. COMPLEXITY MODEL (v6.3)

LOW      鈫� chat / short text
MEDIUM   鈫� structured input
HIGH     鈫� logs / code / structured blocks
CRITICAL 鈫� mixed modality / context_length > 32K tokens
           鈫� EPK OUTPUT: HEAVY_REQUIRED

鈿欙笍 9. EPK (v6.3 鈥� SOLE POLICY ENGINE)

EPK = deterministic policy function over structural state + cost constraints

OUTPUT:
  ALLOW          鈫� normal execution path
                   锌芯谢薪褘泄 DAG 鉁�

  DENY           鈫� 薪械屑械写谢械薪薪褘泄 胁褘褏芯写
                   NO downstream activation 鉂�

  DEGRADED_MODE  鈫� reduced execution path:
                   Memory Retrieval 鉁�
                   Embedding Retrieval 鉁�
                   Reranker 鉁�
                   analysis.py (lightweight) 鉁�
                   Intent Engine 鉁�
                   Fast Tier (8b-instant) 鉁�
                   skip Reasoning Engine 鉂�
                   skip Multi-Agent Coordinator 鉂�
                   skip General Tier 鉂�
                   skip Agent Layer 鉂�
                   skip safety_agent 鉂�
                   skip heavy_input_shaper 鉂�
                   skip Heavy Tier 鉂�
                   skip Consensus 鉂�
                   Response Synthesizer 薪邪锌褉褟屑褍褞 鉁�
                   META lightweight active 鉁�

  HEAVY_REQUIRED 鈫� Heavy path:
                   [SKIP FAST TIER] 鉂�
                   [SKIP GENERAL TIER] 鉂�
                   analysis.py (full) 鉁�
                   Reasoning Engine ACTIVE 鉁�
                   heavy_input_shaper ALWAYS CALLED (self-gated) 鉁�
                   Heavy Tier mandatory 鉁�
                   safety_agent mandatory 鉁�
                   Consensus SKIP (mutex) 鉂�
                   Response Synthesizer 邪谐褉械谐懈褉褍械褌 薪邪锌褉褟屑褍褞 鉁�
                   META full active 鉁�

鉁� SOLE POLICY AUTHORITY
馃毇 NO ACCESS: memory / embeddings / LLM / agents / logs / metrics

馃З 10. COGNITION LAYER (v6.3 鈥� ROLES SEALED)

intent_engine.py
鉁� ROLE: stateless prompt construction / request shaping
  NO policy decision 鉂�
  NO routing control 鉂�

reasoning_engine.py
鉁� ROLE: 泻芯谐薪懈褌懈胁薪邪褟 谢芯谐懈泻邪 褋懈褋褌械屑褘
  褋褌褉芯懈褌 reasoning_plan
  写械泻芯屑锌芯蟹懈褉褍械褌 蟹邪写邪褔褍
  锌械褉械写邪褢褌 plan 鈫� multi_agent_coordinator

鉁� ACTIVATION:
  ACTIVE on ALLOW 鉁�
  ACTIVE on HEAVY_REQUIRED 鉁�
  skip on DENY 鉂�
  skip on DEGRADED_MODE 鉂�

鉁� PRINCIPLE:
  reasoning_engine = control-plane (邪褉褏懈褌械泻褌芯褉)
  Heavy Tier       = data-plane (懈褋锌芯谢薪懈褌械谢褜)
  褉邪蟹写械谢械薪懈械 芯斜褟蟹邪褌械谢褜薪芯 鉁�

鉁� HARD RULES:
  NO model routing 鉂�
  NO agent execution 鉂�
  NO policy authority 鉂�

multi_agent_coordinator.py
鉁� ROLE: 锌谢邪薪懈褉芯胁褖懈泻 胁蟹邪懈屑芯写械泄褋褌胁懈褟 邪谐械薪褌芯胁
  胁褘蟹褘胁邪械褌褋褟 孝袨袥鞋袣袨 orchestrator'芯屑 鉁�
  锌褉懈薪懈屑邪械褌 reasoning_plan
  褋褌褉芯懈褌 agent_execution_plan
  芯锌褉械写械谢褟械褌 锌芯褉褟写芯泻 / 蟹邪胁懈褋懈屑芯褋褌懈
  胁芯蟹胁褉邪褖邪械褌 plan 孝袨袥鞋袣袨 orchestrator'褍 鉁�
  skip on DENY / DEGRADED_MODE 鉂�

鉁� HARD RULES:
  NO 锌褉褟屑芯泄 胁褘蟹芯胁 邪谐械薪褌芯胁 鉂�
  NO 褍锌褉邪胁谢械薪懈械 pipeline 鉂�
  NO 胁褘斜芯褉 屑芯写械谢懈 鉂�
  NO 褎懈薪邪谢褜薪褘械 褉械褕械薪懈褟 鉂�

response_synthesizer.py
鉁� ROLE: FINAL OUTPUT AUTHORITY

鉁� INTERNAL PIPELINE:
  1. assemble_response
  2. structure_output
  3. apply_formatting
  4. apply_correction  鈫� 胁褘蟹褘胁邪械褌 meta/correction.py
  5. finalize_output

鉁� AGGREGATION:
  邪谐褉械谐懈褉褍械褌 Heavy Tier output 锌褉懈 HEAVY_REQUIRED 鉁�

鉁� INVARIANTS:
  correction 袧袝 懈屑械械褌 authority 鉂�
  correction CANNOT override synthesizer intent 鉂�
  location: meta/ | authority: synthesizer 鉁�
  NO policy control 鉂�
  NO agent selection 鉂�
  NO routing decision 鉂�

馃 11. META LAYER (v6.3 鈥� FULLY SEALED)

meta/
鈹溾攢鈹€ analysis.py      鈫� PRE-REASONING (褕邪谐 DAG 写芯 intent_engine)
鈹溾攢鈹€ reflection.py    鈫� POST-EXECUTION (side-channel)
鈹溾攢鈹€ correction.py    鈫� INLINE (owned by meta, called by synthesizer)
鈹斺攢鈹€ memory_audit.py  鈫� OFFLINE DIAGNOSTICS (side-channel)

鉁� 袣袥挟效袝袙袨袡 袠袧袙袗袪袠袗袧孝:
  META LAYER:
    observes system 鉁�
    NEVER controls system 鉂�
    NEVER participates in execution decisions 鉂�

鉁� CRITICAL DISTINCTIONS:
  META 鈮� COGNITION
    meta      鈫� 薪邪斜谢褞写邪械褌 懈 芯褑械薪懈胁邪械褌
    cognition 鈫� 写褍屑邪械褌 懈 锌褉懈薪懈屑邪械褌 褉械褕械薪懈褟

  META 鈮� OBSERVABILITY
    observability 鈫� 褌械褏薪懈褔械褋泻邪褟 褌械谢械屑械褌褉懈褟
                    懈薪褎褉邪褋褌褉褍泻褌褍褉薪褘泄 褍褉芯胁械薪褜
                    system alive? latency? errors?
    meta          鈫� 褋械屑邪薪褌懈褔械褋泻芯械 泻邪褔械褋褌胁芯
                    application 褍褉芯胁械薪褜
                    芯褌胁械褌 谢芯谐懈褔薪褘泄? 锌芯谢薪褘泄? 锌褉芯褌懈胁芯褉械褔懈胁褘泄?

鉁� SIMPLE MODEL:
  memory     鈫� "褔褌芯 屑褘 蟹薪邪械屑"
  cognition  鈫� "泻邪泻 屑褘 写褍屑邪械屑"
  meta       鈫� "薪邪褋泻芯谢褜泻芯 褝褌芯 胁褋褢 薪芯褉屑邪谢褜薪芯 褉邪斜芯褌邪械褌"
  observability 鈫� "卸懈胁褢褌 谢懈 褋懈褋褌械屑邪"

鈹€鈹€ analysis.py 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

鉁� POSITION: PRE-REASONING
  褕邪谐 胁 DAG 写芯 intent_engine
  袧袝 胁褘蟹褘胁邪械褌褋褟 Orchestrator'芯屑 褟胁薪芯 鉂�
  邪胁褌芯屑邪褌懈褔械褋泻懈泄 褕邪谐 pipeline 鉁�

鉁� ACTIVATION:
  ACTIVE on ALLOW (full) 鉁�
  ACTIVE on HEAVY_REQUIRED (full) 鉁�
  ACTIVE on DEGRADED_MODE (lightweight) 鉁�
  SKIP on DENY 鉂�

鉁� OUTPUT: hints (non-binding)
  hints MAY be ignored 鉁�
  hints have ZERO authority 鉁�
  hints are NOT policy 鉁�

鉁� DOES:
  input decomposition
  pattern detection (non-semantic)
  complexity hints (non-binding)

鉁� DOES NOT:
  NO policy decisions 鉂�
  NO routing 鉂�
  NO reasoning 鉂�
  NO memory interaction 鉂�

鈹€鈹€ reflection.py 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

鉁� POSITION: POST-EXECUTION side-channel
  邪泻褌懈胁懈褉褍械褌褋褟 锌芯褋谢械 OUTPUT
  non-blocking, async 鉁�

鉁� ACTIVATION:
  ACTIVE on ALLOW (full) 鉁�
  ACTIVE on HEAVY_REQUIRED (full) 鉁�
  ACTIVE on DEGRADED_MODE (lightweight) 鉁�
  SKIP on DENY 鉂�

鉁� OUTPUT: reflection_report
  DESTINATION:
    鈫� observability (logs / traces) 鉁�
    鈫� optional: memory_audit input (offline) 鉁�
  NO pipeline feedback 鉂�
  NO response modification 鉂�
  NO execution influence 鉂�
  袧袝 胁谢懈褟械褌 薪邪 褌械泻褍褖懈泄 request 鉂�
  褌芯谢褜泻芯 谢芯谐懈褉芯胁邪薪懈械 懈 芯褎褎谢邪泄薪 邪薪邪谢懈蟹 鉁�

鉁� DOES:
  褋褉邪胁薪械薪懈械 intent 鈫� output
  锌褉芯胁械褉泻邪 锌芯谢薪芯褌褘 / 褋芯谐谢邪褋芯胁邪薪薪芯褋褌懈
  胁褘褟胁谢械薪懈械 谢芯谐懈褔械褋泻懈褏 写褘褉

鉁� DOES NOT:
  NO rewriting reasoning 鉂�
  NO regeneration 鉂�
  NO pipeline control 鉂�

鈹€鈹€ correction.py 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

鉁� OWNERSHIP: meta layer
鉁� EXECUTION: ONLY via response_synthesizer (step 4)
鉁� EXCLUDED FROM: META side-channel DAG 鉂�

鉁� POSITION 胁 synthesizer:
  AFTER assemble / structure / format
  BEFORE finalize_output

鉁� DOES:
  improve readability
  fix minor inconsistencies
  normalize structure

鉁� DOES NOT:
  NO full regeneration 鉂�
  NO reasoning override 鉂�
  NO new information 鉂�
  NO pipeline control 鉂�
  CANNOT override synthesizer intent 鉂�

鉁� INVARIANT:
  location: meta/ 鉁�
  authority: response_synthesizer 鉁�
  袧袝 薪械蟹邪胁懈褋懈屑褘泄 褋谢芯泄 execution 鉂�

鈹€鈹€ memory_audit.py 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

鉁� POSITION: OFFLINE DIAGNOSTICS side-channel
  async, non-blocking 鉁�
  袧袝 褔邪褋褌褜 芯褋薪芯胁薪芯谐芯 DAG 鉂�

鉁� ACTIVATION:
  ACTIVE on ALLOW 鉁�
  ACTIVE on HEAVY_REQUIRED 鉁�
  ACTIVE on DEGRADED_MODE (lightweight) 鉁�
  SKIP on DENY 鉂�

鉁� OUTPUT: audit_report (read-only)
  optional input 写谢褟 reflection.py 鉁�

鉁� DOES:
  detect conflicts / duplicates
  detect inconsistencies / stale entries

鉁� HARD RULES:
  NO memory write 鉂�
  NO memory update 鉂�
  NO conflict resolution 鉂�
  NO retrieval influence 鉂�
  NO execution trigger 鉂�
  袧袝 褔邪褋褌褜 memory pipeline 鉂�

鉁� META LAYER 胁 DEGRADED_MODE:
  STATUS: ENABLED (lightweight mode)
  analysis    鈫� lightweight hints 鉁�
  reflection  鈫� lightweight report 鉁�
  memory_audit 鈫� lightweight diagnostics 鉁�
  correction  鈫� 胁褘蟹褘胁邪械褌褋褟 懈蟹 synthesizer 泻邪泻 芯斜褘褔薪芯 鉁�
  REASON: preserve observability of degraded behavior
  INVARIANT:
    meta NEVER affects EPK decision 鉂�
    meta NEVER increases tier 鉂�

鈹€鈹€ META side-channel DAG 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

META side-channel INCLUDES:
  analysis.py    鈫� pre-reasoning step (胁 芯褋薪芯胁薪芯屑 DAG)
  reflection.py  鈫� post-execution (锌芯褋谢械 OUTPUT)
  memory_audit.py 鈫� offline diagnostics (锌芯褋谢械 OUTPUT)

META side-channel EXCLUDES:
  correction.py 鉂� (owned by meta, executed by synthesizer)

馃 12. AGENT LAYER 鈥� SAFETY AGENT (v6.3)

safety_agent.py
鉁� ROLE: POST-REASONING SEMANTIC SAFETY VALIDATION

鉁� ACTIVATION:
  邪泻褌懈胁械薪 锌褉懈 ALLOW 鉁�
  邪泻褌懈胁械薪 锌褉懈 HEAVY_REQUIRED 鉁�
  skip 锌褉懈 DEGRADED_MODE 鉂�
  skip 锌褉懈 DENY 鉂�

鉁� POSITION: LAST in Agent Layer 鈥� final check before Consensus

鉁� RESPONSIBILITIES:
  胁邪谢懈写邪褑懈褟 reasoning_plan 懈 draft_response
  写械褌械泻褑懈褟 unsafe emergent content
  胁褘写邪褢褌 褋懈谐薪邪谢: allow / revise / block

鉁� NON-RESPONSIBILITIES:
  NO input-level filtering 鉂�
  NO deterministic cascade 鉂�
  NO model routing 鉂�

馃攣 13. FINAL EXECUTION DAG (v6.3)

INPUT
鈫�
Safety Gate 鈥� PASS 1 (22m)
  unavailable 鈫� DENY by default
鈫�
Feature Extraction (胁褋械 褋懈谐薪邪谢褘 + is_voice_input)
鈫�
Safety Gate 鈥� PASS 2 (86m + safeguard-20b)
  unavailable 鈫� DENY by default
鈫�
Auth / Rate Limit
鈫�
Event Log
鈫�
Multilingual Normalization
  allam-2-7b    鈫� 邪褉邪斜褋泻懈泄 [芯写懈薪 胁褘蟹芯胁]
  llama-3.3-70b 鈫� 芯褋褌邪谢褜薪褘械
鈫�
EPK [SOLE POLICY AUTHORITY]
  DENY           鈫� EXIT
  ALLOW          鈫� 锌芯谢薪褘泄 DAG 鈫�
  DEGRADED_MODE  鈫� limited path 鈫�
  HEAVY_REQUIRED 鈫� Heavy path 鈫�
鈫�
Memory Retrieval               [skip on DENY]
鈫�
Embedding Retrieval            [skip on DENY]
(bge-large 鈫� bge-small fallback)
鈫�
Reranker                       [skip on DENY]
鈫�
analysis.py                    [skip on DENY]
  ALLOW / HEAVY 鈫� full 鉁�
  DEGRADED      鈫� lightweight 鉁�
  (hints non-binding 鈫� intent_engine)
鈫�
Intent Engine                  [skip on DENY]
鈫�
Reasoning Engine               [skip on DENY / DEGRADED]
                               [ACTIVE on ALLOW / HEAVY_REQUIRED]
鈫�
Multi-Agent Coordinator        [skip on DENY / DEGRADED]
鈫�
Orchestrator (EPK signal execution only)
  鈹溾攢鈹€ HEAVY_REQUIRED
  鈹�   鈫� [SKIP FAST TIER] 鉂�
  鈹�   鈫� [SKIP GENERAL TIER] 鉂�
  鈹�   鈫� heavy_input_shaper (ALWAYS CALLED, self-gated)
  鈹�       shaping needed 鈫� execute 鉁�
  鈹�       not needed 鈫� NO-OP 鉁�
  鈹�   鈫� Heavy Tier (120b / scout) [mandatory]
  鈹�   鈫� safety_agent [mandatory] 鉁�
  鈹�   鈫� [SKIP CONSENSUS] 鉂� (mutex)
  鈹�   鈫� Response Synthesizer (邪谐褉械谐懈褉褍械褌 薪邪锌褉褟屑褍褞) 鉁�
  鈹溾攢鈹€ ALLOW
  鈹�   鈫� Fast Tier (8b) 鉁�
  鈹�   鈫� General Tier (70b / qwen / gpt-oss-20b) 鉁�
  鈹�   鈫� Agent Layer (compound / compound-mini) 鉁�
  鈹�   鈫� safety_agent (final check) 鉁�
  鈹�   鈫� Consensus (120b) 鉁�
  鈹斺攢鈹€ DEGRADED_MODE
      鈫� Fast Tier only (8b) 鉁�
      鈫� [skip everything else] 鉂�
      鈫� Response Synthesizer 薪邪锌褉褟屑褍褞 鉁�
鈫�
Response Synthesizer 鈫� FINAL OUTPUT AUTHORITY
  1. assemble_response
  2. structure_output
  3. apply_formatting
  4. apply_correction (meta/correction.py)
  5. finalize_output
  邪谐褉械谐懈褉褍械褌 Heavy Tier output 锌褉懈 HEAVY_REQUIRED 鉁�
鈫�
  鈹溾攢鈹€ is_voice_input = true  鈫� Speech Output (orpheus)
  鈹斺攢鈹€ is_voice_input = false 鈫� TEXT OUTPUT
鈫�
Event Store 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹�
                          鈹溾攢鈹€ 袩袗袪袗袥袥袝袥鞋袧袨
Memory Write 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹�
鈫�
[META side-channel 鈥� non-blocking, async]
  reflection.py   鈫� report 鈫� observability / memory_audit
  memory_audit.py 鈫� offline diagnostics
  ALLOW / HEAVY   鈫� full mode 鉁�
  DEGRADED        鈫� lightweight mode 鉁�
  DENY            鈫� SKIP 鉂�
鈫�
OUTPUT

馃毇 14. SIDE-CHANNEL CLOSURE (v6.3 鈥� SEALED)

鈹€鈹€ HARD PROHIBITIONS 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

memory       鈫� control 鉂�
embeddings   鈫� routing 鉂�
reranker     鈫� decision 鉂�
LLM          鈫� governance 鉂�
optimization 鈫� system behavior 鉂�
meta         鈫� execution authority 鉂�
meta         鈫� policy authority 鉂�
meta         鈫� routing authority 鉂�
meta         鈫� EPK influence 鉂�
meta         鈫� tier escalation 鉂�

鈹€鈹€ AUTHORITY BOUNDARIES 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

agents 鈫� policy selection 鉂�
agents 鈫� tool selection 鉁�

intent 鈫� policy decision 鉂�
intent 鈫� prompt construction 鉁�

reasoning_engine 鈫� plan construction 鉁�
reasoning_engine 鈫� ACTIVE on ALLOW / HEAVY_REQUIRED 鉁�
reasoning_engine 鈫� skip on DENY / DEGRADED 鉂�
reasoning_engine 鈫� control-plane 鉁�
reasoning_engine 鈫� agent execution 鉂�
reasoning_engine 鈫� policy authority 鉂�

multi_agent_coordinator 鈫� agent planning 鉁�
multi_agent_coordinator 鈫� called by orchestrator only 鉁�
multi_agent_coordinator 鈫� returns plan to orchestrator only 鉁�
multi_agent_coordinator 鈫� agent execution 鉂�
multi_agent_coordinator 鈫� pipeline control 鉂�
multi_agent_coordinator 鈫� model selection 鉂�

safety_agent 鈫� post-reasoning validation 鉁�
safety_agent 鈫� active on ALLOW / HEAVY_REQUIRED 鉁�
safety_agent 鈫� skip on DEGRADED / DENY 鉂�
safety_agent 鈫� input-level filtering 鉂�
safety_agent 鈫� deterministic cascade 鉂�

heavy_input_shaper 鈫� self-gated utility 鉁�
heavy_input_shaper 鈫� ONLY on HEAVY_REQUIRED 鉁�
heavy_input_shaper 鈫� ALWAYS CALLED on HEAVY_REQUIRED 鉁�
heavy_input_shaper 鈫� internal NO-OP if not needed 鉁�
heavy_input_shaper 鈫� SKIP on ALLOW 鉂�
heavy_input_shaper 鈫� SKIP on DEGRADED 鉂�
heavy_input_shaper 鈫� SKIP on DENY 鉂�
heavy_input_shaper 鈫� reasoning 鉂�
heavy_input_shaper 鈫� final output 鉂�
heavy_input_shaper 鈫� NOT a tier 鉂�
heavy_input_shaper 鈫� NOT an agent 鉂�

analysis    鈫� pre-reasoning DAG step 鉁�
analysis    鈫� hints non-binding / zero authority 鉁�
analysis    鈫� ACTIVE on ALLOW / HEAVY (full) 鉁�
analysis    鈫� ACTIVE on DEGRADED (lightweight) 鉁�
analysis    鈫� SKIP on DENY 鉂�
analysis    鈫� NO policy 鉂�
analysis    鈫� NO routing 鉂�
analysis    鈫� NOT called by Orchestrator 鉂�
analysis    鈫� automatic pipeline step 鉁�

reflection  鈫� post-execution side-channel 鉁�
reflection  鈫� OUTPUT: report 鈫� observability / memory_audit 鉁�
reflection  鈫� ACTIVE on ALLOW / HEAVY (full) 鉁�
reflection  鈫� ACTIVE on DEGRADED (lightweight) 鉁�
reflection  鈫� SKIP on DENY 鉂�
reflection  鈫� NO pipeline feedback 鉂�
reflection  鈫� NO response modification 鉂�
reflection  鈫� NO current request influence 鉂�

correction  鈫� owned by meta/ 鉁�
correction  鈫� executed ONLY by response_synthesizer 鉁�
correction  鈫� EXCLUDED from META side-channel DAG 鉂�
correction  鈫� NO authority 鉂�
correction  鈫� NO independent execution 鉂�
correction  鈫� CANNOT override synthesizer intent 鉂�

memory_audit 鈫� read-only diagnostics 鉁�
memory_audit 鈫� OUTPUT: audit_report 鉁�
memory_audit 鈫� optional input 写谢褟 reflection 鉁�
memory_audit 鈫� ACTIVE on ALLOW / HEAVY / DEGRADED 鉁�
memory_audit 鈫� SKIP on DENY 鉂�
memory_audit 鈫� NO memory write 鉂�
memory_audit 鈫� NO conflict resolution 鉂�
memory_audit 鈫� NO execution trigger 鉂�

optimization 鈫� system behavior 鉂�
optimization 鈫� response quality 鉁�

鈹€鈹€ HEAVY_REQUIRED EXECUTION POLICY 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

HEAVY_REQUIRED:
  analysis.py (full) 鉁�
  [SKIP FAST TIER] 鉂�
  [SKIP GENERAL TIER] 鉂�
  Reasoning Engine: ACTIVE 鉁�
  heavy_input_shaper: ALWAYS CALLED (self-gated) 鉁�
  Heavy Tier (mandatory) 鉁�
  safety_agent (mandatory) 鉁�
  Consensus SKIP (mutex) 鉂�
  Response Synthesizer 邪谐褉械谐懈褉褍械褌 薪邪锌褉褟屑褍褞 鉁�
  META: full active 鉁�

鈹€鈹€ DEGRADED_MODE EXECUTION PATH 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

DEGRADED_MODE 鈫�
  Memory Retrieval 鉁�
  Embedding Retrieval 鉁�
  Reranker 鉁�
  analysis.py (lightweight) 鉁�
  Intent Engine 鉁�
  Fast Tier (8b-instant) 鉁�
  skip Reasoning Engine 鉂�
  skip Multi-Agent Coordinator 鉂�
  skip General Tier 鉂�
  skip Agent Layer 鉂�
  skip safety_agent 鉂�
  skip heavy_input_shaper 鉂�
  skip Heavy Tier 鉂�
  skip Consensus 鉂�
  Response Synthesizer 薪邪锌褉褟屑褍褞 鉁�
  correction.py 胁褘蟹褘胁邪械褌褋褟 胁薪褍褌褉懈 synthesizer 鉁�
  META lightweight active 鉁�
    reflection  鈫� lightweight 鉁�
    memory_audit 鈫� lightweight 鉁�

鈹€鈹€ MULTILINGUAL NORMALIZATION 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

allam-2-7b    鈫� 邪褉邪斜褋泻懈泄 褋械谐屑械薪褌 鉁�
                芯写薪邪 屑芯写械谢褜, 芯写懈薪 胁褘蟹芯胁
                褌褉懈 泻芯薪褌械泻褋褌邪: preprocessing / TTS / routing
                袧袝 褌褉懈 懈薪褋褌邪薪褋邪 鉁�
llama-3.3-70b 鈫� 芯褋褌邪谢褜薪褘械 褟蟹褘泻懈 鉁�
袛袨 EPK, NO policy influence 鉂�

鈹€鈹€ OUTPUT AUTHORITY 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

epk                  鈫� SOLE POLICY AUTHORITY 鉁�
epk                  鈫� HEAVY_REQUIRED signal 鉁�
epk                  鈫� DENY 鈫� immediate exit 鉁�

orchestrator         鈫� execution control 鉁�
orchestrator         鈫� EPK signal execution 鉁�
orchestrator         鈫� agent_execution_plan execution 鉁�
orchestrator         鈫� policy generation 鉂�
orchestrator         鈫� routing decisions 鉂�
orchestrator         鈫� Heavy Tier self-activation 鉂�

response_synthesizer 鈫� FINAL OUTPUT AUTHORITY 鉁�
response_synthesizer 鈫� 邪谐褉械谐懈褉褍械褌 Heavy Tier 锌褉懈 HEAVY_REQUIRED 鉁�
response_synthesizer 鈫� 胁褘蟹褘胁邪械褌 correction.py (step 4) 鉁�
response_synthesizer 鈫� policy control 鉂�
response_synthesizer 鈫� agent selection 鉂�

correction           鈫� NO authority 鉂�
correction           鈫� NO independent execution 鉂�
correction           鈫� ONLY via synthesizer 鉁�

鈹€鈹€ ACTIVATION RULES 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

Heavy Tier       鈫� EPK = HEAVY_REQUIRED only
                   output 鈫� Response Synthesizer 薪邪锌褉褟屑褍褞
                   NO self-activation 鉂�

heavy_input_shaper 鈫� ONLY on HEAVY_REQUIRED
                     ALWAYS CALLED, self-gated
                     NO-OP if not needed
                     SKIP on ALLOW / DEGRADED / DENY

gpt-oss-120b     鈫� PRIMARY: Heavy Tier reasoning
                   SECONDARY: Consensus (mutex)
                   薪懈泻芯谐写邪 薪械 邪泻褌懈胁械薪 胁 芯斜械懈褏 褉芯谢褟褏 鉂�

reasoning_engine 鈫� ACTIVE on ALLOW / HEAVY_REQUIRED
                   skip on DENY / DEGRADED

safety_agent     鈫� ACTIVE on ALLOW / HEAVY_REQUIRED
                   skip on DEGRADED / DENY

analysis.py      鈫� ACTIVE on ALLOW / HEAVY (full)
                   ACTIVE on DEGRADED (lightweight)
                   SKIP on DENY

reflection.py    鈫� ACTIVE on ALLOW / HEAVY (full)
                   ACTIVE on DEGRADED (lightweight)
                   SKIP on DENY

memory_audit.py  鈫� ACTIVE on ALLOW / HEAVY / DEGRADED
                   SKIP on DENY

correction.py    鈫� called by synthesizer always
                   (synthesizer 褋邪屑 褉械褕邪械褌 泻芯谐写邪 薪褍卸薪邪 泻芯褉褉械泻褑懈褟)

Speech Output    鈫� is_voice_input = true only

Safety models    鈫� unavailable 鈫� DENY by default

qwen/qwen3-32b   鈫� thinking: False enforced

鈹€鈹€ WRITE ISOLATION 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

Event Store + Memory Write 鈫� 锌邪褉邪谢谢械谢褜薪芯械 胁褘锌芯谢薪械薪懈械
                             薪械蟹邪胁懈褋懈屑褘械 failure domains
                             褋斜芯泄 芯写薪芯谐芯 袧袝 斜谢芯泻懈褉褍械褌 写褉褍谐芯泄

鈹€鈹€ LLM TIER CLARIFICATION 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

FAST / GENERAL / HEAVY = 褌懈褉褘 屑芯褖薪芯褋褌懈
heavy_input_shaper     = self-gated utility, 袧袝 褌懈褉 鉂�
Cognition Layer        = intent / reasoning / coordinator / synthesizer
Meta Layer             = observation / diagnostics / refinement
Observability          = infrastructure telemetry

鈹€鈹€ CROSS-LAYER ISOLATION 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

Safety Layer         鈫� read-only gate 鉁�
safety_agent         鈫� post-reasoning validation only 鉁�
EPK                  鈫� sole policy engine 鉁�
Orchestrator         鈫� execution only 鉁�
Memory               鈫� observational storage only 鉁�
Reranker             鈫� ordering only 鉁�
Consensus            鈫� arbitration only 鉁�
Response Synthesizer 鈫� assembly + aggregation + correction 鉁�
heavy_input_shaper   鈫� input preparation only 鉁�
Meta Layer           鈫� observation only 鉁�
correction.py        鈫� refinement only, no authority 鉁�
memory_audit.py      鈫� diagnostics only, no write 鉁�
analysis.py          鈫� hints only, non-binding 鉁�
reflection.py        鈫� report only, no feedback 鉁�

馃 15. FINAL CLASSIFICATION (v6.3 鈥� PRODUCTION SEALED)

Safety Cascade Pass 1 (22m)
  [DENY by default if unavailable]
鈫�
Feature Extraction (is_voice_input + structural signals)
鈫�
Safety Cascade Pass 2 (86m + safeguard-20b)
  [DENY by default if unavailable]
鈫�
Multilingual Normalization
  allam-2-7b 鈫� 邪褉邪斜褋泻懈泄 / llama-3.3-70b 鈫� 芯褋褌邪谢褜薪褘械
鈫�
EPK [SOLE POLICY AUTHORITY]
  ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED
  DENY 鈫� immediate exit
鈫�
Memory Substrate          [skip on DENY]
鈫�
Embedding Retrieval       [skip on DENY]
鈫�
Reranker                  [skip on DENY]
鈫�
analysis.py               [skip on DENY]
  full on ALLOW / HEAVY
  lightweight on DEGRADED
鈫�
Intent Engine             [skip on DENY]
鈫�
Reasoning Engine          [skip on DENY / DEGRADED]
  [ACTIVE on ALLOW / HEAVY]
  control-plane
鈫�
Multi-Agent Coordinator   [skip on DENY / DEGRADED]
鈫�
Orchestrator (execution only)
鈫�
鈹€鈹€ ALLOW 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
Fast Tier 鈫� General Tier 鈫� Agents 鈫� safety_agent 鈫� Consensus
鈹€鈹€ HEAVY_REQUIRED 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
[SKIP FAST] [SKIP GENERAL]
heavy_input_shaper (self-gated) 鈫� Heavy Tier 鈫� safety_agent
[SKIP CONSENSUS]
鈹€鈹€ DEGRADED 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
Fast Tier only 鈫� [skip all else]
鈹€鈹€ ALL PATHS 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
鈫�
Response Synthesizer (FINAL OUTPUT AUTHORITY)
  assemble 鈫� structure 鈫� format 鈫� correction 鈫� finalize
鈫�
Speech Layer (orpheus) [voice only]
鈫�
Parallel Write (Event Store 鈭� Memory Write)
鈫�
META side-channel [skip on DENY]
  reflection  鈫� report 鈫� observability
  memory_audit 鈫� offline diagnostics
  lightweight on DEGRADED / full on ALLOW / HEAVY
鈫�
OUTPUT