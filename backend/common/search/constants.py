# Query length limits, matching the existing `q` filters.
QUERY_MIN_LENGTH = 2
QUERY_MAX_LENGTH = 100

ERROR_INVALID_SEARCH_QUERY = "invalid_search_query"
MESSAGE_QUERY_TOO_SHORT = "Search text must be at least {min} characters."
MESSAGE_QUERY_TOO_LONG = "Search text must be at most {max} characters."

# Postgres `ts_rank_cd` weights in the order {D, C, B, A}. Field weights (A = title or
# subject, B = body, C = names and emails) are assigned where each search vector is built.
RANK_WEIGHTS = [0.1, 0.2, 0.4, 1.0]
# Normalization flag 32 scales the score to 0..1 (rank / (rank + 1)), so long documents
# do not win just because they are long.
RANK_NORMALIZATION = 32

# Highlight markers. Plain sentinels instead of HTML so the API never returns markup built
# from user content; the frontend splits on them and renders React nodes.
HIGHLIGHT_START = "⟦"
HIGHLIGHT_STOP = "⟧"
HEADLINE_MAX_WORDS = 30
HEADLINE_MIN_WORDS = 15
