"""
Moves the kit to a new version everywhere it's named:

    python tools/bump_version.py 0.3.1

__version__ in edugame/__init__.py, KIT_REF in the workflows games call (game.yml,
game-pages.yml), and the "@v..." in the starter's workflows. Then add the CHANGELOG entry
(## 0.3.1) and publish the release with the tag v0.3.1. Standard library only.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [
    ("edugame/__init__.py", r'(__version__ = ")[^"]+(")', r"\g<1>{v}\g<2>"),
    (".github/workflows/game.yml", r"(^  KIT_REF: v)\S+", r"\g<1>{v}"),
    (".github/workflows/game-pages.yml", r"(^  KIT_REF: v)\S+", r"\g<1>{v}"),
    ("edugame/templates/github/build.yml", r"(edugame-kit/\.github/workflows/game\.yml@v)\S+", r"\g<1>{v}"),
    ("edugame/templates/github/pages.yml", r"(edugame-kit/\.github/workflows/game-pages\.yml@v)\S+", r"\g<1>{v}"),
]


def bump(version):
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        sys.exit("Give the new version like 0.3.1")
    for rel, pattern, repl in FILES:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new, n = re.subn(pattern, repl.format(v=version), text, flags=re.M)
        if not n:
            sys.exit("Couldn't find the version in " + rel)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print("%s: %d" % (rel, n))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    bump(sys.argv[1])
