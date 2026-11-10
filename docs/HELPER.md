# The save helper: `edugame.js`

Every game loads `edugame.js`, and uses the same few calls wherever it runs. The helper finds out
where it is and saves the best way there.

## Calls

```js
EduGame.ready().then(function (info) {
  // info.save       what you saved last time, or null
  // info.results    Scored Games: the learner's kept result on each level, {main: {score: 7, time: 41.5, plays: 3}}
  // info.best       the first ranked score of "main" (games without levels), or null
  // info.bestSeconds, info.plays
  // info.settings   the settings (from Kolibri Games, or the defaults in edugame.json)
  // info.language   the language chosen, like "fr"; info.languages: [{code, name, dir}]
  // info.theme      "light", "dark" or "auto"
  // info.platform   "kolibri-games", "scorm", "sugarizer" or "local"
  // info.canExit    true if the platform has a page to go back to (show a "back" button)
  // info.rules, info.challenge   Kolibri Games only: the coach's rules and challenge, or null
});

EduGame.save({ level: 3, stars: [1, 1, 0] });  // a Promise; call it after each step
EduGame.complete();                            // the learner has finished the activity
EduGame.on("leave", function () {              // the page is closing: the last save goes here
  EduGame.save(currentProgress());
});

// Scored Games (see SCORING.md)
EduGame.start();                       // a round begins: the helper starts timing it
EduGame.start({ board: "en-02" });     // ... on a level
EduGame.finish(12).then(function (r) { // the round's score
  // r.score, r.values, r.seconds, r.kept (the learner's result now), r.best, r.newBest
  // r.platform: on the Kolibri Games games page, the plugin's result ({attempt, standing}), else null
});
EduGame.finish({ acc: 97, wpm: 41 });           // several scores
EduGame.finish({ acc: 72, wpm: 9 }, { passed: false });  // played, but not a result

EduGame.abandon();              // the round ends without a result
EduGame.exit();                 // go back, where info.canExit

// Words and languages (see LANGUAGES.md)
EduGame.t("found", { n: 3 });   // the word "found" in the current language, with {n} filled in
EduGame.lines("help");          // a list of paragraphs
EduGame.number(1234.5, 1);      // written the way the language writes numbers
EduGame.translatePage();        // fill in data-t elements again (done for you when the language changes)
EduGame.language();             // "fr"
EduGame.setLanguage("sw");      // change it, and remember the learner's choice
EduGame.on("languagechange", function (e) { /* make your own text again */ });

// Options (see LANGUAGES.md): the panel the header's Options button opens
EduGame.addOption({ key: "speed", label: "option_speed", choices: [{ value: "normal", label: "speed_normal" }] });
EduGame.option("speed");
EduGame.on("optionchange", function (e) {});   // e.key, e.value
EduGame.theme(); EduGame.setTheme("dark");     // <html data-theme="light|dark">
EduGame.openOptions();

// Content (see LANGUAGES.md)
EduGame.load("words/fr.json");                   // Promise of the data, or null
EduGame.loadLanguage("maps/us/lang");            // the current language's words over the default's
EduGame.loadLanguage("lessons/01", { merge: false });  // the nearest language's edition
EduGame.config.package;                          // {id, title, config} in a package's build

// Only do something on the Kolibri Games games page (safe to call anywhere):
EduGame.move("guess", { value: 42 });   // coaches see every move
EduGame.scoreboard({ board: "en-02" }); // Promise of {rows: [...], boards}, or null elsewhere
EduGame.on("timeup", function () {});   // the coach's time limit ran out
```

In HTML, `data-t="key"` fills an element's text, and `data-t-attr="aria-label:key"` fills an
attribute. See [LANGUAGES.md](LANGUAGES.md).

## Where it saves

The helper checks, in this order:

| Where | How it knows | Saves | Scores |
|---|---|---|---|
| **Kolibri Games games page** | the game is served from the plugin's `play/` address | `KolibriGames.setState` (up to 64 KB), in the learner's account | the plugin's attempts: scoreboards, challenges, every move for coaches |
| **SCORM 1.2**: Kolibri Learn, Moodle, other learning systems | a SCORM `API` object in this page or a parent page (inside a frame, it waits up to 1.5 seconds for it, and keeps looking for 10) | `cmi.suspend_data` (up to 4,096 characters) | kept in `cmi.suspend_data`; outside Kolibri, a 0-100 grade in `cmi.core.score.raw` |
| **Sugarizer** with sugar-web | built with `--sugar-lib` | the Journal entry of this activity | kept with the save |
| **Anywhere else**: RACHEL, Kiwix, a website | nothing above | the browser's `localStorage`, under `edugame:<id>` | kept with the save |

If a platform's connection fails to open, the helper saves in the browser instead, so the game
still works.

## What it saves

Outside Kolibri Games, the helper keeps one JSON object:

```json
{ "_v": 1, "_save": { "level": 3 }, "main": [12, 41.5, 4] }
```

- `_save` is what the game passed to `EduGame.save()`.
- Every other key (Scored Games) is a level, or `main` for a game without levels, holding the
  learner's kept result: one value for each of `scoring.fields`, in that order. For one score
  that's `[score, seconds, times played]`.

Kolibri Games reads these to show **scoreboards for Scored Games in Kolibri channels**, and
skips keys that start with `_`. In SCORM systems, the helper also sets `cmi.core.lesson_status` to
`incomplete` when the game opens and `passed` after `complete()` or a passed round (never
`completed`, which Kolibri ignores), and `cmi.core.exit` to `suspend`, so systems keep the save for
next time (without it, Moodle and others may start a fresh attempt). **It never sends Kolibri a score**: Kolibri reads a SCORM score
as how much of a resource is done. Other learning systems get a grade when `scoring.grade` says
how (see [SCORING.md](SCORING.md)).

## Saving as the page closes

**Save as the learner plays: after every step that matters, or every few seconds while something
changes.** Don't count on a last save as the page closes. In Kolibri Learn it never arrives when the
learner goes back to the channel or to another resource: Kolibri stops listening and sends what it
has before it closes the game's page, so anything saved while the page closes is lost. (Kolibri also
waits about 2 seconds after a save before sending it, and sends it straight away when the learner
leaves, so a save made a moment before leaving is fine.)

The last save still helps elsewhere: when the learner closes the tab, and in other learning systems.
When the learner leaves (closes the page, goes back in Kolibri, follows a link), the browser fires
`pagehide`. The helper then calls the game's `EduGame.on("leave", ...)` handlers, and only after them
ends the learning system's session (SCORM `LMSFinish`, after which systems refuse saves). So:

- **Make the last save in `EduGame.on("leave", ...)`.** Once the helper is ready, `EduGame.save()`
  writes at once, so this save reaches the learning system (but not Kolibri Learn: see above).
- A save in your own `pagehide` listener arrives only if it runs before the helper's, so prefer
  `leave`. A save after that (for example in a `visibilitychange` that follows `pagehide` when a
  visible page closes) is refused, and its Promise says so.
- Phones may close a game in the background without `pagehide`: also save when the page is hidden
  (`visibilitychange`), as long as the page isn't already leaving.

## Things to know

- **Kolibri channels** sync each learner's saved data between Kolibri servers, so a learner can
  carry on from another device that syncs.
- **Moodle** keeps saves per attempt. With "Force new attempt" turned on, every attempt starts
  afresh. See [platforms/MOODLE.md](platforms/MOODLE.md).
- **Forms:** Kolibri runs games in a sandboxed frame where the browser never submits a form, so
  Enter and submit buttons would do nothing. The helper sends a form's `submit` event itself, on
  every platform: handle `submit` and call `preventDefault()`, as usual, and it works everywhere.
  Kolibri's frame also blocks pop-ups and `alert()`; the test page is sandboxed the same way.
- **The browser** keeps saves on that device only, and private browsing may drop them.
- Scores come from the game in the learner's browser, so they can be changed by someone who
  knows how. These are learning games, not tests.
