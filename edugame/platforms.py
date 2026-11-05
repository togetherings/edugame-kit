"""
The extra files each platform needs, made from a Project. Standard library only.

* Kolibri (games page and channels): kolibri-game.json (Project.kolibri_manifest)
* Moodle and other learning systems: imsmanifest.xml, a SCORM 1.2 package
* RACHEL: rachel-index.php, the module's entry on the RACHEL home page
* Sugarizer: activity/activity.info, in an <Name>.activity folder
* Kiwix: ZIM metadata (see build.build_zim)
"""
import re
import struct
import zlib
from xml.sax.saxutils import escape, quoteattr


def scorm_manifest(project, files):
    """imsmanifest.xml for a SCORM 1.2 package with one SCO: the game's start page."""
    ident = re.sub(r"[^A-Za-z0-9_.-]", "_", project.id)
    file_lines = "\n".join('      <file href=%s/>' % quoteattr(name) for name in files)
    return """<?xml version="1.0" encoding="UTF-8"?>
<!-- Made by EduGame Kit. A SCORM 1.2 package: the game saves with cmi.suspend_data. -->
<manifest identifier=%(id)s version=%(version)s
    xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="org">
    <organization identifier="org">
      <title>%(title)s</title>
      <item identifier="item" identifierref="game">
        <title>%(title)s</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="game" type="webcontent" adlcp:scormtype="sco" href=%(entry)s>
%(files)s
    </resource>
  </resources>
</manifest>
""" % {
        "id": quoteattr(ident),
        "version": quoteattr(project.version),
        "title": escape(project.title),
        "entry": quoteattr(project.entry),
        "files": file_lines,
    }


def rachel_index(project):
    """rachel-index.php: RACHEL's home page includes it, with $dir set to the module's folder."""
    icon = ""
    if project.icon:
        icon = '<a href="<?php echo $dir ?>/%s"><img src="<?php echo $dir ?>/%s" alt=""></a>\n' % (
            escape(project.entry), escape(project.icon))
    return """<!-- Made by EduGame Kit. Saves are kept in each browser. -->
<div class="indexmodule">
%s<h2><a href="<?php echo $dir ?>/%s">%s</a></h2>
<p>%s</p>
</div>
""" % (icon, escape(project.entry), escape(project.title), escape(project.description))


def sugar_version(version):
    """Sugar wants a whole number for activity_version: 1.2.3 becomes 10203."""
    parts = [int(p) for p in re.findall(r"\d+", version)[:3]] + [0, 0, 0]
    return parts[0] * 10000 + parts[1] * 100 + parts[2]


def activity_folder_name(project):
    return re.sub(r"[^A-Za-z0-9]+", "", project.title.title()) or project.slug.title()


def activity_info(project):
    """activity/activity.info for Sugarizer (and Sugar)."""
    return """[Activity]
name = %s
activity_version = %d
bundle_id = %s
exec = sugar-activity-web
icon = activity-icon
license = %s
summary = %s
""" % (project.title.replace("\n", " "), sugar_version(project.version), project.id,
       project.license or "unknown", project.description.replace("\n", " "))


def plain_icon_svg(project):
    """A coloured square with the title's first letter, for platforms that need an icon."""
    letter = escape((project.title[:1] or "G").upper())
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 55 55" width="55" height="55">'
            '<rect x="2" y="2" width="51" height="51" rx="10" fill="%s"/>'
            '<text x="27.5" y="37" font-size="28" font-family="sans-serif" text-anchor="middle" fill="#fff">%s</text>'
            '</svg>' % (project.color, letter))


def solid_png(color, size=48):
    """A size x size PNG of one colour (ZIM files need a 48x48 picture), without image libraries."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    row = b"\x00" + bytes((r, g, b)) * size
    raw = row * size

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


#: ZIM metadata wants ISO 639-3 codes.
ISO639_3 = {
    "ar": "ara", "bn": "ben", "de": "deu", "en": "eng", "es": "spa", "fa": "fas", "fr": "fra", "ha": "hau",
    "hi": "hin", "id": "ind", "it": "ita", "ja": "jpn", "km": "khm", "ko": "kor", "mg": "mlg", "my": "mya",
    "ne": "nep", "nl": "nld", "pl": "pol", "ps": "pus", "pt": "por", "ru": "rus", "rw": "kin", "so": "som",
    "sw": "swa", "ta": "tam", "th": "tha", "tl": "tgl", "tr": "tur", "uk": "ukr", "ur": "urd", "vi": "vie",
    "yo": "yor", "zh": "zho", "zu": "zul", "am": "amh", "ig": "ibo", "xh": "xho", "ny": "nya", "sn": "sna",
}


def zim_languages(project):
    out = []
    for code in project.languages:
        base = code.split("-")[0]
        out.append(ISO639_3.get(base, base if len(base) == 3 else "mul"))
    return ",".join(dict.fromkeys(out))
