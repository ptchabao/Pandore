import unittest
from pathlib import Path


class PandoreApiTests(unittest.TestCase):
    def test_catalog_is_discoverable(self):
        archive_root = Path(__file__).resolve().parents[1] / "downloads" / "TikTok直播"
        self.assertTrue(archive_root.exists(), "The archive folder should exist")
        media_files = list(archive_root.rglob("*"))
        self.assertTrue(any(p.is_file() for p in media_files), "There should be at least one archived file")


if __name__ == "__main__":
    unittest.main()
