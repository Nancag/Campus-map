/* Campus map · 地图页交互逻辑 */
const SESSION_VERSION = "2";

function normalizeGender(g) {
  if (!g || g === "null" || g === "undefined" || g === "") return "保密";
  const m = { "female": "女", "f": "女", "女": "女", "male": "男", "m": "男", "男": "男", "private": "保密", "保密": "保密" };
  return m[String(g).toLowerCase()] || "保密";
}

const state = {
  token: localStorage.getItem("cmp_token") || null,
  username: localStorage.getItem("cmp_username") || null,
  gender: normalizeGender(localStorage.getItem("cmp_gender")),
  campuses: [],
  pois: [],
  trips: [],
  selectedCampus: 0,
  selectedGate: null,
  map: null,
  campusLayers: [],
  poiLayers: [],
  rangeCircles: [],
  joinedTripIds: new Set(),
};

const $ = (id) => document.getElementById(id);

/* ---- API 封装 ---- */
async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  if (opts.body) headers["Content-Type"] = "application/json";
  const res = await fetch(path, {
    ...opts,
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({ code: 9001, message: "响应解析失败" }));
  if (res.status === 401 || data.code === 9001) {
    showGuestOverlay();
  }
  return data;
}

function setMsg(id, text, isErr) {
  const el = $(id);
  el.textContent = text || "";
  el.className = "msg" + (isErr ? " err" : "");
}

function showGuestOverlay() {
  state.token = null;
  state.username = null;
  state.gender = "保密";
  localStorage.removeItem("cmp_token");
  localStorage.removeItem("cmp_username");
  localStorage.removeItem("cmp_gender");
  $("guest-overlay").classList.remove("hidden");
  $("user-badge").classList.add("hidden");
  $("logout-btn").classList.add("hidden");
}

function hideGuestOverlay() {
  $("guest-overlay").classList.add("hidden");
  $("user-badge").classList.remove("hidden");
  $("logout-btn").classList.remove("hidden");
  $("user-badge").textContent = state.username + " · " + normalizeGender(state.gender);
}

/* ---- 游客进入 ---- */
let pickedGender = "保密";
document.querySelectorAll(".gender-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".gender-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    pickedGender = btn.dataset.gender;
  });
});

$("enter-btn").addEventListener("click", async () => {
  const username = $("nickname-input").value.trim();
  if (!username) return setMsg("guest-msg", "请输入昵称", true);
  const data = await api("/api/guest/enter", {
    method: "POST",
    body: { username, gender: pickedGender },
  });
  if (data.code !== 0) return setMsg("guest-msg", data.message, true);
  state.token = data.data.token;
  state.username = data.data.username;
  state.gender = normalizeGender(data.data.gender);
  localStorage.setItem("cmp_token", state.token);
  localStorage.setItem("cmp_username", state.username);
  localStorage.setItem("cmp_gender", state.gender);
  localStorage.setItem("cmp_session_version", SESSION_VERSION);
  hideGuestOverlay();
  await initMap();
});

/* ---- 底图图层切换 ---- */
function initBaseLayerControl() {
  const osmLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 19,
    detectRetina: false,
  }).addTo(state.map);

  const satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
      maxZoom: 19,
    }
  );

  L.control.layers(
    { "OSM 街道": osmLayer, "ESRI 卫星": satelliteLayer },
    null,
    { position: "topright" }
  ).addTo(state.map);

  return { osmLayer, satelliteLayer };
}

/* ---- 地图初始化 ---- */
async function initMap() {
  try {
    const campusData = await api("/api/campuses");
    if (campusData.code !== 0) {
      $("campus-list").innerHTML = `<p class="empty-hint">校区数据加载失败：${campusData.message || "未知错误"}</p>`;
      return;
    }
    state.campuses = campusData.data.items;

    renderCampusList();
    renderGateSelect();
    renderMap();

    const poiData = await api("/api/pois");
    if (poiData.code !== 0) {
      $("trip-list").innerHTML = `<p class="empty-hint">地点数据加载失败：${poiData.message || "未知错误"}</p>`;
    } else {
      state.pois = poiData.data.items;
      renderMap();
    }

    await refreshTrips();
  } catch (e) {
    $("campus-list").innerHTML = `<p class="empty-hint">初始化异常：${e.message}</p>`;
  }
}

function renderCampusList() {
  const container = $("campus-list");
  container.innerHTML = "";
  state.campuses.forEach((c, i) => {
    const div = document.createElement("div");
    div.className = "campus-item" + (i === state.selectedCampus ? " active" : "");
    div.innerHTML = `<span class="campus-dot"></span><span>${c.name}</span>`;
    div.addEventListener("click", () => {
      state.selectedCampus = i;
      renderCampusList();
      renderGateSelect();
      flyToCampus(i);
    });
    container.appendChild(div);
  });
}

function renderGateSelect() {
  const sel = $("gate-select");
  const campus = state.campuses[state.selectedCampus];
  if (!campus || !campus.gates) return;
  sel.innerHTML = "";
  campus.gates.forEach((g, i) => {
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = g.name;
    sel.appendChild(opt);
  });
  state.selectedGate = campus.gates[0] || null;
  sel.addEventListener("change", () => {
    state.selectedGate = campus.gates[parseInt(sel.value)] || null;
  });
}

function renderMap() {
  try {
    if (typeof L === "undefined") {
      throw new Error("Leaflet 库未加载");
    }
    if (state.map) {
      state.map.remove();
      state.campusLayers = [];
      state.poiLayers = [];
      state.rangeCircles = [];
    }

    const first = state.campuses[0];
    state.map = L.map("map").setView([first.centerLat, first.centerLng], 15);

    const { osmLayer } = initBaseLayerControl();

    let tileFailCount = 0;
    osmLayer.on("tileerror", (e) => {
      tileFailCount++;
      if (tileFailCount <= 5) {
        const url = e.tile && e.tile.src ? e.tile.src : "(unknown)";
        console.warn("[tileerror #" + tileFailCount + "] " + url);
      }
      if (tileFailCount === 5) {
        console.warn("[tileerror] 已累计 5 次失败，后续仅计数不再输出 URL");
      }
    });

    state.campuses.forEach((c, i) => {
      const color = i === 0 ? "#3f9de0" : "#3fb27f";
      const marker = L.circleMarker([c.centerLat, c.centerLng], {
        radius: 10,
        fillColor: color,
        color: "#fff",
        weight: 3,
        fillOpacity: 0.9,
      }).addTo(state.map);
      marker.bindPopup(`<div class="popup-title">${c.name}</div>`);
      state.campusLayers.push(marker);

      const circle = L.circle([c.centerLat, c.centerLng], {
        radius: c.radiusKm * 1000,
        color: color,
        weight: 1,
        opacity: 0.15,
        fillColor: color,
        fillOpacity: 0.02,
        dashArray: "6 8",
      }).addTo(state.map);
      state.rangeCircles.push(circle);
    });

    fetch("/api/campus-boundaries")
      .then((r) => r.json())
      .then((data) => {
        const boundaries = data.boundaries || [];
        boundaries.forEach((b) => {
          const isBinhai = b.campus_id === "binhai";
          const polyColor = isBinhai ? "#3f9de0" : "#3fb27f";
          const latlngs = b.geometry.map((pt) => [pt[0], pt[1]]);
          L.polygon(latlngs, {
            color: polyColor,
            weight: 2,
            opacity: 0.8,
            fillColor: polyColor,
            fillOpacity: 0.15,
          }).addTo(state.map);
        });
      })
      .catch((e) => console.warn("campus-boundaries load failed:", e));

    state.pois.forEach((p) => {
      const iconHtml = poiIconHtml(p.type);
      const icon = L.divIcon({
        html: iconHtml,
        className: "poi-marker",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
      const marker = L.marker([p.lat, p.lng], { icon }).addTo(state.map);
      marker.bindPopup(buildPoiPopup(p), { maxWidth: 260 });
      state.poiLayers.push(marker);
    });
    setTimeout(() => { if (state.map) state.map.invalidateSize(); }, 100);
  } catch (e) {
    const mapEl = $("map");
    mapEl.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;flex-direction:column;gap:8px;color:#5d7684;font-size:15px;text-align:center;"><span>地图加载失败：${e.message}</span><span>请刷新页面重试</span></div>`;
  }
}

function poiIconHtml(type) {
  const icons = {
    "公园": { l: "#5fcc8e", d: "#3a9d5e", s: '<path d="M12 2 L6 12 L10 12 L10 22 L14 22 L14 12 L18 12 Z"/>' },
    "商场": { l: "#ffb84d", d: "#e89213", s: '<path d="M5 8 L19 8 L18 22 L6 22 Z" fill="none" stroke="white" stroke-width="2"/><path d="M9 8 V6 a3 3 0 0 1 6 0 V8" fill="none" stroke="white" stroke-width="2"/>' },
    "店铺": { l: "#5db4f0", d: "#2480c8", s: '<path d="M4 9 L4 20 L20 20 L20 9 Z M4 9 L6 4 L18 4 L20 9 Z M10 20 V14 H14 V20"/>' },
    "医院": { l: "#ff6b6b", d: "#e23838", s: '<rect x="10" y="4" width="4" height="16" rx="1"/><rect x="4" y="10" width="16" height="4" rx="1"/>' },
    "学校": { l: "#b88df0", d: "#8a52d4", s: '<path d="M12 3 L22 8 L12 13 L2 8 Z"/><path d="M6 11 V17 Q12 19 18 17 V11"/>' },
    "公共交通": { l: "#ffd93d", d: "#e0b020", s: '<rect x="4" y="5" width="16" height="14" rx="2"/><rect x="6" y="7" width="12" height="5" rx="1" fill="rgba(0,0,0,.3)"/><circle cx="8" cy="18" r="2"/><circle cx="16" cy="18" r="2"/>' },
    "生活服务": { l: "#4ee0c4", d: "#1a9d80", s: '<path d="M12 2 L14 8 L20 8 L15 12 L17 18 L12 14 L7 18 L9 12 L4 8 L10 8 Z"/>' },
  };
  const cfg = icons[type] || icons["生活服务"];
  return `<div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(145deg,${cfg.l},${cfg.d});box-shadow:0 3px 6px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;"><svg width="18" height="18" viewBox="0 0 24 24" fill="white">${cfg.s}</svg></div>`;
}

function buildPoiPopup(p) {
  return `
    <div class="popup-title">${p.name}</div>
    <div class="popup-meta">类型：${p.type} | 所属：${p.campus}</div>
    <div class="popup-btns">
      <button class="popup-btn create" onclick="openCreateModal('${p.name}', ${p.lat}, ${p.lng})">创建队伍</button>
      <button class="popup-btn join" onclick="openJoinModal('${p.name}', ${p.lat}, ${p.lng})">附近队伍</button>
    </div>
  `;
}

function flyToCampus(i) {
  const c = state.campuses[i];
  if (c && state.map) {
    state.map.flyTo([c.centerLat, c.centerLng], 15, { duration: 0.8 });
    setTimeout(() => { if (state.map) state.map.invalidateSize(); }, 100);
  }
}

/* ---- 队伍列表 ---- */
async function refreshTrips() {
  const data = await api("/api/trips?size=50");
  if (data.code !== 0) return;
  state.trips = data.data.items;
  renderTripList();
}

function renderTripList() {
  const container = $("trip-list");
  if (state.trips.length === 0) {
    container.innerHTML = `<p class="empty-hint">点击地图上的地点创建队伍</p>`;
    return;
  }
  container.innerHTML = "";
  state.trips.forEach((t) => {
    const div = document.createElement("div");
    div.className = "trip-item";
    const seats = `${t.currentSeats}/${t.maxSeats}`;
    const badge = `<span class="ti-badge ${statusClass(t.status)}">${t.status}</span>`;
    const genderTag = t.gender && t.gender !== "不限" ? ` · ${t.gender}` : "";
    div.innerHTML = `
      <div class="ti-dest">${t.destination}</div>
      <div class="ti-meta">从 ${t.origin} 出发 · ${t.departAt} · ${seats}人${genderTag}</div>
      ${badge}
    `;
    div.addEventListener("click", () => showTripDetail(t));
    container.appendChild(div);
  });
}

function statusClass(s) {
  if (s === "待出发") return "open";
  if (s === "已满员") return "full";
  if (s === "已出发") return "departed";
  return "open";
}

/* ---- 行程生命周期辅助函数 ---- */
function loadJoinedTripIds() {
  try {
    const raw = localStorage.getItem("cmp_joined_trips");
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) state.joinedTripIds = new Set(arr);
    }
  } catch (e) {
    state.joinedTripIds = new Set();
  }
}

function saveJoinedTripIds() {
  try {
    localStorage.setItem("cmp_joined_trips", JSON.stringify([...state.joinedTripIds]));
  } catch (e) {}
}

function computeTripActions(trip) {
  const isLeader = state.username === trip.leaderName;
  const isJoined = state.joinedTripIds.has(trip.tripId);
  const actions = [];

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

async function handleTripActionSuccess(data, tripId, keepOpen, successMsg) {
  if (data.code !== 0) {
    setMsg("jm-msg", data.message, true);
    return;
  }
  setMsg("jm-msg", successMsg);
  await refreshTrips();
  if (keepOpen) {
    const updated = state.trips.find((t) => t.tripId === tripId);
    if (updated) showTripDetail(updated);
    else $("join-modal").classList.add("hidden");
  } else {
    $("join-modal").classList.add("hidden");
  }
}

async function departTrip(tripId) {
  const data = await api(`/api/trips/${tripId}/depart`, { method: "POST" });
  await handleTripActionSuccess(data, tripId, true, "已标记出发");
}

async function completeTrip(tripId) {
  const data = await api(`/api/trips/${tripId}/complete`, { method: "POST" });
  await handleTripActionSuccess(data, tripId, true, "行程已完成");
}

async function cancelTrip(tripId) {
  const data = await api(`/api/trips/${tripId}/cancel`, { method: "POST" });
  await handleTripActionSuccess(data, tripId, false, "队伍已取消");
}

async function leaveTrip(tripId) {
  const data = await api(`/api/trips/${tripId}/leave`, { method: "POST" });
  if (data.code === 0) {
    state.joinedTripIds.delete(tripId);
    saveJoinedTripIds();
  }
  await handleTripActionSuccess(data, tripId, false, "已退出队伍");
}

function showTripDetail(t) {
  const info = $("jm-info");
  const actions = computeTripActions(t);
  const btnsHtml = actions
    .map((a) => `<button class="ji-join-btn" onclick="${a.type}Trip('${t.tripId}')">${a.label}</button>`)
    .join(" ");
  info.innerHTML = `
    <div class="ji-row"><span class="ji-label">目的地</span><span class="ji-value">${t.destination}</span></div>
    <div class="ji-row"><span class="ji-label">出发地</span><span class="ji-value">${t.origin}</span></div>
    <div class="ji-row"><span class="ji-label">出发时间</span><span class="ji-value">${t.departAt}</span></div>
    <div class="ji-row"><span class="ji-label">人数</span><span class="ji-value">${t.currentSeats}/${t.maxSeats}</span></div>
    <div class="ji-row"><span class="ji-label">费用</span><span class="ji-value">${t.fee != null ? t.fee + "元" : "免费"}</span></div>
    <div class="ji-row"><span class="ji-label">性别要求</span><span class="ji-value">${t.gender || "不限"}</span></div>
    <div class="ji-row"><span class="ji-label">状态</span><span class="ji-value">${t.status}</span></div>
    ${t.remark ? `<div class="ji-row"><span class="ji-label">备注</span><span class="ji-value">${t.remark}</span></div>` : ""}
    ${btnsHtml ? `<div class="ji-actions">${btnsHtml}</div>` : ""}
  `;
  $("join-modal").classList.remove("hidden");
}

/* ---- 创建队伍 ---- */
let createTarget = null;

function openCreateModal(destName, destLat, destLng) {
  if (!state.selectedGate) {
    alert("请先选择出发入口");
    return;
  }
  createTarget = { destName, destLat, destLng };
  const gate = state.selectedGate;
  const campus = state.campuses[state.selectedCampus];
  $("cm-origin").textContent = campus.name + " · " + gate.name;
  $("cm-dest").textContent = destName;
  $("cm-depart").value = "";
  $("cm-seats").value = "3";
  $("cm-fee").value = "";
  $("cm-gender").value = "不限";
  $("cm-remark").value = "";
  setMsg("cm-msg", "");
  $("create-modal").classList.remove("hidden");
}

$("cm-cancel").addEventListener("click", () => {
  $("create-modal").classList.add("hidden");
});

$("cm-confirm").addEventListener("click", async () => {
  if (!createTarget) return;
  const gate = state.selectedGate;
  const campus = state.campuses[state.selectedCampus];
  const departAt = $("cm-depart").value;
  if (!departAt) return setMsg("cm-msg", "请选择出发时间", true);

  const body = {
    origin: campus.name + " · " + gate.name,
    destination: createTarget.destName,
    departAt: departAt,
    seats: parseInt($("cm-seats").value) || 1,
    fee: $("cm-fee").value ? parseFloat($("cm-fee").value) : null,
    originLat: gate.lat,
    originLng: gate.lng,
    destinationLat: createTarget.destLat,
    destinationLng: createTarget.destLng,
    gender: $("cm-gender").value,
    remark: $("cm-remark").value || null,
  };

  const data = await api("/api/trips", { method: "POST", body });
  if (data.code !== 0) return setMsg("cm-msg", data.message, true);
  setMsg("cm-msg", "队伍创建成功！");
  $("create-modal").classList.add("hidden");
  await refreshTrips();
});

/* ---- 加入队伍 ---- */
function openJoinModal(destName, destLat, destLng) {
  const nearby = state.trips.filter((t) => t.destination === destName);
  const container = $("jm-info");
  if (nearby.length === 0) {
    container.innerHTML = `<p style="text-align:center;color:var(--ink-soft);padding:16px 0;">该地点暂无队伍，点击「创建队伍」发起一个吧</p>`;
  } else {
    container.innerHTML = "";
    nearby.forEach((t) => {
      const canJoin = t.status === "待出发" && t.currentSeats < t.maxSeats;
      const div = document.createElement("div");
      div.className = "trip-item";
      div.style.marginBottom = "8px";
      div.innerHTML = `
        <div class="ti-dest">${t.destination}</div>
        <div class="ti-meta">从 ${t.origin} · ${t.departAt} · ${t.currentSeats}/${t.maxSeats}人 · ${t.gender || "不限"}</div>
        ${canJoin ? `<button class="ji-join-btn" onclick="joinTrip('${t.tripId}')">加入</button>` : `<span class="ti-badge full">${t.status}</span>`}
      `;
      container.appendChild(div);
    });
  }
  $("join-modal").classList.remove("hidden");
}

async function joinTrip(tripId) {
  const data = await api(`/api/trips/${tripId}/join`, { method: "POST" });
  if (data.code !== 0) {
    setMsg("jm-msg", data.message, true);
    return;
  }
  state.joinedTripIds.add(tripId);
  saveJoinedTripIds();
  setMsg("jm-msg", "加入成功！");
  $("join-modal").classList.add("hidden");
  await refreshTrips();
}

$("jm-cancel").addEventListener("click", () => {
  $("join-modal").classList.add("hidden");
  setMsg("jm-msg", "");
});

/* ---- 退出登录 ---- */
$("logout-btn").addEventListener("click", () => {
  showGuestOverlay();
});

/* ---- 启动 ---- */
(async function start() {
  const ver = localStorage.getItem("cmp_session_version");
  if (ver !== SESSION_VERSION) {
    localStorage.removeItem("cmp_token");
    localStorage.removeItem("cmp_username");
    localStorage.removeItem("cmp_gender");
    state.token = null;
    state.username = null;
    state.gender = "保密";
    showGuestOverlay();
    return;
  }
  loadJoinedTripIds();
  if (state.token && state.username && state.gender) {
    hideGuestOverlay();
    await initMap();
  } else {
    showGuestOverlay();
  }
})();