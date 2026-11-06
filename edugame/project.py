"""
A game folder: its ``edugame.json``, its translations in ``lang/``, and its files.

    my-game/
      edugame.json     what the game is (below)
      lang/en.json     its words, one file per language: {"title": "...", "description": "...", ...}
      index.html       the start page; loads edugame-config.js and edugame.js
      game.js, style.css, icon.svg, ...

edugame.json::

    {
      "format": 1,
      "type": "scored",                  "saved" or "scored"
      "id": "org.example.number-hunt",   never changes
      "version": "1.0.0",
      "languages": ["en", "fr"],         the first is the default; each needs lang/<code>.json
      "icon": "icon.svg", "color": "#2f6f8f",
      "scoring": {"order": "asc", "tiebreak": "seconds", "min": 1, "max": 1000},   (see scoring.py)
      "settings": [...],                 options coaches can change in Kolibri Games
      "authors": ["..."], "license": "MIT"
    }

Server Games aren't made with the kit: they need the Kolibri Games plugin's server.
"""
import json
import os
import re

from . import FORMAT, scoring as scorer

TYPES = ("saved", "scored")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,99}$")
VERSION_RE = re.compile(r"^\d+(\.\d+){0,3}([.-][0-9A-Za-z.]+)?$")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
#: Words every game needs in its default language.
REQUIRED_STRINGS = ("title",)
#: Files the build makes; a game folder mustn't have its own.
GENERATED = ("edugame.js", "edugame-config.js", "kolibri-game.json", "imsmanifest.xml", "rachel-index.php")
#: Left out of builds.
SKIP_NAMES = {".git", ".DS_Store", "Thumbs.db", "__pycache__", "node_modules", "dist", ".github"}
#: SCORM 1.2 suspend_data is at most 4096 characters; see runtime/edugame.js.
MAX_SAVE = 3900


class ProjectError(Exception):
    def __init__(self, problems):
        Exception.__init__(self, "\n".join(problems))
        self.problems = problems


class Project(object):
    """A checked game folder."""

    def __init__(self, folder, data, strings):
        self.folder = folder
        self.data = data
        self.strings = strings  # {language: {key: text}}
        self.type = data["type"]
        self.id = data["id"]
        self.version = data["version"]
        self.languages = data["languages"]
        self.language = self.languages[0]
        self.scoring = data.get("scoring")
        self.settings = data.get("settings", [])
        self.entry = data.get("entry", "index.html")
        self.icon = data.get("icon")
        self.color = data.get("color", "#3b6e8f")
        self.authors = data.get("authors", [])
        self.license = data.get("license", "")

    def text(self, key, language=None, default=""):
        return self.strings.get(language or self.language, {}).get(key) or self.strings[self.language].get(key, default)

    @property
    def score_spec(self):
        """The scoring section in full form (scoring.full), or None for Saved Games."""
        return scorer.full(self.scoring) if self.scoring else None

    def words(self, key, default=""):
        """A word from the default language's lang file: ``key`` itself if it isn't a word there."""
        found = self.strings[self.language].get(key)
        if found:
            return found
        if key in scorer.DEFAULT_WORDS:
            return scorer.DEFAULT_WORDS[key] or default
        return key or default

    @property
    def title(self):
        return self.text("title")

    @property
    def description(self):
        return self.text("description")

    @property
    def slug(self):
        """A short name for folders and files: the last part of the id."""
        return re.sub(r"[^a-z0-9-]+", "-", self.id.split(".")[-1]).strip("-") or "game"

    def files(self):
        """Every file to ship, as paths relative to the folder (generated files excluded), sorted."""
        out = []
        for root, dirs, names in os.walk(self.folder):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_NAMES and not d.startswith("."))
            for name in sorted(names):
                if name in SKIP_NAMES or name.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, name), self.folder).replace(os.sep, "/")
                # lang/ goes into edugame-config.js, so the files themselves aren't needed.
                if rel in GENERATED or rel == "edugame.json" or rel.startswith("lang/"):
                    continue
                out.append(rel)
        return out

    def config(self):
        """What edugame.js needs, written to edugame-config.js."""
        cfg = {
            "id": self.id,
            "type": self.type,
            "version": self.version,
            "languages": self.languages,
            "strings": self.strings,
        }
        if self.scoring:
            cfg["scoring"] = scorer.helper(self.score_spec, self.words)
        if self.settings:
            cfg["settings"] = [{"key": s["key"], "default": s["default"]} for s in self.settings]
        return cfg

    def kolibri_manifest(self):
        """kolibri-game.json for the Kolibri Games plugin (see its docs/GAME_FORMAT.md)."""
        m = {
            "format": 1,
            "type": self.type,
            "id": self.id,
            "version": self.version,
            "title": self.title[:100],
            "description": self.description,
            "entry": self.entry,
            "language": self.language,
            "languages": self.languages,
            "requires_platform": ">=0.2",
            "color": self.color,
            "authors": self.authors,
            "license": self.license,
        }
        if self.icon:
            m["icon"] = self.icon
        if self.scoring:
            m["scoring"] = scorer.kolibri(self.score_spec, self.words)
        if self.settings:
            m["settings"] = self.settings
        return m


def _check_settings(settings, problems):
    if not isinstance(settings, list):
        problems.append("settings must be a list.")
        return
    seen = set()
    for i, s in enumerate(settings):
        where = "settings[%d]" % i
        if not isinstance(s, dict) or not re.match(r"^[a-z][a-z0-9_]{0,39}$", str(s.get("key", ""))):
            problems.append("%s needs a key made of lower-case letters, digits or _." % where)
            continue
        if s["key"] in seen:
            problems.append("%s: the key '%s' is used twice." % (where, s["key"]))
        seen.add(s["key"])
        if s.get("type") not in ("integer", "number", "boolean", "choice", "text"):
            problems.append("%s.type must be integer, number, boolean, choice or text." % where)
        if "default" not in s or not s.get("label"):
            problems.append("%s needs a label and a default." % where)


def load(folder):
    """Read and check a game folder. Raises ProjectError with every problem found."""
    folder = os.path.abspath(folder)
    path = os.path.join(folder, "edugame.json")
    if not os.path.isfile(path):
        raise ProjectError(["There's no edugame.json in %s. Start a game with: edugame new <folder>" % folder])
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        raise ProjectError(["edugame.json isn't valid JSON: %s" % e])
    problems = []
    if not isinstance(data, dict):
        raise ProjectError(["edugame.json must hold an object."])
    if data.get("format") != FORMAT:
        problems.append("format must be %d." % FORMAT)
    if data.get("type") not in TYPES:
        problems.append("type must be 'saved' or 'scored'. (Server Games are made for the Kolibri Games plugin, not with the kit.)")
    if not isinstance(data.get("id"), str) or not ID_RE.match(data["id"]):
        problems.append("id must be 3-100 lower-case letters, digits, '.', '_' or '-' (e.g. org.example.my-game).")
    if not isinstance(data.get("version"), str) or not VERSION_RE.match(data["version"]):
        problems.append("version must look like 1.0.0.")
    languages = data.get("languages", ["en"])
    data["languages"] = languages
    if not isinstance(languages, list) or not languages or not all(isinstance(c, str) and LANG_RE.match(c) for c in languages):
        problems.append("languages must list language codes like 'en' or 'pt-BR', the default first.")
        languages = []
    if data.get("type") == "scored":
        if "scoring" not in data:
            problems.append("Scored Games need a scoring section (is a lower or higher score better?).")
        else:
            scorer.check(data["scoring"], problems)
    elif "scoring" in data:
        problems.append("Saved Games don't keep scores, so they can't have scoring. Use type 'scored'.")
    if "settings" in data:
        _check_settings(data["settings"], problems)
    if "color" in data and not (isinstance(data["color"], str) and COLOR_RE.match(data["color"])):
        problems.append("color must look like #3b6e8f.")
    for key in ("entry", "icon"):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or value.startswith("/") or ".." in value.split("/")):
            problems.append("%s must be a path inside the game folder." % key)
        elif value is not None and not os.path.isfile(os.path.join(folder, value)):
            problems.append("%s: %s isn't in the game folder." % (key, value))
    entry = data.get("entry", "index.html")
    if not os.path.isfile(os.path.join(folder, entry)):
        problems.append("The start page %s isn't in the game folder." % entry)
    else:
        with open(os.path.join(folder, entry), encoding="utf-8", errors="replace") as f:
            page = f.read()
        for script in ("edugame-config.js", "edugame.js"):
            if script not in page:
                problems.append('%s must load %s: <script src="%s"></script>' % (entry, script, script))
    pages_cfg = data.get("pages", {})
    if not isinstance(pages_cfg, dict) or not isinstance(pages_cfg.get("goatcounter", ""), str):
        problems.append('pages must be {"goatcounter": "your-code"} (for the GitHub Pages site only).')
    for name in GENERATED:
        if os.path.exists(os.path.join(folder, name)):
            problems.append("Remove %s from the game folder: the build makes it." % name)

    strings = {}
    for code in languages:
        lang_path = os.path.join(folder, "lang", code + ".json")
        if not os.path.isfile(lang_path):
            problems.append("lang/%s.json is missing (every language in 'languages' needs one)." % code)
            continue
        try:
            with open(lang_path, encoding="utf-8") as f:
                words = json.load(f)
        except ValueError as e:
            problems.append("lang/%s.json isn't valid JSON: %s" % (code, e))
            continue
        if not isinstance(words, dict) or not all(isinstance(v, str) for v in words.values()):
            problems.append("lang/%s.json must map keys to text." % code)
            continue
        strings[code] = words
    if languages and languages[0] in strings:
        default = strings[languages[0]]
        for key in REQUIRED_STRINGS:
            if not default.get(key):
                problems.append("lang/%s.json needs a %s." % (languages[0], key))
    if problems:
        raise ProjectError(problems)
    return Project(folder, data, strings)


def missing_strings(project):
    """{language: [keys]} for words that the default language has and another doesn't."""
    default = project.strings[project.language]
    out = {}
    for code in project.languages[1:]:
        missing = sorted(k for k in default if k not in project.strings.get(code, {}))
        if missing:
            out[code] = missing
    return out
