import re
from typing import List, Tuple

from ast_nodes import *
from expr_parser import transform as _expr_transform, COLORS


GeneratedLine = Tuple[str, int]


def _process_params(params: str) -> str:
    return re.sub(r'(\w+)\s+(?:는|은)\s+([^,]+)', r'\1=\2', params)


def _transform_expr(expr: str) -> str:
    """표현식 문자열을 Python 코드로 변환.

    내부적으로 expr_parser(정규 AST 파서)를 호출한다.
    파싱이 불가능하면 원본을 그대로 반환한다.
    """
    return _expr_transform(expr)


def _render_children(children: List[ASTNode], indent: int) -> List[GeneratedLine]:
    rendered: List[GeneratedLine] = []
    for child in children:
        rendered.extend(generate_with_map(child, indent))
    return rendered


def generate_with_map(node: ASTNode, indent: int = 0) -> List[GeneratedLine]:
    pad = '    ' * indent

    if isinstance(node, Program):
        return _render_children(node.body, 0)

    if isinstance(node, Comment):
        return [(f'{pad}# {node.text}', node.line)]

    if isinstance(node, MultiLineComment):
        lines: List[GeneratedLine] = [(f'{pad}"""', node.line)]
        for line in node.lines:
            lines.append((f'{pad}{line}', node.line))
        lines.append((f'{pad}"""', node.line))
        return lines

    if isinstance(node, ImportStatement):
        if node.alias:
            return [(f'{pad}import {node.module} as {node.alias}', node.line)]
        return [(f'{pad}import {node.module}', node.line)]

    if isinstance(node, ColorPrintStatement):
        color_code = node.color_code
        value = _transform_expr(node.value)
        if node.inline:
            return [(f'{pad}print("\\033[{color_code}m" + str({value}) + "\\033[0m", end="")', node.line)]
        return [(f'{pad}print("\\033[{color_code}m" + str({value}) + "\\033[0m")', node.line)]

    if isinstance(node, PrintStatement):
        value = _transform_expr(node.value)
        if node.inline:
            return [(f'{pad}print({value}, end="")', node.line)]
        return [(f'{pad}print({value})', node.line)]

    if isinstance(node, NewLineStatement):
        return [(f'{pad}print()', node.line)]

    if isinstance(node, Assignment):
        return [(f'{pad}{node.target} = {_transform_expr(node.value)}', node.line)]

    if isinstance(node, InputExpression):
        return [(f'{pad}{node.target} = input()', node.line)]

    if isinstance(node, IfStatement):
        lines: List[GeneratedLine] = [(f'{pad}if {_transform_expr(node.condition)}:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        for elif_clause in node.elifs:
            lines.append((f'{pad}elif {_transform_expr(elif_clause.condition)}:', elif_clause.line or node.line))
            lines.extend(_render_children(elif_clause.body, indent + 1))
        if node.else_body:
            lines.append((f'{pad}else:', node.line))
            lines.extend(_render_children(node.else_body, indent + 1))
        return lines

    if isinstance(node, ForNTimes):
        lines = [(f'{pad}for _ in range({node.count}):', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, ForRange):
        if node.inclusive:
            end_expr = f'{int(node.end) + 1}' if node.end.isdigit() else f'{node.end} + 1'
            lines = [(f'{pad}for {node.var} in range({node.start}, {end_expr}):', node.line)]
        else:
            lines = [(f'{pad}for {node.var} in range({node.start}, {node.end}):', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, ForEach):
        suffix = '.items()' if node.is_items else ''
        lines = [(f'{pad}for {node.var} in {node.iterable}{suffix}:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, WhileTrue):
        lines = [(f'{pad}while True:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, WhileStatement):
        lines = [(f'{pad}while {_transform_expr(node.condition)}:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, FunctionDef):
        lines = [(f'{pad}def {node.name}({_process_params(node.params)}):', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, ClassDef):
        parent = f'({node.parent})' if node.parent else ''
        lines = [(f'{pad}class {node.name}{parent}:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, InitDef):
        lines = [(f'{pad}def __init__(self, {_process_params(node.params)}):', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, SelfAssignment):
        return [(f'{pad}self.{node.attr} = {_transform_expr(node.value)}', node.line)]

    if isinstance(node, ReturnStatement):
        return [(f'{pad}return {_transform_expr(node.value)}', node.line)]

    if isinstance(node, BreakStatement):
        return [(f'{pad}break', node.line)]

    if isinstance(node, ContinueStatement):
        return [(f'{pad}continue', node.line)]

    if isinstance(node, PassStatement):
        return [(f'{pad}pass', node.line)]

    if isinstance(node, RaiseStatement):
        return [(f'{pad}raise Exception({repr(node.message)})', node.line)]

    if isinstance(node, TryStatement):
        lines = [(f'{pad}try:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        if node.except_type:
            exception_name = node.except_type
            if node.except_alias:
                exception_name += f' as {node.except_alias}'
            lines.append((f'{pad}except {exception_name}:', node.line))
        else:
            lines.append((f'{pad}except Exception:', node.line))
        lines.extend(_render_children(node.except_body, indent + 1))
        if node.finally_body:
            lines.append((f'{pad}finally:', node.line))
            lines.extend(_render_children(node.finally_body, indent + 1))
        return lines

    if isinstance(node, WithFileStatement):
        lines = [(f'{pad}with open({node.filepath}, "{node.mode}", encoding="utf-8") as {node.alias}:', node.line)]
        lines.extend(_render_children(node.body, indent + 1))
        return lines

    if isinstance(node, DictDefStatement):
        return [(f'{pad}{node.name} = {node.value}', node.line)]

    if isinstance(node, DictStoreStatement):
        return [(f'{pad}{node.target}[{node.key}] = {node.value}', node.line)]

    if isinstance(node, DictDeleteStatement):
        return [(f'{pad}del {node.target}[{node.key}]', node.line)]

    if isinstance(node, ListAppendStatement):
        return [(f'{pad}{node.target}.append({node.value})', node.line)]

    if isinstance(node, ListRemoveStatement):
        return [(f'{pad}{node.target}.remove({node.value})', node.line)]

    if isinstance(node, ListInsertStatement):
        return [(f'{pad}{node.target}.insert(0, {node.value})', node.line)]

    if isinstance(node, ListPopStatement):
        return [(f'{pad}{node.target}.pop()', node.line)]

    if isinstance(node, ClearScreenStatement):
        return [(f'{pad}os.system("cls" if os.name == "nt" else "clear")', node.line)]

    if isinstance(node, FrameBufferInitStatement):
        return [(
            f'{pad}(os.system("") if os.name == "nt" else None); '
            f'sys.stdout.write("\\033[2J\\033[H\\033[?25l"); '
            f'sys.stdout.flush(); _frame_buf = []',
            node.line,
        )]

    if isinstance(node, FrameStartStatement):
        return [(f'{pad}_frame_buf = []', node.line)]

    if isinstance(node, FrameAppendStatement):
        value = _transform_expr(node.value)
        if node.inline:
            return [(f'{pad}_frame_buf.append(str({value}))', node.line)]
        return [(f'{pad}_frame_buf.append(str({value}) + "\\n")', node.line)]

    if isinstance(node, FrameNewlineStatement):
        return [(f'{pad}_frame_buf.append("\\n")', node.line)]

    if isinstance(node, FrameRenderStatement):
        return [(f'{pad}sys.stdout.write("\\033[H" + "".join(_frame_buf) + "\\033[J"); sys.stdout.flush()', node.line)]

    if isinstance(node, CursorWriteStatement):
        value = _transform_expr(node.value)
        return [(
            f'{pad}sys.stdout.write("\\033[" + str({node.y}) + ";" + '
            f'str({node.x}) + "H" + str({value})); '
            f'sys.stdout.flush()',
            node.line,
        )]

    if isinstance(node, SleepStatement):
        return [(f'{pad}time.sleep({node.ms} / 1000)', node.line)]

    if isinstance(node, FpsControlStatement):
        return [(f'{pad}_frame_wait({node.fps})', node.line)]

    if isinstance(node, RawExpression):
        return [(f'{pad}{_transform_expr(node.source)}', node.line)]

    return [(f'{pad}# UNKNOWN NODE: {node}', getattr(node, "line", 0))]


def generate(node: ASTNode, indent: int = 0) -> str:
    return '\n'.join(text for text, _ in generate_with_map(node, indent))
