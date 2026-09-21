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
  pollTask(currentTaskId);
}


videoButton.addEventListener("click", () => {
  if (!selectedQuality) return;

  startTask("video", {
    height: selectedQuality.height,
    quality_id: selectedQuality.quality_id ?? null
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
      error: "失败"
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
