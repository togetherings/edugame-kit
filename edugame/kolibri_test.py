"""
edugame kolibri-test: play a game in a real Kolibri, the way learners get it.

    pip install kolibri playwright && python -m playwright install chromium
    edugame kolibri-test my-game

What it does (in a throwaway Kolibri, in a temporary folder, so it never touches a Kolibri you use):

1. Builds the game's zip, sets up Kolibri with a learner, and adds the zip to a channel as an
   HTML5 app, as importing a channel from Kolibri Studio would.
2. Starts Kolibri, signs in as the learner and opens the game in Learn.
3. First visit: the save helper must reach Kolibri's SCORM connection. Then the game's own play
   steps run, if it has them (tests/kolibri_play.py, below).
4. The learner leaves. What Kolibri recorded is checked: the save fits SCORM 1.2, the status
   is "incomplete" or "passed" (never a score), and the resource is done if the play steps
   said it should be.
5. Second visit: the game must get back exactly the save Kolibri kept. Then the play steps'
   came_back() runs, to check the game carries on where the learner left off.

Play steps. Without them the test still checks the game opens, connects and reports nothing
wrong; with them it checks saving and coming back. tests/kolibri_play.py in the game folder
(never put in the zip) can define:

    def first_visit(game):      # play a little, so the game saves (and maybe completes)
        game.click("#start")
        game.expect_complete = True        # check Kolibri counts the resource as done
    def came_back(game):        # check the game carried on
        game.check("Level 2" in game.text("#level"), "back on level 2")

`game` has: page and frame (Playwright), visit (1 or 2), data (a dict kept between visits),
js(expression), wait_for(expression), click(selector), fill(selector, text), text(selector),
press(*keys), hold(key, ms), check(condition, what), shot(name), expect_complete.

Standard library only, apart from Playwright (imported when this runs). Kolibri runs as its own
command; the scripts in edugame/kolibri/ run inside it (kolibri manage shell).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from . import build, project as projects

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "kolibri")
PLAY_FILE = "tests/kolibri_play.py"      # project.files() never puts it in the zip
LEARNER, PASSWORD = "learner", "learner123"


class Failed(Exception):
    pass


class Report:
    def __init__(self):
        self.failures = []

    def check(self, cond, what):
        print(("ok   " if cond else "FAIL ") + what, flush=True)
        if not cond:
            self.failures.append(what)
        return bool(cond)

    def note(self, what):
        print("       " + what, flush=True)


# ------------------------------------------------------------------ Kolibri

class Kolibri:
    """A throwaway Kolibri, run with the `kolibri` command."""

    def __init__(self, home, port):
        self.home = home
        self.port = port
        self.base = "http://127.0.0.1:%d/" % port
        self.env = dict(os.environ, KOLIBRI_HOME=home, KOLIBRI_RUN_MODE=os.environ.get("KOLIBRI_RUN_MODE", "edugame-test"))
        self.started = False

    def run(self, *args, **kw):
        out = subprocess.run(["kolibri"] + list(args), env=self.env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, universal_newlines=True, **kw)
        if out.returncode != 0:
            print(out.stdout[-3000:])
            raise Failed("kolibri %s failed (exit %d)" % (" ".join(args[:2]), out.returncode))
        return out.stdout

    def shell(self, script, **env):
        """Run one of edugame/kolibri/*.py inside Kolibri; returns its EDUGAME_RESULT line as data."""
        saved = self.env
        self.env = dict(self.env, **env)
        try:
            out = self.run("manage", "shell", "-c", "exec(open(%r).read())" % os.path.join(SCRIPTS, script))
        finally:
            self.env = saved
        for line in out.splitlines():
            if line.startswith("EDUGAME_RESULT "):
                return json.loads(line[len("EDUGAME_RESULT "):])
        print(out[-3000:])
        raise Failed("%s gave no result" % script)

    def set_up(self, zip_path, title):
        print("Setting up Kolibri in %s ..." % self.home, flush=True)
        self.run("manage", "migrate")
        self.run("manage", "provisiondevice", "--facility", "Test School", "--preset", "formal",
                 "--superusername", "admin", "--superuserpassword", "admin123", "--language_id", "en", "--noinput")
        return self.shell("setup_channel.py", EDUGAME_ZIP=os.path.abspath(zip_path), EDUGAME_TITLE=title,
                          EDUGAME_LEARNER=LEARNER, EDUGAME_PASSWORD=PASSWORD)

    def start(self):
        self.run("start", "--port", str(self.port))
        self.started = True
        for _ in range(90):
            try:
                urllib.request.urlopen(self.base, timeout=5)
                return
            except Exception:
                time.sleep(2)
        raise Failed("Kolibri didn't start on %s" % self.base)

    def stop(self):
        if self.started:
            subprocess.run(["kolibri", "stop"], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.started = False

    def record(self, channel):
        return self.shell("read_record.py", EDUGAME_CONTENT_ID=channel["content_id"], EDUGAME_LEARNER=LEARNER)


# ----------------------------------------------------------- the game in Learn

class Game:
    """What a game's play steps get (see the top of this file)."""

    def __init__(self, page, report, shots, data):
        self.page = page
        self.frame = None
        self.visit = 0
        self.data = data
        self.expect_complete = False
        self._report = report
        self._shots = shots

    def js(self, expression):
        return self.frame.evaluate(expression)

    def wait_for(self, expression, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.frame.evaluate(expression):
                    return True
            except Exception:
                pass
            time.sleep(0.3)
        return False

    def click(self, selector="canvas, body"):
        self.frame.locator(selector).first.click()

    def fill(self, selector, text):
        self.frame.locator(selector).first.fill(str(text))

    def text(self, selector):
        return self.frame.locator(selector).first.inner_text()

    def press(self, *keys):
        for k in keys:
            self.page.keyboard.press(k)
            self.page.wait_for_timeout(150)

    def hold(self, key, ms):
        self.page.keyboard.down(key)
        self.page.wait_for_timeout(ms)
        self.page.keyboard.up(key)

    def check(self, cond, what):
        return self._report.check(cond, what)

    def shot(self, name):
        if self._shots:
            self.page.screenshot(path=os.path.join(self._shots, "%d-%s.png" % (self.visit, name)))


def load_play(path):
    if not path or not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("edugame_kolibri_play", path)
    module = importlib.util.module_from_spec(spec)
    was, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # no __pycache__ in the game's folder
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = was
    return module


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def sign_in(page, base, facility):
    """Through Kolibri's sign-in API (what its sign-in page calls), which changes less than the page."""
    page.goto(base + "en/")
    page.wait_for_load_state("networkidle")
    csrf = next((c["value"] for c in page.context.cookies() if c["name"] in ("kolibri_csrftoken", "csrftoken")), "")
    r = page.request.post(base + "api/auth/session/", headers={"X-CSRFToken": csrf, "Referer": base},
                          data={"username": LEARNER, "password": PASSWORD, "facility": facility})
    return r.ok


def find_game(page, timeout=90):
    """The frame the game runs in (inside Kolibri's sandbox frame, on another port)."""
    end = time.time() + timeout
    while time.time() < end:
        for f in page.frames:
            try:
                if f.evaluate("typeof EduGame !== 'undefined' && typeof EduGame.ready === 'function'"):
                    return f
            except Exception:
                pass
        time.sleep(1)
    return None


def describe_frames(page, report):
    for f in page.frames:
        try:
            d = f.evaluate("""() => ({title: document.title, EduGame: typeof EduGame, API: typeof window.API,
                frames: document.querySelectorAll('iframe').length, body: (document.body ? document.body.innerText : '').slice(0, 200)})""")
        except Exception as e:
            d = "can't read it: %s" % str(e).splitlines()[0]
        report.note("frame %s: %s" % (f.url, d))


def helper_state(frame, timeout=15):
    """What the save helper says: {platform, save}. Waits while it's still looking for SCORM."""
    end = time.time() + timeout
    state = None
    while time.time() < end:
        state = frame.evaluate("() => EduGame.ready().then(function (i) { return {platform: i.platform, save: i.save}; })")
        if state["platform"] == "scorm":
            break
        time.sleep(1)
    return state


def open_game(page, base, channel, report, visit):
    page.goto(base + "en/learn/#/topics/c/" + channel["node_id"])
    frame = find_game(page)
    if not report.check(frame is not None, "visit %d: the game opened in Learn" % visit):
        describe_frames(page, report)
        return None, None
    state = helper_state(frame)
    report.check(state["platform"] == "scorm",
                 "visit %d: the save helper uses Kolibri's SCORM connection (%s)" % (visit, state["platform"]))
    return frame, state


def play(kolibri, channel, play_steps, report, shots):
    from playwright.sync_api import sync_playwright  # only needed here

    errors = []
    data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: r.status >= 400 and "/content/" in r.url and report.note("HTTP %s %s" % (r.status, r.url)))
        game = Game(page, report, shots, data)
        try:
            if not report.check(sign_in(page, kolibri.base, channel["facility"]), "signed in as a learner"):
                return

            # ---- First visit
            game.visit = 1
            game.frame, state = open_game(page, kolibri.base, channel, report, 1)
            if not game.frame:
                return
            report.check(state["save"] is None, "a new learner starts with no save")
            game.shot("opened")
            if play_steps and hasattr(play_steps, "first_visit"):
                play_steps.first_visit(game)
            page.wait_for_timeout(1500)
            game.shot("played")

            # ---- Leave; what did Kolibri keep?
            page.goto(kolibri.base + "en/learn/#/home")
            page.wait_for_timeout(5000)        # Learn sends the last of the learner's progress
            rec = kolibri.record(channel)
            kept = check_record(rec, game.expect_complete, report)

            # ---- Second visit
            game.visit = 2
            game.frame, state = open_game(page, kolibri.base, channel, report, 2)
            if not game.frame:
                return
            if kept is not None:
                report.check(same(state["save"], kept), "visit 2: the game got back the save Kolibri kept")
            page.wait_for_timeout(1000)
            game.shot("came-back")
            if play_steps and hasattr(play_steps, "came_back"):
                play_steps.came_back(game)
        finally:
            report.check(not errors, "no errors on the page: %s" % errors)
            browser.close()


def check_record(rec, expect_complete, report):
    """Checks what Kolibri recorded after the first visit; returns the game's save it kept, or None."""
    if not report.check(rec.get("found"), "Kolibri recorded the learner's visit"):
        return None
    data = rec.get("suspend_data") or ""
    report.note("progress %s, status %r, suspend_data %d characters" % (rec.get("progress"), rec.get("status"), len(data)))
    report.check(len(data) <= 4096, "the save fits SCORM 1.2 (%d of 4096 characters)" % len(data))
    report.check(rec.get("status") in ("incomplete", "passed"), "the status is incomplete or passed, never a score")
    report.check(not rec.get("score_raw"), "no score is sent to Kolibri (it reads a score as how much is done)")
    if expect_complete:
        report.check((rec.get("progress") or 0) >= 1, "the resource counts as done (progress %s)" % rec.get("progress"))
    if not data:
        report.note("the game didn't save during the first visit; add play steps (%s) to test saving" % PLAY_FILE)
        return None
    try:
        record = json.loads(data)
    except ValueError:
        report.check(False, "suspend_data is the helper's record (JSON)")
        return None
    report.check(record.get("_v") == 1, "suspend_data is the helper's record")
    report.note("record keys: %s" % sorted(record))
    return record.get("_save")


# --------------------------------------------------------------------- run

def run(folder, play_file=None, port=8080, shots="kolibri-screenshots", keep=False):
    if not shutil.which("kolibri"):
        sys.exit("This needs Kolibri: pip install kolibri playwright && python -m playwright install chromium")
    try:
        import playwright  # noqa: F401
    except ImportError:
        sys.exit("This needs Playwright: pip install playwright && python -m playwright install chromium")

    try:
        project = projects.load(folder)
    except projects.ProjectError as e:
        sys.exit("%s can't be built yet:\n  - %s" % (folder, "\n  - ".join(e.problems)))
    play_file = play_file or os.path.join(folder, PLAY_FILE)
    play_steps = load_play(play_file)
    print("Playing %s in a real Kolibri%s." % (project.title, " with %s" % play_file if play_steps else " (no play steps)"), flush=True)
    if shots:
        os.makedirs(shots, exist_ok=True)

    work = tempfile.mkdtemp(prefix="edugame-kolibri-")
    home = os.path.join(work, "kolibri-home")
    zip_path = build.build_zip(project, os.path.join(work, "dist"))
    kolibri = Kolibri(home, port)
    report = Report()
    try:
        channel = kolibri.set_up(zip_path, project.title)
        print("Added %s to a channel." % os.path.basename(zip_path), flush=True)
        kolibri.start()
        play(kolibri, channel, play_steps, report, shots)
    except Failed as e:
        report.check(False, str(e))
    finally:
        kolibri.stop()
        if keep:
            print("Kept the test Kolibri's files in %s" % work)
        else:
            shutil.rmtree(work, ignore_errors=True)
    print()
    if report.failures:
        print("%d check(s) failed in Kolibri." % len(report.failures))
        return 1
    print("Played in Kolibri: everything worked.")
    return 0
