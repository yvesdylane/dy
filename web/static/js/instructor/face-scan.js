(function () {
  'use strict';

  var scanStream = null;
  var scanInterval = null;

  document.getElementById("scanStartBtn")?.addEventListener("click", startScan);
  document.getElementById("scanStopBtn")?.addEventListener("click", stopScan);

  function startScan() {
    if (scanStream) return;

    navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 480 } },
    })
      .then(function (stream) {
        scanStream = stream;
        var video = document.getElementById("scanVideo");
        video.srcObject = stream;

        document.getElementById("scanStatus").textContent = "";
        document.getElementById("scanStartBtn").classList.add("hidden");
        document.getElementById("scanModeSelect").disabled = true;
        document.getElementById("scanCameraContainer").classList.remove("hidden");
        document.getElementById("scanCameraContainer").classList.add("flex");

        scanInterval = setInterval(captureAndScan, 1500);
      })
      .catch(function (err) {
        alert("Camera access denied: " + err.message);
      });
  }

  function stopScan() {
    if (scanInterval) {
      clearInterval(scanInterval);
      scanInterval = null;
    }
    if (scanStream) {
      scanStream.getTracks().forEach(function (t) { t.stop(); });
      scanStream = null;
    }
    var canvas = document.getElementById("scanCanvas");
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    document.getElementById("scanVideo").srcObject = null;
    document.getElementById("scanCameraContainer").classList.add("hidden");
    document.getElementById("scanCameraContainer").classList.remove("flex");
    document.getElementById("scanStartBtn").classList.remove("hidden");
    document.getElementById("scanModeSelect").disabled = false;
    document.getElementById("scanDetectedList").innerHTML = "";
    document.getElementById("scanStatus").textContent = "Camera stopped";
  }

  function captureAndScan() {
    var video = document.getElementById("scanVideo");
    if (!video || !video.videoWidth) return;

    var canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(function (blob) {
      var mode = document.getElementById("scanModeSelect").value;
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
        .catch(function () {});
    }, "image/jpeg", 0.8);
  }

  function drawDetected(detected, imgW, imgH) {
    var overlay = document.getElementById("scanCanvas");
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
    var list = document.getElementById("scanDetectedList");
    list.innerHTML = detected.map(function (d) {
      var isMatch = d.status !== "no_match";
      var name = isMatch ? esc(d.name) + " " + esc(d.surname || "") : "???";
      var sim = d.similarity ? (d.similarity * 100).toFixed(1) + "%" : "";
      var statusText = d.status.replace(/_/g, " ");
      var textClass = isMatch ? "text-green-500" : "text-red-400";
      return '<div class="flex items-center gap-2 p-2 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-sm">'
        + '<span class="font-medium flex-1 truncate">' + name + '</span>'
        + (sim ? '<span class="text-xs text-zinc-400">' + sim + '</span>' : "")
        + '<span class="text-xs font-medium ' + textClass + '">' + statusText + '</span>'
        + '</div>';
    }).join("");
  }

  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
