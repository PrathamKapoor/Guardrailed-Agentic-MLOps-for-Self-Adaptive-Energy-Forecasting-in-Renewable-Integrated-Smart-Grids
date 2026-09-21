# -*- coding: utf-8 -*-
"""One-shot converter: scripts' print() -> shared stdout logger.

Rules:
- print(...) with only positional args and/or flush=True -> log.info(...)
  (flush is dropped; the stdout handler flushes per record).
- print(..., file=sys.stderr) and any other kwargs -> LEFT AS PRINT
  (deliberate stderr routing is preserved).
- Idempotent: files already importing _scriptlog are skipped.
"""
import ast
import glob
import io
import os
import sys

ROOT = r"C:\Projects\guardrailed-agentic-mlops-smart-grid_trial"

header_import = "from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL\n"

converted, skipped, failed = [], [], []
for path in sorted(glob.glob(os.path.join(ROOT, "scripts", "*.py"))):
    base = os.path.basename(path)
    if base.startswith("_"):
        continue
    src = io.open(path, encoding="utf-8").read()
    if "_scriptlog" in src or "get_logger" in src:
        skipped.append(base)
        continue
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        failed.append((base, f"syntax: {e}"))
        continue
    src_lines = src.splitlines()

    edits = []  # (start_line0, end_line0_inclusive, replacement)
    has_print = False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"):
            continue
        has_print = True
        # Only convert prints that own their entire line span: nothing but
        # whitespace before col_offset on the first line, and nothing but
        # whitespace after end_col_offset on the last line. Compound
        # one-liners (if x: print(...) / for ...: print(...)) are left alone.
        if src_lines[node.lineno - 1][:node.col_offset].strip():
            continue
        if src_lines[node.end_lineno - 1][node.end_col_offset:].strip():
            continue
        ok_kwargs = all(kw.arg == "flush" for kw in node.keywords)
        has_file = any(kw.arg == "file" for kw in node.keywords)
        if not ok_kwargs or has_file:
            continue  # leave deliberate stderr/other prints alone
        args_src = ", ".join(ast.unparse(a) for a in node.args)
        repl = "log.info(" + args_src + ")"
        edits.append((node.lineno - 1, node.end_lineno - 1, repl))

    if not has_print:
        skipped.append(base)
        continue

    # Apply edits bottom-up so earlier line numbers stay valid.
    lines = src.splitlines()
    for s0, e0, repl in sorted(edits, key=lambda x: -x[0]):
        indent = lines[s0][:len(lines[s0]) - len(lines[s0].lstrip())]
        lines[s0:e0 + 1] = [indent + repl]
    new_src = "\n".join(lines)

    # Insert the helper import after the module docstring (or at top).
    tree2 = ast.parse(new_src)
    insert_at = 0
    if (tree2.body and isinstance(tree2.body[0], ast.Expr)
            and isinstance(tree2.body[0].value, ast.Constant)
            and isinstance(tree2.body[0].value.value, str)):
        insert_at = tree2.body[0].end_lineno
    lines2 = new_src.splitlines()
    name = os.path.splitext(base)[0]
    lines2.insert(insert_at, header_import.rstrip("\n") + f"\nlog = get_logger({name!r})")
    new_src = "\n".join(lines2) + ("\n" if not new_src.endswith("\n") else "")

    try:
        ast.parse(new_src)
    except Exception as e:
        failed.append((base, f"post-convert: {e}"))
        continue
    io.open(path, "w", encoding="utf-8", newline="\n").write(new_src)
    converted.append((base, len(edits)))

print(f"converted {len(converted)} scripts, skipped {len(skipped)}, failed {len(failed)}")
for f, n in converted:
    print(f"  {f}: {n} print calls -> log.info")
for f, why in failed:
    print(f"  FAILED {f}: {why}")
