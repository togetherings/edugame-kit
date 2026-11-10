# Languages, options and content

A game has three kinds of material, and each lives in its own place:

| Kind | Where | What it is |
|---|---|---|
| **Words** | `lang/<code>.json`, one file per language | every word the game shows: buttons, messages, help, the title, the names of levels |
| **Content** | folders listed under `content` in `edugame.json` | the big things the game plays with: maps, lessons, word lists, keyboards. Each folder keeps its data and its languages side by side |
| **Settings** | `edugame.json` (and any `config.js` of the game's own) | what the game is and how it scores. No words |

## Words: `lang/<code>.json`

```json
{
  "_language": { "name": "Français", "dir": "ltr" },
  "_notes": { "menu.goal": "On a mode button, under its name. Keep it short." },
  "title": "Chasse au nombre",
  "description": "Trouve le nombre secret en le moins de coups possible.",
  "too_low": "{n} est trop petit. Mon nombre est plus grand.",
  "guesses": { "one": "{n} coup", "other": "{n} coups" },
  "help.intro": ["Je pense à un nombre.", "À chaque essai, je te dis s'il est plus grand ou plus petit."]
}
```

- **A value** is text, a list of paragraphs, or a plural set. Plural sets use the forms of the
  [Unicode plural rules](https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html)
  (`zero`, `one`, `two`, `few`, `many`, `other`); `other` is always needed. The helper picks the
  form for `{n}` (or `{count}`).
- **`_language`** names the language in itself (`Français`, `Español`, `العربية`), for the
  language list in Options, and says which way it's written (`ltr` or `rtl`).
- **`_notes`** helps translators: where a word is shown, how long it can be. Put it in the default
  language's file. JSON has no comments, so notes go here.
- Other keys starting with `_` are the game's own and are never shown.
- **Keys with a set meaning:** `title` and `description` name the game on every platform;
  `score_label`, `score_unit` and the other scoring labels name scores on scoreboards
  ([SCORING.md](SCORING.md)). Words starting with `kit.` are the kit's own (the Options panel): the
  helper has them in English, French, Spanish and Portuguese, and a game's file can
  change them or add another language's.
- Group keys with dots, like `menu.goal` and `help.intro`.
- Keep whole sentences in one value, with `{names}` for values, so translators can change the word
  order.

### Language codes

Use codes like `en`, `fr`, `pt-BR`, `es-419` (Latin American Spanish) or `zh-Hans`, in file
names and in `languages` in `edugame.json`. The first language in `languages` is the default.

A **regional language** only needs the words that differ. With `"languages": ["en", "en-GB"]`,
`lang/en-GB.json` might hold just `{"_language": {"name": "English (UK)"}, "color": "colour"}`; the
rest comes from `lang/en.json`. A word missing in any language comes from the default language.

### Adding a language

```bash
edugame translate my-game es
```

This adds `es` to `languages` and makes `lang/es.json` with the default language's words to
translate. Write the language's own name in `_language`. Run it again later to add words the
language is missing. `edugame check` lists missing words, and also words the game's code or pages
use (`EduGame.t("key")`, `data-t="key"`) that the default language doesn't have.

### In HTML and code

```html
<button data-t="start">Start</button>
<ol data-t-attr="aria-label:your_guesses"></ol>
```

```js
el.textContent = EduGame.t("summary", { guesses: 7, time: "0:41" });
EduGame.t("guesses", { n: 7 });     // "7 guesses" (the plural set's "other")
EduGame.lines("help.intro");         // ["...", "..."]: one paragraph each
EduGame.number(1234.5, 1);           // "1,234.5" or "1 234,5", as the language writes it
```

`data-t` elements are filled again whenever the language changes. Text your code makes needs
making again: listen for the change.

```js
EduGame.on("languagechange", function (e) { showIntro(); });   // e.language: "fr"
```

## Which language a learner sees

The helper picks the first of these that the game has:

1. **The learner's own choice**, made in Options. It's kept in the learner's save, so it follows
   them where the platform keeps saves with the learner (Kolibri, learning systems, the Kolibri
   Games games page).
2. `?lang=fr` in the game's address.
3. **The platform's language:** Kolibri's language on the Kolibri Games games page, Sugarizer's,
   or `cmi.student_preference.language` from a learning system.
4. The browser's languages.
5. The game's default language.

`fr-CA` matches `fr-CA`, then `fr`, then any other `fr-` language. For Arabic, Persian, Pashto,
Hebrew, Urdu and other right-to-left languages, the page gets `dir="rtl"`. Use CSS that works both
ways (`margin-inline-start` rather than `margin-left`).

## Options

The helper puts a header at the top of the page: the game's title, and an **Options** button beside
it. On the Kolibri Games games page, which shows the title already, the header has only the button.
Don't put the title in your page as well.

The button opens a panel over the game, with:

- **Appearance:** Light, Dark, or Auto (follow the device). The page gets `data-theme="light"` or
  `"dark"` on `<html>`, so style both with CSS variables:
  ```css
  :root { --bg: #fff; --text: #111; }
  :root[data-theme=dark] { --bg: #111; --text: #eee; }
  ```
  The theme is kept on this device, not with the learner.
- **Language:** each of the game's languages, in its own name. It changes when the learner chooses
  **Apply**.
- **The game's own options**, added with `EduGame.addOption()`:
  ```js
  EduGame.addOption({
    key: "skin", label: "option.skin", "default": "medium",
    choices: [{ value: "light", label: "skin.light", color: "#f3d2b9" }, { value: "medium", label: "skin.medium" }],
    keep: "learner"          // in the learner's save; "device" (the default): on this device
  });
  // (a choice's color, if it has one, shows as a dot beside its name)
  EduGame.option("skin");                                   // the chosen value
  EduGame.on("optionchange", function (e) { /* e.key, e.value */ });
  ```

Appearance and the game's options show straight away while the panel is open, so the learner can
see them. **Back** (or Escape) puts back what was there before.

In `edugame.json`:

```json
"options": { "theme": "auto", "header": true }
```

`theme` is the starting theme. With `"header": false` the kit adds no header: put
`data-edugame-options` on your own button, or call `EduGame.openOptions()`.

## Content

Content is too big to load all at once, or there's a lot of it: maps, lessons, word lists. List its
folders in `edugame.json`:

```json
"content": ["lessons", "keyboards"]
```

The build turns each `.json` file in them into a small script (`file.json.js`), so the game can load
it when it's needed, even when it's opened straight from a folder (where browsers block reading
JSON files):

```js
EduGame.load("keyboards/azerty.json").then(function (keyboard) { ... });   // null if it isn't there
```

A content folder keeps its data and its languages side by side. There are two ways to translate
content:

- **A translation** changes the words and keeps the rest. Put the words in a `lang/` folder next to
  the data, and load it with `loadLanguage`: the current language's file is laid over the default
  language's, so a translation only needs the words.
  ```
  maps/us/shapes.js         the data
  maps/us/lang/en.json      {"name": "United States", "regions": {"CA": "California", ...}}
  maps/us/lang/fr.json      {"name": "États-Unis", "regions": {"CA": "Californie", ...}}
  ```
  ```js
  EduGame.loadLanguage("maps/us/lang").then(function (words) { ... });
  ```
- **An edition** is complete in itself, made for one language: a typing lesson in French uses
  French words and a French keyboard, not a translation of the English lesson. Load the nearest
  language's file with `merge: false` (`fr-CA`, then `fr`, then the default):
  ```
  lessons/01/en.json        the English lesson
  lessons/01/fr.json        the French lesson
  ```
  ```js
  EduGame.loadLanguage("lessons/01", { merge: false }).then(function (lesson) { ... });
  ```

## Packages: several zips from one folder

A game with a lot of content can be built as several zips, each with part of it (a zip per lesson,
or per set of maps), so schools can choose what to put on their devices:

```json
"package_files": ["lessons/*"],
"packages": [
  { "id": "lesson-01", "title": "package.lesson_01", "description": "package.lesson_01_about",
    "files": ["lessons/01/*"], "config": { "lesson": "01" } },
  { "id": "french", "title": "package.french", "files": ["lessons/*/fr.json"], "languages": ["fr"] }
]
```

- `package_files`: files that are only in the packages that list them. Every other file is in
  every package.
- `files`: the package's own files. `exclude`: files to leave out of it.
- `title` and `description` are words in `lang/`, so they're translated; they name the package's
  zip on every platform.
- `languages`: the package's languages (the first is its default). Without it, all of the game's.
- `config` reaches the game as `EduGame.config.package.config`. `EduGame.config.package.id` says
  which package is playing.

Every package is the same game, with the same `id`, so the Kolibri Games plugin puts their scores
together.

```bash
edugame build my-game                        # dist/my-game-lesson-01-1.0.0.zip, dist/my-game-french-1.0.0.zip
edugame build my-game --package lesson-01
edugame build my-game --lang fr              # only French
edugame build my-game --each-language        # one zip per language: my-game-lesson-01-fr-1.0.0.zip ...
edugame preview my-game --package lesson-01 --lang fr
```

`edugame check` lists each package with its files and languages. `edugame pages` puts each package
on the site, with its own Play button.
