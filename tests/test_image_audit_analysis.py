"""Filename candidate safety: retain word order and do not merge distinct item names."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('image_audit_analysis', SCRIPTS / 'analyze-image-audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class ImageAuditAnalysisTests(unittest.TestCase):
    def test_mediawiki_title_equivalence_keeps_case_after_first_letter(self):
        self.assertEqual(audit.canonical('research_Notes.png'), 'Research Notes.png')
        self.assertNotEqual(audit.canonical('Research Notes.png'), audit.canonical('Research notes.png'))

    def test_punctuation_can_separate_identical_ordered_words(self):
        self.assertEqual(audit.words('Research Notes: Mattekar Icon.png'), audit.words('Research Notes- Mattekar Icon.png'))
        self.assertEqual(audit.words('Alduressa Boots (Loot) Icon.png'), audit.words('Alduressa Boots Loot Icon.png'))

    def test_different_word_boundaries_and_order_remain_different(self):
        self.assertNotEqual(audit.words("Bandit Cousin's Letter Icon.png"), audit.words("Bandit Cousins' Letter Icon.png"))
        self.assertNotEqual(audit.words('Virindi OCS Screenshot.png'), audit.words('Virindi OCS Screen Shot.png'))
        self.assertNotEqual(audit.words('Sword of Fire Icon.png'), audit.words('Fire Sword Icon.png'))
        self.assertNotEqual(audit.words('Chainmail Tassets Icon.png'), audit.words('Chainmail Tassets Store Icon.png'))
