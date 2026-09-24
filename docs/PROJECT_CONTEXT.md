# External SHC DE map editor

## Intent

Current capability summary, unresolved questions and application plan:
[`EDITOR_READINESS.md`](EDITOR_READINESS.md).

Build a standalone external map editor for Stronghold Crusader Definitive Edition
as an alternative to the built-in editor. The immediate work is reverse engineering
the binary map format with the user, preserving evidence, and extending the parser
and controlled map-writing tools. A finished GUI and a general-purpose writer do
not exist yet.

Continue from the existing research rather than starting over. Read
[`AGENTS.md`](../AGENTS.md) for the ordered handoff,
[`RESEARCH_MEMORY.md`](../RESEARCH_MEMORY.md) for accumulated findings, and
[`SECTION_STATUS_2026-09-19.md`](SECTION_STATUS_2026-09-19.md) for section meanings
and remaining unknowns. Later verified results supersede earlier hypotheses.

## Workspace paths and roles

| Path | Role |
|---|---|
| `C:\repositories\shcde-map-editor` | Editor tools, format research, documentation and archived experiments |
| `C:\Users\rustam\AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Maps` | Live game maps and user-created references; folder existence verified on 2026-09-19 |
| `C:\Users\rustam\AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Saves` | Saved simulation snapshots; Leto .msv files inspected read-only, see `SAVEGAME_LETO_2026-09-19.md` |
| `C:\repositories\shcde-script-extender` | Runtime structures and IDs to cross-check against file evidence |
| `C:\repositories\shcde-stats-rust` | Entity and player research, instructions and memory |
| `C:\repositories\shc-eco-simulator` | Independent modeling evidence, including starting stockpile layout |
| `C:\repositories\shcde-map-editor\vendor\sourcehold-maps` | Legacy map-format research; verify applicability to DE |

The user plans to add other repositories and the game maps path to the SHCDE
project workspace. No additional unnamed repository is assumed to be configured.
When a new source becomes available, read its applicable `AGENTS.md` and relevant
documentation, verify its actual local path, and update this table and the source
list in the editor's `AGENTS.md`. Record revisions and source files alongside any
findings derived from it. Workspace membership alone does not make a repository
a runtime dependency of the editor.

## Research record

Keep project intent and working instructions in `AGENTS.md`, detailed evidence in
focused `docs/` reports, and continuation notes in `RESEARCH_MEMORY.md`. For new
experiments, record source maps and hashes, the controlled change, section IDs,
offsets, types, coordinates, validation results and unresolved questions.

Distinguish confirmed file fields, observed game behavior and hypotheses. Runtime
layouts are supporting evidence, not a file-format specification. Preserve unknown
bytes and original maps; use separately named outputs and archive provenance for
map-writing experiments. Track parser/readback checks separately from actual game
loading and editor-resave results.
