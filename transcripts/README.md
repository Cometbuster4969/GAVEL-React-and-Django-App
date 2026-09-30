# Transcripts and historical verification evidence

Index updated **2026-09-30**. These files preserve prior evidence; their presence
is not proof that the latest working tree has passed the same checks.

[AGENTS.md](../AGENTS.md) defines append-only session logging and submission-time
export. `transcripts/` is `export-ignore` in `.gitattributes`: the files remain
in the private repository but are excluded from `git archive` output. Ensure the
reviewer receives repository access, not only an archive without the transcripts.

| File | Contents and scope |
|---|---|
| [log.txt](log.txt) | Existing AI history export; preserve verbatim. Contains a labeled reconstruction of earlier sessions, not a complete verbatim record of all sessions. |
| [a11y-audit-2026-09-29.md](a11y-audit-2026-09-29.md) | Historical accessibility method/results for ten rendered surfaces, plus residual manual-review items. Not rerun after the frontend split. |
| [a11y-audit-report.json](a11y-audit-report.json) | Original raw axe results supporting the September 29 audit. |
| [validation-2026-09-29.log](validation-2026-09-29.log) | Captured commands/results from the older revision, including 13 tests; not evidence for the latest 35-test working tree. |
| [discord-notification.md](discord-notification.md) | Updated submission/status message template. Not a receipt proving a Discord post was sent. |

## Latest results and export completeness

The September 30 hardening results are documented in [README.md](../README.md).
The documentation update does not rerun historical checks, overwrite logs, or
manufacture tool-native conversation exports.

The original home-directory log was unavailable when the older export was
assembled. As disclosed in `log.txt`, earlier sessions were reconstructed from
repository evidence, followed by the session record available at that time.
That reconstruction must not be described as verbatim original conversation.

Before final submission, export every available current AI session from its
source, preserve older exports, and disclose any unrecoverable gaps. A Markdown
summary of changes is not a substitute for a complete interaction transcript.
Completeness of all sessions has **not** been independently verified in this
sandbox. Do not overwrite the existing export with a newer partial log.

The user reports submission/access logistics are handled. This index does not
assert that collaborator access or a Discord notification is still pending.
