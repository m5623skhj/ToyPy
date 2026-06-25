import unittest

from Toypy import collect_expression_errors, needs_colon_hint, transform_code
from parser import parse


class ToypyTransformTests(unittest.TestCase):
    def test_transform_code_adds_runtime_traceback_and_generated_body(self):
        py_code, warnings, colon_hints, expr_errors = transform_code(
            '이름 은 "철수"\n화면에 보여줘 이름',
            dsl_name="Code/Test.dsl",
        )

        self.assertIn("__TOYPY_DSL_FILE__ = 'Code/Test.dsl'", py_code)
        self.assertIn('이름 = "철수"', py_code)
        self.assertIn("print(이름)", py_code)
        self.assertEqual(warnings, [])
        self.assertEqual(colon_hints, [])
        self.assertEqual(expr_errors, [])

    def test_transform_code_adds_time_import_for_sleep(self):
        py_code, warnings, colon_hints, expr_errors = transform_code("500 밀리초 기다려")

        self.assertIn("import time", py_code)
        self.assertIn("time.sleep(500 / 1000)", py_code)
        self.assertEqual(warnings, [])
        self.assertEqual(colon_hints, [])
        self.assertEqual(expr_errors, [])

    def test_missing_colon_hint_detects_block_statement(self):
        self.assertTrue(needs_colon_hint("만약에 말이야 점수 >= 90"))
        self.assertFalse(needs_colon_hint('화면에 보여줘 "만약에 말이야 점수 >= 90"'))

    def test_collect_expression_errors_finds_invalid_expression(self):
        errors = collect_expression_errors(parse("값 은 1 +"))

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line_no, 1)


if __name__ == "__main__":
    unittest.main()
