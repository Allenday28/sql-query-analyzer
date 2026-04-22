"""A dependency-free SQL SELECT analyzer and linter."""

from analyzer.parser import Query, parse, parse_script
from analyzer.linter import Warning, lint

__version__ = "0.1.0"
__all__ = ["Query", "parse", "parse_script", "Warning", "lint"]
