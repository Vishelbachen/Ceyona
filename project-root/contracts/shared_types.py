from enum import Enum


class Tier(str, Enum):
    FAST    = "FAST"
    GENERAL = "GENERAL"
    HEAVY   = "HEAVY"


class Complexity(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class EPKDecision(str, Enum):
    ALLOW          = "ALLOW"
    DENY           = "DENY"
    DEGRADED_MODE  = "DEGRADED_MODE"
    HEAVY_REQUIRED = "HEAVY_REQUIRED"


class TruthMode(str, Enum):
    STRICT     = "strict"      # только факты из context — без context = блок
    HYBRID     = "hybrid"      # LLM может дополнять, но context приоритетен
    GENERATIVE = "generative"  # свободная генерация (creative, conversation)