# RACHEL and OER2Go

On RACHEL, a game is a **module**: a folder on the server with a `rachel-index.php` that puts it
on RACHEL's home page. The game's zip already has that file.

1. Unzip `dist/<name>-<version>.zip` into a folder named for the language and the game, like
   `en-number-hunt`.
2. Copy that folder into RACHEL's modules folder, usually `/var/www/modules/`. On
   Internet-in-a-Box, OER2Go modules go in `/library/www/html/modules/`.
3. Open RACHEL's home page: the game is listed with its icon, title and description. (If your
   RACHEL has an admin page for modules, turn the new one on there.)

```bash
unzip number-hunt-1.0.0.zip -d en-number-hunt
sudo cp -r en-number-hunt /var/www/modules/
```

## Saves

RACHEL has no learner accounts, so the helper saves in each learner's **browser**: they carry on
next time on the same device and browser. Learners who share a device share its save. If learners
sign in elsewhere (Kolibri, Moodle), put the game there too for saves that follow them.

## Updating a game

Replace the folder with the new version's files. Saves stay in the browsers, because they're
kept under the game's `id`.
