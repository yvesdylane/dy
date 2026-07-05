(function () {
  'use strict';

  loadComplaints();

  function getFilterParams() {
    var typeVal = document.getElementById("complaintTypeFilter").value;
    var deptVal = document.getElementById("complaintDeptFilter").value;
    var params = new URLSearchParams();
    if (typeVal) params.set("complain_type", typeVal);
    if (deptVal) params.set("department", deptVal);
    return params.toString();
  }

  function loadComplaints() {
    var list = document.getElementById("complaintsList");
    if (!list) return;
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-teal-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/complaints?" + getFilterParams())
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        renderComplaints(res.complaints || []);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-sm text-red-500 py-8 text-center">Failed to load complaints.</p>';
      });
  }

  function renderComplaints(items) {
    var el = document.getElementById("complaintsList");
    if (!el) return;
    if (!items || items.length === 0) {
      el.innerHTML = '<p class="text-sm text-zinc-400 py-8 text-center">No complaints or advice yet.</p>';
      return;
    }
    var html = "";
    for (var i = 0; i < items.length; i++) {
      var c = items[i];
      var typeLabel = c.complain_type === "complaint" ? "Complaint" : "Advice";
      var typeClass = c.complain_type === "complaint"
        ? "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300"
        : "bg-blue-100 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300";
      html += '<div class="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-2 cursor-pointer hover:shadow-sm transition-shadow break-words overflow-hidden" onclick="openViewComplaintModal(' + c.id + ')">'
        + '<div class="flex items-start justify-between gap-2 flex-wrap">'
        + '<span class="text-xs px-2 py-0.5 rounded-full font-medium ' + typeClass + '">' + typeLabel + '</span>'
        + (c.department ? '<span class="text-xs px-2 py-0.5 rounded-full font-medium bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300">' + esc(c.department) + '</span>' : '')
        + '</div>'
        + '<p class="text-xs text-zinc-700 dark:text-zinc-300 line-clamp-3">' + esc(c.content) + '</p>'
        + '<div class="flex items-center gap-3 text-xs text-zinc-400 flex-wrap">'
        + (c.group ? '<span>Group ' + esc(c.group) + '</span>' : '')
        + (c.created_at ? '<span>' + c.created_at.slice(0, 10) + '</span>' : '')
        + '</div></div>';
    }
    el.innerHTML = html;
  }

  function openViewComplaintModal(complaintId) {
    fetch("/api/admin/complaints/" + complaintId)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.detail);
        showViewModal(res.complaint);
      })
      .catch(function () {
        alert("Failed to load complaint.");
      });
  }

  function showViewModal(item) {
    var m = document.getElementById("modalOverlay");
    var c = document.getElementById("modalContent");
    var typeLabel = item.complain_type === "complaint" ? "Complaint" : "Advice";
    var typeClass = item.complain_type === "complaint"
      ? "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300"
      : "bg-blue-100 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300";
    c.innerHTML = ''
      + '<div class="flex items-start justify-between gap-3">'
      + '<span class="text-xs px-2 py-0.5 rounded-full font-medium ' + typeClass + '">' + typeLabel + '</span>'
      + (item.department ? '<span class="text-xs px-2 py-0.5 rounded-full font-medium bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300">' + esc(item.department) + '</span>' : '')
      + '</div>'
      + '<p class="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap mt-3">' + esc(item.content) + '</p>'
      + '<div class="flex items-center gap-3 text-xs text-zinc-400 mt-3 flex-wrap">'
      + (item.group ? '<span>Group ' + esc(item.group) + '</span>' : '')
      + (item.created_at ? '<span>' + item.created_at.slice(0, 10) + '</span>' : '')
      + '</div>'
      + '<div class="flex gap-2 pt-4">'
      + '<button onclick="closeModal(); deleteComplaint(' + item.id + ')" class="flex-1 py-2.5 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors">Delete</button>'
      + '<button onclick="closeModal()" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Close</button>'
      + '</div>';
    m.classList.remove("hidden");
  }

  function deleteComplaint(complaintId) {
    if (!confirm("Delete this complaint? This cannot be undone.")) return;
    fetch("/api/admin/complaints/" + complaintId, { method: "DELETE" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        loadComplaints();
      })
      .catch(function () {
        alert("Failed to delete complaint.");
      });
  }

  function exportComplaintsCSV() {
    var params = getFilterParams();
    var url = "/api/admin/complaints?" + params + (params ? "&" : "") + "format=csv";
    window.open(url, "_blank");
  }

  window.loadComplaints = loadComplaints;
  window.openViewComplaintModal = openViewComplaintModal;
  window.deleteComplaint = deleteComplaint;
  window.exportComplaintsCSV = exportComplaintsCSV;
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
