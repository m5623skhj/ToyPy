# -*- coding: utf-8 -*-
"""
ToyPy 표현식 전용 파서.

statement 레벨 파서(parser.py)가 식별한 표현식 문자열을 입력으로 받아,
올바른 결합(associativity)/우선순위로 Python 코드로 변환한다.

설계 요점:
- Pratt 스타일 재귀 하강 파서
- Korean DSL 키워드 (postfix: '를 숫자로 봐줘' 등, infix: '에 ... 가 있어?' 등) 완전 지원
- Python 키워드 (and/or/not/in/is/True/False/None) 및 f-string 통과 지원
- 파싱 실패 시 원본 문자열 그대로 반환 (안전 폴백)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any


# ──────────────────────────────────────────────
# 색상
# ──────────────────────────────────────────────
COLORS = {
    '검은색': 30, '빨간색': 31, '초록색': 32, '노란색': 33,
    '파란색': 34, '보라색': 35, '하늘색': 36, '흰색': 37,
}


# ──────────────────────────────────────────────
# 토큰
# ──────────────────────────────────────────────
@dataclass
class Tok:
    type: str
    value: str
    start: int = 0
    end: int = 0


@dataclass
class ParseIssue:
    message: str
    token: str = ""
    expected: str = ""
    column: int = 1


# 합성 키워드 (공백·물음표 제외한 순수 단어 시퀀스로 매칭)
# 각 항목: (phrase, token_type)
# phrase는 공백으로 word 분리; word 끝에 '?'가 붙어있으면 QMARK도 소비
_KW_PHRASES = [
    ("를 숫자로 봐줘",        "KW_INT"),
    ("를 글자로 봐줘",        "KW_STR"),
    ("가 얼마나 길어?",       "KW_LEN"),
    ("에 뭐뭐 있어?",         "KW_DICTKEYS"),
    ("눌린 키가 뭐야?",       "KW_GETKEY"),
    ("키가 눌렸어?",          "KW_KBHIT"),
    ("주는 것",               "KW_LAMBDA_OUT"),
    ("번째부터",              "KW_NTH_FROM"),
    ("번째까지",              "KW_NTH_TO"),
    ("처음부터",              "KW_BEGIN"),
    ("끝까지",                "KW_END"),
    ("받아서",                "KW_LAMBDA_IN"),
    ("그리고",                "KW_AND"),
    ("또는",                  "KW_OR"),
    ("아님",                  "KW_NOT"),
    ("진짜야",                "KW_TRUE"),
    ("가짜야",                "KW_FALSE"),
    ("무작위",                "KW_RAND"),
    ("가 있어?",              "KW_HAS"),
    ("이 있어?",              "KW_HAS"),
    ("부터",                  "KW_FROM"),
    ("까지",                  "KW_TO"),
    ("의",                    "KW_OF"),
    ("에",                    "KW_AT"),
]

# Python 동의어
_PY_KW = {
    'and':   'KW_AND',
    'or':    'KW_OR',
    'not':   'KW_NOT',
    'True':  'KW_TRUE',
    'False': 'KW_FALSE',
    'None':  'PY_NONE',
    'in':    'PY_IN',
    'is':    'PY_IS',
}

_OPS_2 = ('==', '!=', '<=', '>=', '//', '**')
_OPS_1 = ('+', '-', '*', '/', '%', '<', '>')

_NUM_RE = re.compile(r'\d+(?:\.\d+)?')
_ID_START_RE = re.compile(r'[A-Za-z_\uac00-\ud7a3]')
_ID_CHAR_RE = re.compile(r'[A-Za-z_0-9\uac00-\ud7a3]')

# 식별자 munch 도중에도 분리해야 하는 접미사 키워드.
# (공백 없이 변수명에 붙는 형태로 자주 쓰이는 DSL 키워드들)
_SPLIT_SUFFIXES = sorted(
    ['번째부터', '번째까지', '처음부터', '끝까지', '부터', '까지', '무작위'],
    key=len, reverse=True
)


def _munch_ident(src: str, i: int, n: int) -> Tuple[str, int]:
    """식별자를 greedy하게 소비하되, 꼬리에 붙은 DSL 키워드가 있으면 분리한다.

    예) '너비까지' → ('너비', end-2)   — '까지'는 다음 토큰으로 빠짐
        '2번째부터' 중 '번째부터' 부분 → ('번째부터', end) — 그대로 유지 후
                                         pass 2에서 KW_NTH_FROM으로 합성
        '처음부터' → 그대로, 전체가 키워드
    """
    start = i
    i += 1
    while i < n and _ID_CHAR_RE.match(src[i]):
        i += 1
    end = i
    ident = src[start:end]
    # 최장 접미사 일치로 분리 (단, 식별자 전체가 키워드면 분리하지 않음)
    for suf in _SPLIT_SUFFIXES:
        if ident == suf:
            return ident, end
        if ident.endswith(suf) and len(ident) > len(suf):
            return ident[:-len(suf)], end - len(suf)
    return ident, end


def _lex_raw(src: str) -> List[Tok]:
    """1차 토큰화: 공백/문자열/숫자/식별자/연산자/구두점을 분리."""
    toks: List[Tok] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        # 공백
        if c in ' \t\n\r':
            i += 1
            continue
        # 접두어 붙은 문자열 리터럴 (f"...", r"...", b"...", fr"...", rb"...", etc.)
        if c in 'fFrRbB':
            j = i
            while j < n and src[j] in 'fFrRbB':
                j += 1
            if j < n and src[j] in '"\'':
                quote = src[j]
                j += 1
                while j < n and src[j] != quote:
                    if src[j] == '\\' and j + 1 < n:
                        j += 2
                    else:
                        j += 1
                j = min(j + 1, n)
                toks.append(Tok("STRING", src[i:j], i, j))
                i = j
                continue
        # 문자열
        if c in '"\'':
            quote = c
            j = i + 1
            while j < n and src[j] != quote:
                if src[j] == '\\' and j + 1 < n:
                    j += 2
                else:
                    j += 1
            j = min(j + 1, n)
            toks.append(Tok("STRING", src[i:j], i, j))
            i = j
            continue
        # 숫자
        m = _NUM_RE.match(src, i)
        if m:
            toks.append(Tok("NUMBER", m.group(0), i, m.end()))
            i = m.end()
            continue
        # 구두점
        if c in '()[]{},.:':
            mp = {'(':'LPAREN',')':'RPAREN','[':'LBRACKET',']':'RBRACKET',
                  '{':'LBRACE','}':'RBRACE',',':'COMMA','.':'DOT',':':'COLON'}
            toks.append(Tok(mp[c], c, i, i + 1))
            i += 1
            continue
        # 2글자 연산자
        if i + 1 < n and src[i:i+2] in _OPS_2:
            toks.append(Tok("OP", src[i:i+2], i, i + 2))
            i += 2
            continue
        # 1글자 연산자
        if c in _OPS_1:
            toks.append(Tok("OP", c, i, i + 1))
            i += 1
            continue
        # ? (후방 물음표, 키워드 후처리에서 사용)
        if c == '?':
            toks.append(Tok("QMARK", "?", i, i + 1))
            i += 1
            continue
        # ! (not-equals 단일은 허용 안 함 — 이미 != 처리)
        # 식별자 (영문/Korean/_/숫자 — 단 시작은 숫자 불가)
        if _ID_START_RE.match(c):
            name, j = _munch_ident(src, i, n)
            toks.append(Tok("IDENT", name, i, j))
            i = j
            continue
        # 그 외 — 스킵
        i += 1
    return toks


def _phrase_to_tokens(phrase: str) -> List[Tuple[str, str]]:
    """키워드 phrase를 (type, value) 시퀀스로 분해.

    예: '가 있어?' → [('IDENT','가'), ('IDENT','있어'), ('QMARK','?')]
    """
    out = []
    for word in phrase.split():
        if word.endswith('?'):
            core = word[:-1]
            if core:
                out.append(('IDENT', core))
            out.append(('QMARK', '?'))
        else:
            out.append(('IDENT', word))
    return out


# 미리 전개 (성능)
_KW_PHRASES_EXPANDED = [
    (seq, ttype) for phrase, ttype in _KW_PHRASES
    for seq in [_phrase_to_tokens(phrase)]
]


def _collapse_kw(raw: List[Tok]) -> List[Tok]:
    """2차 패스: 식별자/물음표 시퀀스를 Korean keyword token으로 병합."""
    out: List[Tok] = []
    i = 0
    while i < len(raw):
        # 현재 위치에서 가장 긴 키워드 매칭 시도
        matched = None
        for seq, ttype in _KW_PHRASES_EXPANDED:
            if i + len(seq) > len(raw):
                continue
            ok = True
            for k, (etype, eval_) in enumerate(seq):
                tt = raw[i + k]
                if tt.type != etype or tt.value != eval_:
                    ok = False
                    break
            if ok:
                # 최장 매치 우선
                if matched is None or len(seq) > len(matched[0]):
                    matched = (seq, ttype)
        if matched:
            seq, ttype = matched
            phrase_str = ' '.join(e[1] for e in seq)
            out.append(Tok(ttype, phrase_str, raw[i].start, raw[i + len(seq) - 1].end))
            i += len(seq)
            continue
        # Python 키워드 변환
        t = raw[i]
        if t.type == "IDENT" and t.value in _PY_KW:
            out.append(Tok(_PY_KW[t.value], t.value, t.start, t.end))
            i += 1
            continue
        # 색상 식별자
        if t.type == "IDENT" and t.value in COLORS:
            out.append(Tok("COLOR", t.value, t.start, t.end))
            i += 1
            continue
        out.append(t)
        i += 1
    eof_at = raw[-1].end if raw else 0
    out.append(Tok("EOF", "", eof_at, eof_at))
    return out


def tokenize(src: str) -> List[Tok]:
    return _collapse_kw(_lex_raw(src))


def diagnose(src: str) -> Optional[ParseIssue]:
    """표현식 문법을 검사하고 실패 원인을 구조화해 반환한다."""
    if not src or not src.strip():
        return None

    try:
        toks = tokenize(src)
        parser = Parser(toks)
        parser.parse_toplevel()
        trailing = parser.peek()
        if trailing.type != "EOF":
            actual = trailing.value or trailing.type
            return ParseIssue(
                message=f"'{actual}' 뒤에 해석되지 않은 토큰이 남아 있습니다.",
                token=actual,
                expected="표현식 종료",
                column=trailing.start + 1,
            )
        return None
    except _ParseError as exc:
        token = exc.token or Tok("EOF", "", len(src), len(src))
        actual = token.value or token.type or "EOF"
        return ParseIssue(
            message=exc.message,
            token=actual,
            expected=exc.expected,
            column=token.start + 1,
        )


# ══════════════════════════════════════════════
# 표현식 AST
# ══════════════════════════════════════════════
@dataclass
class ENode: pass

@dataclass
class ERaw(ENode):          # 원본 통과
    src: str = ""

@dataclass
class EIdent(ENode):
    name: str = ""

@dataclass
class ENum(ENode):
    value: str = ""

@dataclass
class EStr(ENode):
    value: str = ""

@dataclass
class EConst(ENode):        # True / False / None
    value: str = ""

@dataclass
class EUnary(ENode):
    op: str = ""
    operand: Any = None

@dataclass
class EBinOp(ENode):
    op: str = ""
    left: Any = None
    right: Any = None

@dataclass
class ECompare(ENode):      # chained comparisons a < b < c
    first: Any = None
    ops: List[str] = field(default_factory=list)
    rest: List[Any] = field(default_factory=list)

@dataclass
class ECall(ENode):
    fn: Any = None
    args: List[Any] = field(default_factory=list)

@dataclass
class EAttr(ENode):
    obj: Any = None
    name: str = ""

@dataclass
class EIndex(ENode):
    obj: Any = None
    index: Any = None

@dataclass
class EList(ENode):
    items: List[Any] = field(default_factory=list)

@dataclass
class EDict(ENode):
    pairs: List[Tuple[Any, Any]] = field(default_factory=list)

@dataclass
class ETuple(ENode):
    items: List[Any] = field(default_factory=list)
    parens: bool = True

@dataclass
class EGroup(ENode):
    expr: Any = None

@dataclass
class ELambda(ENode):
    params: str = ""
    body: Any = None

# ── DSL 특화 ──
@dataclass
class EIntCast(ENode):
    expr: Any = None

@dataclass
class EStrCast(ENode):
    expr: Any = None

@dataclass
class ELen(ENode):
    expr: Any = None

@dataclass
class EDictKeys(ENode):
    expr: Any = None

@dataclass
class EIn(ENode):
    container: Any = None
    item: Any = None

@dataclass
class EKbHit(ENode): pass

@dataclass
class EGetKey(ENode): pass

@dataclass
class ERandom(ENode):
    lo: Any = None
    hi: Any = None

@dataclass
class ESlice(ENode):
    obj: Any = None
    start: Any = None   # None if 처음부터
    end: Any = None     # None if 끝까지

@dataclass
class EColorCall(ENode):
    color: str = ""
    expr: Any = None


# ══════════════════════════════════════════════
# 파서 (Pratt-style)
# ══════════════════════════════════════════════
class _ParseError(Exception):
    def __init__(
        self,
        message: str,
        token: Optional[Tok] = None,
        expected: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.token = token
        self.expected = expected


class Parser:
    def __init__(self, toks: List[Tok]):
        self.toks = toks
        self.pos = 0

    def peek(self, offset: int = 0) -> Tok:
        p = self.pos + offset
        if p >= len(self.toks):
            return Tok("EOF", "")
        return self.toks[p]

    def eat(self, *types: str) -> Tok:
        t = self.toks[self.pos]
        if types and t.type not in types:
            expected = " 또는 ".join(types)
            actual = t.value or t.type
            raise _ParseError(
                f"'{actual}' 위치에서 문법을 이어갈 수 없습니다.",
                token=t,
                expected=expected,
            )
        self.pos += 1
        return t

    def accept(self, type_: str, value: Optional[str] = None) -> Optional[Tok]:
        t = self.toks[self.pos]
        if t.type == type_ and (value is None or t.value == value):
            self.pos += 1
            return t
        return None

    # ── 엔트리 ──
    def parse_toplevel(self) -> ENode:
        """쉼표로 분리된 튜플(비괄호)도 허용."""
        first = self.parse_expr()
        if self.peek().type == "COMMA":
            items = [first]
            while self.accept("COMMA"):
                if self.peek().type in ("EOF",):
                    break
                items.append(self.parse_expr())
            return ETuple(items=items, parens=False)
        return first

    def parse_expr(self) -> ENode:
        return self.parse_or()

    # ── or / and / not ──
    def parse_or(self) -> ENode:
        left = self.parse_and()
        while self.peek().type == "KW_OR":
            self.eat()
            right = self.parse_and()
            left = EBinOp(op="or", left=left, right=right)
        return left

    def parse_and(self) -> ENode:
        left = self.parse_not()
        while self.peek().type == "KW_AND":
            self.eat()
            right = self.parse_not()
            left = EBinOp(op="and", left=left, right=right)
        return left

    def parse_not(self) -> ENode:
        if self.peek().type == "KW_NOT":
            self.eat()
            return EUnary(op="not", operand=self.parse_not())
        return self.parse_cmp()

    # ── 비교 (체인 지원) / '에 … 가 있어?' 포함 ──
    def parse_cmp(self) -> ENode:
        # 좌측 피연산자: in-expr 가능 (A 에 B 가 있어?)
        left = self._parse_in_expr_or_add()
        ops: List[str] = []
        rest: List[ENode] = []
        while True:
            t = self.peek()
            op = None
            if t.type == "OP" and t.value in ('==','!=','<','>','<=','>='):
                op = t.value
                self.eat()
            elif t.type == "PY_IN":
                self.eat()
                op = "in"
            elif t.type == "KW_NOT" and self.peek(1).type == "PY_IN":
                self.eat(); self.eat()
                op = "not in"
            elif t.type == "PY_IS":
                self.eat()
                if self.peek().type == "KW_NOT":
                    self.eat()
                    op = "is not"
                else:
                    op = "is"
            else:
                break
            right = self._parse_in_expr_or_add()
            ops.append(op)
            rest.append(right)
        if not ops:
            return left
        return ECompare(first=left, ops=ops, rest=rest)

    def _parse_in_expr_or_add(self) -> ENode:
        """ 'A 에 B 가 있어?'  또는 일반 add_expr. """
        left = self.parse_add()
        if self.peek().type == "KW_AT":
            save = self.pos
            self.eat()  # 에
            try:
                item = self.parse_add()
                if self.peek().type == "KW_HAS":
                    self.eat()
                    return EIn(container=left, item=item)
            except _ParseError:
                pass
            # 패턴이 완성되지 않았으면 복구
            self.pos = save
        return left

    # ── 산술 ──
    def parse_add(self) -> ENode:
        left = self.parse_mul()
        while self.peek().type == "OP" and self.peek().value in ('+', '-'):
            op = self.eat().value
            right = self.parse_mul()
            left = EBinOp(op=op, left=left, right=right)
        return left

    def parse_mul(self) -> ENode:
        left = self.parse_pow()
        while self.peek().type == "OP" and self.peek().value in ('*', '/', '//', '%'):
            op = self.eat().value
            right = self.parse_pow()
            left = EBinOp(op=op, left=left, right=right)
        return left

    def parse_pow(self) -> ENode:
        left = self.parse_unary()
        if self.peek().type == "OP" and self.peek().value == '**':
            self.eat()
            right = self.parse_pow()  # right-assoc
            return EBinOp(op='**', left=left, right=right)
        return left

    def parse_unary(self) -> ENode:
        if self.peek().type == "OP" and self.peek().value in ('+', '-'):
            op = self.eat().value
            return EUnary(op=op, operand=self.parse_unary())
        return self.parse_postfix()

    # ── postfix: 후치 DSL 연산자들 ──
    def parse_postfix(self) -> ENode:
        node = self.parse_primary()
        while True:
            t = self.peek()
            if t.type == "KW_INT":
                self.eat()
                node = EIntCast(expr=node)
            elif t.type == "KW_STR":
                self.eat()
                node = EStrCast(expr=node)
            elif t.type == "KW_LEN":
                self.eat()
                node = ELen(expr=node)
            elif t.type == "KW_DICTKEYS":
                self.eat()
                node = EDictKeys(expr=node)
            elif t.type == "KW_OF":
                self.eat()
                node = self._parse_slice(node)
            elif t.type == "KW_FROM":
                # A 부터 B 까지 무작위
                self.eat()
                hi = self.parse_add()
                self.eat("KW_TO")
                if self.peek().type != "KW_RAND":
                    raise _ParseError(
                        "'무작위' 키워드가 빠졌습니다.",
                        token=self.peek(),
                        expected="KW_RAND",
                    )
                self.eat()
                node = ERandom(lo=node, hi=hi)
            else:
                break
        return node

    def _parse_slice(self, obj: ENode) -> ENode:
        # obj 의 ... (번째부터|번째까지|처음부터|끝까지) ...
        if self.peek().type == "KW_BEGIN":
            self.eat()
            end = self.parse_postfix()
            self.eat("KW_NTH_TO")
            return ESlice(obj=obj, start=None, end=end)
        start = self.parse_postfix()
        self.eat("KW_NTH_FROM")
        if self.peek().type == "KW_END":
            self.eat()
            return ESlice(obj=obj, start=start, end=None)
        end = self.parse_postfix()
        self.eat("KW_NTH_TO")
        return ESlice(obj=obj, start=start, end=end)

    # ── primary ──
    def parse_primary(self) -> ENode:
        t = self.peek()

        if t.type == "NUMBER":
            self.eat()
            return ENum(value=t.value)

        if t.type == "STRING":
            self.eat()
            return EStr(value=t.value)

        if t.type == "KW_TRUE":
            self.eat()
            return EConst(value="True")
        if t.type == "KW_FALSE":
            self.eat()
            return EConst(value="False")
        if t.type == "PY_NONE":
            self.eat()
            return EConst(value="None")

        if t.type == "KW_KBHIT":
            self.eat()
            return EKbHit()
        if t.type == "KW_GETKEY":
            self.eat()
            return EGetKey()

        if t.type == "COLOR":
            name = t.value
            self.eat()
            if self.peek().type == "LPAREN":
                self.eat()
                inner = self.parse_expr()
                self.eat("RPAREN")
                return EColorCall(color=name, expr=inner)
            return self._parse_chain(EIdent(name=name))

        if t.type == "IDENT":
            # 단일 식별자 람다: x 받아서 expr 주는 것
            if self.peek(1).type == "KW_LAMBDA_IN":
                name = self.eat().value
                self.eat()  # KW_LAMBDA_IN
                body = self.parse_expr()
                self.eat("KW_LAMBDA_OUT")
                return ELambda(params=name, body=body)
            name = self.eat().value
            return self._parse_chain(EIdent(name=name))

        if t.type == "LPAREN":
            return self._parse_paren_or_lambda()

        if t.type == "LBRACKET":
            self.eat()
            items = []
            if self.peek().type != "RBRACKET":
                items.append(self.parse_expr())
                while self.accept("COMMA"):
                    if self.peek().type == "RBRACKET":
                        break
                    items.append(self.parse_expr())
            self.eat("RBRACKET")
            return self._parse_chain(EList(items=items))

        if t.type == "LBRACE":
            self.eat()
            pairs: List[Tuple[ENode, ENode]] = []
            if self.peek().type != "RBRACE":
                k = self.parse_expr()
                self.eat("COLON")
                v = self.parse_expr()
                pairs.append((k, v))
                while self.accept("COMMA"):
                    if self.peek().type == "RBRACE":
                        break
                    k = self.parse_expr()
                    self.eat("COLON")
                    v = self.parse_expr()
                    pairs.append((k, v))
            self.eat("RBRACE")
            return EDict(pairs=pairs)

        actual = t.value or t.type
        raise _ParseError(
            f"'{actual}'은(는) 이 위치에서 올 수 없습니다.",
            token=t,
            expected="NUMBER, STRING, IDENT, LPAREN, LBRACKET 또는 LBRACE",
        )

    def _parse_paren_or_lambda(self) -> ENode:
        """`(...)` 뒤에 '받아서'가 오면 람다로 파싱, 아니면 group/tuple."""
        save = self.pos
        self.eat("LPAREN")
        # 식별자 목록 + ) + 받아서 패턴인지 확인
        params: List[str] = []
        ok = True
        if self.peek().type != "RPAREN":
            if self.peek().type == "IDENT":
                params.append(self.eat().value)
                while self.accept("COMMA"):
                    if self.peek().type != "IDENT":
                        ok = False
                        break
                    params.append(self.eat().value)
            else:
                ok = False
        if ok and self.peek().type == "RPAREN" and self.peek(1).type == "KW_LAMBDA_IN":
            self.eat("RPAREN")
            self.eat()  # KW_LAMBDA_IN
            body = self.parse_expr()
            self.eat("KW_LAMBDA_OUT")
            return ELambda(params=", ".join(params), body=body)
        # 복구 후 group/tuple로 재파싱
        self.pos = save
        self.eat("LPAREN")
        if self.accept("RPAREN"):
            return ETuple(items=[], parens=True)
        first = self.parse_expr()
        if self.peek().type == "COMMA":
            items = [first]
            while self.accept("COMMA"):
                if self.peek().type == "RPAREN":
                    break
                items.append(self.parse_expr())
            self.eat("RPAREN")
            return self._parse_chain(ETuple(items=items, parens=True))
        self.eat("RPAREN")
        return self._parse_chain(EGroup(expr=first))

    def _parse_chain(self, node: ENode) -> ENode:
        while True:
            t = self.peek()
            if t.type == "DOT":
                self.eat()
                if self.peek().type != "IDENT":
                    raise _ParseError(
                        "'.' 뒤에 속성 이름이 필요합니다.",
                        token=self.peek(),
                        expected="IDENT",
                    )
                name = self.eat().value
                node = EAttr(obj=node, name=name)
            elif t.type == "LPAREN":
                self.eat()
                args = []
                if self.peek().type != "RPAREN":
                    args.append(self.parse_expr())
                    while self.accept("COMMA"):
                        if self.peek().type == "RPAREN":
                            break
                        args.append(self.parse_expr())
                self.eat("RPAREN")
                node = ECall(fn=node, args=args)
            elif t.type == "LBRACKET":
                self.eat()
                idx = self.parse_expr()
                self.eat("RBRACKET")
                node = EIndex(obj=node, index=idx)
            else:
                break
        return node


# ══════════════════════════════════════════════
# 코드 생성기
# ══════════════════════════════════════════════
def _g(e: ENode) -> str:
    if isinstance(e, ERaw):       return e.src
    if isinstance(e, EIdent):     return e.name
    if isinstance(e, ENum):       return e.value
    if isinstance(e, EStr):       return e.value
    if isinstance(e, EConst):     return e.value
    if isinstance(e, EUnary):
        sep = ' ' if e.op == 'not' else ''
        return f"{e.op}{sep}{_g(e.operand)}"
    if isinstance(e, EBinOp):
        return f"{_g(e.left)} {e.op} {_g(e.right)}"
    if isinstance(e, ECompare):
        parts = [_g(e.first)]
        for op, r in zip(e.ops, e.rest):
            parts.append(op)
            parts.append(_g(r))
        return " ".join(parts)
    if isinstance(e, ECall):
        return f"{_g(e.fn)}({', '.join(_g(a) for a in e.args)})"
    if isinstance(e, EAttr):
        return f"{_g(e.obj)}.{e.name}"
    if isinstance(e, EIndex):
        return f"{_g(e.obj)}[{_g(e.index)}]"
    if isinstance(e, EList):
        return f"[{', '.join(_g(i) for i in e.items)}]"
    if isinstance(e, EDict):
        return "{" + ", ".join(f"{_g(k)}: {_g(v)}" for k, v in e.pairs) + "}"
    if isinstance(e, ETuple):
        inner = ", ".join(_g(i) for i in e.items)
        if e.parens:
            # 단일 요소 튜플 처리
            if len(e.items) == 1:
                return f"({inner},)"
            return f"({inner})"
        return inner
    if isinstance(e, EGroup):
        return f"({_g(e.expr)})"
    if isinstance(e, ELambda):
        return f"(lambda {e.params}: {_g(e.body)})"
    if isinstance(e, EIntCast):   return f"int({_g(e.expr)})"
    if isinstance(e, EStrCast):   return f"str({_g(e.expr)})"
    if isinstance(e, ELen):       return f"len({_g(e.expr)})"
    if isinstance(e, EDictKeys):  return f"list({_g(e.expr)}.keys())"
    if isinstance(e, EIn):        return f"{_g(e.item)} in {_g(e.container)}"
    if isinstance(e, EKbHit):     return "msvcrt.kbhit()"
    if isinstance(e, EGetKey):    return "_get_key()"
    if isinstance(e, ERandom):    return f"random.randint({_g(e.lo)}, {_g(e.hi)})"
    if isinstance(e, ESlice):
        obj = _g(e.obj)
        if e.start is None:
            return f"{obj}[:{_g(e.end)}]"
        if e.end is None:
            return f"{obj}[{_g(e.start)}-1:]"
        return f"{obj}[{_g(e.start)}-1:{_g(e.end)}]"
    if isinstance(e, EColorCall):
        code = COLORS[e.color]
        return f'("\\033[{code}m" + str({_g(e.expr)}) + "\\033[0m")'
    return f"/* UNKNOWN: {e} */"


# ══════════════════════════════════════════════
# 공개 API
# ══════════════════════════════════════════════
def transform(src: str) -> str:
    """표현식 문자열을 Python으로 변환. 실패 시 원본 반환."""
    if not src or not src.strip():
        return src
    try:
        toks = tokenize(src)
        parser = Parser(toks)
        tree = parser.parse_toplevel()
        if parser.peek().type != "EOF":
            # 파서가 남은 토큰을 소비하지 못함 → 안전하게 원본 유지
            return src
        return _g(tree)
    except _ParseError:
        return src
    except Exception:
        return src
