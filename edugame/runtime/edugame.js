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
 *   EduGame.abandon()           the round ends without a result
 *   EduGame.exit()              leave the game, where the platform has a way back (ready() says canExit)
 *
 * Words and languages (docs/LANGUAGES.md). The words are in lang/<code>.json; the
 * helper picks the language: the learner's own choice (kept in their save), then
 * ?lang=, the platform's language, the browser's, and the game's default.
 *
 *   EduGame.t(key, vars)        a word in the current language: t("found", {n: 3}) for "Found {n}!".
 *                               A plural set {"one": ..., "other": ...} chooses by {n}.
 *   EduGame.lines(key)          a list of paragraphs, as an array
 *   EduGame.number(n, decimals) a number written the way the language writes it
 *   EduGame.translatePage()     fill in every element with data-t="key" (done by ready())
 *   EduGame.language()          the current language code; EduGame.languages(): [{code, name, dir}]
 *   EduGame.setLanguage(code)   change it (and remember the learner's choice)
 *
 * Options. The helper puts a header at the top of the page, with the title and an
 * Options button (only the button on the Kolibri Games games page). The panel has
 * Appearance (light, dark or auto: <html data-theme>), Language and the game's own options.
 *
 *   EduGame.addOption({key, label, choices: [{value, label}], default, keep: "device"|"learner"})
 *   EduGame.option(key)         the chosen value
 *   EduGame.openOptions()       open the panel (any element with data-edugame-options does too)
 *   EduGame.theme(), EduGame.setTheme("dark")
 *   EduGame.on("languagechange" | "themechange" | "optionchange", fn)
 *
 * Content (maps, lessons, word lists: the folders under "content" in edugame.json).
 *
 *   EduGame.load("words/fr.json")          -> Promise of the data, or null
 *   EduGame.loadLanguage("maps/us/lang")   -> Promise of the current language's file, over the default's
 *   EduGame.loadLanguage(dir, {merge: false}) the nearest language's file only (an edition)
 *   EduGame.config.package      the package this build is ({id, title, config}), or undefined
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
 *   {"_v": 1, "_save": <the game's save>, "_lang": "fr", "_options": {...}, "main": [7, 41.5, 3]}
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
  var roundStart = null;           // Date.now() when start() was called
  var readyPromise = null;

  function now() { return Date.now(); }

  // ----------------------------------------------------------- languages
  // Every word a game shows is in lang/<code>.json, one file per language
  // (edugame build puts them all in edugame-config.js as config.strings).
  // A value is text, a list of paragraphs, or a plural set like
  //   {"one": "{n} guess", "other": "{n} guesses"}
  // Keys starting with "_" aren't words: "_language" ({name, dir}) and
  // "_notes" (help for translators). A regional file (en-GB.json) only needs
  // the words that differ: the rest comes from en.json, then the default.

  var LANGS = config.languages || ["en"];  // the game's languages; the first is the default
  var DEFAULT = LANGS[0];
  var current = DEFAULT;                    // the language in use
  var LANG_KEY = "edugame:" + config.id + ":language";

  // The kit's own words (the Options button and panel). A game's lang/ files can
  // replace any of them by using the same key.
  var KIT_WORDS = {
    en: { "kit.options": "Options", "kit.options_title": "Options", "kit.appearance": "Appearance",
          "kit.theme_light": "Light", "kit.theme_dark": "Dark", "kit.theme_auto": "Auto",
          "kit.theme_auto_hint": "(follows this device's light or dark setting)", "kit.language": "Language",
          "kit.apply": "Apply", "kit.back": "Back" },
    fr: { "kit.options": "Options", "kit.options_title": "Options", "kit.appearance": "Apparence",
          "kit.theme_light": "Clair", "kit.theme_dark": "Sombre", "kit.theme_auto": "Auto",
          "kit.theme_auto_hint": "(suit le réglage clair ou sombre de cet appareil)", "kit.language": "Langue",
          "kit.apply": "Appliquer", "kit.back": "Retour" },
    es: { "kit.options": "Opciones", "kit.options_title": "Opciones", "kit.appearance": "Apariencia",
          "kit.theme_light": "Claro", "kit.theme_dark": "Oscuro", "kit.theme_auto": "Automático",
          "kit.theme_auto_hint": "(sigue el ajuste claro u oscuro de este dispositivo)", "kit.language": "Idioma",
          "kit.apply": "Aplicar", "kit.back": "Volver" },
    pt: { "kit.options": "Opções", "kit.options_title": "Opções", "kit.appearance": "Aparência",
          "kit.theme_light": "Claro", "kit.theme_dark": "Escuro", "kit.theme_auto": "Automático",
          "kit.theme_auto_hint": "(segue a configuração clara ou escura deste dispositivo)", "kit.language": "Idioma",
          "kit.apply": "Aplicar", "kit.back": "Voltar" },
    sw: { "kit.options": "Chaguo", "kit.options_title": "Chaguo", "kit.appearance": "Mwonekano",
          "kit.theme_light": "Mwanga", "kit.theme_dark": "Giza", "kit.theme_auto": "Otomatiki",
          "kit.theme_auto_hint": "(hufuata mpangilio wa mwanga au giza wa kifaa hiki)", "kit.language": "Lugha",
          "kit.apply": "Tumia", "kit.back": "Rudi" }
  };

  function cleanLanguage(code) {
    return String(code || "").replace(/_/g, "-").trim();
  }

  function base(code) { return code.split("-")[0].toLowerCase(); }

  /** The best match for `wanted` among the game's languages, or null: exact, then the same base language. */
  function matchLanguage(wanted) {
    wanted = cleanLanguage(wanted).toLowerCase();
    if (!wanted) return null;
    for (var i = 0; i < LANGS.length; i++) if (LANGS[i].toLowerCase() === wanted) return LANGS[i];
    for (var j = 0; j < LANGS.length; j++) if (LANGS[j].toLowerCase() === base(wanted)) return LANGS[j];
    for (var k = 0; k < LANGS.length; k++) if (base(LANGS[k]) === base(wanted)) return LANGS[k];
    return null;
  }

  function storedLanguage() {
    try { return window.localStorage.getItem(LANG_KEY); } catch (e) { return null; }
  }

  /** The learner's own choice first, then ?lang=, the platform's language, the browser's, the game's default. */
  function chooseLanguage(platformLanguage) {
    var m = /[?&]lang=([A-Za-z0-9_-]+)/.exec(location.search);
    var tries = [record._lang, storedLanguage(), m && m[1], platformLanguage]
      .concat(navigator.languages || [navigator.language]);
    for (var i = 0; i < tries.length; i++) {
      var found = matchLanguage(tries[i]);
      if (found) return found;
    }
    return DEFAULT;
  }

  /** The files to look a word up in, best first: fr-CA, then fr, then the default language. */
  function chain(code) {
    var out = [];
    function add(c) {
      for (var i = 0; i < LANGS.length; i++) {
        if (LANGS[i].toLowerCase() === String(c).toLowerCase() && out.indexOf(LANGS[i]) < 0) out.push(LANGS[i]);
      }
    }
    add(code);
    add(base(code));
    add(DEFAULT);
    return out;
  }

  function lookup(key) {
    var langs = chain(current);
    for (var i = 0; i < langs.length; i++) {
      var words = config.strings[langs[i]] || {};
      if (words[key] !== undefined) return words[key];
    }
    var kit = KIT_WORDS[current] || KIT_WORDS[base(current)] || KIT_WORDS.en;
    return kit[key] !== undefined ? kit[key] : KIT_WORDS.en[key];
  }

  /** "one", "few", "other"...: the plural form of n in the current language. */
  function pluralForm(n) {
    try {
      if (window.Intl && Intl.PluralRules) return new Intl.PluralRules(current).select(n);
    } catch (e) { /* an old browser or an unknown language */ }
    return n === 1 ? "one" : "other";
  }

  function fill(text, vars) {
    return String(text).replace(/\{(\w+)\}/g, function (all, name) {
      return vars && vars[name] !== undefined ? vars[name] : all;
    });
  }

  /** A word in the current language, with {names} filled in: t("found", {n: 3}).
   *  Plural sets choose by {n} (or {count}). A missing word shows its key. */
  function t(key, vars) {
    var v = lookup(key);
    if (v === undefined) return key;
    if (Array.isArray(v)) return v.map(function (line) { return fill(line, vars); }).join("\n\n");
    if (v && typeof v === "object") {
      var n = vars && (vars.n !== undefined ? vars.n : vars.count);
      v = v[pluralForm(Number(n))] || v.other || "";
    }
    return fill(v, vars);
  }

  /** A list of paragraphs (a value that's a list), as an array of text. */
  function lines(key, vars) {
    var v = lookup(key);
    if (v === undefined) return [];
    if (!Array.isArray(v)) return [t(key, vars)];
    return v.map(function (line) { return fill(line, vars); });
  }

  /** A number written the way the current language writes it: 1,234.5 or 1 234,5. */
  function number(n, decimals) {
    try {
      return new Intl.NumberFormat(current, { minimumFractionDigits: decimals || 0, maximumFractionDigits: decimals || 0 }).format(n);
    } catch (e) {
      return decimals ? Number(n).toFixed(decimals) : String(Math.round(n));
    }
  }

  function about(code) {
    var meta = (config.strings[code] || {})._language || {};
    return { code: code, name: meta.name || code, dir: meta.dir || (RTL.indexOf(base(code)) >= 0 ? "rtl" : "ltr") };
  }

  /** The game's languages, each with its name in its own language: [{code, name, dir}]. */
  function languages() { return LANGS.map(about); }

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

  function titleKey() { return (config.package && config.package.title) || "title"; }

  /** Show the page in a language (its words, direction and title). */
  function applyLanguage(code) {
    current = code;
    var html = document.documentElement;
    html.lang = code;
    html.dir = about(code).dir;
    var title = t(titleKey());
    if (title && title !== titleKey()) document.title = title;
    translatePage();
  }

  /** Change the language, and remember the learner's choice (in their save, so it can follow them). */
  function setLanguage(code) {
    var found = matchLanguage(code);
    if (!found) return Promise.reject(new Error("This game isn't in " + code + "."));
    applyLanguage(found);
    try { window.localStorage.setItem(LANG_KEY, found); } catch (e) { /* storage blocked */ }
    emit("languagechange", { language: found });
    return ready().then(function () {
      info.language = found;
      record._lang = found;
      return backend.write(record);
    });
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
        // The plugin keeps the scores itself; it gets the game's save and the learner's choices.
        return KG.setState({ _v: VERSION, _save: rec._save, _lang: rec._lang, _options: rec._options });
      },
      start: function (board, resume) {
        return KG.start({ resume: !!resume, board: board === MAIN ? "" : board });
      },
      abandon: function () { return KG.abandon(); },
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

  // -------------------------------------------------------------- events
  // EduGame.on(name, fn): "languagechange", "themechange", "optionchange" from
  // the helper; anything else (like "timeup") comes from the platform.

  var handlers = {};
  var OWN_EVENTS = ["languagechange", "themechange", "optionchange"];

  function emit(name, detail) {
    (handlers[name] || []).forEach(function (fn) { try { fn(detail); } catch (e) { console.error(e); } });
    announce(name, detail);
  }

  // --------------------------------------------------------------- theme
  // Light, dark or auto (follow the device). Kept on this device, not with the
  // learner: someone may want dark on their phone and light on a classroom screen.
  // The page gets data-theme="light" or "dark" on <html>; style both with CSS variables.

  var OPTIONS = config.options || {};
  var THEME_KEY = "edugame:" + config.id + ":theme";
  var THEMES = ["light", "dark", "auto"];
  var darkQuery = null;
  try { darkQuery = window.matchMedia("(prefers-color-scheme: dark)"); } catch (e) { /* old browser */ }

  function theme() {
    var saved = null;
    try { saved = window.localStorage.getItem(THEME_KEY); } catch (e) { /* storage blocked */ }
    if (THEMES.indexOf(saved) >= 0) return saved;
    return THEMES.indexOf(OPTIONS.theme) >= 0 ? OPTIONS.theme : "auto";
  }

  function applyTheme(choice) {
    var dark = choice === "dark" || (choice === "auto" && darkQuery && darkQuery.matches);
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }

  function setTheme(choice, remember) {
    if (THEMES.indexOf(choice) < 0) return;
    applyTheme(choice);
    if (remember !== false) {
      try { window.localStorage.setItem(THEME_KEY, choice); } catch (e) { /* storage blocked */ }
    }
    emit("themechange", { theme: choice });
  }

  applyTheme(theme());   // as early as possible, so the page doesn't flash the wrong theme
  if (darkQuery) {
    var follow = function () { if (theme() === "auto") applyTheme("auto"); };
    if (darkQuery.addEventListener) darkQuery.addEventListener("change", follow);
    else if (darkQuery.addListener) darkQuery.addListener(follow);
  }

  // -------------------------------------------------------- game options
  // A game can add its own choices to the Options panel:
  //   EduGame.addOption({key: "skin", label: "options.skin", default: "medium",
  //                      choices: [{value: "light", label: "skin.light"}, ...],
  //                      keep: "device"})      // or "learner": in their save, so it follows them
  // EduGame.option("skin") reads it; "optionchange" tells the game it changed.

  var gameOptions = [];

  function optionKey(o) { return "edugame:" + config.id + ":option:" + o.key; }

  function option(key) {
    var o = gameOptions.filter(function (x) { return x.key === key; })[0];
    if (!o) return undefined;
    var v;
    if (o.keep === "learner") v = (record._options || {})[key];
    else { try { v = window.localStorage.getItem(optionKey(o)); } catch (e) { /* storage blocked */ } }
    var ok = o.choices.some(function (c) { return String(c.value) === String(v); });
    return ok ? o.choices.filter(function (c) { return String(c.value) === String(v); })[0].value : o["default"];
  }

  function setOption(key, value, remember) {
    var o = gameOptions.filter(function (x) { return x.key === key; })[0];
    if (!o) return;
    if (remember !== false) {
      if (o.keep === "learner") {
        record._options = record._options || {};
        record._options[key] = value;
        if (backend) backend.write(record);
      } else {
        try { window.localStorage.setItem(optionKey(o), String(value)); } catch (e) { /* storage blocked */ }
      }
    }
    emit("optionchange", { key: key, value: value });
  }

  function addOption(o) {
    if (!o || !o.key || !Array.isArray(o.choices) || !o.choices.length) throw new Error("addOption() needs a key and choices.");
    gameOptions = gameOptions.filter(function (x) { return x.key !== o.key; }).concat([{
      key: o.key, label: o.label || o.key, choices: o.choices, keep: o.keep === "learner" ? "learner" : "device",
      "default": o["default"] !== undefined ? o["default"] : o.choices[0].value
    }]);
  }

  // ------------------------------------------------ the Options button and panel
  // By default the kit puts a header at the top of the page: the game's title, and
  // an Options button beside it. "options": {"header": false} in edugame.json leaves
  // it out; then any element with data-edugame-options opens the panel, and so does
  // EduGame.openOptions(). On the Kolibri Games games page, which shows the title
  // already, the header has only the button.
  // The panel lays over the page: Appearance, Language, and the game's own options.
  // Appearance and the game's options change as they're clicked; the language changes
  // on Apply. Back (or Escape) puts back what was there before.

  var STYLE = [
    ".eg-header{display:flex;align-items:center;justify-content:space-between;gap:.5rem 1rem;flex-wrap:wrap;",
    "padding:.5rem 1rem;border-bottom:1px solid var(--eg-line,rgba(127,127,127,.3))}",
    ".eg-header .eg-title{margin:0;font-size:1.25rem;line-height:1.3;font-weight:700}",
    ".eg-header.eg-no-title{justify-content:flex-end;border-bottom:0;padding-bottom:0}",
    ".eg-header.eg-no-title .eg-title{display:none}",
    ".eg-options-button{font:inherit;cursor:pointer;padding:.35rem .9rem;border-radius:8px;",
    "border:2px solid var(--eg-accent);background:transparent;color:inherit}",
    ".eg-options-button:focus-visible,.eg-card button:focus-visible,.eg-card input:focus-visible{outline:3px solid var(--eg-accent);outline-offset:2px}",
    ".eg-overlay{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:flex-start;justify-content:center;",
    "padding:5vh 16px;background:rgba(0,0,0,.45);overflow:auto}",
    ".eg-card{width:100%;max-width:28rem;padding:1rem 1.25rem;border-radius:12px;background:var(--eg-panel,#fff);",
    "color:var(--eg-text,#1d232b);box-shadow:0 10px 40px rgba(0,0,0,.35);font:16px/1.45 system-ui,sans-serif}",
    "[data-theme=dark] .eg-card{background:var(--eg-panel-dark,#20252c);color:var(--eg-text-dark,#e9edf1)}",
    ".eg-card h2{margin:.2rem 0 .6rem;font-size:1.3rem}",
    ".eg-card fieldset{border:2px solid rgba(127,127,127,.35);border-radius:8px;margin:.6rem 0;padding:.4rem .9rem .7rem}",
    ".eg-card legend{padding:0 .35rem;font-weight:700}",
    ".eg-card label{display:block;padding:.25rem 0;cursor:pointer}",
    ".eg-card small{opacity:.75}",
    ".eg-actions{display:flex;gap:.6rem;justify-content:flex-end;margin-top:.8rem;flex-wrap:wrap}",
    ".eg-actions button{font:inherit;cursor:pointer;padding:.45rem 1.1rem;border-radius:8px;",
    "border:2px solid var(--eg-accent);background:transparent;color:inherit}",
    ".eg-actions .eg-primary{background:var(--eg-accent);color:#fff}"
  ].join("");

  function addStyle() {
    if (document.getElementById("edugame-style")) return;
    var st = document.createElement("style");
    st.id = "edugame-style";
    st.textContent = ":root{--eg-accent:" + (config.color || "#3b6e8f") + "}" + STYLE;
    (document.head || document.documentElement).appendChild(st);
  }

  function make(tag, attrs, kids) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") el.textContent = attrs[k];
      else if (k === "className") el.className = attrs[k];
      else el.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (kid) { if (kid) el.appendChild(kid); });
    return el;
  }

  function addHeader() {
    addStyle();
    if (OPTIONS.header === false || document.querySelector(".eg-header")) return;
    var header = make("header", { className: "eg-header" + (looksLikeKolibriGames() ? " eg-no-title" : "") }, [
      make("h1", { className: "eg-title", "data-t": titleKey(), text: t(titleKey()) }),
      make("button", { type: "button", className: "eg-options-button", "data-edugame-options": "", "data-t": "kit.options", text: t("kit.options") })
    ]);
    document.body.insertBefore(header, document.body.firstChild);
  }

  document.addEventListener("click", function (e) {
    var el = e.target;
    while (el && el !== document) {
      if (el.hasAttribute && el.hasAttribute("data-edugame-options")) { e.preventDefault(); openOptions(); return; }
      el = el.parentNode;
    }
  });

  var panel = null;

  function radios(name, items, chosen, onPick) {
    return items.map(function (item) {
      var input = make("input", { type: "radio", name: name, value: String(item.value) });
      input.checked = String(item.value) === String(chosen);
      input.addEventListener("change", function () { if (input.checked) onPick(item.value); });
      var kids = [input, document.createTextNode(" " + item.label)];
      if (item.hint) kids.push(document.createTextNode(" "), make("small", { text: item.hint }));
      return make("label", {}, kids);
    });
  }

  function openOptions() {
    if (panel) return;
    addStyle();
    var opener = document.activeElement;
    var before = { theme: theme(), language: current, options: {} };
    gameOptions.forEach(function (o) { before.options[o.key] = option(o.key); });
    var picked = { language: current };

    var appearance = make("fieldset", {}, [make("legend", { text: t("kit.appearance") })].concat(radios("eg-theme", [
      { value: "light", label: t("kit.theme_light") },
      { value: "dark", label: t("kit.theme_dark") },
      { value: "auto", label: t("kit.theme_auto"), hint: t("kit.theme_auto_hint") }
    ], before.theme, function (v) { setTheme(v, false); picked.theme = v; })));

    var langs = languages();
    var language = make("fieldset", {}, [make("legend", { text: t("kit.language") })].concat(langs.length > 1
      ? radios("eg-language", langs.map(function (l) { return { value: l.code, label: l.name }; }), current,
               function (v) { picked.language = v; })
      : [make("p", { text: about(current).name })]));
    langs.forEach(function (l, i) {   // each language name is written in that language
      var label = language.querySelectorAll("label")[i];
      if (label) { label.setAttribute("lang", l.code); label.setAttribute("dir", l.dir); }
    });

    var own = gameOptions.map(function (o) {
      return make("fieldset", {}, [make("legend", { text: t(o.label) })].concat(radios("eg-opt-" + o.key,
        o.choices.map(function (c) { return { value: c.value, label: t(c.label) }; }), before.options[o.key],
        function (v) { setOption(o.key, v, false); picked["opt:" + o.key] = v; })));
    });

    var apply = make("button", { type: "button", className: "eg-primary", text: t("kit.apply") });
    var back = make("button", { type: "button", text: t("kit.back") });
    var card = make("div", { className: "eg-card" }, [
      make("h2", { id: "eg-options-title", text: t("kit.options_title") }), appearance, language
    ].concat(own).concat([make("div", { className: "eg-actions" }, [apply, back])]));
    panel = make("div", { className: "eg-overlay", role: "dialog", "aria-modal": "true", "aria-labelledby": "eg-options-title" }, [card]);

    function close() {
      document.removeEventListener("keydown", onKey, true);
      if (panel && panel.parentNode) panel.parentNode.removeChild(panel);
      panel = null;
      if (opener && opener.focus) opener.focus();
    }
    function cancel() {   // put back what was there before
      setTheme(before.theme, false);
      gameOptions.forEach(function (o) { if (option(o.key) !== before.options[o.key] || picked["opt:" + o.key] !== undefined) setOption(o.key, before.options[o.key], false); });
      close();
    }
    function onKey(e) {
      if (e.key === "Escape") { e.preventDefault(); cancel(); return; }
      if (e.key !== "Tab") return;
      // Keep the keyboard inside the panel while it's open.
      // Tab stops: each group's chosen radio button (or its first), then the buttons.
      var focusable = Array.prototype.filter.call(card.querySelectorAll("input, button"), function (el) {
        if (el.type !== "radio") return true;
        var group = card.querySelectorAll("input[name='" + el.name + "']");
        var chosen = card.querySelector("input[name='" + el.name + "']:checked");
        return chosen ? el === chosen : el === group[0];
      });
      if (!focusable.length) return;
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    apply.addEventListener("click", function () {
      if (picked.theme) setTheme(picked.theme);
      gameOptions.forEach(function (o) { if (picked["opt:" + o.key] !== undefined) setOption(o.key, picked["opt:" + o.key]); });
      var changed = picked.language !== before.language;
      close();
      if (changed) setLanguage(picked.language);
    });
    back.addEventListener("click", cancel);
    panel.addEventListener("click", function (e) { if (e.target === panel) cancel(); });
    document.addEventListener("keydown", onKey, true);
    document.body.appendChild(panel);
    var firstChoice = card.querySelector("input:checked") || apply;
    firstChoice.focus();
  }

  // ------------------------------------------------------------- content
  // Content that's too big to load all at once (maps, lessons, word lists) lives
  // in JSON files in the folders edugame.json lists under "content". The build
  // turns each into a small script (file.json.js), so it also loads straight
  // from a folder:
  //   EduGame.load("words/fr.json")              one file, or null if it isn't there
  //   EduGame.loadLanguage("maps/us/lang")       maps/us/lang/<language>.json for the current
  //                                              language, with the default language filling gaps
  //   EduGame.loadLanguage("lessons/01", {merge: false})
  //                                              the nearest file only: fr-CA, then fr, then the default

  var contentCache = {};
  var contentWaiting = {};

  function contentLoaded(path, data) {
    contentCache[path] = data;
    (contentWaiting[path] || []).forEach(function (fn) { fn(data); });
    delete contentWaiting[path];
  }

  function load(path) {
    if (contentCache.hasOwnProperty(path)) return Promise.resolve(contentCache[path]);
    return new Promise(function (resolve) {
      if (contentWaiting[path]) { contentWaiting[path].push(resolve); return; }
      contentWaiting[path] = [resolve];
      var s = document.createElement("script");
      s.src = path + ".js";
      s.onerror = function () { contentLoaded(path, null); };
      s.onload = function () { if (!contentCache.hasOwnProperty(path)) contentLoaded(path, null); };
      document.head.appendChild(s);
    });
  }

  function merged(a, b) {
    if (!b || typeof b !== "object" || Array.isArray(b) || !a || typeof a !== "object" || Array.isArray(a)) return b;
    var out = {};
    Object.keys(a).forEach(function (k) { out[k] = a[k]; });
    Object.keys(b).forEach(function (k) { out[k] = k in out ? merged(out[k], b[k]) : b[k]; });
    return out;
  }

  function loadLanguage(dir, opts) {
    opts = opts || {};
    var code = opts.language || current;
    var codes = chain(code).reverse();   // the default first, the closest last
    return Promise.all(codes.map(function (c) { return load(dir + "/" + c + ".json"); })).then(function (files) {
      if (opts.merge === false) {
        for (var i = files.length - 1; i >= 0; i--) if (files[i]) return files[i];
        return null;
      }
      return files.reduce(function (acc, f) { return f ? (acc ? merged(acc, f) : f) : acc; }, null);
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
      applyLanguage(language);
      info = {
        save: record._save === undefined ? null : record._save,
        settings: opened.settings || defaultSettings(),
        language: language,
        languages: languages(),
        theme: theme(),
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

  /** A round begins. opts.board: the level. opts.resume: on the Kolibri Games games page,
   *  carry on an attempt the learner left unfinished (the result says resumed: true). */
  function start(opts) {
    opts = opts || {};
    return ready().then(function () {
      var board = cleanBoard(opts.board);
      round = { board: board, startedAt: now() };
      announce("start", { board: board });
      return backend.start ? backend.start(board, opts.resume) : null;
    });
  }

  /** The round ends without a result (the learner gave up, or it wasn't a real round). */
  function abandon() {
    return ready().then(function () {
      round = null;
      return backend.abandon ? backend.abandon() : null;
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
    if (OWN_EVENTS.indexOf(name) >= 0) {
      (handlers[name] = handlers[name] || []).push(fn);
      return;
    }
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
    abandon: abandon,
    on: on,
    // languages
    t: t,
    lines: lines,
    number: number,
    translatePage: translatePage,
    language: function () { return current; },
    languages: languages,
    setLanguage: setLanguage,
    // appearance and options
    theme: theme,
    setTheme: setTheme,
    addOption: addOption,
    option: option,
    openOptions: openOptions,
    // content
    load: load,
    loadLanguage: loadLanguage,
    _content: contentLoaded,   // called by the build's content scripts
    exit: exit,
    // for tests and the test page
    _compare: function (a, b) { return compare(a, b); },
    _keep: function (old, r, plays) { return keep(old, r, plays); },
    _percent: function (values) { return percent(values); }
  };

  // The header with the Options button, as soon as the page is there.
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", addHeader);
  else addHeader();
})();
