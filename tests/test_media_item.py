import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest

from media_item import Category, MediaItem, Status


class TestMediaItem(unittest.TestCase):
    def test_create_valid_item(self):
        item = MediaItem(title="Dune", category="Book", status="Completed", rating=5)
        self.assertEqual(item.title, "Dune")
        self.assertEqual(item.category, Category.BOOK)
        self.assertEqual(item.status, Status.COMPLETED)
        self.assertEqual(item.rating, 5)
        self.assertFalse(item.watched)

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            MediaItem(title="   ", category="Book")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            MediaItem(title="Dune", category="Podcast")

    def test_rating_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            MediaItem(title="Dune", category="Book", rating=10)

    def test_rating_non_numeric_rejected(self):
        with self.assertRaises(ValueError):
            MediaItem(title="Dune", category="Book", rating="high")

    def test_rating_optional(self):
        item = MediaItem(title="Dune", category="Book", rating=None)
        self.assertIsNone(item.rating)

    def test_toggle_watched(self):
        item = MediaItem(title="Dune", category="Book")
        self.assertFalse(item.watched)
        item.toggle_watched()
        self.assertTrue(item.watched)
        item.toggle_watched()
        self.assertFalse(item.watched)

    def test_round_trip_dict(self):
        item = MediaItem(
            title="Dune",
            category="Book",
            status="In Progress",
            rating=4,
            notes="Great so far",
            watched=True,
            image_path="cover.jpg",
            item_id=3,
        )
        restored = MediaItem.from_dict(item.to_dict())
        self.assertEqual(restored.title, item.title)
        self.assertEqual(restored.category, item.category)
        self.assertEqual(restored.status, item.status)
        self.assertEqual(restored.rating, item.rating)
        self.assertEqual(restored.notes, item.notes)
        self.assertEqual(restored.watched, item.watched)
        self.assertEqual(restored.image_path, item.image_path)
        self.assertEqual(restored.item_id, item.item_id)


if __name__ == "__main__":
    unittest.main()
