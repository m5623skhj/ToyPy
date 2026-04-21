# -*- coding: utf-8 -*-
import os
import sys
import traceback
from KeyWords import BLOCK_KEYWORDS
from parser import parse
from codegen import generate
from ast_nodes import RawExpression, Program

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.join(BASE_DIR, "Code")
OUTPUT_DIR = os.path.join(BASE_DIR, "PythonScript")

AUTO_IMPORTS = {
    "밀리초 기다려":          "import time",
    "프레임 유지":            "import time",
    "키가 눌렸어?":           "import msvcrt",
    "눌린 키가 뭐야?":        "import msvcrt",
    "화면 깨끗이":            "import os",
    "부드럽게 그릴 준비해":   "import sys",
    "프레임 시작":            "import sys",
    "프레임 그려줘":          "import sys",
    "프레임에 보여줘":        "import sys",
    "프레임에 이어서 보여줘": "import sys",
    "프레임 줄 바꿔":         "import sys",
    "위치에 써줘":            "import sys",
    "무작위":                 "import random",
}

AUTO_HELPERS = {
    "눌린 키가 뭐야?": (
        "def _get_key():\n"
        "    c = msvcrt.getch()\n"
        "    if c in (b'\\xe0', b'\\x00'):\n"
        "        k = msvcrt.getch()\n"
        "        return {b'H': 'up', b'P': 'down', b'K': 'left', b'M': 'right'}.get(k, '')\n"
        "    return c.decode('utf-8', errors='ignore')"
    ),
    "프레임 유지": (
        "def _frame_wait(fps):\n"
        "    now = time.perf_counter()\n"
        "    last = getattr(_frame_wait, '_last', now)\n"
        "    target = last + 1.0 / fps\n"
        "    if now < target:\n"
        "        time.sleep(target - now)\n"
        "    _frame_wait._last = max(now, target)"
    ),
}


def needs_colon_hint(line):
    """블록 구문 키워드가 있는데 ':'로 끝나지 않는 줄 감지"""
    stripped = line.strip()
    if not stripped or stripped.startswith("이건 상관 없는 이야기인데"):
        return False
    for kw in BLOCK_KEYWORDS:
        if kw in stripped and not stripped.endswith(":"):
            return True
    return False


def collect_raw_warnings(ast_node):
    """AST에서 RawExpression 노드를 찾아 경고 목록 생성"""
    warnings = []
    if isinstance(ast_node, Program):
        for child in ast_node.body:
            warnings.extend(collect_raw_warnings(child))
    elif isinstance(ast_node, RawExpression):
        warnings.append((ast_node.line, ast_node.source))
    else:
        for attr in ('body', 'else_body', 'except_body', 'finally_body'):
            children = getattr(ast_node, attr, None)
            if isinstance(children, list):
                for child in children:
                    warnings.extend(collect_raw_warnings(child))
        elifs = getattr(ast_node, 'elifs', None)
        if isinstance(elifs, list):
            for elif_clause in elifs:
                warnings.extend(collect_raw_warnings(elif_clause))
    return warnings


def get_required_imports(code):
    required = []
    seen = set()
    for keyword, import_stmt in AUTO_IMPORTS.items():
        if keyword in code and import_stmt not in seen:
            required.append(import_stmt)
            seen.add(import_stmt)
    return required


def get_required_helpers(code):
    required = []
    seen = set()
    for keyword, helper_src in AUTO_HELPERS.items():
        if keyword in code and helper_src not in seen:
            required.append(helper_src)
            seen.add(helper_src)
    return required


def transform_code(code):
    try:
        ast = parse(code)
    except Exception as e:
        raise RuntimeError(f"파싱 단계에서 오류 발생: {e}") from e

    try:
        py_code = generate(ast)
    except Exception as e:
        raise RuntimeError(f"코드 생성 단계에서 오류 발생: {e}") from e

    # RawExpression 경고 (한글 포함 줄만)
    warnings = []
    for line_no, source in collect_raw_warnings(ast):
        if any('\uac00' <= ch <= '\ud7a3' for ch in source):
            warnings.append((line_no, source))

    # 콜론 힌트
    colon_hints = []
    for idx, line in enumerate(code.split('\n')):
        if needs_colon_hint(line):
            colon_hints.append((idx + 1, line))

    # 자동 import / helper 주입
    required_imports = get_required_imports(code)
    existing_imports = [l.strip() for l in py_code.split('\n') if l.strip().startswith("import ")]
    auto_to_add = [imp for imp in required_imports if imp not in existing_imports]
    required_helpers = get_required_helpers(code)

    prefix_lines = []
    if auto_to_add:
        prefix_lines += auto_to_add + ['']
    if required_helpers:
        prefix_lines += required_helpers + ['']
    if prefix_lines:
        py_code = '\n'.join(prefix_lines) + '\n' + py_code

    return py_code, warnings, colon_hints


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def process_file(filepath):
    filename = os.path.basename(filepath)
    name, _ = os.path.splitext(filename)

    # 파일 읽기 (인코딩 폴백)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="cp949") as f:
                code = f.read()
            print(f"\n⚠️  [{filename}] CP949로 읽었습니다. UTF-8 저장을 권장합니다.")
        except Exception as e:
            print(f"\n❌ [{filename}] 파일 읽기 실패: {e}")
            return
    except Exception as e:
        print(f"\n❌ [{filename}] 파일 읽기 실패: {e}")
        return

    if not code.strip():
        print(f"\n⚠️  [{filename}] 파일이 비어있습니다. 건너뜁니다.")
        return

    # 변환
    try:
        py_code, warnings, colon_hints = transform_code(code)
    except RuntimeError as e:
        print(f"\n❌ [{filename}] 변환 실패: {e}")
        return
    except Exception as e:
        print(f"\n❌ [{filename}] 예기치 않은 오류:")
        traceback.print_exc()
        return

    # 저장
    output_path = os.path.join(OUTPUT_DIR, name + ".py")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(py_code)
    except Exception as e:
        print(f"\n❌ [{filename}] 파일 저장 실패: {e}")
        return

    # 결과 출력
    print(f"\n{'='*50}")
    print(f"  ✔ [{filename}] → [{name}.py] 생성 완료")
    print(f"{'='*50}")
    print(f"\n📄 변환된 Python 코드:")
    print("─" * 40)
    print(py_code)
    print("─" * 40)

    has_issues = False

    if warnings:
        has_issues = True
        print(f"\n⚠️  변환되지 않은 의심 라인 ({len(warnings)}건):")
        for line_no, content in warnings:
            print(f"   {line_no}번째 줄 → {content.strip()}")
        print("   💡 한글 문법이 맞는지 확인하세요. 오타가 있으면 그대로 출력됩니다.")

    if colon_hints:
        has_issues = True
        print(f"\n💡 문법 힌트 ({len(colon_hints)}건):")
        for line_no, content in colon_hints:
            print(f"   {line_no}번째 줄 → ':' 가 빠진 것 같습니다")
            print(f"      {content.strip()}")

    if not has_issues:
        print("\n✔ 전체 변환 정상 — 문제가 발견되지 않았습니다.")

    print()


def main():
    ensure_output_dir()

    if not os.path.exists(CODE_DIR):
        print(f"❌ Code 폴더가 없습니다: {CODE_DIR}")
        print(f"   → 해당 폴더를 만들고 .dsl 파일을 넣어주세요.")
        return

    files = sorted([f for f in os.listdir(CODE_DIR) if f.endswith(".dsl")])
    if not files:
        print(f"❌ Code 폴더에 .dsl 파일이 없습니다.")
        print(f"   → .dsl 확장자로 DSL 코드를 작성해주세요.")
        return

    if len(sys.argv) > 1:
        target = sys.argv[1]
        if not target.endswith(".dsl"):
            target += ".dsl"
        filepath = os.path.join(CODE_DIR, target)
        if not os.path.exists(filepath):
            print(f"❌ 파일을 찾을 수 없습니다: {target}")
            print(f"   → Code 폴더에 있는 파일:")
            for f in files:
                print(f"      • {f}")
            return
        process_file(filepath)
    else:
        print(f"📂 {len(files)}개 파일 변환 시작...\n")
        for file in files:
            filepath = os.path.join(CODE_DIR, file)
            process_file(filepath)
        print(f"\n{'='*50}")
        print(f"  📦 전체 {len(files)}개 파일 처리 완료")
        print(f"  📁 출력: {OUTPUT_DIR}")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()