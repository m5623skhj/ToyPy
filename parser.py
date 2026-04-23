import re
from typing import List, Optional, Tuple
from ast_nodes import *


COLORS = {
    '검은색': 30, '빨간색': 31, '초록색': 32, '노란색': 33,
    '파란색': 34, '보라색': 35, '하늘색': 36, '흰색': 37,
}
_COLOR_NAMES_RE = '|'.join(COLORS.keys())


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _collect_block(lines: List[str], start: int, parent_indent: int) -> Tuple[List[ASTNode], int]:
    body: List[ASTNode] = []
    idx = start
    while idx < len(lines):
        if lines[idx].strip() == '':
            idx += 1
            continue
        if _indent_of(lines[idx]) <= parent_indent:
            break
        node, idx = _parse_line(lines, idx)
        if node is not None:
            body.append(node)
    return body, idx


def parse(source: str) -> Program:
    lines = source.split('\n')
    program = Program(body=[])
    idx = 0
    while idx < len(lines):
        node, idx = _parse_line(lines, idx)
        if node is not None:
            program.body.append(node)
    return program


def _parse_line(lines: List[str], idx: int) -> Tuple[Optional[ASTNode], int]:
    if idx >= len(lines):
        return None, idx

    line = lines[idx]
    stripped = line.strip()
    indent = _indent_of(line)
    lineno = idx + 1

    if not stripped:
        return None, idx + 1

    # ── 다중행 주석 ──
    if stripped.startswith("여기서 부터"):
        comment_lines: List[str] = []
        idx += 1
        while idx < len(lines):
            s = lines[idx].strip()
            if s.startswith("여기까지는 상관 없는 이야기인데"):
                idx += 1
                break
            comment_lines.append(s)
            idx += 1
        return MultiLineComment(line=lineno, lines=comment_lines), idx

    # ── 단일행 주석 ──
    if stripped.startswith("이건 상관 없는 이야기인데"):
        text = stripped.replace("이건 상관 없는 이야기인데", "").strip()
        return Comment(line=lineno, text=text), idx + 1

    # ── import (별칭) ──
    m = re.match(r'^저기 있는\s+(\w+)\s+(?:을|를)\s+(\w+)\s+(?:으로|로)\s+가져와$', stripped)
    if m:
        return ImportStatement(line=lineno, module=m.group(1), alias=m.group(2)), idx + 1
    m = re.match(r'^저기 있는\s+(.*)\s+좀 가져와$', stripped)
    if m:
        return ImportStatement(line=lineno, module=m.group(1).strip()), idx + 1

    # ── 클래스 (상속) ──
    m = re.match(r'^이런 설계도가 있어\s+(\w+)\s+(?:는|은)\s+(\w+):$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return ClassDef(line=lineno, name=m.group(1), parent=m.group(2), body=body), next_idx
    m = re.match(r'^이런 설계도가 있어\s+(\w+):$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return ClassDef(line=lineno, name=m.group(1), body=body), next_idx

    # ── 생성자 ──
    m = re.match(r'^만들 때\((.*?)\):$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return InitDef(line=lineno, params=m.group(1), body=body), next_idx

    # ── self 할당 ──
    m = re.match(r'^내\s+(\w+)\s+(?:는|은)\s+(.*)', stripped)
    if m:
        return SelfAssignment(line=lineno, attr=m.group(1), value=m.group(2).strip()), idx + 1

    # ── 함수 정의 ──
    m = re.match(r'^이런 기능이 있어\s+(\w+)\((.*?)\):$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return FunctionDef(line=lineno, name=m.group(1), params=m.group(2), body=body), next_idx

    # ── 파일 with 구문 ──
    m = re.match(r'^파일\s+(.*?)\s+(읽기|쓰기|이어쓰기)로 열어서\s+(\w+)\s+라고 부르고:$', stripped)
    if m:
        mode_map = {"읽기": "r", "쓰기": "w", "이어쓰기": "a"}
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return WithFileStatement(
            line=lineno, filepath=m.group(1), mode=mode_map[m.group(2)],
            alias=m.group(3), body=body
        ), next_idx

    # ── try / except / finally ──
    if stripped == '혹시 모르니까 한번 해봐:':
        body, next_idx = _collect_block(lines, idx + 1, indent)
        node = TryStatement(line=lineno, body=body)
        if next_idx < len(lines):
            s = lines[next_idx].strip()
            em = re.match(r'^근데\s+(\w+)\s+문제가 생기면\s+(\w+)\s+라고 부르고:$', s)
            if em:
                node.except_type = em.group(1)
                node.except_alias = em.group(2)
                node.except_body, next_idx = _collect_block(lines, next_idx + 1, indent)
            else:
                em = re.match(r'^근데\s+(\w+)\s+문제가 생기면:$', s)
                if em:
                    node.except_type = em.group(1)
                    node.except_body, next_idx = _collect_block(lines, next_idx + 1, indent)
                elif s == '근데 문제가 생기면:':
                    node.except_body, next_idx = _collect_block(lines, next_idx + 1, indent)
        if next_idx < len(lines) and lines[next_idx].strip() == '아무튼 간에:':
            node.finally_body, next_idx = _collect_block(lines, next_idx + 1, indent)
        return node, next_idx

    # ── 사전 정의 ──
    m = re.match(r'^"(.*)"\s+(?:라는|이라는)\s+사전에는\s+(.*)\s+라고 되어있어$', stripped)
    if m:
        return DictDefStatement(line=lineno, name=m.group(1), value=m.group(2)), idx + 1

    # ── 사전 포함 조건 (있으면/없으면) — 일반 if보다 먼저 ──
    m = re.match(r'^만약에 말이야\s+(.*)\s+에\s+(.*)\s+(?:이|가)\s+있으면:$', stripped)
    if m:
        condition = f'{m.group(2)} in {m.group(1)}'
        body, next_idx = _collect_block(lines, idx + 1, indent)
        node = IfStatement(line=lineno, condition=condition, body=body)
        while next_idx < len(lines):
            s = lines[next_idx].strip()
            em = re.match(r'^아니면\s+(.*):$', s)
            if em:
                elif_lineno = next_idx + 1
                ebody, next_idx = _collect_block(lines, next_idx + 1, indent)
                node.elifs.append(ElifClause(line=elif_lineno, condition=em.group(1), body=ebody))
                continue
            if s == '전부 아니면:':
                node.else_body, next_idx = _collect_block(lines, next_idx + 1, indent)
                continue
            break
        return node, next_idx

    m = re.match(r'^만약에 말이야\s+(.*)\s+에\s+(.*)\s+(?:이|가)\s+없으면:$', stripped)
    if m:
        condition = f'{m.group(2)} not in {m.group(1)}'
        body, next_idx = _collect_block(lines, idx + 1, indent)
        node = IfStatement(line=lineno, condition=condition, body=body)
        while next_idx < len(lines):
            s = lines[next_idx].strip()
            em = re.match(r'^아니면\s+(.*):$', s)
            if em:
                elif_lineno = next_idx + 1
                ebody, next_idx = _collect_block(lines, next_idx + 1, indent)
                node.elifs.append(ElifClause(line=elif_lineno, condition=em.group(1), body=ebody))
                continue
            if s == '전부 아니면:':
                node.else_body, next_idx = _collect_block(lines, next_idx + 1, indent)
                continue
            break
        return node, next_idx

    # ── 조건문 (일반) ──
    m = re.match(r'^만약에 말이야\s+(.*):$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        node = IfStatement(line=lineno, condition=m.group(1), body=body)
        while next_idx < len(lines):
            s = lines[next_idx].strip()
            em = re.match(r'^아니면\s+(.*):$', s)
            if em:
                elif_lineno = next_idx + 1
                ebody, next_idx = _collect_block(lines, next_idx + 1, indent)
                node.elifs.append(ElifClause(line=elif_lineno, condition=em.group(1), body=ebody))
                continue
            if s == '전부 아니면:':
                node.else_body, next_idx = _collect_block(lines, next_idx + 1, indent)
                continue
            break
        return node, next_idx

    # ── for range (이전까지) ──
    m = re.match(
        r'^(.*)\s+부터\s+(.*)\s+이전까지 하나씩 숫자를 늘려가며\s+(.*)\s+이라고 부르고:$',
        stripped
    )
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return ForRange(line=lineno, start=m.group(1), end=m.group(2),
                        inclusive=False, var=m.group(3), body=body), next_idx

    # ── for range (까지) ──
    m = re.match(
        r'^(\d+)\s+부터\s+(\d+)\s+까지 하나씩 숫자를 늘려가며\s+(.*)\s+이라고 부르고:$',
        stripped
    )
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return ForRange(line=lineno, start=m.group(1), end=m.group(2),
                        inclusive=True, var=m.group(3), body=body), next_idx

    # ── N번 반복해 ──
    m = re.match(r'^(\d+)\s*번 반복해:$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return ForNTimes(line=lineno, count=m.group(1), body=body), next_idx

    # ── for-each ──
    m = re.match(r'^(.*)\s+에 있는 것들 하나씩 꺼내서\s+(.*)\s+이라고 부르고:$', stripped)
    if m:
        is_items = ',' in m.group(2)
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return ForEach(line=lineno, iterable=m.group(1), var=m.group(2),
                       is_items=is_items, body=body), next_idx

    # ── 영원히 반복해 ──
    if stripped == '영원히 반복해:':
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return WhileTrue(line=lineno, body=body), next_idx

    # ── while ──
    m = re.match(r'^(.*)\s+동안 반복해:$', stripped)
    if m:
        body, next_idx = _collect_block(lines, idx + 1, indent)
        return WhileStatement(line=lineno, condition=m.group(1), body=body), next_idx

    # ── break / continue ──
    if stripped == '멈춰':
        return BreakStatement(line=lineno), idx + 1
    if stripped == '다음으로 넘어가':
        return ContinueStatement(line=lineno), idx + 1

    # ── pass ──
    if stripped == "넘어가":
        return PassStatement(line=lineno), idx + 1

    # ── raise ──
    m = re.match(r'^오류를 발생시켜줘\s+"([^"]*)"$', stripped)
    if m:
        return RaiseStatement(line=lineno, message=m.group(1)), idx + 1

    # ── return ──
    m = re.match(r'^결과는\s+(.*)', stripped)
    if m:
        return ReturnStatement(line=lineno, value=m.group(1).strip()), idx + 1

    # ── 사전 저장 ──
    m = re.match(r'^(.*)\s+에\s+(.*)\s+를\s+(.*)\s+(?:으)?로\s+저장해$', stripped)
    if m:
        return DictStoreStatement(line=lineno, target=m.group(1), key=m.group(2), value=m.group(3)), idx + 1

    # ── 사전 삭제 ──
    m = re.match(r'^(.*)\s+에서\s+(.*)\s+(?:은|는)\s+지워줘$', stripped)
    if m:
        return DictDeleteStatement(line=lineno, target=m.group(1), key=m.group(2)), idx + 1

    # ── 리스트 맨 앞 삽입 ──
    m = re.match(r'^(.*)\s+맨 앞에\s+(.*)\s+끼워줘$', stripped)
    if m:
        return ListInsertStatement(line=lineno, target=m.group(1), value=m.group(2)), idx + 1

    # ── 리스트 끝 잘라줘 ──
    m = re.match(r'^(.*)\s+끝 잘라줘$', stripped)
    if m:
        return ListPopStatement(line=lineno, target=m.group(1)), idx + 1

    # ── 리스트 append ──
    m = re.match(r'^(.*)\s+에\s+(.*)\s+도 넣어줘$', stripped)
    if m:
        return ListAppendStatement(line=lineno, target=m.group(1), value=m.group(2)), idx + 1

    # ── 리스트 remove ──
    m = re.match(r'^(.*)\s+에서\s+(.*)\s+(?:은|는) 빼줘$', stripped)
    if m:
        return ListRemoveStatement(line=lineno, target=m.group(1), value=m.group(2)), idx + 1

    # ── 화면 깨끗이 ──
    if stripped == '화면 깨끗이':
        return ClearScreenStatement(line=lineno), idx + 1

    # ── 프레임 버퍼 ──
    if stripped == '부드럽게 그릴 준비해':
        return FrameBufferInitStatement(line=lineno), idx + 1
    if stripped == '프레임 시작':
        return FrameStartStatement(line=lineno), idx + 1
    if stripped == '프레임 줄 바꿔':
        return FrameNewlineStatement(line=lineno), idx + 1
    if stripped == '프레임 그려줘':
        return FrameRenderStatement(line=lineno), idx + 1

    m = re.match(r'^프레임에 이어서 보여줘\s+(.*)', stripped)
    if m:
        return FrameAppendStatement(line=lineno, value=m.group(1), inline=True), idx + 1
    m = re.match(r'^프레임에 보여줘\s+(.*)', stripped)
    if m:
        return FrameAppendStatement(line=lineno, value=m.group(1), inline=False), idx + 1

    # ── 커서 위치 ──
    m = re.match(r'^\(([^,]+),\s*([^)]+)\)\s+위치에 써줘\s+(.*)', stripped)
    if m:
        return CursorWriteStatement(line=lineno, x=m.group(1), y=m.group(2), value=m.group(3)), idx + 1

    # ── 색상 출력 (이어서) ──
    m = re.match(rf'^({_COLOR_NAMES_RE})으로 이어서 보여줘\s+(.*)', stripped)
    if m:
        return ColorPrintStatement(line=lineno, color_name=m.group(1),
                                   color_code=COLORS[m.group(1)], value=m.group(2), inline=True), idx + 1

    # ── 색상 출력 ──
    m = re.match(rf'^({_COLOR_NAMES_RE})으로 보여줘\s+(.*)', stripped)
    if m:
        return ColorPrintStatement(line=lineno, color_name=m.group(1),
                                   color_code=COLORS[m.group(1)], value=m.group(2), inline=False), idx + 1

    # ── 이어서 출력 ──
    m = re.match(r'^화면에 이어서 보여줘\s+(.*)', stripped)
    if m:
        return PrintStatement(line=lineno, value=m.group(1), inline=True), idx + 1

    # ── 줄 바꿔 ──
    if stripped == '줄 바꿔':
        return NewLineStatement(line=lineno), idx + 1

    # ── 화면 출력 ──
    m = re.match(r'^화면에 보여줘\s+(.*)', stripped)
    if m:
        return PrintStatement(line=lineno, value=m.group(1)), idx + 1

    # ── 시간 제어 ──
    m = re.match(r'^([\w.]+)\s+밀리초 기다려$', stripped)
    if m:
        return SleepStatement(line=lineno, ms=m.group(1)), idx + 1

    m = re.match(r'^초당\s+([\w.+\-*/()]+)\s*프레임\s+유지$', stripped)
    if m:
        return FpsControlStatement(line=lineno, fps=m.group(1)), idx + 1

    # ── 입력 ──
    m = re.match(r'^(\w+)\s+(?:는|은)\s+값을 입력할래$', stripped)
    if m:
        return InputExpression(line=lineno, target=m.group(1)), idx + 1

    # ── 튜플 언패킹 ──
    m = re.match(r'^(\w+(?:\s*,\s*\w+)+)\s+(?:는|은)\s+(.*)', stripped)
    if m:
        return Assignment(line=lineno, target=m.group(1), value=m.group(2).strip()), idx + 1

    # ── 변수 할당 ──
    m = re.match(r'^(\w+)\s+(?:는|은)\s+(.*)', stripped)
    if m:
        return Assignment(line=lineno, target=m.group(1), value=m.group(2).strip()), idx + 1

    # ── 폴백 ──
    return RawExpression(line=lineno, source=stripped), idx + 1