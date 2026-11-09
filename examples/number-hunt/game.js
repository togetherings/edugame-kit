/* Number Hunt: the game picks a secret number and answers each guess. The
 * score is the number of guesses. On the Kolibri Games games page every guess
 * is also reported with EduGame.move(), so coaches can see how a game went. */
(function () {
  "use strict";
  var t = EduGame.t;
  var $ = function (id) { return document.getElementById(id); };
  var S = { low: 1, high: 100, min: 1, max: 100, guesses: [], busy: false, over: false, secret: 0, top: 100 };

  function show(id) {
    ["intro", "play", "done"].forEach(function (s) { $(s).hidden = s !== id; });
  }

  function clock(sec) {
    sec = Math.round(sec || 0);
    return Math.floor(sec / 60) + ":" + (sec % 60 < 10 ? "0" : "") + (sec % 60);
  }

  function pct(n) {
    return ((n - S.min) / Math.max(1, S.max - S.min)) * 100;
  }

  function drawLine() {
    var line = $("line");
    Array.prototype.slice.call(line.querySelectorAll(".mark")).forEach(function (m) { m.remove(); });
    $("window").style.left = pct(S.low) + "%";
    $("window").style.right = (100 - pct(S.high)) + "%";
    S.guesses.forEach(function (g) {
      var m = document.createElement("span");
      m.className = "mark " + g.hint;
      m.textContent = g.value;
      m.style.left = Math.min(96, Math.max(4, pct(g.value))) + "%";
      line.appendChild(m);
    });
    $("end-low").textContent = S.min;
    $("end-high").textContent = S.max;
  }

  function addGuess(value, hint) {
    S.guesses.push({ value: value, hint: hint });
    if (hint === "higher") S.low = Math.max(S.low, value + 1);
    if (hint === "lower") S.high = Math.min(S.high, value - 1);
    var li = document.createElement("li");
    li.className = hint;
    li.textContent = t(hint === "higher" ? "go_higher" : hint === "lower" ? "go_lower" : "found_it", { n: value });
    $("history").appendChild(li);
    drawLine();
  }

  function prompt(text) { $("prompt").textContent = text; }

  function error(where, text) {
    var e = $(where + "-error");
    e.textContent = text || "";
    e.hidden = !text;
  }

  function begin() {
    error("intro", "");
    $("btn-start").disabled = true;
    EduGame.start().then(function () {
      S.min = S.low = 1;
      S.max = S.high = S.top;
      S.secret = 1 + Math.floor(Math.random() * S.top);
      S.guesses = [];
      S.over = false;
      $("history").innerHTML = "";
      drawLine();
      show("play");
      prompt(t("first_guess"));
      $("guess").min = S.min;
      $("guess").max = S.max;
      $("guess").value = "";
      $("guess").focus();
    }).catch(function (e) {
      error("intro", e.message);
    }).then(function () { $("btn-start").disabled = false; });
  }

  $("btn-start").addEventListener("click", function () { begin(); });
  $("btn-again").addEventListener("click", function () { show("intro"); begin(); });
  $("btn-exit").addEventListener("click", function () { EduGame.exit(); });

  $("guess-form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (S.busy || S.over) return;
    var value = parseInt($("guess").value, 10);
    if (isNaN(value) || value < S.min || value > S.max) {
      error("play", t("guess_range", { low: S.min, high: S.max }));
      return;
    }
    error("play", "");
    S.busy = true;
    $("btn-guess").disabled = true;
    var hint = value === S.secret ? "correct" : value < S.secret ? "higher" : "lower";
    EduGame.move("guess", { value: value, hint: hint }).then(function () {
      addGuess(value, hint);
      if (hint === "correct") return finish();
      prompt(t(hint === "higher" ? "too_low" : "too_high", { n: value }));
      $("guess").value = "";
      $("guess").focus();
    }).catch(function (err) {
      error("play", err.message);
    }).then(function () {
      S.busy = false;
      $("btn-guess").disabled = false;
    });
  });

  function finish() {
    S.over = true;
    prompt(t("found"));
    var guesses = S.guesses.length;
    return EduGame.finish(guesses).then(function (res) {
      // On the games page, the plugin's own result (its time, practice, rank) is in res.platform.
      var plugin = res.platform || null;
      var seconds = plugin && plugin.attempt ? plugin.attempt.seconds : res.seconds;
      $("done-title").textContent = t("you_found_it");
      $("done-summary").textContent = t(guesses === 1 ? "summary_one" : "summary", { n: S.secret, guesses: guesses, time: clock(seconds) });
      var notes = [];
      if (plugin && plugin.attempt && plugin.attempt.practice) notes.push(t("practice"));
      if (plugin && plugin.standing) notes.push(t("rank", { rank: plugin.standing.rank, of: plugin.standing.of }));
      if (!plugin && res.newBest) notes.push(t("new_best"));
      $("done-standing").textContent = notes.join(" ");
      show("done");
      return EduGame.scoreboard().then(drawBoard);
    }).catch(function (err) {
      $("done-title").textContent = t("not_saved");
      $("done-summary").textContent = err.message;
      show("done");
    });
  }

  function drawBoard(data) {
    var rows = (data && data.rows) || [];
    var body = $("board").querySelector("tbody");
    body.innerHTML = "";
    rows.slice(0, 8).forEach(function (r) {
      var tr = document.createElement("tr");
      if (r.me) tr.className = "me";
      [r.rank, r.me ? t("you", { name: r.name }) : r.name, r.score, clock(r.seconds)].forEach(function (v, i) {
        var td = document.createElement("td");
        td.textContent = v;
        if (i >= 2) td.className = "num";
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    $("board").hidden = rows.length === 0;
  }

  EduGame.on("timeup", function () {
    S.over = true;
    $("done-title").textContent = t("time_up");
    $("done-summary").textContent = t("time_up_text");
    $("done-standing").textContent = "";
    $("board").hidden = true;
    show("done");
  });

  EduGame.ready().then(function (info) {
    showIntro(info);
    // The learner chose another language in Options: redo the words made here.
    EduGame.on("languagechange", function () { showIntro(info); });
  }).catch(function (err) { error("intro", err.message); });

  function showIntro(info) {
    var high = Number(info.settings.max) || 100;
    S.top = high;
    $("intro-text").textContent = t("intro", { high: high });
    $("btn-exit").hidden = !info.canExit;
    var bits = [];
    var rules = info.rules;
    if (rules && rules.counts === "first") bits.push(rules && info.plays ? t("practice_now") : t("first_counts"));
    if (rules && rules.time_limit) bits.push(t("minutes", { n: Math.round(rules.time_limit / 60) }));
    bits.push(t("perfect", { n: Math.ceil(Math.log2(high + 1)) }));
    if (info.best !== null && !rules) bits.push(t("best", { n: info.best }));
    $("intro-rule").textContent = bits.join(" ");
  }
})();
