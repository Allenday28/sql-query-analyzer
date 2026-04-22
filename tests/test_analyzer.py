"""Tests for the SQL query analyzer. Run with `pytest -q`."""

from __future__ import annotations

from analyzer.parser import parse, parse_script
from analyzer.linter import lint


def test_basic_inner_join():
    q = parse("SELECT o.id, c.name FROM orders o INNER JOIN customers c ON o.customer_id = c.id")
    assert not q.unparseable
    assert [t.name for t in q.tables] == ["orders", "customers"]
    assert q.tables[0].alias == "o"
    assert q.joins[0].kind == "INNER"
    assert q.joins[0].on == "o.customer_id = c.id"


def test_select_star_is_flagged():
    q = parse("SELECT * FROM events")
    warnings = lint(q)
    codes = {w.code for w in warnings}
    assert "W001" in codes  # SELECT *
    assert "W002" in codes  # no WHERE, single table


def test_left_join_with_clauses():
    q = parse(
        "SELECT c.region, COUNT(o.id) "
        "FROM customers c "
        "LEFT JOIN orders o ON o.customer_id = c.id "
        "GROUP BY c.region ORDER BY c.region LIMIT 10"
    )
    assert q.joins[0].kind == "LEFT"
    assert q.group_by == "c.region"
    assert q.order_by == "c.region"
    assert q.limit == "10"


def test_non_sargable_like():
    q = parse("SELECT id FROM customers WHERE name LIKE '%smith%'")
    codes = {w.code for w in lint(q)}
    assert "W004" in codes


def test_not_in_subquery():
    q = parse("SELECT id FROM products WHERE id NOT IN (SELECT product_id FROM order_items)")
    codes = {w.code for w in lint(q)}
    assert "W005" in codes


def test_implicit_join():
    q = parse("SELECT o.id FROM orders o, customers c WHERE o.customer_id = c.id")
    assert any(j.implicit for j in q.joins)
    codes = {w.code for w in lint(q)}
    assert "W003" in codes


def test_multi_statement_script():
    queries = parse_script("SELECT 1 FROM a; SELECT 2 FROM b;")
    assert len(queries) == 2
    assert queries[0].tables[0].name == "a"
    assert queries[1].tables[0].name == "b"


def test_unparseable_returns_graceful_error():
    q = parse("UPDATE foo SET x = 1")
    assert q.unparseable
    assert "SELECT" in (q.parse_error or "")


def test_join_missing_on_is_flagged():
    q = parse("SELECT * FROM a JOIN b")
    codes = {w.code for w in lint(q)}
    assert "W006" in codes
