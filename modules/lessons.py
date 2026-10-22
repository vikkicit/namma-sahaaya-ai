# modules/lessons.py
# Curated Daily Kannada Lesson data.
# No Gemini API calls are made here — all data is local.
# Schema per lesson:
#   id          : str  — unique stable identifier
#   title       : str
#   topic       : str  — broad grouping label
#   difficulty  : "Beginner" | "Elementary" | "Intermediate"
#   objectives  : list[str]
#   phrases     : list[dict]  — same schema as PHRASES (kn, roman, meaning_en, meaning_ta)
#   practice    : str  — short plain-text activity description

LESSONS = [
    {
        "id": "greetings-01",
        "title": "First Hellos",
        "topic": "Greetings",
        "difficulty": "Beginner",
        "objectives": [
            "Say hello and goodbye in Kannada.",
            "Use polite greetings at different times of day.",
            "Understand common Kannada pleasantries.",
        ],
        "phrases": [
            {
                "kn": "ನಮಸ್ಕಾರ",
                "roman": "Namaskāra",
                "meaning_en": "Hello / Greetings (formal)",
                "meaning_ta": "வணக்கம்",
            },
            {
                "kn": "ಹೇಗಿದ್ದೀರಾ?",
                "roman": "Hēgiddīrā?",
                "meaning_en": "How are you? (formal)",
                "meaning_ta": "நீங்கள் எப்படி இருக்கிறீர்கள்?",
            },
            {
                "kn": "ಚೆನ್ನಾಗಿದ್ದೇನೆ",
                "roman": "Channāgiddēne",
                "meaning_en": "I am fine / well",
                "meaning_ta": "நான் நலமாக இருக்கிறேன்",
            },
            {
                "kn": "ಧನ್ಯವಾದಗಳು",
                "roman": "Dhanyavādagaḷu",
                "meaning_en": "Thank you",
                "meaning_ta": "நன்றி",
            },
            {
                "kn": "ಮತ್ತೆ ಭೇಟಿಯಾಗೋಣ",
                "roman": "Matte bhēṭiyāgōṇa",
                "meaning_en": "Let us meet again / Goodbye",
                "meaning_ta": "மீண்டும் சந்திக்கலாம்",
            },
        ],
        "practice": (
            "Cover the English/Tamil column and say each phrase aloud. "
            "Then greet an imaginary shopkeeper: say hello, ask how they are, "
            "and say thank you before leaving."
        ),
    },
    {
        "id": "introductions-01",
        "title": "Introducing Yourself",
        "topic": "Introductions",
        "difficulty": "Beginner",
        "objectives": [
            "State your name and where you are from.",
            "Ask someone their name politely.",
            "Say you are new to the area.",
        ],
        "phrases": [
            {
                "kn": "ನನ್ನ ಹೆಸರು …",
                "roman": "Nanna hesaru …",
                "meaning_en": "My name is …",
                "meaning_ta": "என் பெயர் …",
            },
            {
                "kn": "ನಿಮ್ಮ ಹೆಸರೇನು?",
                "roman": "Nimma hesarēnu?",
                "meaning_en": "What is your name? (polite)",
                "meaning_ta": "உங்கள் பெயர் என்ன?",
            },
            {
                "kn": "ನಾನು ತಮಿಳುನಾಡಿನಿಂದ ಬಂದಿದ್ದೇನೆ",
                "roman": "Nānu Tamiḷunāḍininda bandiddēne",
                "meaning_en": "I have come from Tamil Nadu",
                "meaning_ta": "நான் தமிழ்நாட்டிலிருந்து வந்தேன்",
            },
            {
                "kn": "ನಾನು ಇಲ್ಲಿಗೆ ಹೊಸಬನು",
                "roman": "Nānu illige hosabaṇu",
                "meaning_en": "I am new here",
                "meaning_ta": "நான் இங்கே புதியவன்",
            },
            {
                "kn": "ನಿಮ್ಮನ್ನು ಭೇಟಿಯಾಗಿ ಸಂತೋಷ",
                "roman": "Nimmannu bhēṭiyāgi santōṣa",
                "meaning_en": "Nice to meet you",
                "meaning_ta": "உங்களை சந்தித்ததில் மகிழ்ச்சி",
            },
        ],
        "practice": (
            "Imagine you just arrived in Bengaluru. Introduce yourself to your "
            "new neighbour: say your name, that you are from Tamil Nadu, that you "
            "are new here, and that you are happy to meet them."
        ),
    },
    {
        "id": "shopping-01",
        "title": "At the Market",
        "topic": "Shopping",
        "difficulty": "Beginner",
        "objectives": [
            "Ask the price of an item.",
            "Politely request a discount.",
            "Complete a simple purchase.",
        ],
        "phrases": [
            {
                "kn": "ಇದರ ಬೆಲೆ ಎಷ್ಟು?",
                "roman": "Idara bele eṣṭu?",
                "meaning_en": "How much does this cost?",
                "meaning_ta": "இதன் விலை எவ்வளவு?",
            },
            {
                "kn": "ಸ್ವಲ್ಪ ಕಡಿಮೆ ಮಾಡುತ್ತೀರಾ?",
                "roman": "Svalpa kaḍime māḍuttīrā?",
                "meaning_en": "Can you reduce the price a little?",
                "meaning_ta": "கொஞ்சம் விலையைக் குறைப்பீர்களா?",
            },
            {
                "kn": "ನನಗೆ ಇದು ಬೇಕು",
                "roman": "Nanage idu bēku",
                "meaning_en": "I want / need this",
                "meaning_ta": "எனக்கு இது வேண்டும்",
            },
            {
                "kn": "ಇಲ್ಲಿ ಬಿಲ್ ಕೊಡಿ",
                "roman": "Illi bill koḍi",
                "meaning_en": "Give me the bill here",
                "meaning_ta": "இங்கே பில் கொடுங்கள்",
            },
            {
                "kn": "ನಗದು ತೆಗೆದುಕೊಳ್ಳುತ್ತೀರಾ?",
                "roman": "Nagadu tegedukoḷḷuttīrā?",
                "meaning_en": "Do you accept cash?",
                "meaning_ta": "ரொக்கம் எடுத்துக்கொள்வீர்களா?",
            },
        ],
        "practice": (
            "Role-play buying vegetables. Ask for the price, try to negotiate "
            "a small discount, say you want two of the item, then ask for the bill."
        ),
    },
    {
        "id": "restaurant-01",
        "title": "Ordering Food",
        "topic": "Restaurant",
        "difficulty": "Beginner",
        "objectives": [
            "Ask for a menu and order food.",
            "Request water and check for spice level.",
            "Ask for the bill.",
        ],
        "phrases": [
            {
                "kn": "ಊಟದ ಮೆನು ಇದೆಯೇ?",
                "roman": "Ūṭada menu ideyē?",
                "meaning_en": "Do you have a food menu?",
                "meaning_ta": "சாப்பாட்டு மெனு இருக்கிறதா?",
            },
            {
                "kn": "ನೀರು ಕೊಡಿ, ದಯವಿಟ್ಟು",
                "roman": "Nīru koḍi, dayaviṭṭu",
                "meaning_en": "Water please",
                "meaning_ta": "தயவுசெய்து தண்ணீர் கொடுங்கள்",
            },
            {
                "kn": "ಇದು ಖಾರವಾಗಿದೆಯೇ?",
                "roman": "Idu khāravāgideyē?",
                "meaning_en": "Is this spicy?",
                "meaning_ta": "இது காரமாக இருக்கிறதா?",
            },
            {
                "kn": "ಒಂದು ಇಡ್ಲಿ ಕೊಡಿ",
                "roman": "Ondu iḍli koḍi",
                "meaning_en": "Give me one idli",
                "meaning_ta": "ஒரு இட்லி கொடுங்கள்",
            },
            {
                "kn": "ಬಿಲ್ ಕೊಡಿ, ದಯವಿಟ್ಟು",
                "roman": "Bill koḍi, dayaviṭṭu",
                "meaning_en": "The bill, please",
                "meaning_ta": "தயவுசெய்து பில் கொடுங்கள்",
            },
        ],
        "practice": (
            "Imagine you are at a Bengaluru darshini (self-service restaurant). "
            "Ask for the menu, order one idli, ask if it is spicy, request water, "
            "and finally ask for your bill."
        ),
    },
    {
        "id": "transport-01",
        "title": "Getting Around",
        "topic": "Transport",
        "difficulty": "Elementary",
        "objectives": [
            "Ask where a bus stop or station is.",
            "Ask if a bus goes to a destination.",
            "Ask the driver or conductor to stop.",
        ],
        "phrases": [
            {
                "kn": "ಬಸ್ ನಿಲ್ದಾಣಕ್ಕೆ ಹೇಗೆ ಹೋಗುವುದು?",
                "roman": "Bus nildāṇakke hēge hōguvudu?",
                "meaning_en": "How do I get to the bus stop?",
                "meaning_ta": "பேருந்து நிறுத்தத்திற்கு எப்படி செல்வது?",
            },
            {
                "kn": "ರೈಲು ನಿಲ್ದಾಣ ಎಲ್ಲಿದೆ?",
                "roman": "Railu nildāṇa ellide?",
                "meaning_en": "Where is the railway station?",
                "meaning_ta": "ரயில் நிலையம் எங்கே உள்ளது?",
            },
            {
                "kn": "ಈ ಬಸ್ ಬೆಂಗಳೂರಿಗೆ ಹೋಗುತ್ತದೆಯೇ?",
                "roman": "Ī bus Bengaḷūrige hōguttadeyē?",
                "meaning_en": "Does this bus go to Bengaluru?",
                "meaning_ta": "இந்த பேருந்து பெங்களூருக்கு செல்லுமா?",
            },
            {
                "kn": "ದಯವಿಟ್ಟು ಇಲ್ಲಿ ನಿಲ್ಲಿಸಿ",
                "roman": "Dayaviṭṭu illi nillisi",
                "meaning_en": "Please stop here",
                "meaning_ta": "தயவுசெய்து இங்கே நிறுத்துங்கள்",
            },
            {
                "kn": "ಟಿಕೆಟ್ ಎಷ್ಟು?",
                "roman": "Ṭikeṭ eṣṭu?",
                "meaning_en": "How much is the ticket?",
                "meaning_ta": "டிக்கெட் எவ்வளவு?",
            },
        ],
        "practice": (
            "You are at a bus stand and want to reach MG Road, Bengaluru. "
            "Ask if the bus goes there, find out the ticket price, "
            "and practise telling the conductor to stop when you arrive."
        ),
    },
    {
        "id": "directions-01",
        "title": "Asking for Directions",
        "topic": "Directions",
        "difficulty": "Elementary",
        "objectives": [
            "Ask where a place is.",
            "Understand basic directional responses.",
            "Thank someone for giving directions.",
        ],
        "phrases": [
            {
                "kn": "… ಎಲ್ಲಿದೆ?",
                "roman": "… ellide?",
                "meaning_en": "Where is …?",
                "meaning_ta": "… எங்கே உள்ளது?",
            },
            {
                "kn": "ನೇರವಾಗಿ ಹೋಗಿ",
                "roman": "Nēravāgi hōgi",
                "meaning_en": "Go straight ahead",
                "meaning_ta": "நேராக செல்லுங்கள்",
            },
            {
                "kn": "ಎಡಕ್ಕೆ ತಿರುಗಿ",
                "roman": "Eḍakke tirugi",
                "meaning_en": "Turn left",
                "meaning_ta": "இடதுபுறம் திரும்புங்கள்",
            },
            {
                "kn": "ಬಲಕ್ಕೆ ತಿರುಗಿ",
                "roman": "Balakke tirugi",
                "meaning_en": "Turn right",
                "meaning_ta": "வலதுபுறம் திரும்புங்கள்",
            },
            {
                "kn": "ಹತ್ತಿರದಲ್ಲೇ ಇದೆ",
                "roman": "Hattiradallē ide",
                "meaning_en": "It is nearby / close by",
                "meaning_ta": "அது அருகிலேயே இருக்கிறது",
            },
        ],
        "practice": (
            "Ask a passerby where the nearest ATM is. Listen for them to say "
            "go straight then turn left. Practise repeating the directions back "
            "to confirm you understood correctly."
        ),
    },
    {
        "id": "numbers-01",
        "title": "Numbers and Counting",
        "topic": "Numbers",
        "difficulty": "Beginner",
        "objectives": [
            "Count from one to ten in Kannada.",
            "Use numbers when asking prices.",
            "Say how many items you want.",
        ],
        "phrases": [
            {
                "kn": "ಒಂದು, ಎರಡು, ಮೂರು",
                "roman": "Ondu, eraḍu, mūru",
                "meaning_en": "One, two, three",
                "meaning_ta": "ஒன்று, இரண்டு, மூன்று",
            },
            {
                "kn": "ನಾಲ್ಕು, ಐದು, ಆರು",
                "roman": "Nālku, aidu, āru",
                "meaning_en": "Four, five, six",
                "meaning_ta": "நான்கு, ஐந்து, ஆறு",
            },
            {
                "kn": "ಏಳು, ಎಂಟು, ಒಂಬತ್ತು, ಹತ್ತು",
                "roman": "Ēḷu, eṇṭu, ombaṯṯu, hattu",
                "meaning_en": "Seven, eight, nine, ten",
                "meaning_ta": "ஏழு, எட்டு, ஒன்பது, பத்து",
            },
            {
                "kn": "ಎರಡು ಕೊಡಿ",
                "roman": "Eraḍu koḍi",
                "meaning_en": "Give me two",
                "meaning_ta": "இரண்டு கொடுங்கள்",
            },
            {
                "kn": "ಐದು ರೂಪಾಯಿ",
                "roman": "Aidu rūpāyi",
                "meaning_en": "Five rupees",
                "meaning_ta": "ஐந்து ரூபாய்",
            },
        ],
        "practice": (
            "Count from one to ten aloud with the audio. Then practise ordering "
            "at a shop: say you want three items and ask how much five of something costs."
        ),
    },
    {
        "id": "help-01",
        "title": "Asking for Help",
        "topic": "General Help",
        "difficulty": "Beginner",
        "objectives": [
            "Ask for assistance politely.",
            "Say you do not understand.",
            "Ask someone to speak slowly.",
        ],
        "phrases": [
            {
                "kn": "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ",
                "roman": "Dayaviṭṭu sahāya māḍi",
                "meaning_en": "Please help me",
                "meaning_ta": "தயவுசெய்து என்னை உதவுங்கள்",
            },
            {
                "kn": "ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ",
                "roman": "Nanage arthavāgalilla",
                "meaning_en": "I did not understand",
                "meaning_ta": "எனக்கு புரியவில்லை",
            },
            {
                "kn": "ದಯವಿಟ್ಟು ನಿಧಾನವಾಗಿ ಮಾತನಾಡಿ",
                "roman": "Dayaviṭṭu nidhānavāgi māṭanāḍi",
                "meaning_en": "Please speak slowly",
                "meaning_ta": "தயவுசெய்து மெதுவாகப் பேசுங்கள்",
            },
            {
                "kn": "ಮತ್ತೊಮ್ಮೆ ಹೇಳುತ್ತೀರಾ?",
                "roman": "Mattomme hēḷuttīrā?",
                "meaning_en": "Could you say that again?",
                "meaning_ta": "மீண்டும் சொல்வீர்களா?",
            },
            {
                "kn": "ನನಗೆ ಕನ್ನಡ ಸ್ವಲ್ಪ ಮಾತ್ರ ಬರುತ್ತದೆ",
                "roman": "Nanage Kannada svalpa mātra baruttade",
                "meaning_en": "I speak only a little Kannada",
                "meaning_ta": "எனக்கு கொஞ்சம் மட்டுமே கன்னடம் தெரியும்",
            },
        ],
        "practice": (
            "Imagine someone gives you complex directions very quickly. "
            "Practise asking them to repeat slowly, saying you did not understand, "
            "and letting them know you only speak a little Kannada."
        ),
    },
]

# Stable list of all lesson IDs in order
LESSON_IDS = [l["id"] for l in LESSONS]

# Index for quick lookup
LESSONS_BY_ID = {l["id"]: l for l in LESSONS}

# Topic grouping
LESSON_TOPICS = sorted(set(l["topic"] for l in LESSONS))
