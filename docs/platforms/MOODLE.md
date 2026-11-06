# Moodle

The game's zip is a **SCORM 1.2 package**.

1. In your course, turn editing on and choose **Add an activity or resource > SCORM package**.
2. Give it a name and upload the zip (`dist/<name>-<version>.zip`) under **Package file**.
3. Choose the settings below, and save.

Learners open it like any SCORM activity. The helper saves their progress in their attempt.

## Settings that matter

- **Appearance > Display package:** *Current window* suits most games. Hide the course structure
  and navigation for more room.
- **Attempts management > Force new attempt:** leave it at *No*, so learners carry on where they
  left off. With *Always*, every visit starts afresh, and the save is lost.
- **Grading method** (Scored Games): *Highest grade* keeps the learner's best. The helper sends a
  0-100 grade when `scoring.grade` in `edugame.json` says how (which score is 100% and which is
  0%; see [../SCORING.md](../SCORING.md)), and only ever raises it within an attempt.
- **Maximum grade:** 100 matches what the helper sends.
- **Completion tracking:** *Require status*, with *Passed*, marks the activity done after
  `EduGame.complete()` or a passed round (the helper sets `passed`).

## Saves

SCORM 1.2 allows 4,096 characters in `cmi.suspend_data`; the helper refuses saves over 3,900, so
there's room for its own data. Keep saves small (see [../HELPER.md](../HELPER.md)).

## Leaderboards

Moodle doesn't show a scoreboard for SCORM activities by itself. Two add-ons can:

- **Level Up XP** gives points for activity and shows a ranking (its paid add-on gives points for
  grades).
- **Ranking block** shows a ranking from completed activities.

Check that an add-on supports your Moodle version before you install it. Inside Moodle, the
gradebook shows teachers every learner's grade.

## Updating a game

Edit the SCORM activity and upload the new zip. Moodle keeps learners' saves when the package
changes, but a game that changes the shape of its save should still read older saves.
