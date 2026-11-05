# App Studio decisions

The durable agreement between learner and AI. Update only agreed decisions and
actual evidence; pending is a valid state. Keep explanations/help in
[LEARNING.md](LEARNING.md), not a second copy here.

## Current stage

- **Current feature:** APP-003.
- **Status:** APP-002 merged as c5c8ce3 via [PR #4](https://github.com/Singh01113/my-app-studio/pull/4); Issue #3 closed. Both check/windows jobs passed on the feature commit and merged main, verified through GitHub. APP-003 scope agreed, prediction recorded and approved, and implementation authorized. Local implementation, full cumulative checks, and AI review passed; learner check interpretation, browser observations, and Keep decision are recorded; final records approved; commit/push/PR authorized, GitHub completion pending.
- **Next step:** Commit and push the seven approved files and create the PR linked to Issue #5. Review both CI jobs before any merge; no merge or deployment authorized.
- **Implementation marker:** `studio.json` declares `implemented_through: 3` after full APP-003 checks passed; the normal full check also passed. This records tested implementation, not lesson completion.

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
| Own issue / branch / PR | [Issue #3](https://github.com/Singh01113/my-app-studio/issues/3); codex/app-002-shiftboard; [PR #4](https://github.com/Singh01113/my-app-studio/pull/4) merged as c5c8ce3; Issue #3 closed. |

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
- These are AI checks and observations, not the learner’s browser evidence. Learner separately reported successful signup/login/dashboard/logout and a redirect to login on a logged-out dashboard request, then chose Keep. Learner interpreted the copied-cookie replay test. Records approved; PR #4 merged and both CI jobs passed on feature and merged main. No production or APP-003 features added.

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
| Intended admin-only result | A ShiftBoard-branded GET /admin page and GET /api/admin show the current administrator’s username and an access confirmation only. Anonymous page requests redirect to /login (303); anonymous API requests receive 401. Members receive 403 on both; admins receive 200. |
| Permission source and role changes | Reuse prepared security helpers and current SQLite role on every request. Existing sessions reflect promotion/demotion on the next request. Use only the trusted local studio.py user role command; signup remains member-only. Show Admin navigation only for admins. |
| Preservation and boundaries | Preserve homepage, branding, signup, login, dashboard, and logout. No public role-changing endpoint, expanded administration product, or deployment. |
| Actual allowed/denied request evidence | Full contracts passed: anonymous API 401/page 303 to login; member API/page 403; admin API/page 200. Promotion and demotion affect existing sessions. A stale signed admin claim cannot override the member role in SQLite. |
| Own issue / branch / PR | [Issue #5](https://github.com/Singh01113/my-app-studio/issues/5); codex/app-003-shiftboard; PR pending. |

**Keep when:** a direct request cannot bypass the role boundary, role changes
take effect as specified, new signup remains member-only, and full cumulative
checks plus AI review pass. Link the learner's actual interpretation/observation,
reviewed record and verified GitHub result. Hidden navigation alone is insufficient.

### APP-003 local implementation and checks

- app/features/roles.py uses the prepared security.require_admin guard for both GET /api/admin and GET /admin. API success contains only username and an access confirmation; HTML redirects anonymous users to login and returns a branded 403 page for members.
- app/templates/admin.html reuses the existing shared layout and styles. The prepared base template already conditionally shows Admin navigation using the current database role; no base/CSS/helper/CLI changes were needed.
- tests/test_roles.py covers navigation after promotion/demotion, limited API output, no-store responses, and copied administrator-cookie rejection after logout. The earlier account regression now expects member denial (403) on the newly implemented routes instead of route absence (404); prepared contracts remain unchanged.
- python3 studio.py check --lesson APP-003 passed Black/Pylint, 108 foundation/regression tests, 18 cumulative contracts, and 2 real Chromium tests. After setting implemented_through to 3, python3 studio.py check passed the same 128 tests. Initial formatting and sandbox execution failures were resolved before these successful runs. The existing Starlette/httpx deprecation warning remains.
- Separate AI Chromium review used an isolated temporary database and the prepared trusted CLI: member API 403, promotion to admin page/API 200, then demotion page/API 403 in the same session. Navigation reflected each role. Signup/login/dashboard/logout and revoked-cookie rejection still worked. Admin and denied-page screenshots were inspected at 1440px/390px; no horizontal overflow at 1440px/390px/320px, keyboard skip focus passed, and no browser errors occurred.
- Final full APP-003 rerun after the learner’s Keep report passed Black/Pylint, 108 foundation/regression tests, 18 cumulative contracts, and 2 Chromium tests (128 total). Git whitespace check passed. Review of all seven changed/new files found no credential-pattern matches, tracked local database/key/environment files, or unrelated changes.
- AI source/security review found no blocking issue in this scope. Prepared helpers, signup behavior, branding, and trusted CLI remain unchanged. No public role-changing endpoint or deployment was added. Learner interpreted the demotion check, independently tested member/admin access and role changes without logout, and chose Keep because permissions worked and existing features remained intact. The approved promotion was run by AI; the learner reported performing the demotion. Updated records approved; GitHub completion remains pending.

## Evidence

Link actual files/checks and the student's own issues/PRs. No fabricated URLs,
customer research or claims that a timestamp proves learning.

| Feature | Files / own issue / PR | Actual checks and learner observations | Kept / GitHub state |
|---|---|---|---|
| APP-001 | Files above; Issue #1; [PR #2](https://github.com/Singh01113/my-app-studio/pull/2) | Final `python3 studio.py check --lesson APP-001`: Black/Pylint passed; 98 foundation, 2 APP-001 contract, and 2 Chromium tests passed. Revised desktop/narrow visual review and keyboard/navigation checks passed as detailed below. Learner observation, prediction, check interpretation, revision feedback, and final Keep reason drafted in LEARNING.md. | Kept and merged; Issue #1 closed; check and windows passed on feature and merged main, verified through GitHub browser/API |
| APP-002 | [Issue #3](https://github.com/Singh01113/my-app-studio/issues/3); codex/app-002-shiftboard; files above | Full cumulative check and AI browser review passed; learner prediction, copied-cookie interpretation, and actual account-flow observation recorded | Learner chose Keep; records approved; PR #4 merged, Issue #3 closed, both CI jobs passed on feature and merged main |
| APP-003 | Files above; [Issue #5](https://github.com/Singh01113/my-app-studio/issues/5); codex/app-003-shiftboard | Full cumulative and normal checks passed; AI browser review completed | Local only; learner chose Keep after same-session promotion/demotion browser tests; records approved; commit/push/PR authorized, GitHub completion pending |

The instructor's reference branches show possible implementations. They do not
establish this repository's completion or the learner's own reasoning.

Check note: the prepared dependencies emit a Starlette/httpx deprecation warning; it did not fail the checks. These results do not establish full accessibility or security.

Revision validation: `python3 studio.py check` passed Black, Pylint, 98 foundation tests, 2 APP-001 contracts, and 2 real Chromium tests. AI inspected 1920px/390px screenshots and measured no horizontal overflow at 320, 390, 768, 1440, and 1920px. Skip-link focus, purpose navigation, and reduced-motion behavior passed. The existing dependency deprecation warning remains.
