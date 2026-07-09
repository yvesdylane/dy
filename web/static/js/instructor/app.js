(function () {
  'use strict';

  function loadPage(name) {
    fetch("/instructor/page/" + name)
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.text();
      })
      .then(function (html) {
        document.getElementById("content").innerHTML = html;
        updateActiveNav(name);
        updateTitle(name);
        loadPageScript(name);
      })
      .catch(function () {
        document.getElementById("content").innerHTML =
          '<p class="text-red-400 text-center py-8">Failed to load page.</p>';
      });
  }

  function updateActiveNav(name) {
    document.querySelectorAll(".nav-btn").forEach(function (btn) {
      btn.classList.remove(
        "bg-brand-100", "dark:bg-brand-950/50",
        "text-brand-700", "dark:text-brand-300", "font-semibold"
      );
    });
    document.querySelectorAll('[data-page="' + name + '"]').forEach(function (btn) {
      btn.classList.add(
        "bg-brand-100", "dark:bg-brand-950/50",
        "text-brand-700", "dark:text-brand-300", "font-semibold"
      );
    });
  }

  function updateTitle(name) {
    var map = {
      dashboard: "Dashboard",
      "face-scan": "Face Scan",
      tasks: "Tasks",
    };
    var el = document.getElementById("headerTitle");
    if (el) el.textContent = map[name] || "Dashboard";
  }

  function loadPageScript(name) {
    var old = document.getElementById("page-script");
    if (old) old.remove();

    var script = document.createElement("script");
    script.id = "page-script";
    script.src = "/static/js/instructor/" + name + ".js?t=" + Date.now();
    document.body.appendChild(script);
  }

  // --- Modal ---
  var overlay = document.getElementById("modalOverlay");
  var modalContent = document.getElementById("modalContent");

  function openModal(html) {
    modalContent.innerHTML = html;
    overlay.classList.remove("hidden");
  }

  function closeModal() {
    overlay.classList.add("hidden");
    modalContent.innerHTML = "";
  }

  if (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeModal();
    });
  }

  // --- Dark mode ---
  function applyTheme(dark) {
    if (dark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark);

  document.querySelectorAll("#themeToggle, #mobileThemeToggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var isDark = document.documentElement.classList.toggle("dark");
      document.querySelectorAll("#moonIcon, #mobileMoonIcon").forEach(function (el) {
        el.classList.toggle("hidden", isDark);
        el.classList.toggle("block", !isDark);
      });
      document.querySelectorAll("#sunIcon, #mobileSunIcon").forEach(function (el) {
        el.classList.toggle("hidden", !isDark);
        el.classList.toggle("block", isDark);
      });
    });
  });

  // --- Nav click delegation ---
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-page]");
    if (btn) {
      e.preventDefault();
      loadPage(btn.getAttribute("data-page"));
    }
  });

  // --- Expose globals ---
  window.loadPage = loadPage;
  window.openModal = openModal;
  window.closeModal = closeModal;

  // --- Init ---
  document.getElementById("loadingView").classList.add("hidden");
  document.getElementById("appView").classList.remove("hidden");

  loadPage("dashboard");
})();
