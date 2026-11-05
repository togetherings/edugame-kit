import json
import os

import pytest

from edugame import project as projects
from tests.helpers import GAMES, copy_game


def edit(folder, **changes):
    path = os.path.join(folder, "edugame.json")
    data = json.load(open(path))
    for k, v in changes.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    json.dump(data, open(path, "w"))


def problems(folder):
    with pytest.raises(projects.ProjectError) as e:
        projects.load(folder)
    return " ".join(e.value.problems)


def test_examples_and_templates_are_valid_and_fully_translated():
    for folder in GAMES:
        p = projects.load(folder)
        assert p.type in ("saved", "scored") and p.title
        assert projects.missing_strings(p) == {}, folder
        assert "lang/en.json" not in p.files() and "edugame.json" not in p.files()


def test_the_type_decides_scoring(tmp_path):
    folder = copy_game("saved", tmp_path)
    edit(folder, type="server")
    assert "Server Games are made for the Kolibri Games plugin" in problems(folder)
    edit(folder, type="saved", scoring={"order": "asc"})
    assert "Saved Games don't keep scores" in problems(folder)
    edit(folder, type="scored", scoring=None)
    assert "Scored Games need a scoring section" in problems(folder)
    edit(folder, scoring={"order": "up", "grade": {"full": 1, "zero": 1}})
    found = problems(folder)
    assert "scoring.order" in found and "scoring.grade" in found


def test_languages_need_their_words(tmp_path):
    folder = copy_game("scored", tmp_path)
    edit(folder, languages=["en", "sw"])
    assert "lang/sw.json is missing" in problems(folder)
    edit(folder, languages=["EN"])
    assert "languages must list language codes" in problems(folder)
    edit(folder, languages=["fr", "en"])
    p = projects.load(folder)
    assert p.language == "fr" and p.title == "Mon jeu"
    with open(os.path.join(folder, "lang", "en.json"), "w") as f:
        json.dump({"title": "My game"}, f)
    assert "en" in projects.missing_strings(projects.load(folder))


def test_the_start_page_loads_the_helper_and_generated_files_arent_kept(tmp_path):
    folder = copy_game("saved", tmp_path)
    page = os.path.join(folder, "index.html")
    open(page, "w").write("<p>no scripts</p>")
    open(os.path.join(folder, "imsmanifest.xml"), "w").write("<x/>")
    found = problems(folder)
    assert "must load edugame.js" in found and "Remove imsmanifest.xml" in found


def test_kolibri_manifest_takes_words_from_the_default_language():
    p = projects.load(os.path.join(os.path.dirname(GAMES[0]), "number-hunt"))
    m = p.kolibri_manifest()
    assert m["type"] == "scored" and m["title"] == "Number Hunt" and m["languages"] == ["en", "fr"]
    assert m["scoring"]["label"] == "Guesses" and m["scoring"]["unit"] == "guesses"
    assert "grade" not in m["scoring"]  # only for learning systems
    assert m["settings"][0]["key"] == "max"


def test_kolibri_games_accepts_every_kit_manifest():
    mf = pytest.importorskip("kolibri_games.manifest")
    for folder in GAMES:
        m = mf.validate(projects.load(folder).kolibri_manifest())
        assert m.in_channels
        if m.type == "scored":
            # In a channel, the plugin reads the kit's board "main" with the scoreboard built from scoring.
            assert [f["key"] for f in m.channel_spec["fields"]][:2] == ["score", "time"]
