# sql-query-analyzer

A small, dependency-free tool that **parses SQL SELECT statements and tells you what they do**: which tables they touch, what joins they use, what columns are referenced, and which common performance traps they fall into.

Written in pure Python — no ORM, no database connection needed. You feed it SQL text; it gives you structured analysis.

## Why

When reviewing someone's SQL (or your own from six months ago), the first question is always *"what is this thing actually doing?"* — followed by *"is it going to be slow?"*. This tool gives a structured answer to both without needing an EXPLAIN plan or a live database.

## Features

- **Structural parsing** — tables, aliases, joins, where clauses, group-by, order-by, limit
- **Join analysis** — lists every join, flags cross joins and implicit joins (comma-separated FROM)
- **Lint checks** — warns about `SELECT *`, missing `WHERE`, `NOT IN` with subqueries, non-sargable predicates
- **Multi-statement support** — splits by `;` and analyzes each
- **CLI** — `python -m analyzer lint queries.sql`

## Quick start

```bash
python -m analyzer lint examples/queries.sql
```

Example output:

```
=== query 1 ===
tables:      orders (o), customers (c)
joins:       INNER  o → c  ON o.customer_id = c.id
columns:     o.id, o.amount, c.name, c.email
where:       present
warnings:    SELECT * is discouraged — enumerate columns explicitly.
```

## What it checks

| Check | What it flags |
|-------|---------------|
| `SELECT *` | Harder to maintain; breaks when schema changes |
| Missing `WHERE` | Full table scan on what's probably a large table |
| `LIKE '%foo%'` | Non-sargable — can't use a B-tree index |
| Implicit joins (`FROM a, b WHERE ...`) | Readability and correctness risk |
| `NOT IN` with subquery | NULL-in-subquery gotcha; suggest `NOT EXISTS` |
| Cross join | Usually a bug; suggest `INNER JOIN ... ON ...` |

## Project layout

```
sql-query-analyzer/
├── src/analyzer/
│   ├── __init__.py
│   ├── tokenizer.py    # SQL → tokens
│   ├── parser.py       # tokens → structured Query object
│   ├── linter.py       # structured Query → warnings
│   └── cli.py
├── tests/
│   └── test_analyzer.py
├── examples/queries.sql
├── requirements.txt
├── LICENSE
└── .gitignore
```

## Running the tests

```bash
pytest -q
```

## Scope

This is a lightweight analyzer, not a full SQL parser. It handles the common shape of analytical queries (`SELECT … FROM … JOIN … WHERE … GROUP BY … HAVING … ORDER BY … LIMIT`). It deliberately does not try to parse DDL, CTEs, window functions, or dialect-specific syntax — the complexity budget is better spent elsewhere.

## Tech

Python 3.10+ (stdlib only) · pytest

## License

MIT
