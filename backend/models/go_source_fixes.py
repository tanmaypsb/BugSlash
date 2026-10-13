"""Conservative, compiler-guided fixes for simple unused Go declarations."""
import re

_DIAGNOSTIC = re.compile(r"(?:^|/)([^/:\\]+\.go):(\d+):(\d+):\s*(.*)$")
_IMPORT_UNUSED = re.compile(r'(?P<path>"[^"]+") imported and not used$')
_LOCAL_UNUSED = re.compile(r"declared and not used: (?P<name>[A-Za-z_][A-Za-z0-9_]*)$")
_PURE_VALUE = r"""(?:[-+]?(?:[0-9]+(?:\.[0-9]+)?|0[xX][0-9a-fA-F]+)|true|false|nil|"(?:(?:[^"\\])|\\.)*"|'(?:(?:[^'\\])|\\.)*')"""


class GoFixError(RuntimeError):
    pass


def remove_safe_unused(source: str, diagnostics: str, *, preserve_lines: bool = False) -> str:
    """Remove only compiler-confirmed imports and trivial, pure local declarations."""
    lines = source.splitlines(keepends=True)
    remove = set()
    recognized = 0
    for output_line in diagnostics.splitlines():
        match = _DIAGNOSTIC.search(output_line.strip())
        if not match:
            continue
        filename, row_text, _column, message = match.groups()
        row = int(row_text)
        if row < 1 or row > len(lines):
            continue
        current = lines[row - 1].rstrip("\r\n")
        imported = _IMPORT_UNUSED.fullmatch(message.strip())
        local = _LOCAL_UNUSED.fullmatch(message.strip())
        if imported:
            literal = imported.group("path")
            pattern = re.compile(r"\s*(?:[A-Za-z_][A-Za-z0-9_]*\s+)?" + re.escape(literal) + r"\s*,?\s*(?://.*)?")
            if not pattern.fullmatch(current):
                raise GoFixError(f"cannot safely match unused import at {filename}:{row}")
            start = row - 1
            end = row
            block_start = start
            while block_start >= 0 and "import (" not in lines[block_start]:
                block_start -= 1
                if start - block_start > 20:
                    break
            if block_start >= 0:
                block_end = start
                while block_end < len(lines) and ")" not in lines[block_end]:
                    block_end += 1
                if block_end < len(lines):
                    specs = [
                        i for i in range(block_start + 1, block_end)
                        if re.search(r'(?:(?:[A-Za-z_][A-Za-z0-9_]*)\s+)?(?:"[^"]+")', lines[i])
                    ]
                    if len(specs) == 1 and specs[0] == start:
                        start, end = block_start, block_end + 1
            for index in range(start, end):
                remove.add(index)
            recognized += 1
            continue
        if local:
            name = local.group("name")
            pattern = re.compile(r"^\s*" + re.escape(name) + r"\s*:=\s*(?:" + _PURE_VALUE + r")\s*(?://.*)?$")
            if not pattern.fullmatch(current):
                raise GoFixError(f"unused local at {filename}:{row} is not a standalone pure literal declaration")
            remove.add(row - 1)
            recognized += 1
    if recognized == 0:
        raise GoFixError("compiler output contained no safely fixable unused declarations")
    if preserve_lines:
        return "".join(("" if i in remove else line.rstrip("\r\n")) + ("\n" if line.endswith(("\n", "\r")) else "") for i, line in enumerate(lines))
    return "".join(line for i, line in enumerate(lines) if i not in remove)
