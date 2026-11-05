"""
Plays the example games in Chromium, the way each platform runs them:

* in the test page as a learning system (SCORM 1.2, like Kolibri Learn and Moodle)
* in the test page as a website (RACHEL, Kiwix: saves in the browser)
* in French, with ?lang=fr
* on the Kolibri Games games page (when kolibri-games is installed)

    python -m tests.e2e_browser [--screenshots DIR]

Needs Playwright (pip install playwright; playwright install chromium).
"""
import argparse
import json
import os
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

from edugame import build, cli, project as projects
from tests.helpers import EXAMPLES, TEMPLATES

NUMBER_HUNT = os.path.join(EXAMPLES, "number-hunt")
SAVED = os.path.join(TEMPLATES, "saved")


def serve(folder):
    server = cli.make_preview_server(folder, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d/" % server.server_address[1]


def binary_search(frame):
    """Plays Number Hunt perfectly; returns the number of guesses."""
    low, high = 1, int(frame.locator("#end-high").inner_text())
    for n in range(1, 20):
        guess = (low + high) // 2
        frame.locator("#guess").fill(str(guess))
        frame.locator("#btn-guess").click()
        frame.locator("#history li").nth(n - 1).wait_for(state="attached")
        hint = frame.locator("#history li").nth(n - 1).get_attribute("class")
        if hint == "correct":
            return n
        if hint == "higher":
            low = guess + 1
        else:
            high = guess - 1
    raise AssertionError("Number Hunt didn't end")


def test_page(page, base, mode, lang=None):
    page.goto(base)
    page.locator("#game").wait_for()
    page.select_option("#mode", mode)
    if lang:
        page.select_option("#lang", lang)
    return page.frame_locator("#game")


def cmi(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('edugame-test-scorm:org.togetherings.number-hunt') || '{}')")


def check_scorm(page, base, shots):
    frame = test_page(page, base, "scorm")
    frame.locator("#btn-start").click()
    guesses = binary_search(frame)
    frame.locator("#done:not([hidden])").wait_for()
    assert "That's your best yet." in frame.locator("#done-standing").inner_text()
    assert frame.locator("#btn-exit").is_hidden(), "no way back in a learning system"
    saved = cmi(page)
    record = json.loads(saved["cmi.suspend_data"])
    assert record["_v"] == 1 and record["main"][0] == guesses and record["main"][2] == 1, record
    assert saved["cmi.core.lesson_status"] == "completed", saved
    assert saved["cmi.core.score.raw"] == str(round((20 - guesses) / 19 * 100)), saved  # grade: 1 guess = 100%, 20 = 0%
    if shots:
        page.screenshot(path=os.path.join(shots, "1-scorm.png"), full_page=True)
    # The learning system keeps the save, so the best shows next time.
    page.locator("#reload").click()
    page.frame_locator("#game").locator("#intro-rule:has-text('Your best: %d guesses.')" % guesses).wait_for()
    page.locator("#reset").click()
    page.frame_locator("#game").locator("#intro-rule").wait_for()
    assert "Your best" not in page.frame_locator("#game").locator("#intro-rule").inner_text()


def check_french(page, base):
    frame = test_page(page, base, "local", lang="fr")
    frame.locator("h1:has-text('Chasse au nombre')").wait_for()
    assert frame.locator("#btn-start").inner_text() == "Commencer"
    assert frame.locator("html").get_attribute("lang") == "fr"
    assert "Je pense à un nombre de 1 à 100." in frame.locator("#intro-text").inner_text()


def check_local_save(page, base, shots):
    frame = test_page(page, base, "local")
    frame.locator("#question:has-text('What is')").wait_for()
    assert "this browser" in frame.locator("#where").inner_text()
    for level in (2, 3):
        q = frame.locator("#question").inner_text()  # What is a + b?
        a, b = [int(x) for x in q.replace("What is ", "").rstrip("?").split(" + ")]
        frame.locator("#answers button", has_text=str(a + b)).first.click()
        frame.locator("#level:has-text('Level %d of 5')" % level).wait_for()
    if shots:
        page.screenshot(path=os.path.join(shots, "2-local.png"), full_page=True)
    page.locator("#reload").click()
    page.frame_locator("#game").locator("#level:has-text('Level 3 of 5')").wait_for()
    # Translations: the same game in French.
    page.select_option("#lang", "fr")
    page.frame_locator("#game").locator("#level:has-text('Niveau 3 sur 5')").wait_for()


def check_kolibri_games(browser, shots):
    """The same games on the Kolibri Games games page, through the plugin's SDK."""
    try:
        from kolibri_games import devserver, registry
    except ImportError:
        print("skip Kolibri Games games page (kolibri-games isn't installed)")
        return
    from http.server import ThreadingHTTPServer

    games = tempfile.mkdtemp(prefix="edugame-kg-")
    for folder in (NUMBER_HUNT, SAVED):
        p = projects.load(folder)
        build.build_folder(p, os.path.join(games, p.slug))
    os.environ["KOLIBRI_HOME"] = tempfile.mkdtemp(prefix="edugame-kolibri-")
    os.environ["KOLIBRI_GAMES_PATH"] = games
    os.environ["KOLIBRI_GAMES_DEV_QUIET"] = "1"
    registry.discover(refresh=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), devserver.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]
    try:
        page = browser.new_page(viewport={"width": 1100, "height": 860})
        page.goto(base + "?as=amina#/play/g-org.togetherings.number-hunt")
        frame = page.frame_locator("iframe.game-frame")
        frame.locator("#intro-rule:has-text('Your first attempt is the one that counts')").wait_for()
        frame.locator("#btn-start").click()
        guesses = binary_search(frame)
        frame.locator("#done-standing:has-text('number 1 of 1')").wait_for()
        assert frame.locator("#board tbody tr").count() == 1
        assert frame.locator("#btn-exit").is_visible()
        if shots:
            page.screenshot(path=os.path.join(shots, "3-kolibri-games.png"), full_page=True)
        page.goto(base + "?as=amina#/board/g-org.togetherings.number-hunt")
        page.locator(".scores, table").first.wait_for()
        assert str(guesses) in page.locator("body").inner_text()
        # A Saved Game keeps its save in the learner's account.
        page.goto(base + "?as=amina#/play/g-org.example.my-game")
        frame = page.frame_locator("iframe.game-frame")
        frame.locator("#where:has-text('your account')").wait_for()
        q = frame.locator("#question").inner_text()
        a, b = [int(x) for x in q.replace("What is ", "").rstrip("?").split(" + ")]
        frame.locator("#answers button", has_text=str(a + b)).first.click()
        frame.locator("#level:has-text('Level 2 of 5')").wait_for()
        page.goto(base + "?as=ben#/")
        page.goto(base + "?as=amina#/play/g-org.example.my-game")
        page.frame_locator("iframe.game-frame").locator("#level:has-text('Level 2 of 5')").wait_for()
        page.close()
    finally:
        server.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots")
    args = parser.parse_args()
    shots = args.screenshots
    if shots:
        os.makedirs(shots, exist_ok=True)
    hunt, hunt_url = serve(NUMBER_HUNT)
    saved, saved_url = serve(SAVED)
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 860})
            page.on("pageerror", lambda e: errors.append("page: %s" % e))
            page.on("console", lambda m: m.type == "error" and errors.append("console: %s" % m.text))
            check_scorm(page, hunt_url, shots)
            check_french(page, hunt_url)
            check_local_save(page, saved_url, shots)
            # Phone width: the test page and the games fit.
            phone = browser.new_page(viewport={"width": 390, "height": 800}, is_mobile=True)
            test_page(phone, hunt_url, "scorm").locator("#btn-start").wait_for()
            assert phone.evaluate("document.documentElement.scrollWidth") <= 390
            phone.close()
            check_kolibri_games(browser, shots)
            browser.close()
    finally:
        hunt.shutdown()
        saved.shutdown()
    if errors:
        print("\n".join(errors))
        sys.exit("Browser errors (see above).")
    print("EduGame browser test passed.")


if __name__ == "__main__":
    main()
