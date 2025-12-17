const API_BASE_URL = "http://localhost:8000";

function storageGet(keys) {
    return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function storageSet(obj) {
    return new Promise((resolve) => chrome.storage.local.set(obj, resolve));
}

async function ensureInstallId() {
    const { installId } = await storageGet(["installId"]);
    if (installId) return installId;

    // crypto.randomUUID() is available in modern extension contexts
    const newId = crypto.randomUUID();
    await storageSet({ installId: newId });
    return newId;
}

chrome.runtime.onInstalled.addListener(() => {
    // Optional: pre-generate installId so it's stable immediately
    ensureInstallId().catch(() => { });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
        try {
            if (message?.type !== "APPLYAI_EXTENSION_CONNECT" || !message?.code) {
                sendResponse({ ok: false, error: "Ignoring message (wrong type or missing code)." });
                return;
            }

            const installId = await ensureInstallId();

            // Exchange one-time code for extension JWT
            const res = await fetch(`${API_BASE_URL}/extension/connect/exchange`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    one_time_code: message.code,
                    install_id: installId
                })
            });

            if (!res.ok) {
                const text = await res.text().catch(() => "");
                throw new Error(`Exchange failed: ${res.status} ${text}`);
            }

            const data = await res.json();
            const extensionToken = data.token;

            if (!extensionToken) {
                throw new Error("Exchange succeeded but no token returned.");
            }

            await storageSet({ extensionToken });

            // Notify all extension pages
            chrome.runtime.sendMessage({ type: "APPLYAI_EXTENSION_CONNECTED" }, () => {
                // Popup may not be open; ignore this case
                void chrome.runtime.lastError;
            });

            sendResponse({ ok: true });
        } catch (err) {
            sendResponse({ ok: false, error: String(err?.message || err) });
        }
    })();

    // Keep the message channel open for async sendResponse
    return true;
});
