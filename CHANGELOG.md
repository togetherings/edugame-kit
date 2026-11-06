# Changelog

## 0.1.0

First version.

- **Saved Games and Scored Games**, made from a folder with `edugame.json`, `lang/` and web files.
- **The save helper** (`edugame.js`): saves progress and scores on the Kolibri Games games page
  (through its SDK), in SCORM 1.2 learning systems (Kolibri channels, Moodle and others), in
  Sugarizer's Journal (with sugar-web) or in the browser. Inside a frame it waits for a late SCORM
  connection, as Kolibri's can be.
- **Scores of every kind** (docs/SCORING.md): one score, or several `fields` each ranked its own
  way (`rank_by`: the first ranks, the next ones break ties), with or without a time; the first,
  best or latest round, or every round added up (`counts`); rounds that aren't passed; and levels,
  each with its own result and Kolibri Games scoreboard, plus a total scoreboard. The kit can
  describe the scoring of Lessons In Typing, Studies In Geography and Sparkle.
- **Kolibri gets no score** (it would read one as how much is done): only the status, `incomplete`
  then `passed`. Other learning systems get a 0-100 grade when `scoring.grade` says how.
- **The build tool** (`edugame`): `new`, `check`, `preview`, `build` and `translate`. `build`
  makes the universal zip (Kolibri, Kolibri Games, SCORM 1.2, RACHEL), and with `--sugarizer` and
  `--zim` a Sugarizer activity and a ZIM file for Kiwix.
- **Translations:** every game lists its languages; the helper picks the learner's language and
  fills in `data-t` text, and sets right-to-left for Arabic, Persian, Hebrew and Urdu.
- **The test page:** plays a game as a learning system or a website and shows what it saves.
- Templates for both kinds, and two examples moved from Kolibri Games: Number Hunt and Memory
  Match, now in English and French.
- **GitHub Pages:** `edugame pages` makes a site with a front page and the game, and
  `edugame new --github` adds a workflow that publishes it. Visits and rounds can be counted with
  GoatCounter (no cookies), only on the site, never in the zips. The kit publishes Number Hunt.
- Guides for Kolibri, Moodle, RACHEL, Sugarizer, Kiwix, GitHub Pages and other learning systems,
  and the plan for LTI 1.3.
