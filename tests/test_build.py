import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile

import pytest

from edugame import build, platforms, project as projects
from tests.helpers import EXAMPLES, GAMES, copy_game


def number_hunt():
    return projects.load(os.path.join(EXAMPLES, "number-hunt"))


def config_of(text):
    return json.loads(re.search(r"window\.EDUGAME_CONFIG = (.*);\s*$", text, re.S).group(1))


def test_the_universal_zip_has_every_platforms_files(tmp_path):
    p = number_hunt()
    path = build.build_zip(p, str(tmp_path))
    assert os.path.basename(path) == "number-hunt-1.0.0.zip"
    names = build.zip_names(path)
    for name in ("index.html", "game.js", "edugame.js", "edugame-config.js", "kolibri-game.json", "imsmanifest.xml", "rachel-index.php"):
        assert name in names, name
    assert not any(n.startswith("lang/") or n == "edugame.json" or "/" in n and n.endswith("/") for n in names)
    cfg = config_of(build.read_zip(path, "edugame-config.js").decode())
    assert cfg["id"] == p.id and cfg["languages"] == ["en", "fr"] and cfg["strings"]["fr"]["title"] == "Chasse au nombre"
    assert cfg["settings"] == [{"key": "max", "default": 100}] and cfg["scoring"]["grade"] == {"full": 1, "zero": 20}


def test_building_twice_gives_the_same_zip(tmp_path):
    a = open(build.build_zip(number_hunt(), str(tmp_path / "a")), "rb").read()
    b = open(build.build_zip(number_hunt(), str(tmp_path / "b")), "rb").read()
    assert a == b


def test_scorm_manifest_lists_every_file():
    p = number_hunt()
    files = sorted(set(p.files()) | set(build.generated(p)))
    root = ET.fromstring(build.generated(p)["imsmanifest.xml"].encode())
    ns = {"c": "http://www.imsproject.org/xsd/imscp_rootv1p1p2", "a": "http://www.adlnet.org/xsd/adlcp_rootv1p2"}
    assert root.find("c:metadata/c:schemaversion", ns).text == "1.2"
    res = root.find("c:resources/c:resource", ns)
    assert res.get("href") == "index.html" and res.get("{http://www.adlnet.org/xsd/adlcp_rootv1p2}scormtype") == "sco"
    assert sorted(f.get("href") for f in res.findall("c:file", ns)) == files
    assert root.find("c:organizations/c:organization/c:title", ns).text == "Number Hunt"


def test_rachel_index_links_the_game_in_its_folder():
    text = platforms.rachel_index(number_hunt())
    assert '<a href="<?php echo $dir ?>/index.html">Number Hunt</a>' in text
    assert 'src="<?php echo $dir ?>/icon.svg"' in text


def test_sugarizer_activity(tmp_path):
    p = number_hunt()
    path = build.build_sugarizer(p, str(tmp_path))
    names = build.zip_names(path)
    assert all(n.startswith("NumberHunt.activity/") for n in names)
    assert "NumberHunt.activity/activity/activity.info" in names and "NumberHunt.activity/activity/activity-icon.svg" in names
    assert "NumberHunt.activity/imsmanifest.xml" not in names
    info = build.read_zip(path, "NumberHunt.activity/activity/activity.info").decode()
    assert "bundle_id = org.togetherings.number-hunt" in info and "activity_version = 10000" in info
    assert "exec = sugar-activity-web" in info
    cfg = config_of(build.read_zip(path, "NumberHunt.activity/edugame-config.js").decode())
    assert cfg["sugarizer"] is False  # no sugar-web, so saves stay in the browser


def test_sugarizer_with_sugar_web_saves_to_the_journal(tmp_path):
    lib = tmp_path / "lib"
    (lib / "sugar-web" / "activity").mkdir(parents=True)
    (lib / "require.js").write_text("// require")
    (lib / "sugar-web" / "activity" / "activity.js").write_text("// activity")
    path = build.build_sugarizer(number_hunt(), str(tmp_path / "out"), str(lib))
    names = build.zip_names(path)
    assert "NumberHunt.activity/lib/require.js" in names and "NumberHunt.activity/lib/sugar-web/activity/activity.js" in names
    page = build.read_zip(path, "NumberHunt.activity/index.html").decode()
    assert page.index("lib/require.js") < page.index("edugame-config.js") < page.index('src="edugame.js"')
    assert config_of(build.read_zip(path, "NumberHunt.activity/edugame-config.js").decode())["sugarizer"] is True
    with pytest.raises(ValueError):
        build.build_sugarizer(number_hunt(), str(tmp_path / "out"), str(tmp_path))


def test_small_helpers():
    assert platforms.sugar_version("1.2.3") == 10203 and platforms.sugar_version("0.10") == 1000
    png = platforms.solid_png("#2f6f8f")
    assert png.startswith(b"\x89PNG") and png[16:24] == b"\x00\x00\x00\x30\x00\x00\x00\x30"
    p = number_hunt()
    assert platforms.zim_languages(p) == "eng,fra"
    assert "NumberHunt" == platforms.activity_folder_name(p)


def test_zim_for_kiwix(tmp_path):
    reader = pytest.importorskip("libzim.reader")
    path = build.build_zim(number_hunt(), str(tmp_path))
    zim = reader.Archive(path)
    main = zim.main_entry
    while main.is_redirect:
        main = main.get_redirect_entry()
    assert main.path == "index.html"
    assert bytes(zim.get_entry_by_path("edugame.js").get_item().content).startswith(b"/* EduGame")
    assert bytes(zim.get_metadata("Language")).decode() == "eng,fra"
    assert not zim.has_entry_by_path("imsmanifest.xml")


def test_kolibri_games_installs_the_zip(tmp_path):
    pack = pytest.importorskip("kolibri_games.pack")
    from kolibri_games.sources import ZipSource

    for folder in GAMES:
        path = build.build_zip(projects.load(folder), str(tmp_path))
        manifest, found = pack.verify(ZipSource(path))
        assert found == [], (folder, found)


def test_kolibri_games_reads_scores_the_helper_saves():
    channel = pytest.importorskip("kolibri_games.channel")
    from kolibri_games import manifest as mf

    m = mf.validate(number_hunt().kolibri_manifest())
    # What edugame.js puts in cmi.suspend_data after two rounds.
    saved = {"SCORM": {"cmi": {"suspend_data": json.dumps({"_v": 1, "_save": None, "main": [7, 21.4, 2]})}}}
    assert channel.read_boards(m.channel_spec, saved) == {"main": {"score": 7, "time": 21.4, "plays": 2}}


def test_new_game_from_a_template(tmp_path):
    from edugame import cli

    folder = str(tmp_path / "star-steps")
    cli.main(["new", folder, "--type", "scored"])
    p = projects.load(folder)
    assert p.id == "org.example.star-steps" and p.title == "Star steps" and p.type == "scored"
    cli.main(["translate", folder, "sw"])
    p = projects.load(folder)
    assert p.languages == ["en", "fr", "sw"] and p.strings["sw"]["title"] == "Star steps"
    copy = copy_game("saved", tmp_path)
    cli.main(["build", copy, "-o", str(tmp_path / "dist"), "--sugarizer"])
    assert sorted(os.listdir(str(tmp_path / "dist"))) == ["my-game-0.1.0-sugarizer.zip", "my-game-0.1.0.zip"]
