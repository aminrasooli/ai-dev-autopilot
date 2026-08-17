# Research log

Durable findings from the daily R&D runs, with sources and the date they were
verified. Newest first.

## 2026-08-17 — NotebookEdit's subject field, and the state of NotebookRead

- **`NotebookEdit` sends its path as `tool_input.notebook_path`, and has no
  `file_path`.** Verified against the tool schema of the running Claude Code
  build (the JSON schema the session itself publishes for the tool):
  `notebook_path` is required and must be absolute; the other fields are
  `cell_id`, `new_source`, `cell_type`, `edit_mode`. The hooks documentation
  does not enumerate `tool_input` fields per tool, so the build's own schema is
  the primary source. https://code.claude.com/docs/en/hooks (read 2026-08-17)
- **`NotebookRead` no longer exists in current builds.** The tools reference
  lists `NotebookEdit` but no notebook read tool; `.ipynb` reading is folded
  into `Read` ("`.ipynb` files return all cells with their outputs").
  `NotebookEdit` is marked *Permission required: Yes*, so it does raise
  permission dialogs and the PermissionRequest broker genuinely fires for it.
  Notebook permission rules are spelled through `Edit(...)`: "A rule like
  `Edit(notebooks/**)` covers NotebookEdit calls on files in that directory",
  and since 2.1.210 a `NotebookEdit(path)` rule draws a startup warning saying
  to use `Edit(path)`. https://code.claude.com/docs/en/tools-reference
  (read 2026-08-17); https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
- **Newest verified Claude Code: 2.1.233** — unchanged since the 2026-08-16
  check; no releases landed between the two runs.
  https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
  (read 2026-08-17)
- **Why this mattered here:** both hooks read the subject from
  `file_path`/`path` only, so every notebook operation arrived with an empty
  subject — the guard's ceiling silently skipped all path rules for
  `NotebookEdit`, the broker escalated every routine notebook edit, and the
  broker's search-tools arm allowed `NotebookRead` under a justification that
  was false for it. Fixed 2026-08-17; the decision record "A tool's subject is
  read from the field that tool actually sends" in `.ai/decisions.md` carries
  the details.
