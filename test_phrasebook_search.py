# test_phrasebook_search.py
# Unit and regression test suite for Phrasebook search & normalization.
# Tests diacritic-insensitive, case-insensitive, multi-field, and combined filtering.

import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from modules.phrases import (
    PHRASES,
    SCENARIOS,
    get_phrases,
    normalize_text,
    search_phrase,
    filter_phrases,
)


class TestPhrasebookSearch(unittest.TestCase):

    def test_01_namaskara_matches_namaskara_diacritics(self):
        """Test that searching 'Namaskara' matches 'Namaskāra'."""
        results = filter_phrases(query="Namaskara")
        self.assertGreater(len(results), 0)
        matched_kn = [p["kn"] for p in results]
        matched_roman = [p["roman"] for p in results]
        self.assertIn("ನಮಸ್ಕಾರ", matched_kn)
        self.assertIn("Namaskāra", matched_roman)

        # Also test with exact transliteration
        results_exact = filter_phrases(query="Namaskāra")
        self.assertGreater(len(results_exact), 0)
        self.assertIn("ನಮಸ್ಕಾರ", [p["kn"] for p in results_exact])

    def test_02_case_insensitive_matching(self):
        """Test case-insensitive queries (lowercase, uppercase, mixed-case)."""
        lower_res = filter_phrases(query="namaskara")
        upper_res = filter_phrases(query="NAMASKARA")
        mixed_res = filter_phrases(query="NaMaSkArA")

        self.assertGreater(len(lower_res), 0)
        self.assertEqual(len(lower_res), len(upper_res))
        self.assertEqual(len(lower_res), len(mixed_res))
        self.assertIn("ನಮಸ್ಕಾರ", [p["kn"] for p in lower_res])

        # Test another word in mixed case
        res_help_upper = filter_phrases(query="PLEASE HELP")
        res_help_lower = filter_phrases(query="please help")
        self.assertGreater(len(res_help_upper), 0)
        self.assertEqual(len(res_help_upper), len(res_help_lower))

    def test_03_english_meaning_search(self):
        """Test searching via English meaning field."""
        # 'water' should find 'Water, please'
        res_water = filter_phrases(query="water")
        self.assertGreater(len(res_water), 0)
        self.assertTrue(any("water" in p["meaning_en"].lower() for p in res_water))
        self.assertIn("ನೀರು ಕೊಡಿ, ದಯವಿಟ್ಟು", [p["kn"] for p in res_water])

        # 'spicy' should find 'Is this spicy?'
        res_spicy = filter_phrases(query="spicy")
        self.assertGreater(len(res_spicy), 0)
        self.assertIn("ಇದು ಖಾರವಾಗಿದೆಯೇ?", [p["kn"] for p in res_spicy])

        # 'hospital' should find hospital phrases
        res_hosp = filter_phrases(query="hospital")
        self.assertGreater(len(res_hosp), 0)

    def test_04_kannada_text_search(self):
        """Test searching via genuine Kannada Unicode script."""
        res_kn = filter_phrases(query="ನಮಸ್ಕಾರ")
        self.assertGreater(len(res_kn), 0)
        self.assertEqual(res_kn[0]["kn"], "ನಮಸ್ಕಾರ")

        res_water_kn = filter_phrases(query="ನೀರು")
        self.assertGreater(len(res_water_kn), 0)
        self.assertTrue(any("ನೀರು" in p["kn"] for p in res_water_kn))

        res_help_kn = filter_phrases(query="ಸಹಾಯ")
        self.assertGreater(len(res_help_kn), 0)

    def test_05_tamil_meaning_search(self):
        """Test searching via Tamil script meaning field."""
        # 'வணக்கம்' (Vanakkam) should match Namaskara
        res_ta_hello = filter_phrases(query="வணக்கம்")
        self.assertGreater(len(res_ta_hello), 0)
        self.assertIn("ನಮಸ್ಕಾರ", [p["kn"] for p in res_ta_hello])

        # 'நன்றி' (Nandri) should match Dhanyavadagalu (Thank you)
        res_ta_thanks = filter_phrases(query="நன்றி")
        self.assertGreater(len(res_ta_thanks), 0)
        self.assertIn("ಧನ್ಯವಾದಗಳು", [p["kn"] for p in res_ta_thanks])

        # 'தண்ணீர்' (Thanneer) should match Water, please
        res_ta_water = filter_phrases(query="தண்ணீர்")
        self.assertGreater(len(res_ta_water), 0)
        self.assertIn("ನೀರು ಕೊಡಿ, ದಯವಿಟ್ಟು", [p["kn"] for p in res_ta_water])

    def test_06_topic_situation_filtering(self):
        """Test filtering by topic/situation alone."""
        for scenario in SCENARIOS:
            res_sc = filter_phrases(scenario=scenario)
            self.assertGreater(len(res_sc), 0)
            self.assertTrue(all(p["scenario"] == scenario for p in res_sc))

        # Test 'All situations' returns all phrases
        all_res = filter_phrases(scenario="All situations")
        self.assertEqual(len(all_res), len(PHRASES))

    def test_07_search_combined_with_situation_filter(self):
        """Test combining a text query with a situation filter."""
        # Searching 'Namaskara' within 'General Help' should find it
        res_gen = filter_phrases(query="Namaskara", scenario="General Help")
        self.assertEqual(len(res_gen), 1)
        self.assertEqual(res_gen[0]["kn"], "ನಮಸ್ಕಾರ")

        # Searching 'Namaskara' within 'Shopping' should return NO phrases
        res_shop = filter_phrases(query="Namaskara", scenario="Shopping")
        self.assertEqual(len(res_shop), 0)

        # Searching 'price' within 'Shopping' should find shopping phrases
        res_price_shop = filter_phrases(query="price", scenario="Shopping")
        self.assertGreater(len(res_price_shop), 0)
        self.assertTrue(all(p["scenario"] == "Shopping" for p in res_price_shop))

        # Searching 'price' within 'Transport' should return 0
        res_price_trans = filter_phrases(query="price", scenario="Transport")
        self.assertEqual(len(res_price_trans), 0)

    def test_08_empty_search_shows_all_phrases(self):
        """Test empty queries, None, and whitespace-only queries show all phrases."""
        self.assertEqual(len(filter_phrases(query="")), len(PHRASES))
        self.assertEqual(len(filter_phrases(query=None)), len(PHRASES))
        self.assertEqual(len(filter_phrases(query="   ")), len(PHRASES))
        self.assertEqual(len(filter_phrases(query="\t\n ")), len(PHRASES))

        # Empty query with a scenario filter shows all phrases in that scenario
        shop_all = filter_phrases(query="  ", scenario="Shopping")
        shop_expected = [p for p in PHRASES if p["scenario"] == "Shopping"]
        self.assertEqual(len(shop_all), len(shop_expected))

    def test_09_leading_and_trailing_spaces_handled(self):
        """Test queries with leading and trailing spaces match correctly."""
        res_spaced = filter_phrases(query="  Namaskara   ")
        self.assertGreater(len(res_spaced), 0)
        self.assertIn("ನಮಸ್ಕಾರ", [p["kn"] for p in res_spaced])

        res_kn_spaced = filter_phrases(query="  ನಮಸ್ಕಾರ   ")
        self.assertGreater(len(res_kn_spaced), 0)
        self.assertIn("ನಮಸ್ಕಾರ", [p["kn"] for p in res_kn_spaced])

    def test_10_other_diacritics_normalization(self):
        """Test other phrases with diacritics: Dayaviṭṭu, Dhanyavādagaḷu, Ūṭada, nōvāguttide."""
        # 'Dayavittu' matches 'Dayaviṭṭu'
        res_d = filter_phrases(query="Dayavittu")
        self.assertGreater(len(res_d), 0)
        self.assertTrue(any("Dayaviṭṭu" in p["roman"] for p in res_d))

        # 'Dhanyavadagalu' matches 'Dhanyavādagaḷu'
        res_dh = filter_phrases(query="Dhanyavadagalu")
        self.assertGreater(len(res_dh), 0)
        self.assertTrue(any("Dhanyavādagaḷu" in p["roman"] for p in res_dh))

        # 'Utada' matches 'Ūṭada'
        res_u = filter_phrases(query="Utada")
        self.assertGreater(len(res_u), 0)
        self.assertTrue(any("Ūṭada" in p["roman"] for p in res_u))

    def test_11_search_across_topic_and_scenario_fields(self):
        """Test search query matching scenario/topic field and custom phrases with topic field."""
        # Query matching situation name directly
        res_hosp = filter_phrases(query="Hospital")
        self.assertGreater(len(res_hosp), 0)
        self.assertTrue(all(p["scenario"] == "Hospital" for p in res_hosp))

        # Query on custom phrases that use 'topic' instead of 'scenario'
        custom_phrases = [
            {"topic": "Transit", "kn": "ಮೆಟ್ರೋ ನಿಲ್ದಾಣ", "roman": "Metro nildāṇa", "meaning_en": "Metro station", "meaning_ta": "மெட்ரோ நிலையம்"},
            {"topic": "Cafe", "kn": "ಕಾಫಿ ಕೊಡಿ", "roman": "Coffee koḍi", "meaning_en": "Give coffee", "meaning_ta": "காபி கொடுங்கள்"},
        ]
        res_topic_filter = filter_phrases(scenario="Transit", phrases=custom_phrases)
        self.assertEqual(len(res_topic_filter), 1)
        self.assertEqual(res_topic_filter[0]["kn"], "ಮೆಟ್ರೋ ನಿಲ್ದಾಣ")

        # Search across topic field text
        res_topic_query = filter_phrases(query="Cafe", phrases=custom_phrases)
        self.assertEqual(len(res_topic_query), 1)
        self.assertEqual(res_topic_query[0]["kn"], "ಕಾಫಿ ಕೊಡಿ")

    def test_12_punctuation_insensitive_search(self):
        """Test searching with and without punctuation."""
        # Query without comma matches phrase containing comma ('Water, please')
        res_no_comma = filter_phrases(query="water please")
        self.assertGreater(len(res_no_comma), 0)
        self.assertIn("ನೀರು ಕೊಡಿ, ದಯವಿಟ್ಟು", [p["kn"] for p in res_no_comma])

        # Query with comma matches phrase
        res_with_comma = filter_phrases(query="water, please")
        self.assertGreater(len(res_with_comma), 0)
        self.assertIn("ನೀರು ಕೊಡಿ, ದಯವಿಟ್ಟು", [p["kn"] for p in res_with_comma])

        # Query without question mark matches phrase with question mark ('Is this spicy?')
        res_spicy_plain = filter_phrases(query="is this spicy")
        self.assertGreater(len(res_spicy_plain), 0)
        self.assertIn("ಇದು ಖಾರವಾಗಿದೆಯೇ?", [p["kn"] for p in res_spicy_plain])

        # Query with exclamation mark matches phrase ('Namaskara!')
        res_exclamation = filter_phrases(query="Namaskara!")
        self.assertGreater(len(res_exclamation), 0)
        self.assertIn("ನಮಸ್ಕಾರ", [p["kn"] for p in res_exclamation])

    def test_13_phrase_data_integrity(self):
        """Verify phrase data was not tampered with, fake phrases not added, and Namaskāra is preserved."""
        # Must have exactly 20 starter phrases
        self.assertEqual(len(PHRASES), 20)
        # First phrase must retain original diacritics in dataset
        hello_phrase = [p for p in PHRASES if p["kn"] == "ನಮಸ್ಕಾರ"][0]
        self.assertEqual(hello_phrase["roman"], "Namaskāra")
        self.assertEqual(hello_phrase["scenario"], "General Help")
        self.assertEqual(hello_phrase["meaning_en"], "Hello / Greetings")
        self.assertEqual(hello_phrase["meaning_ta"], "வணக்கம்")

    def test_14_combined_filter_and_search_edge_cases(self):
        """Test additional combined filtering and non-matching scenarios."""
        # Searching nonexistent term returns empty list
        res_none = filter_phrases(query="xyznonexistentphrase123")
        self.assertEqual(len(res_none), 0)

        # Searching valid query in wrong situation returns empty list
        res_wrong_scenario = filter_phrases(query="doctor", scenario="Shopping")
        self.assertEqual(len(res_wrong_scenario), 0)

        # Searching valid query in correct situation returns match
        res_correct_scenario = filter_phrases(query="doctor", scenario="Hospital")
        self.assertEqual(len(res_correct_scenario), 1)
        self.assertIn("ದಯವಿಟ್ಟು ವೈದ್ಯರನ್ನು ಕರೆಸಿ", [p["kn"] for p in res_correct_scenario])


if __name__ == "__main__":
    unittest.main(verbosity=2)

