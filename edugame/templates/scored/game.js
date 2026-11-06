/* A Scored Game: ten sums; the score is how many are right. EduGame times the
   round between start() and finish(), keeps the learner's best, and reports
   the score to the platform (Kolibri Games scoreboards, a learning system's
   gradebook). */
(function () {
  "use strict";
  var ROUNDS = 10;
  var t = EduGame.t;
  var $ = function (id) { return document.getElementById(id); };
  var n = 0, right = 0, sum = null;

  function screen(name) {
    ["intro", "play", "done"].forEach(function (id) { $(id).hidden = id !== name; });
  }

  function next() {
    n += 1;
    var a = 2 + Math.floor(Math.random() * 18), b = 2 + Math.floor(Math.random() * 18);
    sum = a + b;
    $("question").textContent = t("question", { n: n, a: a, b: b });
    $("answer").value = "";
    $("answer").focus();
  }

  function showBest(best) {
    $("best").textContent = best === null || best === undefined ? "" : t("best", { best: best });
  }

  $("start").addEventListener("click", function () {
    n = 0; right = 0;
    EduGame.start().then(function () { screen("play"); next(); });
  });
  $("again").addEventListener("click", function () { $("start").click(); });

  $("form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (Number($("answer").value) === sum) right += 1;
    if (n < ROUNDS) return next();
    EduGame.finish(right).then(function (r) {
      $("result").textContent = t("result", { score: r.score, seconds: Math.round(r.seconds) });
      $("new-best").hidden = !r.newBest;
      showBest(r.best);
      screen("done");
    });
  });

  EduGame.ready().then(function (info) { showBest(info.best); });
})();
