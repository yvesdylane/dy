(function () {
  'use strict';

  loadCodes();

  function loadCodes() {
    var list = document.getElementById("codesList");
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/codes")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error(data.detail || "Failed");
        renderCodes(data.codes || []);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-center py-8 text-red-400 text-sm">Failed to load codes.</p>';
      });
  }

  function renderCodes(codes) {
    var list = document.getElementById("codesList");
    if (codes.length === 0) {
      list.innerHTML = '<p class="text-center py-8 text-zinc-400 text-sm">No codes yet.</p>';
      return;
    }
    var html = "";
    codes.forEach(function (c) {
      var statusClass = c.is_used
        ? "text-red-500 bg-red-50 dark:bg-red-950/30"
        : "text-green-600 bg-green-50 dark:bg-green-950/30";
      var roleColor = c.role === "admin"
        ? "bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300"
        : c.role === "instructor"
        ? "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300"
        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300";
      html += '<div class="code-row flex items-center gap-2 p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">'
        + '<input type="checkbox" class="code-checkbox shrink-0 accent-teal-600" data-id="' + c.id + '">'
        + '<div class="flex-1 min-w-0">'
        + '<p class="font-mono text-sm font-medium">' + esc(c.code) + '</p>'
        + '<p class="text-xs text-zinc-500 flex items-center gap-1.5 mt-0.5">'
        + '<span class="inline-block px-1.5 py-0.5 rounded text-xs font-medium ' + statusClass + '">' + (c.is_used ? "Used" : "Available") + '</span>'
        + '<span class="inline-block px-1.5 py-0.5 rounded text-xs font-medium ' + roleColor + '">' + c.role + '</span>'
        + '<span>expires ' + c.expires_at + '</span>'
        + '</p>'
        + '</div>'
        + '<button class="del-code-btn p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg text-xs transition-colors" data-id="' + c.id + '">'
        + '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
        + '</button>'
        + '</div>';
    });
    list.innerHTML = html;
    updateDeleteSelectedBtn();
  }

  function updateDeleteSelectedBtn() {
    var checked = document.querySelectorAll(".code-checkbox:checked");
    var btn = document.getElementById("deleteSelectedCodesBtn");
    var count = document.getElementById("selectedCount");
    if (!btn || !count) return;
    if (checked.length) {
      btn.classList.remove("hidden");
      count.classList.remove("hidden");
      count.textContent = checked.length + " selected";
    } else {
      btn.classList.add("hidden");
      count.classList.add("hidden");
    }
  }

  function openAddCodeModal() {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = '<h3 class="text-lg font-bold mb-1">Generate Code</h3>'
      + '<p class="text-xs text-zinc-500 mb-4">Enter 1 to create a single code, or more to create multiple at once</p>'
      + '<form id="codeForm" class="space-y-3" onsubmit="return false">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Role'
      + '<select name="role" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">'
      + '<option value="intern">Intern</option><option value="instructor">Instructor</option><option value="admin">Admin</option></select></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Expires in (minutes)'
      + '<input name="expiry" type="number" value="60" min="1" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">How many'
      + '<input name="count" type="number" value="1" min="1" max="100" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<p id="codeFormErr" class="text-red-500 text-xs hidden"></p>'
      + '<div class="flex gap-2 pt-2">'
      + '<button type="button" onclick="window.closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button type="submit" id="codeSubmitBtn" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Generate</button></div></form>';
    m.classList.remove("hidden");
    window.closeModal = function () { m.classList.add("hidden"); c.innerHTML = ""; };

    document.getElementById("codeForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("codeSubmitBtn");
      if (btn.disabled) return;
      btn.disabled = true; btn.textContent = "Generating...";
      var f = e.target;
      var body = {
        role: f.elements["role"].value,
        expiry_minutes: parseInt(f.elements["expiry"].value) || 60,
        count: parseInt(f.elements["count"].value) || 1,
      };
      fetch("/api/admin/codes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btn.disabled = false; btn.textContent = "Generate";
          if (res.ok) {
            window.closeModal();
            loadCodes();
          } else {
            var err = document.getElementById("codeFormErr");
            err.textContent = res.detail || "Error";
            err.classList.remove("hidden");
          }
        })
        .catch(function () {
          btn.disabled = false; btn.textContent = "Generate";
          var err = document.getElementById("codeFormErr");
          err.textContent = "Network error";
          err.classList.remove("hidden");
        });
    });
  }

  // --- Event delegation ---
  document.addEventListener("change", function (e) {
    if (e.target.classList.contains("code-checkbox")) updateDeleteSelectedBtn();
  });

  document.addEventListener("change", function (e) {
    if (e.target.id === "selectAllCodes") {
      document.querySelectorAll(".code-checkbox").forEach(function (cb) {
        cb.checked = e.target.checked;
      });
      updateDeleteSelectedBtn();
    }
  });

  document.addEventListener("click", function (e) {
    var d = e.target.closest(".del-code-btn");
    if (!d || d.disabled || !confirm("Delete this code?")) return;
    d.disabled = true;
    fetch("/api/admin/codes/" + d.dataset.id, { method: "DELETE" })
      .then(function () { loadCodes(); })
      .catch(function () { d.disabled = false; });
  });

  document.getElementById("deleteSelectedCodesBtn")?.addEventListener("click", function () {
    var btn = this;
    if (btn.disabled) return;
    var checked = document.querySelectorAll(".code-checkbox:checked");
    var ids = Array.from(checked).map(function (cb) { return parseInt(cb.dataset.id); });
    if (!ids.length || !confirm("Delete " + ids.length + " selected code" + (ids.length > 1 ? "s" : "") + "?")) return;
    btn.disabled = true;
    btn.textContent = "Deleting...";
    fetch("/api/admin/codes/delete-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: ids }),
    })
      .then(function () { loadCodes(); })
      .catch(function () { btn.disabled = false; btn.textContent = "Delete Selected"; });
  });

  document.getElementById("deleteAllCodesBtn")?.addEventListener("click", function () {
    var btn = this;
    if (btn.disabled) return;
    if (!confirm("Delete ALL codes? This cannot be undone.")) return;
    btn.disabled = true;
    btn.textContent = "Deleting...";
    fetch("/api/admin/codes/delete-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ all: true }),
    })
      .then(function () { loadCodes(); })
      .catch(function () { btn.disabled = false; btn.textContent = "Delete All"; });
  });

  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  window.openAddCodeModal = openAddCodeModal;
})();