import unittest
from check_changesets import validate


class ChangesetTests(unittest.TestCase):
    def test_valid(self):
        for bump in ("patch", "minor", "major"):
            self.assertEqual(validate(f"---\ndefault: {bump}\n---\n\nA change.\n"), [])

    def test_unknown_or_quoted_package(self):
        for key in ("python", "swift", '"default"', "'default'"):
            self.assertTrue(validate(f"---\n{key}: patch\n---\nA change."))

    def test_malformed_or_empty(self):
        for text in ("", "A change", "---\ndefault: patch", "---\n---\nA change",
                     "---\ndefault: invalid\n---\nA change", "---\ndefault: patch\n---",
                     "---\ndefault: patch\ndefault: major\n---\nA change"):
            self.assertTrue(validate(text), text)


if __name__ == "__main__":
    unittest.main()
