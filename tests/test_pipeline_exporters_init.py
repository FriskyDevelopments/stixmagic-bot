import unittest
from pipeline.exporters import source_path_to_id

class TestSourcePathToId(unittest.TestCase):
    def test_basic_filename(self):
        self.assertEqual(source_path_to_id("file.txt"), "file")

    def test_path_with_directory(self):
        self.assertEqual(source_path_to_id("/path/to/my_image.png"), "my_image")
        self.assertEqual(source_path_to_id("path/to/another_file.jpg"), "another_file")

    def test_file_without_extension(self):
        self.assertEqual(source_path_to_id("filename_only"), "filename_only")
        self.assertEqual(source_path_to_id("/path/to/filename_only"), "filename_only")

    def test_file_with_multiple_dots(self):
        self.assertEqual(source_path_to_id("archive.tar.gz"), "archive.tar")
        self.assertEqual(source_path_to_id("/path/to/my.awesome.file.txt"), "my.awesome.file")

    def test_hidden_file(self):
        self.assertEqual(source_path_to_id(".hidden_file"), ".hidden_file")
        self.assertEqual(source_path_to_id("/path/to/.hidden"), ".hidden")

    def test_empty_string(self):
        self.assertEqual(source_path_to_id(""), "")

if __name__ == '__main__':
    unittest.main()
