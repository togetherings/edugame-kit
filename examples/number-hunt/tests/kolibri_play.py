"""
Play steps for `edugame kolibri-test` (never put in the game's zip): one round, played
perfectly, then the best is shown when the learner comes back.
"""


def first_visit(game):
    game.click("#btn-start")
    low, high = 1, int(game.text("#end-high"))
    for n in range(1, 20):
        guess = (low + high) // 2
        game.fill("#guess", guess)
        game.click("#btn-guess")
        game.frame.locator("#history li").nth(n - 1).wait_for(state="attached")
        hint = game.frame.locator("#history li").nth(n - 1).get_attribute("class")
        if hint == "correct":
            break
        low, high = (guess + 1, high) if hint == "higher" else (low, guess - 1)
    game.check(game.wait_for("!document.getElementById('done').hidden"), "found the number in %d guesses" % n)
    game.data["guesses"] = n
    game.expect_complete = True       # finishing a round sets the status "passed"


def came_back(game):
    best = "Your best: %d guesses." % game.data["guesses"]
    game.check(game.wait_for("document.getElementById('intro-rule').textContent.indexOf(%r) >= 0" % best),
               "came back to: %s" % best)
