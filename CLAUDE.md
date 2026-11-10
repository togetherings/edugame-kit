# Notes for working on this repository

- `edugame/` is the kit: `runtime/edugame.js` (the save helper every game loads), `runtime/test.html`
  (the test page), `project.py` (reads edugame.json and lang/), `platforms.py` (each platform's
  files), `build.py`, `cli.py` (the `edugame` command), `templates/` (`edugame new`).
- Standard library only in Python (libzim is optional, for ZIM files). The helper is plain ES5-style
  JavaScript with Promises, for old phones: no build step, no libraries.
- Scoring is in `scoring.py` (edugame.json's `scoring`: short form, or fields + rank_by + counts +
  boards + grade). The helper saves each board as a list of the fields' values in `fields` order
  ({"_v": 1, "_save": ..., "main": [...]}), which Kolibri Games reads (its `scoring.py`, `ranking.py`,
  `channel.py`). Change both together. `Project.kolibri_manifest` must pass the plugin's
  `manifest.validate` (a test checks, when kolibri-games is installed).
- Never send a score to Kolibri itself (it reads SCORM score.raw as how much is done). In Kolibri
  the helper only sets status `incomplete`, then `passed` (never `completed`).
- The kit must be able to score every existing game (LIT, SINGE, Sparkle: `EXISTING` in
  tests/test_project.py). BoBo Na Mi will be a Saved Game.
- Only Saved and Scored Games are made with the kit. Server Games belong to the plugin.
- Examples (`examples/`) and templates must stay fully translated (a test checks).
- Words live in `lang/<code>.json` (with `_language` and `_notes`), content in the folders under
  `content`, settings in edugame.json: docs/LANGUAGES.md. The helper owns the language choice, the
  header and the Options panel; games don't add their own title or settings page.
- The template repository (togetherings/edugame-template) is generated from `edugame/templates/` by
  `tools/make_template_repo.py` and pushed by the `Template repository` workflow: change the starter here, not there.
- Tests: `python -m pytest`; `python -m tests.e2e_browser` (Playwright; plays on the Kolibri Games
  games page too when kolibri-games is installed).
- Games call the kit's `.github/workflows/game.yml` and `game-pages.yml` at a release (`@vX.Y.Z`), and
  Dependabot moves them on (docs/UPDATING.md). Those workflows' `KIT_REF` and the starter's `@v...` must
  equal `v` + `__version__` (a test checks): change all of them with `python tools/bump_version.py X.Y.Z`.
  Each CHANGELOG release says under **What games need to do** what games must change themselves.
- Bump the version (`tools/bump_version.py`) and add a CHANGELOG entry before a release. Releases
  are published by a person in GitHub's Releases page (tag `vX.Y.Z`); the Release workflow builds
  and attaches the files. Claude sessions can't create tags or releases.
- Writing style for anything users see: plain words, sentence case, active voice.
