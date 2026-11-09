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
front page lists them, each with its own Play button.

The kit publishes one of its own examples this way: Number Hunt, at
`https://togetherings.github.io/edugame-kit/` (see `.github/workflows/pages.yml`).

## Setting it up for a game's repository

1. Make the repository with the game folder at its top (`edugame.json`, `index.html`, `lang/` ...).
   The quickest way is **Use this template** on
   [edugame-template](https://github.com/togetherings/edugame-template), which has everything already.
   `edugame new my-game --github` adds the workflow for you, as `.github/workflows/pages.yml` (with
   `build.yml`, which builds the zips).
   For a game made earlier, copy
   [`edugame/templates/github/pages.yml`](../../edugame/templates/github/pages.yml) there.
2. Push it to GitHub. Free GitHub Pages need a public repository.
3. In the repository, open **Settings > Pages**, and under **Build and deployment** set
   **Source** to **GitHub Actions**.
4. Push to `main` (or run the workflow from the **Actions** tab). The site appears at
   `https://<your account>.github.io/<repository>/`.

The `.github` folder is never put in the game's zips.

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

- **Page views:** the front page (`/my-game/`) and the game (`/my-game/play/`).
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
