(function () {
  'use strict';

  var currentUserRole = document.getElementById("appView").getAttribute("data-current-user-role");
  var evalDate = document.getElementById("evalDate");
  var tbody = document.getElementById("evalTableBody");
  var saveBtn = document.getElementById("saveAllEvals");
  var missingDiv = document.getElementById("evalMissing");
  var missingCount = document.getElementById("missingCount");
  var missingList = document.getElementById("missingList");
  var includeInactiveCheck = document.getElementById("includeInactiveCheck");
  var includeInactiveLabel = document.getElementById("evalIncludeInactive");

  var selectedDepts = [];
  var selectedGroup = "";

  if (currentUserRole === "super_admin") {
    includeInactiveLabel.classList.remove("hidden");
  }

  function todayStr() {
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  if (!evalDate.value) evalDate.value = todayStr();

  function getParams() {
    var params = "date=" + encodeURIComponent(evalDate.value);
    if (selectedDepts.length > 0) params += "&departments=" + selectedDepts.join(",");
    if (selectedGroup) params += "&group=" + selectedGroup;
    if (includeInactiveCheck && includeInactiveCheck.checked) params += "&include_inactive=true";
    return params;
  }

  function loadEvaluations() {
    saveBtn.disabled = true;
    tbody.innerHTML = '<tr><td colspan="14" class="text-center py-8 text-zinc-400">Loading...</td></tr>';

    fetch("/api/admin/evaluations?" + getParams())
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error("Failed");
        renderTable(data.evaluations);
        loadMissing();
        saveBtn.disabled = false;
      })
      .catch(function () {
        tbody.innerHTML = '<tr><td colspan="14" class="text-center py-8 text-red-400">Failed to load</td></tr>';
      });
  }

  function loadMissing() {
    fetch("/api/admin/evaluations/missing?" + getParams())
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && data.missing && data.missing.length > 0) {
          missingDiv.classList.remove("hidden");
          missingCount.textContent = data.missing.length;
          missingList.textContent = " " + data.missing.map(function (m) { return m.name + " " + m.surname; }).join(", ");
        } else {
          missingDiv.classList.add("hidden");
        }
      })
      .catch(function () {});
  }

  function renderTable(evals) {
    if (!evals || evals.length === 0) {
      tbody.innerHTML = '<tr><td colspan="14" class="text-center py-8 text-zinc-400">No evaluations for this date</td></tr>';
      return;
    }

    var html = "";
    var fields = ["punctuality", "professionalism", "dressing", "conduct", "teamwork", "participation", "leadership", "presentation", "communication"];

    evals.forEach(function (e) {
      var name = e.user_name + " " + e.user_surname;
      var total = e.total || 0;
      var color = total >= 40 ? "text-green-600 dark:text-green-400" : total >= 30 ? "text-yellow-600 dark:text-yellow-400" : "text-red-600 dark:text-red-400";

      html += '<tr class="border-b border-zinc-200 dark:border-zinc-800 eval-row" data-user-id="' + e.user_id + '">';
      html += '<td class="p-2 sticky left-0 bg-white dark:bg-zinc-950 whitespace-nowrap font-medium">' + name + '</td>';
      html += '<td class="p-2 text-zinc-500">' + (e.department || "-") + '</td>';
      html += '<td class="p-2 text-zinc-500">' + (e.group || "-") + '</td>';

      fields.forEach(function (f) {
        var val = e[f];
        html += '<td class="text-center p-2"><select class="eval-score w-14 px-1 py-1 text-xs border rounded dark:bg-zinc-800 dark:border-zinc-700" data-field="' + f + '">';
        html += '<option value="">-</option>';
        for (var i = 1; i <= 5; i++) {
          html += '<option value="' + i + '"' + (val === i ? " selected" : "") + ">" + i + "</option>";
        }
        html += "</select></td>";
      });

      html += '<td class="text-center p-2 font-bold ' + color + ' eval-total">' + total + '</td>';
      html += '<td class="text-center p-2"><input type="text" class="eval-notes w-20 px-1 py-1 text-xs border rounded dark:bg-zinc-800 dark:border-zinc-700" value="' + (e.notes || "") + '" maxlength="200"></td>';
      html += "</tr>";
    });

    tbody.innerHTML = html;
  }

  function collectData() {
    var rows = document.querySelectorAll(".eval-row");
    var results = [];
    rows.forEach(function (row) {
      var userId = parseInt(row.getAttribute("data-user-id"));
      var scores = { user_id: userId, date: evalDate.value };
      row.querySelectorAll(".eval-score").forEach(function (sel) {
        if (sel.value) scores[sel.getAttribute("data-field")] = parseInt(sel.value);
      });
      var notes = row.querySelector(".eval-notes");
      if (notes && notes.value) scores.notes = notes.value;
      results.push(scores);
    });
    return results;
  }

  function updateTotals() {
    var fields = ["punctuality", "professionalism", "dressing", "conduct", "teamwork", "participation", "leadership", "presentation", "communication"];
    document.querySelectorAll(".eval-row").forEach(function (row) {
      var total = 0;
      row.querySelectorAll(".eval-score").forEach(function (sel) {
        if (sel.value) total += parseInt(sel.value);
      });
      var el = row.querySelector(".eval-total");
      if (el) {
        el.textContent = total;
        el.className = "text-center p-2 font-bold eval-total " + (total >= 40 ? "text-green-600 dark:text-green-400" : total >= 30 ? "text-yellow-600 dark:text-yellow-400" : "text-red-600 dark:text-red-400");
      }
    });
  }

  evalDate.addEventListener("change", loadEvaluations);

  document.addEventListener("click", function (e) {
    var deptPill = e.target.closest("#evalDeptPills .dept-pill");
    if (deptPill) {
      var dept = deptPill.getAttribute("data-dept");
      if (dept === "") {
        selectedDepts = [];
        document.querySelectorAll("#evalDeptPills .dept-pill").forEach(function (p) {
          p.classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
          p.classList.add("text-zinc-600", "dark:text-zinc-300");
        });
        deptPill.classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
        deptPill.classList.remove("text-zinc-600", "dark:text-zinc-300");
      } else {
        document.querySelector("#evalDeptPills .dept-pill[data-dept='']").className = "dept-pill px-2.5 py-1 text-[11px] font-medium rounded-md text-zinc-600 dark:text-zinc-300";
        var idx = selectedDepts.indexOf(dept);
        if (idx > -1) {
          selectedDepts.splice(idx, 1);
          deptPill.classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
          deptPill.classList.add("text-zinc-600", "dark:text-zinc-300");
        } else {
          selectedDepts.push(dept);
          deptPill.classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
          deptPill.classList.remove("text-zinc-600", "dark:text-zinc-300");
        }
        if (selectedDepts.length === 0) {
          document.querySelector("#evalDeptPills .dept-pill[data-dept='']").className = "dept-pill px-2.5 py-1 text-[11px] font-medium rounded-md bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm";
        }
      }
      loadEvaluations();
      return;
    }

    var groupPill = e.target.closest("#evalGroupPills .group-pill");
    if (groupPill) {
      selectedGroup = groupPill.getAttribute("data-group");
      document.querySelectorAll("#evalGroupPills .group-pill").forEach(function (p) {
        p.classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
        p.classList.add("text-zinc-600", "dark:text-zinc-300");
      });
      groupPill.classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
      groupPill.classList.remove("text-zinc-600", "dark:text-zinc-300");
      loadEvaluations();
      return;
    }
  });

  document.addEventListener("change", function (e) {
    if (e.target.closest(".eval-score")) {
      updateTotals();
    }
    if (e.target === includeInactiveCheck) {
      loadEvaluations();
    }
  });

  saveBtn.addEventListener("click", function () {
    var dataList = collectData();
    if (dataList.length === 0) return;
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    var promises = dataList.map(function (data) {
      return fetch("/api/admin/evaluations/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then(function (r) { return r.json(); });
    });

    Promise.all(promises)
      .then(function (results) {
        var allOk = results.every(function (r) { return r.ok; });
        if (allOk) {
          saveBtn.textContent = "Saved!";
          setTimeout(function () { saveBtn.textContent = "Save All"; saveBtn.disabled = false; }, 2000);
          loadEvaluations();
        } else {
          saveBtn.textContent = "Error";
          setTimeout(function () { saveBtn.textContent = "Save All"; saveBtn.disabled = false; }, 2000);
        }
      })
      .catch(function () {
        saveBtn.textContent = "Error";
        setTimeout(function () { saveBtn.textContent = "Save All"; saveBtn.disabled = false; }, 2000);
      });
  });

  loadEvaluations();
})();
