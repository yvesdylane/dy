(function () {
  'use strict';

  fetch("/api/admin/stats")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var cards = [
        { label: "Interns", value: data.interns, color: "teal" },
        { label: "Tasks", value: data.tasks, color: "blue" },
        { label: "Leave Requests", value: data.leave_requests, color: "amber" },
        { label: "Instructors", value: data.instructors, color: "purple" },
      ];
      var grid = document.getElementById("statsGrid");
      grid.innerHTML = cards.map(function (c) {
        var colors = {
          teal: "bg-teal-50 dark:bg-teal-950/30 text-teal-600 dark:text-teal-400 border-teal-200 dark:border-teal-900",
          blue: "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-900",
          amber: "bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-900",
          purple: "bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-900",
        };
        return '<div class="p-4 rounded-xl border ' + (colors[c.color] || colors.teal) + '">'
          + '<p class="text-2xl font-bold">' + c.value + '</p>'
          + '<p class="text-xs mt-1 opacity-75">' + c.label + '</p>'
          + '</div>';
      }).join("");
    })
    .catch(function () {
      document.getElementById("statsGrid").innerHTML = '<p class="text-red-400 text-sm col-span-2 text-center py-8">Failed to load stats</p>';
    });
})();
