const APP_BASE_URL = "http://localhost:3000";
const API_BASE_URL = "http://localhost:8000";

function storageGet(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}
function storageSet(obj) {
  return new Promise((resolve) => chrome.storage.local.set(obj, resolve));
}
function storageRemove(keys) {
  return new Promise((resolve) => chrome.storage.local.remove(keys, resolve));
}

document.addEventListener("DOMContentLoaded", () => {
  const statusPill = document.getElementById("statusPill");
  const accountValue = document.getElementById("accountValue");
  const hint = document.getElementById("hint");

  const primaryBtn = document.getElementById("primaryBtn");
  const secondaryBtn = document.getElementById("secondaryBtn");
  const disconnectBtn = document.getElementById("disconnectBtn");

  const setPill = (state, text) => {
    statusPill.className = `pill pill--${state}`;
    statusPill.textContent = text;
  };

  const setConnectedUI = (userLabel) => {
    setPill("ok", "Connected");
    accountValue.textContent = userLabel;
    accountValue.classList.remove("muted");

    primaryBtn.style.display = "none";
    secondaryBtn.style.display = "block";
    disconnectBtn.style.display = "block";

    hint.textContent = "You’re ready. Go to a job application page and start autofilling.";
  };

  const setDisconnectedUI = () => {
    setPill("warn", "Not connected");
    accountValue.textContent = "Not connected";
    accountValue.classList.add("muted");

    primaryBtn.style.display = "block";
    secondaryBtn.style.display = "none";
    disconnectBtn.style.display = "none";

    hint.textContent = "Connect to sync your profile and autofill preferences.";
  };

  const setErrorUI = (msg) => {
    setPill("err", "Error");
    accountValue.textContent = "Not connected";
    accountValue.classList.add("muted");

    primaryBtn.style.display = "block";
    secondaryBtn.style.display = "none";
    disconnectBtn.style.display = "none";

    hint.textContent = msg || "Unable to verify connection. Try connecting again.";
  };

  const updateUI = async () => {
    try {
      setPill("idle", "Checking…");
      const { extensionToken } = await storageGet(["extensionToken"]);

      if (!extensionToken) {
        setDisconnectedUI();
        return;
      }

      const res = await fetch(`${API_BASE_URL}/extension/me`, {
        headers: { Authorization: `Bearer ${extensionToken}` }
      });

      if (!res.ok) {
        // token invalid/expired; wipe it so UI doesn't get stuck
        await storageRemove(["extensionToken"]);
        setDisconnectedUI();
        return;
      }

      const userData = await res.json();
      const displayName = userData?.full_name || userData?.email || "Connected";
      setConnectedUI(displayName);
    } catch (e) {
      setErrorUI("Network error talking to ApplyAI API.");
    }
  };

  // Live refresh when background finishes exchange (if popup is open)
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type === "APPLYAI_EXTENSION_CONNECTED") updateUI();
  });

  primaryBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: `${APP_BASE_URL}/extension/connect` });
    window.close();
  });

  secondaryBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: `${APP_BASE_URL}/home` });
    window.close();
  });

  disconnectBtn.addEventListener("click", async () => {
    await storageRemove(["extensionToken"]);
    setDisconnectedUI();
  });

  updateUI();
});
