import datetime
import json
from pathlib import Path


MTURK_ID_LENGTH = 255  # From Amazon mturk docs
QID_MASTERS_SANDBOX = "2ARFPLSP75KLA8M8DH1HTEQVJT3SY6"
QID_MASTERS_PRODUCTION = "2F1QJWKUDD8XADTFD2Q0G6UTO95ALH"
QID_PERCENT_APPROVED = "000000000000000000L0"
QID_NUM_APPROVED = "00000000000000000040"
QID_COUNTRY = "00000000000000000071"
QID_ADULT = "00000000000000000060"

WORKER_NAME_MAX_LENGTH = 40
NUM_WORDS_WORDS_TO_PRONOUNCE = 3
WORDS_TO_PRONOUNCE = ("apple", "lemon", "lime", "mango", "orange", "peach", "pineapple", "watermelon")
LOCATION_UNKNOWN = "Unknown"
SIMULATED_PREFIX = "simulated/"
ZULU_STRFTIME = "%Y-%m-%dT%H:%M:%SZ"

ENGLISH_SPEAKING_COUNTRIES = (
    "AG",  # Antigua and Barbuda
    "AU",  # Australia
    "BS",  # The Bahamas
    "BB",  # Barbados
    "BZ",  # Belize
    "CA",  # Canada*
    "DM",  # Dominica
    "GD",  # Grenada
    "GY",  # Guyana
    "IE",  # Ireland
    "JM",  # Jamaica
    "MT",  # Malta
    "NZ",  # New Zealand
    "KN",  # St Kitts and Nevis
    "LC",  # St Lucia
    "VC",  # St Vincent and the Grenadines
    "ZA",  # South Africa
    "TT",  # Trinidad and Tobago
    "GB",  # United Kingdom
    "US",  # United States of America
)

CORE_ENGLISH_SPEAKING_COUNTRIES = {"AU", "CA", "IE", "US", "GB"}
CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES = ("Australia", "Canada", "Ireland", "United Kingdom", "United States of America")

# Estimate it takes abouts 3 minutes to verify from the time we start HIT (for UI purposes)
ESTIMATED_BEFORE_VERIFIED_DURATION = datetime.timedelta(minutes=3)

# Load up shared ones
with open(Path(__file__).parent.parent / "shared-constants.json", "r") as _file:
    _data = json.load(_file)

CALL_STEP_INITIAL = _data["CALL_STEP_INITIAL"]
CALL_STEP_VERIFIED = _data["CALL_STEP_VERIFIED"]
CALL_STEP_HOLD = _data["CALL_STEP_HOLD"]
CALL_STEP_CALL = _data["CALL_STEP_CALL"]
CALL_STEP_VOICEMAIL = _data["CALL_STEP_VOICEMAIL"]
CALL_STEP_DONE = _data["CALL_STEP_DONE"]
del _file, _data
