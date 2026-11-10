# Kolibri

Saved and Scored Games reach Kolibri through **Kolibri Studio**, as HTML5 apps in a channel.

## In a channel (Learn)

The zip is an ordinary Kolibri **HTML5 app**. Learners open it from **Learn**, and coaches can put
it in lessons and assign it to classes, like any other resource.

1. In [Kolibri Studio](https://studio.learningequality.org/), open your channel and choose
   **Add > Upload files**, then choose the game's zip (`dist/<name>-<version>.zip`).
2. Fill in the title, language, license and so on, and publish the channel.
3. On the Kolibri device, import the channel (or update it) as usual.

Kolibri gives the game a SCORM connection, so the helper saves each learner's progress in their
Kolibri account. Kolibri syncs it between servers, so learners can carry on from another device
that syncs with this one. When the game calls `EduGame.complete()`, or a Scored Game finishes a
passed round, Kolibri shows the resource as done.

**Save as the learner plays.** When a learner goes back to the channel, Kolibri sends what it has
and stops listening before it closes the game's page, so a save made as the page closes never
arrives. Save after every step that matters (the starters do), or every few seconds while something
changes. See "Saving as the page closes" in [HELPER.md](../HELPER.md).

**Scoreboards:** with [Kolibri Games](https://github.com/togetherings/kolibri-games) 0.2 or later
on the device, Scored Games in channels appear on its games page under **Scored Games in Learn**,
with scoreboards made from the scores they save: one for each level or lesson, and one for the
whole game if `scoring.boards.total` asks for it. Coaches choose what learners see (names,
initials or only their own result) and can download them. Nothing else is needed: the zip already
has the `kolibri-game.json` that tells Kolibri Games how to read them. Saved Games aren't listed
there; they're just played in Learn.

## Scores in Kolibri

The helper never sends Kolibri a score: Kolibri reads a SCORM score as how much of a resource is
done, so a resource would only count as done at 100. It sets the status instead: `incomplete`
when the game opens, and `passed` after `EduGame.complete()` or a passed round. Scoreboards come
from Kolibri Games, above.

(Kolibri Games can also install a zip on its games page, which is handy for trying a game with
coaches' challenges. Studio is the way to give games to learners.)

## Trying it

`edugame preview` plays the game as a learning system, which is how Kolibri Learn runs it. To try
the games page, unzip the built zip into a folder (say `games/my-game`) and run
`kolibri-games-preview games` from kolibri-games.

## Testing in a real Kolibri

`edugame kolibri-test` plays the game in a real Kolibri, the way a learner gets it from a
channel. It needs Kolibri and Playwright (on Linux or macOS; the starter's Build workflow runs it
on GitHub for every push, in a job called **Real Kolibri**):

```bash
pip install kolibri playwright && python -m playwright install chromium
edugame kolibri-test my-game
```

It sets up a throwaway Kolibri in a temporary folder (it never touches a Kolibri you use), adds
the game's zip to a channel as an HTML5 app, signs in as a learner and opens the game in Learn.
Then it checks that:

1. the game opens, and the save helper finds Kolibri's SCORM connection;
2. after the learner leaves, Kolibri kept the save: it fits SCORM 1.2's 4096 characters, the status
   is `incomplete` or `passed`, no score was sent, and the resource counts as done if it should;
3. when the learner comes back, the game gets back exactly that save, with no errors on the page.

Screenshots go in `kolibri-screenshots/`.

The test leaves straight after the first visit's play steps, the way a learner goes back to the
channel. Kolibri drops a save made as the learner leaves (see "Saving as the page closes" in
[HELPER.md](../HELPER.md)), so if the game only saves then, the second visit shows it.

**Play steps.** Kolibri only keeps a save once the game makes one, so tell the test how to play:
`tests/kolibri_play.py` in the game's folder (never put in the zip; the starters have one).

```python
def first_visit(game):          # play a little, so the game saves
    game.click("#start")
    game.data["level"] = game.text("#level")
    game.expect_complete = True        # this visit finishes the game: check Kolibri counts it as done

def came_back(game):            # check the game carried on where the learner left off
    game.check(game.text("#level") == game.data["level"], "came back to the same level")
```

`game` has `click(selector)`, `fill(selector, text)`, `text(selector)`, `press(*keys)`,
`hold(key, ms)`, `js(expression)`, `wait_for(expression)`, `check(condition, what)`, `shot(name)`,
`page` and `frame` (Playwright, for anything else), and `data`, which is kept from the first visit
to the second. For a game drawn on a canvas, click it first so it gets the keys
(`game.click("canvas")`), then `press` and `hold` keys. `edugame kolibri-test my-game --play other.py`
uses another file.
