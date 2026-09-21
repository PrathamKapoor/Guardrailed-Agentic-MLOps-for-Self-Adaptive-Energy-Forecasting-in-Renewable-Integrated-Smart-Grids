# -*- coding: utf-8 -*-
"""Convert human-progress print() calls in scripts/ to logging.

Preserved on stdout (machine-readable protocol output):
  - print(json.dumps(...))
  - print('<ALLCAPS_KEY>=' + ...) style key=value lines
Converted:
  - human-progress prints -> LOGGER.info(...)
  - print(..., file=sys.stderr) -> LOGGER.error(...) (stderr kwarg stripped)
Every file is AST-validated; on any parse failure the original is restored.
"""
import ast
import io
import os
import re
import shutil

ROOT = r"C:\Projects\guardrailed-agentic-mlops-smart-grid_trial\scripts"
PREAMBLE = "import logging\n\nLOGGER = logging.getLogger(__name__)\n"

kept, converted = 0, 0

for name in sorted(os.listdir(ROOT)):
    if not name.endswith(".py"):
        continue
    path = os.path.join(ROOT, name)
    src = io.open(path, encoding="utf-8").read()
    if "print(" not in src:
        continue
    bak = path + ".bak"
    shutil.copyfile(path, bak)

    lines = src.splitlines(keepends=True)
    out = []
    n_conv = n_keep = 0
    for line in lines:
        m = re.search(r"(?<![.\w])print\(", line)
        if not m:
            out.append(line)
            continue
        call_rest = line[m.end():]
        # Machine-readable protocol output stays on stdout.
        if re.search(r"json\.dumps", call_rest) or re.match(r"\s*['\"]([A-Z0-9_]+)=", call_rest):
            out.append(line)
            n_keep += 1
            continue
        # stderr diagnostics -> LOGGER.error (strip the file kwarg on one-liners)
        if "file=sys.stderr" in line:
            new = re.sub(r",\s*file=sys\.stderr", "", line)
            new = new.replace("print(", "LOGGER.error(", 1)
            if "file=sys.stderr" in new:  # multi-line stderr call: leave untouched
                out.append(line)
                n_keep += 1
                continue
            out.append(new)
            n_conv += 1
            continue
        new = line.replace("print(", "LOGGER.info(", 1)
        new = re.sub(r",\s*flush=True\)", ")", new)
        new = re.sub(r",\s*flush=True,", ",", new)
        out.append(new)
        n_conv += 1

    candidate = "".join(out)

    # Insert the logging preamble after the last top-level import (AST-derived).
    try:
        tree = ast.parse(candidate)
    except SyntaxError as e:
        shutil.copyfile(bak, path)
        os.remove(bak)
        print(f"SKIP {name}: parse error after conversion ({e})")
        continue
    last_import = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) and node.col_offset == 0:
            last_import = max(last_import, node.end_lineno or 0)
    if last_import == 0 or "LOGGER = logging.getLogger" in candidate:
        shutil.copyfile(bak, path)
        os.remove(bak)
        print(f"SKIP {name}: no safe preamble insertion point")
        continue
    out_lines = candidate.splitlines(keepends=True)
    out_lines.insert(last_import, PREAMBLE)
    final = "".join(out_lines)

    try:
        ast.parse(final)
    except SyntaxError as e:
        shutil.copyfile(bak, path)
        os.remove(bak)
        print(f"SKIP {name}: parse error after preamble ({e})")
        continue

    io.open(path, "w", encoding="utf-8", newline="\n").write(final)
    os.remove(bak)
    converted += n_conv
    kept += n_keep
    print(f"converted {name}: {n_conv} -> LOGGER, {n_keep} kept on stdout")

print(f"TOTAL converted={converted} kept={kept}")
