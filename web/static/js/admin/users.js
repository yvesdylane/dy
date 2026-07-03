(function () {
  'use strict';

  var currentPage = 0;
  var pageLimit = 50;
  var searchTimer = null;

  loadUsers();

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
    var dept = document.getElementById("filterDept").value;
    var group = document.getElementById("filterGroup").value;
    var gender = document.getElementById("filterGender").value;
    var params = "?skip=" + (currentPage * pageLimit) + "&limit=" + pageLimit;
    if (q) params += "&q=" + encodeURIComponent(q);
    if (role) params += "&role=" + role;
    if (dept) params += "&department=" + dept;
    if (group) params += "&group=" + group;
    if (gender) params += "&gender=" + gender;
    return params;
  }

  function fetchUsers() {
    var list = document.getElementById("usersList");
    list.innerHTML = '<div class="flex justify-center py-8"><div class="animate-spin h-5 w-5 border-2 border-brand-500 border-t-transparent rounded-full"></div></div>';

    fetch("/api/admin/users" + getFilterParams())
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

      html += '<div class="user-row p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors" onclick="openEditUserModal(' + u.id + ')">'
        + '<div class="flex items-center gap-3 min-w-0 flex-1">'
        + '<div class="w-9 h-9 rounded-full bg-brand-200 dark:bg-brand-800 text-brand-700 dark:text-brand-300 flex items-center justify-center text-xs font-bold shrink-0">'
        + (u.name[0] + u.surname[0]).toUpperCase()
        + '</div>'
        + '<div class="min-w-0 flex-1">'
        + '<p class="font-medium text-sm truncate">' + esc(u.name) + ' ' + esc(u.surname) + '</p>'
        + '<p class="text-xs text-zinc-500 truncate">' + meta + '</p>'
        + '</div>'
        + '</div>'
        + '<span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ' + roleColor + '">' + u.role.replace("_", " ") + '</span>'
        + '</div>';
    });
    list.innerHTML = html;
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
    var html = buildUserForm(null);
    window.openModal(html);
  }

  function buildUserForm(u) {
    var isEdit = u !== null;
    var title = isEdit ? "Edit User" : "Add User";
    var btnText = isEdit ? "Save Changes" : "Create User";
    var initials = u ? (u.name[0] + u.surname[0]).toUpperCase() : "?";

    return '<h3 class="text-lg font-bold mb-1">' + title + '</h3>'
      + '<div class="flex items-center gap-4 mb-4 pb-4 border-b border-zinc-200 dark:border-zinc-700">'
      + '<div class="w-14 h-14 rounded-full bg-brand-200 dark:bg-brand-800 text-brand-700 dark:text-brand-300 flex items-center justify-center text-xl font-bold shrink-0">' + initials + '</div>'
      + '<div class="flex-1 grid grid-cols-2 gap-2">'
      + field("name", "First name", u ? u.name : "", false)
      + field("surname", "Last name", u ? u.surname : "", false)
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
      + selectField("group", ["", "A", "B"], u ? (u.group || "") : "")
      + '</div>'
      + field("phone", "Phone", u ? u.phone : "", false)
      + field("email", "Email", u ? u.email || "" : "", false)
      + field("dob", "Date of Birth", u ? u.dob : "", false)
      + '<div class="grid grid-cols-2 gap-3">'
      + field("total_fees", "Total Fees", u ? u.total_fees : "40000", false, "number")
      + field("fees_paid", "Fees Paid", u ? u.fees_paid : "0", false, "number")
      + '</div>'
      + '</div>'
      + '<div class="flex gap-2 justify-end pt-3 border-t border-zinc-200 dark:border-zinc-700 mt-4">'
      + '<button onclick="window.closeModal()" class="px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">Cancel</button>'
      + '<button onclick="saveUser(' + (u ? u.id : "null") + ')" class="px-4 py-2 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium transition-colors">' + btnText + '</button>'
      + '</div>';
  }

  function field(id, label, value, disabled, type) {
    type = type || "text";
    var lbl = label ? '<label for="f-' + id + '" class="block text-xs font-medium text-zinc-500">' + label + '</label>' : '';
    return lbl + '<input id="f-' + id + '" type="' + type + '" value="' + esc(value) + '" step="any" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"/>';
  }

  function selectField(id, options, selected) {
    var opts = options.map(function (o) {
      var sel = o === selected ? ' selected' : '';
      return '<option value="' + o + '"' + sel + '>' + (o || "\u2014") + '</option>';
    }).join("");
    return '<select id="f-' + id + '" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50">' + opts + '</select>';
  }

  function saveUser(userId) {
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
      .then(function () {
        window.closeModal();
        fetchUsers();
        if (window.loadPage) window.loadPage("dashboard");
      })
      .catch(function () {
        alert("Failed to save user. Check console for details.");
      });
  }

  function deleteUser(userId) {
    if (!confirm("Delete this user? This cannot be undone.")) return;
    fetch("/api/admin/users/" + userId, { method: "DELETE" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        window.closeModal();
        fetchUsers();
        if (window.loadPage) window.loadPage("dashboard");
      })
      .catch(function () {
        alert("Failed to delete user.");
      });
  }

  // --- Utility ---
  function esc(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // --- Global event wiring ---
  window.toggleSearch = toggleSearch;
  window.openEditUserModal = openEditUserModal;
  window.openAddUserModal = openAddUserModal;
  window.saveUser = saveUser;
  window.deleteUser = deleteUser;
  window.changePage = changePage;
  window.debounceSearchUsers = debounceSearchUsers;
  window.loadUsers = loadUsers;
})();