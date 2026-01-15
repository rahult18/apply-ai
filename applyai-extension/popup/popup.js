const APP_BASE_URL = "http://localhost:3000";
const API_BASE_URL = "http://localhost:8000";

function storageGet(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}
function storageRemove(keys) {
  return new Promise((resolve) => chrome.storage.local.remove(keys, resolve));
}

document.addEventListener("DOMContentLoaded", () => {
  const statusPill = document.getElementById("statusPill");
  const accountValue = document.getElementById("accountValue");
  const hint = document.getElementById("hint");

  const primaryBtn = document.getElementById("primaryBtn");
  const extractBtn = document.getElementById("extractBtn");
  const secondaryBtn = document.getElementById("secondaryBtn");
  const disconnectBtn = document.getElementById("disconnectBtn");
  const debugExtractBtn = document.getElementById("debugExtractBtn");

  const extractStatus = document.getElementById("extractStatus");

  const resultCard = document.getElementById("resultCard");
  const resultTitle = document.getElementById("resultTitle");
  const resultCompany = document.getElementById("resultCompany");

  // current-session only UI state (no persistence across popup closes)
  let sessionState = "idle"; // idle | extracting | extracted | autofilling | autofilled | error

  const setPill = (state, text) => {
    statusPill.className = `pill pill--${state}`;
    statusPill.textContent = text;
  };

  const setExtractStatus = (text) => {
    extractStatus.style.display = "block";
    extractStatus.textContent = text;
  };

  const clearExtractStatus = () => {
    extractStatus.style.display = "none";
    extractStatus.textContent = "";
  };

  const clearResultCard = () => {
    resultCard.style.display = "none";
    resultTitle.textContent = "";
    resultCompany.textContent = "";
  };

  const showResultCard = ({ job_title, company }) => {
    resultTitle.textContent = job_title || "(Untitled role)";
    resultCompany.textContent = company || "";
    resultCard.style.display = "block";
  };

  const setExtractButtonMode = (mode) => {
    // mode: idle | extracting | extracted | autofilling | error
    if (mode === "extracting") {
      extractBtn.disabled = true;
      extractBtn.textContent = "Extracting…";
      return;
    }

    if (mode === "autofilling") {
      extractBtn.disabled = true;
      extractBtn.textContent = "Generating Autofill…";
      return;
    }

    extractBtn.disabled = false;
    if (mode === "extracted") extractBtn.textContent = "Generate Autofill";
    else if (mode === "error") extractBtn.textContent = "Try again";
    else extractBtn.textContent = "Extract Job Description";
  };

  const setConnectedUI = (userLabel) => {
    setPill("ok", "Connected");
    accountValue.textContent = userLabel;
    accountValue.classList.remove("muted");

    primaryBtn.style.display = "none";
    extractBtn.style.display = "block";
    secondaryBtn.style.display = "block";
    disconnectBtn.style.display = "block";

    hint.textContent = "Go to a job posting page, then click Extract Job Description.";
  };

  const setDisconnectedUI = () => {
    setPill("warn", "Not connected");
    accountValue.textContent = "Not connected";
    accountValue.classList.add("muted");

    primaryBtn.style.display = "block";
    extractBtn.style.display = "none";
    secondaryBtn.style.display = "none";
    disconnectBtn.style.display = "none";

    hint.textContent = "Connect to sync your profile and autofill preferences.";
    clearExtractStatus();
    clearResultCard();
    setExtractButtonMode("idle");
    sessionState = "idle";
  };

  const setErrorUI = (msg) => {
    setPill("err", "Error");
    accountValue.textContent = "Not connected";
    accountValue.classList.add("muted");

    primaryBtn.style.display = "block";
    extractBtn.style.display = "none";
    secondaryBtn.style.display = "none";
    disconnectBtn.style.display = "none";

    hint.textContent = msg || "Unable to verify connection. Try connecting again.";
    clearExtractStatus();
    clearResultCard();
    setExtractButtonMode("idle");
    sessionState = "idle";
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
        await storageRemove(["extensionToken"]);
        setDisconnectedUI();
        return;
      }

      const userData = await res.json();
      const displayName = userData?.full_name || userData?.email || "Connected";
      setConnectedUI(displayName);

      // current-session only: always start clean on popup open
      clearExtractStatus();
      clearResultCard();
      setExtractButtonMode("idle");
      sessionState = "idle";
    } catch (e) {
      setErrorUI("Network error talking to ApplyAI API.");
    }
  };

  // Live refresh when background finishes exchange (if popup is open)
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type === "APPLYAI_EXTENSION_CONNECTED") updateUI();

    if (msg?.type === "APPLYAI_EXTRACT_JD_PROGRESS") {
      // guard: ignore progress if user isn't in extraction flow
      if (sessionState !== "extracting") return;

      setPill("warn", "Working");
      if (msg.stage === "starting") setExtractStatus("Starting…");
      if (msg.stage === "extracting_dom") setExtractStatus("Reading page…");
      if (msg.stage === "sending_to_backend") setExtractStatus("Saving to tracker…");
    }

    if (msg?.type === "APPLYAI_EXTRACT_JD_RESULT") {
      if (msg.ok) {
        sessionState = "extracted";
        setPill("ok", "Saved");
        setExtractStatus("Saved ✓");
        showResultCard({ job_title: msg.job_title, company: msg.company });
        setExtractButtonMode("extracted");
        hint.textContent = "Open the application form, then click Generate Autofill.";
      } else {
        sessionState = "error";
        setPill("err", "Error");
        setExtractStatus(`Extraction failed — ${msg.error || "unknown error"}`);
        clearResultCard();
        setExtractButtonMode("error");
      }
    }

    if (msg?.type === "APPLYAI_AUTOFILL_PROGRESS") {
      if (sessionState !== "autofilling") return;

      setPill("warn", "Working");
      if (msg.stage === "starting") setExtractStatus("Starting…");
      if (msg.stage === "extracting_dom") setExtractStatus("Reading page…");
      if (msg.stage === "planning") setExtractStatus("Generating autofill plan…");
      if (msg.stage === "autofilling") setExtractStatus("Filling form…");
    }

    if (msg?.type === "APPLYAI_AUTOFILL_RESULT") {
      if (msg.ok) {
        sessionState = "autofilled";
        setPill("ok", "Autofilled");
        if (typeof msg.filled === "number") {
          setExtractStatus(`Autofilled ${msg.filled} fields ✓`);
        } else {
          setExtractStatus("Autofill applied ✓");
        }
        setExtractButtonMode("extracted");
        hint.textContent = "Review the form before submitting.";
      } else {
        sessionState = "extracted";
        setPill("err", "Error");
        setExtractStatus(`Autofill failed — ${msg.error || "unknown error"}`);
        setExtractButtonMode("extracted");
      }
    }
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

  const startExtraction = () => {
    sessionState = "extracting";
    clearResultCard();
    setPill("warn", "Working");
    setExtractButtonMode("extracting");
    setExtractStatus("Starting…");

    chrome.runtime.sendMessage({ type: "APPLYAI_EXTRACT_JD" }, (resp) => {
      // background will also send progress/result messages; this callback is a backup
      if (chrome.runtime.lastError) {
        sessionState = "error";
        setPill("err", "Error");
        setExtractButtonMode("error");
        setExtractStatus(`Extraction failed — ${chrome.runtime.lastError.message}`);
        return;
      }
      if (!resp?.ok) {
        sessionState = "error";
        setPill("err", "Error");
        setExtractButtonMode("error");
        setExtractStatus(`Extraction failed — ${resp?.error || "unknown error"}`);
      }
    });
  };

  const startAutofill = () => {
    sessionState = "autofilling";
    setPill("warn", "Working");
    setExtractButtonMode("autofilling");
    setExtractStatus("Generating autofill plan…");

    chrome.runtime.sendMessage({ type: "APPLYAI_AUTOFILL_PLAN" }, (resp) => {
      // background will also send progress/result messages; this callback is a backup
      if (chrome.runtime.lastError) {
        sessionState = "extracted";
        setPill("err", "Error");
        setExtractButtonMode("extracted");
        setExtractStatus(`Autofill failed — ${chrome.runtime.lastError.message}`);
        return;
      }
      if (!resp?.ok) {
        sessionState = "extracted";
        setPill("err", "Error");
        setExtractButtonMode("extracted");
        setExtractStatus(`Autofill failed — ${resp?.error || "unknown error"}`);
      }
    });
  };

  extractBtn.addEventListener("click", async () => {
    if (sessionState === "extracted" || sessionState === "autofilled") {
      startAutofill();
      return;
    }
    startExtraction();
  });

  debugExtractBtn.addEventListener("click", async () => {
    console.log("🐛 DEBUG: Starting form field extraction with dropdown interaction...");
    setPill("warn", "Extracting");
    debugExtractBtn.disabled = true;
    debugExtractBtn.textContent = "🐛 Extracting...";

    chrome.runtime.sendMessage({ type: "APPLYAI_DEBUG_EXTRACT_FIELDS" }, (resp) => {
      debugExtractBtn.disabled = false;
      debugExtractBtn.textContent = "🐛 Extract Form Fields (Debug)";

      if (chrome.runtime.lastError) {
        setPill("err", "Error");
        console.error("🐛 DEBUG: Extraction failed", chrome.runtime.lastError);
        return;
      }

      if (resp?.ok) {
        setPill("ok", "Extracted");
        console.log("🐛 DEBUG: Extraction successful!", resp);
        console.log(`🐛 DEBUG: Found ${resp.fieldCount} fields`);
        console.log("🐛 DEBUG: Check the page console for detailed field data");
      } else {
        setPill("err", "Error");
        console.error("🐛 DEBUG: Extraction failed", resp?.error);
      }
    });
  });

  updateUI();
});
