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
 *   EduGame.ready()             -> Promise of {save, best, results, plays, settings, language,
 *                                  platform, player, canExit, rules, challenge}
 *   EduGame.save(data)          -> Promise; keep the save small (at most MAX_SAVE characters as JSON)
 *   EduGame.complete()          the learner has finished the activity (sets SCORM status "passed")
 *   EduGame.start({board})      Scored Games: a round begins (the helper times it); board = the level
 *   EduGame.finish(score, {board, passed})
 *                               Scored Games: the round ended. `score` is a number, or an object with
 *                               a value for each field: finish({acc: 97, wpm: 41}). With passed: false
 *                               the round is played but not kept as a result.
 *                               -> Promise of {score, values, seconds, kept, best, newBest, platform}
 *   EduGame.t(key, vars)        a translated string: t("found", {n: 3}) for "Found {n}!"
 *   EduGame.translatePage()     fill in every element with data-t="key" (done by ready())
 *   EduGame.exit()              leave the game, where the platform has a way back (ready() says canExit)
 *
 * Extras that only do something on the Kolibri Games games page (elsewhere
 * they do nothing, so a game can always call them):
 *
 *   EduGame.move(type, data)    report a move, so coaches can see how a round went
 *   EduGame.scoreboard({board}) -> Promise of the plugin's scoreboard {rows: [...], boards}, or null
 *   EduGame.on("timeup", fn)    the coach's time limit ran out
 *   ready() also gives `rules` ({counts, time_limit, ...}) and `challenge`, or null
 *
 * WHAT IS SAVED. In SCORM cmi.suspend_data and in this browser, one JSON object:
 *   {"_v": 1, "_save": <the game's save>, "main": [7, 41.5, 3]}
 * Keys starting with "_" belong to the helper and the game. Every other key is a
 * board (a level, or "main" for a game without levels) holding the learner's
 * kept result as a list: one value for each of scoring.fields, in that order.
 * Which round is kept follows scoring.counts: the first, the best, the latest,
 * or every round added up. Kolibri Games reads these lists to show scoreboards
 * for Scored Games in channels (kolibri-games docs/SCORING.md).
 *
 * KOLIBRI. Scores are never sent to Kolibri itself: Kolibri reads a SCORM score
 * as how much of a resource is done, so a game would only count as done at 100.
 * In Kolibri the helper only sets the status: "incomplete", then "passed"
 * (Kolibri ignores "completed"). Other learning systems get a 0-100 grade in
 * cmi.core.score.raw when scoring.grade says how to work it out.
 *
 * Kolibri can add its SCORM connection a moment after the game has loaded, so
 * inside a frame the helper waits for it briefly, and keeps looking for a few
 * seconds more after starting (then moves what it saved in the browser there).
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
  // scoring (from edugame-config.js): {fields: [{key, order, source, total}], rank_by,
  // counts, primary, levels, grade}. See edugame/scoring.py.

  var MAIN = "main";             // the board of a game without levels
  var fields = scoring ? scoring.fields : [];

  function round1(n) { return Math.round(n * 10) / 10; }

  /** A board's kept result as an object {key: value}, from the list that's saved. */
  function fromList(list) {
    if (!Array.isArray(list)) return null;
    var out = {};
    fields.forEach(function (f, i) { out[f.key] = list[i] === undefined ? null : list[i]; });
    return out;
  }

  /** The list that's saved, in fields order. */
  function toList(values) {
    return fields.map(function (f) { var v = values[f.key]; return v === undefined ? null : v; });
  }

  /** Compare two results by rank_by: below 0 if a is better, above 0 if b is. Missing values rank last. */
  function compare(a, b) {
    for (var i = 0; i < scoring.rank_by.length; i++) {
      var key = scoring.rank_by[i];
      var f = fields.filter(function (x) { return x.key === key; })[0];
      var av = a[key], bv = b[key];
      var aMissing = av === null || av === undefined, bMissing = bv === null || bv === undefined;
      if (aMissing || bMissing) {
        if (aMissing !== bMissing) return aMissing ? 1 : -1;
        continue;
      }
      if (av !== bv) return (f.order === "asc" ? av - bv : bv - av) < 0 ? -1 : 1;
    }
    return 0;
  }

  /** Add one finished round to a board's kept result, following scoring.counts. */
  function keep(old, round, plays) {
    var counts = scoring.counts, out = {}, newBest = !old || compare(round, old) < 0;
    fields.forEach(function (f) {
      var o = old ? old[f.key] : null, n = round[f.key];
      if (f.source === "plays") { out[f.key] = plays; return; }
      if (!old) { out[f.key] = n; return; }
      if (counts === "first") out[f.key] = o;
      else if (counts === "latest") out[f.key] = n;
      else if (counts === "best") out[f.key] = newBest ? n : o;
      else {  // total: every round added up, each field by its own rule
        if (n === null || n === undefined) out[f.key] = o;
        else if (o === null || o === undefined) out[f.key] = n;
        else if (f.total === "sum") out[f.key] = round1(o + n);
        else if (f.total === "average") out[f.key] = round1(o + (n - o) / plays);
        else if (f.total === "min") out[f.key] = Math.min(o, n);
        else if (f.total === "max") out[f.key] = Math.max(o, n);
        else if (f.total === "latest") out[f.key] = n;
        else out[f.key] = newBest ? n : o;
      }
    });
    return { values: out, newBest: newBest };
  }

  /** The values a game reported, checked: finish(12) or finish({acc: 97, wpm: 41}). */
  function roundValues(reported, seconds) {
    var values = typeof reported === "number" ? {} : reported;
    if (typeof reported === "number") values[scoring.primary] = reported;
    if (!values || typeof values !== "object") throw new Error("finish() needs a number, or a value for each score.");
    var out = {};
    fields.forEach(function (f) {
      if (f.source === "time") { out[f.key] = round1(seconds); return; }
      if (f.source === "plays") return;
      var v = values[f.key];
      if (v === undefined || v === null) {
        if (scoring.rank_by.indexOf(f.key) >= 0) throw new Error("finish() needs a value for " + f.key + ".");
        out[f.key] = null;
        return;
      }
      if (typeof v !== "number" || !isFinite(v)) throw new Error(f.key + " must be a number.");
      out[f.key] = v;
    });
    return out;
  }

  /** 0-100 for learning systems' gradebooks, from scoring.grade {field, full, zero}; null without one. */
  function percent(values) {
    var g = scoring && scoring.grade;
    if (!g || !values || typeof values[g.field] !== "number") return null;
    var p = (values[g.field] - g.zero) / (g.full - g.zero);
    return Math.round(Math.max(0, Math.min(1, p)) * 100);
  }

  /** Every board's kept result, as objects: {main: {score: 7, time: 41.5, plays: 3}}. */
  function results() {
    var out = {};
    Object.keys(record).forEach(function (k) {
      if (k.charAt(0) !== "_" && Array.isArray(record[k])) out[k] = fromList(record[k]);
    });
    return out;
  }

  function cleanBoard(board) {
    if (board === undefined || board === null || board === "" || board === MAIN) return MAIN;
    board = String(board);
    if (!/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$/.test(board)) throw new Error("A board (level) id is letters, digits, '.', '_', ':' or '-'.");
    return board;
  }

  function parseRecord(text) {
    try {
      var data = typeof text === "string" ? JSON.parse(text) : text;
      if (data && typeof data === "object" && !Array.isArray(data)) return data;
    } catch (e) { /* not ours, or empty */ }
    return { _v: VERSION };
  }

  function hasContent(rec) {
    return Object.keys(rec || {}).some(function (k) { return k !== "_v"; });
  }

  /** Kolibri itself (Learn), where scores mustn't be sent (see the top of this file). */
  function inKolibri() {
    // Kolibri gives HTML5 apps a "kolibri" object (its HTML5 API, with getVersion) and serves
    // them from addresses with /zipcontent/ in them.
    function isKolibri(w) {
      try { return !!(w && w.kolibri && typeof w.kolibri.getVersion === "function"); } catch (e) { return false; }
    }
    return isKolibri(window) || isKolibri(window.parent) || /\/zipcontent\//.test(location.pathname);
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
      // "passed", never "completed": Kolibri ignores "completed".
      complete: function () { set("cmi.core.lesson_status", "passed"); commit(); },
      finish: function (round, kept, passed) {
        var p = inKolibri() ? null : percent(kept);
        if (p !== null) {
          set("cmi.core.score.min", 0);
          set("cmi.core.score.max", 100);
          // Keep the best percentage: learning systems grade by score.raw.
          var old = parseFloat(get("cmi.core.score.raw"));
          if (isNaN(old) || p > old) set("cmi.core.score.raw", p);
        }
        if (passed) set("cmi.core.lesson_status", "passed");
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
    return {
      name: "kolibri-games",
      open: function () {
        return KG.ready().then(function (h) {
          hello = h;
          return KG.getState();
        }).then(function (state) {
          // The plugin keeps the scores itself; its summary says which results count.
          var rec = state && typeof state === "object" ? state : { _v: VERSION };
          var summary = hello.summary || {};
          var boards = summary.boards || {};
          if (summary.counted) boards[MAIN] = summary.counted;
          Object.keys(boards).forEach(function (b) {
            if (boards[b] && boards[b].values) rec[b] = toList(boards[b].values);
          });
          return { record: rec, language: hello.language, player: hello.player, settings: hello.settings,
                   rules: hello.rules, challenge: hello.challenge };
        });
      },
      write: function (rec) {
        // Only the game's own save goes to the plugin: it keeps the scores.
        return KG.setState({ _v: VERSION, _save: rec._save });
      },
      start: function (board) {
        return KG.start({ resume: false, board: board === MAIN ? "" : board });
      },
      finish: function (round, kept, passed) {
        var values = {};
        fields.forEach(function (f) { if (f.source === "game") values[f.key] = round[f.key]; });
        if (!passed) {
          // Not a result: keep the moves for coaches, and end the attempt without a score.
          return KG.move("not_passed", values).then(function () { return KG.abandon(); }).then(function () { return null; });
        }
        return KG.finish({ values: values });
      },
      move: function (type, data) { return KG.move(type, data); },
      scoreboard: function (board) { return KG.scoreboard({ board: board === MAIN ? "" : board }); },
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
    return pickOther();
  }

  /** Resolves with the SCORM API once it's there, or null after `ms`. */
  function waitForScorm(ms) {
    return new Promise(function (resolve) {
      var api = findScorm(), waited = 0;
      if (api || ms <= 0) return resolve(api);
      var timer = setInterval(function () {
        api = findScorm();
        waited += 100;
        if (api || waited >= ms) { clearInterval(timer); resolve(api); }
      }, 100);
    });
  }

  var inFrame = window.parent !== window;

  function pickOther() {
    // Inside a frame (Kolibri, Moodle), wait a moment for the SCORM connection.
    return waitForScorm(inFrame ? 1500 : 0).then(function (api) {
      if (api) return scormBackend(api);
      if (typeof window.requirejs === "function" && config.sugarizer) return sugarizerBackend(window.requirejs);
      return localBackend();
    });
  }

  /** Saving in the browser inside a frame: if a SCORM connection turns up later, move there. */
  function watchForLateScorm() {
    if (!inFrame || backend.name !== "local") return;
    waitForScorm(10000).then(function (api) {
      if (!api || backend.name !== "local") return;
      var late = scormBackend(api);
      late.open().then(function (opened) {
        backend = late;
        info.platform = late.name;
        if (hasContent(opened.record)) record = opened.record;  // the learner's record wins
        else return late.write(record);
      });
    });
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
      info = {
        save: record._save === undefined ? null : record._save,
        settings: opened.settings || defaultSettings(),
        language: language,
        platform: backend.name,
        player: opened.player || null,
        canExit: !!backend.exit,   // show a "back" button only when the platform has somewhere to go
        rules: opened.rules || null,
        challenge: opened.challenge || null
      };
      updateInfo();
      watchForLateScorm();
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

  /** info.results (every board), and best, bestSeconds and plays (the main board), for games with one score. */
  function updateInfo() {
    if (!info) return;
    info.results = scoring ? results() : {};
    var main = info.results[MAIN] || {};
    var timeField = fields.filter(function (f) { return f.source === "time"; })[0];
    var playsField = fields.filter(function (f) { return f.source === "plays"; })[0];
    info.best = scoring && main[scoring.primary] !== undefined ? main[scoring.primary] : null;
    info.bestSeconds = timeField && main[timeField.key] !== undefined ? main[timeField.key] : null;
    info.plays = playsField && main[playsField.key] ? main[playsField.key] : 0;
  }

  var round = null;  // {board, startedAt} between start() and finish()

  /** Tell the page what happened ("edugame:start", "edugame:finish", "edugame:complete").
   *  Nothing in a game zip listens; a GitHub Pages site built with "edugame pages" counts them. */
  function announce(name, detail) {
    try { document.dispatchEvent(new CustomEvent("edugame:" + name, { detail: detail || {} })); } catch (e) { /* old browser */ }
  }

  function start(opts) {
    return ready().then(function () {
      var board = cleanBoard(opts && opts.board);
      round = { board: board, startedAt: now() };
      announce("start", { board: board });
      return backend.start ? backend.start(board) : null;
    });
  }

  function finish(reported, opts) {
    if (!scoring) return Promise.reject(new Error("Saved Games have no scores: use EduGame.save()."));
    opts = opts || {};
    return ready().then(function () {
      var board = cleanBoard(opts.board !== undefined ? opts.board : round && round.board);
      var seconds = round ? (now() - round.startedAt) / 1000 : 0;
      round = null;
      var values = roundValues(reported, seconds);
      var passed = opts.passed !== false;
      var old = fromList(record[board]);
      var playsField = fields.filter(function (f) { return f.source === "plays"; })[0];
      var plays = ((old && playsField && old[playsField.key]) || 0) + 1;
      var kept = old, newBest = false;
      if (passed) {
        var k = keep(old, values, plays);
        kept = k.values;
        newBest = k.newBest;
      } else if (old && playsField) {
        kept = {};
        Object.keys(old).forEach(function (k) { kept[k] = old[k]; });
        kept[playsField.key] = plays;
      }
      if (kept) record[board] = toList(kept);
      var platform = backend.finish ? backend.finish(values, kept, passed) : Promise.resolve(null);
      // The plugin keeps scores itself; everywhere else they're kept in the record.
      var saved = backend.name === "kolibri-games" ? Promise.resolve() : backend.write(record);
      announce("finish", { board: board, passed: passed });
      return Promise.all([platform, saved]).then(function (out) {
        updateInfo();
        return {
          score: values[scoring.primary],
          values: values,
          seconds: seconds,
          board: board,
          passed: passed,
          kept: kept,
          best: kept ? kept[scoring.primary] : null,
          newBest: newBest,
          platform: out[0]
        };
      });
    });
  }

  function move(type, data) {
    return ready().then(function () { return backend.move ? backend.move(type, data) : null; });
  }

  function scoreboard(opts) {
    return ready().then(function () {
      return backend.scoreboard ? backend.scoreboard(cleanBoard(opts && opts.board)) : null;
    });
  }

  function on(name, fn) {
    ready().then(function () { if (backend.on) backend.on(name, fn); });
  }

  function complete() {
    announce("complete");
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
    _compare: function (a, b) { return compare(a, b); },
    _keep: function (old, r, plays) { return keep(old, r, plays); },
    _percent: function (values) { return percent(values); }
  };
})();
