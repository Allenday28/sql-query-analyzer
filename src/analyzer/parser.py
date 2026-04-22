"""Structural parser for SELECT queries. Extracts tables, joins, columns,
and clause presence. Intentionally conservative — it handles common analytical
queries cleanly and reports "unparseable" on shapes outside its grammar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from analyzer.tokenizer import tokenize, split_statements


JOIN_KINDS = {
    "JOIN": "INNER",
    "INNER": "INNER",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT",
    "FULL": "FULL",
    "CROSS": "CROSS",
    "OUTER": "OUTER",
}


@dataclass
class TableRef:
    name: str
    alias: str | None = None

    def display(self) -> str:
        return f"{self.name} ({self.alias})" if self.alias else self.name


@dataclass
class Join:
    kind: str
    right: TableRef
    on: str | None = None
    implicit: bool = False


@dataclass
class Query:
    raw: str
    select: list[str] = field(default_factory=list)
    tables: list[TableRef] = field(default_factory=list)
    joins: list[Join] = field(default_factory=list)
    where: str | None = None
    group_by: str | None = None
    having: str | None = None
    order_by: str | None = None
    limit: str | None = None
    unparseable: bool = False
    parse_error: str | None = None

    @property
    def select_star(self) -> bool:
        return any(item.strip() == "*" or item.strip().endswith(".*") for item in self.select)


def _upper(tok: str) -> str:
    return tok.upper()


def _split_list(s: str) -> list[str]:
    """Split on top-level commas (ignoring commas inside parens/strings)."""
    out, depth, start, in_str = [], 0, 0, False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_str = False
        else:
            if ch == "'":
                in_str = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append(s[start:i].strip())
                start = i + 1
        i += 1
    tail = s[start:].strip()
    if tail:
        out.append(tail)
    return out


def _parse_table_ref(text: str) -> TableRef:
    """Parse 'orders o', 'orders AS o', or just 'orders'."""
    parts = re.split(r"\s+(?:AS\s+)?", text.strip(), flags=re.IGNORECASE, maxsplit=1)
    if len(parts) == 1:
        return TableRef(name=parts[0].strip())
    return TableRef(name=parts[0].strip(), alias=parts[1].strip())


def parse(sql: str) -> Query:
    q = Query(raw=sql.strip())
    try:
        return _parse_impl(sql, q)
    except Exception as e:
        q.unparseable = True
        q.parse_error = str(e)
        return q


def _parse_impl(sql: str, q: Query) -> Query:
    tokens = tokenize(sql)
    if not tokens or _upper(tokens[0]) != "SELECT":
        q.unparseable = True
        q.parse_error = "not a SELECT statement"
        return q

    # Find the clause boundaries by keyword position.
    upper_tokens = [_upper(t) for t in tokens]

    def find(word: str, start: int = 0) -> int:
        try:
            return upper_tokens.index(word, start)
        except ValueError:
            return -1

    sel_start = 1
    from_idx = find("FROM", sel_start)
    if from_idx == -1:
        q.unparseable = True
        q.parse_error = "missing FROM clause"
        return q

    # SELECT list is between SELECT and FROM
    select_list_text = " ".join(tokens[sel_start:from_idx])
    q.select = _split_list(select_list_text)

    # Scan tokens after FROM for JOIN/WHERE/GROUP/HAVING/ORDER/LIMIT boundaries
    boundary_words = {"WHERE", "GROUP", "HAVING", "ORDER", "LIMIT"}

    # First collect the FROM clause (from_idx + 1 up to first boundary or JOIN)
    idx = from_idx + 1
    from_end = idx
    while from_end < len(tokens):
        w = upper_tokens[from_end]
        if w in boundary_words or w in JOIN_KINDS or w == "ON":
            break
        from_end += 1

    from_text = " ".join(tokens[idx:from_end])
    # Might be comma-separated (implicit join)
    table_parts = _split_list(from_text)
    primary = _parse_table_ref(table_parts[0])
    q.tables.append(primary)
    for extra in table_parts[1:]:
        ref = _parse_table_ref(extra)
        q.tables.append(ref)
        q.joins.append(Join(kind="IMPLICIT_CROSS", right=ref, implicit=True))

    # Walk JOIN clauses
    idx = from_end
    while idx < len(tokens) and upper_tokens[idx] in JOIN_KINDS:
        kind_tokens = []
        while idx < len(tokens) and upper_tokens[idx] in JOIN_KINDS:
            kind_tokens.append(upper_tokens[idx])
            idx += 1
        # Normalize: e.g. ['LEFT','OUTER','JOIN'] → 'LEFT'; ['INNER','JOIN'] → 'INNER'
        kind = _normalize_join(kind_tokens)
        # Next tokens: table ref (possibly with alias, up to ON or boundary)
        table_start = idx
        while idx < len(tokens):
            w = upper_tokens[idx]
            if w == "ON" or w in boundary_words or w in JOIN_KINDS:
                break
            idx += 1
        right_text = " ".join(tokens[table_start:idx])
        right = _parse_table_ref(right_text)
        q.tables.append(right)

        on_clause = None
        if idx < len(tokens) and upper_tokens[idx] == "ON":
            idx += 1  # skip ON
            on_start = idx
            while idx < len(tokens):
                w = upper_tokens[idx]
                if w in boundary_words or w in JOIN_KINDS:
                    break
                idx += 1
            on_clause = " ".join(tokens[on_start:idx])

        q.joins.append(Join(kind=kind, right=right, on=on_clause))

    # Parse remaining clauses
    def clause_text(word: str, start: int) -> tuple[str | None, int]:
        pos = find(word, start)
        if pos == -1:
            return None, start
        # GROUP BY / ORDER BY need to consume "BY"
        content_start = pos + 1
        if word in ("GROUP", "ORDER") and content_start < len(tokens) and upper_tokens[content_start] == "BY":
            content_start += 1
        end = content_start
        while end < len(tokens):
            w = upper_tokens[end]
            if w in boundary_words and end != pos:
                break
            end += 1
        return " ".join(tokens[content_start:end]) or None, end

    text, idx = clause_text("WHERE", idx)
    q.where = text
    text, idx = clause_text("GROUP", idx)
    q.group_by = text
    text, idx = clause_text("HAVING", idx)
    q.having = text
    text, idx = clause_text("ORDER", idx)
    q.order_by = text
    text, idx = clause_text("LIMIT", idx)
    q.limit = text

    return q


def _normalize_join(kind_tokens: list[str]) -> str:
    if "CROSS" in kind_tokens:
        return "CROSS"
    if "LEFT" in kind_tokens:
        return "LEFT"
    if "RIGHT" in kind_tokens:
        return "RIGHT"
    if "FULL" in kind_tokens:
        return "FULL"
    return "INNER"


def parse_script(sql: str) -> list[Query]:
    """Parse a script containing multiple SELECT statements separated by ;."""
    return [parse(stmt) for stmt in split_statements(sql)]
