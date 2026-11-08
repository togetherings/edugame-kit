"""Languages, content and packages: lang/ files, content scripts, and several zips from one folder."""
import json
import os
import zipfile

from edugame import build, pages, project as projects

from .helpers import copy_game


def write(folder, rel, data):
    path = os.path.join(folder, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)


def edit(folder, change):
    path = os.path.join(folder, "edugame.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    change(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def problems(folder):
    try:
        projects.load(folder)
    except projects.ProjectError as e:
        return e.problems
    return []


def test_lang_values_can_be_lists_and_plurals(tmp_path):
    folder = copy_game("saved", tmp_path)
    write(folder, "lang/en.json", dict(json.load(open(os.path.join(folder, "lang", "en.json"))), **{
        "help": ["First paragraph.", "Second paragraph."],
        "tries": {"one": "{n} try", "other": "{n} tries"},
        "_notes": {"tries": "how many times the learner tried"},
    }))
    write(folder, "lang/fr.json", dict(json.load(open(os.path.join(folder, "lang", "fr.json"))), **{
        "help": ["Premier.", "Deuxième."], "tries": {"one": "{n} essai", "other": "{n} essais"},
    }))
    p = projects.load(folder)
    assert p.text("help") == "First paragraph.\n\nSecond paragraph."
    assert p.text("tries", "fr") == "{n} essais"

    write(folder, "lang/fr.json", dict(json.load(open(os.path.join(folder, "lang", "fr.json"))), tries={"one": "x"}))
    assert any("plural" in x for x in problems(folder))
    write(folder, "lang/fr.json", dict(json.load(open(os.path.join(folder, "lang", "fr.json"))), tries=3))
    assert any("tries" in x for x in problems(folder))
    write(folder, "lang/fr.json", dict(json.load(open(os.path.join(folder, "lang", "fr.json"))),
                                       tries="x", _language={"name": "Français", "dir": "sideways"}))
    assert any("_language" in x for x in problems(folder))


def test_a_regional_language_only_needs_the_words_that_differ(tmp_path):
    folder = copy_game("saved", tmp_path)
    edit(folder, lambda d: d.update(languages=["en", "en-GB", "fr"]))
    write(folder, "lang/en-GB.json", {"_language": {"name": "English (UK)"}, "title": "My game (UK)"})
    p = projects.load(folder)
    assert projects.missing_strings(p) == {}
    assert p.text("title", "en-GB") == "My game (UK)"
    assert p.text("description", "en-GB") == p.text("description", "en")
    # A build in en-GB alone still takes en's words for the gaps.
    one = p.variant(None, ["en-GB"])
    assert one.languages == ["en-GB"] and "en" in one.strings


def test_check_finds_words_the_code_uses_that_lang_files_dont_have(tmp_path):
    folder = copy_game("saved", tmp_path)
    with open(os.path.join(folder, "game.js"), "a", encoding="utf-8") as f:
        f.write('\nEduGame.t("not_there"); t("kit.options"); t("title");\n')
    write(folder, "extra.html", '<p data-t="also_missing"></p><input data-t-attr="placeholder:level">')
    assert projects.unknown_keys(projects.load(folder)) == {
        "also_missing": ["extra.html"], "not_there": ["game.js"]}


def test_content_json_becomes_scripts_the_helper_loads(tmp_path):
    folder = copy_game("saved", tmp_path)
    write(folder, "words/en.json", {"words": ["cat", "dog"]})
    write(folder, "words/fr.json", {"words": ["chat", "chien"]})
    write(folder, "notes.json", {"not": "content"})
    edit(folder, lambda d: d.update(content=["words"]))
    p = projects.load(folder)
    out = str(tmp_path / "out")
    build.build_folder(p, out)
    assert not os.path.exists(os.path.join(out, "words", "fr.json"))
    with open(os.path.join(out, "words", "fr.json.js"), encoding="utf-8") as f:
        script = f.read()
    assert 'EduGame._content("words/fr.json", {"words":["chat","chien"]});' in script
    assert os.path.exists(os.path.join(out, "notes.json"))  # not in a content folder

    edit(folder, lambda d: d.update(content=["nowhere"]))
    assert any("nowhere" in x for x in problems(folder))
    write(folder, "words/bad.json", "{oops")
    edit(folder, lambda d: d.update(content=["words"]))
    try:
        build.build_folder(projects.load(folder), str(tmp_path / "out2"))
        assert False, "bad JSON should stop the build"
    except ValueError as e:
        assert "words/bad.json" in str(e)


def packaged(tmp_path):
    folder = copy_game("saved", tmp_path)
    for n in ("01", "02"):
        write(folder, "lessons/%s/en.json" % n, {"text": "Lesson " + n})
        write(folder, "lessons/%s/fr.json" % n, {"text": "Leçon " + n})
    en = json.load(open(os.path.join(folder, "lang", "en.json")))
    fr = json.load(open(os.path.join(folder, "lang", "fr.json")))
    en.update({"package.one": "Lesson one", "package.two": "Lesson two", "package.two_about": "The second lesson."})
    fr.update({"package.one": "Leçon un", "package.two": "Leçon deux", "package.two_about": "La deuxième leçon."})
    write(folder, "lang/en.json", en)
    write(folder, "lang/fr.json", fr)
    edit(folder, lambda d: d.update(content=["lessons"], package_files=["lessons/*"], packages=[
        {"id": "lesson-01", "title": "package.one", "files": ["lessons/01/*"], "config": {"lesson": "01"}},
        {"id": "lesson-02", "title": "package.two", "description": "package.two_about",
         "files": ["lessons/02/*"], "languages": ["fr"]},
    ]))
    return folder


def test_packages_make_several_zips_from_one_folder(tmp_path):
    p = projects.load(packaged(tmp_path))
    out = str(tmp_path / "dist")
    made = sorted(os.path.basename(x) for x in build.build_all(p, out))
    assert made == ["my-game-lesson-01-0.1.0.zip", "my-game-lesson-02-0.1.0.zip"]
    with zipfile.ZipFile(os.path.join(out, made[0])) as z:
        names = z.namelist()
        cfg = z.read("edugame-config.js").decode("utf-8")
        manifest = json.loads(z.read("kolibri-game.json"))
    assert "lessons/01/en.json.js" in names and not any(n.startswith("lessons/02") for n in names)
    assert '"lesson-01"' in cfg
    assert manifest["title"] == "Lesson one"
    two = p.variant("lesson-02")
    assert two.languages == ["fr"] and two.title == "Leçon deux" and two.description == "La deuxième leçon."
    assert two.config()["package"] == {"id": "lesson-02", "title": "package.two", "config": {}}

    # One package, each language on its own.
    made = sorted(os.path.basename(x) for x in build.build_all(p, str(tmp_path / "each"), package="lesson-01", each_language=True))
    assert made == ["my-game-lesson-01-en-0.1.0.zip", "my-game-lesson-01-fr-0.1.0.zip"]
    try:
        p.variant("lesson-09")
        assert False
    except projects.ProjectError as e:
        assert "lesson-09" in str(e.problems)


def test_package_mistakes_are_found(tmp_path):
    folder = packaged(tmp_path)
    edit(folder, lambda d: d["packages"].append({"id": "Lesson 3"}))
    assert any("packages[2]" in x for x in problems(folder))
    edit(folder, lambda d: d.update(packages=[{"id": "a"}, {"id": "a"}]))
    assert any("twice" in x for x in problems(folder))
    edit(folder, lambda d: d.update(packages=[{"id": "a", "languages": ["sw"]}]))
    assert any("languages" in x for x in problems(folder))


def test_a_site_lists_every_package(tmp_path):
    p = projects.load(packaged(tmp_path))
    site = str(tmp_path / "site")
    pages.build_pages(p, site)
    with open(os.path.join(site, "index.html"), encoding="utf-8") as f:
        front = f.read()
    assert 'href="play/lesson-01/"' in front and 'href="play/lesson-02/"' in front
    assert "Lesson one" in front and "Leçon deux" in front and "The second lesson." not in front
    assert os.path.exists(os.path.join(site, "play", "lesson-02", "lessons", "02", "fr.json.js"))
    assert not os.path.exists(os.path.join(site, "play", "lesson-02", "lessons", "01"))


def test_options_settings_are_checked(tmp_path):
    folder = copy_game("scored", tmp_path)
    edit(folder, lambda d: d.update(options={"theme": "dark", "header": False}))
    assert projects.load(folder).config()["options"] == {"theme": "dark", "header": False}
    edit(folder, lambda d: d.update(options={"theme": "purple"}))
    assert any("options" in x for x in problems(folder))
