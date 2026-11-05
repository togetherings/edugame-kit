# Sugarizer

Sugarizer runs **activities**: folders named `<Name>.activity` with an `activity/activity.info`.
The build makes one:

```bash
edugame build my-game --sugarizer
# dist/<name>-<version>-sugarizer.zip, holding MyGame.activity/
```

## Installing

Unzip it into Sugarizer's `activities` folder, so you have `activities/MyGame.activity/`, then
restart Sugarizer Server. The activity appears in the list of activities; on Sugarizer Server, an
administrator may need to make it visible in the dashboard's **Activities** page. (Where the
folder is depends on how Sugarizer was installed: look for the folder that holds the other
`.activity` folders.)

## Saves: the Journal, or the browser

- **With sugar-web**, saves go to the activity's entry in the **Journal**, like other Sugarizer
  activities, and so to the learner's account on Sugarizer Server. sugar-web isn't part of the
  kit: copy the `lib` folder of any Sugarizer activity (it has `require.js` and `sugar-web/`)
  and build with it:

  ```bash
  edugame build my-game --sugarizer --sugar-lib path/to/SomeActivity.activity/lib
  ```

  sugar-web is Apache 2.0 licensed; keep its license file in the folder.

- **Without it**, the activity still works and saves in the browser, on that device only.

The helper uses the learner's name and language from Sugarizer when it has sugar-web.

## Trying it

Sugarizer's web version can run from a folder: put the activity in its `activities` folder and
open Sugarizer in the browser. Check the activity opens, saves, and carries on after you close
and reopen it from the Journal.
