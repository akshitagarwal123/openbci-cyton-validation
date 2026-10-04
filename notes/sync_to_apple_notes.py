"""
Push notes/*.md into the macOS Notes app (folder "BrainTech"), creating or updating one note per file.
Images (markdown ![caption](images/x.png)) become links to the same file on GitHub, where they render inline.

Usage:
    python notes/sync_to_apple_notes.py            # syncs daily_log.md and validation_tracker.md
"""

import base64
import html
import os
import tempfile
import re
import subprocess
import sys

FOLDER = "BrainTech"
FILES = ["daily_log.md", "validation_tracker.md"]
HERE = os.path.dirname(os.path.abspath(__file__))


def inline(text):
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<tt>\1</tt>", text)
    return text


REPO_URL = "https://github.com/akshitagarwal123/openbci-cyton-validation"


def github_ref():
    """Newest pushed commit (a permalink keeps working after branches are merged or deleted)."""
    for cmd in (["git", "rev-parse", "@{u}"], ["git", "rev-parse", "origin/main"]):
        r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return "main"


GITHUB_IMAGES = f"{REPO_URL}/blob/{github_ref()}/notes/"


def embed_image(rel_path, caption):
    """Apple Notes won't render images added by automation, so link to the copy on GitHub instead."""
    url = GITHUB_IMAGES + rel_path
    return f'<div>🖼 <a href="{html.escape(url)}">{inline(caption)}</a></div>'


def md_to_html(md):
    out, in_list, table = [], False, []

    def flush_table():
        if not table:
            return
        rows = [r for r in table if not re.match(r"^\|\s*-", r)]
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        h = "<table border='1' cellpadding='4' style='border-collapse:collapse'>"
        for i, row in enumerate(cells):
            tag = "th" if i == 0 else "td"
            h += "<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in row) + "</tr>"
        out.append(h + "</table>")
        table.clear()

    for line in md.splitlines():
        if line.startswith("|"):
            table.append(line)
            continue
        flush_table()
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        img = re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", line)
        if img:
            out.append(embed_image(img.group(2), img.group(1)))
            continue
        m = re.match(r"^(#{1,3}) (.*)", line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
        elif line.strip():
            out.append(f"<div>{inline(line)}</div>")
        else:
            out.append("<div><br></div>")
    flush_table()
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def osa_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sync(path):
    md = open(path).read()
    title = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), os.path.basename(path))
    body = md_to_html(md)
    body_file = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False)
    body_file.write(body)
    body_file.close()
    body_expr = f'(read POSIX file {osa_string(body_file.name)} as «class utf8»)'
    script = f'''
    tell application "Notes"
        if not (exists folder {osa_string(FOLDER)}) then make new folder with properties {{name:{osa_string(FOLDER)}}}
        set f to folder {osa_string(FOLDER)}
        set matches to (notes of f whose name is {osa_string(title)})
        if (count of matches) > 0 then
            set body of item 1 of matches to {body_expr}
            return "updated"
        else
            make new note at f with properties {{body:{body_expr}}}
            return "created"
        end if
    end tell'''
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    os.unlink(body_file.name)
    if res.returncode:
        sys.exit(f"Notes sync failed for {path}: {res.stderr.strip()}")
    print(f"{res.stdout.strip():8s} '{title}' in Notes › {FOLDER}")


if __name__ == "__main__":
    for name in FILES:
        sync(os.path.join(HERE, name))
