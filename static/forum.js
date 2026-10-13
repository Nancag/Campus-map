(function () {
  "use strict";

  var SESSION_KEY = "cmp_session";
  var SESSION_VERSION = "2";
  var FORUM_TOPICS = [
    { key: "carpool", label: "拼车交流", icon: "🚗" },
    { key: "life", label: "校园生活", icon: "🏫" },
    { key: "market", label: "闲置交易", icon: "🛒" },
    { key: "activity", label: "活动组队", icon: "🎫" },
    { key: "study", label: "学习交流", icon: "📚" },
    { key: "lost_found", label: "失物招领", icon: "🔍" }
  ];
  var state = {
    token: null,
    username: null,
    gender: null,
    currentTopic: "",
  };

  function topicDisplay(t) {
    if (!t) return "🏫 校园生活";
    for (var i = 0; i < FORUM_TOPICS.length; i++) {
      if (FORUM_TOPICS[i].key === t) {
        return FORUM_TOPICS[i].icon + " " + FORUM_TOPICS[i].label;
      }
    }
    return t;
  }

  function api(method, path, body) {
    var headers = { "Content-Type": "application/json" };
    if (state.token) headers["Authorization"] = "Bearer " + state.token;
    return fetch(path, {
      method: method,
      headers: headers,
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) { return r.json(); });
  }

  function tryRestoreSession() {
    var token = localStorage.getItem("cmp_token");
    if (token) {
      state.token = token;
      state.username = localStorage.getItem("cmp_username");
      state.gender = localStorage.getItem("cmp_gender") || "保密";
      return true;
    }
    var raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return false;
    try {
      var s = JSON.parse(raw);
      if (s.version !== SESSION_VERSION) { localStorage.removeItem(SESSION_KEY); return false; }
      state.token = s.token;
      state.username = s.username;
      state.gender = s.gender;
      localStorage.setItem("cmp_token", state.token);
      localStorage.setItem("cmp_username", state.username);
      localStorage.setItem("cmp_gender", state.gender);
      localStorage.removeItem(SESSION_KEY);
      return true;
    } catch (e) { return false; }
  }

  function showApp() {
    document.getElementById("login-panel").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    var ua = document.getElementById("user-area");
    ua.innerHTML = '<span class="user-badge">' + escapeHtml(state.username) + "</span>" +
      '<button class="logout-btn" id="logout-btn">退出</button>';
    document.getElementById("logout-btn").addEventListener("click", function () {
      localStorage.removeItem("cmp_token");
      localStorage.removeItem("cmp_username");
      localStorage.removeItem("cmp_gender");
      localStorage.removeItem(SESSION_KEY);
      location.reload();
    });
    bindAppEvents();
    loadPosts();
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  function formatTime(iso) {
    var d = new Date(iso);
    var now = new Date();
    var dDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    var nowDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var dayDiff = Math.round((nowDate - dDate) / 86400000);
    var hh = String(d.getHours()).padStart(2, "0");
    var mm = String(d.getMinutes()).padStart(2, "0");
    if (dayDiff === 0) return hh + ":" + mm;
    if (dayDiff === 1) return "昨天 " + hh + ":" + mm;
    var yyyy = d.getFullYear();
    var MM = String(d.getMonth() + 1).padStart(2, "0");
    var DD = String(d.getDate()).padStart(2, "0");
    return yyyy + "-" + MM + "-" + DD + " " + hh + ":" + mm;
  }

  function loadPosts() {
    var qs = "?page=1&size=50";
    if (state.currentTopic) qs += "&topic=" + encodeURIComponent(state.currentTopic);
    api("GET", "/api/posts" + qs).then(function (res) {
      if (res.code !== 0) {
        if (res.code === 401) {
          localStorage.removeItem("cmp_token");
          localStorage.removeItem("cmp_username");
          localStorage.removeItem("cmp_gender");
          localStorage.removeItem(SESSION_KEY);
          location.reload();
        }
        return;
      }
      var items = res.data.items || [];
      var total = res.data.total || 0;
      document.getElementById("post-count").textContent = "共 " + total + " 条";
      var list = document.getElementById("post-list");
      var empty = document.getElementById("empty-tip");
      if (items.length === 0) {
        list.innerHTML = "";
        empty.classList.remove("hidden");
        return;
      }
      empty.classList.add("hidden");
      list.innerHTML = items.map(function (p) {
        var lc = p.likeCount || 0;
        var cc = p.commentCount || 0;
        var topicName = topicDisplay(p.topic);
        var teamBadge = p.tripId ? '<span class="team-badge">🚗 拼车队伍</span>' : "";
        var canDelete = p.authorName === state.username || state.username === "admin";
        var deleteBtn = canDelete ? '<button class="delete-btn" data-id="' + escapeHtml(p.postId) + '">删除</button>' : "";
        return '<div class="post-card' + (p.tripId ? " team-post-card" : "") + '" data-topic="' + escapeHtml(p.topic || "life") + '" data-id="' + escapeHtml(p.postId) + '">' +
          '<div class="post-meta">' +
          '<span class="topic-tag" data-topic="' + escapeHtml(p.topic || "life") + '">' + escapeHtml(topicName) + "</span>" +
          teamBadge +
          '<span class="post-author">' + escapeHtml(p.authorName) + "</span>" +
          '<span class="post-time">' + formatTime(p.createdAt) + "</span>" +
          deleteBtn +
          "</div>" +
          '<div class="post-title">' + escapeHtml(p.title) + "</div>" +
          '<div class="post-preview">' + escapeHtml(p.content) + "</div>" +
          '<div class="post-footer">' +
          '<span class="post-stat">👍 ' + lc + "</span>" +
          '<span class="post-stat">💬 ' + cc + "</span>" +
          "</div>" +
          "</div>";
      }).join("");
      list.querySelectorAll(".post-card").forEach(function (card) {
        card.addEventListener("click", function () {
          openDetail(card.getAttribute("data-id"));
        });
      });
      list.querySelectorAll(".delete-btn").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          deletePost(btn.getAttribute("data-id"));
        });
      });
    });
  }

  function openDetail(postId) {
    state.currentPostId = postId;
    api("GET", "/api/posts/" + postId).then(function (res) {
      if (res.code !== 0) return;
      var p = res.data;
      var liked = p.liked ? " liked" : "";
      var lc = p.likeCount || 0;
      var body = document.getElementById("detail-body");

      var teamHtml = "";
      if (p.trip) {
        var t = p.trip;
        var seats = t.currentSeats + "/" + t.maxSeats;
        var canJoin = t.status === "待出发" && t.currentSeats < t.maxSeats;
        var joinBtn = canJoin
          ? '<button class="btn-join-team" id="forum-join-btn">一键加入队伍</button>'
          : '<span class="team-status-badge">' + escapeHtml(t.status) + "</span>";
        teamHtml =
          '<div class="team-info-card">' +
          '<div class="team-info-title">🚗 ' + escapeHtml(t.teamName || "未命名队伍") + "</div>" +
          '<div class="team-info-row"><span class="ti-label">队长</span><span>' + escapeHtml(t.leaderName) + "</span></div>" +
          '<div class="team-info-row"><span class="ti-label">路线</span><span>' + escapeHtml(t.origin) + " → " + escapeHtml(t.destination) + "</span></div>" +
          '<div class="team-info-row"><span class="ti-label">出发</span><span>' + escapeHtml(t.departAt) + "</span></div>" +
          '<div class="team-info-row"><span class="ti-label">人数</span><span>' + seats + "人</span></div>" +
          '<div class="team-info-row"><span class="ti-label">性别</span><span>' + escapeHtml(t.gender || "不限") + "</span></div>" +
          (t.remark ? '<div class="team-info-row"><span class="ti-label">备注</span><span>' + escapeHtml(t.remark) + "</span></div>" : "") +
          '<div class="team-info-actions">' + joinBtn + "</div>" +
          "</div>";
      }

      body.innerHTML =
        '<div class="detail-meta">' +
        '<span class="topic-tag" data-topic="' + escapeHtml(p.topic || "life") + '">' + escapeHtml(topicDisplay(p.topic)) + "</span>" +
        '<span class="post-author">' + escapeHtml(p.authorName) + "</span>" +
        '<span class="post-time">' + formatTime(p.createdAt) + "</span>" +
        "</div>" +
        "<h2>" + escapeHtml(p.title) + "</h2>" +
        '<div class="detail-content">' + escapeHtml(p.content) + "</div>" +
        teamHtml +
        '<div class="detail-actions">' +
        '<button class="like-btn' + liked + '" id="like-btn">👍 <span id="like-count">' + lc + "</span></button>" +
        "</div>" +
        '<div class="comment-section">' +
        '<h3 class="comment-title">评论</h3>' +
        '<div id="comment-list" class="comment-list"></div>' +
        '<div class="comment-input-area">' +
        '<textarea id="comment-input" class="comment-input" placeholder="写下你的评论（最多300字）" maxlength="300" rows="3"></textarea>' +
        '<button id="comment-submit" class="btn-primary comment-submit-btn">发表评论</button>' +
        "</div>" +
        "</div>";
      document.getElementById("detail-modal").classList.remove("hidden");
      document.getElementById("like-btn").addEventListener("click", function () { toggleLike(postId); });
      document.getElementById("comment-submit").addEventListener("click", function () { submitComment(postId); });
      var joinBtnEl = document.getElementById("forum-join-btn");
      if (joinBtnEl) {
        joinBtnEl.addEventListener("click", function () { joinTeamFromForum(p.tripId); });
      }
      loadComments(postId);
    });
  }

  function toggleLike(postId) {
    api("POST", "/api/posts/" + postId + "/like").then(function (res) {
      if (res.code !== 0) { alert(res.message || "操作失败"); return; }
      var btn = document.getElementById("like-btn");
      var span = document.getElementById("like-count");
      if (btn && span) {
        span.textContent = res.data.likeCount;
        if (res.data.liked) { btn.classList.add("liked"); }
        else { btn.classList.remove("liked"); }
      }
      loadPosts();
    });
  }

  function deletePost(postId) {
    if (!confirm("确认删除该帖子吗？删除后无法恢复。")) return;
    api("DELETE", "/api/posts/" + postId).then(function (res) {
      if (res.code !== 0) { alert(res.message || "删除失败"); return; }
      loadPosts();
    });
  }

  function loadComments(postId) {
    api("GET", "/api/posts/" + postId + "/comments").then(function (res) {
      if (res.code !== 0) return;
      var list = document.getElementById("comment-list");
      if (!list) return;
      var items = res.data.items || [];
      if (items.length === 0) {
        list.innerHTML = '<div class="comment-empty">暂无评论，快来抢沙发</div>';
        return;
      }
      list.innerHTML = items.map(function (c) {
        return '<div class="comment-item">' +
          '<div class="comment-item-meta">' +
          '<span class="comment-author">' + escapeHtml(c.username) + "</span>" +
          '<span class="comment-time">' + formatTime(c.createdAt) + "</span>" +
          "</div>" +
          '<div class="comment-text">' + escapeHtml(c.content) + "</div>" +
          "</div>";
      }).join("");
    });
  }

  function submitComment(postId) {
    var input = document.getElementById("comment-input");
    var content = input.value.trim();
    if (!content) { alert("评论内容不能为空"); return; }
    api("POST", "/api/posts/" + postId + "/comments", { content: content }).then(function (res) {
      if (res.code !== 0) { alert(res.message || "评论失败"); return; }
      input.value = "";
      loadComments(postId);
      loadPosts();
    });
  }

  function openEditor() {
    document.getElementById("edit-title").value = "";
    document.getElementById("edit-topic").value = "life";
    document.getElementById("edit-content").value = "";
    document.getElementById("editor-modal").classList.remove("hidden");
  }

  function submitPost() {
    var title = document.getElementById("edit-title").value.trim();
    var topic = document.getElementById("edit-topic").value;
    var content = document.getElementById("edit-content").value.trim();
    if (!title || !content) {
      alert("标题和内容不能为空");
      return;
    }
    api("POST", "/api/posts", { title: title, topic: topic, content: content }).then(function (res) {
      if (res.code !== 0) {
        alert(res.message || "发布失败");
        return;
      }
      document.getElementById("editor-modal").classList.add("hidden");
      loadPosts();
    });
  }

  function init() {
    if (tryRestoreSession()) {
      showApp();
      return;
    }
    document.getElementById("login-btn").addEventListener("click", function () {
      var name = document.getElementById("login-name").value.trim();
      var gender = document.getElementById("login-gender").value;
      if (!name) { alert("请输入昵称"); return; }
      api("POST", "/api/guest/enter", { username: name, gender: gender }).then(function (res) {
        if (res.code !== 0) { alert(res.message || "进入失败"); return; }
        state.token = res.data.token;
        state.username = name;
        state.gender = gender;
        localStorage.setItem("cmp_token", state.token);
        localStorage.setItem("cmp_username", state.username);
        localStorage.setItem("cmp_gender", state.gender);
        showApp();
      });
    });

    document.getElementById("login-name").addEventListener("keydown", function (e) {
      if (e.key === "Enter") document.getElementById("login-btn").click();
    });
  }

  if (document.readyState !== "loading") {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }

  function openTeamEditor() {
    api("GET", "/api/my-teams").then(function (res) {
      if (res.code !== 0) { alert(res.message || "获取队伍失败"); return; }
      var teams = res.data.items || [];
      var sel = document.getElementById("team-select");
      if (teams.length === 0) {
        sel.innerHTML = '<option value="">暂无队伍，请先在地图页创建队伍</option>';
      } else {
        sel.innerHTML = teams.map(function (t) {
          var label = (t.teamName || t.destination || "未命名") + " · " + t.origin + "→" + t.destination + " · " + t.status;
          return '<option value="' + escapeHtml(t.tripId) + '">' + escapeHtml(label) + "</option>";
        }).join("");
      }
      document.getElementById("team-edit-title").value = "";
      document.getElementById("team-edit-content").value = "";
      document.getElementById("team-edit-msg").textContent = "";
      document.getElementById("team-editor-modal").classList.remove("hidden");
    });
  }

  function submitTeamPost() {
    var tripId = document.getElementById("team-select").value;
    if (!tripId) { alert("请先选择一支队伍"); return; }
    var title = document.getElementById("team-edit-title").value.trim();
    var content = document.getElementById("team-edit-content").value.trim();
    if (!title || !content) { alert("标题和内容不能为空"); return; }
    api("POST", "/api/posts", { title: title, topic: "carpool", content: content, tripId: tripId }).then(function (res) {
      if (res.code !== 0) {
        document.getElementById("team-edit-msg").textContent = res.message || "发布失败";
        return;
      }
      document.getElementById("team-editor-modal").classList.add("hidden");
      loadPosts();
    });
  }

  function joinTeamFromForum(tripId) {
    api("POST", "/api/trips/" + tripId + "/join").then(function (res) {
      if (res.code !== 0) { alert(res.message || "加入失败"); return; }
      alert("加入成功！");
      openDetail(state.currentPostId);
    });
  }

  function bindAppEvents() {
    document.querySelectorAll(".tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        state.currentTopic = tab.getAttribute("data-topic");
        loadPosts();
      });
    });

    document.getElementById("new-post-btn").addEventListener("click", openEditor);
    document.getElementById("new-team-post-btn").addEventListener("click", openTeamEditor);
    document.getElementById("edit-cancel").addEventListener("click", function () {
      document.getElementById("editor-modal").classList.add("hidden");
    });
    document.getElementById("edit-submit").addEventListener("click", submitPost);
    document.getElementById("team-edit-cancel").addEventListener("click", function () {
      document.getElementById("team-editor-modal").classList.add("hidden");
    });
    document.getElementById("team-edit-submit").addEventListener("click", submitTeamPost);
    document.getElementById("detail-close").addEventListener("click", function () {
      document.getElementById("detail-modal").classList.add("hidden");
    });
    document.querySelectorAll(".modal-overlay").forEach(function (ov) {
      ov.addEventListener("click", function () {
        document.getElementById("editor-modal").classList.add("hidden");
        document.getElementById("detail-modal").classList.add("hidden");
        document.getElementById("team-editor-modal").classList.add("hidden");
      });
    });
  }
})();