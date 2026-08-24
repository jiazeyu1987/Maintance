from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_PATTERN = re.compile(r"(?m)^\s*--.*$")
SYSTEM_MENU_INSERT_PATTERN = re.compile(
    r"insert\s+(?:ignore\s+)?into\s+`?system_menu`?\s*\((?P<columns>[^)]*)\)\s*values\s*(?P<values>.*?);",
    re.IGNORECASE | re.DOTALL,
)
TEMP_TABLE_REFERENCE_PATTERN = re.compile(
    r"(?<![a-z0-9_])`?(tmp_[a-z0-9_]+)`?(?![a-z0-9_])(?!\s*\.)",
    re.IGNORECASE,
)
TEMP_TABLE_CREATE_PATTERN = re.compile(
    r"\bcreate\s+temporary\s+table\s+(?:if\s+not\s+exists\s+)?`?(tmp_[a-z0-9_]+)`?",
    re.IGNORECASE,
)
TEMP_TABLE_TEXT_COLUMN_PATTERN = re.compile(
    r"\b(?:char|varchar|tinytext|text|mediumtext|longtext|enum|set)\b",
    re.IGNORECASE,
)
TEMP_TABLE_CONTRACT_START_DATE = "20260801"


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


def _mask_sql_string_literals(text: str) -> str:
    masked = list(text)
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote is None:
            if char in ("'", '"'):
                quote = char
                masked[index] = " "
            index += 1
            continue
        if char == "\\" and index + 1 < len(text):
            if text[index + 1] != "\n":
                masked[index] = " "
                masked[index + 1] = " "
            index += 2
            continue
        if char == quote:
            if index + 1 < len(text) and text[index + 1] == quote:
                masked[index] = " "
                masked[index + 1] = " "
                index += 2
                continue
            masked[index] = " "
            quote = None
            index += 1
            continue
        if char != "\n":
            masked[index] = " "
        index += 1
    return "".join(masked)


def _iter_sql_statements(text: str) -> list[tuple[str, int]]:
    masked = _mask_sql_string_literals(_mask_sql_comments(text))
    statements: list[tuple[str, int]] = []
    start = 0
    for index, char in enumerate(masked):
        if char != ";":
            continue
        statement = masked[start:index]
        if statement.strip():
            statements.append((statement, start))
        start = index + 1
    trailing = masked[start:]
    if trailing.strip():
        statements.append((trailing, start))
    return statements


def _extract_parenthesized_text(statement: str, start: int) -> str:
    depth = 0
    for index in range(start, len(statement)):
        if statement[index] == "(":
            depth += 1
        elif statement[index] == ")":
            depth -= 1
            if depth == 0:
                return statement[start + 1 : index]
    return ""


def _extract_temp_table_text_columns(statement: str, create_match: re.Match[str]) -> set[str]:
    opening = statement.find("(", create_match.end())
    if opening < 0:
        return set()
    columns_text = _extract_parenthesized_text(statement, opening)
    if not columns_text:
        return set()
    text_columns: set[str] = set()
    for definition in _split_top_level_csv(columns_text):
        column_match = re.match(r"\s*`?([a-z0-9_]+)`?\s+", definition, re.IGNORECASE)
        if not column_match or not TEMP_TABLE_TEXT_COLUMN_PATTERN.search(definition):
            continue
        text_columns.add(column_match.group(1).lower())
    return text_columns


SQL_KEYWORDS = {
    "as",
    "and",
    "by",
    "cross",
    "from",
    "group",
    "having",
    "inner",
    "join",
    "left",
    "limit",
    "on",
    "or",
    "order",
    "right",
    "where",
}


def _extract_temp_table_aliases(statement: str, table_name: str) -> set[str]:
    aliases = {table_name.lower()}
    alias_pattern = re.compile(
        rf"\b{re.escape(table_name)}\b(?:\s+as)?\s+`?([a-z][a-z0-9_]*)`?",
        re.IGNORECASE,
    )
    for match in alias_pattern.finditer(statement):
        alias = match.group(1).lower()
        if alias not in SQL_KEYWORDS:
            aliases.add(alias)
    return aliases


def _contains_temp_text_external_equality(
    statement: str,
    table_name: str,
    text_columns: set[str],
    all_temp_aliases: set[str],
) -> bool:
    aliases = _extract_temp_table_aliases(statement, table_name)
    qualified_column = r"`?([a-z0-9_]+)`?\s*\.\s*`?([a-z0-9_]+)`?"
    for match in re.finditer(rf"(?P<left>{qualified_column})\s*=\s*(?P<right>{qualified_column})", statement, re.IGNORECASE):
        left_alias, left_column = match.group("left").split(".", 1)
        right_alias, right_column = match.group("right").split(".", 1)
        left_alias = left_alias.replace("`", "").strip().lower()
        right_alias = right_alias.replace("`", "").strip().lower()
        left_column = left_column.replace("`", "").strip().lower()
        right_column = right_column.replace("`", "").strip().lower()
        left_is_temp_text = left_alias in aliases and left_column in text_columns
        right_is_temp_text = right_alias in aliases and right_column in text_columns
        if left_is_temp_text and right_alias not in all_temp_aliases:
            return True
        if right_is_temp_text and left_alias not in all_temp_aliases:
            return True
    return False


def _find_repeated_temp_tables(statement: str) -> list[str]:
    repeated_names: set[str] = set()
    for segment in re.split(r";|\bthen\b|\bdo\b", statement, flags=re.IGNORECASE):
        counts = defaultdict(int)
        for match in TEMP_TABLE_REFERENCE_PATTERN.finditer(segment):
            counts[match.group(1).lower()] += 1
        repeated_names.update(table_name for table_name, count in counts.items() if count > 1)
    return sorted(repeated_names)


def _is_temp_table_contract_scope(path: Path) -> bool:
    migration_date = re.match(r"^(\d{8})_", path.name)
    if migration_date is None:
        return True
    # Existing migrations before this baseline are immutable history; new and actively repaired
    # migrations must satisfy the stricter MySQL temp-table contracts.
    return migration_date.group(1) >= TEMP_TABLE_CONTRACT_START_DATE


def _assert_temp_table_contracts(path: Path, text: str) -> None:
    if not _is_temp_table_contract_scope(path):
        return
    statements = _iter_sql_statements(text)
    text_temp_tables: dict[str, tuple[set[str], int, bool]] = {}
    for statement, statement_start in statements:
        create_match = TEMP_TABLE_CREATE_PATTERN.search(statement)
        if not create_match:
            continue
        table_name = create_match.group(1).lower()
        text_columns = _extract_temp_table_text_columns(statement, create_match)
        text_temp_tables[table_name] = (
            text_columns,
            statement_start,
            bool(re.search(r"\bcollate\b", statement, re.IGNORECASE)),
        )

    for statement, statement_start in statements:
        references = [match.group(1).lower() for match in TEMP_TABLE_REFERENCE_PATTERN.finditer(statement)]
        repeated = _find_repeated_temp_tables(statement)
        if repeated:
            line = text.count("\n", 0, statement_start) + 1
            names = ", ".join(repeated)
            raise ReleaseSqlContractError(
                "MySQL temp table reopen risk: the same temporary table is referenced more than once "
                f"in one SQL statement ({names}): {path.as_posix()}:{line}"
            )

        if "=" not in statement:
            continue
        all_temp_aliases = {
            alias
            for table_name in text_temp_tables
            for alias in _extract_temp_table_aliases(statement, table_name)
        }
        for table_name, (text_columns, create_start, has_collation) in text_temp_tables.items():
            if has_collation or not text_columns or table_name not in references:
                continue
            if not _contains_temp_text_external_equality(
                statement,
                table_name,
                text_columns,
                all_temp_aliases,
            ):
                continue
            line = text.count("\n", 0, create_start) + 1
            raise ReleaseSqlContractError(
                "temporary table collation must be explicit for text columns: "
                f"{table_name} in {path.as_posix()}:{line}"
            )


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
        sql_text = path.read_text(encoding="utf-8")
        _assert_temp_table_contracts(path, sql_text)
        for occurrence in _iter_system_menu_insert_occurrences(path):
            occurrences_by_menu_id[occurrence.menu_id].append(occurrence)

    duplicates = {
        menu_id: occurrences
        for menu_id, occurrences in occurrences_by_menu_id.items()
        if len(occurrences) > 1
    }
    if duplicates:
        raise ReleaseSqlContractError(_format_duplicate_message(duplicates))
