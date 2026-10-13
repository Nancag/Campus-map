/* 高德地图 Phase 1 测试页 — 校区 + 校门 PlaceSearch 验证 */

var CAMPUSES = [
  {
    name: "福州外语外贸学院滨海校区",
    shortName: "滨海校区",
    wgs84: { lat: 25.8805227, lng: 119.5566502 },
    city: "福州"
  },
  {
    name: "福州外语外贸学院长乐校区",
    shortName: "长乐校区",
    wgs84: { lat: 25.9259051, lng: 119.4953332 },
    city: "福州"
  }
];

var SEARCH_RADIUS_LEVELS = [100, 300, 500];
var POI_KEYWORD_LIST = ["学校", "图书馆", "体育馆", "便利店", "餐厅", "酒店", "商场", "医院", "生活服务", "公交站", "地铁站", "银行", "超市", "咖啡", "加油站", "停车场", "小区", "写字楼", "公园", "市场"];
var CAMPUS_GATE_NAMES = {
  "滨海校区": ["北门", "南门"],
  "长乐校区": ["北门", "南门", "东门", "西门"]
};
var NOT_FOUND_MESSAGE = "附近暂未识别到明确地点，请点击更靠近地点名称或图标的位置。";
var DATA_SOURCE_LABEL = "高德地图";
var MAX_POI_SNAP_DISTANCE = 50;

var state = {
  map: null,
  markers: [],
  currentCampus: 0,
  campusData: [],
  campusGates: {},
  selectedPoi: null,
  selectedMarker: null,
  isSearching: false,
  lastDistance: 0,
  token: localStorage.getItem("cmp_token") || null,
  username: localStorage.getItem("cmp_username") || null,
  gender: localStorage.getItem("cmp_gender") || "保密",
  trips: [],
  joinedTripIds: new Set(),
  selectedGate: null,
  originMarker: null,
  editingTripId: null,
  calibratingGate: null,
  lastHotspotClickAt: 0
};

function $(id) { return document.getElementById(id); }

async function api(path, opts) {
  opts = opts || {};
  var headers = {};
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  if (opts.body) headers["Content-Type"] = "application/json";
  var res = await fetch(path, {
    method: opts.method || "GET",
    headers: headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  var data = await res.json().catch(function () { return { code: 9001, message: "响应解析失败" }; });
  if (res.status === 401 || data.code === 9001) {
    showGuestOverlay();
  }
  return data;
}

function setMsg(id, text, isErr) {
  var el = $(id);
  if (!el) return;
  el.textContent = text || "";
  el.className = "form-msg" + (isErr ? " err" : "");
}

async function refreshTrips() {
  var campus = CAMPUSES[state.currentCampus];
  var data = await api("/api/trips?origin=" + encodeURIComponent(campus.shortName) + "&size=50");
  if (data.code === 0 && data.data) {
    state.trips = data.data.items || [];
    renderTripList();
  }
}

function renderTripList() {
  var container = $("trip-list");
  if (!container) return;
  if (state.trips.length === 0) {
    container.innerHTML = '<p class="empty-hint">点击地图上的地点创建队伍</p>';
    return;
  }
  container.innerHTML = "";
  state.trips.forEach(function (t) {
    var div = document.createElement("div");
    div.className = "trip-item";
    var seats = t.currentSeats + "/" + t.maxSeats;
    var badge = '<span class="ti-badge ' + statusClass(t.status) + '">' + t.status + '</span>';
    var genderTag = t.gender && t.gender !== "不限" ? " · " + t.gender : "";
    var teamName = t.teamName ? t.teamName : (t.destination || "未命名队伍");
    div.innerHTML =
      '<div class="ti-dest">' + teamName + '</div>' +
      '<div class="ti-meta">' + t.origin + ' → ' + t.destination + ' · ' + t.departAt + ' · ' + seats + '人' + genderTag + '</div>' +
      badge;
    div.addEventListener("click", function () { showTripDetail(t); });
    container.appendChild(div);
  });
}

function statusClass(s) {
  if (s === "待出发") return "open";
  if (s === "已满员") return "full";
  if (s === "已出发") return "departed";
  return "open";
}

function renderGateSelect() {
  var sel = $("gate-select");
  if (!sel) return;
  var campus = CAMPUSES[state.currentCampus];
  var shortName = campus.shortName;
  var cachedGates = state.campusGates[shortName];
  if (cachedGates && Object.keys(cachedGates).length > 0) {
    var options = "";
    var firstGate = null;
    for (var gateName in cachedGates) {
      var g = cachedGates[gateName];
      if (!firstGate) firstGate = g;
      options += '<option value="' + gateName + '">' + g.name + '</option>';
    }
    sel.innerHTML = options;
    state.selectedGate = { name: firstGate.name, lat: firstGate.lat, lng: firstGate.lng, isCampusGate: true, campus: shortName, gateType: firstGate.gateType };
    return;
  }
  var gates = state.campusData[state.currentCampus];
  if (!gates || !gates.gateResult || !gates.gateResult.best) {
    sel.innerHTML = '<option value="">未找到校门</option>';
    state.selectedGate = null;
    return;
  }
  var gate = gates.gateResult.best;
  sel.innerHTML = '<option value="0">' + gate.name + '</option>';
  state.selectedGate = { name: gate.name, lat: gate.location.lat, lng: gate.location.lng };
}

function onGateSelectChange() {
  var sel = $("gate-select");
  if (!sel) return;
  var gateName = sel.value;
  var campus = CAMPUSES[state.currentCampus];
  var shortName = campus.shortName;
  var cachedGates = state.campusGates[shortName];
  if (cachedGates && cachedGates[gateName]) {
    var g = cachedGates[gateName];
    state.selectedGate = { name: g.name, lat: g.lat, lng: g.lng, isCampusGate: true, campus: shortName, gateType: gateName };
    clearOriginMarker();
    setOriginMarker(g);
    console.log("[onGateSelectChange] 出发口已切换:", g.name);
  }
}

function computeTripActions(trip) {
  var isLeader = state.username === trip.leaderName;
  var isJoined = state.joinedTripIds.has(trip.tripId);
  var actions = [];
  if (isLeader) {
    if (trip.status === "待出发" || trip.status === "已满员") {
      actions.push({ type: "depart", label: "标记出发" });
      actions.push({ type: "cancel", label: "取消队伍" });
    } else if (trip.status === "已出发") {
      actions.push({ type: "complete", label: "标记完成" });
    }
    return actions;
  }
  if (isJoined) {
    if (trip.status === "待出发" || trip.status === "已满员") {
      actions.push({ type: "leave", label: "退出队伍" });
    }
    return actions;
  }
  if (trip.status === "待出发" && trip.currentSeats < trip.maxSeats) {
    actions.push({ type: "join", label: "加入队伍" });
  }
  return actions;
}

function showTripDetail(t) {
  var info = $("jm-info");
  var isLeader = state.username === t.leaderName;
  var isJoined = state.joinedTripIds.has(t.tripId);
  var actions = computeTripActions(t);
  var btnsHtml = actions.map(function (a) {
    return '<button class="btn-join" onclick="' + a.type + 'TripFromList(\'' + t.tripId + '\')">' + a.label + '</button>';
  }).join(" ");
  var leaderBtns = "";
  if (isLeader && t.status !== "已取消" && t.status !== "已完成") {
    leaderBtns = '<div class="trip-detail-actions">' +
      '<button class="btn-edit" onclick="openEditTripModal(\'' + t.tripId + '\')">编辑队伍</button>' +
      '<button class="btn-danger" onclick="dissolveTrip(\'' + t.tripId + '\')">解散队伍</button>' +
      '</div>';
  }
  var teamName = t.teamName ? t.teamName : "未命名队伍";
  info.innerHTML =
    '<div class="trip-detail-row"><span class="td-label">队名</span><span class="td-value">' + teamName + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">队长</span><span class="td-value">' + t.leaderName + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">出发地</span><span class="td-value">' + t.origin + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">目的地</span><span class="td-value">' + t.destination + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">出发时间</span><span class="td-value">' + t.departAt + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">人数</span><span class="td-value">' + t.currentSeats + '/' + t.maxSeats + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">费用</span><span class="td-value">' + (t.fee != null ? t.fee + '元' : '免费') + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">性别要求</span><span class="td-value">' + (t.gender || '不限') + '</span></div>' +
    '<div class="trip-detail-row"><span class="td-label">状态</span><span class="td-value">' + t.status + '</span></div>' +
    (t.remark ? '<div class="trip-detail-row"><span class="td-label">备注</span><span class="td-value">' + t.remark + '</span></div>' : '') +
    (btnsHtml ? '<div class="trip-detail-actions">' + btnsHtml + '</div>' : '') +
    leaderBtns;
  setMsg("jm-msg", "");
  $("join-trip-modal").classList.remove("hidden");
  loadTripMembers(t.tripId, isLeader);
}

async function handleTripActionSuccess(data, tripId, keepOpen, successMsg) {
  if (data.code !== 0) { setMsg("jm-msg", data.message, true); return; }
  setMsg("jm-msg", successMsg);
  await refreshTrips();
  if (keepOpen) {
    var updated = state.trips.find(function (t) { return t.tripId === tripId; });
    if (updated) showTripDetail(updated);
    else $("join-trip-modal").classList.add("hidden");
  } else {
    $("join-trip-modal").classList.add("hidden");
  }
}

async function departTripFromList(tripId) {
  var data = await api("/api/trips/" + tripId + "/depart", { method: "POST" });
  await handleTripActionSuccess(data, tripId, true, "已标记出发");
}

async function completeTripFromList(tripId) {
  var data = await api("/api/trips/" + tripId + "/complete", { method: "POST" });
  await handleTripActionSuccess(data, tripId, true, "行程已完成");
}

async function cancelTripFromList(tripId) {
  var data = await api("/api/trips/" + tripId + "/cancel", { method: "POST" });
  await handleTripActionSuccess(data, tripId, false, "队伍已取消");
}

async function leaveTripFromList(tripId) {
  var data = await api("/api/trips/" + tripId + "/leave", { method: "POST" });
  if (data.code === 0) {
    state.joinedTripIds.delete(tripId);
    saveJoinedTripIds();
  }
  await handleTripActionSuccess(data, tripId, false, "已退出队伍");
}

async function joinTripFromList(tripId) {
  var data = await api("/api/trips/" + tripId + "/join", { method: "POST" });
  if (data.code !== 0) { setMsg("jm-msg", data.message, true); return; }
  state.joinedTripIds.add(tripId);
  saveJoinedTripIds();
  setMsg("jm-msg", "加入成功！");
  await refreshTrips();
  var updated = state.trips.find(function (t) { return t.tripId === tripId; });
  if (updated) showTripDetail(updated);
  else $("join-trip-modal").classList.add("hidden");
}

function loadJoinedTripIds() {
  try {
    var raw = localStorage.getItem("cmp_joined_trips");
    if (raw) {
      var arr = JSON.parse(raw);
      state.joinedTripIds = new Set(arr);
    }
  } catch (e) {
    state.joinedTripIds = new Set();
  }
}

function saveJoinedTripIds() {
  try {
    localStorage.setItem("cmp_joined_trips", JSON.stringify(Array.from(state.joinedTripIds)));
  } catch (e) { }
}

function showGuestOverlay() {
  state.token = null;
  state.username = null;
  state.gender = "保密";
  localStorage.removeItem("cmp_token");
  localStorage.removeItem("cmp_username");
  localStorage.removeItem("cmp_gender");
  var ov = $("guest-overlay");
  if (ov) ov.classList.remove("hidden");
  var ub = $("user-badge");
  if (ub) ub.classList.add("hidden");
  var lb = $("logout-btn");
  if (lb) lb.classList.add("hidden");
}

function hideGuestOverlay() {
  var ov = $("guest-overlay");
  if (ov) ov.classList.add("hidden");
  var ub = $("user-badge");
  if (ub) { ub.classList.remove("hidden"); ub.textContent = state.username + " · " + state.gender; }
  var lb = $("logout-btn");
  if (lb) lb.classList.remove("hidden");
}

var pickedGender = "保密";
function initGuestOverlay() {
  var btns = document.querySelectorAll(".gender-btn");
  btns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      btns.forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      pickedGender = btn.getAttribute("data-gender");
    });
  });
  var enterBtn = $("enter-btn");
  if (enterBtn) {
    enterBtn.addEventListener("click", async function () {
      var username = $("nickname-input").value.trim();
      if (!username) { setMsg("guest-msg", "请输入昵称", true); return; }
      var data = await api("/api/guest/enter", { method: "POST", body: { username: username, gender: pickedGender } });
      if (data.code !== 0) { setMsg("guest-msg", data.message, true); return; }
      state.token = data.data.token;
      state.username = data.data.username;
      state.gender = data.data.gender || "保密";
      localStorage.setItem("cmp_token", state.token);
      localStorage.setItem("cmp_username", state.username);
      localStorage.setItem("cmp_gender", state.gender);
      hideGuestOverlay();
      await refreshTrips();
    });
  }
}

function initApp() {
  initGuestOverlay();
  if (!window.CAMPUS_AMAP_CONFIG || !window.CAMPUS_AMAP_CONFIG.key || window.CAMPUS_AMAP_CONFIG.key === "YOUR_AMAP_KEY") {
    $("config-warning").classList.remove("hidden");
    return;
  }

  window._AMapSecurityConfig = {
    securityJsCode: window.CAMPUS_AMAP_CONFIG.securityJsCode
  };

  var script = document.createElement("script");
  script.src = "https://webapi.amap.com/maps?v=2.0&key=" + window.CAMPUS_AMAP_CONFIG.key + "&plugin=AMap.PlaceSearch,AMap.Geocoder,AMap.ToolBar,AMap.Scale,AMap.ControlBar";
  script.onload = onAmapReady;
  script.onerror = function () {
    $("config-warning").innerHTML = "<p>⚠️ 高德 JS API 加载失败，请检查网络连接和 Key 配置。</p>";
    $("config-warning").classList.remove("hidden");
  };
  document.head.appendChild(script);
}

function onAmapReady() {
  $("app").classList.remove("hidden");
  state.map = new AMap.Map("map", {
    zoom: 17,
    center: [119.5566502, 25.8805227],
    viewMode: "3D",
    pitch: 55,
    rotation: -15,

    zooms: [3, 20],
    showBuildingBlock: true,
    isHotspot: true
  });

  state.map.addControl(new AMap.ToolBar({ position: "RT" }));
  state.map.addControl(new AMap.Scale());
  state.map.addControl(new AMap.ControlBar({ position: { top: "10px", left: "10px" } }));


  renderCampusList();
  loadVerifiedGates();
  loadCampus(0);
  state.map.on("hotspotclick", handleHotspotClick);
  state.map.on("click", handleMapClick);
  state.map.on("rightclick", handleMapRightClick);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && state.calibratingGate) {
      cancelGateCalibration();
    }
  });
  loadJoinedTripIds();
  refreshTrips();

  if (state.token && state.username) {
    hideGuestOverlay();
  } else {
    showGuestOverlay();
  }

  var lb = $("logout-btn");
  if (lb) {
    lb.addEventListener("click", function () { showGuestOverlay(); });
  }
}

function renderCampusList() {
  var list = $("campus-list");
  list.innerHTML = CAMPUSES.map(function (c, i) {
    return '<button class="campus-item' + (i === 0 ? " active" : "") + '" data-idx="' + i + '">' + c.shortName + "</button>";
  }).join("");
  list.querySelectorAll(".campus-item").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var idx = parseInt(btn.getAttribute("data-idx"));
      list.querySelectorAll(".campus-item").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      loadCampus(idx);
    });
  });
}

async function loadCampus(idx) {
  state.currentCampus = idx;
  clearMarkers();

  var campus = CAMPUSES[idx];
  var campusResult = await searchCampusPOI(campus);
  var gateResult = await searchGatePOI(campus, campusResult);

  state.campusData[idx] = { campusResult: campusResult, gateResult: gateResult };
  renderGateSelect();
  cacheCampusGates(idx);

  if (campusResult.best) {
    state.map.setZoomAndCenter(17, [campusResult.best.location.lng, campusResult.best.location.lat]);
    addMarker(campusResult.best.location, campus.shortName + "中心", "校区中心");
  }
  if (gateResult.best) {
    addMarker(gateResult.best.location, gateResult.best.name, "学校入口");
  }
}

function clearMarkers() {
  state.markers.forEach(function (m) { state.map.remove(m); });
  state.markers = [];
}

var SELECTED_MARKER_ICON = null;

function initSelectedMarkerIcon() {
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">'
    + '<path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 24 16 24s16-12 16-24c0-8.84-7.16-16-16-16z" fill="#3fb27f" stroke="#fff" stroke-width="2"/>'
    + '<circle cx="16" cy="16" r="5" fill="#fff"/>'
    + '</svg>';
  SELECTED_MARKER_ICON = new AMap.Icon({
    image: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    size: new AMap.Size(32, 40),
    imageSize: new AMap.Size(32, 40)
  });
}

function setSelectedMarker(poi) {
  try {
    if (state.selectedMarker) {
      state.map.remove(state.selectedMarker);
    }
    if (!SELECTED_MARKER_ICON) initSelectedMarkerIcon();
    var marker = new AMap.Marker({
      position: [poi.lng, poi.lat],
      icon: SELECTED_MARKER_ICON,
      anchor: "bottom-center",
      title: poi.name,
      zIndex: 120
    });
    state.map.add(marker);
    state.selectedMarker = marker;
  } catch (e) {
    console.error("[Phase 2A] setSelectedMarker 异常:", e);
  }
}

function clearSelectedMarker() {
  if (state.selectedMarker) {
    state.map.remove(state.selectedMarker);
    state.selectedMarker = null;
  }
  state.selectedPoi = null;
}

function showPoiActionCard(poi) {
  state.selectedPoi = poi;
  $("poi-card-name").textContent = poi.name;
  $("poi-card-address").textContent = poi.address || "—";
  $("poi-card-type").textContent = poi.type || "—";
  $("poi-action-card").classList.remove("hidden");
}

function hidePoiActionCard() {
  $("poi-action-card").classList.add("hidden");
  state.selectedPoi = null;
}

function showPoiNotFound() {
  var el = $("poi-notfound-text");
  if (el) el.textContent = NOT_FOUND_MESSAGE;
  $("poi-notfound").classList.remove("hidden");
}

function hidePoiNotFound() {
  $("poi-notfound").classList.add("hidden");
}

function openCreateTripModal() {
  if (!state.selectedPoi) return;
  if (!state.selectedGate) {
    alert("请先选择出发入口（右键地图设定出发点，或选择校区入口）");
    return;
  }
  var campus = CAMPUSES[state.currentCampus];
  $("cm-origin").textContent = campus.name + " · " + state.selectedGate.name;
  $("cm-dest").textContent = state.selectedPoi.name;
  var routeDist = calculateRouteDistance(
    { lng: state.selectedGate.lng, lat: state.selectedGate.lat },
    { lng: state.selectedPoi.lng, lat: state.selectedPoi.lat }
  );
  $("cm-distance").textContent = formatDistance(routeDist);
  $("cm-team-name").value = "";
  $("cm-depart").value = "";
  $("cm-seats").value = "3";
  $("cm-fee").value = "";
  $("cm-gender").value = "不限";
  $("cm-remark").value = "";
  setMsg("cm-msg", "");
  $("create-trip-modal").classList.remove("hidden");
}

async function submitCreateTrip() {
  if (!state.selectedPoi) return;
  var campus = CAMPUSES[state.currentCampus];
  var departAt = $("cm-depart").value;
  if (!departAt) { setMsg("cm-msg", "请选择出发时间", true); return; }
  var teamName = $("cm-team-name").value.trim();
  if (!teamName) { setMsg("cm-msg", "请输入队名", true); return; }

  var originGate = isCampusGate({ name: state.selectedGate.name });
  var destGate = isCampusGate(state.selectedPoi);
  if (!originGate.isGate && !destGate.isGate) {
    setMsg("cm-msg", "出发地和目的地至少一个必须是学校校门（北门/南门/东门/西门）", true);
    return;
  }

  var body = {
    origin: campus.name + " · " + state.selectedGate.name,
    destination: state.selectedPoi.name,
    teamName: teamName,
    departAt: departAt,
    seats: parseInt($("cm-seats").value) || 1,
    fee: $("cm-fee").value ? parseFloat($("cm-fee").value) : null,
    originLat: state.selectedGate.lat,
    originLng: state.selectedGate.lng,
    destinationLat: state.selectedPoi.lat,
    destinationLng: state.selectedPoi.lng,
    gender: $("cm-gender").value,
    remark: $("cm-remark").value || null
  };

  var data = await api("/api/trips", { method: "POST", body: body });
  if (data.code !== 0) { setMsg("cm-msg", data.message, true); return; }
  setMsg("cm-msg", "队伍创建成功！");
  $("create-trip-modal").classList.add("hidden");
  await refreshTrips();
}

function closeCreateTripModal() {
  $("create-trip-modal").classList.add("hidden");
}

function openJoinTripModal() {
  if (!state.selectedPoi) return;
  api("/api/trips?destination=" + encodeURIComponent(state.selectedPoi.name) + "&size=50").then(function (data) {
    if (data.code !== 0) { setMsg("jm-msg", data.message, true); return; }
    renderJoinTripList(data.data.items || []);
    $("join-trip-modal").classList.remove("hidden");
  });
}

function renderJoinTripList(trips) {
  var container = $("jm-info");
  if (trips.length === 0) {
    container.innerHTML = '<p class="empty-hint">该地点暂无队伍，点击「创建队伍」发起一个吧</p>';
    return;
  }
  container.innerHTML = "";
  trips.forEach(function (t) {
    var canJoin = t.status === "待出发" && t.currentSeats < t.maxSeats;
    var div = document.createElement("div");
    div.className = "join-trip-item";
    div.innerHTML =
      '<div class="jti-dest">' + t.destination + '</div>' +
      '<div class="jti-meta">从 ' + t.origin + ' · ' + t.departAt + ' · ' + t.currentSeats + '/' + t.maxSeats + '人 · ' + (t.gender || "不限") + '</div>' +
      (canJoin
        ? '<button class="btn-join" onclick="joinTripFromList(\'' + t.tripId + '\')">加入</button>'
        : '<span class="status-badge">' + t.status + '</span>');
    container.appendChild(div);
  });
}


function closeJoinTripModal() {
  $("join-trip-modal").classList.add("hidden");
  setMsg("jm-msg", "");
}

function addMarker(location, title, type) {
  var marker = new AMap.Marker({
    position: [location.lng, location.lat],
    title: title
  });
  marker.on("click", function () {
    new AMap.InfoWindow({
      content: "<div style='padding:8px;min-width:160px'><b>" + title + "</b><br/>类型：" + type + "<br/>坐标：" + location.lng.toFixed(6) + ", " + location.lat.toFixed(6) + "</div>",
      offset: new AMap.Pixel(0, -30)
    }).open(state.map, marker.getPosition());
  });
  state.map.add(marker);
  state.markers.push(marker);
}

async function searchCampusPOI(campus) {
  var pois = await searchPOI(campus.name, campus.city);
  var wgs84Converted = null;

  try {
    wgs84Converted = await convertWgs84ToAmap(campus.wgs84.lat, campus.wgs84.lng);
  } catch (e) {
    console.error("[searchCampusPOI] WGS84转换失败:", e);
  }

  var candidates = pois.map(function (p) {
    return {
      poiId: p.id,
      name: p.name,
      location: { lng: p.location.lng, lat: p.location.lat },
      address: p.address || "",
      district: p.adname || p.district || "",
      distance: wgs84Converted ? calcDistance(wgs84Converted, { lng: p.location.lng, lat: p.location.lat }) : null,
      source: "amap"
    };
  });

  var best = selectBestCandidate(candidates, campus.name, wgs84Converted);

  if (!best && wgs84Converted) {
    best = {
      poiId: null,
      name: campus.shortName + "中心（WGS84转换）",
      location: wgs84Converted,
      address: "",
      district: "",
      distance: 0,
      source: "wgs84_convert"
    };
  }

  return { candidates: candidates, best: best, wgs84Converted: wgs84Converted };
}

async function searchGatePOI(campus, campusResult) {
  var gateKeywords = ["北门", "南门", "东门", "西门", "校门", "学校入口"];

  var allResults = [];
  var campusCenter = campusResult.best ? campusResult.best.location : null;

  if (!campusCenter) {
    return { allResults: [], best: null, found: false };
  }

  for (var i = 0; i < gateKeywords.length; i++) {
    var keyword = gateKeywords[i];
    var pois = await searchPOIAround(keyword, campusCenter, 2000);
    var candidates = pois
      .filter(function (p) { return p.location && typeof p.location.lng === "number" && typeof p.location.lat === "number"; })
      .map(function (p) {
        return {
          poiId: p.id,
          name: p.name,
          location: { lng: p.location.lng, lat: p.location.lat },
          address: p.address || "",
          district: p.adname || p.district || "",
          distance: calcDistance(campusCenter, { lng: p.location.lng, lat: p.location.lat }),
          source: "amap",
          keyword: keyword
        };
      })
      .filter(function (c) { return c.distance <= 2000; });

    allResults.push({ keyword: keyword, candidates: candidates });

    if (candidates.length > 0) {
      var best = selectBestGateCandidate(candidates, keyword, campusCenter);
      if (best) {
        return { allResults: allResults, best: best, found: true, keyword: keyword };
      }
    }
  }

  return { allResults: allResults, best: null, found: false };
}

function selectBestCandidate(candidates, targetName, center) {
  if (candidates.length === 0) return null;

  var scored = candidates.map(function (c) {
    var score = 0;
    if (c.name === targetName) score += 100;
    else if (c.name.indexOf(targetName) >= 0) score += 50;
    if (c.district && (c.district.indexOf("长乐") >= 0 || c.district.indexOf("马尾") >= 0 || c.district.indexOf("仓山") >= 0)) score += 20;
    if (center && c.distance !== null) {
      if (c.distance < 1000) score += 30;
      else if (c.distance < 3000) score += 10;
      else if (c.distance > 10000) score -= 50;
    }
    if (c.address && c.address.indexOf("福州") >= 0) score += 5;
    return { candidate: c, score: score };
  });

  scored.sort(function (a, b) { return b.score - a.score; });
  return scored[0].candidate;
}

function selectBestGateCandidate(candidates, keyword, center) {
  if (candidates.length === 0) return null;

  var scored = candidates.map(function (c) {
    var score = 0;
    if (c.name === keyword) score += 100;
    else if (c.name.indexOf(keyword) >= 0) score += 60;
    if (c.name.indexOf("门") >= 0) score += 20;
    if (center && c.distance !== null) {
      if (c.distance < 300) score += 50;
      else if (c.distance < 800) score += 30;
      else if (c.distance < 1500) score += 10;
      else score -= 20;
    }
    return { candidate: c, score: score };
  });

  scored.sort(function (a, b) { return b.score - a.score; });
  if (scored[0].score > 0) return scored[0].candidate;
  return null;
}

function searchPOI(keyword, city) {
  return new Promise(function (resolve) {
    var placeSearch = new AMap.PlaceSearch({
      city: city,
      pageSize: 10,
      citylimit: false
    });
    placeSearch.search(keyword, function (status, result) {
      if (status === "complete" && result.info === "ok" && result.poiList) {
        resolve(result.poiList.pois);
      } else {
        resolve([]);
      }
    });
  });
}

function searchPOIAround(keyword, center, radius) {
  return new Promise(function (resolve) {
    var placeSearch = new AMap.PlaceSearch({
      pageSize: 20,
      around: true,
      center: [center.lng, center.lat],
      radius: radius
    });
    placeSearch.search(keyword, function (status, result) {
      if (status === "complete" && result.info === "ok" && result.poiList) {
        resolve(result.poiList.pois);
      } else {
        resolve([]);
      }
    });
  });
}

async function findNearestAmapPoiWithFallback(lnglat) {
  var lng = typeof lnglat.lng === "number" ? lnglat.lng : (lnglat.getLng ? lnglat.getLng() : null);
  var lat = typeof lnglat.lat === "number" ? lnglat.lat : (lnglat.getLat ? lnglat.getLat() : null);
  if (lng === null || lat === null) return null;

  var center = { lng: lng, lat: lat };

  for (var i = 0; i < SEARCH_RADIUS_LEVELS.length; i++) {
    var radius = SEARCH_RADIUS_LEVELS[i];
    console.log("[Phase 2A] 搜索半径:", radius + "m");
    var result = await searchByRadiusLevel(center, radius);
    if (result) return result;
  }

  return null;
}

async function searchByRadiusLevel(lnglat, radius) {
  try {
    var pois = await searchPOIAround("", lnglat, radius);
    var result = selectNearestValidPoi(pois, lnglat, radius);
    if (result) return result;

    var typedPois = await searchByPoiKeywords(lnglat, radius);
    return selectNearestValidPoi(typedPois, lnglat, radius);
  } catch (e) {
    console.warn("[Phase 2A] searchByRadiusLevel 异常:", e);
    return null;
  }
}

async function searchByPoiKeywords(lnglat, radius) {
  var all = [];
  for (var i = 0; i < POI_KEYWORD_LIST.length; i++) {
    try {
      var pois = await searchPOIAround(POI_KEYWORD_LIST[i], lnglat, radius);
      all = all.concat(pois);
    } catch (e) {
      console.warn("[Phase 2A] 关键词搜索异常:", POI_KEYWORD_LIST[i], e);
    }
  }
  return all;
}

function selectNearestValidPoi(pois, lnglat, radius) {
  if (!pois || !Array.isArray(pois)) return null;
  var valid = pois.filter(function (p) {
    if (!p || !p.location) return false;
    if (typeof p.location.lng !== "number" || typeof p.location.lat !== "number") return false;
    if (!p.name || !String(p.name).trim()) return false;
    if (!p.id) return false;
    return true;
  });
  if (valid.length === 0) return null;

  var scored = valid.map(function (p) {
    return {
      poi: p,
      distance: calcDistance(lnglat, { lng: p.location.lng, lat: p.location.lat })
    };
  });
  scored.sort(function (a, b) { return a.distance - b.distance; });

  if (scored[0].distance > radius) return null;

  var p = scored[0].poi;
  return {
    id: p.id,
    name: p.name,
    lng: p.location.lng,
    lat: p.location.lat,
    address: p.address || "",
    type: p.type || "",
    distance: scored[0].distance
  };
}

async function cacheCampusGates(campusIdx) {
  var campus = CAMPUSES[campusIdx];
  var shortName = campus.shortName;
  var gateNames = CAMPUS_GATE_NAMES[shortName];
  if (!state.campusGates[shortName]) state.campusGates[shortName] = {};

  for (var i = 0; i < gateNames.length; i++) {
    var gateName = gateNames[i];
    if (state.campusGates[shortName][gateName] && state.campusGates[shortName][gateName].verified) {
      console.log("[cacheCampusGates] 已确认校门跳过搜索:", shortName, gateName);
      continue;
    }
    var cd = state.campusData[campusIdx];
    var center = cd && cd.campusResult && cd.campusResult.best ? cd.campusResult.best.location : null;
    if (!center) {
      try { center = await convertWgs84ToAmap(campus.wgs84.lat, campus.wgs84.lng); }
      catch (e) { console.error("[cacheCampusGates] 无法获取校区中心:", e); continue; }
    }
    try {
      var pois = await searchPOIAround(gateName, center, 1500);
      var candidates = pois
        .filter(function (p) { return p.location && typeof p.location.lng === "number" && typeof p.location.lat === "number"; })
        .map(function (p) {
          return {
            poiId: p.id, name: p.name,
            location: { lng: p.location.lng, lat: p.location.lat },
            address: p.address || "",
            distance: calcDistance(center, { lng: p.location.lng, lat: p.location.lat }),
          };
        });
      var best = selectBestGateCandidate(candidates, gateName, center);
      if (best) {
        state.campusGates[shortName][gateName] = {
          name: best.name, poiId: best.poiId,
          lng: best.location.lng, lat: best.location.lat,
          address: best.address || "", campus: shortName, gateType: gateName,
          verified: false
        };
        console.log("[cacheCampusGates] 自动搜索校门:", shortName, gateName, "->", best.name);
      } else {
        console.warn("[cacheCampusGates] 未找到校门:", shortName, gateName, "（请使用校门校准功能）");
      }
    } catch (e) {
      console.error("[cacheCampusGates] 搜索校门异常:", shortName, gateName, e);
    }
  }
}

async function resolveMapPoi(lnglat) {
  var lng = typeof lnglat.lng === "number" ? lnglat.lng : (lnglat.getLng ? lnglat.getLng() : null);
  var lat = typeof lnglat.lat === "number" ? lnglat.lat : (lnglat.getLat ? lnglat.getLat() : null);
  if (lng === null || lat === null) return null;
  var clickPoint = { lng: lng, lat: lat };

  var nearestGate = null;
  var nearestGateDist = 120;
  for (var shortName in state.campusGates) {
    var gates = state.campusGates[shortName];
    for (var gateName in gates) {
      var gate = gates[gateName];
      if (!gate.verified) continue;
      var dist = calcDistance(clickPoint, { lng: gate.lng, lat: gate.lat });
      if (dist <= nearestGateDist) {
        nearestGateDist = dist;
        nearestGate = {
          id: gate.poiId, name: gate.name,
          lng: gate.lng, lat: gate.lat,
          address: gate.address, type: "学校校门",
          distance: dist, isCampusGate: true,
          campus: shortName, gateType: gateName
        };
      }
    }
  }
  if (nearestGate) {
    console.log("[resolveMapPoi] 匹配缓存校门:", nearestGate.name, "距离:", Math.round(nearestGate.distance) + "m");
    return nearestGate;
  }

  var geocodeResult = await reverseGeocode(clickPoint);
  if (geocodeResult) {
    console.log("[resolveMapPoi] Geocoder 识别:", geocodeResult.name, "source:", geocodeResult.source);
    return geocodeResult;
  }

  var poiResult = await findNearestAmapPoiWithFallback(lnglat);
  if (poiResult) {
    console.log("[resolveMapPoi] PlaceSearch 识别:", poiResult.name);
    return poiResult;
  }

  console.warn("[resolveMapPoi] 全部策略失败");
  return null;
}

function reverseGeocode(point) {
  return new Promise(function (resolve) {
    try {
      var geocoder = new AMap.Geocoder({ radius: 500, extensions: "all" });
      geocoder.getAddress([point.lng, point.lat], function (status, result) {
        if (status !== "complete" || !result || !result.regeocode) {
          resolve(null);
          return;
        }
        var rg = result.regeocode;
        var pois = rg.pois || [];
        var best = null;
        var bestDist = Infinity;
        for (var i = 0; i < pois.length; i++) {
          var p = pois[i];
          if (!p.name || !p.location) continue;
          var pLng = typeof p.location.lng === "number" ? p.location.lng : (p.location.getLng ? p.location.getLng() : null);
          var pLat = typeof p.location.lat === "number" ? p.location.lat : (p.location.getLat ? p.location.getLat() : null);
          if (pLng === null || pLat === null) continue;
          var d = calcDistance(point, { lng: pLng, lat: pLat });
          if (d < bestDist) {
            bestDist = d;
            best = {
              id: p.id || ("geo_" + i),
              name: p.name,
              lng: pLng,
              lat: pLat,
              address: p.address || "",
              type: p.type || "",
              distance: d,
              source: "amap-regeocode"
            };
          }
        }
        if (best && bestDist <= MAX_POI_SNAP_DISTANCE) {
          resolve(best);
          return;
        }
        var addr = rg.formattedAddress || "";
        if (addr) {
          resolve({
            id: "geo_addr",
            name: "地图选点",
            lng: point.lng,
            lat: point.lat,
            address: addr,
            type: best ? "附近：" + best.name + "（" + Math.round(bestDist) + "m）" : "地图位置",
            distance: 0,
            source: "amap-click-address"
          });
          return;
        }
        resolve(null);
      });
    } catch (e) {
      console.warn("[reverseGeocode] 异常:", e);
      resolve(null);
    }
  });
}

async function handleHotspotClick(event) {
  if (state.calibratingGate) return;
  state.lastHotspotClickAt = Date.now();
  if (state.isSearching) return;
  state.isSearching = true;
  hidePoiNotFound();
  hidePoiConfirmCard();
  hidePoiActionCard();

  try {
    var lng = event.lnglat ? (event.lnglat.lng || event.lnglat.getLng()) : null;
    var lat = event.lnglat ? (event.lnglat.lat || event.lnglat.getLat()) : null;
    var name = event.name || "高德地点";
    var poiId = event.id || null;
    console.log("[hotspotclick] id:", poiId, "name:", name, "lng:", lng, "lat:", lat);

    var poi = {
      id: poiId || ("hotspot_" + Date.now()),
      name: name,
      lng: lng,
      lat: lat,
      address: "",
      type: "",
      distance: 0,
      source: "amap-hotspot"
    };

    if (poiId && typeof AMap.PlaceSearch !== "undefined") {
      try {
        var details = await getPlaceDetails(poiId);
        if (details) {
          poi.name = details.name || name;
          poi.address = details.address || "";
          poi.type = details.type || "";
          if (details.location) {
            poi.lng = details.location.lng;
            poi.lat = details.location.lat;
          }
        }
      } catch (e) {
        console.warn("[hotspotclick] getDetails 失败:", e);
      }
    }

    clearSelectedMarker();
    setSelectedMarker(poi);
    state.lastDistance = 0;
    showPoiConfirmCard(poi, 0);
  } catch (e) {
    console.error("[hotspotclick] 异常:", e);
  } finally {
    state.isSearching = false;
  }
}

function getPlaceDetails(poiId) {
  return new Promise(function (resolve) {
    try {
      var ps = new AMap.PlaceSearch({});
      ps.getDetails(poiId, function (status, result) {
        if (status === "complete" && result && result.poiList && result.poiList.pois && result.poiList.pois.length > 0) {
          resolve(result.poiList.pois[0]);
        } else {
          resolve(null);
        }
      });
    } catch (e) {
      resolve(null);
    }
  });
}

async function handleMapClick(event) {
  if (state.calibratingGate) {
    var lng = event.lnglat.lng;
    var lat = event.lnglat.lat;
    var campus = CAMPUSES[state.currentCampus];
    var gateName = state.calibratingGate;
    $("gc-confirm-campus").textContent = campus.name;
    $("gc-confirm-gate").textContent = gateName;
    $("gc-confirm-lng").textContent = lng.toFixed(6);
    $("gc-confirm-lat").textContent = lat.toFixed(6);
    $("gc-confirm-dialog").classList.remove("hidden");
    return;
  }
  if (Date.now() - state.lastHotspotClickAt < 500) {
    console.log("[click] 热点点击已处理，跳过普通 click");
    return;
  }
  if (state.isSearching) {
    console.warn("[Phase 2A] 搜索进行中，忽略重复点击");
    return;
  }
  state.isSearching = true;
  hidePoiNotFound();
  hidePoiConfirmCard();
  hidePoiActionCard();

  var lnglat = event.lnglat;
  console.log("[Phase 2A] 点击坐标:", lnglat.lng, lnglat.lat);

  try {
    var poi = await resolveMapPoi(lnglat);
    if (poi) {
      console.log("[Phase 2A] 选中 POI:", poi);
      clearSelectedMarker();
      setSelectedMarker(poi);
      state.lastDistance = poi.distance || 0;
      showPoiConfirmCard(poi, state.lastDistance);
    } else {
      console.warn("[Phase 2A] 未找到 POI");
      clearSelectedMarker();
      showPoiNotFound();
    }
  } catch (e) {
    console.error("[Phase 2A] handleMapClick 异常:", e);
    clearSelectedMarker();
    showPoiNotFound();
  } finally {
    state.isSearching = false;
  }
}

function formatDistance(meters) {
  if (!meters || meters <= 0) return "—";
  if (meters < 1000) return "约 " + Math.round(meters) + " 米";
  return "约 " + (meters / 1000).toFixed(1) + " 公里";
}

function calculateRouteDistance(origin, destination) {
  if (!origin || !destination) return 0;
  var oLng = Number(origin.lng), oLat = Number(origin.lat);
  var dLng = Number(destination.lng), dLat = Number(destination.lat);
  if (!Number.isFinite(oLng) || !Number.isFinite(oLat)) return 0;
  if (!Number.isFinite(dLng) || !Number.isFinite(dLat)) return 0;
  if (typeof AMap !== "undefined" && AMap.GeometryUtil && AMap.GeometryUtil.distance) {
    return AMap.GeometryUtil.distance([oLng, oLat], [dLng, dLat]);
  }
  return calcDistance({ lng: oLng, lat: oLat }, { lng: dLng, lat: dLat });
}

function showPoiConfirmCard(poi, distance) {
  state.selectedPoi = poi;
  state.lastDistance = distance || 0;
  $("poi-confirm-name").textContent = poi.name;
  $("poi-confirm-address").textContent = poi.address || "—";
  $("poi-confirm-type").textContent = poi.type || "—";
  var sourceLabel = "高德地图";
  if (poi.source === "amap-hotspot") sourceLabel = "高德原生地点";
  else if (poi.source === "amap-click-address") sourceLabel = "地图点击位置";
  else if (poi.source === "amap-regeocode") sourceLabel = "高德逆地理编码";
  $("poi-confirm-source").textContent = sourceLabel;
  $("poi-confirm-card").classList.remove("hidden");
}

function hidePoiConfirmCard() {
  var el = $("poi-confirm-card");
  if (el) el.classList.add("hidden");
}

function confirmPoiSelection() {
  hidePoiConfirmCard();
  showPoiActionCard(state.selectedPoi);
}

function reselectPoi() {
  hidePoiConfirmCard();
  clearSelectedMarker();
}

function convertWgs84ToAmap(lat, lng) {
  return new Promise(function (resolve, reject) {
    AMap.convertFrom([lng, lat], "gps", function (status, result) {
      if (status === "complete" && result.info === "ok") {
        var gcj02 = result.locations[0];
        resolve({ lng: gcj02.lng, lat: gcj02.lat });
      } else {
        reject(new Error("WGS84→GCJ02转换失败"));
      }
    });
  });
}

function calcDistance(p1, p2) {
  var R = 6371000;
  var dLat = (p2.lat - p1.lat) * Math.PI / 180;
  var dLng = (p2.lng - p1.lng) * Math.PI / 180;
  var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function isCampusGate(poi) {
  if (!poi || !poi.name) return { isGate: false, campus: null, gateName: null };
  if (poi.isCampusGate) {
    return { isGate: true, campus: poi.campus, gateName: poi.gateType };
  }
  var name = poi.name;
  for (var shortName in CAMPUS_GATE_NAMES) {
    var gates = CAMPUS_GATE_NAMES[shortName];
    for (var i = 0; i < gates.length; i++) {
      if (name.indexOf(gates[i]) >= 0) {
        return { isGate: true, campus: shortName, gateName: gates[i] };
      }
    }
  }
  return { isGate: false, campus: null, gateName: null };
}

async function handleMapRightClick(event) {
  if (state.isSearching) return;
  state.isSearching = true;
  try {
    var poi = await resolveMapPoi(event.lnglat);
    if (poi) {
      clearOriginMarker();
      setOriginMarker(poi);
      state.selectedGate = { name: poi.name, lat: poi.lat, lng: poi.lng };
      if (poi.isCampusGate) {
        state.selectedGate.isCampusGate = true;
        state.selectedGate.campus = poi.campus;
        state.selectedGate.gateType = poi.gateType;
      }
      var gateSel = $("gate-select");
      if (gateSel) gateSel.innerHTML = '<option value="0">' + poi.name + '（右键设定）</option>';
      console.log("[handleMapRightClick] 出发点已设定:", poi.name);
    } else {
      alert("该位置未识别到明确地点，请换个位置右键");
    }
  } catch (e) {
    console.error("[handleMapRightClick] 异常:", e);
  } finally {
    state.isSearching = false;
  }
}

var ORIGIN_MARKER_ICON = null;

function initOriginMarkerIcon() {
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">'
    + '<path d="M16 0C7.16 0 0 7.16 0 16c0 12 16 24 16 24s16-12 16-24c0-8.84-7.16-16-16-16z" fill="#f59e0b" stroke="#fff" stroke-width="2"/>'
    + '<circle cx="16" cy="16" r="5" fill="#fff"/>'
    + '</svg>';
  ORIGIN_MARKER_ICON = new AMap.Icon({
    image: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    size: new AMap.Size(32, 40),
    imageSize: new AMap.Size(32, 40)
  });
}

function setOriginMarker(poi) {
  try {
    if (!ORIGIN_MARKER_ICON) initOriginMarkerIcon();
    var marker = new AMap.Marker({
      position: [poi.lng, poi.lat],
      icon: ORIGIN_MARKER_ICON,
      anchor: "bottom-center",
      title: "出发点：" + poi.name,
      zIndex: 130
    });
    state.map.add(marker);
    state.originMarker = marker;
  } catch (e) {
    console.error("[setOriginMarker] 异常:", e);
  }
}

function clearOriginMarker() {
  if (state.originMarker) {
    state.map.remove(state.originMarker);
    state.originMarker = null;
  }
}

async function loadTripMembers(tripId, isLeader) {
  var container = $("jm-members");
  if (!container) return;
  container.innerHTML = '<p class="member-loading">加载成员中...</p>';
  var data = await api("/api/trips/" + tripId + "/members");
  if (data.code !== 0 || !data.data) {
    container.innerHTML = '<p class="member-empty">暂无成员信息</p>';
    return;
  }
  var members = data.data.members || [];
  var leader = data.data.leader || "";
  if (members.length === 0) {
    container.innerHTML = '<p class="member-empty">暂无成员</p>';
    return;
  }
  var html = '<div class="member-list-title">队伍成员（' + members.length + '人）</div>';
  members.forEach(function (m) {
    var leaderTag = m.username === leader ? '<span class="member-leader-tag">队长</span>' : '';
    var kickBtn = (isLeader && m.username !== leader)
      ? '<button class="btn-kick" onclick="kickMember(\'' + tripId + '\', \'' + m.username + '\')">踢出</button>'
      : '';
    html +=
      '<div class="member-item">' +
      '<span class="member-name">' + m.username + '</span>' +
      '<span class="member-gender">' + (m.gender || "保密") + '</span>' +
      leaderTag + kickBtn +
      '</div>';
  });
  container.innerHTML = html;
}

async function kickMember(tripId, username) {
  if (!confirm("确定踢出成员 " + username + "？")) return;
  var data = await api("/api/trips/" + tripId + "/kick", { method: "POST", body: { username: username } });
  if (data.code !== 0) { setMsg("jm-msg", data.message, true); return; }
  setMsg("jm-msg", "已踢出 " + username);
  await refreshTrips();
  var updated = state.trips.find(function (t) { return t.tripId === tripId; });
  if (updated) showTripDetail(updated);
}

async function dissolveTrip(tripId) {
  if (!confirm("确定解散这支队伍？此操作不可撤销。")) return;
  var data = await api("/api/trips/" + tripId + "/dissolve", { method: "POST" });
  if (data.code !== 0) { setMsg("jm-msg", data.message, true); return; }
  setMsg("jm-msg", "队伍已解散");
  $("join-trip-modal").classList.add("hidden");
  await refreshTrips();
}

function openEditTripModal(tripId) {
  var trip = state.trips.find(function (t) { return t.tripId === tripId; });
  if (!trip) return;
  state.editingTripId = tripId;
  $("em-team-name").value = trip.teamName || "";
  $("em-depart").value = trip.departAt || "";
  $("em-seats").value = trip.maxSeats || 3;
  $("em-gender").value = trip.gender || "不限";
  $("em-remark").value = trip.remark || "";
  setMsg("em-msg", "");
  $("edit-trip-modal").classList.remove("hidden");
}

function closeEditTripModal() {
  $("edit-trip-modal").classList.add("hidden");
  state.editingTripId = null;
}

async function submitEditTrip() {
  if (!state.editingTripId) return;
  var tripId = state.editingTripId;
  var teamName = $("em-team-name").value.trim();
  if (!teamName) { setMsg("em-msg", "请输入队名", true); return; }
  var body = {
    teamName: teamName,
    departAt: $("em-depart").value,
    maxSeats: parseInt($("em-seats").value) || 1,
    gender: $("em-gender").value,
    remark: $("em-remark").value || null
  };
  var data = await api("/api/trips/" + tripId + "/edit", { method: "POST", body: body });
  if (data.code !== 0) { setMsg("em-msg", data.message, true); return; }
  setMsg("em-msg", "保存成功");
  closeEditTripModal();
  await refreshTrips();
  var updated = state.trips.find(function (t) { return t.tripId === tripId; });
  if (updated) showTripDetail(updated);
}

async function loadVerifiedGates() {
  try {
    var data = await api("/api/campus-gates");
    if (data.code === 0 && data.data) {
      for (var shortName in data.data) {
        if (!state.campusGates[shortName]) state.campusGates[shortName] = {};
        var gates = data.data[shortName];
        for (var gateName in gates) {
          var g = gates[gateName];
          if (g.verified) {
            state.campusGates[shortName][gateName] = {
              name: gateName, poiId: null,
              lng: g.lng, lat: g.lat,
              address: g.source || "manual_verified",
              campus: shortName, gateType: gateName,
              verified: true
            };
            console.log("[loadVerifiedGates] 已加载确认校门:", shortName, gateName);
          }
        }
      }
    }
  } catch (e) {
    console.warn("[loadVerifiedGates]", e);
  }
}

function openGateCalibrator() {
  var campus = CAMPUSES[state.currentCampus];
  $("gc-campus-name").textContent = campus.shortName;
  var gateNames = CAMPUS_GATE_NAMES[campus.shortName] || [];
  var btnContainer = $("gc-gate-buttons");
  btnContainer.innerHTML = "";
  gateNames.forEach(function (gn) {
    var btn = document.createElement("button");
    btn.className = "gc-gate-btn";
    btn.textContent = gn;
    var cached = state.campusGates[campus.shortName] && state.campusGates[campus.shortName][gn];
    if (cached && cached.verified) {
      btn.classList.add("verified");
      btn.textContent = gn + " ✓";
    }
    btn.addEventListener("click", function () {
      startGateCalibration(gn);
    });
    btnContainer.appendChild(btn);
  });
  updateGateCalibratorStatus();
  $("gate-calibrator").classList.remove("hidden");
}

function closeGateCalibrator() {
  $("gate-calibrator").classList.add("hidden");
  state.calibratingGate = null;
}

function startGateCalibration(gateName) {
  var campus = CAMPUSES[state.currentCampus];
  state.calibratingGate = gateName;
  $("gate-calibrator").classList.add("hidden");
  $("gc-fb-campus").textContent = campus.shortName;
  $("gc-fb-gate").textContent = gateName;
  $("gc-floating-bar").classList.remove("hidden");
  $("map").classList.add("calibrating");
  console.log("[startGateCalibration] 等待点击地图确认:", campus.shortName, gateName);
}

function cancelGateCalibration() {
  state.calibratingGate = null;
  $("gc-floating-bar").classList.add("hidden");
  $("gc-confirm-dialog").classList.add("hidden");
  $("map").classList.remove("calibrating");
}

function confirmGateSave() {
  var campus = CAMPUSES[state.currentCampus];
  var gateName = state.calibratingGate;
  var lng = parseFloat($("gc-confirm-lng").textContent);
  var lat = parseFloat($("gc-confirm-lat").textContent);
  $("gc-confirm-dialog").classList.add("hidden");
  saveVerifiedGate(campus.shortName, gateName, lng, lat).then(function () {
    cancelGateCalibration();
  });
}

function cancelGateConfirm() {
  $("gc-confirm-dialog").classList.add("hidden");
}

function updateGateCalibratorStatus() {
  var campus = CAMPUSES[state.currentCampus];
  var shortName = campus.shortName;
  var gateNames = CAMPUS_GATE_NAMES[shortName] || [];
  var html = "";
  gateNames.forEach(function (gn) {
    var g = state.campusGates[shortName] && state.campusGates[shortName][gn];
    if (g && g.verified) {
      html += gn + ': <span class="gc-verified-tag">已确认</span> (' + g.lng.toFixed(6) + ", " + g.lat.toFixed(6) + ")<br>";
    } else {
      html += gn + ': <span style="color:#999">未确认</span><br>';
    }
  });
  $("gc-status").innerHTML = html;
  $("gc-instruction").textContent = state.calibratingGate
    ? "请在高德地图上点击真实的「" + state.calibratingGate + "」位置"
    : "请选择要确认的校门：";
}

async function saveVerifiedGate(campusShortName, gateName, lng, lat) {
  var data = await api("/api/campus-gates", {
    method: "POST",
    body: { campus: campusShortName, gateName: gateName, lng: lng, lat: lat }
  });
  if (data.code !== 0) {
    alert("保存失败: " + data.message);
    return;
  }
  if (!state.campusGates[campusShortName]) state.campusGates[campusShortName] = {};
  state.campusGates[campusShortName][gateName] = {
    name: gateName, poiId: null,
    lng: lng, lat: lat,
    address: "manual_verified_amap",
    campus: campusShortName, gateType: gateName,
    verified: true
  };
  console.log("[saveVerifiedGate] 校门已确认:", campusShortName, gateName, lng, lat);

  renderGateSelect();
  updateGateCalibratorStatus();
  var btns = document.querySelectorAll(".gc-gate-btn");
  btns.forEach(function (b) {
    b.classList.remove("calibrating");
    if (b.textContent.indexOf(gateName) >= 0) {
      b.classList.add("verified");
      b.textContent = gateName + " ✓";
    }
  });
}


initApp();