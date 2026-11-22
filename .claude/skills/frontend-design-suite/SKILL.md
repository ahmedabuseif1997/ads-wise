---
name: frontend-design-suite
description: "Design, build, restyle, critique or polish websites, landing pages, app UI and design systems; match a named brand look; test in a browser with Playwright."
user-invocable: true
argument-hint: "[build|style <site>|impeccable <command>|browser|component-test|trace] [target]"
allowed-tools: Bash(playwright-cli:*) Bash(npx playwright:*) Bash(npx --no-install playwright:*)
hooks:
  Stop:
    - hooks:
        - type: command
          command: 'for f in ${CLAUDE_SKILL_DIR:+"$CLAUDE_SKILL_DIR/modules/design-taste-frontend/scripts/gate.mjs"} ${CLAUDE_PROJECT_DIR:+"$CLAUDE_PROJECT_DIR/.claude/skills/frontend-design-suite/modules/design-taste-frontend/scripts/gate.mjs"}; do if [ -f "$f" ]; then exec node "$f" --hook claude; fi; done; for d in .taste-skill */.taste-skill; do if [ -f "$d/build.json" ]; then echo "tasteskill gate: gate.mjs not found; the build in $d is not checked" >&2; break; fi; done; exit 0'
          timeout: 600
---

# Frontend Design Suite

Six modules merged into one skill. `<suite>` = the folder that contains this SKILL.md (the skill base directory the runtime reports; in this repo `.claude/skills/frontend-design-suite`, when synced from claude.ai somewhere else). Always use absolute paths built from it.
Each module keeps its full original instructions in `<suite>/modules/<module>/GUIDE.md`; every
relative path inside a GUIDE.md (`references/…`, `reference/…`, `scripts/…`, `assets/…`, `designs/…`)
resolves against that module's own folder, never against `<suite>`.

## Step 1: route the request, then read only that module's GUIDE.md

| Request | Module | Read |
|---|---|---|
| Build a new site / landing page / company, product, shop, SaaS, AI or game page; page looks generic or "AI-made"; full redesign of a marketing page | **taste** | `modules/design-taste-frontend/GUIDE.md` |
| Critique, audit, polish, animate, colorize, typeset, layout, harden, onboard, optimize, adapt, clarify, distill, bolder, quieter, delight, overdrive, shape, init, document, extract, live, generate; app UI, dashboards, components, native iOS/Android screens, design systems | **impeccable** | `modules/impeccable/GUIDE.md` |
| "Make it look like <brand/site>", pick a visual direction, need a ready DESIGN.md | **design-md** | `modules/design-md-library/GUIDE.md` (then `INDEX.md`, then one `designs/<site>/DESIGN.md`) |
| Drive a browser, take screenshots, fill forms, mock requests, record video, generate or run Playwright tests | **playwright-cli** | `modules/playwright-cli/GUIDE.md` |
| Test React or Vue components in isolation; migrate off `@playwright/experimental-ct-*` | **component-testing** | `modules/playwright-component-testing/GUIDE.md` |
| Inspect a Playwright `trace.zip` (actions, requests, console, errors, snapshots) | **trace** | `modules/playwright-trace/GUIDE.md` |

Routing rules:
- New marketing/company page from scratch → taste. Change, review or improve an existing UI, or
  product/app UI → impeccable. If both fit, the user's wording decides; if it does not, use taste
  for new pages and impeccable for everything else.
- A named brand look combines with a build module: read the design-md file for tokens and rules,
  then build with taste or impeccable using those tokens. Never copy the brand's logo, name,
  trademarks, imagery or copy.
- Verification in a real browser for any module may use playwright-cli.
- Read a second module only when the task actually needs it. Do not read all GUIDE.md files.

## Step 2: module-specific path rules

- **taste**: `<skill>` in its GUIDE.md = `<suite>/modules/design-taste-frontend`. Needs Node 22+
  and Chrome/Chromium. Its finish gate (`node <skill>/scripts/gate.mjs …`) also runs automatically
  at the end of each turn while this suite is active (Stop hook above); it only acts when a
  `.taste-skill/` build exists in the project.
- **impeccable**: `<skill-base-dir>` = `<suite>/modules/impeccable`. Run
  `<suite>/modules/impeccable/scripts/impeccable context` once per session from the project root
  before other impeccable commands. First run downloads its engine binary from the project's GitHub
  releases and verifies it against `scripts/engine-checksums.txt`.
- **design-md**: paths in its GUIDE.md are relative to `<suite>/modules/design-md-library`.
- **playwright-cli**: if `playwright-cli` is not installed, use `npx playwright cli` (Playwright
  ≥ 1.59) or install with `npm install -g @playwright/cli@latest` after the user approves.
- **component-testing / trace**: templates and references are relative to their module folder.

## Sources

| Module | Upstream | Commit | License |
|---|---|---|---|
| design-taste-frontend | Leonxlnx/taste-skill | f6b7657 | MIT |
| impeccable | pbakaus/impeccable (v4.10.0) | b49177d | Apache 2.0 |
| playwright-cli, playwright-component-testing, playwright-trace | microsoft/playwright | 0492267 | Apache 2.0 |
| design-md-library | VoltAgent/awesome-design-md | fcc7028 | MIT |
