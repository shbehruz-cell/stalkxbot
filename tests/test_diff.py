import unittest
from app.handlers import make_new_version_diff


class DiffTests(unittest.TestCase):
    def test_changed_word_is_bold(self):
        result = make_new_version_diff("Salom dunyo", "Salom olam", 1000)
        self.assertIn("<b>olam</b>", result)
        self.assertNotIn("<b>Salom</b>", result)

    def test_deleted_word_is_ellipsis(self):
        result = make_new_version_diff("Salom katta dunyo", "Salom dunyo", 1000)
        self.assertIn("<b>...</b>", result)

    def test_html_is_escaped(self):
        result = make_new_version_diff("a", "<b>", 1000)
        self.assertIn("&lt;b&gt;", result)


if __name__ == "__main__":
    unittest.main()
