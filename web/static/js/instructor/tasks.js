(function () {
  'use strict';

  var tasksData = [];

  document.getElementById("taskGroupFilter")?.addEventListener("change", renderTasks);
  document.getElementById("taskStatusFilter")?.addEventListener("change", renderTasks);

  fetch("/api/admin/tasks")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data.ok) throw new Error("Failed");
      tasksData = data.tasks || [];
      renderTasks();
    })
    .catch(function () {
      document.getElementById("taskList").innerHTML = '<p class="text-red-400 text-sm text-center py-8">Failed to load tasks</p>';
    });

  function renderTasks() {
    var group = document.getElementById("taskGroupFilter").value;
    var status = document.getElementById("taskStatusFilter").value;
    var list = document.getElementById("taskList");

    var filtered = tasksData.filter(function (t) {
      if (group && t.group !== group) return false;
      if (status && t.status !== status) return false;
      return true;
    });

    if (filtered.length === 0) {
      list.innerHTML = '<p class="text-zinc-400 text-sm text-center py-8">No tasks found</p>';
      return;
    }

    list.innerHTML = filtered.map(function (t) {
      var statusColor = t.status === "open"
        ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30"
        : "text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800";
      return '<div class="p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">'
        + '<div class="flex items-center justify-between">'
        + '<h3 class="font-medium text-sm truncate">' + esc(t.title) + '</h3>'
        + '<span class="text-xs px-2 py-0.5 rounded-full font-medium ' + statusColor + '">' + t.status + '</span>'
        + '</div>'
        + '<p class="text-xs text-zinc-400 mt-1">' + (t.description ? esc(t.description.substring(0, 100)) : "") + '</p>'
        + '<div class="flex items-center gap-2 mt-2">'
        + '<span class="text-xs text-zinc-500">' + (t.group ? "Group " + t.group : "All") + '</span>'
        + '<span class="text-xs text-zinc-500">\u00b7</span>'
        + '<span class="text-xs text-zinc-500">Due: ' + (t.due_date || "—") + '</span>'
        + '<button class="view-submissions-btn ml-auto text-xs font-medium text-teal-600 dark:text-teal-400 hover:underline" data-task-id="' + t.id + '">Submissions</button>'
        + '</div>'
        + '</div>';
    }).join("");
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".view-submissions-btn");
    if (btn) {
      e.preventDefault();
      loadSubmissions(parseInt(btn.dataset.taskId));
    }
  });

  function loadSubmissions(taskId) {
    fetch("/api/admin/tasks/" + taskId + "/submissions")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error("Failed");
        showSubmissionsModal(taskId, data.submissions || []);
      })
      .catch(function () {
        alert("Failed to load submissions");
      });
  }

  function showSubmissionsModal(taskId, submissions) {
    var html = '<h2 class="text-lg font-bold">Submissions</h2>';
    if (submissions.length === 0) {
      html += '<p class="text-sm text-zinc-400 py-4">No submissions yet.</p>';
    } else {
      html += '<div class="space-y-2 max-h-96 overflow-y-auto">';
      submissions.forEach(function (s) {
        html += '<div class="p-3 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50">'
          + '<div class="flex items-center justify-between">'
          + '<span class="text-sm font-medium">' + esc(s.user_name) + ' ' + esc(s.user_surname) + '</span>'
          + (s.mark_obtained !== null && s.mark_obtained !== undefined
              ? '<span class="text-xs font-medium text-teal-600 dark:text-teal-400">' + s.mark_obtained + '</span>'
              : '<button class="grade-btn text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline" data-submission-id="' + s.id + '" data-user-name="' + esc(s.user_name) + ' ' + esc(s.user_surname) + '">Grade</button>')
          + '</div>'
          + (s.submitted_url ? '<a href="' + esc(s.submitted_url) + '" target="_blank" class="text-xs text-teal-600 dark:text-teal-400 hover:underline block mt-1">View submission</a>' : '')
          + (s.feedback ? '<p class="text-xs text-zinc-400 mt-1">Feedback: ' + esc(s.feedback) + '</p>' : '')
          + '</div>';
      });
      html += '</div>';
    }
    window.openModal(html);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".grade-btn");
    if (btn) {
      e.preventDefault();
      window.closeModal();
      openGradeModal(parseInt(btn.dataset.submissionId), btn.dataset.userName);
    }
  });

  function openGradeModal(submissionId, userName) {
    var html = '<h2 class="text-lg font-bold">Grade: ' + userName + '</h2>'
      + '<div class="flex gap-2 items-center">'
      + '<input id="gradeMarkInput" type="number" step="0.5" min="0" placeholder="Mark" class="flex-1 px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">'
      + '<button id="gradeSaveBtn" class="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium">Save</button>'
      + '</div>'
      + '<textarea id="gradeFeedbackInput" placeholder="Feedback (optional)" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 rows-3"></textarea>';

    window.openModal(html);

    document.getElementById("gradeSaveBtn").addEventListener("click", function () {
      var mark = document.getElementById("gradeMarkInput").value;
      var feedback = document.getElementById("gradeFeedbackInput").value;
      if (!mark) { alert("Enter a mark"); return; }

      fetch("/api/admin/tasks/submission/" + submissionId + "/grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mark_obtained: parseFloat(mark), feedback: feedback }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            window.closeModal();
          } else {
            alert(data.detail || "Failed to save grade");
          }
        })
        .catch(function () {
          alert("Network error");
        });
    });
  }

  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
