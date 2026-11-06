/* Memory Match: find every pair in as few moves as you can. The score is the
 * number of moves. On the Kolibri Games games page each move is also reported
 * with EduGame.move(), so coaches can review how a game went. */
(function () {
  "use strict";
  var t = EduGame.t;
  var $ = function (id) { return document.getElementById(id); };

  var SYMBOLS = [
    ["Circle", "#e4572e", '<circle cx="50" cy="50" r="34"/>'],
    ["Square", "#2e86ab", '<rect x="18" y="18" width="64" height="64" rx="8"/>'],
    ["Triangle", "#3bb273", '<path d="M50 14L88 82H12z"/>'],
    ["Diamond", "#f0b400", '<path d="M50 10L88 50L50 90L12 50z"/>'],
    ["Star", "#e15a97", '<path d="M50 10l11 26 28 2-21 18 7 28-25-15-25 15 7-28-21-18 28-2z"/>'],
    ["Heart", "#d7263d", '<path d="M50 86C22 64 12 50 12 34c0-12 9-22 21-22 8 0 14 5 17 11 3-6 9-11 17-11 12 0 21 10 21 22 0 16-10 30-38 52z"/>'],
    ["Hexagon", "#6c5ce7", '<path d="M30 14h40l20 36-20 36H30L10 50z"/>'],
    ["Cross", "#00a6a6", '<path d="M38 12h24v26h26v24H62v26H38V62H12V38h26z"/>'],
    ["Moon", "#f39c12", '<path d="M62 12a38 38 0 1 0 26 58A30 30 0 1 1 62 12z"/>'],
    ["Drop", "#1e88e5", '<path d="M50 10C50 10 20 46 20 64a30 30 0 0 0 60 0C80 46 50 10 50 10z"/>'],
    ["Ring", "#8e44ad", '<circle cx="50" cy="50" r="30" fill="none" stroke-width="14"/>'],
    ["Bolt", "#c0ca33", '<path d="M58 8L20 56h24l-6 36 40-50H54z"/>']
  ];

  var S = { cards: [], open: [], moves: 0, found: 0, pairs: 8, busy: false, playing: false, queue: Promise.resolve() };

  function shuffle(list) {
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var x = list[i]; list[i] = list[j]; list[j] = x;
    }
    return list;
  }

  function svgFor(sym) {
    var stroke = sym[2].indexOf('fill="none"') >= 0 ? ' stroke="' + sym[1] + '"' : "";
    return '<svg viewBox="0 0 100 100" fill="' + sym[1] + '"' + stroke + ' aria-hidden="true">' + sym[2] + "</svg>";
  }

  function clock(sec) {
    sec = Math.round(sec || 0);
    return Math.floor(sec / 60) + ":" + (sec % 60 < 10 ? "0" : "") + (sec % 60);
  }

  function updateStats() {
    $("moves").textContent = S.moves;
    $("found").textContent = S.found;
    $("total").textContent = S.pairs;
  }

  function showError(text) {
    $("error").textContent = text || "";
    $("error").hidden = !text;
  }

  // Send move logs in order without making the player wait for them.
  function log(type, data) {
    S.queue = S.queue.then(function () { return EduGame.move(type, data); }).catch(function () {});
  }

  function deal() {
    var picks = shuffle(SYMBOLS.slice()).slice(0, S.pairs);
    var deck = shuffle(picks.concat(picks).map(function (sym, i) { return { sym: sym, id: i }; }));
    S.cards = deck;
    S.open = [];
    S.moves = 0;
    S.found = 0;
    var grid = $("grid");
    var cols = S.pairs > 8 ? 6 : 4;
    grid.style.setProperty("--cols", cols);
    grid.style.setProperty("--rows", Math.ceil((S.pairs * 2) / cols));
    grid.innerHTML = "";
    deck.forEach(function (card, index) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "card";
      b.setAttribute("aria-label", t("card_down", { n: index + 1 }));
      b.innerHTML = svgFor(card.sym);
      b.addEventListener("click", function () { flip(index); });
      card.el = b;
      grid.appendChild(b);
    });
    updateStats();
  }

  function flip(index) {
    var card = S.cards[index];
    if (!S.playing || S.busy || card.matched || S.open.indexOf(index) >= 0) return;
    card.el.classList.add("up");
    card.el.setAttribute("aria-label", t("card_up", { n: index + 1, name: t(card.sym[0]) }));
    S.open.push(index);
    if (S.open.length < 2) return;
    S.moves += 1;
    var a = S.cards[S.open[0]], b = S.cards[S.open[1]];
    var match = a.sym === b.sym;
    log("move", { cards: S.open.slice(), match: match });
    if (match) {
      a.matched = b.matched = true;
      a.el.classList.add("matched");
      b.el.classList.add("matched");
      S.found += 1;
      S.open = [];
      updateStats();
      if (S.found === S.pairs) win();
      return;
    }
    updateStats();
    S.busy = true;
    setTimeout(function () {
      [a, b].forEach(function (c, i) {
        c.el.classList.remove("up");
        c.el.setAttribute("aria-label", t("card_down", { n: S.open[i] + 1 }));
      });
      S.open = [];
      S.busy = false;
    }, 850);
  }

  function win() {
    S.playing = false;
    S.queue.then(function () {
      return EduGame.finish(S.moves);
    }).then(function (res) {
      var plugin = res.platform;  // the games page's own result, or null elsewhere
      var seconds = plugin && plugin.attempt ? plugin.attempt.seconds : res.seconds;
      $("done-title").textContent = t("all_found");
      $("done-summary").textContent = t("summary", { pairs: S.pairs, moves: S.moves, time: clock(seconds) });
      $("done-standing").textContent = plugin && plugin.standing
        ? t("rank", { rank: plugin.standing.rank, of: plugin.standing.of })
        : (res.newBest ? t("new_best") : "");
      $("done").hidden = false;
      $("btn-again").focus();
    }).catch(function (err) { showError(err.message); });
  }

  function begin() {
    showError("");
    $("done").hidden = true;
    // Boards can't be restored after a reload, so every game starts afresh.
    EduGame.start().then(function () {
      deal();
      S.playing = true;
    }).catch(function (err) { showError(err.message); });
  }

  $("btn-again").addEventListener("click", begin);
  $("btn-exit").addEventListener("click", function () { EduGame.exit(); });

  EduGame.on("timeup", function () {
    S.playing = false;
    $("done-title").textContent = t("time_up");
    $("done-summary").textContent = t("time_up_text", { found: S.found, pairs: S.pairs });
    $("done-standing").textContent = "";
    $("done").hidden = false;
  });

  EduGame.ready().then(function (info) {
    S.pairs = Number(info.settings.pairs || 8);
    $("btn-exit").hidden = !info.canExit;
    var rule = t("rule");
    if (info.rules && info.rules.time_limit) rule += " " + t("minutes", { n: Math.round(info.rules.time_limit / 60) });
    if (info.best !== null && !info.rules) rule += " " + t("best", { n: info.best });
    $("rule").textContent = rule;
    begin();
  }).catch(function (err) { showError(err.message); });
})();
