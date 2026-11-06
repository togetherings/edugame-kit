# Kolibri

Saved and Scored Games reach Kolibri through **Kolibri Studio**, as HTML5 apps in a channel.

## In a channel (Learn)

The zip is an ordinary Kolibri **HTML5 app**. Learners open it from **Learn**, and coaches can put
it in lessons and assign it to classes, like any other resource.

1. In [Kolibri Studio](https://studio.learningequality.org/), open your channel and choose
   **Add > Upload files**, then choose the game's zip (`dist/<name>-<version>.zip`).
2. Fill in the title, language, license and so on, and publish the channel.
3. On the Kolibri device, import the channel (or update it) as usual.

Kolibri gives the game a SCORM connection, so the helper saves each learner's progress in their
Kolibri account. Kolibri syncs it between servers, so learners can carry on from another device
that syncs with this one. When the game calls `EduGame.complete()`, or a Scored Game finishes a
passed round, Kolibri shows the resource as done.

**Scoreboards:** with [Kolibri Games](https://github.com/togetherings/kolibri-games) 0.2 or later
on the device, Scored Games in channels appear on its games page under **Scored Games in Learn**,
with scoreboards made from the scores they save: one for each level or lesson, and one for the
whole game if `scoring.boards.total` asks for it. Coaches choose what learners see (names,
initials or only their own result) and can download them. Nothing else is needed: the zip already
has the `kolibri-game.json` that tells Kolibri Games how to read them. Saved Games aren't listed
there; they're just played in Learn.

## Scores in Kolibri

The helper never sends Kolibri a score: Kolibri reads a SCORM score as how much of a resource is
done, so a resource would only count as done at 100. It sets the status instead: `incomplete`
when the game opens, and `passed` after `EduGame.complete()` or a passed round. Scoreboards come
from Kolibri Games, above.

(Kolibri Games can also install a zip on its games page, which is handy for trying a game with
coaches' challenges. Studio is the way to give games to learners.)

## Trying it

`edugame preview` plays the game as a learning system, which is how Kolibri Learn runs it. To try
the games page, unzip the built zip into a folder (say `games/my-game`) and run
`kolibri-games-preview games` from kolibri-games.
