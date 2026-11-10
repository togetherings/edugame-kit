# Keeping games up to date with the kit

A game's GitHub workflows don't hold the kit's steps themselves: they call the kit's own
workflows, at a kit release. `edugame new --github` and the template repository set this up:

```yaml
# .github/workflows/build.yml
jobs:
  kit:
    uses: togetherings/edugame-kit/.github/workflows/game.yml@v0.3.0
```

`game.yml` checks the game, builds the zips and plays the game in a real Kolibri
(`edugame kolibri-test`); `game-pages.yml` publishes it to GitHub Pages. They install the kit
of the same release, so `@v0.3.0` means kit 0.3.0 throughout: the save helper in the zips, the
build, the checks.

## When the kit has a new release

Each game has `.github/dependabot.yml`. Within a day of a kit release, Dependabot opens a pull
request in the game called something like "Bump togetherings/edugame-kit/.github/workflows/game.yml
from 0.3.0 to 0.3.1", with the kit's release notes in it. (To have it look now: the game's
**Insights > Dependency graph > Dependabot > Check for updates**.)

1. The game's checks run on the pull request with the new kit: its own tests, `edugame check`,
   the build, and playing it in a real Kolibri.
2. Read the release notes' **What games need to do**. Usually nothing: fixes in the save helper
   reach the game through its next build. When a game must change its own code (say, a new
   way to save), make that change on the same pull request, or on another one.
3. When **Checks passed** passes, merge it. The next release of the game has the new kit.

Dependabot also keeps the GitHub actions (checkout, setup-python ...) up to date, in one pull
request for all of them.

To be told about every kit release yourself, choose **Watch > Custom > Releases** on the kit's
GitHub page.

## Moving a game made before 0.3.0

Games made before 0.3.0 have the kit's steps in their own `build.yml` and `pages.yml`, with
`KIT_VERSION: main`. Once, by hand (or ask for a pull request):

1. Replace `.github/workflows/build.yml` and `pages.yml` with the starter's
   ([`edugame/templates/github/`](../edugame/templates/github/)). Keep anything the game added:
   its own tests go in `with: tests: ...` (like `tests: node tests/run-tests.js`); other jobs stay
   as jobs of their own, listed in **Checks passed**'s `needs`.
2. Add [`dependabot.yml`](../edugame/templates/github/dependabot.yml) as `.github/dependabot.yml`.
3. Add `tests/kolibri_play.py` (see [platforms/KOLIBRI.md](platforms/KOLIBRI.md)) so the
   real-Kolibri test checks saving, or `kolibri: false` to skip it.

The check jobs are then called **Kit / Build** and **Kit / Real Kolibri**; **Checks passed** keeps
its name, so the "Protect main" ruleset doesn't change.

## Releasing the kit

1. `python tools/bump_version.py 0.3.1` (it changes `__version__`, the workflows' `KIT_REF` and the
   starter's `@v...`), and add `## 0.3.1` to CHANGELOG.md with a **What games need to do** part.
2. Merge that, then publish a release on GitHub with the tag `v0.3.1`. The Release workflow
   attaches the files and the notes; the Template repository workflow updates edugame-template;
   Dependabot opens pull requests in the games.

Between merging and publishing, the starter names a release that doesn't exist yet, so publish
soon after merging.
