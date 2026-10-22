# modules/phrases.py
# Starter phrasebook. Romanization is an approximate learner aid, not IPA.
# Have a fluent Kannada speaker validate every phrase before public deployment.

import unicodedata

SCENARIOS = ["Shopping", "Transport", "Restaurant", "Hospital", "General Help"]

PHRASES = [
    {"scenario":"General Help","kn":"ನಮಸ್ಕಾರ","roman":"Namaskāra","meaning_en":"Hello / Greetings","meaning_ta":"வணக்கம்","intent":"greeting"},
    {"scenario":"General Help","kn":"ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ","roman":"Dayaviṭṭu sahāya māḍi","meaning_en":"Please help me","meaning_ta":"தயவுசெய்து எனக்கு உதவுங்கள்","intent":"help"},
    {"scenario":"General Help","kn":"ನನಗೆ ಕನ್ನಡ ಸ್ವಲ್ಪ ಮಾತ್ರ ಬರುತ್ತದೆ","roman":"Nanage Kannada svalpa mātra baruttade","meaning_en":"I speak only a little Kannada","meaning_ta":"எனக்கு கொஞ்சம் மட்டுமே கன்னடம் தெரியும்","intent":"language"},
    {"scenario":"General Help","kn":"ಇಂಗ್ಲಿಷ್ ಮಾತನಾಡುತ್ತೀರಾ?","roman":"English māṭanāḍuttīrā?","meaning_en":"Do you speak English?","meaning_ta":"உங்களுக்கு ஆங்கிலம் பேசத் தெரியுமா?","intent":"language"},
    {"scenario":"Shopping","kn":"ಇದರ ಬೆಲೆ ಎಷ್ಟು?","roman":"Idara bele eṣṭu?","meaning_en":"How much does this cost?","meaning_ta":"இதன் விலை எவ்வளவு?","intent":"price"},
    {"scenario":"Shopping","kn":"ಸ್ವಲ್ಪ ಕಡಿಮೆ ಮಾಡುತ್ತೀರಾ?","roman":"Svalpa kaḍime māḍuttīrā?","meaning_en":"Could you reduce the price a little?","meaning_ta":"கொஞ்சம் விலையைக் குறைப்பீர்களா?","intent":"bargain"},
    {"scenario":"Shopping","kn":"ನನಗೆ ಇದು ಬೇಕು","roman":"Nanage idu bēku","meaning_en":"I want this","meaning_ta":"எனக்கு ಇದು வேண்டும்","intent":"buy"},
    {"scenario":"Shopping","kn":"ಧನ್ಯವಾದಗಳು","roman":"Dhanyavādagaḷu","meaning_en":"Thank you","meaning_ta":"நன்றி","intent":"thanks"},
    {"scenario":"Transport","kn":"ರೈಲು ನಿಲ್ದಾಣ ಎಲ್ಲಿದೆ?","roman":"Railu nildāṇa ellide?","meaning_en":"Where is the railway station?","meaning_ta":"ரயில் நிலையம் எங்கே உள்ளது?","intent":"directions"},
    {"scenario":"Transport","kn":"ಬಸ್ ನಿಲ್ದಾಣಕ್ಕೆ ಹೇಗೆ ಹೋಗುವುದು?","roman":"Bus nildāṇakke hēge hōguvudu?","meaning_en":"How do I get to the bus stop?","meaning_ta":"பேருந்து நிறுத்தத்திற்கு எப்படி செல்வது?","intent":"directions"},
    {"scenario":"Transport","kn":"ದಯವಿಟ್ಟು ಇಲ್ಲಿ ನಿಲ್ಲಿಸಿ","roman":"Dayaviṭṭu illi nillisi","meaning_en":"Please stop here","meaning_ta":"தயவுசெய்து இங்கே நிறுத்துங்கள்","intent":"stop"},
    {"scenario":"Transport","kn":"ಈ ಬಸ್ ಮೈಸೂರಿಗೆ ಹೋಗುತ್ತದೆಯೇ?","roman":"Ī bus Maisūrige hōguttadeyē?","meaning_en":"Does this bus go to Mysuru?","meaning_ta":"இந்தப் பேருந்து மைசூருக்குச் செல்லுமா?","intent":"route"},
    {"scenario":"Restaurant","kn":"ಊಟದ ಮೆನು ಇದೆಯೇ?","roman":"Ūṭada menu ideyē?","meaning_en":"Do you have a food menu?","meaning_ta":"சாப்பாட்டு மெனு இருக்கிறதா?","intent":"menu"},
    {"scenario":"Restaurant","kn":"ನೀರು ಕೊಡಿ, ದಯವಿಟ್ಟು","roman":"Nīru koḍi, dayaviṭṭu","meaning_en":"Water, please","meaning_ta":"தயவுசெய்து தண்ணீர் கொடுங்கள்","intent":"water"},
    {"scenario":"Restaurant","kn":"ಇದು ಖಾರವಾಗಿದೆಯೇ?","roman":"Idu khāravāgideyē?","meaning_en":"Is this spicy?","meaning_ta":"இது காரமாக இருக்கிறதா?","intent":"spicy"},
    {"scenario":"Restaurant","kn":"ಬಿಲ್ ಕೊಡಿ, ದಯವಿಟ್ಟು","roman":"Bill koḍi, dayaviṭṭu","meaning_en":"The bill, please","meaning_ta":"தயவுசெய்து பில் கொடுங்கள்","intent":"bill"},
    {"scenario":"Hospital","kn":"ನನಗೆ ಸಹಾಯ ಬೇಕು","roman":"Nanage sahāya bēku","meaning_en":"I need help","meaning_ta":"எனக்கு உதவி தேவை","intent":"help"},
    {"scenario":"Hospital","kn":"ನನಗೆ ನೋವಾಗುತ್ತಿದೆ","roman":"Nanage nōvāguttide","meaning_en":"I am in pain","meaning_ta":"எனக்கு வலிக்கிறது","intent":"pain"},
    {"scenario":"Hospital","kn":"ಹತ್ತಿರದಲ್ಲಿ ಆಸ್ಪತ್ರೆ ಎಲ್ಲಿದೆ?","roman":"Hattiradalli asp atre ellide?","meaning_en":"Where is a nearby hospital?","meaning_ta":"அருகில் மருத்துவமனை எங்கே உள்ளது?","intent":"hospital"},
    {"scenario":"Hospital","kn":"ದಯವಿಟ್ಟು ವೈದ್ಯರನ್ನು ಕರೆಸಿ","roman":"Dayaviṭṭu vaidyaranū karesī","meaning_en":"Please call a doctor","meaning_ta":"தயவுசெய்து மருத்துவரை அழைக்கவும்","intent":"doctor"},
]


def normalize_text(text: str) -> str:
    """
    Normalize text for case-insensitive, diacritic-insensitive search.
    - Strips leading and trailing whitespace.
    - Removes Latin combining diacritical marks (e.g. ā -> a, ū -> u, ṭ -> t, ḍ -> d, ḷ -> l).
    - Preserves native Indic characters (Kannada, Tamil).
    - Replaces punctuation and symbols with spaces so queries match regardless of punctuation.
    - Converts to lower-case and normalizes multiple spaces.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", str(text).strip())
    # Strip Latin combining diacritical marks (U+0300 to U+036F, U+1AB0 to U+1AFF, U+1DC0 to U+1DFF, U+20D0 to U+20FF, U+FE20 to U+FE2F)
    stripped = "".join(
        c for c in decomposed
        if not (
            0x0300 <= ord(c) <= 0x036F
            or 0x1AB0 <= ord(c) <= 0x1AFF
            or 0x1DC0 <= ord(c) <= 0x1DFF
            or 0x20D0 <= ord(c) <= 0x20FF
            or 0xFE20 <= ord(c) <= 0xFE2F
        )
    )
    recomposed = unicodedata.normalize("NFC", stripped).lower()
    cleaned = "".join(
        " " if unicodedata.category(c).startswith("P") or unicodedata.category(c).startswith("S") else c
        for c in recomposed
    )
    return " ".join(cleaned.split())


def search_phrase(phrase: dict, query: str) -> bool:
    """
    Check if a phrase matches the search query across:
    - Kannada text (kn)
    - Romanized transliteration (roman)
    - English meaning (meaning_en)
    - Tamil meaning (meaning_ta)
    - Situation / Scenario / Topic (scenario, topic)
    - Intent (intent)
    """
    if not query or not str(query).strip():
        return True

    q_norm = normalize_text(query)
    if not q_norm:
        return True

    fields_to_check = [
        phrase.get("kn", ""),
        phrase.get("roman", ""),
        phrase.get("meaning_en", ""),
        phrase.get("meaning_ta", ""),
        phrase.get("scenario", ""),
        phrase.get("topic", ""),
        phrase.get("intent", ""),
    ]

    norm_fields = [normalize_text(field) for field in fields_to_check if field]

    # Direct substring match
    for nf in norm_fields:
        if q_norm in nf:
            return True

    # Token match: all query words appear across phrase fields
    tokens = q_norm.split()
    if len(tokens) > 1:
        combined = " ".join(norm_fields)
        if all(t in combined for t in tokens):
            return True

    return False


def get_phrases(scenario: str) -> list[dict]:
    """Return phrases belonging to the given scenario."""
    return [p for p in PHRASES if p.get("scenario") == scenario]


def filter_phrases(
    query: str = None,
    scenario: str = None,
    phrases: list[dict] = None,
) -> list[dict]:
    """
    Filter phrases by scenario/situation and search query.
    - If scenario is given and not 'All situations' / 'All', filters by scenario.
    - If query is given and not empty, searches across all relevant fields with
      case-insensitivity and Unicode transliteration diacritic normalization.
    - Returns all phrases if query is empty or only whitespace.
    """
    phrase_list = phrases if phrases is not None else PHRASES
    result = phrase_list

    if scenario and scenario not in ("All situations", "All", "All topics"):
        result = [
            p for p in result
            if p.get("scenario") == scenario or p.get("topic") == scenario
        ]

    if query and str(query).strip():
        result = [p for p in result if search_phrase(p, query)]

    return result
