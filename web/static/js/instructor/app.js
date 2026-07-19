(function () {
  'use strict';

  var JS_MAP = {
    registers: "/static/js/admin/registers.js",
    leaves: "/static/js/admin/registers.js",
    pass: "/static/js/admin/registers.js",
    evaluations: "/static/js/admin/evaluations.js",
  };

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
    var navMap = { leaves: "registers", pass: "registers", evaluations: "evaluations" };
    var navName = navMap[name] || name;
    document.querySelectorAll(".nav-btn").forEach(function (btn) {
      btn.classList.remove(
        "bg-brand-100", "dark:bg-brand-950/50",
        "text-brand-700", "dark:text-brand-300", "font-semibold"
      );
    });
    document.querySelectorAll('[data-page="' + navName + '"]').forEach(function (btn) {
      btn.classList.add(
        "bg-brand-100", "dark:bg-brand-950/50",
        "text-brand-700", "dark:text-brand-300", "font-semibold"
      );
    });
  }

  function updateTitle(name) {
    var map = {
      dashboard: "Dashboard",
      tasks: "Tasks",
      registers: "Attendance",
      leaves: "Leaves",
      pass: "Pass Codes",
      evaluations: "Evaluation",
    };
    var el = document.getElementById("headerTitle");
    if (el) el.textContent = map[name] || "Dashboard";

    var attPills = document.getElementById("headerAttPills");
    if (attPills) {
      if (name === "registers" || name === "leaves" || name === "pass") {
        attPills.classList.remove("hidden");
        var attMap = { registers: 0, leaves: 1, pass: 2 };
        var activeAtt = attMap[name] || 0;
        var at = attPills.querySelectorAll(".att-tab");
        if (at.length) {
          at.forEach(function (a, i) {
            a.classList.toggle("bg-white", i === activeAtt);
            a.classList.toggle("dark:bg-zinc-700", i === activeAtt);
            a.classList.toggle("text-zinc-900", i === activeAtt);
            a.classList.toggle("dark:text-zinc-100", i === activeAtt);
            a.classList.toggle("shadow-sm", i === activeAtt);
            a.classList.toggle("text-zinc-600", i !== activeAtt);
            a.classList.toggle("dark:text-zinc-300", i !== activeAtt);
          });
        }
      } else {
        attPills.classList.add("hidden");
      }
    }
  }

  function loadPageScript(name) {
    var old = document.getElementById("page-script");
    if (old) old.remove();

    var script = document.createElement("script");
    script.id = "page-script";
    var path = JS_MAP[name] || "/static/js/instructor/" + name + ".js?t=" + Date.now();
    script.src = path + (path.indexOf("?") !== -1 ? "" : "?t=") + Date.now();
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
      return;
    }
    var aTab = e.target.closest("[data-att-tab]");
    if (aTab) {
      e.preventDefault();
      loadPage(aTab.getAttribute("data-att-tab"));
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
