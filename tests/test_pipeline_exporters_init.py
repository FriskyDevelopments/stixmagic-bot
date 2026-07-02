import unittest

from pipeline.exporters import source_path_to_id


class TestSourcePathToId(unittest.TestCase):
    def test_basic_filename(self):
        self.assertEqual(source_path_to_id("file.txt"), "file")

    def test_path_with_directories(self):
        self.assertEqual(source_path_to_id("/a/b/c/file.txt"), "file")

    def test_filename_with_no_extension(self):
        self.assertEqual(source_path_to_id("file"), "file")

    def test_filename_with_multiple_extensions(self):
        self.assertEqual(source_path_to_id("file.tar.gz"), "file.tar")

    def test_relative_path(self):
        self.assertEqual(source_path_to_id("dir/subdir/file.txt"), "file")


if __name__ == "__main__":
    unittest.main()
