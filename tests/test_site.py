"""A site of pages for a game with packages and a menu page (edugame pages, pages.menu: docs/platforms/GITHUB_PAGES.md)."""
import json
import os
import re
import zipfile

from edugame import build, cli, pages, project as projects
from tests.test_languages import edit, packaged

MENU = """<!doctype html>
<html><head><meta charset="utf-8"><title>Menu</title></head>
<body><ul id="list"></ul>
<script src="edugame-config.js"></script>
<script src="edugame.js"></script>
<script src="js/menu.js"></script>
</body></html>
"""

MENU_JS = """(function () {
  var site = EduGame.site(), list = document.getElementById("list");
  site.packages.forEach(function (p) {
    var a = document.createElement("a");
    a.href = p.url; a.textContent = p.title; a.className = "pkg";
    var li = document.createElement("li"); li.appendChild(a); list.appendChild(li);
  });
})();
"""


def with_menu(tmp_path, **menu):
    """The packaged game (lesson-01 in en and fr, lesson-02 in fr only), with a menu page."""
    folder = packaged(tmp_path)
    with open(os.path.join(folder, "menu.html"), "w", encoding="utf-8") as f:
        f.write(MENU)
    os.makedirs(os.path.join(folder, "js"), exist_ok=True)
    with open(os.path.join(folder, "js", "menu.js"), "w", encoding="utf-8") as f:
        f.write(MENU_JS)
    cfg = {"page": "menu.html", "files": ["js/menu.js"]}
    cfg.update(menu)
    edit(folder, lambda d: d.update(pages={"menu": cfg}))
    return folder


def config_of(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return json.loads(re.search(r"window\.EDUGAME_CONFIG = (.*);\s*$", text, re.S).group(1))


def test_each_package_in_each_language_has_its_own_address(tmp_path):
    p = projects.load(with_menu(tmp_path))
    site = str(tmp_path / "site")
    pages.build_pages(p, site)
    made = json.load(open(os.path.join(site, "site.json")))["pages"]
    assert made == ["en/", "en/lesson-01/", "fr/", "fr/lesson-01/", "fr/lesson-02/"]

    # The menu: the game's menu page, with its own files; a package: the game's start page, without them.
    with open(os.path.join(site, "en", "index.html"), encoding="utf-8") as f:
        assert 'src="js/menu.js"' in f.read()
    assert os.path.exists(os.path.join(site, "en", "js", "menu.js"))
    assert not os.path.exists(os.path.join(site, "en", "lesson-01", "js", "menu.js"))
    assert not os.path.exists(os.path.join(site, "en", "lesson-01", "menu.html"))
    for extra in pages.PLATFORM_FILES:
        assert not os.path.exists(os.path.join(site, "fr", "lesson-02", extra))

    menu = config_of(os.path.join(site, "en", "edugame-config.js"))
    assert menu["languages"] == ["en"] and "package" not in menu
    assert menu["site"]["package"] is None and menu["site"]["home"] == "../en/"
    assert [x["id"] for x in menu["site"]["packages"]] == ["lesson-01"]
    assert menu["site"]["packages"][0] == {"id": "lesson-01", "title": "Lesson one", "description": p.text("description"),
                                           "url": "../en/lesson-01/", "config": {"lesson": "01"}}
    assert menu["site"]["languages"] == [
        {"code": "en", "name": "English", "url": "../en/", "packages": 1},
        {"code": "fr", "name": "Français", "url": "../fr/", "packages": 2}]

    one = config_of(os.path.join(site, "fr", "lesson-01", "edugame-config.js"))["site"]
    assert one["home"] == "../../fr/" and one["next"] == "../../fr/lesson-02/" and one["package"] == "lesson-01"
    assert [x["url"] for x in one["languages"]] == ["../../en/lesson-01/", "../../fr/lesson-01/"]
    two = config_of(os.path.join(site, "fr", "lesson-02", "edugame-config.js"))["site"]
    assert two["next"] is None
    assert [x["url"] for x in two["languages"]] == ["../../en/", "../../fr/lesson-02/"]   # no lesson 2 in English
    assert two["packages"][1]["title"] == "Leçon deux"

    # The bare address and the old ones go to the new pages.
    with open(os.path.join(site, "index.html"), encoding="utf-8") as f:
        root = f.read()
    assert "egChoose" in root and '"address": "fr"' in root
    with open(os.path.join(site, "play", "lesson-02", "index.html"), encoding="utf-8") as f:
        assert "../../?p=lesson-02" in f.read()


def test_addresses_are_the_language_codes_in_lower_case(tmp_path):
    folder = with_menu(tmp_path)
    os.rename(os.path.join(folder, "lang", "fr.json"), os.path.join(folder, "lang", "pt-BR.json"))
    for n in ("01", "02"):
        os.rename(os.path.join(folder, "lessons", n, "fr.json"), os.path.join(folder, "lessons", n, "pt-BR.json"))

    def langs(d):
        d["languages"] = ["en", "pt-BR"]
        d["packages"][1]["languages"] = ["pt-BR"]
    edit(folder, langs)
    site = str(tmp_path / "site")
    pages.build_pages(projects.load(folder), site)
    assert os.path.isdir(os.path.join(site, "pt-br", "lesson-02"))
    assert json.load(open(os.path.join(site, "site.json")))["languages"] == {"en": "en", "pt-BR": "pt-br"}


def test_menu_files_are_never_in_the_zips(tmp_path):
    p = projects.load(with_menu(tmp_path))
    for path in build.build_all(p, str(tmp_path / "dist")):
        names = zipfile.ZipFile(path).namelist()
        assert "menu.html" not in names and "js/menu.js" not in names
        assert "js/menu.js" not in zipfile.ZipFile(path).read("imsmanifest.xml").decode("utf-8")


def test_counting_is_on_every_page_but_the_redirects(tmp_path):
    site = str(tmp_path / "site")
    pages.build_pages(projects.load(with_menu(tmp_path)), site, goatcounter="example")
    for page in ("en/index.html", "fr/lesson-02/index.html"):
        with open(os.path.join(site, page), encoding="utf-8") as f:
            assert "example.goatcounter.com" in f.read()
    with open(os.path.join(site, "index.html"), encoding="utf-8") as f:
        assert "goatcounter" not in f.read()


def test_offline_copy_is_one_page_with_every_page_at_an_address(tmp_path):
    p = projects.load(with_menu(tmp_path, offline="all-lessons"))
    path = pages.offline_zip(p, str(tmp_path / "out"))
    assert os.path.basename(path) == "my-game-all-lessons-0.1.0.zip"
    z = zipfile.ZipFile(path)
    names = z.namelist()
    for name in ("index.html", "README.txt", "edugame.js", "site/pages.js", "site/router.js", "js/menu.js",
                 "lessons/01/en.json.js", "lessons/02/fr.json.js"):
        assert name in names, name
    assert "menu.html" not in names and "edugame-config.js" not in names and "kolibri-game.json" not in names
    data = json.loads(re.search(r"window\.EDUGAME_SITE = (.*);\s*$", z.read("site/pages.js").decode("utf-8"), re.S).group(1))
    assert sorted(data["configs"]) == ["en", "en/lesson-01", "fr", "fr/lesson-01", "fr/lesson-02"]
    assert '<script src="{config}">' in data["menu"] and "js/menu.js" in data["menu"]
    cfg = json.loads(re.search(r"window\.EDUGAME_CONFIG = (.*);\s*$",
                               z.read(data["configs"]["fr/lesson-01"]).decode("utf-8"), re.S).group(1))
    assert cfg["site"]["mode"] == "hash" and cfg["site"]["home"] == "#fr" and cfg["site"]["next"] == "#fr/lesson-02"
    assert cfg["package"]["id"] == "lesson-01"


def test_bundle_makes_the_offline_copy_too(tmp_path, capsys):
    folder = with_menu(tmp_path, offline="all-lessons")
    out = str(tmp_path / "bundles")
    cli.main(["bundle", folder, "-o", out])
    assert sorted(os.listdir(out)) == ["my-game-all-languages-0.1.0.zip", "my-game-all-lessons-0.1.0.zip",
                                       "my-game-en-0.1.0.zip", "my-game-fr-0.1.0.zip"]


def test_menu_settings_are_checked(tmp_path):
    folder = with_menu(tmp_path)
    for bad, says in [({"page": "menus/menu.html"}, "top of the game folder"),
                      ({"page": "nothere.html"}, "isn't in the game folder"),
                      ({"page": "menu.html", "offline": "All Lessons"}, "pages.menu.offline"),
                      ({"page": "menu.html", "colour": "red"}, "pages.menu must be like")]:
        edit(folder, lambda d: d.update(pages={"menu": bad}))
        try:
            projects.load(folder)
            assert False, bad
        except projects.ProjectError as e:
            assert any(says in x for x in e.problems), (bad, e.problems)
    edit(folder, lambda d: d.update(pages={"menu": {"page": "menu.html"}, "colour": "red"}))
    try:
        projects.load(folder)
        assert False
    except projects.ProjectError as e:
        assert any("pages must be like" in x for x in e.problems)


def test_a_site_built_inside_the_game_never_ends_up_in_its_pages(tmp_path):
    # game-pages.yml runs "edugame pages . -o _site": the site lands inside the game's folder (v0.3.5 copied each
    # page into the next ones, until the runner ran out of space).
    folder = with_menu(tmp_path)
    for out in ("_site", "web"):
        site = os.path.join(folder, out)
        pages.build_pages(projects.load(folder), site)
        pages.build_pages(projects.load(folder), site)                    # again, with the first one there
        for root, dirs, files in os.walk(site):
            assert out not in dirs, root
        assert json.load(open(os.path.join(site, "site.json")))["pages"] == [
            "en/", "en/lesson-01/", "fr/", "fr/lesson-01/", "fr/lesson-02/"]
        if out == "web":
            import shutil
            shutil.rmtree(site)


def test_links_to_the_release_and_the_code_with_a_repo(tmp_path):
    p = projects.load(with_menu(tmp_path, offline="all-lessons"))
    site = str(tmp_path / "site")
    pages.build_pages(p, site, repo="owner/game")
    links = config_of(os.path.join(site, "en", "edugame-config.js"))["site"]["links"]
    assert links == {"release": "https://github.com/owner/game/releases/latest", "code": "https://github.com/owner/game",
                     "offline": "my-game-all-lessons-0.1.0.zip"}
    pages.build_pages(p, site)
    assert config_of(os.path.join(site, "en", "edugame-config.js"))["site"]["links"]["release"] is None


def test_the_starter_menu(tmp_path, capsys):
    folder = packaged(tmp_path)
    cli.main(["menu", folder])
    for name in ("menu.html", "menu/menu.js", "menu/menu.css"):
        assert os.path.exists(os.path.join(folder, name)), name
    p = projects.load(folder)
    assert p.menu == {"page": "menu.html", "files": ["menu/*"], "offline": "all"}
    for path in build.build_all(p, str(tmp_path / "dist")):
        assert not [n for n in zipfile.ZipFile(path).namelist() if n.startswith("menu")]
    site = str(tmp_path / "site")
    pages.build_pages(p, site, repo="owner/game")
    assert os.path.exists(os.path.join(site, "fr", "menu", "menu.js"))
    with open(os.path.join(site, "fr", "index.html"), encoding="utf-8") as f:
        assert 'data-eg="get"' in f.read()
    try:                                                         # never over a game's own files
        cli.main(["menu", folder])
        assert False
    except SystemExit as e:
        assert "already there" in str(e)
