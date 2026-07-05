(function () {
  'use strict';

  var CURRENT_ATT_TAB = "registers";

  // --- Tab switching ---
  function switchAttTab(name) {
    CURRENT_ATT_TAB = name;
    var tabs = ["registers", "leaves", "pass"];
    tabs.forEach(function (t) {
      var el = document.getElementById("att" + t.charAt(0).toUpperCase() + t.slice(1) + "Tab");
      if (el) el.classList.toggle("hidden", t !== name);
    });
    var pills = document.querySelectorAll("#headerAttPills .att-tab");
    pills.forEach(function (p) {
      if (p.dataset.attTab === name) {
        p.classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
        p.classList.remove("text-zinc-600", "dark:text-zinc-300");
      } else {
        p.classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
        p.classList.add("text-zinc-600", "dark:text-zinc-300");
      }
    });
    if (name === "leaves") loadLeaves();
    if (name === "pass") loadPass();
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("#headerAttPills .att-tab");
    if (btn) {
      e.preventDefault();
      switchAttTab(btn.dataset.attTab);
    }
  });

  // ========== Attendance Registers ==========
  var today = new Date().toISOString().split("T")[0];
  document.getElementById("attDate").value = today;

  document.getElementById("attLoadBtn").addEventListener("click", loadAttendance);
  document.getElementById("attDate").addEventListener("change", function () {
    if (this.value) loadAttendance();
  });
  document.getElementById("attCreateBtn")?.addEventListener("click", createAttendance);
  document.getElementById("attSaveBtn")?.addEventListener("click", saveAttendance);
  document.getElementById("attDeleteBtn")?.addEventListener("click", deleteAttendance);

  loadAttendance();

  function loadAttendance() {
    var ds = document.getElementById("attDate").value;
    if (!ds) return;
    var list = document.getElementById("attStudents");
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/attendance?date=" + ds)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error("Failed");
        window._attId = data.attendance_id;
        renderAttendance(data);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-center py-8 text-red-400 text-sm">Failed to load attendance.</p>';
      });
  }

  function renderAttendance(data) {
    var list = document.getElementById("attStudents");
    var badge = document.getElementById("attGroupBadge");
    var actions = document.getElementById("attActions");
    var saveBtn = document.getElementById("attSaveBtn");
    var createBtn = document.getElementById("attCreateBtn");
    var deleteBtn = document.getElementById("attDeleteBtn");

    if (data.group) {
      badge.classList.remove("hidden");
      badge.textContent = "Group " + data.group;
    } else {
      badge.classList.add("hidden");
    }

    if (data.exists) {
      list.innerHTML = (data.students || []).map(function (s) {
        return '<div class="flex items-center gap-2 p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900" data-user-id="' + s.user_id + '">'
          + '<span class="flex-1 text-sm font-medium truncate">' + esc(s.name) + ' ' + esc(s.surname) + '</span>'
          + (s.status === "exempted"
              ? '<span class="text-xs text-blue-500 font-medium">Exempted</span>'
              : '<input type="time" class="enter-time px-2 py-1 rounded border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-xs focus:outline-none focus:ring-1 focus:ring-teal-500/50" value="' + (s.enter_at || "") + '">'
              + '<input type="time" class="exit-time px-2 py-1 rounded border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-xs focus:outline-none focus:ring-1 focus:ring-teal-500/50" value="' + (s.left_at || "") + '">')
          + '</div>';
      }).join("");
      actions.classList.remove("hidden");
      saveBtn.classList.remove("hidden");
      createBtn.classList.add("hidden");
      deleteBtn.classList.remove("hidden");
    } else {
      list.innerHTML = '<p class="text-center py-8 text-zinc-400 text-sm">No attendance record for this date. Click Create to start.</p>';
      actions.classList.remove("hidden");
      saveBtn.classList.add("hidden");
      createBtn.classList.remove("hidden");
      deleteBtn.classList.add("hidden");
    }
  }

  function createAttendance() {
    var ds = document.getElementById("attDate").value;
    if (!ds) return;
    var btn = document.getElementById("attCreateBtn");
    btn.disabled = true; btn.textContent = "Creating...";
    fetch("/api/admin/attendance/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: ds }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btn.disabled = false; btn.textContent = "Create";
        if (data.ok) loadAttendance();
        else alert(data.detail || "Failed");
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = "Create";
        alert("Network error");
      });
  }

  function saveAttendance() {
    var rows = document.querySelectorAll("#attStudents div[data-user-id]");
    var entries = [];
    rows.forEach(function (row) {
      var uid = parseInt(row.dataset.userId);
      var et = row.querySelector(".enter-time");
      var lt = row.querySelector(".exit-time");
      if (!et && !lt) return;
      var ev = et ? et.value : "";
      var lv = lt ? lt.value : "";
      if (ev || lv) entries.push({ user_id: uid, enter_at: ev || null, left_at: lv || null });
    });
    var btn = document.getElementById("attSaveBtn");
    btn.disabled = true; btn.textContent = "Saving...";
    fetch("/api/admin/attendance/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ attendance_id: window._attId, entries: entries }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btn.disabled = false; btn.textContent = "Save";
        if (data.ok) loadAttendance();
        else alert(data.detail || "Failed");
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = "Save";
        alert("Network error");
      });
  }

  function deleteAttendance() {
    var ds = document.getElementById("attDate").value;
    if (!ds || !confirm("Delete attendance for this date?")) return;
    var btn = document.getElementById("attDeleteBtn");
    btn.disabled = true; btn.textContent = "Deleting...";
    fetch("/api/admin/attendance?date=" + ds, { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btn.disabled = false; btn.textContent = "Delete";
        if (data.ok) loadAttendance();
        else alert(data.detail || "Failed");
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = "Delete";
        alert("Network error");
      });
  }

  // ========== Leaves ==========
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

  // ========== Pass Codes ==========
  var passAnimFrame = null;
  var passPollInterval = null;
  var PASS_TOTAL = 60;
  var PASS_CIRC = 94.25;

  document.getElementById("passStartBtn")?.addEventListener("click", startPass);
  document.getElementById("passStopBtn")?.addEventListener("click", stopPass);

  function animatePass() {
    var cells = document.querySelectorAll("#passGrid .pass-cell");
    if (!cells.length) { passAnimFrame = null; return; }
    var now = Date.now();
    cells.forEach(function (cell) {
      var expires = new Date(cell.dataset.expires).getTime();
      var remaining = Math.max(0, Math.floor((expires - now) / 1000));
      var ring = cell.querySelector(".timer-ring");
      var label = cell.querySelector(".timer-label");
      if (ring) ring.setAttribute("stroke-dashoffset", PASS_CIRC * (1 - remaining / PASS_TOTAL));
      if (label) label.textContent = remaining;
    });
    passAnimFrame = requestAnimationFrame(animatePass);
  }

  function loadPass() {
    var grid = document.getElementById("passGrid");
    var status = document.getElementById("passStatus");
    var startBtn = document.getElementById("passStartBtn");
    var stopBtn = document.getElementById("passStopBtn");
    if (!grid) return;

    fetch("/api/admin/codes/pass/active")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error("Failed");
        grid.innerHTML = "";
        var codes = data.codes || [];
        codes.forEach(function (c) {
          var expires = new Date(c.expires_at).getTime();
          var remaining = Math.max(0, Math.floor((expires - Date.now()) / 1000));
          var offset = PASS_CIRC * (1 - remaining / PASS_TOTAL);
          var cell = document.createElement("div");
          cell.className = "pass-cell flex items-center justify-between p-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900";
          cell.dataset.expires = c.expires_at;
          cell.innerHTML = '<code class="text-sm font-mono font-bold tracking-wider text-teal-600 dark:text-teal-400">' + esc(c.code) + '</code>'
            + '<div class="relative w-9 h-9 shrink-0">'
            + '<svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">'
            + '<circle cx="18" cy="18" r="15" fill="none" stroke="currentColor" stroke-width="3" class="text-zinc-200 dark:text-zinc-700"/>'
            + '<circle class="timer-ring text-teal-500" cx="18" cy="18" r="15" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="' + PASS_CIRC + '" stroke-dashoffset="' + offset + '"/>'
            + '</svg>'
            + '<span class="timer-label absolute inset-0 flex items-center justify-center text-xs font-mono text-zinc-500 dark:text-zinc-400">' + remaining + '</span>'
            + '</div>';
          grid.appendChild(cell);
        });
        status.textContent = codes.length + "/16 active";
        grid.classList.toggle("hidden", codes.length === 0);
        startBtn.classList.toggle("hidden", codes.length > 0);
        stopBtn.classList.toggle("hidden", codes.length === 0);

        if (codes.length && !passAnimFrame) {
          passAnimFrame = requestAnimationFrame(animatePass);
        }
      })
      .catch(function () {
        status.textContent = "Failed to load codes";
      });
  }

  function startPass() {
    var btn = document.getElementById("passStartBtn");
    btn.disabled = true;
    btn.textContent = "Starting...";
    fetch("/api/admin/codes/pass/start", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btn.disabled = false; btn.textContent = "Start";
        if (data.ok) {
          loadPass();
          if (!passPollInterval) passPollInterval = setInterval(loadPass, 2000);
        } else {
          alert(data.detail || "Failed to start");
        }
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = "Start";
        alert("Network error");
      });
  }

  function stopPass() {
    var btn = document.getElementById("passStopBtn");
    if (btn.disabled) return;
    btn.disabled = true;
    fetch("/api/admin/codes/pass/stop", { method: "POST" });
    if (passAnimFrame) { cancelAnimationFrame(passAnimFrame); passAnimFrame = null; }
    if (passPollInterval) { clearInterval(passPollInterval); passPollInterval = null; }
    var grid = document.getElementById("passGrid");
    grid.classList.add("hidden");
    grid.innerHTML = "";
    document.getElementById("passStatus").textContent = "0/16 active";
    document.getElementById("passStartBtn").classList.remove("hidden");
    document.getElementById("passStopBtn").classList.add("hidden");
  }

  // ========== Utilities ==========
  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
