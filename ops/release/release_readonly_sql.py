"""Shared SQL lexer; supported by remote Python 3.6 and local Python 3.12."""
import re

FORBIDDEN_PATTERN = re.compile(
    r"\b(?:insert|update|delete|replace|create|alter|drop|truncate|rename|call|do|handler|"
    r"load|lock|unlock|grant|revoke|commit|rollback|start\s+transaction|set|outfile|dumpfile|"
    r"get_lock|release_lock|release_all_locks|load_file|sleep|benchmark|delimiter|charset|into)\b|:=|"
    r"\bfor\s+update\b|\block\s+in\s+share\s+mode\b",
    re.IGNORECASE,
)
class ReadonlySqlError(RuntimeError):
    pass


def _executable_sql(text):
    # Parse comments and literals together: quotes inside a comment must never
    # mask executable statements on a later line. Queries use doubled SQL quotes;
    # backslash commands/escapes are disallowed regardless of server sql_mode.
    if '\\' in text or '/*' in text:
        raise ReadonlySqlError('client commands, backslash escapes and block comments are forbidden')
    output = list(text)
    quote = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote is None:
            comment = char == '#' or (text.startswith('--', index) and
                       (index + 2 == len(text) or text[index + 2].isspace()))
            if comment:
                while index < len(text) and text[index] not in '\r\n':
                    output[index] = ' '
                    index += 1
                continue
            if char in ("'", '"', '`'):
                quote = char
                output[index] = " "
            index += 1
            continue
        if char == quote:
            if index + 1 < len(text) and text[index + 1] == quote:
                output[index] = output[index + 1] = " "
                index += 2
                continue
            output[index] = " "
            quote = None
            index += 1
            continue
        if char != "\n":
            output[index] = " "
        index += 1
    if quote is not None:
        raise ReadonlySqlError("unterminated SQL string literal")
    return "".join(output)


