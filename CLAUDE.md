# Notes for working on this repository

- `edugame/` is the kit: `runtime/edugame.js` (the save helper every game loads), `runtime/test.html`
  (the test page), `project.py` (reads edugame.json and lang/), `platforms.py` (each platform's
  files), `build.py`, `cli.py` (the `edugame` command), `templates/` (`edugame new`).
- Standard library only in Python (libzim is optional, for ZIM files). The helper is plain ES5-style
  JavaScript with Promises, for old phones: no build step, no libraries.
- The save format in SCORM `cmi.suspend_data` ({"_v": 1, "_save": ..., "main": [best, seconds, plays]})
  is read by Kolibri Games (github.com/togetherings/kolibri-games, `channel.py` and
  `manifest.default_scoreboards`). Change both together. `Project.kolibri_manifest` must pass the
  plugin's `manifest.validate` (a test checks, when kolibri-games is installed).
- Only Saved and Scored Games are made with the kit. Server Games belong to the plugin.
- Examples (`examples/`) and templates must stay fully translated (a test checks).
- Tests: `python -m pytest`; `python -m tests.e2e_browser` (Playwright; plays on the Kolibri Games
  games page too when kolibri-games is installed).
- Bump `__version__` in `edugame/__init__.py` and add a CHANGELOG entry before a release. Releases
  are published by a person in GitHub's Releases page (tag `vX.Y.Z`); the Release workflow builds
  and attaches the files. Claude sessions can't create tags or releases.
- Writing style for anything users see: plain words, sentence case, active voice.
