"""
Building a game folder into files for each platform.

* build_zip: the universal zip. The same file works as a Kolibri HTML5 app
  (channels and the Kolibri Games games page), a SCORM 1.2 package (Moodle and
  other learning systems) and, unzipped, a RACHEL module or a website.
* build_sugarizer: a zip holding <Name>.activity/, for Sugarizer.
* build_zim: a ZIM file for Kiwix (needs the libzim package).
* build_folder: the game with its generated files, unzipped (used by the test page).
"""
import json
import os
import re
import shutil
import time
import zipfile

from . import __version__, platforms

RUNTIME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime")
#: Same date for every file, so building the same game twice gives the same zip.
ZIP_DATE = (2020, 1, 1, 0, 0, 0)


def helper_js():
    with open(os.path.join(RUNTIME, "edugame.js"), encoding="utf-8") as f:
        return f.read()


def config_js(project, **extra):
    cfg = project.config()
    cfg.update(extra)
    return ("/* Made by EduGame Kit %s from edugame.json and lang/. Don't edit: run edugame build. */\n"
            "window.EDUGAME_CONFIG = %s;\n" % (__version__, json.dumps(cfg, ensure_ascii=False, sort_keys=True)))


def generated(project, **extra):
    """{path: text} for the files every build adds."""
    files = project.files()
    out = {
        "edugame.js": helper_js(),
        "edugame-config.js": config_js(project, **extra),
        "kolibri-game.json": json.dumps(project.kolibri_manifest(), indent=2, ensure_ascii=False) + "\n",
        "rachel-index.php": platforms.rachel_index(project),
    }
    listed = sorted(set(files) | set(out) | {"imsmanifest.xml"})
    out["imsmanifest.xml"] = platforms.scorm_manifest(project, listed)
    return out


def _write_zip(path, entries):
    """entries: [(name in zip, bytes)]."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    os.replace(tmp, path)
    return path


def _read(project, rel):
    with open(os.path.join(project.folder, rel), "rb") as f:
        return f.read()


def entries(project, **extra):
    out = [(rel, _read(project, rel)) for rel in project.files()]
    out += [(name, text.encode("utf-8")) for name, text in sorted(generated(project, **extra).items())]
    return out


def build_zip(project, out_dir):
    path = os.path.join(out_dir, "%s-%s.zip" % (project.slug, project.version))
    return _write_zip(path, entries(project))


def build_folder(project, target):
    """Write the game and its generated files into target (emptied first)."""
    if os.path.isdir(target):
        shutil.rmtree(target)
    for name, data in entries(project):
        path = os.path.join(target, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    return target


SUGAR_LOADER = ('<script src="lib/require.js"></script>\n'
                '<script>requirejs.config({ baseUrl: "lib" });</script>\n')


def build_sugarizer(project, out_dir, sugar_lib=None):
    """A zip with <Name>.activity/ inside, to unzip into Sugarizer's activities folder.

    sugar_lib: the lib folder of any Sugarizer activity (with require.js and
    sugar-web/). With it, saves go to Sugarizer's Journal; without it they're
    kept in the browser.
    """
    folder = platforms.activity_folder_name(project) + ".activity"
    items = entries(project, sugarizer=bool(sugar_lib))
    out = []
    for name, data in items:
        if name in ("imsmanifest.xml", "rachel-index.php"):
            continue
        if name == project.entry and sugar_lib:
            # Load sugar-web's loader before the helper, so edugame.js can find it.
            page = data.decode("utf-8")
            page = re.sub(r'(<script[^>]*src="edugame-config\.js")', SUGAR_LOADER.replace("\\", "\\\\") + r"\1", page, count=1)
            data = page.encode("utf-8")
        out.append((folder + "/" + name, data))
    icon = None
    if project.icon and project.icon.endswith(".svg"):
        icon = _read(project, project.icon)
    out.append((folder + "/activity/activity-icon.svg", icon or platforms.plain_icon_svg(project).encode("utf-8")))
    out.append((folder + "/activity/activity.info", platforms.activity_info(project).encode("utf-8")))
    if sugar_lib:
        if not os.path.isfile(os.path.join(sugar_lib, "require.js")) or not os.path.isdir(os.path.join(sugar_lib, "sugar-web")):
            raise ValueError("%s needs require.js and a sugar-web folder (copy the lib folder of any Sugarizer activity)." % sugar_lib)
        for root, dirs, names in os.walk(sugar_lib):
            dirs.sort()
            for n in sorted(names):
                full = os.path.join(root, n)
                rel = os.path.relpath(full, sugar_lib).replace(os.sep, "/")
                with open(full, "rb") as f:
                    out.append((folder + "/lib/" + rel, f.read()))
    path = os.path.join(out_dir, "%s-%s-sugarizer.zip" % (project.slug, project.version))
    return _write_zip(path, out)


MIME = {
    ".html": "text/html", ".htm": "text/html", ".js": "application/javascript", ".css": "text/css",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
    ".wav": "audio/wav", ".woff": "font/woff", ".woff2": "font/woff2", ".txt": "text/plain", ".xml": "text/xml",
}


def build_zim(project, out_dir):
    """A ZIM file for Kiwix. Needs libzim (pip install libzim); raises ImportError without it."""
    from libzim.writer import Creator, Hint, Item, StringProvider

    class Entry(Item):
        def __init__(self, path, data, title=""):
            super().__init__()
            self.path, self.data, self.title = path, data, title

        def get_path(self):
            return self.path

        def get_title(self):
            return self.title

        def get_mimetype(self):
            return MIME.get(os.path.splitext(self.path)[1].lower(), "application/octet-stream")

        def get_contentprovider(self):
            return StringProvider(self.data)

        def get_hints(self):
            return {Hint.FRONT_ARTICLE: self.path == project.entry}

    path = os.path.join(out_dir, "%s_%s.zim" % (project.slug, project.version))
    os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    with Creator(path).config_indexing(False, platforms.zim_languages(project).split(",")[0]) as creator:
        creator.set_mainpath(project.entry)
        for name, data in entries(project):
            if name in ("imsmanifest.xml", "rachel-index.php", "kolibri-game.json"):
                continue
            creator.add_item(Entry(name, data, project.title if name == project.entry else ""))
        meta = {
            "Name": project.slug, "Title": project.title[:30], "Description": (project.description or project.title)[:80],
            "Language": platforms.zim_languages(project), "Creator": ", ".join(project.authors) or "Unknown",
            "Publisher": ", ".join(project.authors) or "Unknown", "Date": time.strftime("%Y-%m-%d"),
            "Tags": "_category:games;edugame", "Source": project.id, "License": project.license or "unknown",
        }
        for key, value in meta.items():
            creator.add_metadata(key, value)
        try:
            creator.add_illustration(48, platforms.solid_png(project.color))  # libzim up to 3.7
        except TypeError:
            pass  # newer libzim changed this call; the picture is only for Kiwix's library
    return path


def zip_names(path):
    with zipfile.ZipFile(path) as z:
        return z.namelist()


def read_zip(path, name):
    with zipfile.ZipFile(path) as z:
        return z.read(name)

