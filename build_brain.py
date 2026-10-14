#!/usr/bin/env python3
"""Brain 3D: turn a folder of markdown notes into an interactive 3D brain.

Usage:
    python build_brain.py <notes-folder> [--config brain.config.json] [--out brain.html] [--open]

Every markdown file becomes a node. Real links between files become connections:
markdown links, [[wikilinks]], and file or folder paths written in the text.
Nothing is guessed. The result is one self-contained HTML file you open in a browser.

Standard library only. Python 3.8 or newer.
"""

import argparse
import base64
import fnmatch
import json
import mimetypes
import os
import re
import sys
import webbrowser
from collections import deque
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "brain.template.html")
REPO_URL = "https://github.com/Adminlesshq/brain-3d"

DEFAULTS = {
    "name": None,                      # shown in the header; defaults to the folder name
    "center": None,                    # file at the heart of the brain; auto-detected if empty
    "categories": None,                # list of groups; auto-built from top-level folders if empty
    "exclude": [".git", "node_modules", ".obsidian", ".trash", ".venv", "venv",
                "__pycache__", "dist", "build"],
    "include_hidden": [".claude"],     # dot-folders that are still read (e.g. Claude skills)
    "extensions": [".md", ".markdown"],
    "private": [],                     # files shown as a node, but their content is never read
    "stub_words": 60,                  # notes shorter than this are flagged as stubs
    "logo": None,                      # optional image file shown in the header
    "credit": True,                    # small "Built with Brain 3D" link in the corner
    "theme": {
        "background": "#000000",
        "text": "#F5F3EF",
        "muted": "#8F8A84",
        "accent": "#F5A623",
        "alert": "#D64532",
    },
}

PALETTE = ["#F5A623", "#4FC3F7", "#B388FF", "#69F0AE", "#FF7EB3", "#FFD54F",
           "#80DEEA", "#FF8A65", "#AED581", "#CE93D8", "#90A4AE", "#F48FB1"]
CENTER_CANDIDATES = ["AGENTS.md", "CLAUDE.md", "README.md", "index.md", "Home.md", "HOME.md"]
INDEX_FILES = ("README.md", "SKILL.md", "AGENT.md", "index.md")


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULTS))
    base = None
    if path:
        with open(path, encoding="utf-8") as fh:
            user = json.load(fh)
        base = os.path.dirname(os.path.abspath(path))
        for k, v in user.items():
            if k.startswith("_"):
                continue
            if k == "theme" and isinstance(v, dict):
                cfg["theme"].update(v)
            else:
                cfg[k] = v
    return cfg, base


def collect_files(root, cfg):
    exclude = set(cfg["exclude"])
    hidden_ok = set(cfg["include_hidden"])
    exts = tuple(e.lower() for e in cfg["extensions"])
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in exclude and (not d.startswith(".") or d in hidden_ok)
        )
        for f in sorted(filenames):
            if f.lower().endswith(exts):
                rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
                if not any(fnmatch.fnmatch(rel, pat) for pat in exclude):
                    out.append(rel)
    return out


def strip_md(s):
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"[*_>#|~]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def read_meta(rel, text):
    lines = text.splitlines()
    title, body = None, lines
    if lines and lines[0].strip() == "---":  # YAML frontmatter
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for l in lines[1:i]:
                    m = re.match(r"(?:name|title):\s*(.+)", l)
                    if m and not title:
                        title = m.group(1).strip().strip("'\"")
                body = lines[i + 1:]
                break
    for l in body:
        m = re.match(r"#\s+(.+)", l)
        if m:
            title = strip_md(m.group(1))
            break
    if not title:
        title = os.path.splitext(os.path.basename(rel))[0].replace("_", " ").replace("-", " ")
    para, in_code = [], False
    for l in body:
        t = l.strip()
        if t.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not t:
            if para:
                break
            continue
        if t.startswith(("#", "|", "---", "<", "![")):
            if para:
                break
            continue
        para.append(t)
    summary = strip_md(" ".join(para))
    if len(summary) > 260:
        summary = summary[:257].rsplit(" ", 1)[0] + "..."
    sections = [strip_md(m.group(1)) for m in re.finditer(r"^##\s+(.+)$", "\n".join(body), re.M)][:10]
    words = len(re.findall(r"\w+", text))
    return title, summary, sections, words


def pretty(name):
    name = re.sub(r"^[\d_.\- ]+", "", name) or name
    return name.replace("-", " ").replace("_", " ").strip().capitalize()


def build_categories(files, cfg):
    """Return (categories, assign) where assign maps file -> category id."""
    cats = []
    if cfg["categories"]:
        for i, c in enumerate(cfg["categories"]):
            cid = c.get("id") or re.sub(r"[^a-z0-9]+", "-", c["label"].lower()).strip("-") or f"c{i}"
            cats.append({
                "id": cid, "label": c["label"],
                "color": c.get("color") or PALETTE[i % len(PALETTE)],
                "blurb": c.get("description", ""),
                "inner": bool(c.get("inner", False)),
                "folders": [f.strip("/").replace("\\", "/") for f in c.get("folders", [])],
                "root": bool(c.get("root_files", False)),
            })
    else:
        tops = {}
        for f in files:
            if "/" in f:
                tops[f.split("/")[0]] = tops.get(f.split("/")[0], 0) + 1
        ordered = sorted(tops, key=lambda k: (-tops[k], k))
        keep, rest = ordered[:10], ordered[10:]
        if any("/" not in f for f in files):
            cats.append({"id": "core", "label": "Core", "color": "#F5F3EF", "blurb": "Files at the top of the folder",
                         "inner": True, "folders": [], "root": True})
        for i, t in enumerate(keep):
            cats.append({"id": "f-" + re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-"), "label": pretty(t),
                         "color": PALETTE[i % len(PALETTE)], "blurb": t + "/", "inner": False,
                         "folders": [t], "root": False})
        if rest:
            cats.append({"id": "other", "label": "Other", "color": "#90A4AE", "blurb": ", ".join(r + "/" for r in rest),
                         "inner": False, "folders": rest, "root": False})

    def match(f):
        best, best_len = None, -1
        for c in cats:
            for folder in c["folders"]:
                if (f == folder or f.startswith(folder + "/")) and len(folder) > best_len:
                    best, best_len = c["id"], len(folder)
        if best:
            return best
        if "/" not in f:
            for c in cats:
                if c["root"]:
                    return c["id"]
        return None

    assign = {}
    for f in files:
        cid = match(f)
        if cid is None:
            if not any(c["id"] == "other" for c in cats):
                cats.append({"id": "other", "label": "Other", "color": "#90A4AE", "blurb": "Not in any group",
                             "inner": False, "folders": [], "root": False})
            cid = "other"
        assign[f] = cid
    used = set(assign.values())
    cats = [c for c in cats if c["id"] in used or cfg["categories"]]
    for c in cats:
        c.pop("folders", None)
        c.pop("root", None)
    return cats, assign


def main():
    ap = argparse.ArgumentParser(description="Turn a folder of markdown notes into a 3D brain.")
    ap.add_argument("folder", nargs="?", default=".", help="the notes folder to map (default: current folder)")
    ap.add_argument("--config", help="path to a brain.config.json (default: <folder>/brain.config.json if present)")
    ap.add_argument("--out", help="where to write the page (default: brain.html in the current folder)")
    ap.add_argument("--open", action="store_true", help="open the result in your browser")
    args = ap.parse_args()

    root = os.path.abspath(args.folder)
    if not os.path.isdir(root):
        sys.exit(f"Folder not found: {root}")
    cfg_path = args.config or (os.path.join(root, "brain.config.json")
                               if os.path.exists(os.path.join(root, "brain.config.json")) else None)
    cfg, cfg_dir = load_config(cfg_path)
    name = cfg["name"] or (pretty(os.path.basename(root)) + " brain")

    files = collect_files(root, cfg)
    if not files:
        sys.exit(f"No markdown files found in {root}")
    fileset = set(files)
    private = {f for f in files if any(fnmatch.fnmatch(f, p.replace("\\", "/")) for p in cfg["private"])}
    categories, assign = build_categories(files, cfg)

    by_base, by_stem = {}, {}
    for f in files:
        by_base.setdefault(os.path.basename(f).lower(), []).append(f)
        by_stem.setdefault(os.path.splitext(os.path.basename(f))[0].lower(), []).append(f)
    folder_index = {}
    for f in files:
        d, b = os.path.dirname(f), os.path.basename(f)
        if b in INDEX_FILES and (d not in folder_index or b != "README.md"):
            folder_index[d] = f
    slugs = {}
    for d, f in folder_index.items():
        slug = d.split("/")[-1] if d else ""
        if len(slug) >= 5 and re.search(r"[-_]", slug) and d.count("/") >= 1:
            slugs.setdefault(slug, f)

    def resolve(src, target):
        target = target.strip().split("#")[0].strip("<>").replace("\\", "/")
        if not target or re.match(r"^[a-z]+:", target):
            return None
        for base in (os.path.dirname(src), ""):
            p = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/")
            if p.startswith(".."):
                continue
            if p in fileset:
                return p
            if p.rstrip("/") in folder_index:
                return folder_index[p.rstrip("/")]
        if target.lower().endswith(tuple(cfg["extensions"])) and "/" not in target.strip("/"):
            hits = by_base.get(target.lower(), [])
            if len(hits) == 1:
                return hits[0]
        return None

    titles = {}
    nodes, edges = [], {}
    rank = {"link": 3, "reference": 2, "mention": 1}

    def add_edge(a, b, kind):
        if b and a != b and ((a, b) not in edges or rank[kind] > rank[edges[(a, b)]]):
            edges[(a, b)] = kind

    texts = {}
    for rel in files:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        hidden = rel in private
        title, summary, sections, words = read_meta(rel, text)
        if hidden:
            summary, sections = "Private. Content is not shown.", []
        else:
            texts[rel] = text
        titles.setdefault(title.lower(), []).append(rel)
        nodes.append({"id": rel, "title": title, "cat": assign[rel], "summary": summary,
                      "sections": sections, "words": words, "private": hidden,
                      "stub": (not hidden) and words < cfg["stub_words"]})

    for rel, text in texts.items():
        for m in re.finditer(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):       # markdown links
            add_edge(rel, resolve(rel, m.group(1)), "link")
        for m in re.finditer(r"\[\[([^\]|#]+)", text):                                  # [[wikilinks]]
            key = m.group(1).strip().lower()
            hit = resolve(rel, m.group(1).strip())
            if not hit:
                cands = by_stem.get(os.path.splitext(os.path.basename(key))[0], []) or titles.get(key, [])
                hit = cands[0] if len(cands) == 1 else None
            add_edge(rel, hit, "link")
        for m in re.finditer(r"([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*/?)", text):       # file and folder paths
            tok = m.group(1)
            if tok.lower().endswith(tuple(cfg["extensions"])) or ("/" in tok and len(tok) > 3):
                add_edge(rel, resolve(rel, tok), "reference")
        for slug, target in slugs.items():                                                # named skills, agents
            if re.search(r"(?<![\w/-])" + re.escape(slug) + r"(?![\w-])", text):
                add_edge(rel, target, "mention")

    edge_list = [{"s": a, "t": b, "k": k} for (a, b), k in sorted(edges.items())]
    adj = {n["id"]: set() for n in nodes}
    for e in edge_list:
        adj[e["s"]].add(e["t"])
        adj[e["t"]].add(e["s"])

    center = cfg["center"]
    if center and center.replace("\\", "/") in fileset:
        center = center.replace("\\", "/")
    else:
        if center:
            print(f"Note: center file '{center}' was not found, picking one automatically.")
        center = next((c for c in CENTER_CANDIDATES if c in fileset), None) or max(adj, key=lambda k: (len(adj[k]), k))

    order, parent, seen, q = [], {center: None}, {center}, deque([center])
    while q:
        cur = q.popleft()
        order.append(cur)
        for nb in sorted(adj[cur], key=lambda x: (-len(adj[x]), x)):
            if nb not in seen:
                seen.add(nb)
                parent[nb] = cur
                q.append(nb)
    for n in nodes:
        if n["id"] not in seen:
            order.append(n["id"])
            parent[n["id"]] = None
    pos = {k: i for i, k in enumerate(order)}
    for n in nodes:
        n["parent"], n["order"] = parent[n["id"]], pos[n["id"]]

    graph = {"name": name, "built": date.today().isoformat(), "center": center,
             "stubWords": cfg["stub_words"], "theme": cfg["theme"], "credit": bool(cfg["credit"]),
             "categories": categories, "nodes": nodes, "edges": edge_list}

    logo_html = ""
    if cfg["logo"]:
        lp = cfg["logo"] if os.path.isabs(cfg["logo"]) else os.path.join(cfg_dir or root, cfg["logo"])
        if os.path.exists(lp):
            mime = mimetypes.guess_type(lp)[0] or "image/png"
            with open(lp, "rb") as fh:
                uri = f"data:{mime};base64,{base64.b64encode(fh.read()).decode()}"
            logo_html = f'<img src="{uri}" alt="">'
        else:
            print(f"Note: logo '{cfg['logo']}' was not found, building without it.")

    with open(TEMPLATE, encoding="utf-8") as fh:
        page = fh.read()
    t = cfg["theme"]
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    page = (page.replace("__TITLE__", esc(name))
                .replace("__LOGO_HTML__", logo_html)
                .replace("__REPO_URL__", REPO_URL)
                .replace("/*__THEME__*/", f"--ink: {t['background']}; --text: {t['text']}; --muted: {t['muted']}; "
                                         f"--accent: {t['accent']}; --alert: {t['alert']};")
                .replace("/*__GRAPH__*/null", json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")))

    out = os.path.abspath(args.out or "brain.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)

    kinds = {}
    for e in edge_list:
        kinds[e["k"]] = kinds.get(e["k"], 0) + 1
    lone = sum(1 for n in nodes if not adj[n["id"]])
    print(f"{name}: {len(nodes)} notes, {len(edge_list)} connections "
          f"({kinds.get('link', 0)} links, {kinds.get('reference', 0)} references, {kinds.get('mention', 0)} mentions)")
    print(f"Groups: {', '.join(c['label'] for c in categories)}")
    print(f"Centre: {center}  |  stubs: {sum(1 for n in nodes if n['stub'])}  |  unconnected: {lone}")
    print(f"Wrote {out}")
    if args.open:
        webbrowser.open("file://" + out.replace(os.sep, "/"))


if __name__ == "__main__":
    main()
