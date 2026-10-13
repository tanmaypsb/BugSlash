"""Stable source-context identities for analyzer findings.

Whitespace, line breaks, and columns are deliberately excluded. Tokens around the
reported location preserve enough source identity to distinguish separate findings.
"""
from bisect import bisect_right


def finding_identity(item, lines, language=None):
    if language is None:
        return (str(item.get("code") or ""), str(item.get("message") or ""))
    location = item.get("location") or {}
    row = location.get("row")
    column = location.get("column", 1)
    source = "\n".join(lines)
    context = _token_context(source, row, column, language)
    if not context and isinstance(row, int) and 0 < row <= len(lines):
        context = ("line", " ".join(lines[row - 1].split()))
    return str(item.get("code") or ""), str(item.get("message") or ""), context


def _token_context(source, row, column, language=None):
    if not isinstance(row, int) or row < 1:
        return ()
    lang = (language or "").lower()
    line_starts = [0]
    line_starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
    if row > len(line_starts):
        return ()

    tokens = []
    spans = []
    token_rows = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("//", index):
            newline = source.find("\n", index)
            index = len(source) if newline < 0 else newline
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = len(source) if end < 0 else end + 2
            continue
        if char == "#" and lang == "python":
            newline = source.find("\n", index)
            index = len(source) if newline < 0 else newline
            continue

        start = index
        if char in {"'", '"', chr(96)}:
            quote = char
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                    continue
                if source[index] == quote:
                    index += 1
                    break
                if source[index] == "\n" and quote != chr(96):
                    break
                index += 1
            token = source[start:index]
            if quote in {"'", '"'} and lang in {"javascript", "typescript", "python"}:
                token = "STRING:" + token[1:-1]
        elif char.isalnum() or char in {"_", "$"}:
            index += 1
            while index < len(source) and (source[index].isalnum() or source[index] in {"_", "$"}):
                index += 1
            token = source[start:index]
        else:
            index += 1
            token = char
            if lang in {"c", "cpp"} and char in {"{", "}"}:
                continue
        tokens.append(token)
        spans.append((start, index))
        token_rows.append(bisect_right(line_starts, start))

    on_line = [token_index for token_index, token_row in enumerate(token_rows) if token_row == row]
    if not on_line:
        return ()
    target = line_starts[row - 1] + max(int(column or 1) - 1, 0)
    selected = next(
        (
            token_index
            for token_index, (start, end) in enumerate(spans)
            if token_rows[token_index] == row and start <= target < end
        ),
        None,
    )
    if selected is None:
        selected = min(on_line, key=lambda token_index: abs(spans[token_index][0] - target))
    return tuple(tokens[max(0, selected - 4):selected + 5])
