# LTI 1.3 (planned)

**Not built yet.** This is the plan, so the rest of the kit leaves room for it.

LTI 1.3 lets a learning system open a game on another server, sign the learner in and receive a
grade. It's the way to use the games in learning systems without SCORM, like self-hosted Canvas,
and an alternative to SCORM in Moodle, Blackboard, Brightspace and others.

## How it will work

```
Learning system ──launch (LTI 1.3, signed)──▶ EduGame LTI server ──serves──▶ the game (same zip)
       ▲                                           │
       └────────── grade (Assignment and Grade Services) ◀── EduGame.finish()
```

1. **A small LTI server**, `edugame-lti`, run by the school (it could run on the same Raspberry
   Pi). Standard library Python plus one JWT library, with a small SQLite database. An
   administrator adds game zips to it, and registers it with the learning system once.
2. **Launch:** the learning system sends a signed launch. The server checks it, finds the learner
   and the activity, and opens the game with a short-lived token.
3. **Saves:** a new **"lti"** way of saving in `edugame.js`: `EduGame.save()` sends the save to
   the LTI server, keyed by learning system, course, activity and learner.
4. **Grades:** `EduGame.finish()` sends the score; the server sends the learner's best 0-100 grade
   to the learning system with Assignment and Grade Services, using `scoring.grade`.
5. **Deep linking**, so a teacher can pick a game from a list when they add the activity.

Games won't need to change: the same zip and the same calls work, because the helper picks the
way to save.

## What needs to be decided

- Whether `edugame-lti` is its own project or part of the kit.
- How the server is installed on Internet-in-a-Box and other offline servers, and how the
  learning system reaches it.
- Whether scoreboards are shown inside the game, like on the Kolibri Games games page.

## Order of work

1. The launch and the "lti" saves, tested against Moodle's LTI 1.3 support (open source, easy to
   run for testing).
2. Grades with Assignment and Grade Services.
3. Canvas, then deep linking.
