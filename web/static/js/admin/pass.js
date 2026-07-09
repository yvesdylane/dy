(function () {
  'use strict';

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
        var modeSelect = document.getElementById("passModeSelect");
        if (modeSelect) modeSelect.disabled = codes.length > 0;
        stopBtn.disabled = false;

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
    var modeSelect = document.getElementById("passModeSelect");
    var mode = modeSelect ? modeSelect.value : "entry";
    btn.disabled = true;
    btn.textContent = "Starting...";
    fetch("/api/admin/codes/pass/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode }),
    })
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
    var modeSelect = document.getElementById("passModeSelect");
    if (modeSelect) modeSelect.disabled = false;
  }

  // ========== Utilities ==========
  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  loadPass();
})();
