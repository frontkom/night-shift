# Suggestions

Improvement ideas for the Night Shift project itself. Maintained by the `suggest-improvements` task.

## DEV.md is referenced but doesn't exist

- **Why:** README.md and earlier conversations talk about a `DEV.md` for plumbing details (versioning, raw URLs, environment IDs). The file was never created. Anyone clicking through expecting it will hit a 404.
- **Effort:** S
- **Files:** create `DEV.md` (or remove the references). Suggest removing references — the README is short enough that plumbing details can live there or in `HOW-TO.md`.

~~`bundles/all.md` doesn't write to the central runs log~~ **Obsolete.** The central runs log was removed entirely — writing run logs (which include private project names and activity) to the public night-shift repo would leak information. The audit trail is now the labelled PR list per repo (`gh pr list --label night-shift`) plus the trigger dashboard output.

~~Manifest parsing is implicit~~ **Fixed.** Bundle prompts now fetch and parse `manifest.yml` at runtime to resolve their task list. Editing the manifest is enough — the bundle file does not need updating.
