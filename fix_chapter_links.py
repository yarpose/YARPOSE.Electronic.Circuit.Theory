#!/usr/bin/env python3
"""Build a TOC and fix cross-chapter navigation links in Jupyter notebooks.

Layout assumed (PARENT_DIR is the folder this script scans):

    PARENT_DIR/
    |-- chapter.1/chapter1.ipynb
    |-- chapter.2/chapter2.ipynb
    |-- chapter.3/...
    +-- TOC.md                <- generated here

What it does
    1. Scans PARENT_DIR for chapter.N folders (N = 1, 2, 3, ...).
    2. Writes/updates PARENT_DIR/TOC.md with one correct link per chapter.
    3. In every chapterN.ipynb, inserts or rewrites the markdown cell that
       starts with <!--NAVIGATION--> so it contains correct
       Previous / TOC / Next links (e.g. ../chapter.2/chapter2.ipynb).
       Extra lines already in an existing navigation cell (e.g. a docx
       download link) are preserved.
    4. Repairs markdown links elsewhere in the notebooks that point to a
       chapter notebook by bare filename (chapter2.ipynb) when that link
       does not resolve, rewriting it to ../chapter.2/chapter2.ipynb.

Why links can still 404 in the browser: Jupyter only serves files under
the directory it was launched from. Start it from PARENT_DIR and reload
open tabs (F5):

    cd PARENT_DIR
    jupyter lab          # or: jupyter notebook

Usage
    python fix_chapter_links.py [PARENT_DIR] [--dry-run] [--backup]

PARENT_DIR defaults to the folder containing this script, so you can copy
the script into the parent folder and run it with no arguments.
"""

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from urllib.parse import unquote

CHAPTER_DIR_RE = re.compile(r"^chapter\.(\d+)$", re.IGNORECASE)
IPYNB_LINK_RE = re.compile(r"\]\(([^)#?]+?\.ipynb)\)")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.*?)\s*#*\s*$")
MD_CHARS_RE = re.compile(r"[*_`]")
NAV_MARKER = "<!--NAVIGATION-->"
TOC_NAME = "TOC.md"


class Chapter:
    def __init__(self, num, folder, nb_path):
        self.num = num
        self.folder = folder
        self.nb_path = nb_path
        self.title = None
        self.nb = None            # parsed notebook JSON (None if unreadable)
        self.error = None
        self.nav_action = "unchanged"   # inserted | rewritten | unchanged
        self.link_fixes = []      # (old_href, new_href)


def find_chapters(parent):
    chapters = []
    for entry in sorted(os.listdir(parent)):
        folder = os.path.join(parent, entry)
        m = CHAPTER_DIR_RE.match(entry)
        if not (m and os.path.isdir(folder)):
            continue
        num = int(m.group(1))
        nb_path = pick_notebook(folder, num)
        if nb_path:
            chapters.append(Chapter(num, folder, nb_path))
        else:
            print("  ! %s: no .ipynb found, folder skipped" % entry)
    chapters.sort(key=lambda c: c.num)
    return chapters


def pick_notebook(folder, num):
    pref = os.path.join(folder, "chapter%d.ipynb" % num)
    if os.path.isfile(pref):
        return pref
    cands = sorted(f for f in os.listdir(folder) if f.lower().endswith(".ipynb"))
    if not cands:
        return None
    for c in cands:
        if re.search(r"\b0*%d\b" % num, os.path.splitext(c)[0]):
            return os.path.join(folder, c)
    return os.path.join(folder, cands[0])


def load_notebook(ch):
    try:
        with open(ch.nb_path, "r", encoding="utf-8") as f:
            ch.nb = json.load(f)
    except (OSError, ValueError) as exc:
        ch.error = str(exc)


def cell_lines(cell):
    src = cell.get("source", [])
    if isinstance(src, str):
        return src.splitlines(True)
    return list(src)


def extract_title(nb):
    first_any = None
    for cell in nb.get("cells", []):
        if not isinstance(cell, dict) or cell.get("cell_type") != "markdown":
            continue
        for line in cell_lines(cell):
            m = HEADING_RE.match(line)
            if not m:
                continue
            text = MD_CHARS_RE.sub("", m.group(1)).strip()
            if first_any is None:
                first_any = text
            if line.lstrip().startswith("# "):
                return text
    return first_any


def rel_href(from_dir, target_path):
    return os.path.relpath(target_path, from_dir).replace(os.sep, "/")


def find_nav_cell(nb):
    for cell in nb.get("cells", []):
        if isinstance(cell, dict) and cell.get("cell_type") == "markdown":
            if NAV_MARKER in "".join(cell_lines(cell)):
                return cell
    return None


def keep_extra_lines(nav_cell):
    """Lines of an existing nav cell that are NOT generated navigation
    (e.g. a docx download link) and must survive the rewrite."""
    kept = []
    for line in cell_lines(nav_cell):
        s = line.strip()
        if not s or s == NAV_MARKER:
            continue
        if IPYNB_LINK_RE.search(line):
            continue                      # old prev/toc/next links
        if s.startswith("(") and "](" in s:
            continue                      # the ( ... ) nav wrapper line
        kept.append(line if line.endswith("\n") else line + "\n")
    return kept


def patch_nav(ch, chapters, idx):
    cells = ch.nb.get("cells")
    if cells is None:
        ch.nav_action = "skipped (no cells array)"
        return
    nav = find_nav_cell(ch.nb)
    extra = keep_extra_lines(nav) if nav else []

    parts = []
    if idx > 0:
        p = chapters[idx - 1]
        parts.append("Previous: [**%s**](%s)" % (p.title, rel_href(ch.folder, p.nb_path)))
    toc_path = os.path.join(os.path.dirname(ch.folder), TOC_NAME)
    parts.append("[**TOC**](%s)" % rel_href(ch.folder, toc_path))
    if idx < len(chapters) - 1:
        n = chapters[idx + 1]
        parts.append("Next: [**%s**](%s)" % (n.title, rel_href(ch.folder, n.nb_path)))

    new_source = [NAV_MARKER + "\n", "( " + " | ".join(parts) + " )\n"]
    if extra:
        new_source.append("\n")
        new_source.extend(extra)

    if nav is not None:
        if "".join(cell_lines(nav)) == "".join(new_source):
            ch.nav_action = "unchanged"
        else:
            nav["source"] = new_source
            ch.nav_action = "rewritten"
    else:
        cell = {"cell_type": "markdown", "metadata": {}, "source": new_source}
        if ch.nb.get("nbformat") == 4 and (
            ch.nb.get("nbformat_minor", 0) >= 5
            or any(isinstance(c, dict) and "id" in c for c in cells)
        ):
            cell["id"] = "nav-" + uuid.uuid4().hex[:8]
        cells.insert(0, cell)
        ch.nav_action = "inserted"


def fix_links(ch, known):
    """Rewrite broken bare-filename links to the right chapter notebook."""
    if ch.nb is None:
        return
    for cell in ch.nb.get("cells", []):
        if not isinstance(cell, dict) or cell.get("cell_type") not in ("markdown", "raw"):
            continue
        fixes_here = []
        out_lines = []
        for line in cell_lines(cell):
            def repl(m):
                href = m.group(1).strip()
                if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", href) or href.startswith(("#", "/")):
                    return m.group(0)          # URL, anchor or server-absolute
                target = os.path.normpath(os.path.join(ch.folder, unquote(href)))
                if os.path.exists(target):
                    return m.group(0)          # already resolves, leave it
                dest = known.get(os.path.basename(unquote(href)).lower())
                if dest:
                    new_href = rel_href(ch.folder, dest)
                    fixes_here.append((href, new_href))
                    return "](%s)" % new_href
                return m.group(0)
            out_lines.append(IPYNB_LINK_RE.sub(repl, line))
        if fixes_here:
            cell["source"] = out_lines
            ch.link_fixes.extend(fixes_here)


def dump_notebook(ch):
    with open(ch.nb_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ch.nb, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def write_toc(parent, chapters):
    lines = ["# Table of Contents", ""]
    for i, ch in enumerate(chapters, 1):
        href = rel_href(parent, ch.nb_path)
        title = ch.title or "Chapter %d" % ch.num
        lines.append("%d. [**Chapter %d — %s**](%s)" % (i, ch.num, title, href))
    lines.append("")
    content = "\n".join(lines)
    path = os.path.join(parent, TOC_NAME)
    try:
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return path, False
    except OSError:
        pass
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return path, True


def report(ch, dry_run):
    print('  [%s] %s — "%s"' % (os.path.basename(ch.folder),
                                os.path.basename(ch.nb_path),
                                ch.title or "?"))
    status = ch.nav_action
    if dry_run and status in ("inserted", "rewritten"):
        status += " (dry run, not saved)"
    print("      nav cell : %s" % status)
    if ch.link_fixes:
        print("      links    : %d fixed" % len(ch.link_fixes))
        for old, new in ch.link_fixes:
            print("          %s -> %s" % (old, new))


def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Build TOC.md and fix navigation links across chapter.N folders.")
    ap.add_argument("parent", nargs="?",
                    default=os.path.dirname(os.path.abspath(__file__)),
                    help="parent folder containing chapter.N folders (default: this script's folder)")
    ap.add_argument("--dry-run", action="store_true", help="show changes without writing any file")
    ap.add_argument("--backup", action="store_true", help="save each patched notebook as <name>.ipynb.bak")
    args = ap.parse_args(argv)

    parent = os.path.abspath(args.parent)
    if not os.path.isdir(parent):
        ap.error("not a directory: %s" % parent)

    print("Scanning %s" % parent)
    chapters = find_chapters(parent)
    if not chapters:
        print("No chapter.N folders with notebooks found. Nothing to do.")
        return 1

    for ch in chapters:
        load_notebook(ch)
        if ch.nb is None:
            print("  ! %s: unreadable (%s) — TOC link only, no patching" % (ch.nb_path, ch.error))
            ch.title = "Chapter %d" % ch.num
        else:
            ch.title = extract_title(ch.nb) or "Chapter %d" % ch.num

    known = {os.path.basename(c.nb_path).lower(): c.nb_path for c in chapters}

    for idx, ch in enumerate(chapters):
        if ch.nb is None:
            report(ch, args.dry_run)
            continue
        patch_nav(ch, chapters, idx)
        fix_links(ch, known)
        will_write = ch.nav_action in ("inserted", "rewritten") or ch.link_fixes
        if will_write and not args.dry_run:
            if args.backup:
                shutil.copy2(ch.nb_path, ch.nb_path + ".bak")
            dump_notebook(ch)
        report(ch, args.dry_run)

    if args.dry_run:
        toc_status = "(dry run, not saved)"
    else:
        _, toc_changed = write_toc(parent, chapters)
        toc_status = "written" if toc_changed else "unchanged"
    print("TOC        : %s %s" % (os.path.join(parent, TOC_NAME), toc_status))

    print("\nDone. Note: Jupyter must be launched from %s" % parent)
    print("    cd \"%s\"  &&  jupyter lab   (or: jupyter notebook)" % parent)
    print("Then reload open notebook tabs (F5) so the browser picks up the patched files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
