"""
The edugame command.

    edugame new my-game [--type scored]   start a game from a template
    edugame check my-game                 find problems, and words still to translate
    edugame preview my-game               try it in the test page (pretend learning system)
    edugame build my-game                 dist/<name>-<version>.zip, the universal zip
    edugame build my-game --sugarizer --zim
    edugame translate my-game fr          add a language to translate
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

from . import __version__, build, project as projects

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
    print("Made %s, a %s Game. Next:" % (args.folder, "Saved" if args.type == "saved" else "Scored"))
    print("  edugame preview %s    try it" % args.folder)
    print("  edugame build %s      make the zip" % args.folder)
    print("Change the id in edugame.json to one of your own before you share the game.")


def cmd_check(args):
    p = _load(args.folder)
    print("%s %s: a %s Game in %s." % (p.title, p.version, p.type.capitalize(), ", ".join(p.languages)))
    for code, keys in sorted(projects.missing_strings(p).items()):
        print("  lang/%s.json is missing %d words: %s" % (code, len(keys), ", ".join(keys[:8]) + (" ..." if len(keys) > 8 else "")))
    print("No problems found.")


def cmd_build(args):
    p = _load(args.folder)
    made = [build.build_zip(p, args.out_dir)]
    if args.sugarizer or args.all:
        made.append(build.build_sugarizer(p, args.out_dir, args.sugar_lib))
    if args.zim or args.all:
        try:
            made.append(build.build_zim(p, args.out_dir))
        except ImportError:
            msg = "Making a ZIM file needs libzim: pip install libzim"
            if args.zim:
                sys.exit(msg)
            print(msg + " (skipped)", file=sys.stderr)
    for path in made:
        print("Made %s (%d KB)" % (path, (os.path.getsize(path) + 1023) // 1024))


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
    added = [k for k in p.strings[p.language] if k not in words]
    for k in added:
        words[k] = p.strings[p.language][k]  # to be translated
    with open(path, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)
        f.write("\n")
    if code not in p.languages:
        p.data["languages"] = p.languages + [code]
        with open(os.path.join(p.folder, "edugame.json"), "w", encoding="utf-8") as f:
            json.dump(p.data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print("lang/%s.json has %d words to translate (copied from %s)." % (code, len(added), p.language))


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
            build.build_folder(projects.load(self.folder), target)
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
            p = projects.load(self.folder)
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


def make_preview_server(folder, port):
    folder = os.path.abspath(folder)
    built = tempfile.mkdtemp(prefix="edugame-preview-")
    build.build_folder(projects.load(folder), built)
    state = {"built": built, "sig": _signature(folder), "lock": threading.Lock(), "old": []}
    handler = type("Handler", (_PreviewHandler,), {"folder": folder, "state": state})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def cmd_preview(args):
    _load(args.folder)
    server = make_preview_server(args.folder, args.port)
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
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("preview", help="try the game in the test page")
    p.add_argument("folder")
    p.add_argument("--port", type=int, default=8100)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("translate", help="add a language (or the words it's missing)")
    p.add_argument("folder")
    p.add_argument("language")
    p.set_defaults(func=cmd_translate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
