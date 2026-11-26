# GitHub Pages

A game can have its own web page on GitHub Pages, where anyone can read about it, play it in the
browser, and download it for their school. `edugame pages` builds the site:

```bash
edugame pages my-game -o site --repo your-name/my-game
```

```
site/
  index.html   the front page: title, description, Play, the languages, where to get the game
  play/        the game itself (saves stay in the visitor's browser)
```

A game with `packages` in its `edugame.json` gets each package at `play/<package id>/`, and the
front page lists them, each with its own Play button. A game with packages can have a menu page of
its own instead: see [A site with a menu](#a-site-with-a-menu-games-with-packages).

The kit publishes one of its own examples this way: Number Hunt, at
`https://togetherings.github.io/edugame-kit/` (see `.github/workflows/pages.yml`, which calls
`game-pages.yml` as games do).

## Setting it up for a game's repository

1. Make the repository with the game folder at its top (`edugame.json`, `index.html`, `lang/` ...).
   The quickest way is **Use this template** on
   [edugame-template](https://github.com/togetherings/edugame-template), which has everything already.
   `edugame new my-game --github` adds the workflow for you, as `.github/workflows/pages.yml` (with
   `build.yml`, which builds the zips).
   For a game made earlier, copy
   [`edugame/templates/github/pages.yml`](../../edugame/templates/github/pages.yml) there (see
   [UPDATING.md](../UPDATING.md)). It calls the kit's `game-pages.yml` at a kit release, which
   Dependabot keeps up to date.
2. Push it to GitHub. Free GitHub Pages need a public repository.
3. In the repository, open **Settings > Pages**, and under **Build and deployment** set
   **Source** to **GitHub Actions**.
4. Push to `main` (or run the workflow from the **Actions** tab). The site appears at
   `https://<your account>.github.io/<repository>/`.

The `.github` folder is never put in the game's zips.

To keep `main` safe, import the ruleset [`docs/rulesets/protect-main.json`](../rulesets/README.md): changes then
reach `main` through pull requests, and only when the Build workflow's **Checks passed** job passes.

## A site with a menu (games with packages)

A game made of packages (LIT's lessons, SINGE's maps) can have its own menu page, in the game's
own look, and a site where **each package in each language has its own address**:

```
site/
  index.html            goes to the menu in the visitor's language
  en/                   the menu in English
  en/lesson-03/         lesson 3 in English
  en-gb/lesson-03/      lesson 3 in British English
  fr/                   the menu in French (only the packages that are in French)
  play/lesson-03/       an address from before the menu: goes to the new one
```

The language's part of an address is its code in lower case (`en-GB` is `en-gb`). The bare address
goes to the menu in the language chosen last on the site, then `?lang=`, then the browser's
languages, then the game's default. All the pages share one save, since they're one website.

Add the menu page to the game, and name it in `edugame.json`:

```json
"pages": { "menu": { "page": "menu.html", "files": ["js/menu.js"], "offline": "all-lessons" } }
```

- `page`: the menu page, at the top of the game folder. Like the start page, it loads
  `edugame-config.js` and `edugame.js`.
- `files`: files only the menu uses. They, and the menu page, are never in a zip.
- `offline` (optional): the name of the offline copy below (`<game>-all-lessons-<version>.zip`;
  `all` if left out).

On every page of the site, `EduGame.site()` says where the others are (it's `null` in a zip):

```js
{
  language: "en", package: "lesson-03",       // this page (package is null on the menu)
  home: "../../en/",                          // this language's menu
  next: "../../en/lesson-04/",                // the next package in this language, or null
  languages: [{code: "fr", name: "Français", url: "../../fr/", packages: 1}, ...],
  packages: [{id: "lesson-01", title: "...", description: "...", url: "../../en/lesson-01/",
              config: {lesson: "01"}}, ...]   // the packages in this language, in order
}
```

The menu page lists `site.packages` and opens one with `EduGame.goTo(p.url)` (or a link). The
results of every package are in `EduGame.ready()`'s `results`, one board each, as the game names
them. The helper also:

- adds a link back to the menu at the start of the header on a package's page. Its word is
  `kit.menu` ("Menu"): a game can say "Lessons" instead in its `lang/` files.
- makes Options' language go to the same package in that language, or to that language's menu
  if the package isn't in it.
- gives each page its own title in the browser's tab: the package's title (or the game's, on the menu).

### The offline copy

Pages opened from a folder (`file://`) can't share a save in every browser (Firefox keeps one for
each file), so the offline copy is one page: `index.html` shows the menu at `#en` and a package at
`#en/lesson-03`, with every package's files in one folder. `edugame bundle` makes it with the
bundles, so `release-bundles: true` attaches it to releases. `site.home`, `site.next` and the
languages' `url`s are then `#` addresses, and `EduGame.goTo()` loads them.

## Counting visits with GoatCounter

[GoatCounter](https://www.goatcounter.com/) counts visits without cookies and without collecting
personal data, so visitors don't need to accept anything. It has a free plan; check its site for
the current terms.

**Counting is only added to the GitHub Pages site.** The zips for Kolibri, Moodle and other
learning systems, RACHEL, Sugarizer and Kiwix never contain it: `edugame build` doesn't know about
it, and a test checks.

### Once, for your GitHub account

1. Sign up at [goatcounter.com](https://www.goatcounter.com/) and choose a **code**, for example
   `togetherings`. Your counts are then at `https://togetherings.goatcounter.com`.
2. That's all the account needs. Every GitHub Pages site of an account has the same address,
   `https://<account>.github.io/`, with each repository in its own folder
   (`/edugame-kit/`, `/lit/`, `/sparkle/` ...). GoatCounter shows each page's path, so **one code
   counts every repository's site**, and you can tell them apart by the first part of the path.
   (A repository with its own domain would need its own GoatCounter site, made from the same login.)

### For each repository

1. Open **Settings > Secrets and variables > Actions**, choose the **Variables** tab, and click
   **New repository variable**.
2. Name: `GOATCOUNTER_CODE`. Value: your code, like `togetherings`. (It isn't a secret: it ends up
   in the page anyway.)
3. Run the workflow again. The front page's footer then says visits are counted.

Personal GitHub accounts have no account-wide variables, so each repository needs its own. (An
organization can set it once, as an organization variable.) Instead of the variable, you can also
write the code into `edugame.json`, which only `edugame pages` reads:

```json
"pages": { "goatcounter": "togetherings" }
```

or pass `--goatcounter togetherings` to `edugame pages`.

### What's counted

- **Page views:** the front page (`/my-game/`) and the game (`/my-game/play/`); on a site with a
  menu, each menu and package page (`/my-game/en/`, `/my-game/en/lesson-03/`), but not the bare
  address, which only goes to a menu.
- **Rounds**, as events: the save helper announces when a round starts and finishes, and the
  site counts `round-started` and `round-finished` under the game's path. Use `--no-events` to
  count page views only.

### Sites not made with the kit

Any GitHub Pages site of the account can be counted with the same code: put this in each page's
`<head>`:

```html
<script data-goatcounter="https://togetherings.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
```

For a site that's also packed into zips for Kolibri or another platform (like the Lessons In
Typing site), add it only in the step that builds the site, never in the zips: those run offline,
and they shouldn't report anything outside the school.
