(function () {
  'use strict';

  var currentPage = 0;
  var pageLimit = 20;
  var searchTimer = null;
  var currentUserRole = document.getElementById("appView").dataset.currentUserRole;

  var df = window.dashboardFilter;
  if (df) {
    window.dashboardFilter = null;
    if (df.role) {
      var roleSel = document.getElementById("filterRole");
      if (roleSel) roleSel.value = df.role;
    }
    if (df.fees_paid_min) {
      var feesInput = document.getElementById("filterFees");
      if (feesInput) feesInput.value = df.fees_paid_min;
    }
    if (df.fully_paid) {
      var paidChk = document.getElementById("filterFullyPaid");
      if (paidChk) paidChk.checked = true;
    }
  }

  loadUsers();

  // --- Tab switching ---
  function switchPeopleTab(name) {
    var usersTab = document.getElementById("peopleUsersTab");
    var codesTab = document.getElementById("peopleCodesTab");
    var pills = document.querySelectorAll(".people-tab");
    if (name === "codes") {
      usersTab.classList.add("hidden");
      codesTab.classList.remove("hidden");
      pills[0].classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
      pills[0].classList.add("text-zinc-600", "dark:text-zinc-300");
      pills[1].classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
      pills[1].classList.remove("text-zinc-600", "dark:text-zinc-300");
      loadPeopleCodes();
    } else {
      codesTab.classList.add("hidden");
      usersTab.classList.remove("hidden");
      pills[1].classList.remove("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
      pills[1].classList.add("text-zinc-600", "dark:text-zinc-300");
      pills[0].classList.add("bg-white", "dark:bg-zinc-700", "text-zinc-900", "dark:text-zinc-100", "shadow-sm");
      pills[0].classList.remove("text-zinc-600", "dark:text-zinc-300");
    }
  }

  // --- Codes functions ---
  function loadPeopleCodes() {
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
      html += '<div class="flex items-center gap-2 p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">'
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
    updateCodeButtons();
  }

  function updateCodeButtons() {
    var checked = document.querySelectorAll("#peopleCodesTab .code-checkbox:checked");
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
            loadPeopleCodes();
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

  // --- Search toggle ---
  function toggleSearch() {
    var bar = document.getElementById("searchBar");
    bar.classList.toggle("hidden");
    if (!bar.classList.contains("hidden")) {
      document.getElementById("userSearch").focus();
    }
  }

  // --- Load ---
  function loadUsers() {
    currentPage = 0;
    fetchUsers();
  }

  function getFilterParams() {
    var q = document.getElementById("userSearch").value.trim();
    var role = document.getElementById("filterRole").value;
    var depts = Array.from(document.querySelectorAll("#filterDeptDropdown .dept-checkbox:checked"))
      .map(function (b) { return b.value; });
    var group = document.getElementById("filterGroup").value;
    var gender = document.getElementById("filterGender").value;
    var feesMin = document.getElementById("filterFees").value;
    var fullyPaid = document.getElementById("filterFullyPaid").checked;
    var status = document.getElementById("filterStatus").value;
    var params = "?skip=" + (currentPage * pageLimit) + "&limit=" + pageLimit;
    if (q) params += "&q=" + encodeURIComponent(q);
    if (role) params += "&role=" + role;
    if (depts.length) params += "&departments=" + depts.join(",");
    if (group) params += "&group=" + group;
    if (gender) params += "&gender=" + gender;
    if (status) params += "&is_active=" + status;
    if (feesMin) params += "&fees_paid_min=" + feesMin;
    if (fullyPaid) params += "&fully_paid=true";
    return params;
  }

  function fetchUsers() {
    var list = document.getElementById("usersList");
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-brand-500 border-t-transparent rounded-full"></div></div>';

    return fetch("/api/admin/users" + getFilterParams())
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function (data) {
        renderUsers(data.users || []);
        updatePagination(data.total || 0);
      })
      .catch(function () {
        list.innerHTML = '<p class="text-center py-8 text-red-400 text-sm">Failed to load users.</p>';
      });
  }

  function renderUsers(users) {
    var list = document.getElementById("usersList");
    if (users.length === 0) {
      list.innerHTML = '<p class="text-center py-8 text-zinc-400 text-sm">No users found.</p>';
      return;
    }
    var html = "";
    users.forEach(function (u) {
      var roleColor = u.role === "admin" || u.role === "super_admin"
        ? "bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300"
        : u.role === "instructor"
        ? "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300"
        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300";

      var meta = u.department;
      if (u.group) meta += " \u00b7 Group " + u.group;
      if (u.quarter) meta += " \u00b7 " + esc(u.quarter);
      meta += " \u00b7 " + esc(u.phone);
      if (u.fees_paid) meta += ' \u00b7 <span class="' + (u.fees_paid >= u.total_fees ? 'text-emerald-600 dark:text-emerald-400' : 'text-zinc-500') + '">\u00A3' + u.fees_paid + '</span>';

      var initials = (u.name[0] + u.surname[0]).toUpperCase();
      var avatarHtml = u.photo_url
        ? '<img src="' + u.photo_url + '" class="w-full h-full object-cover" loading="lazy">'
        : '<span class="text-xs font-bold text-brand-700 dark:text-brand-300">' + initials + '</span>';
      var avatarClass = u.photo_url
        ? 'w-9 h-9 rounded-full shrink-0 overflow-hidden'
        : 'w-9 h-9 rounded-full bg-brand-200 dark:bg-brand-800 text-brand-700 dark:text-brand-300 flex items-center justify-center text-xs font-bold shrink-0';

      html += '<div class="user-row p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors" data-user-id="' + u.id + '" onclick="openEditUserModal(' + u.id + ')">'
        + '<div class="flex items-center gap-3 min-w-0 flex-1">'
        + '<div class="' + avatarClass + '">' + avatarHtml + '</div>'
        + '<div class="min-w-0 flex-1">'
        + '<p class="font-medium text-sm truncate">' + esc(u.name) + ' ' + esc(u.surname) + '</p>'
        + '<p class="text-xs text-zinc-500 truncate">' + meta + '</p>'
        + '</div>'
        + '</div>'
        + '<div class="flex items-center gap-1.5 shrink-0">'
        + (u.is_active === false ? '<span class="text-xs px-2 py-0.5 rounded-full font-medium bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400">Inactive</span>' : '')
        + '<span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ' + roleColor + '">' + u.role.replace("_", " ") + '</span>'
        + '</div>'
        + '</div>';
    });
    list.innerHTML = html;
    // Pre-cache profile images for instant subsequent loads
    users.forEach(function (u) {
      if (u.photo_url) { var img = new Image(); img.src = u.photo_url; }
    });
  }

  function updatePagination(total) {
    var info = document.getElementById("usersInfo");
    var prevBtn = document.getElementById("prevPage");
    var nextBtn = document.getElementById("nextPage");
    if (info) info.textContent = total + " user" + (total !== 1 ? "s" : "");
    if (prevBtn) prevBtn.disabled = currentPage <= 0;
    if (nextBtn) nextBtn.disabled = (currentPage + 1) * pageLimit >= total;
  }

  function changePage(delta) {
    currentPage += delta;
    if (currentPage < 0) currentPage = 0;
    fetchUsers();
  }

  function debounceSearchUsers() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      currentPage = 0;
      fetchUsers();
    }, 300);
  }

  // --- Edit / Create modal ---
  function openEditUserModal(userId) {
    stopCaptureCamera();
    pendingPhotoFile = null;
    editingUserId = userId;
    fetch("/api/admin/users/" + userId)
      .then(function (r) { return r.json(); })
      .then(function (u) {
        var html = buildUserForm(u);
        window.openModal(html);
      })
      .catch(function () {
        window.openModal('<p class="text-red-400 text-center">Failed to load user.</p>');
      });
  }

  function openAddUserModal() {
    stopCaptureCamera();
    pendingPhotoFile = null;
    var html = buildUserForm(null);
    window.openModal(html);
  }

  var pendingPhotoFile = null;
  var editingUserId = null;
  var savingUser = false;
  var deletingUser = false;
  var cameraCaptureStream = null;
  var cameraCaptureFacing = "environment";

  document.addEventListener("click", function (e) {
    if (e.target === document.getElementById("modalOverlay")) {
      stopCaptureCamera();
    }
  });

  function buildUserForm(u) {
    var isEdit = u !== null;
    var title = isEdit ? "Edit User" : "Add User";
    var btnText = isEdit ? "Save Changes" : "Create User";
    var initials = u ? (u.name[0] + u.surname[0]).toUpperCase() : "?";
    var photoUrl = u && u.photo_url ? u.photo_url : null;

    var avatarHtml = photoUrl
      ? '<img id="photoPreview" src="' + photoUrl + '" class="w-14 h-14 rounded-full object-cover">'
      : '<div class="w-14 h-14 rounded-full bg-brand-200 dark:bg-brand-800 text-brand-700 dark:text-brand-300 flex items-center justify-center text-xl font-bold shrink-0" id="photoInitials">' + initials + '</div>';

    return '<h3 class="text-lg font-bold mb-1">' + title + '</h3>'
      + '<div id="photoSection" class="flex items-center gap-4 mb-4 pb-4 border-b border-zinc-200 dark:border-zinc-700">'
      + '<div class="relative shrink-0">'
      + '<div id="avatarWrap" class="w-14 h-14 rounded-full overflow-hidden cursor-pointer group">'
      + avatarHtml
      + '<div class="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">'
      + '<svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>'
      + '</div></div>'
      + '<input type="file" id="photoInput" accept="image/*" class="hidden">'
      + '</div>'
      + '<div class="flex-1 grid grid-cols-2 gap-2">'
      + field("name", "First name", u ? u.name : "", false)
      + field("surname", "Last name", u ? u.surname : "", false)
      + '</div>'
      + '</div>'
      + '<div id="cameraCaptureView" class="hidden mb-4">'
      + '<div class="relative w-full max-w-xs mx-auto">'
      + '<video id="cameraCaptureVideo" autoplay playsinline class="w-full rounded-lg bg-black" style="aspect-ratio:3/4"></video>'
      + '<button id="captureCloseBtn" class="absolute top-1 right-1 p-1.5 rounded-full bg-black/50 text-white hover:bg-black/70 text-sm leading-none transition-colors">\u2715</button>'
      + '</div>'
      + '<div class="flex items-center justify-center gap-6 mt-2">'
      + '<button id="captureToggleBtn" class="p-2 rounded-full bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600 transition-colors" type="button">'
      + '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>'
      + '</button>'
      + '<button id="captureBtn" class="w-14 h-14 rounded-full border-4 border-zinc-400 dark:border-zinc-500 bg-transparent hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors flex items-center justify-center" type="button">'
      + '<div class="w-10 h-10 rounded-full bg-zinc-500 dark:bg-zinc-400"></div>'
      + '</button>'
      + '</div>'
      + '<div class="text-center mt-1">'
      + '<button id="captureGalleryBtn" class="text-xs text-zinc-400 underline hover:text-zinc-300 transition-colors" type="button">Upload from gallery</button>'
      + '</div>'
      + '</div>'

      + '<div class="space-y-3">'
      + '<div class="grid grid-cols-2 gap-3">'
      + field("quarter", "Quarter/Neighborhood", u ? (u.quarter || "") : "", false)
      + field("school", "School", u ? u.school : "", false)
      + '</div>'
      + '<div class="grid grid-cols-2 gap-3">'
      + '<label class="block text-xs font-medium text-zinc-500">Gender</label>'
      + '<label class="block text-xs font-medium text-zinc-500">Role</label>'
      + '</div><div class="grid grid-cols-2 gap-3">'
      + selectField("gender", ["male", "female"], u ? u.gender : "male")
      + selectField("role", ["intern", "instructor", "admin", "super_admin"], u ? u.role : "intern")
      + '</div>'
      + '<div class="grid grid-cols-2 gap-3">'
      + selectField("department", ["ISM", "SWE", "CGWD", "EDM", "CSN", "DBMS", "NWS"], u ? u.department : "ISM")
      + selectField("group", ["", "A", "B", "C"], u ? (u.group || "") : "")
      + '</div>'
      + field("phone", "Phone", u ? u.phone : "", false)
      + field("email", "Email", u ? u.email || "" : "", false)
      + field("dob", "Date of Birth", u ? u.dob : "", false, "date")
      + (isEdit && currentUserRole === 'super_admin' ? '<div><label class="block text-xs font-medium text-zinc-500 mb-1">Status</label>' + selectField("is_active", ["true", "false"], u ? (u.is_active !== false ? "true" : "false") : "true") + '</div>' : '')
      + '<div class="grid grid-cols-2 gap-3">'
      + field("total_fees", "Total Fees", u ? u.total_fees : "40000", false, "number")
      + field("fees_paid", "Fees Paid", u ? u.fees_paid : "0", false, "number")
      + '</div>'
      + '</div>'
      + '<div class="flex gap-2 justify-end pt-3 border-t border-zinc-200 dark:border-zinc-700 mt-4">'
      + '<button onclick="window.closeModal()" class="px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button onclick="saveUser(' + (u ? u.id : "null") + ')" class="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">' + btnText + '</button>'
      + '</div>';
  }

  function field(id, label, value, disabled, type) {
    type = type || "text";
    var lbl = label ? '<label for="f-' + id + '" class="block text-xs font-medium text-zinc-500">' + label + '</label>' : '';
    return lbl + '<input id="f-' + id + '" type="' + type + '" value="' + esc(value) + '" step="any" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"/>';
  }

  function selectField(id, options, selected) {
    var opts = options.map(function (o) {
      var sel = o === selected ? ' selected' : '';
      return '<option value="' + o + '"' + sel + '>' + (o || "\u2014") + '</option>';
    }).join("");
    return '<select id="f-' + id + '" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">' + opts + '</select>';
  }

  function saveUser(userId) {
    if (savingUser) return;
    savingUser = true;
    var data = {
      name: document.getElementById("f-name").value.trim(),
      surname: document.getElementById("f-surname").value.trim(),
      email: document.getElementById("f-email").value.trim() || null,
      phone: document.getElementById("f-phone").value.trim(),
      gender: document.getElementById("f-gender").value,
      role: document.getElementById("f-role").value,
      department: document.getElementById("f-department").value,
      group: document.getElementById("f-group").value || null,
      quarter: document.getElementById("f-quarter").value.trim() || null,
      dob: document.getElementById("f-dob").value,
      school: document.getElementById("f-school").value.trim(),
      total_fees: parseFloat(document.getElementById("f-total_fees").value) || 0,
      fees_paid: parseFloat(document.getElementById("f-fees_paid").value) || 0,
    };
    var url, method;
    if (userId) {
      var isActiveEl = document.getElementById("f-is_active");
      if (isActiveEl) data.is_active = isActiveEl.value === "true";
      url = "/api/admin/users/" + userId;
      method = "PUT";
      data.telegram_id = document.getElementById("f-telegram_id")
        ? document.getElementById("f-telegram_id").value.trim()
        : undefined;
    } else {
      url = "/api/admin/users";
      method = "POST";
    }
    fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function (saved) {
        savingUser = false;
        stopCaptureCamera();
        window.closeModal();
        var savedId = saved.id || userId;
        if (pendingPhotoFile) {
          var file = pendingPhotoFile;
          pendingPhotoFile = null;
          uploadPhoto(savedId, file).then(function () {
            window.refreshHeaderAvatar(savedId);
            return fetchUsers();
          }).then(function () {
            var card = document.querySelector('.user-row[data-user-id="' + savedId + '"]');
            if (card) {
              var img = card.querySelector('img');
              if (img) img.src = img.src.split('?')[0] + '?t=' + Date.now();
            }
          }).catch(function () {
            if (pendingPhotoFile) pendingPhotoFile = null;
            fetchUsers();
            setTimeout(function () { alert("Photo upload failed. User data was saved."); }, 100);
          });
        } else {
          fetchUsers();
        }
      })
      .catch(function () {
        savingUser = false;
        alert("Failed to save user. Check console for details.");
      });
  }

  function uploadPhoto(userId, file) {
    var form = new FormData();
    form.append("file", file);
    return fetch("/api/admin/users/" + userId + "/photo", {
      method: "POST",
      body: form,
    }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
  }

  function deleteUser(userId) {
    if (deletingUser || !confirm("Delete this user? This cannot be undone.")) return;
    deletingUser = true;
    fetch("/api/admin/users/" + userId, { method: "DELETE" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        deletingUser = false;
        stopCaptureCamera();
        window.closeModal();
        fetchUsers();
      })
      .catch(function () {
        deletingUser = false;
        alert("Failed to delete user.");
      });
  }

  // --- Utility ---
  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // --- Photo upload handler ---
  document.addEventListener("change", function (e) {
    if (e.target.id === "photoInput") {
      var file = e.target.files[0];
      if (!file) return;
      pendingPhotoFile = file;
      var reader = new FileReader();
      reader.onload = function (ev) {
        var wrap = document.getElementById("avatarWrap");
        if (!wrap) return;
        wrap.innerHTML = '<img id="photoPreview" src="' + ev.target.result + '" class="w-14 h-14 rounded-full object-cover">';
      };
      reader.readAsDataURL(file);
    }
  });

  // --- Camera capture handlers ---
  document.addEventListener("click", function (e) {
    if (e.target.closest("#captureCloseBtn")) {
      stopCaptureCamera();
    }
  });
  document.addEventListener("click", function (e) {
    if (e.target.closest("#captureBtn")) {
      captureSnapshot();
    }
  });
  document.addEventListener("click", function (e) {
    if (e.target.closest("#captureToggleBtn")) {
      toggleCaptureCamera();
    }
  });
  document.addEventListener("click", function (e) {
    if (e.target.closest("#captureGalleryBtn")) {
      var input = document.getElementById("photoInput");
      if (input) input.click();
    }
  });



  function startCaptureCamera() {
    if (cameraCaptureStream) return;
    navigator.mediaDevices.getUserMedia({
      video: { facingMode: cameraCaptureFacing, width: { ideal: 640 }, height: { ideal: 480 } },
    })
      .then(function (stream) {
        cameraCaptureStream = stream;
        var video = document.getElementById("cameraCaptureVideo");
        video.srcObject = stream;
        document.getElementById("photoSection").classList.add("hidden");
        document.getElementById("cameraCaptureView").classList.remove("hidden");
      })
      .catch(function (err) {
        alert("Camera access denied: " + err.message);
      });
  }

  function stopCaptureCamera() {
    if (cameraCaptureStream) {
      cameraCaptureStream.getTracks().forEach(function (t) { t.stop(); });
      cameraCaptureStream = null;
    }
    var video = document.getElementById("cameraCaptureVideo");
    if (video) video.srcObject = null;
    var view = document.getElementById("cameraCaptureView");
    if (view) view.classList.add("hidden");
    var section = document.getElementById("photoSection");
    if (section) section.classList.remove("hidden");
  }

  function captureSnapshot() {
    var video = document.getElementById("cameraCaptureVideo");
    if (!video || !video.videoWidth) return;
    var canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    var ctx = canvas.getContext("2d");
    if (cameraCaptureFacing === "user") {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(function (blob) {
      var file = new File([blob], "capture.jpg", { type: "image/jpeg" });
      pendingPhotoFile = file;
      var reader = new FileReader();
      reader.onload = function (ev) {
        var wrap = document.getElementById("avatarWrap");
        if (wrap) wrap.innerHTML = '<img id="photoPreview" src="' + ev.target.result + '" class="w-full h-full object-cover">';
      };
      reader.readAsDataURL(file);
      stopCaptureCamera();
    }, "image/jpeg", 0.8);
  }

  function toggleCaptureCamera() {
    if (!cameraCaptureStream) return;
    cameraCaptureFacing = cameraCaptureFacing === "environment" ? "user" : "environment";
    cameraCaptureStream.getTracks().forEach(function (t) { t.stop(); });
    cameraCaptureStream = null;
    var video = document.getElementById("cameraCaptureVideo");
    video.srcObject = null;
    navigator.mediaDevices.getUserMedia({
      video: { facingMode: cameraCaptureFacing, width: { ideal: 640 }, height: { ideal: 480 } },
    })
      .then(function (stream) {
        cameraCaptureStream = stream;
        video.srcObject = stream;
      })
      .catch(function (err) {
        alert("Camera access denied: " + err.message);
        document.getElementById("cameraCaptureView").classList.add("hidden");
        document.getElementById("photoSection").classList.remove("hidden");
      });
  }

  function stopCaptureOnModalClose() {
    stopCaptureCamera();
  }

  document.addEventListener("click", function (e) {
    if (e.target.closest("#avatarWrap")) {
      startCaptureCamera();
    }
  });

  // --- Event wiring ---
  document.addEventListener("change", function (e) {
    if (e.target.classList.contains("code-checkbox")) updateCodeButtons();
  });

  document.addEventListener("change", function (e) {
    if (e.target.id === "selectAllCodes") {
      document.querySelectorAll("#peopleCodesTab .code-checkbox").forEach(function (cb) {
        cb.checked = e.target.checked;
      });
      updateCodeButtons();
    }
  });

  document.addEventListener("click", function (e) {
    var d = e.target.closest(".del-code-btn");
    if (!d || d.disabled || !confirm("Delete this code?")) return;
    d.disabled = true;
    fetch("/api/admin/codes/" + d.dataset.id, { method: "DELETE" })
      .then(function () { loadPeopleCodes(); })
      .catch(function () { d.disabled = false; });
  });

  document.getElementById("deleteSelectedCodesBtn")?.addEventListener("click", function () {
    var btn = this;
    if (btn.disabled) return;
    var checked = document.querySelectorAll("#peopleCodesTab .code-checkbox:checked");
    var ids = Array.from(checked).map(function (cb) { return parseInt(cb.dataset.id); });
    if (!ids.length || !confirm("Delete " + ids.length + " selected code" + (ids.length > 1 ? "s" : "") + "?")) return;
    btn.disabled = true;
    btn.textContent = "Deleting...";
    fetch("/api/admin/codes/delete-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: ids }),
    })
      .then(function () { loadPeopleCodes(); })
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
      .then(function () { loadPeopleCodes(); })
      .catch(function () { btn.disabled = false; btn.textContent = "Delete All"; });
  });

  // --- Dept dropdown ---
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
        loadUsers();
      });
    });

    document.addEventListener("click", function (e) {
      if (!container.contains(e.target)) menu.classList.add("hidden");
    });
  }

  initDeptDropdown("filterDeptDropdown");

  // --- Pill click delegation ---
  document.addEventListener("click", function (e) {
    var pill = e.target.closest(".people-tab");
    if (pill) switchPeopleTab(pill.dataset.peopleTab);
  });

  // --- Global exports ---
  window.toggleSearch = toggleSearch;
  window.openEditUserModal = openEditUserModal;
  window.openAddUserModal = openAddUserModal;
  window.openAddCodeModal = openAddCodeModal;
  window.saveUser = saveUser;
  window.deleteUser = deleteUser;
  window.changePage = changePage;
  window.debounceSearchUsers = debounceSearchUsers;
  window.loadUsers = loadUsers;
  window.switchPeopleTab = switchPeopleTab;
})();