"""
A Scored Game's ``scoring`` section in edugame.json: what its scores are, how
they're ranked, and its levels. Standard library only.

The short form is for games with one score::

    "scoring": {
      "order": "asc",          lower is better ("desc": higher is better)
      "tiebreak": "seconds",   a faster round wins a tie ("none": no time at all)
      "counts": "first",       which round counts: first, best, latest or total
      "min": 1, "max": 1000,   impossible scores are refused (Kolibri Games)
      "grade": {"full": 1, "zero": 20}   learning systems' gradebooks (not Kolibri)
    }

Its score is called by the words "score_label" and "score_unit" in lang/.

The full form is for anything else: several scores, each ranked its own way,
and levels with a scoreboard each (and one for the whole game)::

    "scoring": {
      "fields": [
        {"key": "acc", "label": "accuracy", "unit": "%", "order": "desc", "total": "average"},
        {"key": "wpm", "label": "speed", "unit": "wpm", "order": "desc", "total": "average"},
        {"key": "plays", "label": "times_played", "source": "plays"}
      ],
      "rank_by": ["acc", "wpm"],       the first ranks; the next ones break ties
      "counts": "best",
      "boards": {"label": "lesson", "names": {"en-01": "lesson_1"}, "total": {"label": "all_lessons"}},
      "grade": {"field": "acc", "full": 100, "zero": 50}
    }

``label``, ``unit`` and board names are keys in lang/<code>.json (so they're
translated); if a language doesn't have the key, the text itself is used.

Each field's ``source`` is "game" (the game reports it), "time" (the helper or
Kolibri Games times the round) or "plays" (how many rounds were finished).
``total`` says how values add up when every round counts ("counts": "total")
and on the total scoreboard: sum, average, min, max, best or latest.

``full()`` turns either form into the full form. ``kolibri()`` turns that into
the Kolibri Games plugin's ``scoring`` (see its docs/SCORING.md): the same
thing, with the words in the default language, and no ``saved_data``, because
the helper saves each board the kit's way: a list of the fields' values, in
``fields`` order.
"""
import re

COUNTS = ("first", "best", "latest", "total")
TOTALS = ("sum", "average", "min", "max", "best", "latest")
SOURCES = ("game", "time", "plays")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
BOARD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$")
MAX_FIELDS = 8
MAX_RANK_BY = 4


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _short(s):
    """The fields of the short form: score, the time (when it breaks ties), and times played."""
    fields = [{"key": "score", "label": "score_label", "unit": "score_unit", "order": s.get("order"),
               "min": s.get("min"), "max": s.get("max"), "decimals": s.get("decimals", 0), "total": s.get("total", "sum")}]
    rank_by = ["score"]
    if s.get("tiebreak", "seconds") == "seconds":
        fields.append({"key": "time", "label": "time_label", "source": "time", "order": "asc", "total": "sum"})
        rank_by.append("time")
    fields.append({"key": "plays", "label": "plays_label", "source": "plays"})
    return fields, rank_by


def check(scoring, problems):
    """Check a scoring section; adds to ``problems``."""
    full(scoring, problems)


def full(scoring, problems=None):
    """The scoring section in full form (see the module docstring)."""
    problems = [] if problems is None else problems
    if not isinstance(scoring, dict):
        problems.append("scoring must be an object.")
        return None
    if "fields" in scoring:
        raw, rank_by = scoring.get("fields"), scoring.get("rank_by")
        if "order" in scoring or "tiebreak" in scoring:
            problems.append("scoring: with fields, give each field its own order and list rank_by (leave out order and tiebreak).")
    else:
        if scoring.get("order") not in ("asc", "desc"):
            problems.append("scoring.order must be 'asc' (lower is better) or 'desc' (higher is better).")
        if scoring.get("tiebreak", "seconds") not in ("seconds", "none"):
            problems.append("scoring.tiebreak must be 'seconds' (faster wins ties) or 'none' (no time).")
        raw, rank_by = _short(scoring)
    if not isinstance(raw, list) or not 0 < len(raw) <= MAX_FIELDS:
        problems.append("scoring.fields must list 1 to %d scores." % MAX_FIELDS)
        raw = []
    fields, keys = [], {}
    for i, f in enumerate(raw):
        where = "scoring.fields[%d]" % i
        if not isinstance(f, dict):
            problems.append("%s must be an object." % where)
            continue
        key = f.get("key")
        if not isinstance(key, str) or not KEY_RE.match(key) or key == "boards":
            problems.append("%s.key must be lower_case letters, digits or _ (and not 'boards')." % where)
            continue
        if key in keys:
            problems.append("%s: the key '%s' is used twice." % (where, key))
        if f.get("order") not in (None, "asc", "desc"):
            problems.append("%s.order must be 'asc' or 'desc'." % where)
        if f.get("source", "game") not in SOURCES:
            problems.append("%s.source must be game, time or plays." % where)
        if f.get("total", "sum") not in TOTALS:
            problems.append("%s.total must be one of %s." % (where, ", ".join(TOTALS)))
        for bound in ("min", "max"):
            if f.get(bound) is not None and not _number(f[bound]):
                problems.append("%s.%s must be a number." % (where, bound))
        if not isinstance(f.get("label", key), str):
            problems.append("%s.label must be text (or a word in lang/)." % where)
        clean = {
            "key": key,
            "label": f.get("label", key),
            "unit": f.get("unit", ""),
            "order": f.get("order"),
            "source": f.get("source", "game"),
            "total": f.get("total", "sum"),
            "decimals": f.get("decimals", 0),
            "seconds": bool(f.get("seconds", f.get("source") == "time")),
            "min": f.get("min"),
            "max": f.get("max"),
        }
        keys[key] = clean
        fields.append(clean)
    if not isinstance(rank_by, list) or not 0 < len(rank_by) <= MAX_RANK_BY:
        problems.append("scoring.rank_by must list 1 to %d fields: the first ranks, the next ones break ties." % MAX_RANK_BY)
        rank_by = []
    for k in rank_by:
        if k not in keys:
            problems.append("scoring.rank_by: '%s' isn't one of the fields." % k)
        elif not keys[k]["order"]:
            problems.append("scoring.rank_by: give the field '%s' an order." % k)
    if rank_by and rank_by[0] in keys and keys[rank_by[0]]["source"] != "game":
        problems.append("scoring.rank_by: the first field must be one the game reports.")
    counts = scoring.get("counts", "first")
    if counts not in COUNTS:
        problems.append("scoring.counts must be one of %s." % ", ".join(COUNTS))
    boards = scoring.get("boards")
    if boards is not None:
        if not isinstance(boards, dict):
            problems.append("scoring.boards must be an object.")
            boards = None
        else:
            names = boards.get("names", {})
            if not isinstance(names, dict) or not all(isinstance(k, str) and BOARD_RE.match(k) and isinstance(v, str)
                                                      for k, v in names.items()):
                problems.append("scoring.boards.names must map level ids (letters, digits, '.', '_', ':', '-') to names.")
                names = {}
            total = boards.get("total")
            if total is True:
                total = {}
            if total not in (None, False) and not isinstance(total, dict):
                problems.append("scoring.boards.total must be true or an object.")
                total = None
            boards = {"label": boards.get("label", "level_label"), "names": names,
                      "total": total if isinstance(total, dict) else None}
    grade = scoring.get("grade")
    if grade is not None:
        primary = rank_by[0] if rank_by else None
        gfield = grade.get("field", primary) if isinstance(grade, dict) else None
        if not (isinstance(grade, dict) and _number(grade.get("full")) and _number(grade.get("zero"))
                and grade["full"] != grade["zero"] and gfield in keys):
            problems.append("scoring.grade must be {\"full\": the score for 100%, \"zero\": the score for 0%}, "
                            "with an optional \"field\".")
            grade = None
        else:
            grade = {"field": gfield, "full": grade["full"], "zero": grade["zero"]}
    return {
        "fields": fields,
        "rank_by": list(rank_by),
        "counts": counts,
        "boards": boards,
        "grade": grade,
        "primary": rank_by[0] if rank_by else None,
    }


def kolibri(spec, words):
    """The Kolibri Games plugin's scoring section. ``words(key, default)`` gives text in the default language."""
    fields = []
    for f in spec["fields"]:
        out = {"key": f["key"], "label": words(f["label"], _default_label(f)), "source": f["source"], "total": f["total"]}
        unit = words(f["unit"], "") if f["unit"] and f["unit"] not in ("%",) else f["unit"]
        if unit:
            out["unit"] = unit
        for k in ("order", "min", "max"):
            if f[k] is not None:
                out[k] = f[k]
        if f["decimals"]:
            out["decimals"] = f["decimals"]
        if f["seconds"]:
            out["seconds"] = True
        fields.append(out)
    m = {"fields": fields, "rank_by": spec["rank_by"], "counts": spec["counts"]}
    if spec["boards"]:
        b = spec["boards"]
        boards = {"label": words(b["label"], "Level"),
                  "names": {k: words(v, v) for k, v in b["names"].items()}}
        if b["total"] is not None:
            label = words(b["total"].get("label", "all_label"), "All")
            boards["total"] = {"label": label}
            if b["total"].get("count_label"):
                boards["total"]["count_label"] = words(b["total"]["count_label"], b["total"]["count_label"])
            if b["total"].get("rank_by"):
                boards["total"]["rank_by"] = b["total"]["rank_by"]
        m["boards"] = boards
    return m


#: Words the short form and defaults use; games can translate them in lang/, or get these.
DEFAULT_WORDS = {"score_label": "Score", "score_unit": "", "time_label": "Time", "plays_label": "Times played",
                 "level_label": "Level", "all_label": "All"}


def _default_label(f):
    return {"time": "Time", "plays": "Times played"}.get(f["source"]) or f["key"].replace("_", " ").capitalize()


def helper(spec, words):
    """What the save helper needs (in edugame-config.js): the fields' keys, orders and how they add up."""
    out = {
        "fields": [{"key": f["key"], "order": f["order"], "source": f["source"], "total": f["total"]} for f in spec["fields"]],
        "rank_by": spec["rank_by"],
        "counts": spec["counts"],
        "primary": spec["primary"],
        "levels": bool(spec["boards"]),
    }
    if spec["grade"]:
        out["grade"] = spec["grade"]
    return out
