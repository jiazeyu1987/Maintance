from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_PATTERN = re.compile(r"(?m)^\s*--.*$")
SYSTEM_MENU_INSERT_PATTERN = re.compile(
    r"insert\s+(?:ignore\s+)?into\s+`?system_menu`?\s*\((?P<columns>.*?)\)\s*values\s*(?P<values>.*?);",
    re.IGNORECASE | re.DOTALL,
)


class ReleaseSqlContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class MenuInsertOccurrence:
    menu_id: str
    path: Path
    line: int


def _mask_sql_comments(text: str) -> str:
    def _mask(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    without_block_comments = BLOCK_COMMENT_PATTERN.sub(_mask, text)
    return LINE_COMMENT_PATTERN.sub(_mask, without_block_comments)


def _parse_columns(columns_text: str) -> list[str]:
    columns = []
    for raw_column in columns_text.split(","):
        column = raw_column.strip().strip("`").strip().lower()
        if column:
            columns.append(column)
    return columns


def _split_top_level_csv(text: str) -> list[str]:
    values: list[str] = []
    token: list[str] = []
    depth = 0
    in_single_quote = False
    in_double_quote = False
    escape = False

    for char in text:
        if escape:
            token.append(char)
            escape = False
            continue
        if char == "\\" and (in_single_quote or in_double_quote):
            token.append(char)
            escape = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            token.append(char)
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            token.append(char)
            continue
        if not in_single_quote and not in_double_quote:
            if char == "(":
                depth += 1
            elif char == ")" and depth > 0:
                depth -= 1
            elif char == "," and depth == 0:
                values.append("".join(token).strip())
                token = []
                continue
        token.append(char)

    if token:
        values.append("".join(token).strip())
    return values


def _extract_value_tuples(values_text: str) -> list[tuple[str, int]]:
    tuples: list[tuple[str, int]] = []
    index = 0
    length = len(values_text)

    while index < length:
        while index < length and values_text[index].isspace():
            index += 1
        if index >= length or values_text[index] != "(":
            break

        start_index = index
        depth = 0
        in_single_quote = False
        in_double_quote = False
        escape = False

        while index < length:
            char = values_text[index]
            if escape:
                escape = False
                index += 1
                continue
            if char == "\\" and (in_single_quote or in_double_quote):
                escape = True
                index += 1
                continue
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                index += 1
                continue
            if char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                index += 1
                continue
            if in_single_quote or in_double_quote:
                index += 1
                continue

            if char == "(":
                depth += 1
                index += 1
                continue
            if char == ")" and depth > 0:
                depth -= 1
                if depth == 0:
                    tuples.append((values_text[start_index + 1 : index], start_index))
                    index += 1
                    break
                index += 1
                continue
            index += 1

        while index < length and values_text[index].isspace():
            index += 1
        if index < length and values_text[index] == ",":
            index += 1
            continue
        break
    return tuples


def _parse_menu_id(path: Path, line: int, raw_value: str) -> str:
    value = raw_value.strip()
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        value = value[1:-1].strip()
    if value.isdigit():
        return value
    raise ReleaseSqlContractError(
        f"system_menu.id must be an integer literal for release preflight: {path.as_posix()}:{line} -> {raw_value.strip()}"
    )


def _iter_system_menu_insert_occurrences(path: Path) -> list[MenuInsertOccurrence]:
    text = path.read_text(encoding="utf-8")
    masked = _mask_sql_comments(text)
    occurrences: list[MenuInsertOccurrence] = []

    for match in SYSTEM_MENU_INSERT_PATTERN.finditer(masked):
        columns = _parse_columns(match.group("columns"))
        if "id" not in columns:
            continue
        id_index = columns.index("id")
        values_start = match.start("values")
        original_values_text = text[match.start("values") : match.end("values")]
        for tuple_text, tuple_offset in _extract_value_tuples(original_values_text):
            fields = _split_top_level_csv(tuple_text)
            if id_index >= len(fields):
                raise ReleaseSqlContractError(
                    f"system_menu insert tuple is shorter than the declared columns: {path.as_posix()}"
                )
            line = text.count("\n", 0, values_start + tuple_offset) + 1
            menu_id = _parse_menu_id(path, line, fields[id_index])
            occurrences.append(MenuInsertOccurrence(menu_id=menu_id, path=path, line=line))
    return occurrences


def _format_duplicate_message(duplicates: dict[str, list[MenuInsertOccurrence]]) -> str:
    details = []
    for menu_id in sorted(duplicates, key=lambda item: int(item)):
        locations = ", ".join(
            f"{occurrence.path.as_posix()}:{occurrence.line}" for occurrence in duplicates[menu_id]
        )
        details.append(f"{menu_id} -> {locations}")
    return "duplicate system_menu.id detected across release SQL history: " + "; ".join(details)


def assert_release_sql_contracts(sql_paths: list[Path | str]) -> None:
    occurrences_by_menu_id: dict[str, list[MenuInsertOccurrence]] = defaultdict(list)
    for raw_path in sql_paths:
        path = Path(raw_path).resolve()
        for occurrence in _iter_system_menu_insert_occurrences(path):
            occurrences_by_menu_id[occurrence.menu_id].append(occurrence)

    duplicates = {
        menu_id: occurrences
        for menu_id, occurrences in occurrences_by_menu_id.items()
        if len(occurrences) > 1
    }
    if duplicates:
        raise ReleaseSqlContractError(_format_duplicate_message(duplicates))
