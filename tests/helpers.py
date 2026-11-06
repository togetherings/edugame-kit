import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples")
TEMPLATES = os.path.join(ROOT, "edugame", "templates")
GAMES = [os.path.join(EXAMPLES, n) for n in sorted(os.listdir(EXAMPLES))] + \
        [os.path.join(TEMPLATES, n) for n in ("saved", "scored")]


def copy_game(name, tmp_path):
    """A copy of an example or template, to change in a test."""
    src = os.path.join(EXAMPLES, name) if os.path.isdir(os.path.join(EXAMPLES, name)) else os.path.join(TEMPLATES, name)
    dst = os.path.join(str(tmp_path), name)
    shutil.copytree(src, dst)
    return dst
