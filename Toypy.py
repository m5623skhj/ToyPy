# -*- coding: utf-8 -*-
import os
import re
import sys
import traceback
from typing import Optional
from KeyWords import BLOCK_KEYWORDS, STATEMENT_KEYWORDS, EXPR_KEYWORDS
from parser import parse
from codegen import generate
from ast_nodes import (
    Program, RawExpression, Assignment, SelfAssignment, ReturnStatement,
    IfStatement, ForRange, ForEach, WhileStatement, PrintStatement,
    ColorPrintStatement, DictDefStatement, DictStoreStatement,
    DictDeleteStatement, ListAppendStatement, ListRemoveStatement,
    ListInsertStatement, ListPopStatement, FrameAppendStatement,
    CursorWriteStatement, SleepStatement, FpsControlStatement,
)
from dsl_error import DSLError, ErrorKind
from expr_parser import diagnose as diagnose_expr, ParseIssue

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

# ── 키워드별 올바른 예시 ────────────────────────────────────────────────
# _find_nearest_keyword()가 반환하는 값(= KeyWords.py의 실제 키워드)을 키로 사용.
# 키가 없으면 예시 없이 suggestion만 표시된다.
_KEYWORD_EXAMPLE: dict[str, str] = {
    # ── 출력 ──────────────────────────────────────────────────────
    "화면에 보여줘":            "화면에 보여줘 변수명",
    "화면에 이어서 보여줘":     "화면에 이어서 보여줘 변수명",
    "줄 바꿔":                  "줄 바꿔",
    "으로 보여줘":              "빨간색으로 보여줘 변수명",
    "으로 이어서 보여줘":       "빨간색으로 이어서 보여줘 변수명",

    # ── 조건 ──────────────────────────────────────────────────────
    "만약에 말이야":            "만약에 말이야 조건:",
    "아니면":                   "아니면 조건:",
    "전부 아니면":              "전부 아니면:",

    # ── 반복 ──────────────────────────────────────────────────────
    "번 반복해":                "3번 반복해:",
    "영원히 반복해":            "영원히 반복해:",
    "동안 반복해":              "조건 동안 반복해:",
    "하나씩 꺼내서":            "목록 에 있는 것들 하나씩 꺼내서 항목 이라고 부르고:",
    "숫자를 늘려가며":          "1 부터 10 이전까지 하나씩 숫자를 늘려가며 i 이라고 부르고:",
    "이전까지":                 "1 부터 10 이전까지 하나씩 숫자를 늘려가며 i 이라고 부르고:",

    # ── 흐름 제어 ─────────────────────────────────────────────────
    "멈춰":                     "멈춰",
    "다음으로 넘어가":          "다음으로 넘어가",

    # ── 함수 / 클래스 ──────────────────────────────────────────────
    "이런 기능이 있어":         "이런 기능이 있어 함수명(매개변수):",
    "이런 설계도가 있어":       "이런 설계도가 있어 클래스명:",
    "만들 때":                  "만들 때(self, 인자):",
    "결과는":                   "결과는 반환값",

    # ── 예외 처리 ─────────────────────────────────────────────────
    "혹시 모르니까 한번 해봐":  "혹시 모르니까 한번 해봐:",
    "근데 문제가 생기면":       "근데 ValueError 문제가 생기면:",
    "아무튼 간에":              "아무튼 간에:",

    # ── 변수 / 입력 ───────────────────────────────────────────────
    "값을 입력할래":            "변수명 은 값을 입력할래",

    # ── 리스트 ────────────────────────────────────────────────────
    "도 넣어줘":                "목록 에 값 도 넣어줘",
    "은 빼줘":                  "목록 에서 값 은 빼줘",
    "맨 앞에":                  "목록 맨 앞에 값 끼워줘",
    "끝 잘라줘":                "목록 끝 잘라줘",

    # ── 사전 ──────────────────────────────────────────────────────
    "으로 저장해":              '사전 에 "키" 를 값 으로 저장해',
    "로 저장해":                '사전 에 "키" 를 값 으로 저장해',
    "은 지워줘":                '사전 에서 "키" 은 지워줘',
    "는 지워줘":                '사전 에서 "키" 는 지워줘',

    # ── 파일 ──────────────────────────────────────────────────────
    "읽기로 열어서":            '파일 "파일명.txt" 읽기로 열어서 f 라고 부르고:',
    "쓰기로 열어서":            '파일 "파일명.txt" 쓰기로 열어서 f 라고 부르고:',
    "이어쓰기로 열어서":        '파일 "파일명.txt" 이어쓰기로 열어서 f 라고 부르고:',

    # ── 화면 / 프레임 ─────────────────────────────────────────────
    "화면 깨끗이":              "화면 깨끗이",
    "부드럽게 그릴 준비해":     "부드럽게 그릴 준비해",
    "프레임 시작":              "프레임 시작",
    "프레임 그려줘":            "프레임 그려줘",
    "프레임 줄 바꿔":           "프레임 줄 바꿔",
    "프레임에 보여줘":          "프레임에 보여줘 변수명",
    "프레임에 이어서 보여줘":   "프레임에 이어서 보여줘 변수명",
    "위치에 써줘":              "(열, 행) 위치에 써줘 변수명",

    # ── 시간 ──────────────────────────────────────────────────────
    "밀리초 기다려":            "500 밀리초 기다려",
    "프레임 유지":              "초당 30 프레임 유지",

    # ── 표현식 키워드 ─────────────────────────────────────────────
    "를 숫자로 봐줘":           "변수 를 숫자로 봐줘",
    "를 글자로 봐줘":           "변수 를 글자로 봐줘",
    "가 얼마나 길어?":          "목록 가 얼마나 길어?",
    "에 뭐뭐 있어?":            "사전 에 뭐뭐 있어?",
    "키가 눌렸어?":             "키가 눌렸어?",
    "눌린 키가 뭐야?":          "눌린 키가 뭐야?",
    "받아서":                   "x 받아서 x * x 주는 것",
    "주는 것":                  "x 받아서 x * x 주는 것",
    "무작위":                   "1 부터 10 무작위",
    "번째부터":                 "목록 의 2번째부터 5번째까지",
    "번째까지":                 "목록 의 2번째부터 5번째까지",
    "그리고":                   "조건1 그리고 조건2",
    "또는":                     "조건1 또는 조건2",
    "아님":                     "아님 조건",
    "진짜야":                   "변수 는 진짜야",
    "가짜야":                   "변수 는 가짜야",
}


# ──────────────────────────────────────────────────────────────
# 에러 생성 헬퍼
# ──────────────────────────────────────────────────────────────

def _find_nearest_keyword(text: str) -> Optional[str]:
    """
    입력 줄과 가장 유사한 DSL 키워드를 반환.

    1차: BLOCK/STATEMENT/EXPR 키워드 전체에서 줄 안에 부분 포함되는 것을 반환.
         길이 긴 키워드부터 확인해 오탐을 줄인다.
    2차: 공통 글자 수 기준 최근접. 단, 공통 글자가 2개 미만이면 None 반환
         (관련 없는 키워드를 억지로 추천하지 않음).
    """
    all_kw = BLOCK_KEYWORDS + STATEMENT_KEYWORDS + EXPR_KEYWORDS
    text_stripped = text.strip()

    # 1차: 긴 키워드부터 부분 포함 확인
    for kw in sorted(all_kw, key=len, reverse=True):
        if kw in text_stripped:
            return kw

    # 2차: 공통 고유 글자 수 기준
    def common_chars(a: str, b: str) -> int:
        return sum(1 for c in set(a) if c in b)

    scored = [(common_chars(kw, text_stripped), kw) for kw in all_kw]
    best_score, best_kw = max(scored, key=lambda x: x[0], default=(0, None))

    # 공통 글자 2개 미만이면 추천하지 않음
    return best_kw if best_score >= 2 else None


def _make_raw_error(line_no: int, source: str) -> DSLError:
    """인식 못한 줄 → 구체적인 에러 객체 생성"""
    specialized = _make_statement_pattern_error(line_no, source)
    if specialized is not None:
        return specialized

    nearest = _find_nearest_keyword(source)
    suggestion = (
        f"'{nearest}' 문법을 쓰려고 하신 건 아닌가요?"
        if nearest else
        "ToyPy 문법이 맞는지 확인하세요."
    )
    hint = _KEYWORD_EXAMPLE.get(nearest, "") if nearest else ""

    return DSLError(
        kind=ErrorKind.UNKNOWN_COMMAND,
        line_no=line_no,
        source_line=source,
        message="어떤 ToyPy 문법과도 일치하지 않는 줄입니다.",
        suggestion=suggestion,
        hint_code=hint,
    )


def _make_statement_pattern_error(line_no: int, source: str) -> Optional[DSLError]:
    """지원하는 문장형 DSL과 유사하지만 형식이 틀린 줄을 더 구체적으로 안내한다."""
    stripped = source.strip()
    statement_patterns = [
        (
            "화면에 보여줘",
            "출력 문장 형식이 어긋났습니다.",
            "뒤에 출력할 값을 한 칸 띄워서 적어주세요.",
            '화면에 보여줘 "안녕"',
        ),
        (
            "화면에 이어서 보여줘",
            "이어쓰기 출력 문장 형식이 어긋났습니다.",
            "뒤에 이어서 출력할 값을 적어주세요.",
            '화면에 이어서 보여줘 "계속"',
        ),
        (
            "파일",
            "파일 열기 문장 형식이 어긋났습니다.",
            "'파일 ... 읽기/쓰기/이어쓰기로 열어서 ... 라고 부르고:' 형식을 확인해주세요.",
            '파일 "demo.txt" 읽기로 열어서 f 라고 부르고:',
        ),
        (
            "저장해",
            "사전 저장 문장 형식이 어긋났습니다.",
            "'사전 에 키 를 값 으로 저장해' 순서를 확인해주세요.",
            '사전 에 "키" 를 값 으로 저장해',
        ),
        (
            "보여줘",
            "출력 관련 문장 형식이 어긋났습니다.",
            "'화면에 보여줘 ...' 또는 '프레임에 보여줘 ...' 형식을 확인해주세요.",
            '화면에 보여줘 값',
        ),
    ]

    for marker, message, suggestion, hint in statement_patterns:
        if marker in stripped:
            return DSLError(
                kind=ErrorKind.UNKNOWN_COMMAND,
                line_no=line_no,
                source_line=source,
                message=message,
                suggestion=suggestion,
                hint_code=hint,
            )
    return None


def _make_colon_error(line_no: int, source: str) -> DSLError:
    """콜론 누락 줄 → 에러 객체 생성"""
    return DSLError(
        kind=ErrorKind.MISSING_COLON,
        line_no=line_no,
        source_line=source,
        message="블록을 시작하는 문법인데 줄 끝에 ':'이 없습니다.",
        suggestion="줄 맨 끝에 ':' 를 붙여주세요.",
        hint_code=source.strip() + ":",
    )


def _make_expression_error(line_no: int, source: str, issue: ParseIssue) -> DSLError:
    """표현식 문법 오류를 사용자용 에러 객체로 변환한다."""
    statement_like = _make_statement_pattern_error(line_no, source)
    if statement_like is not None:
        return DSLError(
            kind=ErrorKind.PARSE_FAILED,
            line_no=line_no,
            column_no=issue.column,
            source_line=source,
            message=statement_like.message,
            suggestion=statement_like.suggestion,
            hint_code=statement_like.hint_code,
        )

    suggestion = "표현식을 완성한 뒤 다시 실행해주세요."
    if issue.expected:
        suggestion = f"이 위치에는 {issue.expected} 형태가 와야 합니다."

    hint = ""
    if issue.token == "EOF":
        hint = source.rstrip() + " ..."

    return DSLError(
        kind=ErrorKind.PARSE_FAILED,
        line_no=line_no,
        column_no=issue.column,
        source_line=source,
        message=issue.message,
        suggestion=suggestion,
        hint_code=hint,
    )


# ──────────────────────────────────────────────────────────────
# 파싱 관련 유틸
# ──────────────────────────────────────────────────────────────

def needs_colon_hint(line: str) -> bool:
    """
    블록 구문 키워드가 있는데 ':'로 끝나지 않는 줄을 감지한다.

    수정: 문자열 리터럴("...") 안에 있는 키워드는 무시한다.
    예) 화면에 보여줘 "아니면 뭐야"  → '아니면'이 문자열 안에 있으므로 오탐하지 않음.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("이건 상관 없는 이야기인데"):
        return False
    if stripped.endswith(":"):
        return False

    # 문자열 리터럴 제거 후 키워드 탐색
    cleaned = re.sub(r'"[^"]*"', '', stripped)
    for kw in BLOCK_KEYWORDS:
        if kw in cleaned:
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


def _iter_expression_sources(ast_node):
    """AST 노드에서 문법 검사가 필요한 표현식 문자열을 순회한다."""
    if isinstance(ast_node, Program):
        for child in ast_node.body:
            yield from _iter_expression_sources(child)
        return

    expression_fields = []

    if isinstance(ast_node, (Assignment, SelfAssignment, ReturnStatement)):
        expression_fields.append(ast_node.value)
    elif isinstance(ast_node, IfStatement):
        expression_fields.append(ast_node.condition)
        for elif_clause in ast_node.elifs:
            expression_fields.append(elif_clause.condition)
            yield from _iter_expression_sources(elif_clause)
    elif isinstance(ast_node, ForRange):
        expression_fields.extend([ast_node.start, ast_node.end])
    elif isinstance(ast_node, ForEach):
        expression_fields.append(ast_node.iterable)
    elif isinstance(ast_node, WhileStatement):
        expression_fields.append(ast_node.condition)
    elif isinstance(ast_node, PrintStatement):
        expression_fields.append(ast_node.value)
    elif isinstance(ast_node, ColorPrintStatement):
        expression_fields.append(ast_node.value)
    elif isinstance(ast_node, DictDefStatement):
        expression_fields.append(ast_node.value)
    elif isinstance(ast_node, DictStoreStatement):
        expression_fields.extend([ast_node.target, ast_node.key, ast_node.value])
    elif isinstance(ast_node, DictDeleteStatement):
        expression_fields.extend([ast_node.target, ast_node.key])
    elif isinstance(ast_node, ListAppendStatement):
        expression_fields.extend([ast_node.target, ast_node.value])
    elif isinstance(ast_node, ListRemoveStatement):
        expression_fields.extend([ast_node.target, ast_node.value])
    elif isinstance(ast_node, ListInsertStatement):
        expression_fields.extend([ast_node.target, ast_node.value])
    elif isinstance(ast_node, ListPopStatement):
        expression_fields.append(ast_node.target)
    elif isinstance(ast_node, FrameAppendStatement):
        expression_fields.append(ast_node.value)
    elif isinstance(ast_node, CursorWriteStatement):
        expression_fields.extend([ast_node.x, ast_node.y, ast_node.value])
    elif isinstance(ast_node, SleepStatement):
        expression_fields.append(ast_node.ms)
    elif isinstance(ast_node, FpsControlStatement):
        expression_fields.append(ast_node.fps)
    elif isinstance(ast_node, RawExpression):
        expression_fields.append(ast_node.source)

    for expr_source in expression_fields:
        if expr_source and expr_source.strip():
            yield ast_node.line, expr_source

    for attr in ("body", "else_body", "except_body", "finally_body"):
        children = getattr(ast_node, attr, None)
        if isinstance(children, list):
            for child in children:
                yield from _iter_expression_sources(child)


def collect_expression_errors(ast_node):
    """AST 노드에서 표현식 문법 오류를 수집한다."""
    errors = []
    seen = set()
    for line_no, expr_source in _iter_expression_sources(ast_node):
        issue = diagnose_expr(expr_source)
        if issue is None:
            continue
        key = (line_no, expr_source, issue.column, issue.message)
        if key in seen:
            continue
        seen.add(key)
        errors.append(_make_expression_error(line_no, expr_source, issue))
    return errors


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

    expr_errors = collect_expression_errors(ast)
    expr_error_lines = {err.line_no for err in expr_errors}

    # RawExpression 경고 (한글 포함 줄만)
    warnings = []
    for line_no, source in collect_raw_warnings(ast):
        if line_no not in expr_error_lines and any('\uac00' <= ch <= '\ud7a3' for ch in source):
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

    return py_code, warnings, colon_hints, expr_errors


# ──────────────────────────────────────────────────────────────
# 파일 처리
# ──────────────────────────────────────────────────────────────

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

    source_lines = code.split('\n')  # 에러 컨텍스트 출력용

    # 변환
    try:
        py_code, raw_warnings, colon_hints, expr_errors = transform_code(code)
    except RuntimeError as e:
        err = DSLError(
            kind=ErrorKind.PARSE_FAILED,
            line_no=0,
            source_line="",
            message=str(e),
            suggestion="문법 오류가 있는지 처음부터 확인해보세요.",
        )
        print(f"\n❌ [{filename}] 변환 실패")
        print(err.format())
        return
    except Exception as e:
        print(f"\n❌ [{filename}] 예기치 않은 오류:")
        traceback.print_exc()
        return

    # ── 에러/경고 수집 ──────────────────────────────────────
    all_errors: list[DSLError] = []

    for line_no, source in raw_warnings:
        all_errors.append(_make_raw_error(line_no, source))

    for line_no, source in colon_hints:
        all_errors.append(_make_colon_error(line_no, source))

    all_errors.extend(expr_errors)

    all_errors.sort(key=lambda e: (e.line_no, e.column_no, e.kind.label))
    has_blocking_errors = bool(all_errors)

    output_path = os.path.join(OUTPUT_DIR, name + ".py")
    output_file_exists = os.path.exists(output_path)
    file_written = False
    if not has_blocking_errors:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(py_code)
            file_written = True
        except Exception as e:
            print(f"\n❌ [{filename}] 파일 저장 실패: {e}")
            return

    # ── 결과 출력 ────────────────────────────────────────────
    print(f"\n{'═'*52}")
    if has_blocking_errors:
        print(f"  ⚠️  [{filename}] 문법 오류 {len(all_errors)}건 발견")
        if output_file_exists:
            print(f"  ⛔ [{name}.py] 기존 파일은 유지되었고 수정되지 않았습니다.")
        else:
            print(f"  ⛔ [{name}.py] 출력 파일은 생성되지 않았습니다.")
    else:
        status = "저장 완료" if file_written else "변환 완료"
        print(f"  ✔  [{filename}] → [{name}.py] {status}")
    print(f"{'═'*52}")

    print(f"\n📄 변환된 Python 코드:")
    print("─" * 40)
    print(py_code)
    print("─" * 40)

    if all_errors:
        print(f"\n{'━'*52}")
        print(f"  🚨 발견된 문제 목록 ({len(all_errors)}건)")
        print(f"{'━'*52}")
        for err in all_errors:
            print(err.format(source_lines))
        # 에러 종류별 요약
        kinds: dict[str, int] = {}
        for e in all_errors:
            kinds[e.kind.label] = kinds.get(e.kind.label, 0) + 1
        print(f"\n  📊 요약: " + " / ".join(f"{k} {v}건" for k, v in kinds.items()))
    else:
        print("\n  ✔ 전체 변환 정상 — 문제가 발견되지 않았습니다.")

    print()


# ──────────────────────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────────────────────

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
