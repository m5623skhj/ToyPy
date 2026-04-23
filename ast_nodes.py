from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ASTNode:
    line: int = 0

@dataclass
class Program(ASTNode):
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class PrintStatement(ASTNode):
    value: str = ""
    inline: bool = False

@dataclass
class ColorPrintStatement(ASTNode):
    color_name: str = ""
    color_code: int = 0
    value: str = ""
    inline: bool = False

@dataclass
class NewLineStatement(ASTNode):
    pass

@dataclass
class Assignment(ASTNode):
    target: str = ""
    value: str = ""

@dataclass
class InputExpression(ASTNode):
    target: str = ""

@dataclass
class ElifClause(ASTNode):
    condition: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class IfStatement(ASTNode):
    condition: str = ""
    body: List[ASTNode] = field(default_factory=list)
    elifs: List[ElifClause] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForNTimes(ASTNode):
    count: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForRange(ASTNode):
    start: str = ""
    end: str = ""
    inclusive: bool = False
    var: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForEach(ASTNode):
    iterable: str = ""
    var: str = ""
    is_items: bool = False
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class WhileTrue(ASTNode):
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class WhileStatement(ASTNode):
    condition: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class FunctionDef(ASTNode):
    name: str = ""
    params: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ClassDef(ASTNode):
    name: str = ""
    parent: Optional[str] = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class InitDef(ASTNode):
    params: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class SelfAssignment(ASTNode):
    attr: str = ""
    value: str = ""

@dataclass
class ReturnStatement(ASTNode):
    value: str = ""

@dataclass
class BreakStatement(ASTNode):
    pass

@dataclass
class ContinueStatement(ASTNode):
    pass

@dataclass
class TryStatement(ASTNode):
    body: List[ASTNode] = field(default_factory=list)
    except_type: Optional[str] = None
    except_alias: Optional[str] = None
    except_body: List[ASTNode] = field(default_factory=list)
    finally_body: List[ASTNode] = field(default_factory=list)

@dataclass
class ImportStatement(ASTNode):
    module: str = ""
    alias: Optional[str] = None

@dataclass
class Comment(ASTNode):
    text: str = ""

@dataclass
class MultiLineComment(ASTNode):
    lines: List[str] = field(default_factory=list)

@dataclass
class WithFileStatement(ASTNode):
    filepath: str = ""
    mode: str = "r"
    alias: str = ""
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class DictDefStatement(ASTNode):
    name: str = ""
    value: str = ""

@dataclass
class DictStoreStatement(ASTNode):
    target: str = ""
    key: str = ""
    value: str = ""

@dataclass
class DictDeleteStatement(ASTNode):
    target: str = ""
    key: str = ""

@dataclass
class ListAppendStatement(ASTNode):
    target: str = ""
    value: str = ""

@dataclass
class ListRemoveStatement(ASTNode):
    target: str = ""
    value: str = ""

@dataclass
class ListInsertStatement(ASTNode):
    target: str = ""
    value: str = ""

@dataclass
class ListPopStatement(ASTNode):
    target: str = ""

@dataclass
class ClearScreenStatement(ASTNode):
    pass

@dataclass
class FrameBufferInitStatement(ASTNode):
    pass

@dataclass
class FrameStartStatement(ASTNode):
    pass

@dataclass
class FrameAppendStatement(ASTNode):
    value: str = ""
    inline: bool = False

@dataclass
class FrameNewlineStatement(ASTNode):
    pass

@dataclass
class FrameRenderStatement(ASTNode):
    pass

@dataclass
class CursorWriteStatement(ASTNode):
    x: str = ""
    y: str = ""
    value: str = ""

@dataclass
class SleepStatement(ASTNode):
    ms: str = ""

@dataclass
class FpsControlStatement(ASTNode):
    fps: str = ""

@dataclass
class RawExpression(ASTNode):
    source: str = ""

@dataclass
class PassStatement(ASTNode):
    pass

@dataclass
class RaiseStatement(ASTNode):
    message: str = ""