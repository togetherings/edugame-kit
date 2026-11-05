/* EduGame save helper, version 1.
 *
 * One small script that lets the same game save its progress (and, for Scored
 * Games, its scores) wherever it's played. It finds out where it is and uses
 * the best way to save there:
 *
 *   "kolibri-games"  the Kolibri Games plugin's games page (saves in the learner's
 *                    account, scores on the plugin's scoreboards and challenges)
 *   "scorm"          a SCORM 1.2 connection: Kolibri channels (Learn), Moodle and
 *                    other learning systems (saved with the learner's record)
 *   "sugarizer"      Sugarizer, when its sugar-web library is in the activity
 *                    (saved in the Journal)
 *   "local"          anywhere else: RACHEL, Kiwix, a web server or a folder
 *                    (saved in this browser only)
 *
 * The game uses the same calls everywhere:
 *
 *   EduGame.ready()          -> Promise of {save, best, plays, settings, language, platform, player, canExit}
 *   EduGame.save(data)       -> Promise; keep the save small (at most MAX_SAVE characters as JSON)
 *   EduGame.complete()       mark the activity as done (Kolibri and learning systems show progress)
 *   EduGame.start()          Scored Games: a round begins (the helper times it)
 *   EduGame.finish(score)    Scored Games: the round ended -> Promise of {score, seconds, best, newBest}
 *   EduGame.t(key, vars)     a translated string: t("found", {n: 3}) for "Found {n}!"
 *   EduGame.translatePage()  fill in every element with data-t="key" (done by ready())
 *   EduGame.exit()           leave the game, where the platform has a way back (ready() says canExit)
 *
 * Extras that only do something on the Kolibri Games games page (elsewhere
 * they do nothing, so a game can always call them):
 *
 *   EduGame.move(type, data)  report a move, so coaches can see how a round went
 *   EduGame.scoreboard()      -> Promise of the plugin's scoreboard {rows: [...]}, or null
 *   EduGame.on("timeup", fn)  the coach's time limit ran out
 *   ready() also gives `rules` ({counts, time_limit, ...}) and `challenge`, or null
 *
 * What it saves, in SCORM cmi.suspend_data and in this browser, is one JSON object:
 *   {"_v": 1, "_save": <the game's save>, "main": [best score, seconds, times played]}
 * Kolibri Games reads "main" to show scoreboards for Scored Games in channels,
 * and skips keys starting with "_" (see kolibri-games' docs/CHANNEL_GAMES.md).
 *
 * The build tool (edugame build) writes edugame-config.js next to this file,
 * with the game's settings from edugame.json and every translation, so this
 * also works when the game is opened straight from a folder.
 */
(function () {
  "use strict";
  if (window.EduGame) return;

  var VERSION = 1;
  // SCORM 1.2 allows 4096 characters in suspend_data. The scores and the
  // helper's own keys need about 100 of them.
  var MAX_SAVE = 3900;
  var RTL = ["ar", "fa", "he", "ps", "ur", "yi", "dv", "ckb"];

  var config = window.EDUGAME_CONFIG || { id: "game", type: "saved", languages: ["en"], strings: { en: {} } };
  var scoring = config.scoring || null;
  var record = { _v: VERSION };   // what's saved (see above)
  var backend = null;              // one of the backends below
  var info = null;                 // what ready() resolves with
  var strings = {};                // translations for the chosen language
  var roundStart = null;           // Date.now() when start() was called
  var readyPromise = null;

  function now() { return Date.now(); }

  function cleanLanguage(code) {
    return String(code || "").replace("_", "-").trim();
  }

  /** The best match for `wanted` among the game's languages, or null. */
  function matchLanguage(wanted) {
    wanted = cleanLanguage(wanted).toLowerCase();
    if (!wanted) return null;
    var langs = config.languages || [];
    for (var i = 0; i < langs.length; i++) if (langs[i].toLowerCase() === wanted) return langs[i];
    var base = wanted.split("-")[0];
    for (var j = 0; j < langs.length; j++) if (langs[j].toLowerCase().split("-")[0] === base) return langs[j];
    return null;
  }

  /** ?lang= in the address, then the platform's language, then the browser's, then the game's first. */
  function chooseLanguage(platformLanguage) {
    var m = /[?&]lang=([A-Za-z0-9_-]+)/.exec(location.search);
    var tries = [m && m[1], platformLanguage].concat(navigator.languages || [navigator.language]);
    for (var i = 0; i < tries.length; i++) {
      var found = matchLanguage(tries[i]);
      if (found) return found;
    }
    return (config.languages || ["en"])[0];
  }

  function t(key, vars) {
    var text = strings[key];
    if (text === undefined) text = (config.strings[(config.languages || ["en"])[0]] || {})[key];
    if (text === undefined) return key;
    return String(text).replace(/\{(\w+)\}/g, function (all, name) {
      return vars && vars[name] !== undefined ? vars[name] : all;
    });
  }

  function translatePage(root) {
    root = root || document;
    var els = root.querySelectorAll("[data-t]");
    for (var i = 0; i < els.length; i++) els[i].textContent = t(els[i].getAttribute("data-t"));
    // data-t-attr="placeholder:key,title:key2" for attributes
    var attrs = root.querySelectorAll("[data-t-attr]");
    for (var k = 0; k < attrs.length; k++) {
      attrs[k].getAttribute("data-t-attr").split(",").forEach(function (pair) {
        var p = pair.split(":");
        if (p.length === 2) attrs[k].setAttribute(p[0].trim(), t(p[1].trim()));
      });
    }
  }

  function setLanguage(code) {
    strings = config.strings[code] || {};
    var html = document.documentElement;
    html.lang = code;
    html.dir = RTL.indexOf(code.split("-")[0]) >= 0 ? "rtl" : "ltr";
    if (strings.title) document.title = strings.title;
  }

  function defaultSettings() {
    var out = {};
    (config.settings || []).forEach(function (s) { out[s.key] = s["default"]; });
    return out;
  }

  // -------------------------------------------------------------- scores

  /** True if score a (with seconds) beats score b. */
  function better(a, aSecs, b, bSecs) {
    if (b === null || b === undefined) return true;
    if (a !== b) return scoring && scoring.order === "asc" ? a < b : a > b;
    return scoring && scoring.tiebreak === "seconds" && aSecs < bSecs;
  }

  /** 0-100 for learning systems' gradebooks. scoring.grade = {full, zero} says which
   *  scores get 100% and 0%; without it, scoring.min and max are used. */
  function percent(score) {
    if (!scoring) return null;
    var g = scoring.grade || {};
    var full = typeof g.full === "number" ? g.full : (scoring.order === "asc" ? scoring.min : scoring.max);
    var zero = typeof g.zero === "number" ? g.zero : (scoring.order === "asc" ? scoring.max : scoring.min);
    if (typeof full !== "number" || typeof zero !== "number" || full === zero) return null;
    var p = (score - zero) / (full - zero);
    return Math.round(Math.max(0, Math.min(1, p)) * 100);
  }

  /** Update record.main with a finished round; returns true for a new best. */
  function addScore(score, seconds) {
    var main = record.main || [null, null, 0];
    var isBest = better(score, seconds, main[0], main[1]);
    if (isBest) { main[0] = score; main[1] = Math.round(seconds * 10) / 10; }
    main[2] = (main[2] || 0) + 1;
    record.main = main;
    return isBest;
  }

  function parseRecord(text) {
    try {
      var data = typeof text === "string" ? JSON.parse(text) : text;
      if (data && typeof data === "object" && !Array.isArray(data)) return data;
    } catch (e) { /* not ours, or empty */ }
    return { _v: VERSION };
  }

  // ------------------------------------------------------------ backends
  // Each backend has: name, open() -> Promise of {record, language, player},
  // write(record) -> Promise, and optional complete(), start(), finish(), exit().

  function findScorm() {
    // The SCORM 1.2 API object is on this window or one of its parents.
    var w = window;
    for (var i = 0; i < 10 && w; i++) {
      try { if (w.API && typeof w.API.LMSInitialize === "function") return w.API; } catch (e) { return null; }
      if (w.parent === w) break;
      w = w.parent;
    }
    try { if (window.opener && window.opener.API) return window.opener.API; } catch (e2) { /* other origin */ }
    return null;
  }

  function scormBackend(api) {
    function get(name) { try { return api.LMSGetValue(name) || ""; } catch (e) { return ""; } }
    // Systems answer "true" or true; Kolibri's may answer nothing. Only "false" means no.
    function set(name, value) {
      try { var ok = api.LMSSetValue(name, String(value)); return ok !== false && ok !== "false"; } catch (e) { return false; }
    }
    function commit() { try { api.LMSCommit(""); } catch (e) { /* the system may not need it */ } }
    var finished = false;
    return {
      name: "scorm",
      open: function () {
        try { api.LMSInitialize(""); } catch (e) { /* already started */ }
        if (get("cmi.core.lesson_status") === "not attempted") set("cmi.core.lesson_status", "incomplete");
        commit();
        // Leaving the page ends the SCORM session, which saves for good in most systems.
        window.addEventListener("pagehide", function () {
          if (finished) return;
          finished = true;
          commit();
          try { api.LMSFinish(""); } catch (e) { /* closed already */ }
        });
        return Promise.resolve({
          record: parseRecord(get("cmi.suspend_data")),
          language: get("cmi.student_preference.language"),
          player: { name: get("cmi.core.student_name") }
        });
      },
      write: function (rec) {
        var ok = set("cmi.suspend_data", JSON.stringify(rec));
        commit();
        return ok ? Promise.resolve() : Promise.reject(new Error("The learning system didn't take the save."));
      },
      complete: function () { set("cmi.core.lesson_status", "completed"); commit(); },
      finish: function (score) {
        var p = percent(score);
        if (p !== null) {
          set("cmi.core.score.min", 0);
          set("cmi.core.score.max", 100);
          // Keep the best percentage: learning systems grade by score.raw.
          var old = parseFloat(get("cmi.core.score.raw"));
          if (isNaN(old) || p > old) set("cmi.core.score.raw", p);
        }
        set("cmi.core.lesson_status", "completed");
        commit();
        return Promise.resolve(null);
      }
    };
  }

  function localBackend() {
    var key = "edugame:" + config.id;
    return {
      name: "local",
      open: function () {
        var text = null;
        try { text = window.localStorage.getItem(key); } catch (e) { /* storage blocked */ }
        return Promise.resolve({ record: parseRecord(text), language: null, player: null });
      },
      write: function (rec) {
        try { window.localStorage.setItem(key, JSON.stringify(rec)); return Promise.resolve(); } catch (e) {
          return Promise.reject(new Error("This browser won't keep the save (private browsing?)."));
        }
      }
    };
  }

  /** The Kolibri Games plugin serves games under .../play/<token>/ and its SDK at __kolibri_games__/sdk.js. */
  function looksLikeKolibriGames() {
    return window.parent !== window && /\/play\/[A-Za-z0-9_\-:.]+\//.test(location.pathname);
  }

  function loadScript(src, ms) {
    return new Promise(function (resolve) {
      var s = document.createElement("script");
      var timer = setTimeout(function () { resolve(false); }, ms);
      s.onload = function () { clearTimeout(timer); resolve(true); };
      s.onerror = function () { clearTimeout(timer); resolve(false); };
      s.src = src;
      document.head.appendChild(s);
    });
  }

  function kolibriGamesBackend(KG) {
    var hello = null;
    var attempt = null;
    return {
      name: "kolibri-games",
      open: function () {
        return KG.ready().then(function (h) {
          hello = h;
          return KG.getState();
        }).then(function (state) {
          var rec = state && typeof state === "object" ? state : { _v: VERSION };
          var counted = hello.summary && hello.summary.counted;
          if (counted && typeof counted.score === "number") {
            rec.main = [counted.score, counted.seconds, (hello.summary.attempts || 0)];
          }
          return { record: rec, language: hello.language, player: hello.player, settings: hello.settings,
                   rules: hello.rules, challenge: hello.challenge };
        });
      },
      write: function (rec) { return KG.setState(rec); },
      start: function () {
        return KG.start({ resume: false }).then(function (r) { attempt = r.attempt; return r; });
      },
      finish: function (score) {
        return KG.finish({ score: score }).then(function (r) { attempt = null; return r; });
      },
      move: function (type, data) { return KG.move(type, data); },
      scoreboard: function () { return KG.scoreboard(); },
      on: function (name, fn) { KG.on(name, fn); },
      exit: function () { KG.exit(); }
    };
  }

  /** Sugarizer, when the activity includes sugar-web (see docs/SUGARIZER.md). */
  function sugarizerBackend(requirejs) {
    var activity = null;
    return {
      name: "sugarizer",
      open: function () {
        return new Promise(function (resolve, reject) {
          requirejs(["sugar-web/activity/activity", "sugar-web/env"], function (act, env) {
            activity = act;
            activity.setup();
            env.getEnvironment(function (err, environment) {
              var user = (environment && environment.user) || {};
              var base = { record: { _v: VERSION }, language: user.language, player: { name: user.name } };
              if (err || !environment.objectId) return resolve(base);
              activity.getDatastoreObject().loadAsText(function (e2, metadata, text) {
                base.record = parseRecord(e2 ? null : text);
                resolve(base);
              });
            });
          }, reject);
        });
      },
      write: function (rec) {
        return new Promise(function (resolve, reject) {
          var obj = activity.getDatastoreObject();
          obj.setDataAsText(JSON.stringify(rec));
          obj.save(function (err) { return err ? reject(err) : resolve(); });
        });
      },
      exit: function () { activity.close(); }
    };
  }

  function pickBackend() {
    if (looksLikeKolibriGames()) {
      return loadScript("__kolibri_games__/sdk.js", 4000).then(function (ok) {
        return ok && window.KolibriGames ? kolibriGamesBackend(window.KolibriGames) : pickOther();
      });
    }
    return Promise.resolve(pickOther());
  }

  function pickOther() {
    var api = findScorm();
    if (api) return scormBackend(api);
    if (typeof window.requirejs === "function" && config.sugarizer) return sugarizerBackend(window.requirejs);
    return localBackend();
  }

  // ------------------------------------------------------------- the API

  function ready() {
    if (readyPromise) return readyPromise;
    readyPromise = pickBackend().then(function (b) {
      backend = b;
      return b.open().catch(function (err) {
        // A platform that fails to open shouldn't stop the game: save in this browser instead.
        console.warn("EduGame: " + b.name + " didn't open, saving in this browser.", err);
        backend = localBackend();
        return backend.open();
      });
    }).then(function (opened) {
      record = opened.record || { _v: VERSION };
      var language = chooseLanguage(opened.language);
      setLanguage(language);
      translatePage();
      var main = record.main || [null, null, 0];
      info = {
        save: record._save === undefined ? null : record._save,
        best: main[0],
        bestSeconds: main[1],
        plays: main[2] || 0,
        settings: opened.settings || defaultSettings(),
        language: language,
        platform: backend.name,
        player: opened.player || null,
        canExit: !!backend.exit,   // show a "back" button only when the platform has somewhere to go
        rules: opened.rules || null,
        challenge: opened.challenge || null
      };
      return info;
    });
    return readyPromise;
  }

  function save(data) {
    var text = JSON.stringify(data === undefined ? null : data);
    return ready().then(function () {
      // The plugin keeps up to 64 KB; everywhere else the SCORM 1.2 limit applies, so games
      // behave the same on every platform.
      if (backend.name !== "kolibri-games" && text.length > MAX_SAVE) {
        throw new Error("The save is too big (" + text.length + " characters; at most " + MAX_SAVE + ").");
      }
      record._save = data;
      return backend.write(record);
    });
  }

  function start() {
    return ready().then(function () {
      roundStart = now();
      return backend.start ? backend.start() : null;
    });
  }

  function finish(score) {
    if (typeof score !== "number" || !isFinite(score)) return Promise.reject(new Error("finish() needs a number."));
    return ready().then(function () {
      var seconds = roundStart === null ? 0 : (now() - roundStart) / 1000;
      roundStart = null;
      var isBest = addScore(score, seconds);
      var platform = backend.finish ? backend.finish(score) : Promise.resolve(null);
      // The plugin keeps scores itself; everywhere else they're kept in the record.
      var kept = backend.name === "kolibri-games" ? Promise.resolve() : backend.write(record);
      return Promise.all([platform, kept]).then(function (results) {
        info.best = record.main[0];
        info.bestSeconds = record.main[1];
        info.plays = record.main[2];
        return { score: score, seconds: seconds, best: record.main[0], newBest: isBest, platform: results[0] };
      });
    });
  }

  function move(type, data) {
    return ready().then(function () { return backend.move ? backend.move(type, data) : null; });
  }

  function scoreboard() {
    return ready().then(function () { return backend.scoreboard ? backend.scoreboard() : null; });
  }

  function on(name, fn) {
    ready().then(function () { if (backend.on) backend.on(name, fn); });
  }

  function complete() {
    ready().then(function () { if (backend.complete) backend.complete(); });
  }

  function exit() {
    if (backend && backend.exit) backend.exit();
  }

  window.EduGame = {
    version: VERSION,
    MAX_SAVE: MAX_SAVE,
    config: config,
    ready: ready,
    save: save,
    complete: complete,
    start: start,
    finish: finish,
    move: move,
    scoreboard: scoreboard,
    on: on,
    t: t,
    translatePage: translatePage,
    exit: exit,
    // for tests and the test page
    _better: better,
    _percent: percent
  };
})();
