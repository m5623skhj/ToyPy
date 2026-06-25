import unittest

from expr_parser import diagnose, transform


class ExprParserTests(unittest.TestCase):
    def test_transforms_length_expression(self):
        self.assertEqual(transform("이름 가 얼마나 길어?"), "len(이름)")

    def test_transforms_random_range_expression(self):
        self.assertEqual(transform("1 부터 6까지 무작위"), "random.randint(1, 6)")

    def test_preserves_python_arithmetic_precedence(self):
        self.assertEqual(transform("1 + 2 * 3"), "1 + 2 * 3")

    def test_diagnose_reports_incomplete_expression(self):
        issue = diagnose("1 +")

        self.assertIsNotNone(issue)
        self.assertEqual(issue.token, "EOF")
        self.assertGreaterEqual(issue.column, 1)


if __name__ == "__main__":
    unittest.main()
