---
name: 3d-brain
description: Turns a folder of markdown notes (an AI operating system, a second brain, an Obsidian vault, a docs repo) into an interactive 3D brain page using Brain 3D. Use when someone asks to see their brain in 3D, visualise their notes or knowledge base, or map how their docs connect.
---

# 3D Brain

Builds a single HTML page that shows every markdown note as a node in 3D and every real link between notes as a connection, with a growth replay and cinema mode. It uses the Brain 3D tool: `build_brain.py` plus `brain.template.html`.

## 1. Find the tool

Look for `build_brain.py` in this order: next to this skill file's parent folders, in a `brain-3d/` folder in the workspace, or anywhere the person points to. If it is not there, ask the person to download it from the Brain 3D GitHub repo (green Code button, Download ZIP) and tell you where they unzipped it. Do not rewrite the tool from memory.

## 2. Find the notes folder

Ask which folder holds their notes if it is not obvious. It should contain `.md` files. Look at its top-level folders so you can suggest groups.

## 3. Agree the setup with the person

Show them, in plain words, before writing anything:

- **Name** shown in the header.
- **Centre note**, the file everything grows out from. Default: `AGENTS.md`, `CLAUDE.md`, `README.md` or `index.md`, whichever exists.
- **Groups**: by default each top-level folder becomes a group. Offer to merge or rename them (3 to 7 groups reads best).
- **Private files** whose content must never appear in the page (finance, contracts with personal data, anything confidential). They still show as a node.
- **Colours**: ask if they have brand colours. Use them for the accent and the groups. Backgrounds must stay dark.

Then write `brain.config.json` in the notes folder. `brain.config.example.json` next to the tool lists every option.

## 4. Build it

```
python <path-to>/build_brain.py <notes-folder> --out <notes-folder>/brain.html
```

Read the summary it prints: note count, connections, stubs, unconnected notes. If the numbers look wrong (very few connections, everything in one group), fix the config and rebuild before showing the person.

## 5. Hand it over

Tell the person where `brain.html` is and that it opens in Chrome or Edge with an internet connection. Mention what they can do: drag to orbit, click a note, **Watch it grow**, **Cinema**. Point out the stubs and unconnected notes it found, since those are the gaps in their brain.

## Rules

- Never invent nodes or connections. If something looks missing, it is missing in the notes.
- The page contains text from the notes. Warn the person before they share it or put it in a public repo.
- Never add `brain.html` to the Brain 3D repo itself.
