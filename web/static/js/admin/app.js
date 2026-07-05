(function () {
  'use strict';

  // --- Navigation ---
  function loadPage(name) {
    fetch("/admin/page/" + name)
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
      users: "People",
      codes: "Registration Codes",
      registers: "Attendance",
      leaves: "Leaves",
      pass: "Pass Codes",
      tasks: "Tasks",
      cleaning: "Cleaning",
      notes: "Notes",
      info: "Announcements",
      complaints: "Complaints",
    };
    var el = document.getElementById("headerTitle");
    if (el) el.textContent = map[name] || "Dashboard";

    var pills = document.getElementById("headerPills");
    var attPills = document.getElementById("headerAttPills");
    if (pills) {
      if (name === "users") {
        pills.classList.remove("hidden");
        var ps = pills.querySelectorAll(".people-tab");
        if (ps.length) {
          ps[0].classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
          ps[0].classList.remove("text-zinc-600", "dark:text-zinc-300");
          ps[1].classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
          ps[1].classList.add("text-zinc-600", "dark:text-zinc-300");
        }
      } else {
        pills.classList.add("hidden");
      }
    }
    if (attPills) {
      if (name === "registers") {
        attPills.classList.remove("hidden");
        var at = attPills.querySelectorAll(".att-tab");
        if (at.length) {
          at[0].classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
          at[0].classList.remove("text-zinc-600", "dark:text-zinc-300");
          for (var i = 1; i < at.length; i++) {
            at[i].classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
            at[i].classList.add("text-zinc-600", "dark:text-zinc-300");
          }
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
    script.src = "/static/js/admin/" + name + ".js?t=" + Date.now();
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

  window.withGuard = function (btn, loadingText, fn) {
    if (typeof loadingText === "function") {
      fn = loadingText;
      loadingText = null;
    }
    return function () {
      if (btn.disabled) return;
      var orig = btn.textContent;
      btn.disabled = true;
      if (loadingText) btn.textContent = loadingText;
      var result;
      try { result = fn.apply(this, arguments); } catch (e) { result = Promise.reject(e); }
      if (result && typeof result.then === "function") {
        return result.then(function (v) {
          btn.disabled = false;
          btn.textContent = orig;
          return v;
        }).catch(function (e) {
          btn.disabled = false;
          btn.textContent = orig;
          throw e;
        });
      }
      btn.disabled = false;
      btn.textContent = orig;
      return result;
    };
  };
  window.formatFees = function (val) {
    return Number(val).toLocaleString("en-US", {
      style: "currency",
      currency: "XAF",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).replace("XAF", "FCFA");
  };

  // --- Init ---
  document.getElementById("loadingView").classList.add("hidden");
  document.getElementById("appView").classList.remove("hidden");

  loadPage("dashboard");
})();
