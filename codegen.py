import re
from ast_nodes import *
from expr_parser import transform as _expr_transform, COLORS


def _process_params(params: str) -> str:
    return re.sub(r'(\w+)\s+(?:는|은)\s+([^,]+)', r'\1=\2', params)


def _transform_expr(expr: str) -> str:
    """표현식 문자열을 Python 코드로 변환.

    내부적으로 expr_parser(정규 AST 파서)를 호출한다.
    파싱이 불가능하면 원본을 그대로 반환한다.
    """
    return _expr_transform(expr)


def generate(node: ASTNode, indent: int = 0) -> str:
    pad = '    ' * indent

    if isinstance(node, Program):
        return '\n'.join(generate(child, 0) for child in node.body)

    if isinstance(node, Comment):
        return f'{pad}# {node.text}'

    if isinstance(node, MultiLineComment):
        lines = [f'{pad}"""']
        for l in node.lines:
            lines.append(f'{pad}{l}')
        lines.append(f'{pad}"""')
        return '\n'.join(lines)

    if isinstance(node, ImportStatement):
        if node.alias:
            return f'{pad}import {node.module} as {node.alias}'
        return f'{pad}import {node.module}'

    if isinstance(node, ColorPrintStatement):
        c = node.color_code
        val = _transform_expr(node.value)
        if node.inline:
            return f'{pad}print("\\033[{c}m" + str({val}) + "\\033[0m", end="")'
        return f'{pad}print("\\033[{c}m" + str({val}) + "\\033[0m")'

    if isinstance(node, PrintStatement):
        val = _transform_expr(node.value)
        if node.inline:
            return f'{pad}print({val}, end="")'
        return f'{pad}print({val})'

    if isinstance(node, NewLineStatement):
        return f'{pad}print()'

    if isinstance(node, Assignment):
        return f'{pad}{node.target} = {_transform_expr(node.value)}'

    if isinstance(node, InputExpression):
        return f'{pad}{node.target} = input()'

    if isinstance(node, IfStatement):
        lines = [f'{pad}if {_transform_expr(node.condition)}:']
        lines += [generate(c, indent + 1) for c in node.body]
        for ec in node.elifs:
            lines.append(f'{pad}elif {_transform_expr(ec.condition)}:')
            lines += [generate(c, indent + 1) for c in ec.body]
        if node.else_body:
            lines.append(f'{pad}else:')
            lines += [generate(c, indent + 1) for c in node.else_body]
        return '\n'.join(lines)

    if isinstance(node, ForNTimes):
        lines = [f'{pad}for _ in range({node.count}):']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, ForRange):
        if node.inclusive:
            end_expr = f'{int(node.end) + 1}' if node.end.isdigit() else f'{node.end} + 1'
            lines = [f'{pad}for {node.var} in range({node.start}, {end_expr}):']
        else:
            lines = [f'{pad}for {node.var} in range({node.start}, {node.end}):']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, ForEach):
        suffix = '.items()' if node.is_items else ''
        lines = [f'{pad}for {node.var} in {node.iterable}{suffix}:']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, WhileTrue):
        lines = [f'{pad}while True:']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, WhileStatement):
        lines = [f'{pad}while {_transform_expr(node.condition)}:']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, FunctionDef):
        lines = [f'{pad}def {node.name}({_process_params(node.params)}):']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, ClassDef):
        parent = f'({node.parent})' if node.parent else ''
        lines = [f'{pad}class {node.name}{parent}:']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, InitDef):
        lines = [f'{pad}def __init__(self, {_process_params(node.params)}):']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, SelfAssignment):
        return f'{pad}self.{node.attr} = {_transform_expr(node.value)}'

    if isinstance(node, ReturnStatement):
        return f'{pad}return {_transform_expr(node.value)}'

    if isinstance(node, BreakStatement):
        return f'{pad}break'

    if isinstance(node, ContinueStatement):
        return f'{pad}continue'

    if isinstance(node, TryStatement):
        lines = [f'{pad}try:']
        lines += [generate(c, indent + 1) for c in node.body]
        if node.except_type:
            exc = node.except_type
            if node.except_alias:
                exc += f' as {node.except_alias}'
            lines.append(f'{pad}except {exc}:')
        else:
            lines.append(f'{pad}except Exception:')
        lines += [generate(c, indent + 1) for c in node.except_body]
        if node.finally_body:
            lines.append(f'{pad}finally:')
            lines += [generate(c, indent + 1) for c in node.finally_body]
        return '\n'.join(lines)

    if isinstance(node, WithFileStatement):
        lines = [f'{pad}with open({node.filepath}, "{node.mode}", encoding="utf-8") as {node.alias}:']
        lines += [generate(c, indent + 1) for c in node.body]
        return '\n'.join(lines)

    if isinstance(node, DictDefStatement):
        return f'{pad}{node.name} = {node.value}'

    if isinstance(node, DictStoreStatement):
        return f'{pad}{node.target}[{node.key}] = {node.value}'

    if isinstance(node, DictDeleteStatement):
        return f'{pad}del {node.target}[{node.key}]'

    if isinstance(node, ListAppendStatement):
        return f'{pad}{node.target}.append({node.value})'

    if isinstance(node, ListRemoveStatement):
        return f'{pad}{node.target}.remove({node.value})'

    if isinstance(node, ListInsertStatement):
        return f'{pad}{node.target}.insert(0, {node.value})'

    if isinstance(node, ListPopStatement):
        return f'{pad}{node.target}.pop()'

    if isinstance(node, ClearScreenStatement):
        return f'{pad}os.system("cls" if os.name == "nt" else "clear")'

    if isinstance(node, FrameBufferInitStatement):
        return (
            f'{pad}(os.system("") if os.name == "nt" else None); '
            f'sys.stdout.write("\\033[2J\\033[H\\033[?25l"); '
            f'sys.stdout.flush(); _frame_buf = []'
        )

    if isinstance(node, FrameStartStatement):
        return f'{pad}_frame_buf = []'

    if isinstance(node, FrameAppendStatement):
        val = _transform_expr(node.value)
        if node.inline:
            return f'{pad}_frame_buf.append(str({val}))'
        return f'{pad}_frame_buf.append(str({val}) + "\\n")'

    if isinstance(node, FrameNewlineStatement):
        return f'{pad}_frame_buf.append("\\n")'

    if isinstance(node, FrameRenderStatement):
        return f'{pad}sys.stdout.write("\\033[H" + "".join(_frame_buf) + "\\033[J"); sys.stdout.flush()'

    if isinstance(node, CursorWriteStatement):
        val = _transform_expr(node.value)
        return (
            f'{pad}sys.stdout.write("\\033[" + str({node.y}) + ";" + '
            f'str({node.x}) + "H" + str({val})); '
            f'sys.stdout.flush()'
        )

    if isinstance(node, SleepStatement):
        return f'{pad}time.sleep({node.ms} / 1000)'

    if isinstance(node, FpsControlStatement):
        return f'{pad}_frame_wait({node.fps})'

    if isinstance(node, RawExpression):
        return f'{pad}{_transform_expr(node.source)}'

    return f'{pad}# UNKNOWN NODE: {node}'