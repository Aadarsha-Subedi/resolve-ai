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
