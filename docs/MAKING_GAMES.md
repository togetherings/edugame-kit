# Making a game

## The game folder

```
my-game/
  edugame.json     what the game is (below): settings, no words
  lang/en.json     every word it shows, one file per language
  lang/fr.json
  index.html       the start page
  game.js          your game
  style.css, icon.svg, pictures, sounds ...
  lessons/ maps/ ...   content, if it has a lot (see LANGUAGES.md)
```

The kit adds a header to the top of the page, with the game's title and an **Options** button
(appearance, language, and options of your own). Don't put the title in your page too. See
[LANGUAGES.md](LANGUAGES.md).

`edugame new my-game --type saved` (or `--type scored`) makes one from a template. The start page
must load the two files the build makes, before your own script:

```html
<script src="edugame-config.js"></script>
<script src="edugame.js"></script>
<script src="game.js"></script>
```

Don't add `edugame.js`, `edugame-config.js`, `kolibri-game.json`, `imsmanifest.xml` or
`rachel-index.php` yourself: the build writes them.

## The rules your game runs under

- **Everything is inside the game.** Kolibri and Kolibri Games block loading files from other
  servers, and the game must work offline. Bundle your libraries, fonts and pictures.
- **Relative paths only:** `game.js` or `img/cat.png`, never `/game.js`.
- **Save with the helper,** not `localStorage` or cookies directly. See [HELPER.md](HELPER.md).
- **Keep saves small:** at most 3,900 characters as JSON, because SCORM 1.2 allows 4,096. Save
  what the learner has done (levels, stars, unlocked words), not the whole game.
- **Keep it light.** Games run on old phones and laptops, often from a Raspberry Pi.

## `edugame.json`

```json
{
  "format": 1,
  "type": "scored",
  "id": "org.example.number-hunt",
  "version": "1.0.0",
  "languages": ["en", "fr"],
  "icon": "icon.svg",
  "color": "#2f6f8f",
  "scoring": {
    "order": "asc",
    "tiebreak": "seconds",
    "counts": "first",
    "min": 1,
    "max": 1000,
    "grade": { "full": 1, "zero": 20 }
  },
  "settings": [
    { "key": "max", "type": "choice", "label": "Numbers to search", "default": 100,
      "choices": [{ "value": 20, "label": "1 to 20" }, { "value": 100, "label": "1 to 100" }] }
  ],
  "authors": ["Your name"],
  "license": "CC-BY-4.0"
}
```

| Field | Required | Meaning |
|---|---|---|
| `format` | yes | Always `1`. |
| `type` | yes | `"saved"` (progress only) or `"scored"` (progress and a score). |
| `id` | yes | Unique, lower-case, never changes: `org.yourschool.my-game`. Platforms use it to know a new version is the same game, and saves are kept under it. |
| `version` | yes | Like `1.0.0`. |
| `languages` | no | The languages the game is translated into, the default first. Default `["en"]`. Each needs `lang/<code>.json`. |
| `entry` | no | The start page. Default `index.html`. |
| `icon`, `color` | no | An icon file (SVG works everywhere) and an accent colour, used by Kolibri Games, RACHEL, Sugarizer and Kiwix. |
| `scoring` | Scored Games | What the scores are and how they compare: see [SCORING.md](SCORING.md). |
| `settings` | no | Options coaches can change on the Kolibri Games games page (the format is in Kolibri Games' [GAME_FORMAT.md](https://github.com/togetherings/kolibri-games/blob/main/docs/GAME_FORMAT.md)). Everywhere else, the game gets the `default` values. |
| `options` | no | The Options button: `{"theme": "auto", "header": true}`. See [LANGUAGES.md](LANGUAGES.md). |
| `exclude` | no | Files in the folder that aren't part of the game, like `["tools/*", "docs/*", "*.md"]`. |
| `content` | no | Folders of content JSON, loaded when needed: `["lessons", "maps"]`. |
| `packages`, `package_files` | no | Several zips from one folder, each with part of the content. |
| `authors`, `license` | no | Shown by platforms that list them. |

The title and description come from the default language's `lang/<code>.json` (`title`,
`description`), so they're translated too.

### `scoring`

One score is short: `{"order": "asc", "tiebreak": "seconds", "counts": "first"}`. Several scores,
each ranked its own way, and levels with a scoreboard each, use `fields`, `rank_by` and `boards`.
See **[SCORING.md](SCORING.md)**.

## Commands

```bash
edugame new my-game --type scored [--id org.example.my-game] [--title "My game"]
edugame check my-game         # problems, and words a language is missing
edugame preview my-game       # the test page; reload it after you change the game
edugame build my-game         # dist/<name>-<version>.zip (one for each package)
edugame build my-game --package lesson-01 --lang fr --each-language
edugame build my-game --sugarizer [--sugar-lib path/to/lib] --zim
edugame translate my-game sw  # add Kiswahili: copies the English words to translate
edugame pages my-game -o site # a GitHub Pages site (see platforms/GITHUB_PAGES.md)
```

### The test page

`edugame preview` opens the game inside a test page. Choose how to play it:

- **As a learning system:** the page pretends to be Kolibri Learn or Moodle (SCORM 1.2) and shows
  what the game saves, how big the save is, and the status and grade it reports.
- **As a website:** like RACHEL or Kiwix; saves stay in the browser.

You can also switch the language, reload the game to check it carries on where it left off, and
delete the save to start again. To try a game on the Kolibri Games games page, build it, unzip it
into a folder and run `kolibri-games-preview <that folder's parent>` (from kolibri-games).

## Making an existing game a kit game

1. Add `edugame.json` and `lang/en.json` (at least a `title`). Move every word the game shows
   into `lang/`, and big content into its own folders (see [LANGUAGES.md](LANGUAGES.md)).
2. Load `edugame-config.js` and `edugame.js` before your script. Take out your own title and any
   settings page: the kit's header and Options panel do that.
3. Replace your own saving with `EduGame.save()` and read it back from `EduGame.ready()`.
4. For a Scored Game, call `EduGame.start()` when a round begins and `EduGame.finish(score)` when
   it ends.
5. Run `edugame check` and `edugame preview`.
