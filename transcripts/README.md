# Transcripts

Exported AI interaction and verification evidence for the HackerRank *Build Your Own
Full-Stack Application* submission. `AGENTS.md` §2 keeps the live transcript log in
`$HOME/hackerrank_react_django_application/log.txt`; §6.2 requires a copy here at
submission time. `transcripts/` is marked `export-ignore` in `.gitattributes`, so these
files ship with the repository but stay out of the submission archive.

| File | Contents |
|---|---|
| `log.txt` | The append-only conversation log, copied verbatim from `$HOME/hackerrank_react_django_application/log.txt`. |
| `a11y-audit-2026-09-29.md` | Accessibility audit report: method, results per surface, violations found and fixed, residual manual-review items, reproduce steps. |
| `a11y-audit-report.json` | Raw `axe-core` results for all 10 audited surfaces, including per-node failure summaries. |
| `validation-2026-09-29.log` | Captured output of the verification commands run against this revision (install, seed, Django check, 13 tests, worker pass, production build, Prettier, `py_compile`, health probe, live API E2E). |
| `discord-notification.md` | Draft submission post plus the exact steps, because posting to Discord needs owner-held credentials. |

## Log provenance

The home-directory log file did not exist when this session started, so the browser-local
history of earlier sessions was unavailable. `log.txt` therefore opens with a clearly
labelled reconstruction of the three earlier sessions drawn from repository evidence
(git history, merged pull requests, `report.md`, `HANDOFF.md`, `SECURITY.md`, `test.md`),
followed by the verbatim prompt and full record of the session that produced this export.
