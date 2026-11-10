"""
Plays the example games in Chromium, the way each platform runs them:

* in the test page as a learning system (SCORM 1.2, like Kolibri Learn and Moodle)
* in the test page as a website (RACHEL, Kiwix: saves in the browser)
* in French, with ?lang=fr, and with the kit's Options panel
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

from edugame import build, cli, kolibri_test, project as projects
from tests.helpers import EXAMPLES, TEMPLATES

NUMBER_HUNT = os.path.join(EXAMPLES, "number-hunt")
MEMORY = os.path.join(EXAMPLES, "memory-match")
SAVED = os.path.join(TEMPLATES, "saved")
LESSONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "lessons")


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
    assert saved["cmi.core.lesson_status"] == "passed", saved  # "passed": Kolibri ignores "completed"
    assert saved["cmi.core.score.raw"] == str(round((20 - guesses) / 19 * 100)), saved  # grade: 1 guess = 100%, 20 = 0%
    assert saved["cmi.core.exit"] == "suspend", saved  # or some systems start afresh next time
    if shots:
        page.screenshot(path=os.path.join(shots, "1-scorm.png"), full_page=True)
    # A save made as the page closes ("leave") reaches the system before LMSFinish ends the session.
    page.evaluate("""() => document.getElementById('game').contentWindow.EduGame.on('leave', function () {
        document.getElementById('game').contentWindow.EduGame.save({ left: 'just now' }); })""")
    # The learning system keeps the save, so the best shows next time.
    page.locator("#reload").click()
    page.frame_locator("#game").locator("#intro-rule:has-text('Your best: %d guesses.')" % guesses).wait_for()
    assert json.loads(cmi(page)["cmi.suspend_data"])["_save"] == {"left": "just now"}, "the leave save arrived" 
    page.locator("#reset").click()
    page.frame_locator("#game").locator("#intro-rule").wait_for()
    assert "Your best" not in page.frame_locator("#game").locator("#intro-rule").inner_text()


def check_french(page, base):
    frame = test_page(page, base, "local", lang="fr")
    frame.locator(".eg-title:has-text('Chasse au nombre')").wait_for()
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


def answer_sum(frame):
    q = frame.locator("#question").inner_text()  # What is a + b?
    a, b = [int(x) for x in q.replace("What is ", "").rstrip("?").split(" + ")]
    frame.locator("#answers button", has_text=str(a + b)).first.click()


def saved_cmi(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('edugame-test-scorm:org.example.my-game') || '{}')")


def check_save_problem(page, base, shots):
    """A save the helper can't read is never written over: the learner chooses."""
    frame = test_page(page, base, "scorm")
    page.locator("#reset").click()
    frame = page.frame_locator("#game")
    frame.locator("#question:has-text('What is')").wait_for()
    answer_sum(frame)
    frame.locator("#level:has-text('Level 2 of 5')").wait_for()

    # Damaged: the helper asks, the game starts afresh, and nothing is saved over it.
    page.locator("#damage").click()
    damaged = saved_cmi(page)["cmi.suspend_data"]
    frame.locator(".eg-problem:has-text('Start over')").wait_for()
    if shots:
        page.screenshot(path=os.path.join(shots, "3-save-problem.png"), full_page=True)
    frame.locator(".eg-problem button:has-text('Play without saving')").click()
    assert frame.locator(".eg-problem").count() == 0
    frame.locator("#level:has-text('Level 1 of 5')").wait_for()
    answer_sum(frame)
    frame.locator("#level:has-text('Level 2 of 5')").wait_for()
    page.wait_for_timeout(300)
    assert saved_cmi(page)["cmi.suspend_data"] == damaged, "a damaged save was written over"
    problem = page.frame_locator("#game").locator("html").evaluate(
        "() => EduGame.ready().then(function (i) { return i.saveProblem; })")
    assert problem == "unreadable", problem

    # Start over: saving begins again.
    page.locator("#reload").click()
    frame.locator(".eg-problem button:has-text('Start over')").click()
    frame.locator("#question:has-text('What is')").wait_for()
    answer_sum(frame)
    frame.locator("#level:has-text('Level 2 of 5')").wait_for()
    page.wait_for_timeout(300)
    assert json.loads(saved_cmi(page)["cmi.suspend_data"])["_save"] == {"level": 2}

    # From a newer version of the game: kept, with no way to start over.
    newer = json.dumps({"_v": 99, "_save": {"level": 4}})
    page.evaluate("(t) => API.LMSSetValue('cmi.suspend_data', t)", newer)
    page.locator("#reload").click()
    frame.locator(".eg-problem:has-text('newer version')").wait_for()
    assert frame.locator(".eg-problem button:has-text('Start over')").count() == 0
    frame.locator(".eg-problem button").click()
    answer_sum(frame)
    page.wait_for_timeout(300)
    assert saved_cmi(page)["cmi.suspend_data"] == newer, "a save from a newer version was written over"
    page.locator("#reset").click()


def check_options(browser, base, shots):
    """The kit's Options panel: the theme shows at once, Back puts it back, the language changes on Apply."""
    page = browser.new_page(viewport={"width": 1000, "height": 760}, color_scheme="light")
    frame = test_page(page, base, "scorm")
    html = frame.locator("html")
    frame.locator(".eg-header .eg-title:has-text('Memory Match')").wait_for()
    assert html.get_attribute("data-theme") == "light"
    frame.locator(".eg-options-button").click()
    card = frame.locator(".eg-card")
    card.wait_for()
    assert card.locator("label[lang=fr]").inner_text().strip() == "Français"
    assert card.locator("legend", has_text="Wrong cards stay face up").count() == 1  # the game's own option
    card.locator("input[name=eg-theme][value=dark]").check()
    assert html.get_attribute("data-theme") == "dark"                     # shown straight away
    page.keyboard.press("Escape")
    assert html.get_attribute("data-theme") == "light" and card.count() == 0  # Back puts it back
    frame.locator(".eg-options-button").click()
    card.locator("input[name=eg-theme][value=dark]").check()
    card.locator("label[lang=fr]").click()
    assert frame.locator(".eg-title").inner_text() == "Memory Match"      # the language waits for Apply
    if shots:
        page.screenshot(path=os.path.join(shots, "6-options.png"))
    card.locator("button.eg-primary").click()
    frame.locator(".eg-title:has-text('Paires de cartes')").wait_for()
    frame.locator(".eg-options-button:has-text('Options')").wait_for()
    frame.locator("[data-t=again]:has-text('Rejouer')").wait_for(state="attached")
    assert html.get_attribute("lang") == "fr" and html.get_attribute("data-theme") == "dark"
    # The language is kept with the learner's save (here, the learning system's), the theme on this device.
    record = json.loads(page.evaluate(
        "() => JSON.parse(localStorage.getItem('edugame-test-scorm:org.togetherings.memory-match'))['cmi.suspend_data']"))
    assert record["_lang"] == "fr", record
    page.locator("#reload").click()
    page.frame_locator("#game").locator("html[lang=fr][data-theme=dark]").wait_for()
    # On a phone the header still fits.
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.frame_locator("#game").locator("body").evaluate("b => b.scrollWidth <= b.clientWidth + 1")
    page.locator("#reset").click()
    page.frame_locator("#game").locator("html[lang=en][data-theme=light]").wait_for()
    page.close()


def lessons_cmi(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('edugame-test-scorm:org.example.lessons-test') || '{}')")


def finish_lesson(frame, board, acc, wpm, passed=True):
    frame.locator("#board").select_option(board)
    frame.locator("#acc").fill(str(acc))
    frame.locator("#wpm").fill(str(wpm))
    before = frame.locator("#out").inner_text()
    frame.locator("#passed" if passed else "#failed").click()
    frame.locator("#out").filter(has_not_text=before).wait_for()  # the result changed
    return json.loads(frame.locator("#out").inner_text())


def check_lessons(page, base):
    """Two scores (both higher is better), a board for each lesson, only passed rounds kept; Kolibri gets no score."""
    frame = test_page(page, base, "scorm")
    frame.locator("#out:has-text('ready')").wait_for()
    assert finish_lesson(frame, "l1", 90, 20)["kept"] == {"acc": 90, "wpm": 20, "plays": 1}
    assert finish_lesson(frame, "l1", 95, 15)["newBest"] is True           # higher accuracy wins, even slower
    assert finish_lesson(frame, "l1", 95, 10)["kept"] == {"acc": 95, "wpm": 15, "plays": 3}  # same accuracy: faster stays
    assert finish_lesson(frame, "l2", 99, 50, passed=False)["kept"] is None  # not passed: not a result
    saved = lessons_cmi(page)
    record = json.loads(saved["cmi.suspend_data"])
    assert record["l1"] == [95, 15, 3] and "l2" not in record, record
    assert saved["cmi.core.lesson_status"] == "passed", saved   # never "completed" (Kolibri ignores it)
    assert saved["cmi.core.score.raw"] == "90", saved            # (95 - 50) / (100 - 50): a learning system's grade
    # In Kolibri, no score is sent: Kolibri would read it as how much is done.
    page.locator("#as-kolibri").check()
    page.locator("#reset").click()            # a new learner, in Kolibri (deleting the save starts the game again)
    # Kolibri answers "" for a status not set yet: opening the game must still mark it "incomplete".
    page.wait_for_function("() => (JSON.parse(localStorage.getItem('edugame-test-scorm:org.example.lessons-test') || '{}')"
                           "['cmi.core.lesson_status']) === 'incomplete'", timeout=5000)
    frame = page.frame_locator("#game")
    frame.locator("#out:has-text('ready')").wait_for()
    finish_lesson(frame, "l1", 80, 30)
    saved = lessons_cmi(page)
    assert "cmi.core.score.raw" not in saved and saved["cmi.core.lesson_status"] == "passed", saved
    assert json.loads(saved["cmi.suspend_data"])["l1"] == [80, 30, 1]
    page.locator("#as-kolibri").uncheck()


def check_pages_counting(browser, shots):
    """The GitHub Pages site counts page views and rounds with GoatCounter (stubbed here: no network)."""
    import functools
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    from edugame import pages

    site = tempfile.mkdtemp(prefix="edugame-site-")
    pages.build_pages(projects.load(NUMBER_HUNT), site, goatcounter="example", repo="togetherings/edugame-kit")
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=site)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]
    try:
        page = browser.new_page(viewport={"width": 1000, "height": 760})
        # Instead of GoatCounter's script, a stand-in that remembers what it was asked to count.
        page.route("**/gc.zgo.at/count.js", lambda route: route.fulfill(
            content_type="text/javascript",
            body="window.counted = []; window.goatcounter = { count: function (v) { window.counted.push(v); } };"))
        page.goto(base)
        page.locator("a.play").wait_for()
        if shots:
            page.screenshot(path=os.path.join(shots, "5-github-pages.png"), full_page=True)
        page.locator("a.play").click()
        page.locator("#btn-start").click()
        binary_search(page)
        page.locator("#done:not([hidden])").wait_for()
        page.wait_for_function("window.counted && window.counted.length >= 2")
        paths = page.evaluate("window.counted.map(function (c) { return c.path + (c.event ? ' (event)' : ''); })")
        assert paths == ["/play/round-started (event)", "/play/round-finished (event)"], paths
        page.close()
    finally:
        server.shutdown()


def check_kolibri_games(browser, shots):
    """The same games on the Kolibri Games games page, through the plugin's SDK."""
    try:
        from kolibri_games import devserver, registry
    except ImportError:
        print("skip Kolibri Games games page (kolibri-games isn't installed)")
        return
    from http.server import ThreadingHTTPServer

    games = tempfile.mkdtemp(prefix="edugame-kg-")
    for folder in (NUMBER_HUNT, SAVED, LESSONS):
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
        # The games page shows the title already: the kit's header has only the Options button.
        frame.locator(".eg-header.eg-no-title .eg-options-button").wait_for()
        assert frame.locator(".eg-title").is_hidden()
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
        # Wait until the plugin has the save before leaving the page (on a slow machine it can still be on its way).
        with page.expect_response(lambda r: r.url.endswith("/state") and r.request.method == "POST"):
            frame.locator("#answers button", has_text=str(a + b)).first.click()
        frame.locator("#level:has-text('Level 2 of 5')").wait_for()
        page.goto(base + "?as=ben#/")
        page.goto(base + "?as=amina#/play/g-org.example.my-game")
        page.frame_locator("iframe.game-frame").locator("#level:has-text('Level 2 of 5')").wait_for()
        # Two scores and lessons: the plugin ranks them and has a board for each lesson, and a total.
        page.goto(base + "?as=amina#/play/g-org.example.lessons-test")
        frame = page.frame_locator("iframe.game-frame")
        frame.locator("#out:has-text('kolibri-games')").wait_for()
        finish_lesson(frame, "l1", 90, 20)
        finish_lesson(frame, "l2", 95, 30)
        finish_lesson(frame, "l2", 99, 50, passed=False)  # not passed: no result
        page.goto(base + "?as=amina#/board/g-org.example.lessons-test/b/l2")
        page.locator(".panel.board tbody tr").first.wait_for()
        row = page.locator(".panel.board tbody tr").first.inner_text()
        assert "95%" in row and "30 wpm" in row, row
        assert page.locator(".board-link").all_inner_texts() == ["All lessons", "Lesson 1", "Lesson 2"]
        page.locator(".board-link", has_text="All lessons").click()
        page.locator(".panel.board h2:has-text('All lessons')").wait_for()
        total = page.locator(".panel.board tbody tr").first.inner_text()
        assert "92.5%" in total and "Amina" in total, total  # (90 + 95) / 2
        if shots:
            page.screenshot(path=os.path.join(shots, "4-kolibri-games-lessons.png"), full_page=True)
        page.close()
    finally:
        server.shutdown()


def check_play_steps(browser, folder, shots):
    """The play steps edugame kolibri-test uses (tests/kolibri_play.py) work, here in the
    test page as a learning system, so they're right before a real Kolibri runs them."""
    steps = kolibri_test.load_play(os.path.join(folder, kolibri_test.PLAY_FILE))
    server, base = serve(folder)
    page = browser.new_page(viewport={"width": 1200, "height": 860})
    report = kolibri_test.Report()
    game = kolibri_test.Game(page, report, shots, {})
    try:
        test_page(page, base, "scorm")
        for visit, step in ((1, steps.first_visit), (2, steps.came_back)):
            if visit == 2:
                page.locator("#reload").click()
                page.wait_for_timeout(500)
            game.visit = visit
            game.frame = kolibri_test.find_game(page, timeout=20)
            assert game.frame is not None and game.frame != page.main_frame
            assert kolibri_test.helper_state(game.frame)["platform"] == "scorm"
            step(game)
        assert not report.failures, "%s: %s" % (folder, report.failures)
        assert game.expect_complete
    finally:
        page.close()
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
    lessons, lessons_url = serve(LESSONS)
    memory, memory_url = serve(MEMORY)
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
            check_save_problem(page, saved_url, shots)
            check_lessons(page, lessons_url)
            check_options(browser, memory_url, shots)
            # Phone width: the test page and the games fit.
            phone = browser.new_page(viewport={"width": 390, "height": 800}, is_mobile=True)
            test_page(phone, hunt_url, "scorm").locator("#btn-start").wait_for()
            assert phone.evaluate("document.documentElement.scrollWidth") <= 390
            phone.close()
            for folder in (SAVED, os.path.join(TEMPLATES, "scored"), NUMBER_HUNT):
                check_play_steps(browser, folder, None)
            check_pages_counting(browser, shots)
            check_kolibri_games(browser, shots)
            browser.close()
    finally:
        hunt.shutdown()
        saved.shutdown()
        lessons.shutdown()
        memory.shutdown()
    if errors:
        print("\n".join(errors))
        sys.exit("Browser errors (see above).")
    print("EduGame browser test passed.")


if __name__ == "__main__":
    main()
