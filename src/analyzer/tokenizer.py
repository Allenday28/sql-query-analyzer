"""Minimal SQL tokenizer: splits SQL text into whitespace-stripped tokens,
preserving string literals and parenthesized subqueries as single units."""

from __future__ import annotations

import re


_COMMENT_LINE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_comments(sql: str) -> str:
    """Remove `-- line` and `/* block */` comments from SQL."""
    sql = _COMMENT_BLOCK.sub(" ", sql)
    sql = _COMMENT_LINE.sub(" ", sql)
    return sql


_TOKEN_RE = re.compile(
    r"""
    '(?:[^'\\]|\\.)*'       # single-quoted string literal
    | "(?:[^"\\]|\\.)*"     # double-quoted identifier
    | \(                    # opening paren (handled specially)
    | \)                    # closing paren
    | ,                     # comma
    | ;                     # semicolon
    | \s+                   # whitespace (skipped)
    | [^\s(),;]+            # everything else as a run
    """,
    re.VERBOSE,
)


def tokenize(sql: str) -> list[str]:
    """Break SQL into tokens, grouping balanced parentheses into one token.

    Whitespace is dropped. String/identifier literals are preserved with quotes.
    Line (`-- …`) and block (`/* … */`) comments are removed before tokenizing.
    """
    sql = strip_comments(sql)
    raw = [m.group(0) for m in _TOKEN_RE.finditer(sql) if not m.group(0).isspace()]

    # Group balanced parentheses
    out: list[str] = []
    i = 0
    while i < len(raw):
        tok = raw[i]
        if tok == "(":
            depth = 1
            j = i + 1
            while j < len(raw) and depth > 0:
                if raw[j] == "(":
                    depth += 1
                elif raw[j] == ")":
                    depth -= 1
                j += 1
            out.append("".join(raw[i:j]))
            i = j
        else:
            out.append(tok)
            i += 1
    return out


def split_statements(sql: str) -> list[str]:
    """Split by top-level semicolons, ignoring those inside strings/parens."""
    sql = strip_comments(sql)
    depth = 0
    start = 0
    out: list[str] = []
    in_str = False
    i = 0
    while i < len(sql):
        ch = sql[i]
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
            elif ch == ";" and depth == 0:
                stmt = sql[start:i].strip()
                if stmt:
                    out.append(stmt)
                start = i + 1
        i += 1
    tail = sql[start:].strip()
    if tail:
        out.append(tail)
    return out
