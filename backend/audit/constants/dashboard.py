CACHE_NAMESPACE = "dashboard"
CACHE_TTL_SECONDS = 30
THROTTLE_SCOPE = "dashboard"

DEFAULT_TIMEZONE = "UTC"
# Browsers can report legacy names that other systems do not know; they are rewritten to the
# canonical IANA name before use (and echoed back in that form).
TIMEZONE_ALIASES = {
    "Asia/Katmandu": "Asia/Kathmandu",
    "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "Asia/Rangoon": "Asia/Yangon",
    "Asia/Dacca": "Asia/Dhaka",
    "Asia/Thimbu": "Asia/Thimphu",
    "Asia/Ujung_Pandang": "Asia/Makassar",
    "Europe/Kiev": "Europe/Kyiv",
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
    "America/Indianapolis": "America/Indiana/Indianapolis",
    "Atlantic/Faeroe": "Atlantic/Faroe",
    "Pacific/Truk": "Pacific/Chuuk",
    "Pacific/Ponape": "Pacific/Pohnpei",
    "US/Eastern": "America/New_York",
    "US/Central": "America/Chicago",
    "US/Mountain": "America/Denver",
    "US/Pacific": "America/Los_Angeles",
    "GMT": "UTC",
    "Etc/UTC": "UTC",
    "Etc/GMT": "UTC",
}
DEFAULT_PERIOD = "30d"
PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90}
CUSTOM_PERIOD = "custom"
MAX_CUSTOM_DAYS = 366  # inclusive: from and to may span at most this many days
DAILY_BUCKET_MAX_DAYS = 31  # longer periods are bucketed by week
BUCKET_WEEK_DAYS = 7

SECTION_SUMMARY = "summary"
SECTION_VOLUME = "volume"
SECTION_RECENT = "recent_tickets"
SECTION_WAITING = "waiting"
SECTION_ACTIVITY = "activity"
SECTIONS = (
    SECTION_SUMMARY,
    SECTION_VOLUME,
    SECTION_RECENT,
    SECTION_WAITING,
    SECTION_ACTIVITY,
)

DEFAULT_RECENT_LIMIT = 5
DEFAULT_WAITING_LIMIT = 5
DEFAULT_ACTIVITY_LIMIT = 10
MIN_LIMIT = 1
MAX_LIMIT = 50

ACTIVITY_SOURCE_TICKET = "ticket"
