import os
import re
import sys
from KeyWords import KEYWORDS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.join(BASE_DIR, "Code")
OUTPUT_DIR = os.path.join(BASE_DIR, "PythonScript")

# 특정 키워드가 코드에 포함될 경우 자동으로 추가할 import 목록
AUTO_IMPORTS = {
    "밀리초 기다려":   "import time",
    "키가 눌렸어?":    "import msvcrt",
    "눌린 키가 뭐야?": "import msvcrt",
    "화면 깨끗이":     "import os",
}

def needs_colon_hint(line):
    for kw in KEYWORDS:
        if kw in line and not line.strip().endswith(":"):
            return True
    return False

def get_required_imports(code):
    """코드 내 키워드를 스캔하여 필요한 import 문을 반환 (중복 제거)"""
    required = []
    seen = set()
    for keyword, import_stmt in AUTO_IMPORTS.items():
        if keyword in code and import_stmt not in seen:
            required.append(import_stmt)
            seen.add(import_stmt)
    return required

def transform_line(line):
    stripped = line.strip()
    original = stripped

    # 1. 외부 라이브러리 사용 (Import)
    stripped = re.sub(r'^저기 있는\s+(.*)\s+좀 가져와', r'import \1', stripped)

    # 2. 클래스 정의 (Class)
    stripped = re.sub(r'^이런 설계도가 있어\s+(\w+):', r'class \1:', stripped)
    stripped = re.sub(r'^만들 때\((.*?)\):', r'def __init__(self, \1):', stripped)
    stripped = re.sub(r'^내\s+(\w+)\s+(는|은)\s+(.*)', r'self.\1 = \3', stripped)

    # 3. 사전(Dictionary) 기능
    stripped = re.sub(r'^"(.*)"\s+(?:라는|이라는)\s+사전에는\s+(.*)\s+라고 되어있어', r'\1 = \2', stripped)
    stripped = re.sub(r'만약에 말이야\s+(.*)\s+에\s+(.*)\s+(?:이|가)\s+있으면:', r'if \2 in \1:', stripped)
    stripped = re.sub(r'만약에 말이야\s+(.*)\s+에\s+(.*)\s+(?:이|가)\s+없으면:', r'if \2 not in \1:', stripped)
    stripped = re.sub(r'(.*)\s+에\s+뭐뭐\s+있어\?', r'list(\1.keys())', stripped)
    stripped = re.sub(r'(.*)\s+에\s+(.*)\s+를\s+(.*)\s+(?:으)?로\s+저장해', r'\1[\2] = \3', stripped)
    stripped = re.sub(r'(.*)\s+에서\s+(.*)\s+(?:은|는)\s+지워줘', r'del \1[\2]', stripped)
    stripped = re.sub(r'(.*)\s+에\s+(.*)\s+(?:이|가)\s+있어\?', r'\2 in \1', stripped)

    # 4. 함수 정의
    stripped = re.sub(r'^이런 기능이 있어\s+(\w+)\((.*?)\):', r'def \1(\2):', stripped)

    # 5. 반복문 - for 계열
    # 이전까지 (exclusive, 표현식 지원): 0 부터 높이+2 이전까지 하나씩 숫자를 늘려가며 y 이라고 부르고:
    stripped = re.sub(
        r'^(.*)\s+부터\s+(.*)\s+이전까지 하나씩 숫자를 늘려가며\s+(.*)\s+이라고 부르고:',
        r'for \3 in range(\1, \2):',
        stripped
    )
    # 까지 (inclusive, 숫자만): 1 부터 10 까지 하나씩 숫자를 늘려가며 i 이라고 부르고:
    stripped = re.sub(
        r'^(\d+)\s+부터\s+(\d+)\s+까지 하나씩 숫자를 늘려가며\s+(.*)\s+이라고 부르고:',
        lambda m: f'for {m.group(3)} in range({m.group(1)}, {int(m.group(2)) + 1}):',
        stripped
    )
    stripped = re.sub(r'^(\d+)\s*번 반복해:', r'for _ in range(\1):', stripped)

    # 6. 조건문
    stripped = re.sub(r'^만약에 말이야\s+(.*):', r'if \1:', stripped)
    stripped = re.sub(r'^아니면\s+(.*):', r'elif \1:', stripped)
    stripped = re.sub(r'^전부 아니면:', r'else:', stripped)

    # 7. 반복문 - while 계열
    stripped = re.sub(r'^영원히 반복해:', r'while True:', stripped)
    stripped = re.sub(r'^(.*)\s+동안 반복해:', r'while \1:', stripped)

    # 8. break / continue
    stripped = re.sub(r'^멈춰$', r'break', stripped)
    stripped = re.sub(r'^다음으로 넘어가$', r'continue', stripped)

    # 9. 반복문 - 리스트/사전 순회
    if "하나씩 꺼내서" in stripped and "," in stripped:
        stripped = re.sub(r'^(.*)\s+에 있는 것들 하나씩 꺼내서\s+(.*)\s+이라고 부르고:', r'for \2 in \1.items():', stripped)
    else:
        stripped = re.sub(r'^(.*)\s+에 있는 것들 하나씩 꺼내서\s+(.*)\s+이라고 부르고:', r'for \2 in \1:', stripped)

    # 10. 예외 처리
    stripped = re.sub(r'^혹시 모르니까 한번 해봐:', r'try:', stripped)
    stripped = re.sub(r'^근데 문제가 생기면:', r'except Exception:', stripped)
    stripped = re.sub(r'^아무튼 간에:', r'finally:', stripped)

    # 11. 리스트 조작 및 타입 변환
    stripped = re.sub(r'^(.*)\s+맨 앞에\s+(.*)\s+끼워줘$', r'\1.insert(0, \2)', stripped)
    stripped = re.sub(r'^(.*)\s+끝 잘라줘$', r'\1.pop()', stripped)
    stripped = re.sub(r'(.*)\s+에\s+(.*)\s+도 넣어줘', r'\1.append(\2)', stripped)
    stripped = re.sub(r'(.*)\s+에서\s+(.*)\s+은 빼줘', r'\1.remove(\2)', stripped)
    stripped = re.sub(r'(.*)\s+가 얼마나 길어\?', r'len(\1)', stripped)
    stripped = re.sub(r'(.*)\s+를 숫자로 봐줘', r'int(\1)', stripped)
    stripped = re.sub(r'(.*)\s+를 글자로 봐줘', r'str(\1)', stripped)

    # 12. 화면 출력
    # 화면 깨끗이 — 화면에 보여줘보다 반드시 먼저 처리
    if stripped == "화면 깨끗이":
        stripped = 'os.system("cls" if os.name == "nt" else "clear")'
    # 이어서 출력 (end="" — 줄바꿈 없음)
    stripped = re.sub(r'^화면에 이어서 보여줘\s+(.*)', r'print(\1, end="")', stripped)
    # 줄 바꿔 (빈 print)
    if stripped == "줄 바꿔":
        stripped = "print()"
    # 일반 출력
    stripped = re.sub(r'^화면에 보여줘\s+(.*)', r'print(\1)', stripped)

    # 13. 함수 반환 및 변수 할당
    stripped = re.sub(r'^결과는\s+(.*)', r'return \1', stripped)
    stripped = re.sub(r'^(\w+)\s+(는|은)\s+값을 입력할래', r'\1 = input()', stripped)
    stripped = re.sub(r'^(\w+)\s+(는|은)\s+(.*)', r'\1 = \3', stripped)

    # 14. 비동기 입력 (msvcrt, Windows) — 할당 변환 이후에 적용
    stripped = re.sub(r'키가 눌렸어\?', r'msvcrt.kbhit()', stripped)
    stripped = re.sub(r'눌린 키가 뭐야\?', r"msvcrt.getch().decode('utf-8', errors='ignore')", stripped)

    # 15. 시간 지연: N 밀리초 기다려 → time.sleep(N / 1000)
    stripped = re.sub(r'^([\w.]+)\s+밀리초 기다려$', r'time.sleep(\1 / 1000)', stripped)

    # 16. 논리 연산자
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

        if stripped_line.startswith("여기서 부터"):
            in_multiline_comment = True
            result.append(' ' * indent + '"""')
            continue
        if stripped_line.startswith("여기까지는 상관 없는 이야기인데"):
            in_multiline_comment = False
            result.append(' ' * indent + '"""')
            continue
        if in_multiline_comment:
            result.append(' ' * indent + stripped_line)
            continue
        if stripped_line.startswith("이건 상관 없는 이야기인데"):
            comment = stripped_line.replace("이건 상관 없는 이야기인데", "").strip()
            result.append(' ' * indent + f"# {comment}")
            continue

        original, transformed = transform_line(line)

        if original == transformed:
            for kw in KEYWORDS:
                if kw in original:
                    warnings.append((idx + 1, line))
                    break

        if needs_colon_hint(line):
            colon_hints.append((idx + 1, line))

        result.append(' ' * indent + transformed)

    required_imports = get_required_imports(code)
    transformed_imports = [l.strip() for l in result if l.strip().startswith("import ")]
    auto_to_add = [imp for imp in required_imports if imp not in transformed_imports]
    if auto_to_add:
        result = auto_to_add + [''] + result

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
            print(f" → {line_no}번째 줄: {content.strip()}")
    if colon_hints:
        print("\n💡 문법 힌트:")
        for line_no, content in colon_hints:
            print(f" → {line_no}번째 줄: ':' 빠진 것 같습니다")
            print(f"    {content.strip()}")
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