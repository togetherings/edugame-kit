# Changelog

## 0.1.0

First version.

- **Saved Games and Scored Games**, made from a folder with `edugame.json`, `lang/` and web files.
- **The save helper** (`edugame.js`): saves progress, and Scored Games' best score, time and
  plays, on the Kolibri Games games page (through its SDK), in SCORM 1.2 learning systems
  (Kolibri channels, Moodle and others), in Sugarizer's Journal (with sugar-web) or in the browser.
  Scored Games also send a 0-100 grade to learning systems.
- **The build tool** (`edugame`): `new`, `check`, `preview`, `build` and `translate`. `build`
  makes the universal zip (Kolibri, Kolibri Games, SCORM 1.2, RACHEL), and with `--sugarizer` and
  `--zim` a Sugarizer activity and a ZIM file for Kiwix.
- **Translations:** every game lists its languages; the helper picks the learner's language and
  fills in `data-t` text, and sets right-to-left for Arabic, Persian, Hebrew and Urdu.
- **The test page:** plays a game as a learning system or a website and shows what it saves.
- Templates for both kinds, and two examples moved from Kolibri Games: Number Hunt and Memory
  Match, now in English and French.
- Guides for Kolibri, Moodle, RACHEL, Sugarizer, Kiwix and other learning systems, and the plan
  for LTI 1.3.
