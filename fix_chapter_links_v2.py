#!/usr/bin/env python3
"""Build a styled TOC.md and fix cross-chapter navigation links (v2).

Layout assumed (PARENT_DIR is the folder this script scans):

    PARENT_DIR/
    |-- chapter.1/chapter1.ipynb
    |-- chapter.2/chapter2.ipynb
    |-- chapter.3/...
    +-- TOC.md                <- generated here

What it does
    1. Scans PARENT_DIR for chapter.N folders (N = 1, 2, 3, ...).
    2. Writes PARENT_DIR/TOC.md containing the FULL TEXT AND STYLE of the
       project README (default source: the YARPOSE.ML-Electronics README),
       with the entries of its "Course contents" list turned into the real,
       correct links to the scanned chapter notebooks. Chapters that have no
       matching README entry are appended to that list; README entries with
       no chapter folder are kept as plain (unlinked) text.
    3. In every chapterN.ipynb, inserts or rewrites the markdown cell that
       starts with <!--NAVIGATION--> so it contains correct
       Previous / TOC / Next links (e.g. ../chapter.2/chapter2.ipynb).
       Extra lines already in an existing navigation cell (e.g. a docx
       download link) are preserved.
    4. Repairs markdown links elsewhere in the notebooks that point to a
       chapter notebook by bare filename (chapter2.ipynb) when that link
       does not resolve, rewriting it to ../chapter.2/chapter2.ipynb.

README source priority:
    --readme PATH  >  PARENT_DIR/README.md  >  --readme-url download
    >  embedded copy of the GitHub README (always available, offline-safe).
Use --no-readme for the plain v1-style TOC (chapter links only).

Note: the README references images relative to the repo (media/...). For
them to render, the media/ folder must exist next to the generated TOC.md.

Why links can still 404 in the browser: Jupyter only serves files under
the directory it was launched from. Start it from PARENT_DIR and reload
open tabs (F5):

    cd PARENT_DIR
    jupyter lab          # or: jupyter notebook

Usage
    python fix_chapter_links_v2.py [PARENT_DIR] [--dry-run] [--backup]
                                   [--readme PATH] [--readme-url URL]
                                   [--no-readme]

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

DEFAULT_README_URL = (
    "https://raw.githubusercontent.com/yarpose/YARPOSE.ML-Electronics/master/README.md"
)

EMBEDDED_README = r"""# ML-Assisted Basics of Electronics for ALL (ML-Electronics)
By [Ali Jaberi](https://www.linkedin.com/in/alijaberii/) and [M. B. Ghaznavi-Ghoushchi](https://www.linkedin.com/in/ghaznavi-ghoushchi/).

Version 2023.01

A Full open-source/Full with Python/ interactive course for all who like to know "What is electronics?" from scratch to basic applications.
This is the repo of **ML-Assisted Basics of Electronics for ALL**  project. It brings ALL of **Basic Electronics** into browser via Python jupyter including examples, plots, equations, simulations and narration. The narrations of text is generated via ML tools.


This project is based on:

1. Python
2. Jupyter notebook and run-able on Google colab
3. schemdraw library
4. PySpice simulation wrapper
5. ElevenLabs.io (ML generated human voices for whole the project)
6. Good learning resources
7. ... and days and hours of hard work 



# Course contents:

1. Basics of physics for semiconductors
2. Basics of circuit theory 
3. Diode theory and circuits
4. Bipolar Junction Transistor (BJT)
5. Metal-Oxide Semiconductor Field Effect Transistor (MOS)
6. How to install and use required tools/libraries
7. Project Codes All-In-One (AIO)

# Main features:

# ALL Circuits are drawn via Python in Jypyter
ALL the schematics of the circuits are reproduced utilizing ```schemdraw``` python library.

# Circuit simulation utilizing PySpice
ALL the simulations of the circuits are performed utilizing ```PySpice``` python library.

# Interactive features in circuit draw and simulation
ALL the interactive features in circuit re-draw and parameter modifications are implemented utilizing ```ipywidgets``` python library.

# ML-assisted text narration
ALL the course text materials are narrated by ML-assisted  ```ElevenLabs.io```.

# Circuit explanation utilizing LaTeX
ALL the interactive features in circuit re-draw and parameter modifications are implemented utilizing $LaTeX$ 

# All in one bunch of codes, figures, audio, etc.
ALL of codes, figures, ipynb, docx are ready to download and re-use under the copyright notice verbatim. 

# Unique "Spoon" style of Jupyter Python coding 
We followed stand-alone coding for each example just like insert your spoon in Dessert and eat each section without need to run its upper or lower jupyter cells which usually you see in the most of ```jupyter notebooks``` samples. This enables reader to look at each example as a fully separated and functional code.

# Fully open-source course
The project is totally open-source in hope of help to extended ease of understating for "Basics of Electronics".

# Contents are in Compliance with "Basics of Electronic Circuits - Electronics I"
The contents of this project are ready to use for  second year undergraduate courses like:
 1. Basics of Electronics
 2. Electronics I
 3. Electronic Circuit Theory.

![Startup](media/ML-Electronics.gif)



### Copyrights and usage terms:
Licensing terms for Project **ML-Assisted Basics of Electronics for ALL**

This project is licensed under the terms of the 3-Clause BSD License (also known as New or Revised or Modified BSD License, or the BSD-3-Clause license), as follows:

Copyright (c) 2023 Ali Jaberi and M. B. Ghaznavi-Ghoushchi. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
```
Redistributions of any part of this project must retain the above copyright notice, this list of conditions and the following disclaimer. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
```

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# How to contact us
You can reach us from the following links:


<p>
  <a href="https://www.linkedin.com/in/alijaberii/" rel="nofollow noreferrer">
    <img src="media/LI.png" alt="linkedin"> Ali Jaberi
  </a>
  <br>
  <a href="https://www.linkedin.com/in/ghaznavi-ghoushchi" rel="nofollow noreferrer">
    <img src="media/LI.png" alt="linkedin"> M. B. Ghaznavi-Ghoushchi
  </a> &nbsp; 
  <a href="https://github.com/ghoushchi" rel="nofollow noreferrer">
    <img src="media/GH.png" alt="github"> ghoushchi
  </a><br><a href="https://github.com/yarpose" rel="nofollow noreferrer">
    <img src="media/GH.png" alt="github"> YARPOSE - A Dejavu project in EDA
  </a>
</p>"""

CHAPTER_DIR_RE = re.compile(r"^chapter\.(\d+)$", re.IGNORECASE)
IPYNB_LINK_RE = re.compile(r"\]\(([^)#?]+?\.ipynb)\)")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.*?)\s*#*\s*$")
MD_CHARS_RE = re.compile(r"[*_`]")
NAV_MARKER = "<!--NAVIGATION-->"
TOC_NAME = "TOC.md"
COURSE_HEADING_RE = re.compile(r"^#{1,6}\s+Course\s+contents", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.*?)\s*$")


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


def download_readme(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "fix_chapter_links_v2"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def resolve_readme(parent, args):
    """Return (readme_text, source_description) or (None, None) for --no-readme."""
    if args.no_readme:
        return None, None
    if args.readme:
        with open(args.readme, "r", encoding="utf-8") as f:
            return f.read(), "--readme %s" % args.readme
    local = os.path.join(parent, "README.md")
    if os.path.isfile(local):
        with open(local, "r", encoding="utf-8") as f:
            return f.read(), "local README.md"
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
    ap = argparse.ArgumentParser(
        description="Build a README-styled TOC.md and fix navigation links across chapter.N folders.")
    ap.add_argument("parent", nargs="?",
                    default=os.path.dirname(os.path.abspath(__file__)),
                    help="parent folder containing chapter.N folders (default: this script's folder)")
    ap.add_argument("--dry-run", action="store_true", help="show changes without writing any file")
    ap.add_argument("--backup", action="store_true", help="save each patched notebook as <name>.ipynb.bak")
    ap.add_argument("--readme", metavar="PATH",
                    help="README text to embed in the TOC (default: PARENT_DIR/README.md, "
                         "then download, then embedded copy)")
    ap.add_argument("--readme-url", metavar="URL", default=DEFAULT_README_URL,
                    help="where to download the README from if there is no local one")
    ap.add_argument("--no-readme", action="store_true",
                    help="plain v1-style TOC (chapter links only, no README text)")
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

    readme_text, readme_src = resolve_readme(parent, args)
    if readme_text is None:
        content = build_plain_toc(chapters, parent)
        readme_src = "plain (no README)"
    else:
        content = build_rich_toc(readme_text, chapters, parent)
        if "media/" in readme_text and not os.path.isdir(os.path.join(parent, "media")):
            print("  note: the README references media/ images but there is no media folder "
                  "next to TOC.md — copy it there for the images to render")

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
