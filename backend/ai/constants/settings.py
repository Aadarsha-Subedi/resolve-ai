MODE_RESOLVE_AI = "resolve_ai"
MODE_OWN_KEY = "own_key"
MODES = (MODE_RESOLVE_AI, MODE_OWN_KEY)

MODE_MAX_LENGTH = 20
PROVIDER_MAX_LENGTH = 20
MODEL_MAX_LENGTH = 60
KEY_LAST4_LENGTH = 4
API_KEY_MIN_LENGTH = 8
API_KEY_MAX_LENGTH = 512

# Ciphertext is bound to its owner: "<workspace id>|<user id>|<api key>".
SEAL_SEPARATOR = "|"

# AI usage log (owner only): one row per AI call in the workspace.
USAGE_FEATURE_ASK = "ask"
USAGE_FEATURE_REWRITE = "rewrite"
USAGE_FEATURE_RERANK = "rerank"
USAGE_FEATURE_EMBEDDING = "embedding"
USAGE_FEATURES = (
    USAGE_FEATURE_ASK,
    USAGE_FEATURE_REWRITE,
    USAGE_FEATURE_RERANK,
    USAGE_FEATURE_EMBEDDING,
)
USAGE_OUTCOME_CACHE_HIT = "cache_hit"  # answered from the semantic cache, no LLM call
USAGE_OUTCOME_LLM_CALL = "llm_call"  # sent to the provider
USAGE_OUTCOME_ERROR = "error"  # the provider call failed
USAGE_OUTCOMES = (USAGE_OUTCOME_CACHE_HIT, USAGE_OUTCOME_LLM_CALL, USAGE_OUTCOME_ERROR)
USAGE_FEATURE_MAX_LENGTH = 20
USAGE_OUTCOME_MAX_LENGTH = 20
USAGE_ERROR_MAX_LENGTH = 60
USAGE_SEARCH_MAX_LENGTH = 200
USAGE_RETENTION_DAYS = 90
USAGE_ORDERINGS = {
    "created_at": "created_at",
    "user": "user__display_name",
    "feature": "feature",
    "outcome": "outcome",
    "tokens": "total_tokens",
}
TASK_PURGE_USAGE_LOGS = "ai.purge_usage_logs"
