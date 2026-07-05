(function () {
  'use strict';

  var searchTimer = null;

  loadTasks();

  function getFilterParams() {
    var q = document.getElementById("taskSearch").value.trim();
    var dept = document.getElementById("filterDept").value;
    var params = "";
    if (q) params += "&q=" + encodeURIComponent(q);
    if (dept) params += "&department=" + dept;
    return params;
  }

  function loadTasks() {
    var list = document.getElementById("tasksList");
    if (!list) return;
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/tasks?" + getFilterParams())
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error(data.detail || "Failed");
        renderTasks(data.tasks || []);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-center py-8 text-red-400 text-sm">Failed to load tasks.</p>';
      });
  }

  function renderTasks(tasks) {
    var list = document.getElementById("tasksList");
    if (!list) return;
    if (tasks.length === 0) {
      list.innerHTML = '<p class="text-center py-8 text-zinc-400 text-sm">No tasks yet.</p>';
      return;
    }
    var html = "";
    tasks.forEach(function (t) {
      var deptBadge = t.department
        ? '<span class="text-xs px-2 py-0.5 rounded-full font-medium bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300">' + esc(t.department) + '</span>'
        : "";
      var fileTag = t.file_name
        ? '<span class="inline-flex items-center gap-1 text-xs text-zinc-500"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' + esc(t.file_name) + '</span>'
        : "";
      var urlTag = t.supporting_doc
        ? '<span class="inline-flex items-center gap-1 text-xs text-teal-600 dark:text-teal-400"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>URL</span>'
        : "";
      var deadline = t.submission_deadline ? new Date(t.submission_deadline).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "";

      html += '<div class="task-card p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors" data-id="' + t.id + '">'
        + '<div class="flex items-start justify-between gap-2">'
        + '<div class="min-w-0 flex-1">'
        + '<p class="font-medium text-sm truncate">' + esc(t.name) + '</p>'
        + '<div class="flex items-center gap-2 mt-1 flex-wrap">'
        + deptBadge
        + '<span class="text-xs text-zinc-500">' + deadline + '</span>'
        + '<span class="text-xs text-zinc-500">' + t.total_mark_on + ' marks</span>'
        + '</div>'
        + '<div class="flex items-center gap-3 mt-1.5">'
        + fileTag
        + urlTag
        + '</div>'
        + '</div>'
        + '<svg class="w-4 h-4 text-zinc-400 shrink-0 mt-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>'
        + '</div>'
        + '</div>';
    });
    list.innerHTML = html;
  }

  document.addEventListener("click", function (e) {
    var card = e.target.closest(".task-card");
    if (!card) return;
    var id = parseInt(card.dataset.id);
    if (!id) return;
    navigateToTaskDetail(id);
  });

  function navigateToTaskDetail(taskId) {
    fetch("/admin/task/" + taskId)
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.text();
      })
      .then(function (html) {
        document.getElementById("content").innerHTML = html;
        var titleEl = document.getElementById("headerTitle");
        if (titleEl) titleEl.textContent = "Task Detail";
      })
      .catch(function () {
        alert("Failed to load task details.");
      });
  }

  function openCreateTaskModal() {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    c.innerHTML = ''
      + '<h3 class="text-lg font-bold mb-1">Create Task</h3>'
      + '<p class="text-xs text-zinc-500 mb-4">Fill in the task details below.</p>'
      + '<form id="taskForm" class="space-y-3" onsubmit="return false">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Name *'
      + '<input name="name" type="text" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Description *'
      + '<textarea name="description" rows="3" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></textarea></label>'
      + '<div class="grid grid-cols-2 gap-3">'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Department *'
      + '<select name="department" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">'
      + '<option value="ISM">ISM</option><option value="SWE">SWE</option><option value="CGWD">CGWD</option><option value="EDM">EDM</option><option value="CSN">CSN</option><option value="DBMS">DBMS</option><option value="NWS">NWS</option></select></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Total Marks *'
      + '<input name="total_mark_on" type="number" value="10" min="1" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '</div>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Submission Deadline *'
      + '<input name="submission_deadline" type="datetime-local" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Supporting Doc URL'
      + '<input name="supporting_doc" type="url" placeholder="https://" class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"></label>'
      + '<label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">Attach File'
      + '<input name="file" type="file" class="mt-1 w-full text-sm text-zinc-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-teal-50 dark:file:bg-teal-950/30 file:text-teal-700 dark:file:text-teal-300 hover:file:bg-teal-100 dark:hover:file:bg-teal-950/50"></label>'
      + '<p id="taskFormErr" class="text-red-500 text-xs hidden"></p>'
      + '<div class="flex gap-2 pt-2">'
      + '<button type="button" onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button type="submit" id="taskSubmitBtn" class="flex-1 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">Create</button></div></form>';
    m.classList.remove("hidden");

    document.getElementById("taskForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = document.getElementById("taskSubmitBtn");
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = "Creating...";
      var f = e.target;
      var formData = new FormData();
      formData.append("name", f.elements["name"].value);
      formData.append("description", f.elements["description"].value);
      formData.append("department", f.elements["department"].value);
      formData.append("total_mark_on", f.elements["total_mark_on"].value);
      var deadline = f.elements["submission_deadline"].value;
      formData.append("submission_deadline", deadline ? new Date(deadline).toISOString() : "");
      var urlVal = f.elements["supporting_doc"].value.trim();
      if (urlVal) formData.append("supporting_doc", urlVal);
      var fileInput = f.elements["file"];
      if (fileInput && fileInput.files[0]) {
        formData.append("file", fileInput.files[0]);
      }

      fetch("/api/admin/tasks", {
        method: "POST",
        body: formData,
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btn.disabled = false;
          btn.textContent = "Create";
          if (res.ok) {
            closeModal();
            loadTasks();
          } else {
            var err = document.getElementById("taskFormErr");
            err.textContent = res.detail || "Error creating task";
            err.classList.remove("hidden");
          }
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Create";
          var err = document.getElementById("taskFormErr");
          err.textContent = "Network error";
          err.classList.remove("hidden");
        });
    });
  }

  function debounceSearchTasks() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      loadTasks();
    }, 300);
  }

  window.navigateToTaskDetail = navigateToTaskDetail;
  window.openCreateTaskModal = openCreateTaskModal;
  window.loadTasks = loadTasks;
  window.debounceSearchTasks = debounceSearchTasks;
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
