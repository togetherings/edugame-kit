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

A game with packages and a menu page (``"pages": {"menu": {"page": "menu.html"}}``)
gets a site of its own instead (docs/platforms/GITHUB_PAGES.md): each package in each language at
its own address, and the game's menu for each language.

    site/
      index.html            goes to the menu in the visitor's language
      en/index.html         the menu in English (the game's menu page)
      en/lesson-03/         a package in English
      en-gb/lesson-03/      the same package in British English
      play/lesson-03/       old addresses: go to the new one

The same pages also come as one offline copy (``offline_zip``): a single
index.html that shows each page at #en/lesson-03, since pages opened from a
folder (file://) can't share a save in every browser.
"""
import json
import os
import re
import shutil
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


def _language_name(project, code):
    """The language's name in itself ("Français"), from _language in lang/<code>.json."""
    info = project.strings.get(code, {}).get("_language")
    name = info.get("name") if isinstance(info, dict) else None
    return name or code


def _play_links(project, href):
    """The Play button, and (with several languages) a link to play in each, named in that
    language ("English · Français"). Not the game's title in each language: many games keep
    one name in every language (Bobo na Mi, Plenty Heaps), and the links would all look alike."""
    out = '<a class="play" href="%s">Play</a>\n' % escape(href)
    if len(project.languages) > 1:
        out += '<p class="langs">Play in: ' + " · ".join(
            '<a href="%s?lang=%s" lang="%s">%s</a>' % (escape(href), escape(code), escape(code), escape(_language_name(project, code)))
            for code in project.languages) + "</p>\n"
    return out


def front_page(project, repo=None, counter="", packages=None):
    """The site's index.html. ``packages``: [(package's project, its folder)] for a game with packages."""
    if packages:
        lang_links = "".join(
            '<section class="package">\n<h2>%s</h2>\n<p>%s</p>\n%s</section>\n' % (
                escape(v.title), escape(v.description), _play_links(v, "play/%s/" % folder))
            for v, folder in packages)
    else:
        lang_links = _play_links(project, "play/")
    icon_dir = "play/%s/" % packages[0][1] if packages else "play/"
    icon = '<img class="icon" src="%s%s" alt="">' % (icon_dir, escape(project.icon)) if project.icon else ""
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
  .package { margin-top: 1.25rem; padding: .25rem 1.25rem 1rem; background: var(--panel); border-radius: 12px; }
  .package h2 { font-size: 1.15rem; margin: .5rem 0 .25rem; }
  .package p { margin: .25rem 0; }
  .get { margin-top: 2.5rem; padding: 1rem 1.25rem; background: var(--panel); border-radius: 12px; }
  .get h2 { font-size: 1.15rem; margin: .25rem 0; }
  footer { margin-top: 2rem; color: var(--muted); font-size: .85rem; }
</style>
%(counter)s</head>
<body>
<main>
<header>%(icon)s<h1>%(title)s</h1></header>
<p class="desc">%(desc)s</p>
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


def _site_game(project, folder, counter):
    """One playable copy of the game, for the web only."""
    build.build_folder(project, folder)
    # The platform files would just confuse visitors.
    for extra in ("imsmanifest.xml", "rachel-index.php", "kolibri-game.json"):
        path = os.path.join(folder, extra)
        if os.path.exists(path):
            os.remove(path)
    if counter:
        entry = os.path.join(folder, *project.entry.split("/"))
        with open(entry, encoding="utf-8") as f:
            html = f.read()
        with open(entry, "w", encoding="utf-8") as f:
            f.write(_inject(html, counter))


def build_pages(project, target, goatcounter=None, repo=None, events=True):
    """Write the site into ``target`` (emptied first). Returns the GoatCounter code used, or None.

    A game with packages gets each one at play/<package id>/, listed on the front page; with a menu
    page (pages.menu), a site of pages instead (build_site).
    """
    code = goatcounter_code(project, goatcounter)
    counter = tracker(code, events) if code else ""
    if os.path.isdir(target):
        shutil.rmtree(target)
    # Built in a folder of its own, then moved into place: the target is often inside the game's folder
    # (game-pages.yml: "edugame pages . -o _site"), and pages built there would be copied into the next ones.
    import tempfile
    work = tempfile.mkdtemp(prefix="edugame-pages-")
    try:
        _build_pages(project, os.path.join(work, "site"), code, counter, repo)
        shutil.move(os.path.join(work, "site"), target)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return code


def _build_pages(project, target, code, counter, repo):
    os.makedirs(target)
    if project.menu and project.packages():
        build_site(project, target, counter, repo=repo)
        return
    play = os.path.join(target, "play")
    packages = []
    if project.packages():
        for pkg in project.packages():
            v = project.variant(pkg["id"])
            _site_game(v, os.path.join(play, pkg["id"]), counter)
            packages.append((v, pkg["id"]))
    else:
        _site_game(project, play, counter)
    with open(os.path.join(target, "index.html"), "w", encoding="utf-8") as f:
        f.write(front_page(project, repo, counter, packages))
    open(os.path.join(target, ".nojekyll"), "w").close()
    with open(os.path.join(target, "site.json"), "w", encoding="utf-8") as f:
        json.dump({"game": project.id, "version": project.version, "goatcounter": bool(code),
                   "packages": [folder for _, folder in packages]}, f)


# ------------------------------------------------------------------ a site with a menu

PLATFORM_FILES = ("imsmanifest.xml", "rachel-index.php", "kolibri-game.json")


def address(code):
    """A language's part of the address: its code in lower case (en-GB -> en-gb)."""
    return code.lower()


def site_plan(project, languages=None):
    """The site's pages: {language: [package, ...]}, in the game's order, for the languages asked for."""
    codes = list(languages) if languages else list(project.languages)
    unknown = [c for c in codes if c not in project.languages]
    if unknown:
        raise ValueError("This game isn't in %s (it's in %s)." % (", ".join(unknown), ", ".join(project.languages)))
    return [(code, [p for p in project.packages() if not p.get("languages") or code in p["languages"]]) for code in codes]


def _page_path(code, pkg=None):
    return address(code) + "/" + (pkg["id"] + "/" if pkg else "")


def site_links(project, repo=None):
    """Where to get the game: the latest release and the code on GitHub (with --repo), and the offline copy's file."""
    base = "https://github.com/%s" % repo if repo else None
    return {"release": base + "/releases/latest" if base else None, "code": base,
            "offline": offline_name(project) if project.menu and project.menu.get("offline") else None}


def site_config(project, plan, code, pkg, mode, repo=None):
    """config.site for one page: where the other pages are (relative addresses, or #addresses offline)."""
    depth = 2 if pkg else 1

    def url(to_code, to_pkg=None):
        if mode == "hash":
            return "#" + address(to_code) + ("/" + to_pkg["id"] if to_pkg else "")
        return "../" * depth + _page_path(to_code, to_pkg)

    mine = dict(plan)[code]
    langs = []
    for other, pkgs in plan:
        same = pkg and next((p for p in pkgs if p["id"] == pkg["id"]), None)
        langs.append({"code": other, "name": _language_name(project, other), "url": url(other, same),
                      "packages": len(pkgs)})
    listed = []
    for p in mine:
        v = project.variant(p["id"], [code])
        listed.append({"id": p["id"], "title": v.title, "description": v.description, "url": url(code, p),
                       "config": p.get("config", {})})
    nxt = None
    if pkg:
        ids = [p["id"] for p in mine]
        at = ids.index(pkg["id"])
        if at + 1 < len(mine):
            nxt = url(code, mine[at + 1])
    return {"mode": mode, "language": code, "address": address(code), "package": pkg["id"] if pkg else None,
            "home": url(code), "next": nxt, "languages": langs, "packages": listed, "links": site_links(project, repo)}


def _page_variant(project, code, pkg):
    if pkg:
        return project.variant(pkg["id"], [code])
    v = project.variant(None, [code])
    v.for_menu = True
    return v


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


#: Picks the visitor's language: ?lang=, their last choice on the site, the browser's languages, the default.
#: SITE = {id, languages: [{code, address, packages: [ids]}]}. Old style ES5, like the helper.
CHOOSER = r"""
function egChoose(SITE) {
  var langs = SITE.languages, i, j;
  function low(c) { return String(c || "").replace(/_/g, "-").toLowerCase(); }
  function base(c) { return low(c).split("-")[0]; }
  function match(w) {
    w = low(w);
    if (!w) return null;
    for (i = 0; i < langs.length; i++) if (low(langs[i].code) === w || langs[i].address === w) return langs[i];
    for (j = 0; j < langs.length; j++) if (low(langs[j].code) === base(w)) return langs[j];
    for (j = 0; j < langs.length; j++) if (base(langs[j].code) === base(w)) return langs[j];
    return null;
  }
  var stored = null;
  try { stored = window.localStorage.getItem("edugame:" + SITE.id + ":language"); } catch (e) { /* storage blocked */ }
  var m = /[?&]lang=([A-Za-z0-9_-]+)/.exec(location.search);
  var tries = [m && m[1], stored].concat(navigator.languages || [navigator.language]);
  for (var k = 0; k < tries.length; k++) { var found = match(tries[k]); if (found) return found; }
  return langs[0];
}
function egHas(lang, pkg) {
  for (var i = 0; i < lang.packages.length; i++) if (lang.packages[i] === pkg) return true;
  return false;
}
"""


def _chooser_data(project, plan):
    return {"id": project.id, "languages": [{"code": c, "address": address(c), "packages": [p["id"] for p in pkgs]}
                                           for c, pkgs in plan]}


def _redirect_page(title, script, fallback):
    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<script>%s</script>
</head>
<body>
<p><a href="%s">%s</a></p>
</body>
</html>
""" % (escape(title), script, escape(fallback), escape(title))


def build_site(project, target, counter="", languages=None, repo=None):
    """The site of pages, written into ``target`` (which must be empty or missing)."""
    plan = site_plan(project, languages)
    made = []
    for code, pkgs in plan:
        for pkg in [None] + pkgs:
            v = _page_variant(project, code, pkg)
            folder = os.path.join(target, *_page_path(code, pkg).strip("/").split("/"))
            if os.path.isdir(folder):
                shutil.rmtree(folder)
            for name, data in build.entries(v, site=site_config(project, plan, code, pkg, "pages", repo)):
                if name in PLATFORM_FILES:
                    continue
                _write(os.path.join(folder, *name.split("/")), data)
            entry = os.path.join(folder, *project.entry.split("/"))
            if not pkg:
                # The menu: the game's menu page is this folder's index.html.
                shutil.move(os.path.join(folder, project.menu["page"]), os.path.join(folder, "index.html"))
                if project.entry != "index.html" and os.path.exists(entry):
                    os.remove(entry)
                entry = os.path.join(folder, "index.html")
            if counter:
                with open(entry, encoding="utf-8") as f:
                    html = f.read()
                with open(entry, "w", encoding="utf-8") as f:
                    f.write(_inject(html, counter))
            made.append(_page_path(code, pkg))
    data = json.dumps(_chooser_data(project, plan))
    # The bare address: the menu in the visitor's language (old links with ?p=<package> go to that package).
    root = (CHOOSER + "var SITE = %s; var lang = egChoose(SITE);\n"
            "var p = /[?&]p=([a-z0-9-]+)/.exec(location.search);\n"
            "location.replace(lang.address + '/' + (p && egHas(lang, p[1]) ? p[1] + '/' : '') + location.hash);\n" % data)
    _write(os.path.join(target, "index.html"), _redirect_page(project.title, root, address(plan[0][0]) + "/").encode("utf-8"))
    # Old addresses (play/<package>/, before the menu): to the package in the visitor's language.
    for pkg in project.packages():
        script = "location.replace('../../?p=%s' + location.search.replace(/^\\?/, '&'));" % pkg["id"]
        _write(os.path.join(target, "play", pkg["id"], "index.html"),
               _redirect_page(project.title, script, "../../").encode("utf-8"))
    open(os.path.join(target, ".nojekyll"), "w").close()
    with open(os.path.join(target, "site.json"), "w", encoding="utf-8") as f:
        json.dump({"game": project.id, "version": project.version, "goatcounter": bool(counter),
                   "languages": {c: address(c) for c, _ in plan}, "pages": made}, f)
    return made


def _script_src(html, name, new):
    """Point the page's <script src="name"> at ``new``."""
    out, n = re.subn(r"""(<script[^>]*\ssrc=["'])%s(["'])""" % re.escape(name), r"\g<1>%s\g<2>" % new, html)
    if not n:
        raise ValueError("The page doesn't load %s with a <script src> tag." % name)
    return out


def offline_name(project):
    return "%s-%s-%s.zip" % (project.slug, project.menu.get("offline") or "all", project.version)


def offline_entries(project, languages=None, repo=None):
    """The offline copy: [(name, bytes)]. One index.html shows every page, chosen by #address:
    #en (the menu in English), #en/lesson-03 (a package). Every page's files are in one folder."""
    plan = site_plan(project, languages)
    files = {}
    configs = {}
    helper = None
    for code, pkgs in plan:
        for pkg in [None] + pkgs:
            v = _page_variant(project, code, pkg)
            key = address(code) + ("/" + pkg["id"] if pkg else "")
            for name, data in build.entries(v, site=site_config(project, plan, code, pkg, "hash", repo)):
                if name in PLATFORM_FILES:
                    continue
                if name == "edugame-config.js":
                    configs[key] = data
                elif name == "edugame.js":
                    helper = data
                elif name in (project.entry, project.menu["page"]):
                    continue   # the pages themselves are in site/pages.js
                else:
                    files[name] = data
    out = []
    names = {}
    for i, key in enumerate(sorted(configs)):
        names[key] = "site/page-%d.js" % i
        out.append((names[key], configs[key]))
    with open(os.path.join(project.folder, project.entry), encoding="utf-8") as f:
        game = f.read()
    with open(os.path.join(project.folder, project.menu["page"]), encoding="utf-8") as f:
        menu = f.read()
    data = _chooser_data(project, plan)
    data.update({"configs": names, "game": _script_src(game, "edugame-config.js", "{config}"),
                 "menu": _script_src(menu, "edugame-config.js", "{config}")})
    router = CHOOSER + r"""
(function () {
  var SITE = window.EDUGAME_SITE;
  var parts = location.hash.replace(/^#/, "").split("/");
  var lang = null, i;
  for (i = 0; i < SITE.languages.length; i++) if (SITE.languages[i].address === parts[0]) lang = SITE.languages[i];
  if (!lang) lang = egChoose(SITE);
  var pkg = parts[1] && egHas(lang, parts[1]) ? parts[1] : null;
  var key = lang.address + (pkg ? "/" + pkg : "");
  if (location.hash !== "#" + key) location.replace("#" + key);
  var page = (pkg ? SITE.game : SITE.menu).replace("{config}", SITE.configs[key]);
  document.write(page);
})();
"""
    out.append(("site/pages.js", ("/* Made by EduGame Kit: every page of the offline copy. */\nwindow.EDUGAME_SITE = %s;\n"
                                  % json.dumps(data, ensure_ascii=False)).encode("utf-8")))
    out.append(("site/router.js", router.encode("utf-8")))
    index = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="site/pages.js"></script>
<script src="site/router.js"></script>
</head>
<body>
<noscript>%s needs JavaScript.</noscript>
</body>
</html>
""" % escape(project.title)
    out.append(("index.html", index.encode("utf-8")))
    out.append(("edugame.js", helper))
    readme = ("%s %s\n\nOpen index.html in a web browser to play: it works without the internet.\n"
              "Results are kept in that browser. Keep all these files together.\n" % (project.title, project.version))
    out.append(("README.txt", readme.encode("utf-8")))
    out += sorted(files.items())
    return out


def offline_zip(project, out_dir, languages=None, repo=None):
    """<game>-<offline>-<version>.zip, the offline copy of the site. Returns its path."""
    path = os.path.join(out_dir, offline_name(project))
    return build._write_zip(path, offline_entries(project, languages, repo))
