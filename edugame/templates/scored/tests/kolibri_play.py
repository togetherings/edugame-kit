"""
Play steps for `edugame kolibri-test`: how a learner plays this game, so the test can check
that Kolibri keeps their best score. (This file is never put in the game's zip.)

`game` can: click(selector), fill(selector, text), text(selector), press(*keys),
hold(key, ms), js(expression), wait_for(expression), check(condition, what), shot(name).
game.data is kept from the first visit to the second. Set game.expect_complete = True when
the first visit should finish the game, to check Kolibri counts it as done.
"""
import re


def first_visit(game):
    # One round of ten sums, all right.
    game.click("#start")
    game.check(game.wait_for("!document.getElementById('play').hidden"), "the round started")
    for _ in range(10):
        a, b = map(int, re.findall(r"\d+", game.text("#question"))[-2:])    # "3 of 10: what is a + b?"
        game.fill("#answer", a + b)
        game.press("Enter")
        game.page.wait_for_timeout(200)
    game.check(game.wait_for("!document.getElementById('done').hidden"), "the round finished")
    game.data["best"] = game.text("#best")
    game.check("10" in game.data["best"], "the best score is 10: %s" % game.data["best"])
    game.expect_complete = True       # finishing a round sets the status "passed"


def came_back(game):
    # The learner's best score was kept.
    game.wait_for("document.getElementById('best').textContent !== ''")
    game.check(game.text("#best") == game.data["best"], "came back with: %s" % game.text("#best"))
