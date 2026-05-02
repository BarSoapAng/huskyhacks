const STORAGE_KEY = "huskyhacks.timer";
const DASHBOARD_URL = "http://127.0.0.1:5173";

const timerDisplay = document.getElementById("timerDisplay");
const minutesInput = document.getElementById("minutesInput");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resetBtn = document.getElementById("resetBtn");
const dashboardBtn = document.getElementById("dashboardBtn");

let timerState = {
  durationSeconds: 5 * 60,
  remainingSeconds: 5 * 60,
  isRunning: false,
  endsAt: null
};

function formatTime(totalSeconds) {
  const safeSeconds = Math.max(0, totalSeconds);
  const minutes = Math.floor(safeSeconds / 60).toString().padStart(2, "0");
  const seconds = (safeSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function getLiveRemainingSeconds(state) {
  if (!state.isRunning || !state.endsAt) {
    return state.remainingSeconds;
  }

  return Math.max(0, Math.ceil((state.endsAt - Date.now()) / 1000));
}

function render() {
  const remainingSeconds = getLiveRemainingSeconds(timerState);
  timerDisplay.textContent = formatTime(remainingSeconds);
  minutesInput.value = Math.max(1, Math.round(timerState.durationSeconds / 60)).toString();
  startBtn.disabled = timerState.isRunning;
  pauseBtn.disabled = !timerState.isRunning;
}

async function saveState() {
  await chrome.storage.local.set({ [STORAGE_KEY]: timerState });
}

async function loadState() {
  const stored = await chrome.storage.local.get(STORAGE_KEY);
  const savedState = stored[STORAGE_KEY];

  if (savedState) {
    timerState = {
      ...timerState,
      ...savedState,
      remainingSeconds: getLiveRemainingSeconds(savedState)
    };

    if (timerState.remainingSeconds === 0) {
      timerState.isRunning = false;
      timerState.endsAt = null;
    }
  }

  render();
}

async function startTimer() {
  const minutes = Number(minutesInput.value);
  const durationSeconds = Math.max(1, Math.min(180, Math.round(minutes || 5))) * 60;
  const remainingSeconds = timerState.remainingSeconds > 0 ? timerState.remainingSeconds : durationSeconds;

  timerState = {
    durationSeconds,
    remainingSeconds,
    isRunning: true,
    endsAt: Date.now() + remainingSeconds * 1000
  };

  render();
  await saveState();
}

async function pauseTimer() {
  timerState = {
    ...timerState,
    remainingSeconds: getLiveRemainingSeconds(timerState),
    isRunning: false,
    endsAt: null
  };

  render();
  await saveState();
}

async function resetTimer() {
  const minutes = Number(minutesInput.value);
  const durationSeconds = Math.max(1, Math.min(180, Math.round(minutes || 5))) * 60;

  timerState = {
    durationSeconds,
    remainingSeconds: durationSeconds,
    isRunning: false,
    endsAt: null
  };

  render();
  await saveState();
}

startBtn.addEventListener("click", startTimer);
pauseBtn.addEventListener("click", pauseTimer);
resetBtn.addEventListener("click", resetTimer);
minutesInput.addEventListener("change", resetTimer);
dashboardBtn.addEventListener("click", () => chrome.tabs.create({ url: DASHBOARD_URL }));

setInterval(async () => {
  if (!timerState.isRunning) {
    return;
  }

  timerState.remainingSeconds = getLiveRemainingSeconds(timerState);

  if (timerState.remainingSeconds === 0) {
    timerState.isRunning = false;
    timerState.endsAt = null;
    await saveState();
  }

  render();
}, 500);

loadState();
