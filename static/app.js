const $ = (selector) => document.querySelector(selector);

const form = $("#parseForm");
const input = $("#urlInput");
const parseButton = $("#parseButton");
const statusText = $("#status");
const result = $("#result");

const downloadDir = $("#downloadDir");
const chooseFolderButton = $("#chooseFolderButton");
const askEachTime = $("#askEachTime");
const fragments = $("#fragments");
const cookieBrowser = $("#cookieBrowser");
const cookieProfile = $("#cookieProfile");
const cookieStatusBadge = $("#cookieStatusBadge");

const qualitiesBox = $("#qualities");
const qualityCount = $("#qualityCount");
const videoButton = $("#videoButton");
const audioButton = $("#audioButton");
const coverButton = $("#coverButton");

const subtitleSelect = $("#subtitleSelect");
const subtitleButton = $("#subtitleButton");
const subtitleControls = $("#subtitleControls");
const subtitleCount = $("#subtitleCount");
const subtitleEmpty = $("#subtitleEmpty");
const danmakuSection = $("#danmakuSection");
const danmakuButton = $("#danmakuButton");

const taskPanel = $("#taskPanel");
const taskTitle = $("#taskTitle");
const taskState = $("#taskState");
const taskDetails = $("#taskDetails");
const taskActions = $("#taskActions");
const openFolderButton = $("#openFolderButton");
const fileLink = $("#fileLink");

const videoProgressRow = $("#videoProgressRow");
const videoProgressText = $("#videoProgressText");
const videoProgressBar = $("#videoProgressBar");

const audioProgressRow = $("#audioProgressRow");
const audioProgressText = $("#audioProgressText");
const audioProgressBar = $("#audioProgressBar");

const singleProgressRow = $("#singleProgressRow");
const singleProgressText = $("#singleProgressText");
const singleProgressBar = $("#singleProgressBar");

let currentVideo = null;
let selectedQuality = null;
let currentTaskId = null;
let pollTimer = null;


function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "未知";
  const total = Math.floor(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${minutes}:${String(secs).padStart(2, "0")}`;
}


function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;

  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }

  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}


function componentText(component) {
  if (!component) return "等待";
  if (component.status === "done") return "✓";

  if (typeof component.progress === "number") {
    const details = [`${component.progress.toFixed(1)}%`];

    if (component.speed) {
      details.push(`${formatBytes(component.speed)}/s`);
    }

    if (component.eta !== null && component.eta !== undefined) {
      details.push(`剩余 ${component.eta}s`);
    }

    return details.join(" · ");
  }

  return "下载中";
}


function componentProgress(component) {
  if (!component) return 0;
  if (component.status === "done") return 100;
  return typeof component.progress === "number" ? component.progress : 0;
}


async function loadSettings() {
  const response = await fetch("/api/settings");
  const data = await response.json();

  downloadDir.value = data.download_dir;
  askEachTime.checked = data.ask_each_time;
  fragments.value = String(data.concurrent_fragments);
  cookieBrowser.value = data.cookie_browser || "none";
  cookieProfile.value = data.cookie_profile || "";
  updateCookieBadge();
}


async function saveSettings() {
  const response = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ask_each_time: askEachTime.checked,
      concurrent_fragments: Number(fragments.value),
      cookie_browser: cookieBrowser.value,
      cookie_profile: cookieProfile.value.trim()
    })
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "设置保存失败");
  }
}


async function chooseFolder(saveAsDefault = false) {
  chooseFolderButton.disabled = true;
  chooseFolderButton.textContent = "等待选择…";

  try {
    const response = await fetch("/api/select-folder", { method: "POST" });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "无法打开文件夹选择窗口");
    }

    if (data.cancelled) return null;

    if (saveAsDefault) {
      const update = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ download_dir: data.path })
      });

      const updated = await update.json();

      if (!update.ok) {
        throw new Error(updated.detail || "保存默认目录失败");
      }

      downloadDir.value = updated.download_dir;
    }

    return data.path;

  } finally {
    chooseFolderButton.disabled = false;
    chooseFolderButton.textContent = "选择文件夹";
  }
}


chooseFolderButton.addEventListener("click", async () => {
  try {
    await chooseFolder(true);
  } catch (error) {
    alert(error.message);
  }
});


askEachTime.addEventListener("change", () => {
  saveSettings().catch((error) => alert(error.message));
});


fragments.addEventListener("change", () => {
  saveSettings().catch((error) => alert(error.message));
});


function updateCookieBadge() {
  const browser = cookieBrowser.value;

  if (browser === "none") {
    cookieStatusBadge.textContent = "未启用";
    cookieStatusBadge.classList.remove("enabled");
    cookieProfile.disabled = true;
  } else {
    const names = {
      chrome: "Chrome",
      edge: "Edge",
      firefox: "Firefox",
      brave: "Brave"
    };

    cookieStatusBadge.textContent = `使用 ${names[browser] || browser}`;
    cookieStatusBadge.classList.add("enabled");
    cookieProfile.disabled = false;
  }
}


cookieBrowser.addEventListener("change", () => {
  updateCookieBadge();

  saveSettings()
    .then(() => {
      if (currentVideo) {
        statusText.textContent = "登录态设置已更新，请重新点击“解析”以刷新字幕。";
      }
    })
    .catch((error) => alert(error.message));
});


cookieProfile.addEventListener("change", () => {
  saveSettings()
    .then(() => {
      if (currentVideo) {
        statusText.textContent = "Profile 设置已更新，请重新解析视频。";
      }
    })
    .catch((error) => alert(error.message));
});


function resetTaskPanel() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }

  currentTaskId = null;
  taskPanel.classList.add("hidden");
  taskActions.classList.add("hidden");

  for (const row of [videoProgressRow, audioProgressRow, singleProgressRow]) {
    row.classList.add("hidden");
  }

  videoProgressBar.style.width = "0%";
  audioProgressBar.style.width = "0%";
  singleProgressBar.style.width = "0%";
}


function renderQualities(qualities) {
  qualitiesBox.innerHTML = "";
  selectedQuality = null;
  videoButton.disabled = true;
  videoButton.textContent = "先选择画质";

  if (!qualities || qualities.length === 0) {
    qualityCount.textContent = "";
    qualitiesBox.textContent = "没有读取到可显示的分辨率。";
    return;
  }

  qualityCount.textContent = `${qualities.length} 个分辨率`;

  qualities.forEach((quality) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "quality";

    const fps = quality.fps && quality.fps > 30
      ? ` · ${Math.round(quality.fps)} FPS`
      : "";

    const resolution = quality.width
      ? `${quality.width}×${quality.height}`
      : `${quality.height} px`;

    const label = quality.label || `${quality.height}P`;

    item.innerHTML = `
      <strong>${label}</strong>
      <small>${resolution}${fps}</small>
    `;

    item.addEventListener("click", () => {
      document.querySelectorAll(".quality").forEach((el) => {
        el.classList.remove("selected");
      });

      item.classList.add("selected");
      selectedQuality = quality;
      videoButton.disabled = false;
      videoButton.textContent = `下载 ${label} MP4`;
    });

    qualitiesBox.appendChild(item);
  });
}


function renderSubtitles(subtitles) {
  subtitleSelect.innerHTML = "";

  if (!subtitles || subtitles.length === 0) {
    subtitleCount.textContent = "0";
    subtitleControls.classList.add("hidden");
    subtitleEmpty.classList.remove("hidden");
    return;
  }

  subtitleCount.textContent = `${subtitles.length} 个`;
  subtitleControls.classList.remove("hidden");
  subtitleEmpty.classList.add("hidden");

  subtitles.forEach((subtitle) => {
    const option = document.createElement("option");
    option.value = subtitle.id;
    option.textContent = `${subtitle.name} (${subtitle.id})`;
    subtitleSelect.appendChild(option);
  });
}


function renderDanmaku(hasDanmaku) {
  danmakuSection.classList.toggle("hidden", !hasDanmaku);
}


async function resolveOutputDir() {
  await saveSettings();

  if (!askEachTime.checked) {
    return null;
  }

  const selected = await chooseFolder(false);

  if (!selected) {
    throw new Error("已取消选择保存位置");
  }

  return selected;
}


async function startTask(kind, extra = {}) {
  if (!currentVideo) return;

  let outputDir;

  try {
    outputDir = await resolveOutputDir();
  } catch (error) {
    if (error.message !== "已取消选择保存位置") {
      alert(error.message);
    }
    return;
  }

  resetTaskPanel();
  taskPanel.classList.remove("hidden");

  taskTitle.textContent = {
    video: "视频下载",
    audio: "音频下载",
    cover: "封面下载",
    subtitle: "字幕下载",
    danmaku: "弹幕下载"
  }[kind];

  taskState.textContent = "创建任务…";
  taskDetails.textContent = "";

  if (kind === "video") {
    videoProgressRow.classList.remove("hidden");
    audioProgressRow.classList.remove("hidden");
  } else {
    singleProgressRow.classList.remove("hidden");
  }

  const payload = {
    url: currentVideo.webpage_url,
    title: currentVideo.title,
    kind,
    concurrent_fragments: Number(fragments.value),
    ...extra
  };

  if (outputDir) {
    payload.output_dir = outputDir;
  }

  const response = await fetch("/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await response.json();

  if (!response.ok) {
    taskState.textContent = "失败";
    taskDetails.textContent = data.detail || "创建任务失败";
    return;
  }

  currentTaskId = data.task_id;
  refreshTaskCenter();
  pollTask(currentTaskId);
}


videoButton.addEventListener("click", () => {
  if (!selectedQuality) return;

  startTask("video", {
    height: selectedQuality.height,
    quality_id: selectedQuality.quality_id ?? null,
    quality_label: selectedQuality.label || `${selectedQuality.height}P`
  });
});

audioButton.addEventListener("click", () => startTask("audio"));
coverButton.addEventListener("click", () => startTask("cover"));

subtitleButton.addEventListener("click", () => {
  if (!subtitleSelect.value) return;
  startTask("subtitle", { subtitle_lang: subtitleSelect.value });
});

danmakuButton.addEventListener("click", () => {
  startTask("danmaku");
});


async function pollTask(taskId) {
  try {
    const response = await fetch(`/api/tasks/${taskId}`);
    const task = await response.json();

    if (!response.ok) {
      throw new Error(task.detail || "读取任务状态失败");
    }

    taskState.textContent = {
      queued: "排队中",
      starting: "准备中",
      downloading: "下载中",
      processing: "处理中",
      done: "完成",
      error: "失败",
      cancelled: "已取消"
    }[task.status] || task.status;

    if (task.kind === "video") {
      const video = task.components?.video;
      const audio = task.components?.audio;

      videoProgressText.textContent = componentText(video);
      audioProgressText.textContent = componentText(audio);

      videoProgressBar.style.width = `${componentProgress(video)}%`;
      audioProgressBar.style.width = `${componentProgress(audio)}%`;

      if (task.status === "processing") {
        taskDetails.textContent = "下载阶段完成，正在由 FFmpeg 合并/处理音视频。";
      }
    } else {
      const component =
        task.components?.audio ||
        task.components?.file ||
        task.components?.video;

      const progress = componentProgress(component);
      singleProgressBar.style.width = `${task.status === "done" ? 100 : progress}%`;

      if (task.status === "processing") {
        singleProgressText.textContent = "处理中…";
      } else if (task.status === "done") {
        singleProgressText.textContent = "100%";
      } else {
        singleProgressText.textContent = componentText(component);
      }
    }

    if (task.status === "done") {
      taskDetails.textContent =
        `已保存：${task.filepath}` +
        (task.file_size ? ` · ${formatBytes(task.file_size)}` : "");

      fileLink.href = `/api/files/${taskId}`;
      fileLink.textContent = "浏览器另存一份";
      taskActions.classList.remove("hidden");
      return;
    }

    if (task.status === "error") {
      taskDetails.textContent = task.error || "未知错误";
      return;
    }

    if (task.status === "cancelled") {
      taskDetails.textContent = "排队任务已取消";
      return;
    }

    pollTimer = setTimeout(() => pollTask(taskId), 900);

  } catch (error) {
    taskState.textContent = "状态读取失败";
    taskDetails.textContent = error.message;
  }

}


openFolderButton.addEventListener("click", async () => {
  if (!currentTaskId) return;

  const response = await fetch(`/api/open-folder/${currentTaskId}`, {
    method: "POST"
  });

  if (!response.ok) {
    const data = await response.json();
    alert(data.detail || "无法打开文件夹");
  }
});


form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url = input.value.trim();
  if (!url) return;

  result.classList.add("hidden");
  resetTaskPanel();

  parseButton.disabled = true;
  parseButton.textContent = "解析中…";
  statusText.textContent = "正在识别平台并读取媒体信息、画质和字幕…";

  try {
    const response = await fetch("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "解析失败");
    }

    currentVideo = data;

    $("#platformBadge").textContent = data.platform_name || "Media";
    $("#title").textContent = data.title;
    $("#uploader").textContent = data.uploader;
    $("#duration").textContent = formatDuration(data.duration);
    $("#videoId").textContent = data.id || "未知";
    $("#sourceLink").href = data.webpage_url;

    const thumbnail = $("#thumbnail");

    if (data.thumbnail_proxy) {
      thumbnail.src = data.thumbnail_proxy;
      thumbnail.style.display = "block";
    } else {
      thumbnail.style.display = "none";
    }

    renderQualities(data.qualities);
    renderSubtitles(data.subtitles);
    renderDanmaku(Boolean(data.danmaku));

    result.classList.remove("hidden");
    statusText.textContent = "解析成功。";

  } catch (error) {
    statusText.textContent = error.message;

  } finally {
    parseButton.disabled = false;
    parseButton.textContent = "解析";
  }
});


loadSettings().catch((error) => {
  statusText.textContent = `读取设置失败：${error.message}`;
});


// One history for the Web UI and Telegram Bot. The server performs all file actions.
const taskList = $("#taskList");
const managerMessage = $("#managerMessage");
const pageLabel = $("#taskPageLabel");
const pageSize = 20;
let taskTab = "current";
let taskPage = 0;
let refreshSequence = 0;

function taskStatusLabel(status) {
  return {
    queued: "排队中", starting: "准备中", downloading: "下载中",
    processing: "处理中", done: "已完成", error: "失败", cancelled: "已取消"
  }[status] || status;
}

function appendAction(parent, label, action) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", action);
  parent.appendChild(button);
}

async function taskOperation(path, method = "POST") {
  const response = await fetch(path, { method });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "操作失败");
  return data;
}

function runAction(callback) {
  Promise.resolve().then(callback).then(() => refreshTaskCenter()).catch((error) => {
    managerMessage.textContent = error.message;
  });
}

function renderManagerTask(task) {
  const item = document.createElement("article");
  item.className = "manager-item";
  const heading = document.createElement("div");
  heading.className = "manager-item-head";
  const title = document.createElement("strong");
  title.textContent = task.title || task.filename || "未命名任务";
  const state = document.createElement("span");
  state.className = `manager-state ${task.status === "error" ? "is-error" : task.status === "done" ? "is-done" : ""}`;
  state.textContent = taskStatusLabel(task.status);
  heading.append(title, state);
  item.appendChild(heading);

  const meta = document.createElement("div");
  meta.className = "manager-meta";
  const kind = { video: "视频", audio: "音频", cover: "封面", subtitle: "字幕", danmaku: "弹幕" }[task.kind] || task.kind;
  const created = task.created_at ? new Date(task.created_at).toLocaleString("zh-CN") : "";
  const details = [task.platform || "Media", kind, task.quality_label || (task.height ? `${task.height}P` : ""),
    task.source === "telegram" ? "Telegram" : "Web", created];
  if (task.status === "done") {
    details.push(task.file_size != null ? formatBytes(task.file_size) : "");
  }
  details.filter(Boolean).forEach((value) => {
    const span = document.createElement("span");
    span.textContent = value;
    meta.appendChild(span);
  });
  item.appendChild(meta);

  if (["starting", "downloading", "processing"].includes(task.status)) {
    const track = document.createElement("div");
    track.className = "progress-track";
    const bar = document.createElement("div");
    bar.className = "progress-bar";
    bar.style.width = `${Math.max(0, Math.min(100, task.progress || 0))}%`;
    track.appendChild(bar);
    item.appendChild(track);
    const telemetry = document.createElement("div");
    telemetry.className = "manager-telemetry";
    const speed = task.speed ? ` · ${formatBytes(task.speed)}/s` : "";
    const eta = task.eta != null ? ` · 剩余约 ${Math.ceil(task.eta)} 秒` : "";
    const componentDetail = task.kind === "video" && Object.keys(task.components || {}).length
      ? ` · 视频 ${componentText(task.components.video)} / 音频 ${componentText(task.components.audio)}` : "";
    telemetry.textContent = `${task.progress ?? 0}%${speed}${eta}${componentDetail}`;
    if (task.status === "processing") telemetry.textContent += " · 正在处理文件";
    item.appendChild(telemetry);
  }

  if (task.status === "error" && task.error) {
    const error = document.createElement("p");
    error.className = "manager-error";
    error.textContent = task.error;
    item.appendChild(error);
  }
  if (task.status === "done" && task.filepath) {
    const path = document.createElement("p");
    path.className = "manager-path";
    path.textContent = task.filepath;
    item.appendChild(path);
  }

  const actions = document.createElement("div");
  actions.className = "manager-item-actions";
  if (task.status === "done" && task.filepath) {
    appendAction(actions, "打开文件", () => runAction(() => taskOperation(`/api/open-file/${task.id}`)));
    appendAction(actions, "打开所在文件夹", () => runAction(() => taskOperation(`/api/open-folder/${task.id}`)));
    const link = document.createElement("a");
    link.href = `/api/files/${task.id}`;
    link.textContent = "浏览器另存";
    actions.appendChild(link);
  }
  if (task.status === "error") {
    appendAction(actions, "重新下载", () => runAction(async () => {
      await taskOperation(`/api/tasks/${task.id}/retry`);
      selectTaskTab("current");
    }));
  }
  if (task.status === "queued") {
    appendAction(actions, "取消排队", () => runAction(() => taskOperation(`/api/tasks/${task.id}/cancel`)));
  }
  if (actions.childElementCount) item.appendChild(actions);
  return item;
}

async function refreshTaskCenter() {
  const sequence = ++refreshSequence;
  const tab = taskTab;
  const offset = taskPage * pageSize;
  try {
    const [listResponse, countsResponse] = await Promise.all([
      fetch(`/api/tasks?status=${tab}&limit=${pageSize}&offset=${offset}`),
      fetch("/api/tasks/summary")
    ]);
    if (!listResponse.ok || !countsResponse.ok) throw new Error("读取下载任务失败");
    const [listing, counts] = await Promise.all([listResponse.json(), countsResponse.json()]);
    if (sequence !== refreshSequence || tab !== taskTab) return;
    const emptyText = {
      current: "现在没有正在下载的任务。", queued: "队列是空的。",
      done: "还没有完成的下载。", failed: "没有失败或取消的任务。"
    };
    taskList.replaceChildren(...(listing.items.length
      ? listing.items.map(renderManagerTask)
      : [Object.assign(document.createElement("p"), { className: "manager-message", textContent: emptyText[tab] })]));
    ["current", "queued", "done", "failed"].forEach((name) => {
      $(`#count${name[0].toUpperCase()}${name.slice(1)}`).textContent = String(counts[name] || 0);
    });
    const activeCount = (counts.current || 0) + (counts.queued || 0);
    $("#sidebarActiveCount").textContent = String(activeCount);
    $("#sidebarActiveCount").hidden = activeCount === 0;
    pageLabel.textContent = listing.total ? `${taskPage + 1} / ${Math.ceil(listing.total / pageSize)}` : "0 / 0";
    $("#previousTasks").disabled = taskPage === 0;
    $("#nextTasks").disabled = offset + pageSize >= listing.total;
    managerMessage.textContent = "";
  } catch (error) {
    if (sequence === refreshSequence) managerMessage.textContent = error.message;
  }
}

function selectTaskTab(name) {
  taskTab = name;
  taskPage = 0;
  document.querySelectorAll("[data-task-tab]").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.taskTab === name));
  });
  refreshTaskCenter();
}

document.querySelectorAll("[data-task-tab]").forEach((button) => {
  button.addEventListener("click", () => selectTaskTab(button.dataset.taskTab));
});
$("#previousTasks").addEventListener("click", () => { taskPage--; refreshTaskCenter(); });
$("#nextTasks").addEventListener("click", () => { taskPage++; refreshTaskCenter(); });
$("#clearHistory").addEventListener("click", () => {
  if (!confirm("清除已完成、失败和已取消的任务记录？已下载的文件不会删除。")) return;
  runAction(async () => {
    const result = await taskOperation("/api/tasks/history", "DELETE");
    taskPage = 0;
    managerMessage.textContent = `已清除 ${result.removed} 条记录`;
  });
});
refreshTaskCenter();
setInterval(refreshTaskCenter, 2000);

const views = { home: "首页 / 媒体解析", downloads: "下载 / 任务中心", settings: "设置 / 个性化" };
function navigate(view) {
  if (!Object.hasOwn(views, view)) return;
  document.body.dataset.view = view;
  $("#viewTitle").textContent = views[view];
  document.querySelectorAll("[data-nav]").forEach((button) => {
    if (button.dataset.nav === view) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  sessionStorage.setItem("moontrace-view", view);
  if (view === "downloads") refreshTaskCenter();
  window.scrollTo({ top: 0, behavior: "instant" });
}
document.querySelectorAll("[data-nav]").forEach((button) => {
  button.addEventListener("click", () => navigate(button.dataset.nav));
});
navigate(sessionStorage.getItem("moontrace-view") || "home");

const themePresets = {
  moon: ["#64a8ff", "#776bff", "#c576ff", "#f7f9ff"],
  aoko: ["#50d5ef", "#468fff", "#c0a8ff", "#f7fbff"],
  ember: ["#ffc07c", "#ff808d", "#ce84e3", "#fff7f0"]
};
const themeFields = {
  accent_a: $("#themeAccentA"), accent_b: $("#themeAccentB"),
  accent_c: $("#themeAccentC"), text: $("#themeText"),
  overlay: $("#themeOverlay"), panel_opacity: $("#themeOpacity")
};
let hasThemeBackground = false;
let backgroundVersion = Date.now();

function currentTheme() {
  return {
    preset: $("#themePreset").value,
    accent_a: themeFields.accent_a.value, accent_b: themeFields.accent_b.value,
    accent_c: themeFields.accent_c.value, text: themeFields.text.value,
    overlay: Number(themeFields.overlay.value),
    panel_opacity: Number(themeFields.panel_opacity.value)
  };
}

function previewTheme() {
  const theme = currentTheme();
  document.body.classList.toggle("has-user-background", hasThemeBackground);
  $("#overlayValue").textContent = `${theme.overlay}%`;
  $("#panelOpacityValue").textContent = `${theme.panel_opacity}%`;
  const background = hasThemeBackground
    ? `url("/api/theme-background?v=${backgroundVersion}")` : "none";
  $("#themeVariables").textContent = `:root {
    --accent-a: ${theme.accent_a}; --accent-b: ${theme.accent_b};
    --accent-c: ${theme.accent_c}; --text: ${theme.text};
    --theme-overlay: ${theme.overlay / 100};
    --theme-panel-opacity: ${theme.panel_opacity / 100};
    --theme-background-image: ${background};
  }`;
}

function fillTheme(theme) {
  $("#themePreset").value = theme.preset;
  for (const [key, element] of Object.entries(themeFields)) element.value = theme[key];
  hasThemeBackground = Boolean(theme.background);
  previewTheme();
}

async function themeRequest(url, options) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "主题操作失败");
  return result;
}

function themeMessage(errorOrText) {
  $("#themeMessage").textContent = errorOrText;
}

$("#themePreset").addEventListener("change", () => {
  const preset = themePresets[$("#themePreset").value];
  if (preset) {
    ["accent_a", "accent_b", "accent_c", "text"].forEach((key, index) => {
      themeFields[key].value = preset[index];
    });
  }
  previewTheme();
});
for (const [key, element] of Object.entries(themeFields)) {
  element.addEventListener("input", () => {
    if (key !== "overlay" && key !== "panel_opacity") $("#themePreset").value = "custom";
    previewTheme();
  });
}
$("#themeReset").addEventListener("click", () => {
  fillTheme({ preset: "moon", accent_a: "#64a8ff", accent_b: "#776bff",
    accent_c: "#c576ff", text: "#f7f9ff", overlay: 36,
    panel_opacity: 80, background: hasThemeBackground });
  themeMessage("已预览月夜配色，点击「保存主题」后生效。背景图片保持不变。");
});
$("#saveTheme").addEventListener("click", async () => {
  try {
    await themeRequest("/api/theme", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTheme())
    });
    themeMessage("主题已保存到本机。");
  } catch (error) { themeMessage(error.message); }
});
$("#backgroundUpload").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 12 * 1024 * 1024) {
    themeMessage("背景图片不能超过 12 MB。");
    event.target.value = "";
    return;
  }
  try {
    const result = await themeRequest("/api/theme/background", {
      method: "POST", headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file
    });
    hasThemeBackground = result.background;
    backgroundVersion = Date.now();
    previewTheme();
    themeMessage("背景图片已保存到本机。");
  } catch (error) { themeMessage(error.message); }
  event.target.value = "";
});
$("#removeBackground").addEventListener("click", async () => {
  try {
    await themeRequest("/api/theme/background", { method: "DELETE" });
    hasThemeBackground = false;
    previewTheme();
    themeMessage("背景图片已移除，月夜渐变仍会显示。");
  } catch (error) { themeMessage(error.message); }
});
themeRequest("/api/theme").then(fillTheme).catch((error) => themeMessage(error.message));
