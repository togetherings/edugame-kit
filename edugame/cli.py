"""
The edugame command.

    edugame new my-game [--type scored]   start a game from a template
    edugame check my-game                 find problems, and words still to translate
    edugame preview my-game               try it in the test page (pretend learning system)
    edugame build my-game                 dist/<name>-<version>.zip, the universal zip
    edugame build my-game --sugarizer --zim
    edugame translate my-game fr          add a language to translate
    edugame pages my-game -o site         a GitHub Pages site for the game (with GoatCounter, if asked)
"""
import argparse
import functools
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, build, pages, project as projects

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _load(folder):
    try:
        return projects.load(folder)
    except projects.ProjectError as e:
        print("%s can't be built yet:" % folder, file=sys.stderr)
        for p in e.problems:
            print("  - " + p, file=sys.stderr)
        sys.exit(1)


def cmd_new(args):
    if os.path.exists(args.folder) and os.listdir(args.folder):
        sys.exit("%s already exists and isn't empty." % args.folder)
    shutil.copytree(os.path.join(TEMPLATES, args.type), args.folder, dirs_exist_ok=True)
    name = os.path.basename(os.path.abspath(args.folder))
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "my-game"
    path = os.path.join(args.folder, "edugame.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["id"] = args.id or "org.example." + slug
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    lang = os.path.join(args.folder, "lang", "en.json")
    with open(lang, encoding="utf-8") as f:
        words = json.load(f)
    words["title"] = args.title or name.replace("-", " ").replace("_", " ").strip().capitalize()
    with open(lang, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)
        f.write("\n")
    if args.github:
        workflows = os.path.join(args.folder, ".github", "workflows")
        os.makedirs(workflows, exist_ok=True)
        for name in ("pages.yml", "build.yml"):
            shutil.copy(os.path.join(TEMPLATES, "github", name), os.path.join(workflows, name))
    print("Made %s, a %s Game. Next:" % (args.folder, "Saved" if args.type == "saved" else "Scored"))
    print("  edugame preview %s    try it" % args.folder)
    print("  edugame build %s      make the zip" % args.folder)
    print("Change the id in edugame.json to one of your own before you share the game.")
    if args.github:
        print("On GitHub: make the folder a repository and push it. The Build workflow makes the zips (and attaches")
        print("them to each release); for the web page, choose GitHub Actions in Settings > Pages.")


def cmd_check(args):
    p = _load(args.folder)
    print("%s %s: a %s Game in %s." % (p.title, p.version, p.type.capitalize(), ", ".join(p.languages)))
    for pkg in p.packages():
        v = p.variant(pkg["id"])
        print("  package %s: %s (%d files, %s)" % (pkg["id"], v.title, len(v.files()), ", ".join(v.languages)))
    for code, keys in sorted(projects.missing_strings(p).items()):
        print("  lang/%s.json is missing %d words: %s" % (code, len(keys), ", ".join(keys[:8]) + (" ..." if len(keys) > 8 else "")))
    for key, files in sorted(projects.unknown_keys(p).items()):
        print("  %s uses the word '%s', which lang/%s.json doesn't have" % (", ".join(files[:3]), key, p.language))
    print("No problems found.")


def _languages(args):
    return [c.strip() for c in args.lang.split(",") if c.strip()] if getattr(args, "lang", None) else None


def cmd_build(args):
    p = _load(args.folder)
    zim = args.zim or args.all
    if zim:
        try:
            import libzim.writer  # noqa: F401
        except ImportError:
            msg = "Making a ZIM file needs libzim: pip install libzim"
            if args.zim:
                sys.exit(msg)
            print(msg + " (skipped)", file=sys.stderr)
            zim = False
    try:
        made = build.build_all(p, args.out_dir, package=args.package, languages=_languages(args),
                               each_language=args.each_language, sugarizer=args.sugarizer or args.all,
                               sugar_lib=args.sugar_lib, zim=zim)
    except (projects.ProjectError, ValueError) as e:
        sys.exit(str(e))
    for path in made:
        print("Made %s (%d KB)" % (path, (os.path.getsize(path) + 1023) // 1024))


def cmd_pages(args):
    p = _load(args.folder)
    try:
        code = pages.build_pages(p, args.out_dir, args.goatcounter, args.repo, events=not args.no_events)
    except ValueError as e:
        sys.exit(str(e))
    print("Made the site in %s%s" % (args.out_dir, " (counted with GoatCounter: %s)" % code if code else " (no counting)"))


def cmd_translate(args):
    p = _load(args.folder)
    code = args.language
    if not projects.LANG_RE.match(code):
        sys.exit("Use a language code like fr or pt-BR.")
    path = os.path.join(p.folder, "lang", code + ".json")
    words = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            words = json.load(f)
    if "_language" not in words:
        rtl = code.split("-")[0].lower() in ("ar", "fa", "he", "ps", "ur", "yi", "dv", "ckb")
        words["_language"] = {"name": code, "dir": "rtl" if rtl else "ltr"}  # write the name in the language itself
    # The default language's words, to be translated (its notes for translators stay in its own file).
    added = [k for k in p.strings[p.language] if k not in words and k != "_notes"]
    for k in added:
        words[k] = p.strings[p.language][k]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)
        f.write("\n")
    if code not in p.languages:
        p.data["languages"] = p.languages + [code]
        with open(os.path.join(p.folder, "edugame.json"), "w", encoding="utf-8") as f:
            json.dump(p.data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print("lang/%s.json has %d words to translate (copied from %s). Put the language's own name in _language."
          % (code, len(added), p.language))
    if p.content_dirs:
        print("Content folders (%s) may need lang/%s.json files or editions too: see docs/LANGUAGES.md."
              % (", ".join(p.content_dirs), code))


def _signature(folder):
    """Changes whenever a file in the game folder changes."""
    sig = []
    for root, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in projects.SKIP_NAMES]
        for n in names:
            try:
                st = os.stat(os.path.join(root, n))
                sig.append((root, n, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
    return hash(tuple(sorted(sig)))


class _PreviewHandler(SimpleHTTPRequestHandler):
    """Serves the test page at /test/ and the game at /game/, rebuilt when its files change."""

    folder = None
    state = None  # {"built": folder, "sig": signature, "lock": Lock, "old": [folders]}

    @property
    def built(self):
        return self.state["built"]

    def rebuild(self):
        """Build into a new folder and switch to it, so requests already running still find their files."""
        with self.state["lock"]:
            sig = _signature(self.folder)
            if sig == self.state["sig"]:
                return
            target = tempfile.mkdtemp(prefix="edugame-preview-")
            build.build_folder(_preview_project(self.folder, self.state["package"], self.state["languages"]), target)
            self.state["old"].append(self.state["built"])
            self.state["built"], self.state["sig"] = target, sig
            while len(self.state["old"]) > 2:
                shutil.rmtree(self.state["old"].pop(0), ignore_errors=True)

    def translate_path(self, path):
        path = path.split("?", 1)[0]
        if path.startswith("/test/"):
            return os.path.join(build.RUNTIME, "test.html")
        if path.startswith("/game/"):
            rel = path[len("/game/"):] or "index.html"
            return os.path.join(self.built, *[x for x in rel.split("/") if x not in ("", "..")])
        return os.path.join(build.RUNTIME, "missing")

    def do_GET(self):
        if self.path in ("/", ""):
            p = _preview_project(self.folder, self.state["package"], self.state["languages"])
            self.send_response(302)
            self.send_header("Location", "/test/?game=/game/%s&id=%s&languages=%s" % (p.entry, p.id, ",".join(p.languages)))
            self.end_headers()
            return
        if self.path.split("?")[0].endswith(".html") and self.path.startswith("/game/"):
            try:
                self.rebuild()
            except projects.ProjectError as e:
                body = ("<h1>The game has problems</h1><ul>%s</ul>" % "".join("<li>%s</li>" % x for x in e.problems)).encode()
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return
        SimpleHTTPRequestHandler.do_GET(self)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        SimpleHTTPRequestHandler.end_headers(self)

    def log_message(self, *a):
        pass


def _preview_project(folder, package=None, languages=None):
    p = projects.load(folder)
    if package is None and p.packages():
        package = p.packages()[0]["id"]
    return p.variant(package, languages) if (package or languages) else p


class _QuietServer(ThreadingHTTPServer):
    """The preview server, without a traceback each time a browser closes a connection early."""
    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            ThreadingHTTPServer.handle_error(self, request, client_address)


def make_preview_server(folder, port, package=None, languages=None):
    folder = os.path.abspath(folder)
    built = tempfile.mkdtemp(prefix="edugame-preview-")
    build.build_folder(_preview_project(folder, package, languages), built)
    state = {"built": built, "sig": _signature(folder), "lock": threading.Lock(), "old": [],
             "package": package, "languages": languages}
    handler = type("Handler", (_PreviewHandler,), {"folder": folder, "state": state})
    return _QuietServer(("127.0.0.1", port), handler)


def cmd_kolibri_test(args):
    from . import kolibri_test
    sys.exit(kolibri_test.run(args.folder, play_file=args.play, port=args.port,
                              shots=args.screenshots, keep=args.keep))


def cmd_preview(args):
    _load(args.folder)
    try:
        server = make_preview_server(args.folder, args.port, args.package, _languages(args))
    except projects.ProjectError as e:
        sys.exit(str(e))
    url = "http://127.0.0.1:%d/" % server.server_address[1]
    print("Test page: %s  (press Ctrl+C to stop; reload the page after you change the game)" % url)
    if not args.no_browser:
        threading.Timer(0.5, functools.partial(webbrowser.open, url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="edugame", description="Make games that save everywhere: Kolibri, Moodle, RACHEL, Sugarizer and Kiwix.")
    parser.add_argument("--version", action="version", version="EduGame Kit %s" % __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="start a game from a template")
    p.add_argument("folder")
    p.add_argument("--type", choices=("saved", "scored"), default="saved", help="Saved Games keep progress; Scored Games also keep a score")
    p.add_argument("--id", help="the game's id, like org.example.my-game")
    p.add_argument("--title")
    p.add_argument("--github", action="store_true", help="also add workflows that build the zips and publish the game to GitHub Pages")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("check", help="find problems and missing translations")
    p.add_argument("folder")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("build", help="make the zip (and the Sugarizer and Kiwix files)")
    p.add_argument("folder")
    p.add_argument("-o", "--out-dir", default="dist")
    p.add_argument("--sugarizer", action="store_true", help="also make a Sugarizer activity")
    p.add_argument("--sugar-lib", help="the lib folder of a Sugarizer activity, to save in the Journal")
    p.add_argument("--zim", action="store_true", help="also make a ZIM file for Kiwix (needs libzim)")
    p.add_argument("--all", action="store_true", help="make everything this computer can")
    p.add_argument("--package", help="only this package (see packages in edugame.json)")
    p.add_argument("--lang", help="only these languages, like fr or fr,en (the first is the default)")
    p.add_argument("--each-language", action="store_true", help="one zip per language, instead of one with every language")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("preview", help="try the game in the test page")
    p.add_argument("folder")
    p.add_argument("--port", type=int, default=8100)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--package", help="the package to try (the first, if the game has packages)")
    p.add_argument("--lang", help="only these languages, like fr or fr,en")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("pages", help="make a GitHub Pages site: a front page and the game")
    p.add_argument("folder")
    p.add_argument("-o", "--out-dir", default="site")
    p.add_argument("--goatcounter", help="count visits with this GoatCounter code (or set GOATCOUNTER_CODE)")
    p.add_argument("--repo", help="owner/name on GitHub, to link the latest release")
    p.add_argument("--no-events", action="store_true", help="count page views only, not rounds")
    p.set_defaults(func=cmd_pages)

    p = sub.add_parser("translate", help="add a language (or the words it's missing)")
    p.add_argument("folder")
    p.add_argument("language")
    p.set_defaults(func=cmd_translate)

    p = sub.add_parser("kolibri-test", help="play the game in a real Kolibri, as a learner (needs kolibri and playwright)")
    p.add_argument("folder")
    p.add_argument("--play", help="the game's play steps (default: tests/kolibri_play.py in the folder)")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--screenshots", default="kolibri-screenshots", help="folder for screenshots ('' for none)")
    p.add_argument("--keep", action="store_true", help="keep the throwaway Kolibri's files, to look at afterwards")
    p.set_defaults(func=cmd_kolibri_test)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
