# Brain 3D

Turn a folder of markdown notes into an interactive 3D brain.

Point it at your AI operating system, second brain, Obsidian vault or docs repo. Every note becomes a glowing node, every real link between notes becomes a connection, and you can watch the whole thing grow out from one central idea.

One Python file, no installs. The result is a single HTML page you open in your browser.

## What you get

- **A 3D globe of your notes**, grouped by folder (or by groups you choose), each group in its own colour.
- **Watch it grow:** the brain builds itself out from your central note, one real connection at a time.
- **Cinema mode:** panels hidden, a big counter running, made for screen recordings and demos.
- **Click any note** to read its summary and sections, and jump to everything it links to or is linked from.
- **Search, hide or solo groups**, and a full list of every note.
- **Health check:** stubs (notes that are too short) get a red ring, and notes with no connections are counted, so you can see the gaps.
- **Your brand:** set your own name, logo, accent colour and group colours.

## Quick start

You need Python 3.8 or newer and a modern browser (Chrome, Edge, Firefox or Safari).

1. Download this repo (green **Code** button, then **Download ZIP**) and unzip it.
2. Try the sample brain:
   ```
   python build_brain.py example --open
   ```
3. Now map your own notes:
   ```
   python build_brain.py "path/to/your/notes" --open
   ```

That writes `brain.html` in the folder you ran it from and opens it. The page needs an internet connection the first time it loads, to fetch the 3D library and fonts.

### Using it with Claude

The `skill/3d-brain/` folder is a ready-made Claude skill. Add it to Claude (Claude Code, or as a custom skill in the Claude app), then just ask: *"turn my notes into a 3D brain."* Claude will find your notes, agree the groups and colours with you, write the config and build the page.

## Making it yours

Put a `brain.config.json` in your notes folder (or pass `--config path/to/file.json`). Everything is optional. Copy `brain.config.example.json` to start.

| Setting | What it does | Default |
|---|---|---|
| `name` | Title in the header and browser tab | The folder name |
| `center` | The note everything grows out from | `AGENTS.md`, `CLAUDE.md`, `README.md` or `index.md`, else the most connected note |
| `categories` | Your groups: `label`, `folders`, `color`, `description`. `root_files: true` puts top-level files in that group. `inner: true` places the group close to the centre | One group per top-level folder |
| `exclude` | Folder names or path patterns to skip | `.git`, `node_modules`, `.obsidian`, and similar |
| `include_hidden` | Dot-folders to read anyway | `.claude` |
| `private` | Files shown as a node but whose text never goes into the page | None |
| `stub_words` | Notes shorter than this are flagged as stubs | `60` |
| `logo` | An image file shown in the header | None |
| `credit` | Small "Built with Brain 3D" link in the corner | `true` |
| `theme` | `background`, `text`, `muted`, `accent`, `alert` colours. Keep the background dark | Black with an amber accent |

## How connections are found

Only real links count. Nothing is guessed.

- **Links:** markdown links `[text](path/to/note.md)` and wikilinks `[[Note name]]`.
- **References:** a file or folder path written in the text, like `docs/pricing.md` or `skills/weekly-review/`, that points to a real note.
- **Mentions (drawn fainter):** the name of a skill or agent folder, like `weekly-review`, written in plain text.

If two notes could match a link, it is left out rather than guessed. If your brain looks thin, the links are missing in your notes, and the health panel shows you where.

## Privacy

The page you build contains the titles, summaries and section headings of your notes. It never leaves your computer unless you share it. Before you share it or put it online, check it, and use `private` for anything confidential. `brain.html` is in `.gitignore` so it never ends up in this repo by accident.

## Credits

Built by [Muhammad Shoaib Amin](https://muhammadshoaibamin.com/portfolio), founder of Adminless.
