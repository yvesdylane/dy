(function () {
  'use strict';

  var searchTimer;

  loadNotes();

  function loadNotes() {
    var q = document.getElementById("notesSearch").value.trim();
    var dept = document.getElementById("notesDeptFilter").value;
    var params = new URLSearchParams();
    if (q) params.set("q", q);
    if (dept) params.set("department", dept);

    var list = document.getElementById("notesList");
    if (!list) return;
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/notes?" + params.toString())
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        renderNotes(res.notes || []);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-sm text-red-500 py-8 text-center">Failed to load notes.</p>';
      });
  }

  function renderNotes(notes) {
    var el = document.getElementById("notesList");
    if (!el) return;
    if (!notes || notes.length === 0) {
      el.innerHTML = '<p class="text-sm text-zinc-400 py-8 text-center">No notes found.</p>';
      return;
    }
    var html = "";
    for (var i = 0; i < notes.length; i++) {
      var n = notes[i];
      html += '<div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-2 cursor-pointer hover:shadow-sm transition-shadow break-words overflow-hidden" onclick="openViewNoteModal(' + n.id + ')">'
        + '<div class="flex items-start justify-between gap-2">'
        + '<h3 class="text-sm font-semibold">' + esc(n.title) + '</h3>'
        + (n.department ? '<span class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300">' + esc(n.department) + '</span>' : '')
        + '</div>'
        + (n.content ? '<p class="text-xs text-zinc-500 line-clamp-2">' + esc(n.content) + '</p>' : '')
        + '<div class="flex items-center gap-3 text-xs text-zinc-400 flex-wrap">'
        + (n.uploader_name ? '<span>' + esc(n.uploader_name + " " + (n.uploader_surname || "")) + '</span>' : '')
        + (n.created_at ? '<span>' + n.created_at.slice(0, 10) + '</span>' : '')
        + (n.file_name ? '<span class="inline-flex items-center gap-1 max-w-full overflow-hidden"><svg class="w-3 h-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg><span class="truncate">' + esc(n.file_name) + '</span></span>' : '')
        + '</div></div>';
    }
    el.innerHTML = html;
  }

  function openViewNoteModal(noteId) {
    fetch("/api/admin/notes/" + noteId)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        showViewModal(res.note);
      })
      .catch(function () {
        alert("Failed to load note.");
      });
  }

  function showViewModal(note) {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<div class="flex items-start justify-between gap-3">'
      + '<h3 class="text-lg font-bold">' + esc(note.title) + '</h3>'
      + (note.department ? '<span class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300">' + esc(note.department) + '</span>' : '')
      + '</div>'
      + (note.content ? '<p class="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap mt-3">' + esc(note.content) + '</p>' : '')
      + '<div class="flex items-center gap-3 text-xs text-zinc-400 mt-3">'
      + (note.uploader_name ? '<span>By ' + esc(note.uploader_name + " " + (note.uploader_surname || "")) + '</span>' : '')
      + (note.created_at ? '<span>' + note.created_at.slice(0, 10) + '</span>' : '')
      + '</div>'
      + (note.file_name ? '<div class="mt-3"><a href="/api/admin/notes/' + note.id + '/file" download="' + esc(note.file_name) + '" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-xs font-medium text-zinc-700 dark:text-zinc-300 transition-colors"><svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' + esc(note.file_name) + '</a></div>' : '')
      + '<div class="flex gap-2 pt-4">'
      + '<button onclick="closeModal(); openEditNoteModal(' + note.id + ')" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Edit</button>'
      + '<button onclick="closeModal(); deleteNote(' + note.id + ')" class="flex-1 py-2.5 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors">Delete</button>'
      + '<button onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Close</button>'
      + '</div>';
    m.classList.remove("hidden");
  }

  function openCreateNoteModal() {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<h3 class="text-lg font-bold mb-1">Create Note</h3>'
      + '<p class="text-xs text-zinc-500 mb-4">Add a new note for a department.</p>'
      + '<form id="noteForm" class="space-y-3" onsubmit="return false">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Title *'
      + '<input name="title" type="text" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Content'
      + '<textarea name="content" rows="4" class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></textarea></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Department *'
      + '<select name="department" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">'
      + '<option value="">Select department</option><option value="ISM">ISM</option><option value="SWE">SWE</option><option value="CGWD">CGWD</option><option value="EDM">EDM</option><option value="CSN">CSN</option><option value="DBMS">DBMS</option><option value="NWS">NWS</option></select></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Attach File'
      + '<input name="file" type="file" class="mt-1 w-full text-sm text-zinc-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-teal-50 dark:file:bg-teal-950/30 file:text-teal-700 dark:file:text-teal-300 hover:file:bg-teal-100 dark:hover:file:bg-teal-950/50"></label>'
      + '<p id="noteFormErr" class="text-red-500 text-xs hidden"></p>'
      + '<div class="flex gap-2 pt-2">'
      + '<button type="button" onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button type="submit" id="noteSubmitBtn" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Create</button></div></form>';
    m.classList.remove("hidden");

    document.getElementById("noteForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("noteSubmitBtn");
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = "Creating...";
      var f = e.target;
      var formData = new FormData();
      formData.append("title", f.elements["title"].value);
      formData.append("content", f.elements["content"].value);
      formData.append("department", f.elements["department"].value);
      var fileInput = f.elements["file"];
      if (fileInput && fileInput.files[0]) {
        formData.append("file", fileInput.files[0]);
      }

      fetch("/api/admin/notes", {
        method: "POST",
        body: formData,
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btn.disabled = false;
          btn.textContent = "Create";
          if (res.ok) {
            closeModal();
            loadNotes();
          } else {
            var err = document.getElementById("noteFormErr");
            err.textContent = res.detail || "Error creating note";
            err.classList.remove("hidden");
          }
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Create";
          var err = document.getElementById("noteFormErr");
          err.textContent = "Network error";
          err.classList.remove("hidden");
        });
    });
  }

  function openEditNoteModal(noteId) {
    fetch("/api/admin/notes/" + noteId)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        showEditNoteModal(res.note);
      })
      .catch(function () {
        alert("Failed to load note data.");
      });
  }

  function showEditNoteModal(note) {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<h3 class="text-lg font-bold mb-1">Edit Note</h3>'
      + '<p class="text-xs text-zinc-500 mb-4">Update the note details below.</p>'
      + '<form id="noteForm" class="space-y-3" onsubmit="return false">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Title *'
      + '<input name="title" type="text" value="' + esc(note.title) + '" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Content'
      + '<textarea name="content" rows="4" class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">' + esc(note.content || "") + '</textarea></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Department *'
      + '<select name="department" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">'
      + '<option value="ISM"' + (note.department === "ISM" ? " selected" : "") + '>ISM</option><option value="SWE"' + (note.department === "SWE" ? " selected" : "") + '>SWE</option><option value="CGWD"' + (note.department === "CGWD" ? " selected" : "") + '>CGWD</option><option value="EDM"' + (note.department === "EDM" ? " selected" : "") + '>EDM</option><option value="CSN"' + (note.department === "CSN" ? " selected" : "") + '>CSN</option><option value="DBMS"' + (note.department === "DBMS" ? " selected" : "") + '>DBMS</option><option value="NWS"' + (note.department === "NWS" ? " selected" : "") + '>NWS</option></select></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Attach File' + (note.file_name ? ' <span class="text-xs text-zinc-400">(current: ' + esc(note.file_name) + ')</span>' : '')
      + '<input name="file" type="file" class="mt-1 w-full text-sm text-zinc-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-teal-50 dark:file:bg-teal-950/30 file:text-teal-700 dark:file:text-teal-300 hover:file:bg-teal-100 dark:hover:file:bg-teal-950/50"></label>'
      + '<p id="noteFormErr" class="text-red-500 text-xs hidden"></p>'
      + '<div class="flex gap-2 pt-2">'
      + '<button type="button" onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button type="submit" id="noteSubmitBtn" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Save Changes</button></div></form>';
    m.classList.remove("hidden");

    document.getElementById("noteForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("noteSubmitBtn");
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = "Saving...";
      var f = e.target;
      var formData = new FormData();
      formData.append("title", f.elements["title"].value);
      formData.append("content", f.elements["content"].value);
      formData.append("department", f.elements["department"].value);
      var fileInput = f.elements["file"];
      if (fileInput && fileInput.files[0]) {
        formData.append("file", fileInput.files[0]);
      }

      fetch("/api/admin/notes/" + note.id, {
        method: "PUT",
        body: formData,
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btn.disabled = false;
          btn.textContent = "Save Changes";
          if (res.ok) {
            closeModal();
            loadNotes();
          } else {
            var err = document.getElementById("noteFormErr");
            err.textContent = res.detail || "Error updating note";
            err.classList.remove("hidden");
          }
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Save Changes";
          var err = document.getElementById("noteFormErr");
          err.textContent = "Network error";
          err.classList.remove("hidden");
        });
    });
  }

  function deleteNote(noteId) {
    if (!confirm("Delete this note? This cannot be undone.")) return;
    fetch("/api/admin/notes/" + noteId, { method: "DELETE" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        loadNotes();
      })
      .catch(function () {
        alert("Failed to delete note.");
      });
  }

  function debounceSearchNotes() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      loadNotes();
    }, 300);
  }

  window.loadNotes = loadNotes;
  window.openViewNoteModal = openViewNoteModal;
  window.openCreateNoteModal = openCreateNoteModal;
  window.openEditNoteModal = openEditNoteModal;
  window.deleteNote = deleteNote;
  window.debounceSearchNotes = debounceSearchNotes;
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
