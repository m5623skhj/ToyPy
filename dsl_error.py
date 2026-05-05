# dsl_errors.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class ErrorKind(Enum):
    UNKNOWN_COMMAND = ("❓", "알 수 없는 명령")
    MISSING_COLON   = ("🔲", "콜론 누락")
    PARSE_FAILED    = ("💥", "파싱 실패")
    CODEGEN_FAILED  = ("⚙️",  "코드 생성 실패")
    SUSPICIOUS_LINE = ("⚠️",  "변환 의심 줄")

    def __init__(self, icon: str, label: str):
        self.icon = icon
        self.label = label


@dataclass
class DSLError:
    kind: ErrorKind
    line_no: int
    source_line: str          # 실제 소스 줄
    message: str = ""
    suggestion: str = ""      # 어떻게 고치면 되는지
    hint_code: str = ""       # 올바른 예시 코드

    def format(self, source_lines: Optional[List[str]] = None) -> str:
        """터미널에 출력할 에러 블록 생성"""
        out = []
        sep = "─" * 52

        out.append(sep)
        out.append(
            f"  {self.kind.icon} [{self.kind.label}]  "
            f"{'─' * max(0, 46 - len(self.kind.label))}"
        )
        out.append(f"  📍 {self.line_no}번째 줄")
        out.append("")

        # ── 소스 컨텍스트 (앞뒤 줄 포함) ──────────────────
        if source_lines and 0 < self.line_no <= len(source_lines):
            ctx_start = max(0, self.line_no - 2)
            ctx_end   = min(len(source_lines), self.line_no + 1)
            for i in range(ctx_start, ctx_end):
                is_target = (i == self.line_no - 1)
                prefix = "→ " if is_target else "  "
                # 표시 형식: "  →  7 │ 내용"
                # prefix 2 + prefix 2 + lineno 3 + " │ " 3 = 10칸
                out.append(f"  {prefix}{i+1:3d} │ {source_lines[i].rstrip()}")
                if is_target:
                    # 캐럿 줄: "        │ " (공백 8 + "│ " 2 = 10칸, 위 줄과 정렬 일치)
                    indent = len(source_lines[i]) - len(source_lines[i].lstrip())
                    caret_len = max(1, len(self.source_line.strip()))
                    out.append(f"        │ {' ' * indent}{'^' * caret_len}")
        else:
            # source_lines 없으면 source_line만 표시
            out.append(f"        │ {self.source_line.rstrip()}")

        # ── 진단 정보 ──────────────────────────────────────
        if self.message:
            out.append("")
            out.append(f"  🔎 원인: {self.message}")
        if self.suggestion:
            out.append(f"  💡 제안: {self.suggestion}")
        if self.hint_code:
            out.append(f"  📝 예시: {self.hint_code}")

        out.append(sep)
        return "\n".join(out)