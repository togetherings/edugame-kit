# Kiwix

Kiwix opens **ZIM files**. The build makes one when Python's libzim package is installed:

```bash
pip install libzim
edugame build my-game --zim
# dist/<name>_<version>.zim
```

(libzim has ready-made packages for Linux, macOS and Windows on common computers, including the
Raspberry Pi.)

## Opening it

- **Kiwix apps** (desktop, Android): open the `.zim` file.
- **kiwix-serve** (including Internet-in-a-Box): add the file to the server's library. On
  Internet-in-a-Box, copy it to `/library/zims/content/` and run `sudo iiab-make-kiwix-lib`.

The game opens at its start page. The ZIM has the game's title, description, languages and a
small picture in the game's colour for Kiwix's library.

## Saves

The helper saves in the **browser** (or the Kiwix app), on that device only. With kiwix-serve,
saves belong to the server's address: they're lost if the address changes.

Games need JavaScript, which kiwix-serve and the current Kiwix apps run. Some older Kiwix apps
don't run JavaScript in ZIM files.
