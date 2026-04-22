"""Linter: structured Query → list of warnings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from analyzer.parser import Query


@dataclass
class Warning:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def lint(q: Query) -> list[Warning]:
    warnings: list[Warning] = []

    if q.unparseable:
        warnings.append(Warning("PARSE", f"Could not parse query: {q.parse_error}"))
        return warnings

    if q.select_star:
        warnings.append(
            Warning("W001", "SELECT * is discouraged — enumerate columns explicitly.")
        )

    if q.where is None and any(j.kind != "CROSS" for j in q.joins) is False and not q.joins:
        # Single table, no WHERE. Cheapest heuristic for full-scan risk.
        warnings.append(
            Warning("W002", "No WHERE clause on a single-table query — this is a full scan.")
        )

    # Implicit (comma-separated FROM) joins
    for j in q.joins:
        if j.implicit or j.kind == "CROSS":
            warnings.append(
                Warning(
                    "W003",
                    "Implicit or CROSS join detected — use explicit INNER JOIN ... ON ... for clarity.",
                )
            )
            break

    # Non-sargable LIKE: leading wildcard
    if q.where and re.search(r"LIKE\s+'%[^']*'", q.where, re.IGNORECASE):
        warnings.append(
            Warning(
                "W004",
                "LIKE pattern with a leading %% wildcard is non-sargable — B-tree indexes cannot be used.",
            )
        )

    # NOT IN with subquery
    if q.where and re.search(r"NOT\s+IN\s*\(\s*SELECT", q.where, re.IGNORECASE):
        warnings.append(
            Warning(
                "W005",
                "NOT IN with a subquery has NULL gotchas — prefer NOT EXISTS.",
            )
        )

    # Joins missing ON clause (other than CROSS)
    for j in q.joins:
        if j.kind != "CROSS" and not j.implicit and not j.on:
            warnings.append(
                Warning(
                    "W006",
                    f"{j.kind} JOIN on {j.right.name} is missing an ON clause.",
                )
            )

    return warnings


def format_report(q: Query) -> str:
    """Human-readable report for a single query."""
    if q.unparseable:
        return f"unparseable: {q.parse_error}\n  {q.raw}"

    lines = []
    tables_str = ", ".join(t.display() for t in q.tables)
    lines.append(f"tables:    {tables_str}")

    if q.joins:
        lines.append("joins:")
        for j in q.joins:
            on_part = f" ON {j.on}" if j.on else ""
            prefix = "(implicit) " if j.implicit else ""
            lines.append(f"  - {prefix}{j.kind}  → {j.right.display()}{on_part}")

    lines.append(f"select:    {', '.join(q.select)}")

    clause_summary = []
    for name, val in [
        ("where", q.where),
        ("group by", q.group_by),
        ("having", q.having),
        ("order by", q.order_by),
        ("limit", q.limit),
    ]:
        if val is not None:
            clause_summary.append(f"{name}: {val}")
    if clause_summary:
        lines.append("clauses:   " + " | ".join(clause_summary))

    warnings = lint(q)
    if warnings:
        lines.append("warnings:")
        for w in warnings:
            lines.append(f"  {w}")
    else:
        lines.append("warnings:  none")

    return "\n".join(lines)
