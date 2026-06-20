from __future__ import annotations

import re
from dataclasses import dataclass


FORBIDDEN_KEYWORDS = {
    "alter",
    "analyze",
    "begin",
    "call",
    "comment",
    "commit",
    "copy",
    "create",
    "deallocate",
    "delete",
    "do",
    "drop",
    "execute",
    "grant",
    "insert",
    "into",
    "listen",
    "lock",
    "merge",
    "notify",
    "prepare",
    "refresh",
    "reindex",
    "reset",
    "revoke",
    "rollback",
    "selectinto",
    "set",
    "truncate",
    "unlisten",
    "update",
    "vacuum",
}

FORBIDDEN_PATTERNS = [
    re.compile(r"\bfor\s+(update|no\s+key\s+update|share|key\s+share)\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class SqlValidationResult:
    is_valid: bool
    cleaned_sql: str | None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "is_valid": self.is_valid,
            "cleaned_sql": self.cleaned_sql,
            "reason": self.reason,
        }


def _strip_comments_and_literals(sql: str) -> str:
    output: list[str] = []
    index = 0
    length = len(sql)

    while index < length:
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < length else ""

        if char == "-" and next_char == "-":
            end = sql.find("\n", index + 2)
            if end == -1:
                output.append(" " * (length - index))
                break
            output.append(" " * (end - index))
            index = end
            continue

        if char == "/" and next_char == "*":
            end = sql.find("*/", index + 2)
            if end == -1:
                output.append(" " * (length - index))
                break
            output.append(" " * (end + 2 - index))
            index = end + 2
            continue

        if char == "'":
            start = index
            index += 1
            while index < length:
                if sql[index] == "'" and index + 1 < length and sql[index + 1] == "'":
                    index += 2
                    continue
                if sql[index] == "'":
                    index += 1
                    break
                index += 1
            output.append(" " * (index - start))
            continue

        if char == '"':
            start = index
            index += 1
            while index < length:
                if sql[index] == '"' and index + 1 < length and sql[index + 1] == '"':
                    index += 2
                    continue
                if sql[index] == '"':
                    index += 1
                    break
                index += 1
            output.append(" " * (index - start))
            continue

        if char == "$":
            delimiter_match = re.match(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$", sql[index:])
            if delimiter_match:
                delimiter = delimiter_match.group(0)
                end = sql.find(delimiter, index + len(delimiter))
                if end == -1:
                    output.append(" " * (length - index))
                    break
                end += len(delimiter)
                output.append(" " * (end - index))
                index = end
                continue

        output.append(char)
        index += 1

    return "".join(output)


def _has_multiple_statements(scan_sql: str) -> bool:
    first_semicolon = scan_sql.find(";")
    if first_semicolon == -1:
        return False
    return bool(scan_sql[first_semicolon + 1 :].strip())


def _strip_trailing_semicolon(sql: str, scan_sql: str) -> str:
    first_semicolon = scan_sql.find(";")
    if first_semicolon != -1 and not scan_sql[first_semicolon + 1 :].strip():
        return sql[:first_semicolon].strip()

    cleaned = sql.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def validate_readonly_sql(sql: object) -> SqlValidationResult:
    if not isinstance(sql, str) or not sql.strip():
        return SqlValidationResult(False, None, "SQL must be a non-empty string.")

    if "\x00" in sql:
        return SqlValidationResult(False, None, "SQL contains a null byte.")

    scan_sql = _strip_comments_and_literals(sql)
    if _has_multiple_statements(scan_sql):
        return SqlValidationResult(False, None, "Only one SQL statement is allowed.")

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(scan_sql):
            return SqlValidationResult(False, None, "Locking clauses are not allowed.")

    tokens = [token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", scan_sql)]
    if not tokens:
        return SqlValidationResult(False, None, "SQL does not contain a query.")

    if tokens[0] not in {"select", "with"}:
        return SqlValidationResult(False, None, "Only SELECT or WITH queries are allowed.")

    forbidden = sorted(set(tokens).intersection(FORBIDDEN_KEYWORDS))
    if forbidden:
        return SqlValidationResult(False, None, f"Forbidden SQL keyword used: {', '.join(forbidden)}.")

    return SqlValidationResult(True, _strip_trailing_semicolon(sql, scan_sql))
