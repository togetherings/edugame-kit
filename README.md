# EduGame Kit

Make a learning game once, and play it in **Kolibri**, **Moodle** (and other learning systems),
**RACHEL**, **Sugarizer** and **Kiwix**, with each learner's progress saved wherever they play.

A game is a folder of ordinary web files (HTML, JavaScript, CSS, pictures) plus a small
`edugame.json`. The kit gives it:

- **A save helper**, `edugame.js`, that finds out where the game is running and saves the
  learner's progress the best way there: in their Kolibri or Moodle account, in Sugarizer's
  Journal, or in the browser.
- **A build tool**, `edugame`, that makes **one zip that works everywhere**: a Kolibri HTML5 app
  (with Kolibri Games scoreboards), a SCORM 1.2 package for Moodle and other learning systems, and
  (unzipped) a RACHEL module. It can also make a Sugarizer activity and a ZIM file for Kiwix.
- **Translations** from the start: put each language's words in `lang/<code>.json`.
- **A test page** that plays your game as a learning system or a website and shows what it saves.

Two kinds of game can be made with the kit:

| Kind | What it keeps | Examples |
|---|---|---|
| **Saved Games** (`"type": "saved"`) | The learner's progress, like their level | Story paths, practice levels, puzzles |
| **Scored Games** (`"type": "scored"`) | Progress and scores: one score or several (like accuracy and speed), each ranked its own way, with or without a time, for the whole game or for each level | [Number Hunt](examples/number-hunt), [Memory Match](examples/memory-match) |

Scored Games get scoreboards in [Kolibri Games](https://github.com/togetherings/kolibri-games)
(one for each level, and one for the whole game), and grades in Moodle's gradebook. Kolibri
itself gets no score: it would read one as how much of a resource is done.

*Server Games*, the third kind in Kolibri Games, need that plugin's server to run their rules
(like [Wiki BLAZE](https://github.com/togetherings/kolibri-games) and
[BeaconHunt](https://github.com/togetherings/beacon-hunt)), so they aren't made with this kit.

## Start

**Without installing anything:** open [edugame-template](https://github.com/togetherings/edugame-template) and click
**Use this template**. You change the game in GitHub's editor, and GitHub checks it, builds the zips and publishes
its web page for you.

**On your own computer:** you need Python 3.8 or later. Nothing else.

```bash
pip install git+https://github.com/togetherings/edugame-kit
edugame new my-game --type scored    # or --type saved; add --github for the GitHub workflows
edugame preview my-game              # play it in the test page
edugame build my-game                # dist/my-game-0.1.0.zip
edugame build my-game --all          # also the Sugarizer activity and, with libzim, the ZIM file
edugame pages my-game -o site        # a GitHub Pages site for the game
edugame kolibri-test my-game         # play it in a real Kolibri (needs kolibri and playwright)
```

Change the `id` in `my-game/edugame.json` to one of your own (like `org.yourschool.my-game`),
write your game in `game.js`, and put its words in `lang/en.json`. See
**[docs/MAKING_GAMES.md](docs/MAKING_GAMES.md)**.

## Putting a game on each platform

| Platform | Use | Saves go to | Guide |
|---|---|---|---|
| Kolibri, through Kolibri Studio (Learn) | the zip, as an HTML5 app in a channel | the learner's account; synced between Kolibri servers; scoreboards in Kolibri Games | [KOLIBRI.md](docs/platforms/KOLIBRI.md) |
| Moodle | the zip, as a SCORM package | the learner's attempt; scores go to the gradebook | [MOODLE.md](docs/platforms/MOODLE.md) |
| Other learning systems | the zip, as a SCORM 1.2 package | the learner's record | [OTHER_LMS.md](docs/platforms/OTHER_LMS.md) |
| RACHEL and OER2Go | the zip, unzipped into the modules folder | the browser | [RACHEL.md](docs/platforms/RACHEL.md) |
| Sugarizer | `*-sugarizer.zip` | the Journal (with sugar-web) or the browser | [SUGARIZER.md](docs/platforms/SUGARIZER.md) |
| Kiwix | `*.zim` | the browser or the Kiwix app | [KIWIX.md](docs/platforms/KIWIX.md) |
| GitHub Pages | `edugame pages`: a front page and the game, with visits counted by GoatCounter if you like | the browser | [GITHUB_PAGES.md](docs/platforms/GITHUB_PAGES.md) |

Canvas, and learning systems without SCORM, will be able to use the games through LTI 1.3. That's
planned: see [docs/LTI.md](docs/LTI.md).

## More

- [docs/MAKING_GAMES.md](docs/MAKING_GAMES.md): the game folder, `edugame.json` and the commands
- [docs/SCORING.md](docs/SCORING.md): scores, levels and which round counts
- [docs/HELPER.md](docs/HELPER.md): the save helper's calls, and what it saves where
- [docs/UPDATING.md](docs/UPDATING.md): how games get new kit releases (Dependabot pull requests)
- [docs/LANGUAGES.md](docs/LANGUAGES.md): words, languages, the Options button, content and packages
- [CHANGELOG.md](CHANGELOG.md)

## Development

```bash
pip install -e . pytest playwright && playwright install chromium
python -m pytest                 # unit tests
python -m tests.e2e_browser      # plays the examples in Chromium
```

Install [kolibri-games](https://github.com/togetherings/kolibri-games) as well to also test the
games on its games page and check the zips with its own checks.

The template repository, [edugame-template](https://github.com/togetherings/edugame-template), is made from the
saved starter by `tools/make_template_repo.py`. The `Template repository` workflow pushes it there whenever the
starter changes on `main`, using a deploy key kept as the secret `TEMPLATE_DEPLOY_KEY`. Change the starter here,
never in the template repository.

## License

MIT. See [LICENSE](LICENSE). Games you make with the kit can use any license.
