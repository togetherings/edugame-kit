"""
Play steps for `edugame kolibri-test`: how a learner plays this game, so the test can check
that Kolibri keeps their progress. (This file is never put in the game's zip.)

`game` can: click(selector), fill(selector, text), text(selector), press(*keys),
hold(key, ms), js(expression), wait_for(expression), check(condition, what), shot(name).
game.data is kept from the first visit to the second. Set game.expect_complete = True when
the first visit should finish the game, to check Kolibri counts it as done.
"""
import re


def first_visit(game):
    # Answer every sum right: five levels, then the game calls EduGame.complete().
    game.check(game.wait_for("document.querySelectorAll('#answers button').length > 0"), "the first sum is showing")
    for _ in range(5):
        a, b = map(int, re.findall(r"\d+", game.text("#question"))[-2:])     # "What is a + b?"
        game.click("#answers button:text-is('%d')" % (a + b))
        game.page.wait_for_timeout(300)
    game.data["level"] = game.text("#level")
    game.check(game.wait_for("document.querySelectorAll('#answers button').length === 0"), "every level is done")
    game.expect_complete = True


def came_back(game):
    # The learner carries on where they were: every level done.
    game.wait_for("document.getElementById('level').textContent !== ''")
    game.check(game.text("#level") == game.data["level"], "came back to: %s" % game.text("#level"))
