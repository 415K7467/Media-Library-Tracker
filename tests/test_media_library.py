import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from media_item import MediaItem
from media_library import MediaLibrary, MediaLibraryError


class TestMediaLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.tmp_dir, "library.json")
        self.library = MediaLibrary(self.storage_path)
        self.library.load()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_missing_file_starts_empty(self):
        self.assertEqual(self.library.items, [])

    def test_add_item_persists_to_disk(self):
        item = MediaItem(title="Dune", category="Book")
        self.library.add_item(item)

        reloaded = MediaLibrary(self.storage_path)
        reloaded.load()
        self.assertEqual(len(reloaded.items), 1)
        self.assertEqual(reloaded.items[0].title, "Dune")
        self.assertEqual(reloaded.items[0].item_id, item.item_id)

    def test_add_item_assigns_incrementing_ids(self):
        first = self.library.add_item(MediaItem(title="Dune", category="Book"))
        second = self.library.add_item(MediaItem(title="Arrival", category="Movie"))
        self.assertEqual(first.item_id, 1)
        self.assertEqual(second.item_id, 2)

    def test_delete_item_removes_it(self):
        item = self.library.add_item(MediaItem(title="Dune", category="Book"))
        self.library.delete_item(item.item_id)
        self.assertEqual(self.library.items, [])

    def test_delete_unknown_item_raises(self):
        with self.assertRaises(MediaLibraryError):
            self.library.delete_item(999)

    def test_toggle_watched(self):
        item = self.library.add_item(MediaItem(title="Dune", category="Book"))
        self.assertFalse(item.watched)
        self.library.toggle_watched(item.item_id)
        self.assertTrue(self.library.get_item(item.item_id).watched)

    def test_search_by_title(self):
        self.library.add_item(MediaItem(title="Dune", category="Book"))
        self.library.add_item(MediaItem(title="Arrival", category="Movie"))
        results = self.library.search("dune")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Dune")

    def test_search_empty_query_returns_all(self):
        self.library.add_item(MediaItem(title="Dune", category="Book"))
        self.library.add_item(MediaItem(title="Arrival", category="Movie"))
        self.assertEqual(len(self.library.search("")), 2)

    def test_search_specific_field(self):
        self.library.add_item(MediaItem(title="Dune", category="Book", notes="desert planet"))
        results = self.library.search("desert", field="notes")
        self.assertEqual(len(results), 1)
        results_wrong_field = self.library.search("desert", field="title")
        self.assertEqual(results_wrong_field, [])

    def test_sort_by_title(self):
        self.library.add_item(MediaItem(title="Zelda", category="Game"))
        self.library.add_item(MediaItem(title="Arrival", category="Movie"))
        sorted_items = self.library.sort(self.library.items, "title")
        self.assertEqual([i.title for i in sorted_items], ["Arrival", "Zelda"])

    def test_sort_ratings_none_last(self):
        self.library.add_item(MediaItem(title="No rating", category="Book", rating=None))
        self.library.add_item(MediaItem(title="Rated", category="Book", rating=3))
        sorted_items = self.library.sort(self.library.items, "rating")
        self.assertEqual(sorted_items[0].title, "Rated")
        self.assertEqual(sorted_items[1].title, "No rating")

    def test_sort_unknown_field_raises(self):
        with self.assertRaises(MediaLibraryError):
            self.library.sort(self.library.items, "unknown_field")

    def test_statistics(self):
        self.library.add_item(MediaItem(title="Dune", category="Book", watched=True))
        self.library.add_item(MediaItem(title="Arrival", category="Movie", watched=False))
        self.library.add_item(MediaItem(title="Foundation", category="Book", watched=True))
        stats = self.library.statistics()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["watched"], 2)
        self.assertEqual(stats["unwatched"], 1)
        self.assertEqual(stats["by_category"], {"Book": 2, "Movie": 1})

    def test_export_csv(self):
        self.library.add_item(MediaItem(title="Dune", category="Book", rating=5))
        csv_path = os.path.join(self.tmp_dir, "export.csv")
        self.library.export_csv(csv_path)

        with open(csv_path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Dune")
        self.assertEqual(rows[0]["rating"], "5")

    def test_load_corrupted_json_raises(self):
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            handle.write("{not valid json")
        broken_library = MediaLibrary(self.storage_path)
        with self.assertRaises(MediaLibraryError):
            broken_library.load()

    def test_load_skips_invalid_records(self):
        records = [
            {"title": "Valid", "category": "Book", "status": "Planned", "item_id": 1},
            {"title": "", "category": "Book", "status": "Planned", "item_id": 2},
        ]
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle)

        recovered = MediaLibrary(self.storage_path)
        recovered.load()
        self.assertEqual(len(recovered.items), 1)
        self.assertEqual(recovered.items[0].title, "Valid")


if __name__ == "__main__":
    unittest.main()
