import unittest

from ast_nodes import Assignment, IfStatement, PrintStatement
from codegen import generate
from parser import parse


class ParserCodegenTests(unittest.TestCase):
    def test_parses_assignment_and_print_statement(self):
        program = parse('이름 은 "철수"\n화면에 보여줘 이름')

        self.assertIsInstance(program.body[0], Assignment)
        self.assertEqual(program.body[0].target, "이름")
        self.assertEqual(program.body[0].value, '"철수"')
        self.assertIsInstance(program.body[1], PrintStatement)
        self.assertEqual(program.body[1].value, "이름")

    def test_generates_basic_assignment_and_print_code(self):
        py_code = generate(parse('이름 은 "철수"\n화면에 보여줘 이름'))

        self.assertEqual(py_code, '이름 = "철수"\nprint(이름)')

    def test_generates_if_elif_else_block(self):
        source = "\n".join([
            "만약에 말이야 점수 >= 90:",
            '    화면에 보여줘 "A"',
            "아니면 점수 >= 80:",
            '    화면에 보여줘 "B"',
            "전부 아니면:",
            '    화면에 보여줘 "C"',
        ])

        program = parse(source)
        py_code = generate(program)

        self.assertIsInstance(program.body[0], IfStatement)
        self.assertEqual(
            py_code,
            'if 점수 >= 90:\n'
            '    print("A")\n'
            'elif 점수 >= 80:\n'
            '    print("B")\n'
            'else:\n'
            '    print("C")',
        )

    def test_generates_inclusive_range_loop(self):
        source = "\n".join([
            "1 부터 3 까지 하나씩 숫자를 늘려가며 i 이라고 부르고:",
            "    화면에 보여줘 i",
        ])

        self.assertEqual(
            generate(parse(source)),
            "for i in range(1, 4):\n    print(i)",
        )


if __name__ == "__main__":
    unittest.main()
