# Changelog

## 0.3.1

### What games need to do

- Nothing.

### Changes

- **Test page:** **Delete the save** and **Damage the save** close the game first. A game that saves as it
  closes (on `leave`) used to write its save back straight after, so the save wasn't deleted or damaged.
  (Found while trying Plenty Heaps' message for a damaged save.)

## 0.3.0

### What games need to do

- **Once, to get kit updates as pull requests:** replace `.github/workflows/build.yml` and `pages.yml`
  with the starter's, which call the kit's workflows at this release, and add `.github/dependabot.yml`.
  See docs/UPDATING.md. From then on, Dependabot opens a pull request in the game for each kit release.
- **Save as the learner plays**, not only when the page closes: in Kolibri Learn a save made as the page
  closes is lost (below). Games that save after every step need nothing.
- Add `tests/kolibri_play.py` so the real-Kolibri test checks the game's saving (docs/platforms/KOLIBRI.md).
- **A game with its own save format** should check it when it loads, and never save over one it couldn't read
  without asking the learner (docs/HELPER.md, "When a save can't be read"). The kit now does this for its record.

### Changes

- **A save that can't be read is never written over.** When what the platform kept is damaged (not
  JSON) or from a newer version of the game, the helper used to treat it as no save, and the game's
  first save replaced it. Now `ready()` says `saveProblem` ("unreadable" or "newer"), nothing is saved
  over it, and the helper asks the learner (Play without saving, or Start over), unless the game shows
  its own message with `EduGame.on("saveproblem")` and `EduGame.startOver()`. The test page has a
  **Damage the save** button, and `edugame kolibri-test` checks a damaged save survives in a real
  Kolibri. (Found while looking at saving in Plenty Heaps.)
- **Kit updates reach games as pull requests.** Games' workflows now call the kit's own
  `.github/workflows/game.yml` (check, build, real Kolibri) and `game-pages.yml` (GitHub Pages) at a kit
  release (`@v0.3.0`), and the starter has a `.github/dependabot.yml`, so Dependabot opens a pull request
  in each game when the kit has a new release, with the game's checks run on it. docs/UPDATING.md says
  how, and how to move a game made earlier. `tools/bump_version.py` changes the version everywhere it's
  named. The template repository is now updated when a kit release is published, not on every change
  to main.
- **Languages:** the kit's own words (the Options panel) are no longer in Kiswahili; they're in English,
  French, Spanish and Portuguese.
- **GitHub actions on Node.js 24:** actions/checkout v7, setup-python v7, upload-artifact v7,
  upload-pages-artifact v5 and deploy-pages v5, in the kit's workflows and the starter's (GitHub stops
  running actions on Node.js 20). Dependabot keeps them up to date in the kit too.
- **Kolibri:** a game that isn't finished on the learner's first visit now shows as started. The
  helper sets `incomplete` when the game opens, but only if the status read "not attempted"; Kolibri
  answers "" for a status not set yet, so nothing was set. The test page's Kolibri box now answers
  like Kolibri. (Found by the real-Kolibri test in Bobo na Mi, the first game that isn't finished on
  its first visit.)
- **GitHub Pages:** the front page's "Play in" links name each language in itself ("English ·
  Français"), not by the game's title in that language, which many games keep the same in every
  language (they all read "Bobo na Mi"). (Found while putting Bobo na Mi on GitHub Pages.)
- **Docs:** in Kolibri Learn, a save made as the page closes (`pagehide`, `EduGame.on("leave")`) never
  arrives: Kolibri stops listening before it closes the game's page. HELPER.md and KOLIBRI.md now say
  to save as the learner plays. (Found by the real-Kolibri test in Plenty Heaps.)
- **SCORM:** the helper sets `cmi.core.exit` to `suspend`, so learning systems keep the save for next
  time (Moodle and others may start a fresh attempt without it).
- **Saving as the page closes:** a new event, `EduGame.on("leave", fn)`, runs when the page closes,
  before the helper ends the SCORM session, so the game's last save arrives. Once the helper is ready,
  `EduGame.save()` writes at once instead of after a Promise step. Saves after the session has ended
  are refused with a clear message. The test page now refuses saves after `LMSFinish`, like learning
  systems do.
- **`edugame kolibri-test`** plays a game in a real Kolibri: it adds the zip to a channel in a
  throwaway Kolibri, opens it in Learn as a learner, and checks the save reaches Kolibri, fits
  SCORM 1.2, comes back on the next visit, and that the resource counts as done when it should.
  The game's play steps go in `tests/kolibri_play.py` (never put in the zip). See
  docs/platforms/KOLIBRI.md.
- The starters come with play steps, and the starter's Build workflow has a **Real Kolibri** job
  (so the jobs are now **Build**, **Real Kolibri** and **Checks passed**). The kit's own tests play
  both starters and Number Hunt in a real Kolibri.
- **Forms work in Kolibri.** Kolibri's sandboxed frame never submits forms, so in Learn the
  Scored starter and Number Hunt couldn't take an answer (found by the new test). The helper now
  sends forms' `submit` events itself, on every platform. The test page's frame is sandboxed as
  Kolibri's is, so `edugame preview` shows problems like this.

## 0.2.0

- **Rulesets** for game repositories in `docs/rulesets/`: one for repositories with code (pull requests only, and
  the check **Checks passed** must pass), one for repositories a workflow writes to. The kit's tests and the
  starter's Build workflow have a **Checks passed** job, so new games fit the ruleset from the start.

- **Options:** the helper adds a header with the game's title and an Options button (only the
  button on the Kolibri Games games page). The panel lays over the game: Appearance (light, dark or
  auto, as `data-theme` on the page), Language (each in its own name), and options of the game's
  own (`EduGame.addOption`). Appearance and options show at once; the language changes on Apply;
  Back puts things back.
- **Languages:** the learner's choice is kept in their save, and comes before `?lang=`, the
  platform's language (Kolibri's, from the Kolibri Games plugin), the browser's and the default.
  Lang files take lists of paragraphs, plural sets, `_language` (the language's own name and
  direction) and `_notes` for translators. A regional file (`en-GB`) only needs the words that
  differ. New calls: `lines`, `number`, `language`, `languages`, `setLanguage`, `on("languagechange")`.
- **Content:** folders listed under `content` are built into small scripts the game loads when it
  needs them (`EduGame.load`, `EduGame.loadLanguage`), as translations or as editions. The build
  lists the files it put in, so the helper never asks for one that isn't there.
- **Packages:** several zips from one folder (`packages`, `package_files`), with `edugame build
  --package`, `--lang` and `--each-language`. The GitHub Pages site lists every package.
- `exclude` in `edugame.json` leaves files out of the game (tools, notes).
- `edugame check` lists words the code uses that the lang files don't have.
- The templates and examples use the header, the theme and translated words throughout. Memory
  Match has an option of its own.
- Guide: docs/LANGUAGES.md (it replaces TRANSLATING.md).
- **Template repository:** github.com/togetherings/edugame-template, made from the saved starter and kept up to
  date by a workflow, for making a game without installing anything.
- `edugame new --github` also adds a Build workflow: it checks the game, keeps the zips from each push, and attaches
  them to each release.

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
