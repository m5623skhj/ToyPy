import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.join(BASE_DIR, "Code")
OUTPUT_DIR = os.path.join(BASE_DIR, "PythonScript")

KEYWORDS = [ 
    "이런 기능이 있어", "번 반복해", "만약에 말이야", "아니면", "전부 아니면",
    "하나씩 꺼내서", "혹시 모르니까 한번 해봐", "근데 문제가 생기면", "아무튼 간에",
    "이런 설계도가 있어", "만들 때"
]

def needs_colon_hint(line):
    for kw in KEYWORDS:
        if kw in line and not line.strip().endswith(":"):
            return True
    return False

def transform_line(line):
    stripped = line.strip()
    original = stripped

    # 1. 외부 라이브러리 사용 (Import)
    # 문법: 저기 있는 [라이브러리] 좀 가져와
    stripped = re.sub(r'^저기 있는\s+(.*)\s+좀 가져와', r'import \1', stripped)

    # 2. 클래스 정의 (Class)
    # 문법: 이런 설계도가 있어 [이름]:
    stripped = re.sub(r'^이런 설계도가 있어\s+(\w+):', r'class \1:', stripped)
    # 문법: 만들 때(인자...): -> __init__ (파이썬 관례상 self 자동 추가)
    stripped = re.sub(r'^만들 때\((.*?)\):', r'def __init__(self, \1):', stripped)
    # 문법: 내 [속성] 은 [값] -> self.[속성] = [값]
    stripped = re.sub(r'^내\s+(\w+)\s+(는|은)\s+(.*)', r'self.\1 = \3', stripped)

    # 3. 함수 및 제어문
    stripped = re.sub(r'^이런 기능이 있어\s+(\w+)\((.*?)\):', r'def \1(\2):', stripped)
    stripped = re.sub(r'^(\d+)\s*번 반복해:', r'for _ in range(\1):', stripped)
    stripped = re.sub(r'^만약에 말이야\s+(.*):', r'if \1:', stripped)
    stripped = re.sub(r'^아니면\s+(.*):', r'elif \1:', stripped)
    stripped = re.sub(r'^전부 아니면:', r'else:', stripped)
    
    # 4. Foreach (리스트 반복)
    stripped = re.sub(r'^(.*)\s+에 있는 것들 하나씩 꺼내서\s+(.*)\s+이라고 부르고:', r'for \2 in \1:', stripped)

    # 5. 예외 처리
    stripped = re.sub(r'^혹시 모르니까 한번 해봐:', r'try:', stripped)
    stripped = re.sub(r'^근데 문제가 생기면:', r'except Exception:', stripped)
    stripped = re.sub(r'^아무튼 간에:', r'finally:', stripped)

    # 6. 리스트 조작 (List Operations) 및 타입 변환 (Casting)
    # 아래 기능들은 할당문(=) 내부에 포함될 수 있으므로 먼저 처리하거나 치환합니다.
    
    # 리스트 추가: [리스트] 에 [값] 도 넣어줘
    stripped = re.sub(r'(.*)\s+에\s+(.*)\s+도 넣어줘', r'\1.append(\2)', stripped)
    # 리스트 삭제: [리스트] 에서 [값] 은 빼줘
    stripped = re.sub(r'(.*)\s+에서\s+(.*)\s+은 빼줘', r'\1.remove(\2)', stripped)
    # 리스트 길이: [리스트] 가 얼마나 길어?
    stripped = re.sub(r'(.*)\s+가 얼마나 길어\?', r'len(\1)', stripped)
    
    # 타입 변환: [값] 을 숫자로 봐줘 / 글자로 봐줘
    stripped = re.sub(r'(.*)\s+를 숫자로 봐줘', r'int(\1)', stripped)
    stripped = re.sub(r'(.*)\s+를 글자로 봐줘', r'str(\1)', stripped)

    # 7. 출력 및 할당
    stripped = re.sub(r'^화면에 보여줘\s+(.*)', r'print(\1)', stripped)
    stripped = re.sub(r'^결과는\s+(.*)', r'return \1', stripped)
    stripped = re.sub(r'^(\w+)\s+(는|은)\s+값을 입력할래', r'\1 = input()', stripped)
    stripped = re.sub(r'^(\w+)\s+(는|은)\s+(.*)', r'\1 = \3', stripped)

    # 8. 논리 연산
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
