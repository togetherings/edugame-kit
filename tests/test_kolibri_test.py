"""edugame kolibri-test: the parts that run without Kolibri (CI plays games in a real one)."""
import json
import os
import zipfile

from edugame import build, cli, kolibri_test, project as projects
from tests.helpers import EXAMPLES, TEMPLATES


def test_new_games_come_with_play_steps_that_are_never_shipped(tmp_path):
    for kind in ("saved", "scored"):
        folder = str(tmp_path / kind)
        cli.main(["new", folder, "--type", kind, "--github"])
        play = os.path.join(folder, kolibri_test.PLAY_FILE)
        steps = kolibri_test.load_play(play)
        assert callable(steps.first_visit) and callable(steps.came_back)
        p = projects.load(folder)
        assert kolibri_test.PLAY_FILE not in p.files()
        with zipfile.ZipFile(build.build_zip(p, str(tmp_path / ("dist-" + kind)))) as z:
            assert not any(n.startswith("tests/") for n in z.namelist())
        workflow = open(os.path.join(folder, ".github", "workflows", "build.yml")).read()
        assert "edugame-kit/.github/workflows/game.yml@v" in workflow
        assert "needs: [kit]" in workflow and "name: Checks passed" in workflow


def test_the_examples_play_steps_load():
    steps = kolibri_test.load_play(os.path.join(EXAMPLES, "number-hunt", kolibri_test.PLAY_FILE))
    assert callable(steps.first_visit) and callable(steps.came_back)
    assert kolibri_test.load_play(os.path.join(EXAMPLES, "nowhere", kolibri_test.PLAY_FILE)) is None


def test_the_command_is_there(capsys):
    try:
        cli.main(["kolibri-test", "--help"])
    except SystemExit:
        pass
    assert "--play" in capsys.readouterr().out


def test_the_shell_scripts_are_shipped_with_the_kit():
    for name in ("setup_channel.py", "read_record.py"):
        assert os.path.isfile(os.path.join(kolibri_test.SCRIPTS, name))
    pyproject = open(os.path.join(os.path.dirname(TEMPLATES), "..", "pyproject.toml")).read()
    assert '"kolibri/*"' in pyproject


def record(**cmi):
    out = {"found": True, "progress": 1.0, "status": "passed", "score_raw": None, "exit": "suspend",
           "suspend_data": json.dumps({"_v": 1, "_save": {"level": 3}})}
    out.update(cmi)
    return out


def test_what_kolibri_recorded_is_checked():
    report = kolibri_test.Report()
    assert kolibri_test.check_record(record(), True, report) == {"level": 3}
    assert not report.failures

    for bad in (dict(found=False), dict(suspend_data="x" * 4097), dict(status="completed"),
                dict(score_raw="80"), dict(exit=""), dict(progress=0.0), dict(suspend_data="not json")):
        report = kolibri_test.Report()
        kolibri_test.check_record(record(**bad), True, report)
        assert report.failures, bad

    # Not done yet is fine when the play steps didn't finish the game.
    report = kolibri_test.Report()
    kolibri_test.check_record(record(progress=0.0, status="incomplete"), False, report)
    assert not report.failures


def test_a_game_with_packages_is_played_as_its_packages(tmp_path):
    from tests.test_languages import packaged
    p = projects.load(packaged(tmp_path))
    assert not any(f.startswith("lessons/") for f in p.files())       # what it used to play

    every = kolibri_test.packages_to_play(p)
    assert [i for _, i in every] == ["lesson-01", "lesson-02"]
    assert "lessons/01/en.json" in every[0][0].files() and "lessons/02/fr.json" not in every[0][0].files()
    assert "lessons/02/fr.json" in every[1][0].files() and "lessons/01/en.json" not in every[1][0].files()
    assert [i for _, i in kolibri_test.packages_to_play(p, "ALL")] == ["lesson-01", "lesson-02"]
    assert [i for _, i in kolibri_test.packages_to_play(p, "1")] == ["lesson-01"]
    assert [i for _, i in kolibri_test.packages_to_play(p, 5)] == ["lesson-01", "lesson-02"]
    assert [i for _, i in kolibri_test.packages_to_play(p, package="lesson-02")] == ["lesson-02"]
    for bad in ("0", "-1", "some", ""):
        try:
            kolibri_test.packages_to_play(p, bad)
        except projects.ProjectError as e:
            assert "number" in str(e.problems)
        else:
            assert False, "%r isn't a number of packages" % bad


def test_a_game_without_packages_is_played_as_it_is():
    p = projects.load(os.path.join(EXAMPLES, "number-hunt"))
    assert kolibri_test.packages_to_play(p) == [(p, None)]
    assert kolibri_test.packages_to_play(p, "1") == [(p, None)]
    try:
        kolibri_test.packages_to_play(p, package="lesson-01")
    except projects.ProjectError as e:
        assert "no package" in str(e.problems)
    else:
        assert False, "a game without packages has no lesson-01"


def test_the_build_workflow_passes_how_many_packages_to_play():
    workflow = open(os.path.join(os.path.dirname(TEMPLATES), "..", ".github", "workflows", "game.yml")).read()
    assert "kolibri-packages:" in workflow and '--packages "${{ inputs.kolibri-packages }}"' in workflow
    assert "each-language:" in workflow and "--each-language" in workflow
    assert "browser-tests:" in workflow and "${{ inputs.browser-tests }}" in workflow
    assert "release-bundles:" in workflow and "edugame bundle" in workflow and "bundles/*.zip" in workflow
