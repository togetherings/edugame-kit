"""
A GitHub Pages site for a game: a front page, and the game itself to play in
the browser. Standard library only.

    site/
      index.html         the front page: title, description, Play, languages, where to get the game
      play/              the game, built as for any other platform (saves stay in the browser)
      .nojekyll          tells GitHub Pages to serve the files as they are

Visits can be counted with GoatCounter (goatcounter.com), which uses no
cookies. Its script is added **only here**: never to the zips for Kolibri,
learning systems, RACHEL, Sugarizer or Kiwix (build.py doesn't know about it).
The GoatCounter code comes from ``--goatcounter``, the GOATCOUNTER_CODE
environment variable (the workflow sets it from a repository variable), or
``"pages": {"goatcounter": "..."}`` in edugame.json.

With counting on, each page view is counted (GoatCounter sees the path, like
/my-game/play/), and so are rounds: the save helper announces "edugame:start"
and "edugame:finish" on the page, and the script here counts them as events.
"""
import json
import os
import re
from xml.sax.saxutils import escape, quoteattr

from . import build

GOATCOUNTER_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,49}$")


def goatcounter_code(project, given=None):
    """The GoatCounter code to use, or None for no counting."""
    code = given or os.environ.get("GOATCOUNTER_CODE") or ((project.data.get("pages") or {}).get("goatcounter"))
    if not code:
        return None
    code = code.strip().lower()
    if not GOATCOUNTER_RE.match(code):
        raise ValueError("A GoatCounter code is the part before .goatcounter.com, like 'togetherings'.")
    return code


def tracker(code, events=True):
    """GoatCounter's script, and (with events) counting of rounds the save helper announces."""
    out = ('<!-- Visits are counted with GoatCounter (no cookies). Only on GitHub Pages, never in the game zips. -->\n'
           '<script data-goatcounter=%s async src="//gc.zgo.at/count.js"></script>\n'
           % quoteattr("https://%s.goatcounter.com/count" % code))
    if events:
        out += ('<script>\n'
                '  (function () {\n'
                '    function count(name) {\n'
                '      if (window.goatcounter && window.goatcounter.count) {\n'
                '        window.goatcounter.count({ path: location.pathname.replace(/[^/]*$/, "") + name, title: name, event: true });\n'
                '      }\n'
                '    }\n'
                '    document.addEventListener("edugame:start", function () { count("round-started"); });\n'
                '    document.addEventListener("edugame:finish", function () { count("round-finished"); });\n'
                '  })();\n'
                '</script>\n')
    return out


def _inject(html, snippet):
    """Put the snippet just before </head> (or at the start, for a page without one)."""
    at = html.lower().rfind("</head>")
    return html[:at] + snippet + html[at:] if at >= 0 else snippet + html


def front_page(project, repo=None, counter=""):
    """The site's index.html."""
    langs = project.languages
    lang_links = ""
    if len(langs) > 1:
        lang_links = '<p class="langs">Play in: ' + " · ".join(
            '<a href="play/?lang=%s" lang="%s">%s</a>' % (escape(code), escape(code), escape(project.text("title", code)))
            for code in langs) + "</p>"
    icon = '<img class="icon" src="play/%s" alt="">' % escape(project.icon) if project.icon else ""
    get = ""
    if repo:
        base = "https://github.com/%s" % repo
        get = ('<section class="get">\n<h2>Use it in your school</h2>\n'
               '<p>Download the game from the <a href="%s/releases/latest">latest release</a>. The same zip works in:</p>\n'
               '<ul>\n<li><b>Kolibri</b>: upload it to a channel in Kolibri Studio</li>\n'
               '<li><b>Moodle</b> and other learning systems: add it as a SCORM package</li>\n'
               '<li><b>RACHEL</b>: unzip it into the modules folder</li>\n</ul>\n'
               '<p>There are also files for Sugarizer and Kiwix. <a href="%s">The game\'s code</a> is on GitHub.</p>\n'
               '</section>\n' % (base, base))
    kind = "Your progress is kept in this browser." if project.type == "saved" else \
        "Your results are kept in this browser."
    return """<!doctype html>
<html lang="%(lang)s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content=%(desc_attr)s>
<style>
  :root { --accent: %(color)s; --bg: #f6f7f8; --panel: #fff; --text: #1d232b; --muted: #5a6470; }
  @media (prefers-color-scheme: dark) { :root { --bg: #14171b; --panel: #1d2127; --text: #e9edf1; --muted: #a5afba; } }
  * { box-sizing: border-box; }
  body { margin: 0; font: 17px/1.55 system-ui, sans-serif; background: var(--bg); color: var(--text); }
  main { max-width: 40rem; margin: 0 auto; padding: 2.5rem 16px 3rem; }
  header { display: flex; gap: 1rem; align-items: center; }
  .icon { width: 72px; height: 72px; border-radius: 16px; }
  h1 { font-size: 2rem; line-height: 1.2; margin: 0; }
  .desc { font-size: 1.15rem; color: var(--muted); }
  .play { display: inline-block; margin: .75rem 0 .5rem; padding: .75rem 1.6rem; border-radius: 12px;
          background: var(--accent); color: #fff; font-weight: 600; font-size: 1.1rem; text-decoration: none; }
  .play:focus-visible { outline: 3px solid var(--text); outline-offset: 3px; }
  .note, .langs { color: var(--muted); font-size: .95rem; }
  a { color: inherit; }
  .get { margin-top: 2.5rem; padding: 1rem 1.25rem; background: var(--panel); border-radius: 12px; }
  .get h2 { font-size: 1.15rem; margin: .25rem 0; }
  footer { margin-top: 2rem; color: var(--muted); font-size: .85rem; }
</style>
%(counter)s</head>
<body>
<main>
<header>%(icon)s<h1>%(title)s</h1></header>
<p class="desc">%(desc)s</p>
<a class="play" href="play/">Play</a>
%(langs)s
<p class="note">%(kind)s Nothing is sent to a teacher from this page.</p>
%(get)s
<footer>Made with <a href="https://github.com/togetherings/edugame-kit">EduGame Kit</a>.%(counted)s</footer>
</main>
</body>
</html>
""" % {
        "lang": escape(project.language), "title": escape(project.title), "desc": escape(project.description),
        "desc_attr": quoteattr(project.description), "color": project.color, "icon": icon, "langs": lang_links,
        "kind": kind, "get": get, "counter": counter,
        "counted": " Visits are counted with GoatCounter, without cookies." if counter else "",
    }


def build_pages(project, target, goatcounter=None, repo=None, events=True):
    """Write the site into ``target`` (emptied first). Returns the GoatCounter code used, or None."""
    code = goatcounter_code(project, goatcounter)
    counter = tracker(code, events) if code else ""
    play = os.path.join(target, "play")
    build.build_folder(project, play)  # removes the old site's game first
    for name in os.listdir(target):
        if name != "play":
            path = os.path.join(target, name)
            if os.path.isfile(path):
                os.remove(path)
    # This copy is for the web only: the platform files would just confuse visitors.
    for extra in ("imsmanifest.xml", "rachel-index.php", "kolibri-game.json"):
        path = os.path.join(play, extra)
        if os.path.exists(path):
            os.remove(path)
    if counter:
        entry = os.path.join(play, *project.entry.split("/"))
        with open(entry, encoding="utf-8") as f:
            html = f.read()
        with open(entry, "w", encoding="utf-8") as f:
            f.write(_inject(html, counter))
    with open(os.path.join(target, "index.html"), "w", encoding="utf-8") as f:
        f.write(front_page(project, repo, counter))
    open(os.path.join(target, ".nojekyll"), "w").close()
    with open(os.path.join(target, "site.json"), "w", encoding="utf-8") as f:
        json.dump({"game": project.id, "version": project.version, "goatcounter": bool(code)}, f)
    return code
