(function () {
  'use strict';

  document.getElementById("leaveStatusFilter")?.addEventListener("change", loadLeaves);

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".leave-review-btn");
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    var id = parseInt(btn.dataset.id);
    var action = btn.dataset.action;
    fetch("/api/admin/leaves/" + id + "/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: action }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btn.disabled = false;
        if (data.ok) loadLeaves();
        else alert(data.detail || "Failed to review");
      })
      .catch(function () {
        btn.disabled = false;
        alert("Network error");
      });
  });

  function loadLeaves() {
    var list = document.getElementById("leavesList");
    if (!list) return;
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/leaves")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error("Failed");
        renderLeaves(data.leaves || []);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-center py-8 text-red-400 text-sm">Failed to load leaves.</p>';
      });
  }

  function renderLeaves(leaves) {
    var list = document.getElementById("leavesList");
    if (!list) return;
    var filter = document.getElementById("leaveStatusFilter").value;
    var items = filter ? leaves.filter(function (l) { return l.status === filter; }) : leaves;

    if (items.length === 0) {
      list.innerHTML = '<p class="text-center py-8 text-zinc-400 text-sm">No leave requests found.</p>';
      return;
    }

    list.innerHTML = items.map(function (l) {
      var statusColor = l.status === "approved"
        ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30"
        : l.status === "rejected"
        ? "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30"
        : "text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/30";
      return '<div class="p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">'
        + '<div class="flex items-center justify-between">'
        + '<p class="font-medium text-sm">' + esc(l.user_name) + '</p>'
        + '<span class="text-xs px-2 py-0.5 rounded-full font-medium ' + statusColor + '">' + l.status + '</span>'
        + '</div>'
        + '<p class="text-xs text-zinc-500 mt-1">' + (l.department || "") + (l.group ? " \u00b7 Group " + l.group : "") + " \u00b7 " + l.date + '</p>'
        + '<p class="text-xs text-zinc-400 mt-1 italic truncate">"' + esc(l.reason) + '"</p>'
        + '<p class="text-xs text-zinc-400 mt-0.5">' + (l.created_at || "") + '</p>'
        + (l.status === "pending"
            ? '<div class="flex gap-2 mt-2">'
            + '<button class="leave-review-btn px-3 py-1 rounded-lg bg-green-500 hover:bg-green-600 text-white text-xs font-medium" data-id="' + l.id + '" data-action="approved">Approve</button>'
            + '<button class="leave-review-btn px-3 py-1 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-medium" data-id="' + l.id + '" data-action="rejected">Reject</button>'
            + '</div>'
            : "")
        + '</div>';
    }).join("");
  }

  loadLeaves();

  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();