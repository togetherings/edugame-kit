# Kolibri

The game's zip works in Kolibri two ways. You can use both.

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
round, Kolibri can show the resource as done.

**Scoreboards:** with [Kolibri Games](https://github.com/togetherings/kolibri-games) 0.2 or later
on the device, Scored Games in channels appear on its games page under **Scored Games in Learn**,
with scoreboards made from the scores they save. Coaches choose what learners see (names,
initials or only their own result) and can download them. Nothing else is needed: the zip already
has the `kolibri-game.json` that tells Kolibri Games how to read them. Saved Games aren't listed
there; they're just played in Learn.

## On the Kolibri Games games page

With the Kolibri Games plugin, a device administrator can also install the same zip on the games
page:

1. Open **Games** in Kolibri's menu, then **Setup**.
2. Choose the zip and click **Install**.

There the game uses the plugin's own saving and scores:

- Saves go to the learner's account (up to 64 KB).
- Scored Games get the plugin's scoreboards and **challenges**: a coach sets the game up for a
  class with its own dates, time limit and settings.
- Coaches can change the game's `settings` and see every move a game reports with
  `EduGame.move()`.

Installing a newer version on the Setup page keeps the old one, so you can go back.

## Trying it

`edugame preview` plays the game as a learning system, which is how Kolibri Learn runs it. To try
the games page, unzip the built zip into a folder (say `games/my-game`) and run
`kolibri-games-preview games` from kolibri-games.
