(function () {
  // Check for error query param (redirected back after failed auth)
  var params = new URLSearchParams(window.location.search);
  var error = params.get("error");
  if (error) {
    var el = document.getElementById("errorMsg");
    if (el) {
      el.textContent = decodeURIComponent(error);
      el.classList.remove("hidden");
    }
    return;
  }

  var tg = window.Telegram?.WebApp;
  if (!tg) {
    var el = document.getElementById("errorMsg");
    if (el) {
      el.textContent = "Not running in Telegram";
      el.classList.remove("hidden");
    }
    console.log("[auth] Telegram.WebApp not available");
    return;
  }

  console.log("[auth] Telegram.WebApp available, version=" + (tg.version || "?"));

  tg.ready();
  tg.expand();

  var initData = tg.initData || "";
  console.log("[auth] initData present=" + !!initData + " length=" + initData.length + " preview=" + initData.substring(0, 80));
  if (!initData) {
    console.warn("[auth] initData is empty — Mini App not launched from Telegram or no session");
  }

  // Use a form POST (real navigation) so the session cookie
  // set by the server is properly persisted across redirects.
  // This avoids cookie-loss issues in embedded browsers (Linux Qt WebEngine).
  var form = document.createElement("form");
  form.method = "POST";
  form.action = "/auth/telegram";
  form.style.display = "none";

  var input = document.createElement("input");
  input.type = "hidden";
  input.name = "initData";
  input.value = initData;
  form.appendChild(input);

  document.body.appendChild(form);
  console.log("[auth] submitting form to /auth/telegram");
  form.submit();
})();
