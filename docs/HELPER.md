# The save helper: `edugame.js`

Every game loads `edugame.js`, and uses the same few calls wherever it runs. The helper finds out
where it is and saves the best way there.

## Calls

```js
EduGame.ready().then(function (info) {
  // info.save       what you saved last time, or null
  // info.best       Scored Games: the learner's best score, or null
  // info.bestSeconds, info.plays
  // info.settings   the settings (from Kolibri Games, or the defaults in edugame.json)
  // info.language   the language chosen, like "fr"
  // info.platform   "kolibri-games", "scorm", "sugarizer" or "local"
  // info.canExit    true if the platform has a page to go back to (show a "back" button)
  // info.rules, info.challenge   Kolibri Games only: the coach's rules and challenge, or null
});

EduGame.save({ level: 3, stars: [1, 1, 0] });  // a Promise; call it after each step
EduGame.complete();                            // the learner has finished the activity

// Scored Games
EduGame.start();                       // a round begins: the helper starts timing it
EduGame.finish(12).then(function (r) { // the round's score
  // r.score, r.seconds, r.best, r.newBest
  // r.platform: on the Kolibri Games games page, the plugin's result ({attempt, standing}), else null
});

EduGame.t("found", { n: 3 });   // the translated text for "found", with {n} filled in
EduGame.translatePage();        // fill in data-t elements again (ready() does it once)
EduGame.exit();                 // go back, where info.canExit

// Only do something on the Kolibri Games games page (safe to call anywhere):
EduGame.move("guess", { value: 42 });   // coaches see every move
EduGame.scoreboard();                   // Promise of {rows: [...]}, or null elsewhere
EduGame.on("timeup", function () {});   // the coach's time limit ran out
```

In HTML, `data-t="key"` fills an element's text, and `data-t-attr="aria-label:key"` fills an
attribute. See [TRANSLATING.md](TRANSLATING.md).

## Where it saves

The helper checks, in this order:

| Where | How it knows | Saves | Scores |
|---|---|---|---|
| **Kolibri Games games page** | the game is served from the plugin's `play/` address | `KolibriGames.setState` (up to 64 KB), in the learner's account | the plugin's attempts: scoreboards, challenges, every move for coaches |
| **SCORM 1.2**: Kolibri Learn, Moodle, other learning systems | a SCORM `API` object in this page or a parent page | `cmi.suspend_data` (up to 4,096 characters) | kept in `cmi.suspend_data`; a 0-100 grade in `cmi.core.score.raw` |
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
- `main` (Scored Games) is `[best score, seconds for that score, times played]`.

Kolibri Games reads `main` to show **scoreboards for Scored Games in Kolibri channels**, and
skips keys that start with `_`. In SCORM systems, the helper also sets `cmi.core.lesson_status` to
`incomplete` when the game opens and `completed` after `complete()` or a finished round.

## Things to know

- **Kolibri channels** sync each learner's saved data between Kolibri servers, so a learner can
  carry on from another device that syncs.
- **Moodle** keeps saves per attempt. With "Force new attempt" turned on, every attempt starts
  afresh. See [platforms/MOODLE.md](platforms/MOODLE.md).
- **The browser** keeps saves on that device only, and private browsing may drop them.
- Scores come from the game in the learner's browser, so they can be changed by someone who
  knows how. These are learning games, not tests.
