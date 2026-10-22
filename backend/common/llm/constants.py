"""Providers, model allowlists and call limits. Model names live here, not in logic."""

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDERS = (PROVIDER_GEMINI, PROVIDER_OPENAI)

# Models a user may pick with their own key.
GEMINI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-4-argon",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
)
OPENAI_MODELS = (
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-5",
)
ALLOWED_MODELS = {
    PROVIDER_GEMINI: GEMINI_MODELS,
    PROVIDER_OPENAI: OPENAI_MODELS,
}
DEFAULT_MODELS = {
    PROVIDER_GEMINI: "gemini-3.5-flash-lite",
    PROVIDER_OPENAI: "gpt-5-mini",
}

# The Resolve AI key costs us money, so it only serves cheap models.
RESOLVE_AI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
)

REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.2
