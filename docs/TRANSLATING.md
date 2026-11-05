# Translating a game

Every game's words are in `lang/<code>.json`, one file per language, with the same keys:

```json
{
  "title": "Number Hunt",
  "description": "Find the secret number in as few guesses as you can.",
  "score_label": "Guesses",
  "too_low": "{n} is too low. My number is higher."
}
```

- `title` and `description` name the game on every platform.
- `score_label` and `score_unit` (Scored Games) name the score on scoreboards.
- Your game's own words can use `{names}` for values: `EduGame.t("too_low", { n: 42 })`.

## Adding a language

```bash
edugame translate my-game sw
```

This adds `sw` to `languages` in `edugame.json` and makes `lang/sw.json` with the default
language's words, ready to translate. Run it again later to add words the language is missing.
`edugame check` lists them too.

Use codes like `fr`, `sw`, `pt-BR` or `zh-Hans`. The first language in `languages` is the default:
it's used for words a translation doesn't have.

## Which language a learner sees

The helper picks the first of these that the game has:

1. `?lang=fr` in the game's address
2. the platform's language, where it says (Sugarizer, and SCORM systems that fill in
   `cmi.student_preference.language`)
3. the browser's languages
4. the game's default language

For Arabic, Persian, Pashto, Hebrew, Urdu and other right-to-left languages, it sets
`dir="rtl"` on the page. Use CSS that works both ways (`margin-inline-start` rather than
`margin-left`).

## In HTML and code

```html
<button data-t="start">Start</button>
<ol data-t-attr="aria-label:your_guesses"></ol>
```

```js
el.textContent = EduGame.t("summary", { guesses: 7, time: "0:41" });
```

Keep whole sentences in one string, with `{names}` for the values, so translators can change the
word order.
