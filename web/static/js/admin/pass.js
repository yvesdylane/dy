(function () {
  'use strict';

  var passAnimFrame = null;
  var passPollInterval = null;
  var PASS_TOTAL = 60;
  var PASS_CIRC = 94.25;

  document.getElementById("passStartBtn")?.addEventListener("click", startPass);
  document.getElementById("passStopBtn")?.addEventListener("click", stopPass);
  document.getElementById("passCameraBtn")?.addEventListener("click", startCamera);
  document.getElementById("passCameraStopBtn")?.addEventListener("click", stopCamera);

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

  // ========== Camera Face Scan ==========
  var passStream = null;
  var passScanInterval = null;

  function startCamera() {
    if (passStream) return;

    if (passPollInterval) {
      clearInterval(passPollInterval);
      passPollInterval = null;
    }
    if (passAnimFrame) {
      cancelAnimationFrame(passAnimFrame);
      passAnimFrame = null;
    }

    navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 480 } },
    })
      .then(function (stream) {
        passStream = stream;
        var video = document.getElementById("passVideo");
        video.srcObject = stream;

        document.getElementById("passGrid").classList.add("hidden");
        document.getElementById("passStatus").textContent = "";
        document.getElementById("passStartBtn").classList.add("hidden");
        document.getElementById("passStopBtn").classList.add("hidden");
        document.getElementById("passModeSelect").disabled = true;
        document.getElementById("passCameraContainer").classList.remove("hidden");
        document.getElementById("passCameraContainer").classList.add("flex");
        document.getElementById("passCameraBtn").classList.add("hidden");

        passScanInterval = setInterval(captureAndScan, 1500);
      })
      .catch(function (err) {
        alert("Camera access denied: " + err.message);
      });
  }

  function stopCamera() {
    if (passScanInterval) {
      clearInterval(passScanInterval);
      passScanInterval = null;
    }
    if (passStream) {
      passStream.getTracks().forEach(function (t) { t.stop(); });
      passStream = null;
    }
    var canvas = document.getElementById("passCanvas");
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    document.getElementById("passVideo").srcObject = null;
    document.getElementById("passCameraContainer").classList.add("hidden");
    document.getElementById("passCameraContainer").classList.remove("flex");
    document.getElementById("passGrid").classList.remove("hidden");
    document.getElementById("passStartBtn").classList.remove("hidden");
    document.getElementById("passStopBtn").classList.add("hidden");
    document.getElementById("passModeSelect").disabled = false;
    document.getElementById("passCameraBtn").classList.remove("hidden");
    document.getElementById("passDetectedList").innerHTML = "";

    loadPass();
  }

  function captureAndScan() {
    var video = document.getElementById("passVideo");
    if (!video || !video.videoWidth) return;

    var canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(function (blob) {
      var mode = document.getElementById("passModeSelect").value;
      var formData = new FormData();
      formData.append("file", blob, "scan.jpg");

      fetch("/api/face/scan?mode=" + mode, {
        method: "POST",
        body: formData,
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok && data.detected) {
            drawDetected(data.detected, video.videoWidth, video.videoHeight);
            displayDetected(data.detected);
          }
        })
        .catch(function () {
          // retry on next interval
        });
    }, "image/jpeg", 0.8);
  }

  function drawDetected(detected, imgW, imgH) {
    var overlay = document.getElementById("passCanvas");
    overlay.width = overlay.offsetWidth || imgW;
    overlay.height = overlay.offsetHeight || imgH;
    var scaleX = overlay.width / imgW;
    var scaleY = overlay.height / imgH;
    var ctx = overlay.getContext("2d");
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    detected.forEach(function (d) {
      var bx1 = d.bbox[0] * scaleX;
      var by1 = d.bbox[1] * scaleY;
      var bx2 = d.bbox[2] * scaleX;
      var by2 = d.bbox[3] * scaleY;

      var isMatch = d.status !== "no_match";
      ctx.strokeStyle = isMatch ? "#22c55e" : "#ef4444";
      ctx.lineWidth = 3;
      ctx.strokeRect(bx1, by1, bx2 - bx1, by2 - by1);

      if (isMatch && d.name) {
        var label = d.name + " " + (d.surname || "");
        ctx.font = "13px sans-serif";
        var textW = ctx.measureText(label).width;
        ctx.fillStyle = "#22c55e";
        ctx.fillRect(bx1, by1 - 18, textW + 8, 18);
        ctx.fillStyle = "#fff";
        ctx.fillText(label, bx1 + 4, by1 - 4);
      }
    });
  }

  function displayDetected(detected) {
    var list = document.getElementById("passDetectedList");
    list.innerHTML = detected.map(function (d) {
      var isMatch = d.status !== "no_match";
      var name = isMatch ? esc(d.name) + " " + esc(d.surname || "") : "???";
      var sim = d.similarity ? (d.similarity * 100).toFixed(1) + "%" : "";
      var statusText = d.status.replace(/_/g, " ");
      var textClass = isMatch
        ? "text-green-500"
        : "text-red-400";
      return '<div class="flex items-center gap-2 p-2 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-sm">'
        + '<span class="font-medium flex-1 truncate">' + name + '</span>'
        + (sim ? '<span class="text-xs text-zinc-400">' + sim + '</span>' : "")
        + '<span class="text-xs font-medium ' + textClass + '">' + statusText + '</span>'
        + '</div>';
    }).join("");
  }

  // ========== Utilities ==========
  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  loadPass();
})();
