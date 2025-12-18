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

    const newId = crypto.randomUUID();
    await storageSet({ installId: newId });
    return newId;
}

chrome.runtime.onInstalled.addListener(() => {
    ensureInstallId().catch(() => { });
});

/**
 * Helper: get active tab (current window)
 */
async function getActiveTab() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs?.[0] || null;
}

/**
 * Helper: extract DOM HTML via on-demand injection (Option B)
 */
async function extractDomHtmlFromTab(tabId) {
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
            try {
                return {
                    url: location.href,
                    dom_html: document.documentElement?.outerHTML || ""
                };
            } catch (e) {
                return { url: location.href, dom_html: "" };
            }
        }
    });

    return result || { url: "", dom_html: "" };
}

/**
 * Helper: basic URL scheme guard
 */
function isRestrictedUrl(url) {
    if (!url) return true;
    return (
        url.startsWith("chrome://") ||
        url.startsWith("edge://") ||
        url.startsWith("about:") ||
        url.startsWith("file://")
    );
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
        try {
            /**
             * Existing: connect exchange
             */
            if (message?.type === "APPLYAI_EXTENSION_CONNECT" && message?.code) {
                const installId = await ensureInstallId();

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

                chrome.runtime.sendMessage({ type: "APPLYAI_EXTENSION_CONNECTED" }, () => {
                    void chrome.runtime.lastError;
                });

                sendResponse({ ok: true });
                return;
            }

            /**
             * New: Extract JD
             */
            if (message?.type === "APPLYAI_EXTRACT_JD") {
                // progress helper
                const progress = (stage) => {
                    chrome.runtime.sendMessage({ type: "APPLYAI_EXTRACT_JD_PROGRESS", stage }, () => {
                        void chrome.runtime.lastError;
                    });
                };

                progress("starting");

                const { extensionToken } = await storageGet(["extensionToken"]);
                if (!extensionToken) {
                    sendResponse({ ok: false, error: "Not connected. Please connect first." });
                    return;
                }

                const tab = await getActiveTab();
                if (!tab?.id) {
                    sendResponse({ ok: false, error: "No active tab found." });
                    return;
                }

                const tabUrl = tab.url || "";
                if (isRestrictedUrl(tabUrl)) {
                    sendResponse({ ok: false, error: "Cannot access this page." });
                    return;
                }

                progress("extracting_dom");

                let { url, dom_html } = await extractDomHtmlFromTab(tab.id);

                // fallback to tab.url if injection didn't return it
                if (!url) url = tabUrl;

                // size guard: if HTML is too large, drop it and let backend fallback to URL fetch
                const MAX_HTML_CHARS = 2_500_000; // ~2.5MB as characters; adjust later
                if (dom_html && dom_html.length > MAX_HTML_CHARS) {
                    dom_html = null;
                }

                progress("sending_to_backend");

                const ingestRes = await fetch(`${API_BASE_URL}/extension/jobs/ingest`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${extensionToken}`
                    },
                    body: JSON.stringify({
                        job_link: url,
                        dom_html: dom_html || null
                    })
                });

                if (ingestRes.status === 401) {
                    // token invalid/expired
                    await storageSet({ extensionToken: null });
                    sendResponse({ ok: false, error: "Session expired. Please connect again." });
                    return;
                }

                if (!ingestRes.ok) {
                    const text = await ingestRes.text().catch(() => "");
                    sendResponse({ ok: false, error: `Ingest failed: ${ingestRes.status} ${text}` });
                    return;
                }

                const ingestData = await ingestRes.json().catch(() => ({}));

                const jobTitle = ingestData?.job_title || null;
                const company = ingestData?.company || null;

                // persist last result (not used by popup now, but kept for debugging)
                await storageSet({
                    lastIngest: {
                        at: new Date().toISOString(),
                        url,
                        ok: true,
                        job_application_id: ingestData?.job_application_id || null,
                        job_title: jobTitle,
                        company
                    }
                });

                // notify popup (if open)
                chrome.runtime.sendMessage(
                    {
                        type: "APPLYAI_EXTRACT_JD_RESULT",
                        ok: true,
                        url,
                        job_application_id: ingestData?.job_application_id || null,
                        job_title: jobTitle,
                        company
                    },
                    () => void chrome.runtime.lastError
                );

                sendResponse({
                    ok: true,
                    job_application_id: ingestData?.job_application_id || null,
                    job_title: jobTitle,
                    company
                });
                return;
            }

            // default: ignore
            sendResponse({ ok: false, error: "Ignoring message (unknown type)." });
        } catch (err) {
            const msg = String(err?.message || err);

            // persist last failure (not used by popup now, but kept for debugging)
            try {
                await storageSet({
                    lastIngest: {
                        at: new Date().toISOString(),
                        ok: false,
                        reason: msg
                    }
                });
            } catch (_) { }

            chrome.runtime.sendMessage(
                { type: "APPLYAI_EXTRACT_JD_RESULT", ok: false, error: msg },
                () => void chrome.runtime.lastError
            );

            sendResponse({ ok: false, error: msg });
        }
    })();

    return true; // keep channel open for async sendResponse
});
