import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from repair_content import repair_wikitext

class RepairContent(unittest.TestCase):
    def test_rows_and_final_count_use_same_counter(self):
        text='|-{{AUTOINCREMENT}}\n|One\n|-{{AUTOINCREMENT}}\n|Two\n{{#expr:{{AUTOINCREMENT}}-1}}'
        fixed, counts=repair_wikitext(text)
        self.assertEqual(counts['counter_calls'], 3)
        self.assertTrue(fixed.startswith('{{#vardefine:acpedia_archive_row|0}}'))
        self.assertEqual(fixed.count('#vardefineecho:acpedia_archive_row'), 3)
        self.assertEqual(repair_wikitext(fixed)[0], fixed)

    def test_only_expression_category_operand_is_changed(self):
        text='{{#expr:{{PAGESINCATEGORY:Dungeon}}-4}} / {{PAGESINCATEGORY:Dungeon}}'
        fixed, counts=repair_wikitext(text)
        self.assertEqual(fixed,'{{#expr:{{PAGESINCATEGORY:Dungeon|R}}-4}} / {{PAGESINCATEGORY:Dungeon}}')
        self.assertEqual(counts['raw_category_operands'],1)
        self.assertEqual(repair_wikitext(fixed)[0],fixed)

    def test_nested_category_name_and_existing_raw_flag(self):
        fixed, counts=repair_wikitext('{{#expr:{{PAGESINCATEGORY:{{PAGENAME}}}}-1}} {{#expr:{{PAGESINCATEGORY:Quest|R}}-1}}')
        self.assertIn('PAGESINCATEGORY:{{PAGENAME}}|R',fixed)
        self.assertEqual(counts['raw_category_operands'],1)

    def test_examples_and_comments_are_preserved(self):
        for text in ['<!-- {{AUTOINCREMENT}} -->','<nowiki>{{AUTOINCREMENT}}</nowiki>','<pre>{{#expr:{{PAGESINCATEGORY:Dungeon}}-4}}</pre>']:
            self.assertEqual(repair_wikitext(text)[0],text)

    def test_existing_variable_is_not_clobbered(self):
        fixed,_=repair_wikitext('{{#var:acpedia_archive_row}} {{AUTOINCREMENT}}')
        self.assertTrue(fixed.startswith('{{#vardefine:acpedia_archive_row_|0}}'))

    def test_image_reference_correction_is_exact_and_preserves_examples(self):
        text='[[File:017D.png|Map]] {{Dungeon|Map=017D.png}} [[File:1017D.png]] <nowiki>017D.png</nowiki>'
        fixed,counts=repair_wikitext(text,{'017D.png':'017D.gif'})
        self.assertEqual(counts['image_references'],2)
        self.assertIn('[[File:017D.gif|Map]]',fixed)
        self.assertIn('Map=017D.gif',fixed)
        self.assertIn('[[File:1017D.png]]',fixed)
        self.assertIn('<nowiki>017D.png</nowiki>',fixed)

if __name__=='__main__':unittest.main()
