# App Studio decisions

The durable agreement between learner and AI. Update only agreed decisions and
actual evidence; pending is a valid state. Keep explanations/help in
[LEARNING.md](LEARNING.md), not a second copy here.

## Current stage

- **Current feature:** APP-002.
- **Status:** APP-001 merged and verified. APP-002 implemented locally; full cumulative checks and AI browser review passed. Learner completed their browser test and chose Keep; test interpretation and record approval recorded; commit/push/PR authorized, GitHub CI review and merge pending.
- **Next step:** Commit and push the approved APP-002 files, open a PR linked to Issue #3, and review both CI jobs. Do not merge without authorization.
- **Implementation marker:** `studio.json` now declares `implemented_through: 2` after the full cumulative APP-002 checks passed. This marks checked implementation, not lesson completion.

This repository owns application code. Server/proxy changes and production
deployment are outside these three local-development lessons. Prepared helpers
are reusable foundations, not evidence that unfinished routes are implemented.

## APP-001 · Branded homepage

**Scope:** make the neutral FastAPI homepage express one chosen identity with
a simple original SVG mark, coherent copy, navigation and shared style tokens.
Keep account actions honest about their unfinished state.

| Decision | Agreement |
|---|---|
| Visitor and concrete use situation | Small-business owners, managers, and employees visiting to understand how ShiftBoard aims to help them communicate and stay organized. |
| Reused IS117 brand, or name / promise / primary archetype | ShiftBoard; “Keep workplace communication simple, organized, and accessible”; Caregiver (approachable, supportive, reliable). Tagline: “Keep your team in the loop.” |
| One visible choice and visitor benefit | Forest green, warm white, clean typography, and a modern professional layout; learner expects a welcoming, trustworthy impression and clearer understanding of the purpose. |
| Own issue / branch / PR | [Issue #1](https://github.com/Singh01113/my-app-studio/issues/1) (learner supplied); local branch `feature/app-001-shiftboard` verified. [PR #2](https://github.com/Singh01113/my-app-studio/pull/2) merged as e28bf5c; Issue #1 closed. |

**Keep when:** the agreed identity is visible and usable at desktop/narrow widths;
full foundation + APP-001 checks pass; AI review and the learner's actual check
interpretation/browser observation/keep reason are recorded; reviewed evidence
and verified GitHub state are linked below.

### Local implementation

- `app/brand.json`: agreed identity, copy, voice, and shared color tokens.
- `app/static/logo.svg`: original conversation-board mark; `app/static/site.css`: responsive layout, visible keyboard focus, and reduced-motion support.
- `app/templates/base.html` and `home.html`: ShiftBoard wordmark, tagline, purpose, design principles, in-page navigation, and an explicit notice that accounts and team tools are unavailable.
- Learner-requested revision: content maximum width increased from 1080px to 1240px; larger body, navigation, supporting text, and headings; rebalanced section spacing. Mobile stacking, focus styles, and reduced-motion support retained.
- Supporting homepage copy and mark are AI-drafted from the approved brief. No account or role routes were implemented.

## APP-002 · Signup, login and logout

**Scope:** add browser forms and REST behavior for member signup, login, a private
dashboard and logout backed by SQLite. Reuse the prepared password/JWT/CSRF/session
helpers; keep data local. New accounts cannot choose their role. Preserve ShiftBoard branding and responsive layout. Employee/business records, APP-003, and deployment remain outside this scope.

| Decision | Agreement |
|---|---|
| Expected public/private behavior and account flow | Preserve ShiftBoard branding. Signup/login forms and REST routes share SQLite/security helpers. Dashboard redirects to login before authentication and after logout; authenticated users see their own account information. API identity requests return 401 before login and 200 after login. |
| Valid and rejected cases to demonstrate | Valid signup/login/dashboard/logout; reject duplicate or invalid signup, role input, wrong credentials, missing/invalid CSRF, and revoked/expired sessions. Use prepared hashing, signed expiring JWTs, HttpOnly cookies, input limits, throttling, and server-side revocation. Throwaway local accounts only. |
| Own issue / branch / PR | [Issue #3](https://github.com/Singh01113/my-app-studio/issues/3); codex/app-002-shiftboard; PR pending. |

**Keep when:** the agreed forms/API work; duplicate/invalid signup and wrong
credentials are rejected; passwords are hashed; authentication uses validated,
expiring JWTs with protected cookies and CSRF; private requests require a live
session and logout revokes it. Full cumulative checks, AI review, actual learner
contributions and GitHub state are recorded. This is not a production-security certification.

### APP-002 local implementation and checks

- app/features/accounts.py connects GET /api/csrf, POST /api/signup, POST /api/login, GET /api/me, and POST /api/logout to the existing security helpers. Browser GET/POST signup/login, protected GET dashboard, and POST logout use the same services.
- app/templates/account.html, dashboard.html, and account_error.html provide branded forms, current-account information, and recoverable errors. Password fields are never repopulated. Homepage availability copy now links to working account pages; api.html maps the routes. Account CSS preserves the shared logo, colors, and typography.
- tests/test_accounts.py adds route-level coverage for extra/duplicate fields, GET/CSRF logout rejection, expired/tampered JWTs, expired database sessions, public-only identity output, and unchanged admin-route absence. Existing helpers and acceptance contracts remain unchanged.
- Final full cumulative APP-002 rerun after the learner’s Keep report passed Black/Pylint, 106 foundation/regression tests, 14 cumulative contracts, and 2 Chromium tests. AI used an isolated temporary database for visual review: signup/login/dashboard at 1440, 390, and 320px had no horizontal overflow; inspected screenshots were legible. Wrong-login recovery, keyboard skip focus, logout, and denied dashboard revisit passed. API identity returned 200 while logged in, 401 after logout, and 401 when replaying a copied logged-out session.
- Final diff/security review found no blocking issue in the scoped account implementation. Prepared security/database helpers, schemas, brand/logo, and role source remain unchanged. No credential-pattern matches were found in changed/new files; test passphrase/key literals are disposable fixtures, and runtime data remains ignored.
- These are AI checks and observations, not the learner’s browser evidence. Learner separately reported successful signup/login/dashboard/logout and a redirect to login on a logged-out dashboard request, then chose Keep. Learner interpreted the copied-cookie replay test. Records approved; GitHub CI review and merge remain pending. No production or APP-003 features added.

## APP-003 · Server-enforced roles

**Scope:** enforce a small member/admin boundary in the API and browser. Assign
roles only through the trusted local terminal command; use current server-side
permissions, including for an existing session after a role change.

| Visitor | Homepage | Member area | Admin area/API |
|---|---|---|---|
| Anonymous | Allowed | Login required | Login required |
| Member | Allowed | Allowed | Forbidden |
| Admin | Allowed | Allowed | Allowed |

| Decision | Agreement |
|---|---|
| Intended admin-only result | Pending |
| Actual allowed/denied request evidence | Pending |
| Own issue / branch / PR | Pending |

**Keep when:** a direct request cannot bypass the role boundary, role changes
take effect as specified, new signup remains member-only, and full cumulative
checks plus AI review pass. Link the learner's actual interpretation/observation,
reviewed record and verified GitHub result. Hidden navigation alone is insufficient.

## Evidence

Link actual files/checks and the student's own issues/PRs. No fabricated URLs,
customer research or claims that a timestamp proves learning.

| Feature | Files / own issue / PR | Actual checks and learner observations | Kept / GitHub state |
|---|---|---|---|
| APP-001 | Files above; Issue #1; [PR #2](https://github.com/Singh01113/my-app-studio/pull/2) | Final `python3 studio.py check --lesson APP-001`: Black/Pylint passed; 98 foundation, 2 APP-001 contract, and 2 Chromium tests passed. Revised desktop/narrow visual review and keyboard/navigation checks passed as detailed below. Learner observation, prediction, check interpretation, revision feedback, and final Keep reason drafted in LEARNING.md. | Kept and merged; Issue #1 closed; check and windows passed on feature and merged main, verified through GitHub browser/API |
| APP-002 | [Issue #3](https://github.com/Singh01113/my-app-studio/issues/3); codex/app-002-shiftboard; files above | Full cumulative check and AI browser review passed; learner prediction, copied-cookie interpretation, and actual account-flow observation recorded | Learner chose Keep; local changes only; records approved; PR/CI/merge pending |
| APP-003 | Pending | Unfinished; explicit contracts not yet passed | Pending |

The instructor's reference branches show possible implementations. They do not
establish this repository's completion or the learner's own reasoning.

Check note: the prepared dependencies emit a Starlette/httpx deprecation warning; it did not fail the checks. These results do not establish full accessibility or security.

Revision validation: `python3 studio.py check` passed Black, Pylint, 98 foundation tests, 2 APP-001 contracts, and 2 real Chromium tests. AI inspected 1920px/390px screenshots and measured no horizontal overflow at 320, 390, 768, 1440, and 1920px. Skip-link focus, purpose navigation, and reduced-motion behavior passed. The existing dependency deprecation warning remains.
