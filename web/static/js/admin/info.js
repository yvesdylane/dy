(function () {
  'use strict';

  var searchTimer;

  loadInfo();

  function loadInfo() {
    var q = document.getElementById("infoSearch").value.trim();
    var params = q ? "?q=" + encodeURIComponent(q) : "";

    var list = document.getElementById("infoList");
    if (!list) return;
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/info" + params)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        renderInfo(res.info || []);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-sm text-red-500 py-8 text-center">Failed to load announcements.</p>';
      });
  }

  function renderInfo(items) {
    var el = document.getElementById("infoList");
    if (!el) return;
    if (!items || items.length === 0) {
      el.innerHTML = '<p class="text-sm text-zinc-400 py-8 text-center">No announcements yet.</p>';
      return;
    }
    var html = "";
    for (var i = 0; i < items.length; i++) {
      var n = items[i];
      html += '<div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-2 cursor-pointer hover:shadow-sm transition-shadow break-words overflow-hidden" onclick="openViewInfoModal(' + n.id + ')">'
        + '<div class="flex items-start justify-between gap-2">'
        + '<h3 class="text-sm font-semibold">' + esc(n.title) + '</h3>'
        + '</div>'
        + (n.content ? '<p class="text-xs text-zinc-500 line-clamp-2">' + esc(n.content) + '</p>' : '')
        + '<div class="flex items-center gap-3 text-xs text-zinc-400 flex-wrap">'
        + (n.creator_name ? '<span>' + esc(n.creator_name + " " + (n.creator_surname || "")) + '</span>' : '')
        + (n.created_at ? '<span>' + n.created_at.slice(0, 10) + '</span>' : '')
        + (n.file_name ? '<span class="inline-flex items-center gap-1 max-w-full overflow-hidden"><svg class="w-3 h-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg><span class="truncate">' + esc(n.file_name) + '</span></span>' : '')
        + '</div></div>';
    }
    el.innerHTML = html;
  }

  function openViewInfoModal(infoId) {
    fetch("/api/admin/info/" + infoId)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        showViewModal(res.info);
      })
      .catch(function () {
        alert("Failed to load announcement.");
      });
  }

  function showViewModal(item) {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<h3 class="text-lg font-bold">' + esc(item.title) + '</h3>'
      + (item.content ? '<p class="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap mt-3">' + esc(item.content) + '</p>' : '')
      + '<div class="flex items-center gap-3 text-xs text-zinc-400 mt-3">'
      + (item.creator_name ? '<span>By ' + esc(item.creator_name + " " + (item.creator_surname || "")) + '</span>' : '')
      + (item.created_at ? '<span>' + item.created_at.slice(0, 10) + '</span>' : '')
      + '</div>'
      + (item.file_name ? '<div class="mt-3"><a href="/api/admin/info/' + item.id + '/file" download="' + esc(item.file_name) + '" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-xs font-medium text-zinc-700 dark:text-zinc-300 transition-colors"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' + esc(item.file_name) + '</a></div>' : '')
      + '<div class="flex gap-2 pt-4">'
      + '<button onclick="closeModal(); openEditInfoModal(' + item.id + ')" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Edit</button>'
      + '<button onclick="closeModal(); deleteInfo(' + item.id + ')" class="flex-1 py-2.5 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors">Delete</button>'
      + '<button onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Close</button>'
      + '</div>';
    m.classList.remove("hidden");
  }

  function openCreateInfoModal() {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<h3 class="text-lg font-bold mb-1">Create Announcement</h3>'
      + '<p class="text-xs text-zinc-500 mb-4">Post a new announcement.</p>'
      + '<form id="infoForm" class="space-y-3" onsubmit="return false">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Title *'
      + '<input name="title" type="text" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Content *'
      + '<textarea name="content" rows="4" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></textarea></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Attach File'
      + '<input name="file" type="file" class="mt-1 w-full text-sm text-zinc-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-teal-50 dark:file:bg-teal-950/30 file:text-teal-700 dark:file:text-teal-300 hover:file:bg-teal-100 dark:hover:file:bg-teal-950/50"></label>'
      + '<p id="infoFormErr" class="text-red-500 text-xs hidden"></p>'
      + '<div class="flex gap-2 pt-2">'
      + '<button type="button" onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button type="submit" id="infoSubmitBtn" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Create</button></div></form>';
    m.classList.remove("hidden");

    document.getElementById("infoForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("infoSubmitBtn");
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = "Creating...";
      var f = e.target;
      var formData = new FormData();
      formData.append("title", f.elements["title"].value);
      formData.append("content", f.elements["content"].value);
      var fileInput = f.elements["file"];
      if (fileInput && fileInput.files[0]) {
        formData.append("file", fileInput.files[0]);
      }

      fetch("/api/admin/info", {
        method: "POST",
        body: formData,
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btn.disabled = false;
          btn.textContent = "Create";
          if (res.ok) {
            closeModal();
            loadInfo();
          } else {
            var err = document.getElementById("infoFormErr");
            err.textContent = res.detail || "Error creating announcement";
            err.classList.remove("hidden");
          }
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Create";
          var err = document.getElementById("infoFormErr");
          err.textContent = "Network error";
          err.classList.remove("hidden");
        });
    });
  }

  function openEditInfoModal(infoId) {
    fetch("/api/admin/info/" + infoId)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        showEditModal(res.info);
      })
      .catch(function () {
        alert("Failed to load announcement data.");
      });
  }

  function showEditModal(item) {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<h3 class="text-lg font-bold mb-1">Edit Announcement</h3>'
      + '<p class="text-xs text-zinc-500 mb-4">Update the announcement.</p>'
      + '<form id="infoForm" class="space-y-3" onsubmit="return false">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Title *'
      + '<input name="title" type="text" value="' + esc(item.title) + '" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Content *'
      + '<textarea name="content" rows="4" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">' + esc(item.content) + '</textarea></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Attach File' + (item.file_name ? ' <span class="text-xs text-zinc-400">(current: ' + esc(item.file_name) + ')</span>' : '')
      + '<input name="file" type="file" class="mt-1 w-full text-sm text-zinc-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-teal-50 dark:file:bg-teal-950/30 file:text-teal-700 dark:file:text-teal-300 hover:file:bg-teal-100 dark:hover:file:bg-teal-950/50"></label>'
      + '<p id="infoFormErr" class="text-red-500 text-xs hidden"></p>'
      + '<div class="flex gap-2 pt-2">'
      + '<button type="button" onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button type="submit" id="infoSubmitBtn" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Save Changes</button></div></form>';
    m.classList.remove("hidden");

    document.getElementById("infoForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("infoSubmitBtn");
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = "Saving...";
      var f = e.target;
      var formData = new FormData();
      formData.append("title", f.elements["title"].value);
      formData.append("content", f.elements["content"].value);
      var fileInput = f.elements["file"];
      if (fileInput && fileInput.files[0]) {
        formData.append("file", fileInput.files[0]);
      }

      fetch("/api/admin/info/" + item.id, {
        method: "PUT",
        body: formData,
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btn.disabled = false;
          btn.textContent = "Save Changes";
          if (res.ok) {
            closeModal();
            loadInfo();
          } else {
            var err = document.getElementById("infoFormErr");
            err.textContent = res.detail || "Error updating announcement";
            err.classList.remove("hidden");
          }
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Save Changes";
          var err = document.getElementById("infoFormErr");
          err.textContent = "Network error";
          err.classList.remove("hidden");
        });
    });
  }

  function deleteInfo(infoId) {
    if (!confirm("Delete this announcement? This cannot be undone.")) return;
    fetch("/api/admin/info/" + infoId, { method: "DELETE" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        loadInfo();
      })
      .catch(function () {
        alert("Failed to delete announcement.");
      });
  }

  function debounceSearchInfo() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      loadInfo();
    }, 300);
  }

  window.loadInfo = loadInfo;
  window.openViewInfoModal = openViewInfoModal;
  window.openCreateInfoModal = openCreateInfoModal;
  window.openEditInfoModal = openEditInfoModal;
  window.deleteInfo = deleteInfo;
  window.debounceSearchInfo = debounceSearchInfo;
  window.closeModal = window.closeModal || function () {
    document.getElementById("modalOverlay").classList.add("hidden");
    document.getElementById("modalContent").innerHTML = "";
  };

  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
