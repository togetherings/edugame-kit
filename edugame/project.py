"""
A game folder: its ``edugame.json``, its words in ``lang/``, its content, and its files.

    my-game/
      edugame.json     what the game is (below): no words, only settings
      lang/en.json     EVERY word the game shows in one language, one file per language
      lang/fr.json     (and the kit's words: title, description, score labels, level names)
      words/ maps/ lessons/ ...   content: big things the game plays with, loaded when
                                  needed (see "content" below and docs/LANGUAGES.md)
      index.html       the start page; loads edugame-config.js and edugame.js
      game.js, style.css, icon.svg, ...

A lang file maps keys to words. A value is text, a list of paragraphs, or a
plural set ({"one": "{n} guess", "other": "{n} guesses"}). Keys starting with
"_" aren't words: "_language" ({"name": "Français", "dir": "ltr"}) and
"_notes" (help for translators: {"menu.goal": "shown on a mode button"}).
A regional file, like lang/en-GB.json, only needs the words that differ.

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
      "options": {"theme": "auto", "header": true},   the Options button and panel (see edugame.js)
      "content": ["words", "maps"],      folders of content JSON, loaded when needed
      "packages": [...], "package_files": [...],      several zips from one folder (see packages())
      "authors": ["..."], "license": "MIT"
    }

Packages: a game can be built as several zips, each with part of its content
(SINGE: a zip per set of maps; LIT: a zip per lesson)::

    "package_files": ["lessons/*"],      files only in the packages that list them
    "packages": [
      {"id": "lesson-01", "title": "package.lesson_01", "files": ["lessons/01/*"],
       "config": {"lesson": "01"}, "languages": ["en", "fr"]}
    ]

A package's title and description are words in lang/; its config reaches the
game as EduGame.config.package.config. Every package is the same game (the
same id), so Kolibri Games puts their scores together.

Server Games aren't made with the kit: they need the Kolibri Games plugin's server.
"""
import copy
import fnmatch
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
#: Plural forms a word can have (Unicode CLDR); "other" is always needed.
PLURAL_FORMS = ("zero", "one", "two", "few", "many", "other")
#: Keys with a set meaning in lang/ files (see docs/LANGUAGES.md). "kit." words are the kit's own.
RESERVED_WORDS = ("title", "description", "score_label", "score_unit", "time_label", "plays_label",
                  "level_label", "all_label")
PACKAGE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def matches(path, patterns):
    """True if a path matches one of the patterns ("*" also matches across folders)."""
    return any(fnmatch.fnmatchcase(path, p) or fnmatch.fnmatchcase(path, p.rstrip("/") + "/*") for p in patterns)


def plain(value):
    """A lang value as one piece of text: a list's paragraphs joined, a plural set's "other"."""
    if isinstance(value, list):
        return "\n\n".join(value)
    if isinstance(value, dict):
        return value.get("other", "")
    return value


class ProjectError(Exception):
    def __init__(self, problems):
        Exception.__init__(self, "\n".join(problems))
        self.problems = problems


class Project(object):
    """A checked game folder."""

    def __init__(self, folder, data, strings, package=None):
        self.folder = folder
        self.data = data
        self.strings = strings  # {language: {key: text}}
        self.package = package  # one of packages(), for a package's build
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
        """A word, as text: in ``language`` (or the default), then its base language, then the default."""
        language = language or self.language
        for code in (language, language.split("-")[0], self.language):
            v = self.strings.get(code, {}).get(key)
            if v:
                return plain(v)
        return default

    def packages(self):
        """The game's packages ([] when it's built as one zip)."""
        return self.data.get("packages", [])

    def variant(self, package=None, languages=None):
        """This game as one package and/or in some of its languages (the first is the default)."""
        data = copy.deepcopy(self.data)
        pkg = None
        if package is not None:
            pkg = next((p for p in self.packages() if p["id"] == package), None)
            if pkg is None:
                raise ProjectError(["There's no package '%s' (packages: %s)." % (
                    package, ", ".join(p["id"] for p in self.packages()) or "none")])
            if pkg.get("languages"):
                data["languages"] = [c for c in pkg["languages"] if c in self.languages]
        if languages:
            unknown = [c for c in languages if c not in self.languages]
            if unknown:
                raise ProjectError(["This game isn't in %s (it's in %s)." % (", ".join(unknown), ", ".join(self.languages))])
            data["languages"] = list(languages)
        # Regional files need their base language to fill gaps (en-GB needs en).
        keep = list(data["languages"])
        for code in data["languages"]:
            b = code.split("-")[0]
            if b != code and b in self.strings and b not in keep:
                keep.append(b)
        strings = {c: self.strings[c] for c in keep if c in self.strings}
        if not any(c in strings for c in data["languages"]):
            strings[data["languages"][0]] = self.strings[self.language]
        return Project(self.folder, data, strings, pkg)

    @property
    def score_spec(self):
        """The scoring section in full form (scoring.full), or None for Saved Games."""
        return scorer.full(self.scoring) if self.scoring else None

    def words(self, key, default=""):
        """A word from the default language's lang file: ``key`` itself if it isn't a word there."""
        found = self.text(key)
        if found:
            return found
        if key in scorer.DEFAULT_WORDS:
            return scorer.DEFAULT_WORDS[key] or default
        return key or default

    @property
    def title(self):
        if self.package and self.package.get("title"):
            return self.words(self.package["title"])
        return self.text("title")

    @property
    def description(self):
        if self.package and self.package.get("description"):
            return self.words(self.package["description"])
        return self.text("description")

    @property
    def content_dirs(self):
        return [d.strip("/") for d in self.data.get("content", [])]

    def is_content(self, rel):
        """A content JSON file: the build makes a script of it (file.json.js)."""
        return rel.endswith(".json") and any(rel.startswith(d + "/") for d in self.content_dirs)

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
                # Files that belong to packages are only in the packages that list them.
                only = self.data.get("package_files", [])
                if only and matches(rel, only) and not (self.package and matches(rel, self.package.get("files", []))):
                    continue
                if self.package and matches(rel, self.package.get("exclude", [])):
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
            "color": self.color,
            "options": self.data.get("options", {}),
        }
        if self.package:
            cfg["package"] = {"id": self.package["id"], "title": self.package.get("title") or "title",
                              "config": self.package.get("config", {})}
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
    _check_more(data, folder, problems, languages)
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
        bad = _check_words(words, code)
        if bad:
            problems.extend(bad)
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


def _check_words(words, code):
    """Problems with one lang file."""
    where = "lang/%s.json" % code
    if not isinstance(words, dict):
        return ["%s must hold an object of words." % where]
    out = []
    for key, v in words.items():
        if key == "_language":
            if not isinstance(v, dict) or not isinstance(v.get("name", ""), str) or v.get("dir", "ltr") not in ("ltr", "rtl"):
                out.append('%s: _language must be {"name": "the language in itself", "dir": "ltr" or "rtl"}.' % where)
        elif key == "_notes":
            if not isinstance(v, dict) or not all(isinstance(x, str) for x in v.values()):
                out.append("%s: _notes must map keys to notes for translators." % where)
        elif key.startswith("_"):
            continue  # anything else starting with _ is the game's own, never shown
        elif isinstance(v, str):
            continue
        elif isinstance(v, list):
            if not all(isinstance(x, str) for x in v):
                out.append("%s: %s must be a list of text." % (where, key))
        elif isinstance(v, dict):
            if "other" not in v or not all(k in PLURAL_FORMS and isinstance(x, str) for k, x in v.items()):
                out.append('%s: %s must be text, a list, or plural forms like {"one": ..., "other": ...}.' % (where, key))
        else:
            out.append("%s: %s must be text, a list of text, or plural forms." % (where, key))
    return out


def _check_more(data, folder, problems, languages):
    """The options, content and packages sections."""
    options = data.get("options", {})
    if not isinstance(options, dict) or options.get("theme", "auto") not in ("auto", "light", "dark") \
            or not isinstance(options.get("header", True), bool):
        problems.append('options must be like {"theme": "auto" (or "light", "dark"), "header": true}.')
    content = data.get("content", [])
    if not isinstance(content, list) or not all(isinstance(d, str) and d and ".." not in d.split("/") for d in content):
        problems.append('content must list folders inside the game, like ["words", "maps"].')
    else:
        for d in content:
            if not os.path.isdir(os.path.join(folder, d)):
                problems.append("content: the folder %s isn't in the game." % d)
    only = data.get("package_files", [])
    if not isinstance(only, list) or not all(isinstance(x, str) for x in only):
        problems.append('package_files must list file patterns, like ["maps/*"].')
    packages = data.get("packages", [])
    if not isinstance(packages, list):
        problems.append("packages must be a list.")
        return
    seen = set()
    for i, p in enumerate(packages):
        where = "packages[%d]" % i
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not PACKAGE_ID_RE.match(p["id"]):
            problems.append("%s needs an id: lower-case letters, digits and -." % where)
            continue
        if p["id"] in seen:
            problems.append("%s: the id '%s' is used twice." % (where, p["id"]))
        seen.add(p["id"])
        for key in ("files", "exclude", "languages"):
            if key in p and not (isinstance(p[key], list) and all(isinstance(x, str) for x in p[key])):
                problems.append("%s.%s must be a list." % (where, key))
        if [c for c in p.get("languages", []) if c not in languages]:
            problems.append("%s.languages must be some of the game's languages." % where)
        if "config" in p and not isinstance(p["config"], dict):
            problems.append("%s.config must be an object." % where)


def missing_strings(project):
    """{language: [keys]} for words that the default language has and another doesn't.

    A regional language (en-GB) whose base language (en) is in the game only
    needs the words that differ, so it's never missing anything.
    """
    default = project.strings[project.language]
    out = {}
    for code in project.languages[1:]:
        if "-" in code and code.split("-")[0] in project.strings:
            continue
        missing = sorted(k for k in default if not k.startswith("_") and k not in project.strings.get(code, {}))
        if missing:
            out[code] = missing
    return out


KEY_PATTERNS = [
    re.compile(r"""(?:EduGame\.t|EduGame\.lines|\bt)\(\s*["']([A-Za-z0-9_.-]+)["']"""),
    re.compile(r"""data-t=["']([A-Za-z0-9_.-]+)["']"""),
    re.compile(r"""data-t-attr=["']([^"']+)["']"""),
]


def used_keys(project):
    """Words the game's code and pages use by name ({key: [files]}). Keys built in code
    (like "mode." + name) can't be found this way."""
    found = {}
    for rel in project.files():
        if not rel.endswith((".js", ".html")) or rel in GENERATED:
            continue
        with open(os.path.join(project.folder, rel), encoding="utf-8", errors="replace") as f:
            text = f.read()
        for i, pat in enumerate(KEY_PATTERNS):
            for m in pat.finditer(text):
                keys = [pair.split(":")[-1].strip() for pair in m.group(1).split(",")] if i == 2 else [m.group(1)]
                for k in keys:
                    found.setdefault(k, []).append(rel)
    return found


def unknown_keys(project):
    """{key: [files]}: words the code uses that no lang file has (in the default language)."""
    have = set(project.strings[project.language])
    return {k: sorted(set(v)) for k, v in used_keys(project).items()
            if k not in have and not k.startswith("kit.") and k not in RESERVED_WORDS}
