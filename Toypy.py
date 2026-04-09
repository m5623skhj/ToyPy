import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.join(BASE_DIR, "Code")
OUTPUT_DIR = os.path.join(BASE_DIR, "PythonScript")

KEYWORDS = [
    "이런 기능이 있어",
    "번 반복해",
    "만약에 말이야",
    "아니면",
    "전부 아니면"
]


def needs_colon_hint(line):
    for kw in KEYWORDS:
        if kw in line and not line.strip().endswith(":"):
            return True
    return False


def transform_line(line):
    stripped = line.strip()
    original = stripped

    stripped = re.sub(r'^이런 기능이 있어\s+(\w+)\((.*?)\):', r'def \1(\2):', stripped)
    stripped = re.sub(r'^(\d+)\s*번 반복해:', r'for _ in range(\1):', stripped)

    stripped = re.sub(r'^만약에 말이야\s+(.*):', r'if \1:', stripped)
    stripped = re.sub(r'^아니면\s+(.*):', r'elif \1:', stripped)
    stripped = re.sub(r'^전부 아니면:', r'else:', stripped)

    stripped = re.sub(r'^화면에 보여줘\s+(.*)', r'print(\1)', stripped)
    stripped = re.sub(r'^결과는\s+(.*)', r'return \1', stripped)

    stripped = re.sub(r'^(\w+)\s+(는|은)\s+값을 입력할래', r'\1 = input()', stripped)
    stripped = re.sub(r'^(\w+)\s+(는|은)\s+(.*)', r'\1 = \3', stripped)

    stripped = stripped.replace("그리고", "and")
    stripped = stripped.replace("또는", "or")
    stripped = stripped.replace("아님", "not")

    stripped = stripped.replace("진짜야", "True")
    stripped = stripped.replace("가짜야", "False")

    return original, stripped


def transform_code(code):
    result = []
    warnings = []
    colon_hints = []

    lines = code.split('\n')
    in_multiline_comment = False

    for idx, line in enumerate(lines):
        stripped_line = line.strip()
        indent = len(line) - len(line.lstrip())

        # 🔥 다중행 주석 시작
        if stripped_line.startswith("여기서 부터"):
            in_multiline_comment = True
            result.append(' ' * indent + '"""')
            continue

        # 🔥 다중행 주석 끝
        if stripped_line.startswith("여기까지는 상관 없는 이야기인데"):
            in_multiline_comment = False
            result.append(' ' * indent + '"""')
            continue

        # 🔥 다중행 주석 내부
        if in_multiline_comment:
            result.append(' ' * indent + stripped_line)
            continue

        # 🔥 단일행 주석
        if stripped_line.startswith("이건 상관 없는 이야기인데"):
            comment = stripped_line.replace("이건 상관 없는 이야기인데", "").strip()
            result.append(' ' * indent + f"# {comment}")
            continue

        original, transformed = transform_line(line)

        # 변환 실패 감지
        if original == transformed:
            for kw in KEYWORDS:
                if kw in original:
                    warnings.append((idx + 1, line))
                    break

        # 콜론 힌트
        if needs_colon_hint(line):
            colon_hints.append((idx + 1, line))

        result.append(' ' * indent + transformed)

    return '\n'.join(result), warnings, colon_hints


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def process_file(filepath):
    filename = os.path.basename(filepath)
    name, _ = os.path.splitext(filename)

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    py_code, warnings, colon_hints = transform_code(code)

    output_path = os.path.join(OUTPUT_DIR, name + ".py")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(py_code)

    print(f"\n✔ [{filename}] → [{name}.py] 생성 완료")

    print("\n📄 변환된 Python 코드:")
    print("----------------------------------")
    print(py_code)
    print("----------------------------------")

    if warnings:
        print("\n⚠️ 변환되지 않은 의심 라인:")
        for line_no, content in warnings:
            print(f"  → {line_no}번째 줄: {content.strip()}")

    if colon_hints:
        print("\n💡 문법 힌트:")
        for line_no, content in colon_hints:
            print(f"  → {line_no}번째 줄: ':' 빠진 것 같습니다")
            print(f"     {content.strip()}")

    if not warnings and not colon_hints:
        print("\n✔ 전체 변환 정상")


def main():
    ensure_output_dir()

    if not os.path.exists(CODE_DIR):
        print("Code 폴더가 없습니다.")
        return

    files = [f for f in os.listdir(CODE_DIR) if f.endswith(".dsl")]

    if not files:
        print("Code 폴더에 .dsl 파일이 없습니다.")
        return

    if len(sys.argv) > 1:
        target = sys.argv[1]
        filepath = os.path.join(CODE_DIR, target)

        if not os.path.exists(filepath):
            print("해당 파일이 없습니다.")
            return

        process_file(filepath)
    else:
        for file in files:
            filepath = os.path.join(CODE_DIR, file)
            process_file(filepath)


if __name__ == "__main__":
    main()