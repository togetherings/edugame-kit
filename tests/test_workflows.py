"""The workflows games use (game.yml, game-pages.yml) and the starter's calls to them."""
import os
import re

from edugame import __version__, cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
STARTER = os.path.join(ROOT, "edugame", "templates", "github")
RELEASE = "v" + __version__


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def test_the_game_workflows_install_this_release_of_the_kit():
    # A game calling game.yml@v0.3.0 must get kit 0.3.0: bump these with __version__.
    for name in ("game.yml", "game-pages.yml"):
        assert re.search(r"^  KIT_REF: %s\b" % re.escape(RELEASE), read(WORKFLOWS, name), re.M), name


def test_the_starter_calls_this_release():
    for name, workflow in (("build.yml", "game.yml"), ("pages.yml", "game-pages.yml")):
        text = read(STARTER, name)
        refs = re.findall(r"togetherings/edugame-kit/\.github/workflows/([\w.-]+)@(\S+)", text)
        assert refs == [(workflow, RELEASE)], (name, refs)


def test_workflows_use_actions_on_node_24():
    old = {"actions/checkout": 5, "actions/setup-python": 6, "actions/upload-artifact": 6,
           "actions/upload-pages-artifact": 4, "actions/deploy-pages": 5}
    for folder in (WORKFLOWS, STARTER):
        for name in os.listdir(folder):
            for action, major in re.findall(r"uses: (actions/[\w-]+)@v(\d+)", read(folder, name)):
                assert int(major) >= old.get(action, 0), (name, action, major)


def test_new_games_get_dependabot(tmp_path):
    folder = str(tmp_path / "game")
    cli.main(["new", folder, "--github"])
    config = read(folder, ".github", "dependabot.yml")
    assert "package-ecosystem: github-actions" in config
    assert os.path.isfile(os.path.join(folder, ".github", "workflows", "pages.yml"))


def test_the_game_workflows_do_what_the_starter_promises():
    build = read(WORKFLOWS, "game.yml")
    assert "edugame check" in build and "gh release upload" in build and "edugame kolibri-test" in build
    pages = read(WORKFLOWS, "game-pages.yml")
    assert "edugame pages" in pages and "vars.GOATCOUNTER_CODE" in pages and "actions/deploy-pages" in pages
