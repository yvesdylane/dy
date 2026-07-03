(function () {
  'use strict';

  var cards = document.querySelectorAll("#section-dashboard .stat-card");
  cards.forEach(function (c) {
    var p = c.querySelector(".text-xl");
    if (p && p.textContent === "\u2014") p.textContent = "...";
  });

  fetch("/api/admin/stats")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      for (var key in data) {
        var el = document.getElementById("stat-" + key);
        if (!el) continue;
        var val = data[key];
        if (key.indexOf("fees") !== -1) {
          el.textContent = window.formatFees(val);
        } else {
          el.textContent = val;
        }
      }
    })
    .catch(function () {
      cards.forEach(function (c) {
        var p = c.querySelector(".text-xl");
        if (p && p.textContent === "...") p.textContent = "\u2014";
      });
    });
})();
