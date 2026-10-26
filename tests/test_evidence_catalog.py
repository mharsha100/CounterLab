"""Catalog metadata must cover the fixed exports without mixing evidence types."""
import unittest

from counterlab.api import (GUARDED_RECORDED_ID, RECORDED_ID, SOURCE_RECORDED_ID, archive_response)
from counterlab.evidence_catalog import evidence_catalog
from counterlab.judge_release import routes


class EvidenceCatalogTests(unittest.TestCase):
    def test_catalog_covers_exactly_the_reviewed_downloads_and_separates_simulation(self):
        data = evidence_catalog(RECORDED_ID, SOURCE_RECORDED_ID, GUARDED_RECORDED_ID)
        items = data['items']
        _, exports = routes()
        self.assertEqual({item['route'] for item in items}, set(exports))
        self.assertEqual(len(items), 8)
        self.assertEqual(len({item['id'] for item in items}), 8)
        self.assertEqual(len({item['filename'] for item in items}), 8)
        self.assertFalse(data['numerical_replay_in_browser'])
        self.assertEqual(data['inference_requests_on_open'], 0)
        self.assertEqual([item['id'] for item in items if item['kind'] == 'integration'], ['guarded-source', 'source-v1'])
        self.assertTrue(all(item['label'] == 'Simulated planning' for item in items if item['kind'] == 'integration'))
        self.assertTrue(all(item['setup'] is None for item in items if item['id'] != 'source-reproduction'))
        self.assertIn('not bundled', next(item for item in items if item['id'] == 'source-reproduction')['setup'])
        self.assertIn('does not recompute', next(item for item in items if item['id'] == 'constructed-run')['expectation'])

    def test_archive_filename_cannot_introduce_headers_or_paths(self):
        for name in ('../outside.zip', 'a\r\nX-Test: bad.zip', 'https://example.com/a.zip', 'bad.txt'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                archive_response(b'fixture', name)


if __name__ == '__main__':
    unittest.main()
