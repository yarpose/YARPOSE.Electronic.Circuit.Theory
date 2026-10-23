#!/usr/bin/env python3
"""Build a styled TOC.md, bottom navigation, Docs/ docx moves, and links (v4).

Layout assumed (PARENT_DIR is the folder this script scans):

    PARENT_DIR/
    |-- README.md             <- project README, defines TOC text/style and
    |                            the copyright/contact section format
    |-- chapter.1/
    |   |-- chapter1.ipynb
    |   |-- chapter1.docx     <- moved into chapter.1/Docs/ by this script
    |   +-- Docs/             <- created if needed
    |-- chapter.2/chapter2.ipynb
    |-- chapter.3/...
    +-- TOC.md                <- generated here

What it does
    1. Scans PARENT_DIR for chapter.N folders (N = 1, 2, 3, ...).
    2. Writes PARENT_DIR/TOC.md containing the FULL TEXT AND STYLE of the
       project README, with the entries of its "Course contents" list turned
       into the real, correct links to the scanned chapter notebooks.
    3. Moves every .docx sitting directly in chapter.N/ into
       chapter.N/Docs/ (created if needed), then updates the chapter
       notebook so its .docx links point at ./Docs/<file>.
    4. Ensures every chapterN.ipynb has BOTH a top and a bottom
       <!--NAVIGATION--> markdown cell with correct Previous / TOC / Next
       links (e.g. ../chapter.2/chapter2.ipynb). The bottom cell is appended
       only when missing; extra lines in existing nav cells (e.g. a docx
       download link) are preserved.
    5. Repairs markdown links elsewhere in the notebooks that point to a
       chapter notebook or docx by bare filename when the link does not
       resolve, rewriting it to the correct relative path.
    6. Appends "Copyrights and usage terms:" and "How to contact us"
       sections crediting 2026 Abbas Kohan and M. B. Ghaznavi-Ghoushchi,
       in the format defined by the project README. If the README source
       already contains those 2026 sections they are kept verbatim and not
       duplicated.

README source priority:
    --readme PATH  >  PARENT_DIR/readme.md (any letter case)
    >  --readme-url download (only if explicitly given)
    >  embedded copy of the project README (always available, offline-safe).
Use --no-readme for the plain TOC (chapter links only, plus the
copyright/contact sections).

Note: the README references images relative to the repo (media/...). For
them to render, the media/ folder must exist next to the generated TOC.md.

Why links can still 404 in the browser: Jupyter only serves files under
the directory it was launched from. Start it from PARENT_DIR and reload
open tabs (F5):

    cd PARENT_DIR
    jupyter lab          # or: jupyter notebook

Usage
    python fix_chapter_links_v4.py [PARENT_DIR] [--dry-run] [--backup]
                                   [--readme PATH] [--readme-url URL]
                                   [--no-readme] [--no-copyright]

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

EMBEDDED_README = r"""# Revitalized Electronic Circuit Theory: Devices, Models, and Circuits (Henry J. Zimmermann, Samuel J. Mason)
By [Abbas Kohan] and [M. B. Ghaznavi-Ghoushchi](https://www.linkedin.com/in/ghaznavi-ghoushchi/).

Version 2026.01

![Electronic Circuit Theory: Devices, Models, and Circuits](media/1.jpg)

A Full redo open-source/Full with Python/ interactive course for all who like to know "What are the basics of electronics circuit design?" from scratch to basic applications.
This is the repo of **Electronic Circuit Theory: Devices, Models, and Circuits for ALL**  project. It brings ALL of **Fundamentals of Electronics** into browser via Python jupyter including examples, plots, equations and simulations.


This project is based on:

1. Python
2. Jupyter notebook and run-able on Google colab
3. schemdraw library
4. PySpice simulation wrapper
5. ElevenLabs.io (ML generated human voices for whole the project)
6. Good learning resources
7. ... and days and hours of hard work (we did it in about 11 months!)



# Course contents:

1. [Basics of physics for semiconductors](chapter.1/chapter1.ipynb)
2. [Basics of circuit theory](chapter.2/chapter2.ipynb)
3. [Diode theory and circuits](chapter.3/chapter3.ipynb)
4. [Bipolar Junction Transistor (BJT)](chapter.4/chapter4.ipynb)
5. [Metal-Oxide Semiconductor Field Effect Transistor (MOS)](chapter.5/chapter5.ipynb)
6. [How to install and use required tools/libraries](chapter.6/chapter6.ipynb)
7. [Project Codes All-In-One (AIO)](chapter.7/chapter7.ipynb)
8. [**Chapter 8 — 8.1 Introduction**](chapter.8/chapter8.ipynb)
9. [**Chapter 9 — By Abbas Kohan and M. B. Ghaznavi-Ghoushchi**](Chapter.9/chapter9.ipynb)
10. [**Chapter 10 — 10.1 Introduction**](chapter.10/chapter10.ipynb)
11. [**Chapter 11 — 11.1 Introduction**](chapter.11/chapter11.ipynb)
12. [**Chapter 12 — Logic Design with MOSFETs 2**](chapter.12/chapter.12.ipynb)

# Main features:

# ALL Circuits are drawn via Python in Jupyter
ALL the schematics of the circuits are reproduced utilizing ```schemdraw``` python library.

# Circuit simulation utilizing PySpice
ALL the simulations of the circuits are performed utilizing ```PySpice``` python library.

# Interactive features in circuit draw and simulation
ALL the interactive features in circuit re-draw and parameter modifications are implemented utilizing ```ipywidgets``` python library.

# Circuit explanation utilizing LaTeX
ALL the interactive features in circuit re-draw and parameter modifications are implemented utilizing $LaTeX$ 

# All in one bunch of codes, figures, audio, etc.
ALL of codes, figures, ipynb, docx are ready to download and re-use under the copyright notice verbatim. 

# Unique "Spoon" style of Jupyter Python coding 
We followed stand-alone coding for each example just like insert your spoon in Dessert and eat each section without need to run its upper or lower jupyter cells which usually you see in the most of ```jupyter notebooks``` samples. This enables reader to look at each example as a fully separated and functional code.

# Fully open-source course
The project is totally open-source in hope of help to extended ease of understating for "Fundamentals of Electronics".

# Contents (most) are in Compliance with "Basics of Electronic Circuits - Electronics I"
The contents of this project are ready to use for  second year undergraduate courses like:
 1. Basics of Electronics
 2. Electronics I
 3. Electronic Circuit Theory.


---
## Copyrights and usage terms:
Licensing terms for Project **Revitalized Electronic Circuit Theory: Devices, Models, and Circuits (Henry J. Zimmermann, Samuel J. Mason)**

This project is licensed under the terms of the 3-Clause BSD License (also known as New or Revised or Modified BSD License, or the BSD-3-Clause license), as follows:

Copyright (c) 2026 Abbas Kohan and M. B. Ghaznavi-Ghoushchi. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
```
Redistributions of any part of this project must retain the above copyright notice, this list of conditions and the following disclaimer. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
```

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

---

# How to contact us
You can reach us from the following links:

- Abbas Kohan
- [M. B. Ghaznavi-Ghoushchi](https://www.linkedin.com/in/ghaznavi-ghoushchi/)
- [ghoushchi (GitHub)](https://github.com/ghoushchi)
- [YARPOSE - A Dejavu project in EDA (GitHub)](https://github.com/yarpose)"""

CHAPTER_DIR_RE = re.compile(r"^chapter\.(\d+)$", re.IGNORECASE)
IPYNB_LINK_RE = re.compile(r"\]\(([^)#?]+?\.ipynb)\)")
DOCX_LINK_RE = re.compile(r"\]\(([^)#?]+?\.docx)\)", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.*?)\s*#*\s*$")
MD_CHARS_RE = re.compile(r"[*_`]")
NAV_MARKER = "<!--NAVIGATION-->"
TOC_NAME = "TOC.md"
COURSE_HEADING_RE = re.compile(r"^#{1,6}\s+Course\s+contents", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.*?)\s*$")

PROJECT_TITLE = ("Revitalized Electronic Circuit Theory: Devices, Models, "
                 "and Circuits (Henry J. Zimmermann, Samuel J. Mason)")
COPYRIGHT_YEAR = "2026"
COPYRIGHT_HOLDERS = "Abbas Kohan and M. B. Ghaznavi-Ghoushchi"
CONTACT_LINKS = [
    ("Abbas Kohan", ""),
    ("M. B. Ghaznavi-Ghoushchi", "https://www.linkedin.com/in/ghaznavi-ghoushchi/"),
    ("ghoushchi (GitHub)", "https://github.com/ghoushchi"),
    ("YARPOSE - A Dejavu project in EDA (GitHub)", "https://github.com/yarpose"),
]


class Chapter:
    def __init__(self, num, folder, nb_path):
        self.num = num
        self.folder = folder
        self.nb_path = nb_path
        self.title = None
        self.nb = None            # parsed notebook JSON (None if unreadable)
        self.error = None
        self.nav_top_action = "unchanged"     # inserted | rewritten | unchanged
        self.nav_bottom_action = "unchanged"  # appended | rewritten | unchanged
        self.link_fixes = []      # (old_href, new_href) for .ipynb links
        self.docx_moved = []      # docx file names moved into Docs/
        self.docx_fixes = []      # (old_href, new_href) for .docx links


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


def move_docx(ch, dry_run):
    """Move .docx files sitting directly in the chapter folder into
    chapter.N/Docs/. Returns (moved_names, docx_names_in_docs_after)."""
    docs_dir = os.path.join(ch.folder, "Docs")
    to_move = sorted(
        entry for entry in os.listdir(ch.folder)
        if entry.lower().endswith(".docx")
        and os.path.isfile(os.path.join(ch.folder, entry))
    )
    moved = []
    if not dry_run and to_move:
        os.makedirs(docs_dir, exist_ok=True)
        for entry in to_move:
            dst = os.path.join(docs_dir, entry)
            if os.path.exists(dst):
                print("  ! %s: Docs/%s already exists — %s left in place"
                      % (os.path.basename(ch.folder), entry, entry))
                continue
            shutil.move(os.path.join(ch.folder, entry), dst)
            moved.append(entry)
    names = set()
    if os.path.isdir(docs_dir):
        names.update(f for f in os.listdir(docs_dir) if f.lower().endswith(".docx"))
    if dry_run:
        names.update(to_move)
        return to_move, sorted(names)      # report what WOULD be moved
    names.update(moved)
    return moved, sorted(names)


def ensure_nav(ch, chapters, idx):
    """Ensure the notebook has a top and a bottom <!--NAVIGATION--> cell
    carrying the current Previous / TOC / Next links."""
    cells = ch.nb.get("cells")
    if cells is None:
        ch.nav_top_action = ch.nav_bottom_action = "skipped (no cells array)"
        return
    nav_cells = [c for c in cells
                 if isinstance(c, dict) and c.get("cell_type") == "markdown"
                 and NAV_MARKER in "".join(cell_lines(c))]
    last = cells[-1] if cells else None
    top = nav_cells[0] if nav_cells else None
    bottom = nav_cells[-1] if len(nav_cells) >= 2 else None
    if len(nav_cells) == 1 and nav_cells[0] is last:
        top, bottom = None, nav_cells[0]   # a lone nav cell at the end is a footer

    parts = []
    if idx > 0:
        p = chapters[idx - 1]
        parts.append("Previous: [**%s**](%s)" % (p.title, rel_href(ch.folder, p.nb_path)))
    toc_path = os.path.join(os.path.dirname(ch.folder), TOC_NAME)
    parts.append("[**TOC**](%s)" % rel_href(ch.folder, toc_path))
    if idx < len(chapters) - 1:
        n = chapters[idx + 1]
        parts.append("Next: [**%s**](%s)" % (n.title, rel_href(ch.folder, n.nb_path)))
    core = [NAV_MARKER + "\n", "( " + " | ".join(parts) + " )\n"]

    def set_cell(cell):
        extra = keep_extra_lines(cell)
        new_source = core + (["\n"] + extra if extra else [])
        if "".join(cell_lines(cell)) == "".join(new_source):
            return "unchanged"
        cell["source"] = new_source
        return "rewritten"

    def new_cell(tag):
        cell = {"cell_type": "markdown", "metadata": {}, "source": list(core)}
        if ch.nb.get("nbformat") == 4 and (
            ch.nb.get("nbformat_minor", 0) >= 5
            or any(isinstance(c, dict) and "id" in c for c in cells)
        ):
            cell["id"] = tag + uuid.uuid4().hex[:8]
        return cell

    if top is not None:
        ch.nav_top_action = set_cell(top)
    else:
        cells.insert(0, new_cell("nav-"))
        ch.nav_top_action = "inserted"
    if bottom is not None:
        ch.nav_bottom_action = set_cell(bottom)
    else:
        cells.append(new_cell("navbot-"))
        ch.nav_bottom_action = "appended"


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


def fix_docx_links(ch, docs_names):
    """Point broken .docx links at the Docs/ subfolder."""
    if ch.nb is None or not docs_names:
        return
    by_lower = {name.lower(): name for name in docs_names}
    for cell in ch.nb.get("cells", []):
        if not isinstance(cell, dict) or cell.get("cell_type") not in ("markdown", "raw"):
            continue
        fixes_here = []
        out_lines = []
        for line in cell_lines(cell):
            def repl(m):
                href = m.group(1).strip()
                if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", href) or href.startswith(("#", "/")):
                    return m.group(0)
                actual = by_lower.get(os.path.basename(unquote(href)).lower())
                if actual:                 # canonical post-move location is Docs/
                    new_href = "./Docs/" + actual
                    if new_href != href:
                        fixes_here.append((href, new_href))
                        return "](%s)" % new_href
                    return m.group(0)      # already points at Docs/<file>
                target = os.path.normpath(os.path.join(ch.folder, unquote(href)))
                if os.path.exists(target):
                    return m.group(0)      # some other docx, resolves fine
                return m.group(0)
            out_lines.append(DOCX_LINK_RE.sub(repl, line))
        if fixes_here:
            cell["source"] = out_lines
            ch.docx_fixes.extend(fixes_here)


def dump_notebook(ch):
    with open(ch.nb_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ch.nb, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def download_readme(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "fix_chapter_links_v4"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def find_local_readme(parent):
    for entry in sorted(os.listdir(parent)):
        path = os.path.join(parent, entry)
        if entry.lower() == "readme.md" and os.path.isfile(path):
            return path
    return None


def resolve_readme(parent, args):
    """Return (readme_text, source_description) or (None, None) for --no-readme."""
    if args.no_readme:
        return None, None
    if args.readme:
        with open(args.readme, "r", encoding="utf-8") as f:
            return f.read(), "--readme %s" % args.readme
    local = find_local_readme(parent)
    if local:
        with open(local, "r", encoding="utf-8") as f:
            return f.read(), "local %s" % os.path.basename(local)
    if args.readme_url:
        try:
            return download_readme(args.readme_url), "downloaded %s" % args.readme_url
        except Exception as exc:
            print("  ! README download failed (%s) — using embedded copy" % exc)
    return EMBEDDED_README, "embedded fallback copy"


def build_rich_toc(readme_text, chapters, parent):
    """README text and style, with its Course-contents list turned into
    the real chapter links."""
    lines = readme_text.splitlines()
    by_num = {ch.num: ch for ch in chapters}
    out = []
    done = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not done and COURSE_HEADING_RE.match(line.strip()):
            out.append(line)
            i += 1
            while i < n and lines[i].strip() == "":
                out.append(lines[i])
                i += 1
            seen = set()
            while i < n and LIST_ITEM_RE.match(lines[i]):
                m = LIST_ITEM_RE.match(lines[i])
                num, text = int(m.group(1)), m.group(2).strip()
                seen.add(num)
                ch = by_num.get(num)
                if ch:
                    out.append("%d. [%s](%s)" % (num, text, rel_href(parent, ch.nb_path)))
                else:
                    out.append(lines[i].rstrip())
                i += 1
            for ch in chapters:
                if ch.num not in seen:
                    title = ch.title or "Chapter %d" % ch.num
                    out.append("%d. [**Chapter %d — %s**](%s)"
                               % (ch.num, ch.num, title, rel_href(parent, ch.nb_path)))
            done = True
            continue
        out.append(line)
        i += 1
    if not done:
        out.extend(["", "# Course contents (auto-generated):", ""])
        for ch in chapters:
            title = ch.title or "Chapter %d" % ch.num
            out.append("%d. [**Chapter %d — %s**](%s)"
                       % (ch.num, ch.num, title, rel_href(parent, ch.nb_path)))
    return "\n".join(out) + "\n"


def build_plain_toc(chapters, parent):
    lines = ["# Table of Contents", ""]
    for i, ch in enumerate(chapters, 1):
        href = rel_href(parent, ch.nb_path)
        title = ch.title or "Chapter %d" % ch.num
        lines.append("%d. [**Chapter %d — %s**](%s)" % (i, ch.num, title, href))
    lines.append("")
    return "\n".join(lines)


def build_copyright_sections():
    """2026 copyright + contact sections, in the format of the project
    README. The BSD conditions and disclaimer are extracted verbatim from
    the embedded README so the legal text stays byte-identical."""
    m = re.search(r"conditions are met:\s*```\n(.*?)\n```", EMBEDDED_README, re.DOTALL)
    conditions = m.group(1).strip() if m else (
        "Redistributions of any part of this project must retain the above copyright "
        "notice, this list of conditions and the following disclaimer.")
    m = re.search(r"THIS SOFTWARE IS PROVIDED.*", EMBEDDED_README)
    disclaimer = m.group(0).strip() if m else (
        "THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "
        "WITHOUT ANY EXPRESS OR IMPLIED WARRANTIES.")
    lines = [
        "",
        "---",
        "",
        "## Copyrights and usage terms:",
        "Licensing terms for Project **%s**" % PROJECT_TITLE,
        "",
        "This project is licensed under the terms of the 3-Clause BSD License "
        "(also known as New or Revised or Modified BSD License, or the "
        "BSD-3-Clause license), as follows:",
        "",
        "Copyright (c) %s %s. All rights reserved." % (COPYRIGHT_YEAR, COPYRIGHT_HOLDERS),
        "",
        "Redistribution and use in source and binary forms, with or without "
        "modification, are permitted provided that the following conditions are met:",
        "",
        "```",
        conditions,
        "```",
        "",
        disclaimer,
        "",
        "---",
        "",
        "# How to contact us",
        "You can reach us from the following links:",
        "",
    ]
    for name, url in CONTACT_LINKS:
        lines.append("- [%s](%s)" % (name, url) if url else "- %s" % name)
    lines.append("")
    return "\n".join(lines) + "\n"


def write_toc(parent, content):
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
    if ch.docx_moved:
        names = ", ".join("%s -> Docs/%s" % (name, name) for name in ch.docx_moved)
        suffix = " (dry run, not moved)" if dry_run else ""
        print("      docx     : moved %s%s" % (names, suffix))
    if ch.docx_fixes:
        print("      docx lnk : %d fixed" % len(ch.docx_fixes))
        for old, new in ch.docx_fixes:
            print("          %s -> %s" % (old, new))
    nav = "top %s | bottom %s" % (ch.nav_top_action, ch.nav_bottom_action)
    if dry_run and ("inserted" in nav or "rewritten" in nav or "appended" in nav):
        nav += " (dry run, not saved)"
    print("      nav      : %s" % nav)
    if ch.link_fixes:
        print("      links    : %d fixed" % len(ch.link_fixes))
        for old, new in ch.link_fixes:
            print("          %s -> %s" % (old, new))


def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(
        description="Build a README-styled TOC.md with copyright/contact sections, "
                    "move chapter docx files into Docs/, add top+bottom navigation "
                    "cells, and fix links across chapter.N folders.")
    ap.add_argument("parent", nargs="?",
                    default=os.path.dirname(os.path.abspath(__file__)),
                    help="parent folder containing chapter.N folders (default: this script's folder)")
    ap.add_argument("--dry-run", action="store_true", help="show changes without writing any file")
    ap.add_argument("--backup", action="store_true", help="save each patched notebook as <name>.ipynb.bak")
    ap.add_argument("--readme", metavar="PATH",
                    help="README text to embed in the TOC (default: PARENT_DIR/readme.md, "
                         "then --readme-url if given, then embedded copy)")
    ap.add_argument("--readme-url", metavar="URL", default=None,
                    help="optional URL to download the README from when there is no local one")
    ap.add_argument("--no-readme", action="store_true",
                    help="plain TOC (chapter links only, plus the copyright/contact sections)")
    ap.add_argument("--no-copyright", action="store_true",
                    help="do not append the copyright/contact sections to TOC.md")
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
        moved, docs_names = move_docx(ch, args.dry_run)
        ch.docx_moved = moved
        if ch.nb is None:
            report(ch, args.dry_run)
            continue
        ensure_nav(ch, chapters, idx)
        fix_links(ch, known)
        fix_docx_links(ch, docs_names)
        will_write = (ch.nav_top_action in ("inserted", "rewritten")
                      or ch.nav_bottom_action in ("appended", "rewritten")
                      or ch.link_fixes or ch.docx_fixes)
        if will_write and not args.dry_run:
            if args.backup:
                shutil.copy2(ch.nb_path, ch.nb_path + ".bak")
            dump_notebook(ch)
        report(ch, args.dry_run)

    readme_text, readme_src = resolve_readme(parent, args)
    if readme_text is None:
        content = build_plain_toc(chapters, parent)
        readme_src = "plain (no README)"
    else:
        content = build_rich_toc(readme_text, chapters, parent)
        if "media/" in readme_text and not os.path.isdir(os.path.join(parent, "media")):
            print("  note: the README references media/ images but there is no media folder "
                  "next to TOC.md — copy it there for the images to render")

    if not args.no_copyright:
        if readme_text is not None and COPYRIGHT_HOLDERS in readme_text \
                and "Copyrights and usage terms" in readme_text:
            print("             copyright/contact: already present in the README source, "
                  "kept verbatim (not duplicated)")
        else:
            content += build_copyright_sections()
            print("             copyright/contact: appended (c) %s %s"
                  % (COPYRIGHT_YEAR, COPYRIGHT_HOLDERS))

    if args.dry_run:
        toc_status = "(dry run, not saved)"
    else:
        _, toc_changed = write_toc(parent, content)
        toc_status = "written" if toc_changed else "unchanged"
    print("TOC        : %s %s" % (os.path.join(parent, TOC_NAME), toc_status))
    print("             README source: %s" % readme_src)

    print("\nDone. Note: Jupyter must be launched from %s" % parent)
    print('    cd "%s"  &&  jupyter lab   (or: jupyter notebook)' % parent)
    print("Then reload open notebook tabs (F5) so the browser picks up the patched files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
