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
    var navMap = {
      codes: "users",
      leaves: "registers",
      pass: "registers",
      notes: "tasks",
      complaints: "info",
    };
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
      users: "People",
      codes: "Registration Codes",
      registers: "Attendance",
      leaves: "Leaves",
      pass: "Pass Codes",
      tasks: "Tasks",
      notes: "Tasks",
      cleaning: "Cleaning",
      info: "Bulletin",
      complaints: "Bulletin",
    };
    var el = document.getElementById("headerTitle");
    if (el) el.textContent = map[name] || "Dashboard";

    var pills = document.getElementById("headerPills");
    var attPills = document.getElementById("headerAttPills");
    var tasksPills = document.getElementById("headerTasksPills");
    var bulletinPills = document.getElementById("headerBulletinPills");
    if (pills) {
      if (name === "users" || name === "codes") {
        pills.classList.remove("hidden");
        var activePeople = name === "codes" ? 1 : 0;
        var ps = pills.querySelectorAll(".people-tab");
        if (ps.length) {
          ps.forEach(function (p, i) {
            p.classList.toggle("bg-white", i === activePeople);
            p.classList.toggle("dark:bg-zinc-700", i === activePeople);
            p.classList.toggle("text-zinc-900", i === activePeople);
            p.classList.toggle("dark:text-zinc-100", i === activePeople);
            p.classList.toggle("shadow-sm", i === activePeople);
            p.classList.toggle("text-zinc-600", i !== activePeople);
            p.classList.toggle("dark:text-zinc-300", i !== activePeople);
          });
        }
      } else {
        pills.classList.add("hidden");
      }
    }
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
    if (tasksPills) {
      if (name === "tasks" || name === "notes") {
        tasksPills.classList.remove("hidden");
        var isNote = name === "notes" ? 1 : 0;
        var ts = tasksPills.querySelectorAll(".tasks-tab");
        if (ts.length) {
          ts.forEach(function (t, i) {
            t.classList.toggle("bg-white", i === isNote);
            t.classList.toggle("dark:bg-zinc-700", i === isNote);
            t.classList.toggle("text-zinc-900", i === isNote);
            t.classList.toggle("dark:text-zinc-100", i === isNote);
            t.classList.toggle("shadow-sm", i === isNote);
            t.classList.toggle("text-zinc-600", i !== isNote);
            t.classList.toggle("dark:text-zinc-300", i !== isNote);
          });
        }
      } else {
        tasksPills.classList.add("hidden");
      }
    }
    if (bulletinPills) {
      if (name === "info" || name === "complaints") {
        bulletinPills.classList.remove("hidden");
        var isIssue = name === "complaints" ? 1 : 0;
        var bs = bulletinPills.querySelectorAll(".bulletin-tab");
        if (bs.length) {
          bs.forEach(function (b, i) {
            b.classList.toggle("bg-white", i === isIssue);
            b.classList.toggle("dark:bg-zinc-700", i === isIssue);
            b.classList.toggle("text-zinc-900", i === isIssue);
            b.classList.toggle("dark:text-zinc-100", i === isIssue);
            b.classList.toggle("shadow-sm", i === isIssue);
            b.classList.toggle("text-zinc-600", i !== isIssue);
            b.classList.toggle("dark:text-zinc-300", i !== isIssue);
          });
        }
      } else {
        bulletinPills.classList.add("hidden");
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
      return;
    }
    var pTab = e.target.closest("[data-people-tab]");
    if (pTab) {
      e.preventDefault();
      loadPage(pTab.getAttribute("data-people-tab"));
      return;
    }
    var aTab = e.target.closest("[data-att-tab]");
    if (aTab) {
      e.preventDefault();
      loadPage(aTab.getAttribute("data-att-tab"));
      return;
    }
    var tTab = e.target.closest("[data-tasks-tab]");
    if (tTab) {
      e.preventDefault();
      loadPage(tTab.getAttribute("data-tasks-tab"));
      return;
    }
    var bTab = e.target.closest("[data-bulletin-tab]");
    if (bTab) {
      e.preventDefault();
      loadPage(bTab.getAttribute("data-bulletin-tab"));
    }
  });

  // --- Header avatar ---
  function refreshHeaderAvatar(userId) {
    var el = document.getElementById("headerAvatar");
    if (!el) return;
    var src = "/api/admin/users/" + userId + "/photo?t=" + Date.now();
    if (el.tagName === "IMG") {
      el.src = src;
    } else {
      var img = document.createElement("img");
      img.id = "headerAvatar";
      img.className = "w-8 h-8 rounded-lg object-cover border-2 border-brand-500 shrink-0";
      img.src = src;
      img.onerror = function () {
        var div = document.createElement("div");
        div.id = "headerAvatar";
        div.className = "w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-sm shrink-0";
        div.textContent = "A";
        img.parentNode.replaceChild(div, img);
      };
      el.parentNode.replaceChild(img, el);
    }
  }

  // --- Expose globals ---
  window.loadPage = loadPage;
  window.openModal = openModal;
  window.closeModal = closeModal;
  window.refreshHeaderAvatar = refreshHeaderAvatar;

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
