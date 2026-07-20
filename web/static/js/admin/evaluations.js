(function () {
  'use strict';

  var currentUserRole = document.getElementById("appView").getAttribute("data-current-user-role");
  var evalDate = document.getElementById("evalDate");
  var listView = document.getElementById("evalListView");
  var saveBtn = document.getElementById("saveAllEvals");
  var createBtn = document.getElementById("createEvalsBtn");
  var missingDiv = document.getElementById("evalMissing");
  var missingCount = document.getElementById("missingCount");
  var missingList = document.getElementById("missingList");
  var includeInactiveCheck = document.getElementById("includeInactiveCheck");
  var includeInactiveLabel = document.getElementById("evalIncludeInactive");
  var evalInfo = document.getElementById("evalInfo");
  var prevPageBtn = document.getElementById("evalPrevPage");
  var nextPageBtn = document.getElementById("evalNextPage");

  var currentPage = 0;
  var pageLimit = 20;
  var searchTimer = null;

  var FIELDS = ["punctuality","professionalism","dressing","conduct","teamwork","participation","leadership","presentation","communication"];
  var FIELD_LABELS = {punctuality:"Punct",professionalism:"Prof",dressing:"Dress",conduct:"Cond",teamwork:"Team",participation:"Part",leadership:"Lead",presentation:"Pres",communication:"Comm"};

  if (currentUserRole === "super_admin") {
    includeInactiveLabel.classList.remove("hidden");
  }

  // --- Dept dropdown init ---
  function initDeptDropdown(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var toggle = container.querySelector(".dept-dropdown-toggle");
    var menu = container.querySelector(".dept-dropdown-menu");
    var label = container.querySelector(".dept-dropdown-label");
    if (!toggle || !menu || !label) return;

    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      menu.classList.toggle("hidden");
    });

    container.querySelectorAll(".dept-checkbox").forEach(function (cb) {
      cb.addEventListener("change", function () {
        var checked = container.querySelectorAll(".dept-checkbox:checked");
        var names = Array.from(checked).map(function (c) { return c.value; });
        label.textContent = names.length ? names.join(", ") : "All Departments";
        currentPage = 0;
        loadEvaluations();
      });
    });

    document.addEventListener("click", function (e) {
      if (!container.contains(e.target)) menu.classList.add("hidden");
    });
  }

  initDeptDropdown("evalDeptDropdown");

  function todayStr() {
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  if (!evalDate.value) evalDate.value = todayStr();

  function getDepts() {
    return Array.from(document.querySelectorAll("#evalDeptDropdown .dept-checkbox:checked")).map(function (b) { return b.value; });
  }

  function getParams() {
    var params = "date=" + encodeURIComponent(evalDate.value);
    var depts = getDepts();
    if (depts.length > 0) params += "&departments=" + depts.join(",");
    if (includeInactiveCheck && includeInactiveCheck.checked) params += "&include_inactive=true";
    var q = document.getElementById("evalSearchInput");
    if (q && q.value.trim()) params += "&q=" + encodeURIComponent(q.value.trim());
    params += "&skip=" + (currentPage * pageLimit) + "&limit=" + pageLimit;
    return params;
  }

  function loadEvaluations() {
    saveBtn.disabled = true;
    listView.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-brand-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/evaluations?" + getParams())
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error("Failed");
        renderEvals(data.evaluations);
        updatePagination(data.total || 0);
        loadMissing();
        saveBtn.disabled = false;
      })
      .catch(function () {
        listView.innerHTML = '<p class="text-center py-8 text-red-400 text-sm">Failed to load</p>';
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

  function renderEvals(evals) {
    if (!evals || evals.length === 0) {
      listView.innerHTML = '<p class="text-center py-8 text-zinc-400 text-sm">No evaluations for this date</p>';
      createBtn.classList.remove("hidden");
      return;
    }
    createBtn.classList.add("hidden");

    if (window.innerWidth < 768) {
      renderMobileCards(evals);
    } else {
      renderDesktopTable(evals);
    }
  }

  // ── Desktop: table ──
  function renderDesktopTable(evals) {
    var html = '<div class="overflow-x-auto"><table class="w-full text-sm border-collapse"><thead><tr class="bg-zinc-100 dark:bg-zinc-800">'
      + '<th class="text-left p-2 whitespace-nowrap sticky left-0 bg-zinc-100 dark:bg-zinc-800">Intern</th>'
      + '<th class="text-left p-2 whitespace-nowrap">Dept</th>'
      + '<th class="text-left p-2 whitespace-nowrap">Grp</th>';
    FIELDS.forEach(function (f) {
      html += '<th class="text-center p-2 whitespace-nowrap text-[11px]">' + f.charAt(0).toUpperCase() + f.slice(1) + '</th>';
    });
    html += '<th class="text-center p-2 whitespace-nowrap">Total</th><th class="text-center p-2 whitespace-nowrap">Notes</th></tr></thead><tbody>';

    evals.forEach(function (e) {
      var name = esc(e.user_name) + " " + esc(e.user_surname);
      var total = e.total || 0;
      var color = total >= 40 ? "text-green-600 dark:text-green-400" : total >= 30 ? "text-yellow-600 dark:text-yellow-400" : "text-red-600 dark:text-red-400";

      html += '<tr class="eval-row border-b border-zinc-200 dark:border-zinc-800" data-user-id="' + e.user_id + '">'
        + '<td class="p-2 sticky left-0 bg-white dark:bg-zinc-950 whitespace-nowrap font-medium text-xs">' + name + '</td>'
        + '<td class="p-2 text-zinc-500 text-xs">' + (e.department || "-") + '</td>'
        + '<td class="p-2 text-zinc-500 text-xs">' + (e.group || "-") + '</td>';

      FIELDS.forEach(function (f) {
        var val = e[f];
        html += '<td class="text-center p-1"><select class="eval-score w-12 px-1 py-1 text-xs border rounded dark:bg-zinc-800 dark:border-zinc-700" data-field="' + f + '">';
        html += '<option value="">-</option>';
        for (var i = 1; i <= 5; i++) {
          html += '<option value="' + i + '"' + (val === i ? " selected" : "") + ">" + i + "</option>";
        }
        html += "</select></td>";
      });

      html += '<td class="text-center p-2 font-bold text-xs ' + color + ' eval-total">' + total + '</td>'
        + '<td class="text-center p-1"><input type="text" class="eval-notes w-16 px-1 py-1 text-xs border rounded dark:bg-zinc-800 dark:border-zinc-700" value="' + esc(e.notes || "") + '" maxlength="200"></td>'
        + "</tr>";
    });

    html += "</tbody></table></div>";
    listView.innerHTML = html;
  }

  // ── Mobile: cards ──
  function renderMobileCards(evals) {
    var html = '<div class="space-y-3">';

    evals.forEach(function (e) {
      var name = esc(e.user_name) + " " + esc(e.user_surname);
      var total = e.total || 0;
      var dot = total >= 40 ? "bg-green-500" : total >= 30 ? "bg-yellow-500" : "bg-red-500";

      html += '<div class="eval-row rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-3" data-user-id="' + e.user_id + '">'
        + '<div class="flex items-center justify-between mb-2">'
        + '<div class="min-w-0 flex-1"><p class="font-medium text-sm truncate">' + name + '</p>'
        + '<p class="text-xs text-zinc-500">' + (e.department || "-") + ' · ' + (e.group || "-") + '</p></div>'
        + '<div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full ' + dot + '"></span><span class="eval-total font-bold text-sm">' + total + '</span></div>'
        + '</div>'
        + '<div class="grid grid-cols-3 gap-1.5">';

      FIELDS.forEach(function (f) {
        var val = e[f];
        html += '<div><label class="block text-[10px] text-zinc-400 mb-0.5">' + (FIELD_LABELS[f] || f) + '</label>'
          + '<select class="eval-score w-full px-1 py-1 text-xs border rounded dark:bg-zinc-800 dark:border-zinc-700" data-field="' + f + '">'
          + '<option value="">-</option>';
        for (var i = 1; i <= 5; i++) {
          html += '<option value="' + i + '"' + (val === i ? " selected" : "") + ">" + i + "</option>";
        }
        html += '</select></div>';
      });

      html += '</div>'
        + '<div class="mt-1.5"><input type="text" class="eval-notes w-full px-2 py-1 text-xs border rounded dark:bg-zinc-800 dark:border-zinc-700" value="' + esc(e.notes || "") + '" maxlength="200" placeholder="Notes..."></div>'
        + '</div>';
    });

    html += "</div>";
    listView.innerHTML = html;
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
    document.querySelectorAll(".eval-row").forEach(function (row) {
      var total = 0;
      row.querySelectorAll(".eval-score").forEach(function (sel) {
        if (sel.value) total += parseInt(sel.value);
      });
      var el = row.querySelector(".eval-total");
      if (el) {
        el.textContent = total;
        var dot = row.querySelector(".w-2\\.5");
        if (dot) {
          dot.className = "w-2.5 h-2.5 rounded-full " + (total >= 40 ? "bg-green-500" : total >= 30 ? "bg-yellow-500" : "bg-red-500");
        }
        el.className = "eval-total font-bold text-sm " + (total >= 40 ? "text-green-600 dark:text-green-400" : total >= 30 ? "text-yellow-600 dark:text-yellow-400" : "text-red-600 dark:text-red-400");
      }
    });
  }

  function updatePagination(total) {
    if (evalInfo) evalInfo.textContent = total + " evaluation" + (total !== 1 ? "s" : "");
    if (prevPageBtn) prevPageBtn.disabled = currentPage <= 0;
    if (nextPageBtn) nextPageBtn.disabled = (currentPage + 1) * pageLimit >= total;
  }

  function changeEvalPage(delta) {
    currentPage += delta;
    if (currentPage < 0) currentPage = 0;
    loadEvaluations();
  }

  function debounceSearchEvals() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      currentPage = 0;
      loadEvaluations();
    }, 300);
  }

  function toggleEvalSearch() {
    var bar = document.getElementById("evalSearchBar");
    var input = document.getElementById("evalSearchInput");
    if (bar.classList.contains("hidden")) {
      bar.classList.remove("hidden");
      setTimeout(function () { input.focus(); }, 100);
    } else {
      bar.classList.add("hidden");
      if (input.value.trim()) {
        input.value = "";
        currentPage = 0;
        loadEvaluations();
      }
    }
  }

  // ── Event wiring ──
  evalDate.addEventListener("change", function () {
    currentPage = 0;
    loadEvaluations();
  });

  document.addEventListener("change", function (e) {
    if (e.target.closest(".eval-score")) {
      updateTotals();
    }
    if (e.target === includeInactiveCheck) {
      currentPage = 0;
      loadEvaluations();
    }
  });

  createBtn.addEventListener("click", function () {
    var ds = evalDate.value;
    if (!ds) return;
    var depts = getDepts();
    var body = { date: ds };
    if (depts.length) body.departments = depts.join(",");
    createBtn.disabled = true; createBtn.textContent = "Creating...";
    fetch("/api/admin/evaluations/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        createBtn.disabled = false; createBtn.textContent = "Create";
        if (data.ok) loadEvaluations();
        else alert(data.detail || "Failed");
      })
      .catch(function () {
        createBtn.disabled = false; createBtn.textContent = "Create";
        alert("Network error");
      });
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
        saveBtn.textContent = allOk ? "Saved!" : "Error";
        setTimeout(function () { saveBtn.textContent = "Save All"; saveBtn.disabled = false; }, 2000);
        if (allOk) loadEvaluations();
      })
      .catch(function () {
        saveBtn.textContent = "Error";
        setTimeout(function () { saveBtn.textContent = "Save All"; saveBtn.disabled = false; }, 2000);
      });
  });

  // ── Resize listener for responsive layout ──
  var resizeTimer;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      var evals = listView.querySelectorAll(".eval-row");
      if (evals.length > 0) {
        fetch("/api/admin/evaluations?" + getParams())
          .then(function (r) { return r.json(); })
          .then(function (data) { if (data.ok) renderEvals(data.evaluations); })
          .catch(function () {});
      }
    }, 300);
  });

  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  window.toggleEvalSearch = toggleEvalSearch;
  window.changeEvalPage = changeEvalPage;
  window.debounceSearchEvals = debounceSearchEvals;

  loadEvaluations();
})();
