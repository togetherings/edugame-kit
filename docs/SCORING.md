# Scores

A Scored Game says in `edugame.json` what its scores are and how they're ranked. The same
`scoring` section works everywhere: the save helper keeps each learner's result by it, Kolibri
Games builds its scoreboards from it, and learning systems get a grade from it.

## One score

```json
"scoring": {
  "order": "asc",
  "tiebreak": "seconds",
  "counts": "first",
  "min": 1,
  "max": 1000,
  "grade": { "full": 1, "zero": 20 }
}
```

| Setting | Meaning |
|---|---|
| `order` | `"asc"` if a lower score is better (guesses, moves); `"desc"` if higher is better (points). |
| `tiebreak` | `"seconds"`: a faster round wins a tie (the helper times rounds). `"none"`: the game has no time at all. |
| `counts` | Which round is the learner's result: see [Which round counts](#which-round-counts). |
| `min`, `max` | Kolibri Games refuses scores outside these. |
| `grade` | For learning systems' gradebooks: the score that gets 100% (`full`) and 0% (`zero`). Leave it out to send no grade. |

The score is named by `score_label` and `score_unit` in `lang/<code>.json`, so it's translated:
`"score_label": "Guesses"`, `"score_unit": "guesses"`.

```js
EduGame.start();
// ... the round ...
EduGame.finish(12).then(function (r) { /* r.score, r.best, r.newBest */ });
```

## Several scores

List them as `fields`, and say in `rank_by` which ones rank learners: **the first decides, the next
ones break ties, and each has its own order**. A game can rank by higher accuracy and then higher
speed (Lessons In Typing), higher accuracy and then lower time (Studies In Geography), or fewer
misses and then more points.

```json
"scoring": {
  "fields": [
    { "key": "acc",   "label": "accuracy", "unit": "%",   "order": "desc", "min": 0, "max": 100, "total": "average" },
    { "key": "wpm",   "label": "speed",    "unit": "wpm", "order": "desc", "total": "average" },
    { "key": "plays", "label": "times_played", "source": "plays" }
  ],
  "rank_by": ["acc", "wpm"],
  "counts": "best",
  "grade": { "field": "acc", "full": 100, "zero": 50 }
}
```

```js
EduGame.finish({ acc: 97, wpm: 41 });
```

Each field:

| Setting | Meaning |
|---|---|
| `key` | Its name, used in `finish()`: lower-case letters, digits or `_`. |
| `label`, `unit` | A word in `lang/` (so it's translated), or the text itself. A `unit` of `%` shows as `97%`. |
| `order` | `"asc"` (lower is better) or `"desc"` (higher is better). Fields in `rank_by` need one. |
| `source` | `"game"` (the game reports it in `finish()`; the default), `"time"` (the helper times the round; Kolibri Games measures it itself) or `"plays"` (how many rounds the learner has finished). |
| `total` | How values add up when every round counts (`counts: "total"`) and on a total scoreboard: `"sum"` (the default), `"average"`, `"min"`, `"max"`, `"best"` or `"latest"`. |
| `min`, `max`, `decimals` | Impossible values are refused; decimals to show. |

The first field in `rank_by` must be one the game reports. `finish()` needs a value for every
reported field in `rank_by`; the others are optional.

## Which round counts

| `counts` | The learner's result is | For example |
|---|---|---|
| `"first"` | their first round. Later rounds are practice. | A fair class contest |
| `"best"` | their best round, by `rank_by`. Every value comes from that one round. | Lessons, maps |
| `"latest"` | their latest round. | Progress checks |
| `"total"` | every round added up, each field by its `total`. | Points earned day after day |

In Kolibri Games, coaches can change it for their classes.

## Not passed

`EduGame.finish(values, { passed: false })` records that a round was played, but doesn't keep it
as a result: a lesson whose pass marks weren't reached, say. `EduGame.complete()` and every
passed round set the SCORM status to `passed`.

## Levels and lessons

A game with levels (lessons, maps, puzzles) can keep a result for each, and Kolibri Games shows a
scoreboard for each, and one for the whole game:

```json
"scoring": {
  "fields": [ ... ],
  "rank_by": ["acc", "wpm"],
  "boards": {
    "label": "lesson",
    "names": { "en-01": "lesson_1", "en-02": "lesson_2" },
    "total": { "label": "all_lessons", "count_label": "lessons_passed" }
  }
}
```

```js
EduGame.start({ board: "en-02" });
EduGame.finish({ acc: 97, wpm: 41 });         // kept for "en-02"
EduGame.ready().then(function (info) {
  info.results["en-02"];                       // {acc: 97, wpm: 41, plays: 1}
});
```

- A level's id (its **board**) is letters, digits, `.`, `_`, `:` or `-`. Never change it once
  learners have played: their results are kept under it.
- `names` names levels with words from `lang/` (or the text itself).
- `total` adds a scoreboard that adds up each learner's levels, field by field with each field's
  `total`, after a count of levels (named by `count_label`). It ranks by that count, then by
  `rank_by`, unless `total.rank_by` says otherwise.

### A scoreboard for each language

Boards needn't be levels. A game played in several languages can make each language a board, so
learners playing in French aren't ranked against learners playing in English (Sparkle does this):

```json
"boards": { "label": "board_label", "names": { "en": "board.en", "fr": "board.fr" } }
```

```js
EduGame.start({ board: EduGame.language() });
EduGame.finish(points);                       // kept for the language the round started in
EduGame.on("languagechange", function () { /* show that language's results and scoreboard */ });
```

Leave out `total` unless a scoreboard across languages makes sense for the game.

## What the helper saves

In SCORM `cmi.suspend_data` (Kolibri channels, Moodle) and in the browser, each level is a key
holding a list of the fields' values, in `fields` order:

```json
{ "_v": 1, "_save": { "unlocked": 3 }, "en-01": [95, 15, 3], "en-02": [97, 41, 1] }
```

A game without levels uses `main`. This is how Kolibri Games reads scores in channels. Keep the
order of `fields` once learners have played; add new fields at the end.

## Grades and Kolibri

**Kolibri itself gets no score.** Kolibri reads a SCORM score as how much of a resource is done,
so a resource would only count as done at 100. In Kolibri, the helper only sets the status:
`incomplete`, then `passed`. Its scoreboards come from Kolibri Games instead.

**Other learning systems** (Moodle and the rest) get a 0-100 grade in `cmi.core.score.raw` when
`scoring.grade` says how: `field` (the first ranked field if left out), the value for 100%
(`full`) and for 0% (`zero`). The helper sends the learner's kept result, and only ever raises
the grade.

## Our games, as examples

| Game | Scoring |
|---|---|
| Number Hunt | One score, lower is better, time breaks ties, first round counts. |
| Memory Match | One score, lower is better, time breaks ties, best round counts. |
| Lessons In Typing | `acc` then `wpm`, both `desc`; a board per lesson and a total; rounds that miss the pass marks are `passed: false`. |
| Studies In Geography | `acc` (`desc`) then `time` (`source: "time"`, `asc`); a board per map and mode, and a total. |
| Sparkle | `score` (`desc`) and `plays`, `counts: "total"`: each day's points add up; a board for each language, and no total. |

The full sections for the last three are in the kit's tests (`tests/test_project.py`,
`EXISTING`).
