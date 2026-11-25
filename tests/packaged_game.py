"""
Makes a game with packages, for the Real Kolibri job in .github/workflows/ci.yml: the Saved Game
starter, built as two zips (lesson-01, and lesson-02 in French only), like LIT's lessons and
SINGE's maps. edugame kolibri-test must play each package's zip, with its own files.

    python -m tests.packaged_game FOLDER
"""
import os
import sys

from tests.test_languages import packaged


def main(folder):
    made = packaged(os.path.dirname(os.path.abspath(folder)) or ".")
    if os.path.abspath(made) != os.path.abspath(folder):
        os.rename(made, folder)
    print("Made %s, a game with two packages." % folder)


if __name__ == "__main__":
    main(sys.argv[1])
