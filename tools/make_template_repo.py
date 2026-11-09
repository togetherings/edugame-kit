"""
Makes the files of the template repository (github.com/togetherings/edugame-template):
the starter game from "edugame new --github", and the README in tools/template-repo/.

    python tools/make_template_repo.py OUT_FOLDER

The workflow .github/workflows/template.yml runs this whenever the starter changes on main,
and pushes the result to the template repository. Standard library only.
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from edugame import cli  # noqa: E402


def make(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    cli.main(["new", out, "--github", "--id", "org.example.my-game", "--title", "My game"])
    shutil.copy(os.path.join(ROOT, "tools", "template-repo", "README.md"), os.path.join(out, "README.md"))
    # The README is for the repository, not part of the game's zips.
    path = os.path.join(out, "edugame.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["exclude"] = ["README.md"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    make(sys.argv[1])
