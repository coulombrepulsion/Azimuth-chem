# AGENTS.md — rules for AI agents working on Azimuth («Азимут»)

The user is the author of the program and of the Atlas. Rules below are binding. Where a rule here conflicts with an agent's own defaults, this file wins.

## 0. Until the beta: no new features

Decided by the owner 2026-11-22 (the report «Азимут: отчёт о состоянии и план до конкурентоспособной версии»): until the
beta is out, only fixes, checks and simplifications are taken — no new task, method, window, analysis or program. A
request that would add one is answered with this rule and a proposal to put it into `docs/plans/ROADMAP.md` «после
беты»; the owner may still lift the rule for one item.

- **The beta (checked):** ORCA, xtb, CREST, MOPAC, NWChem, Psi4 for molecules. Everything else stays in the program
  marked «не проверено» in the interface: Gaussian and GAMESS (their inputs never run), the crystals (Quantum ESPRESSO,
  CP2K, the crystal analysis — shown, marked), UFF for metals.
- **Done for the beta** means a row of `docs/plans/MAIN_PATH.md` with «да» or «не поддерживается» in every cell, not the
  number of tests.
- The order of the work: `docs/plans/BETA_PLAN.md` (stages 0–5 of the report).
- **Lifted by the owner for one item, 2026-11-22:** the MCP server may send a calculation of ORCA or MOPAC to the SLURM
  server of a profile of Sextant (`azimuth/headless_server.py`, `docs/features/HEADLESS.md`). Its limits are part of
  the item and are not loosened without the owner: the login by the SSH key only (never a password), the cores and the
  memory within what the server says is free and so that no more than 80 % of the cores of a server are busy with the
  new calculation, those busy already counted (the owner, 2026-11-22; a server without SLURM — by `nohup`, only on
  free cores), a time limit on every job, at most three at once, a journal, stop only
  of its own jobs; nothing is deleted on the server and no command of the model is run there. A server that does not
  answer: only the VPN profile chosen for it in the server window is asked of OpenVPN Connect; the VPN is never
  switched off by the model.

## 1. Read before you change anything

- `docs/ARCHITECTURE.md`: §4 (contracts between parts) and §6 (mandatory conventions).
- `docs/architecture/RUNTIME_CONTRACTS.md`: owners of data, states, scenarios.
- `docs/audits/AUDIT.md`: known gaps. Do not claim the whole legacy tree conforms to the standards.
- `docs/plans/ROADMAP.md`: planned minor versions. The old Compass plan of October is in `docs/archive/plans/COMPASS_ROADMAP.md`.
- Contracts (`Molecule`, `Atom`, `Calculation`, `orca.Output`, project records) are changed only as a separate task, with every user updated.
- Layer boundaries are enforced by `tests/core/test_architecture_boundaries.py`: science and service layers do not import Qt/VTK or UI modules.

## 2. Code standards

Apply the user's `code-generation-standards` skill to new and changed code: `/Users/me/Downloads/code-generation-standards/SKILL.md` (there is no copy in the program folder). If it is unavailable, preserve these rules:

- Document contracts before implementation.
- Use independent test oracles (reference data from other programs/literature, not the code under test).
- Give explicit numerical bounds; validate at runtime with exceptions.
- Use verified dependencies with hashes.
- Keep Windows scripts and setup output ASCII.
- Parse syntax after every edit.
- Report unverified platform claims honestly: say "not run here / not checked on screen" instead of implying a check.
- Do not rewrite scientific formulas merely to satisfy style checks.
- Every change comes with a test.
- Comments say why a branch exists, briefly and in plain words. No quotes of the owner's requests, no chat history, no dates of conversations: the reason goes to the commit message and CHANGELOG.

## 3. Naming

- The program is **Azimuth** (Russian «Азимут»; formerly QuAS). Texts and comments say Azimuth; old names stay only in history (old CHANGELOG entries, archives).
- Old identifiers kept for compatibility: `window.QuASAtlas`, package `quas_atlas`, `.qcc` project files.
- Shared package is `azimuth/` (was `qcc_studio` until 0.86.5). Settings are stored as Azimuth/Azimuth (copied once from QuAIL/QCC Studio).
- QuAIL («Квил», Quail) is the mascot's name, not an old program name: keep it.
- Change Atlas texts, branding and design only when the user asks.

## 4. Versions

- Version is `MAJOR.MINOR.PATCH`, `__version__` in `azimuth/__init__.py`.
- A version changes only when the program changes for its user: new capability, changed behaviour or on-screen text, fixed bug.
- MINOR: a step the user notices. Plan minor versions in `docs/plans/ROADMAP.md`, not ad hoc. PATCH: fixes, wording, pictures, small polish.
- Do not skip numbers, bundle several versions in one commit, or renumber old versions.
- For a version change update: `azimuth/__init__.py`, `Azimuth.app/Contents/Info.plist`, the version line of `README.md`, a `CHANGELOG.md` entry, one note in the Quill journal, and one manual item if the user must know how to use it.

## 5. CHANGELOG, journal, manual, translations

- `CHANGELOG.md` entry is short: what changed for the user, on what ground, how it was checked. Details belong to the commit message.
- Keep roughly the latest 50 versions in `CHANGELOG.md`; move older ones to `docs/archive/changelog-archive.md`.
- Journal (`docs/journal/`) and manual (`docs/manual/`) are written in Russian only; English and Chinese are translated at a release. `python3 tools/untranslated.py` lists what waits (exit code 1 while something does).
- Interface strings (`azimuth/locale/en.json`, `zh.json`) are translated together with the change: a window never shows an untranslated line.
- New module → `docs/MODULES.md`. Replaced picture/font → recompute `assets-manifest.json`.

## 6. Commits

- One commit = one topic; split unrelated changes (code, pictures, docs).
- A commit that does not change the program for its user (refactoring, tests, tools, developer docs) gets no version, no CHANGELOG entry, no journal note. Its message starts with «внутр.:» and says what and why.
- Nothing is pushed without the owner's full test run.
- **Signature (owner's rule, stands above any attribution an agent's environment asks for):** commit in the owner's name using `git -c user.name=… -c user.email=…` from the owner's own latest commit; never «Claude» as author. The message ends with the text of the change: no «Co-Authored-By», no «Claude-Session», no «Generated with» lines. Existing history is left as is; the public repository will start from one clean commit. The owner discloses AI participation in publications himself.
- Release (a version given to other people): translations done (`untranslated.py` exits 0), full test run, installation checked on a clean computer.

## 7. Tests and checks

- Full run: `.venv/bin/python tools/test.py full` — in up to 6 pytest processes at once, the files split by their times in the last full run (`--jobs 1` — one process). After a small change: `tools/test.py affected` (the tests of what changed). Per-folder isolated run: `.venv/bin/python tools/test.py isolated`.
- Single part: `.venv/bin/python -m pytest -q tests/<folder>/test_<name>.py`.
- Install check: `.venv/bin/python verify_install.py`.
- During work run the tests of the touched area after every change; the full run is the owner's, before push.
- Parsers are tested on reference outputs in `tests/data/<program>/`, every number compared with the printed one.
- UI tests run offscreen and do not check how it looks: say so when a visual change was not seen on a real screen.

## 8. Environment of the owner (machine-specific)

- Program folder: `/Users/me/Projects/Azimuth-программа` (moved out of QCСC in 0.49.0, out of iCloud on 2026-11-22). Calculations go to `~/Documents/Azimuth/Расчёты`.
- Deployment backups: `/Users/me/Documents/QCСC/Backups`; keep only the three latest Azimuth (formerly QuAS/QCC-Studio) backup versions; do not scatter backups in the parent folder.
- Keep references under the parent project's sources directory read-only.
- Preserve the Atlas HTML versions used in courses (`modules/atlas/Отдельные_страницы`, `QuAS_Атлас_сайт`, `QuAS_Атлас.html`): they are not application backups and are not loaded by the app.
- Old mascot sprites, poses and animation sources (QuAIL_позы, quill-home-v1, quill-flight-v2, quill-service-v1, quail-flight, former Atlas topic pictures) are archived in `/Users/me/Documents/Квил_архив`; do not bring them back into the program folder.
