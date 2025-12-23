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

async function applyAutofillPlanToTab(tabId, planJson) {
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId },
        func: (plan) => {
            const cssEscape = (value) => {
                if (window.CSS && typeof window.CSS.escape === "function") {
                    return window.CSS.escape(value);
                }
                return String(value).replace(/"/g, '\\"');
            };

            const toBoolean = (value) => {
                if (typeof value === "boolean") return value;
                if (typeof value === "number") return value !== 0;
                if (typeof value === "string") {
                    const normalized = value.trim().toLowerCase();
                    if (["true", "yes", "y", "1"].includes(normalized)) return true;
                    if (["false", "no", "n", "0"].includes(normalized)) return false;
                }
                return Boolean(value);
            };

            const dispatchEvents = (el) => {
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
            };

            const selectOption = (el, value) => {
                const target = value == null ? "" : String(value);
                const options = Array.from(el.options || []);
                let match = options.find((opt) => opt.value === target);
                if (!match) {
                    match = options.find((opt) => (opt.textContent || "").trim().toLowerCase() === target.toLowerCase());
                }
                if (match) {
                    el.value = match.value;
                    dispatchEvents(el);
                    return true;
                }
                return false;
            };

            const fillTextInput = (el, value) => {
                if (value == null) return false;
                const tag = (el.tagName || "").toLowerCase();
                if (tag === "input" && (el.getAttribute("type") || "").toLowerCase() === "file") {
                    return false;
                }
                el.value = typeof value === "string" ? value : JSON.stringify(value);
                dispatchEvents(el);
                return true;
            };

            const fillRadioGroup = (nodes, value) => {
                if (value == null) return false;
                const target = String(value).trim().toLowerCase();
                let matched = false;
                for (const node of nodes) {
                    const nodeValue = (node.value || "").trim().toLowerCase();
                    if (nodeValue && nodeValue === target) {
                        node.checked = true;
                        dispatchEvents(node);
                        matched = true;
                        break;
                    }
                }
                return matched;
            };

            const fillCheckboxGroup = (nodes, value) => {
                if (!nodes.length) return false;
                if (Array.isArray(value)) {
                    let changed = false;
                    const normalized = value.map((v) => String(v).trim().toLowerCase());
                    for (const node of nodes) {
                        const nodeValue = (node.value || "").trim().toLowerCase();
                        const shouldCheck = normalized.includes(nodeValue);
                        node.checked = shouldCheck;
                        dispatchEvents(node);
                        changed = changed || shouldCheck;
                    }
                    return changed;
                }
                const shouldCheck = toBoolean(value);
                for (const node of nodes) {
                    node.checked = shouldCheck;
                    dispatchEvents(node);
                }
                return shouldCheck;
            };

            let filled = 0;
            let skipped = 0;
            const errors = [];

            const fields = Array.isArray(plan?.fields) ? plan.fields : [];
            for (const field of fields) {
                if (field?.action !== "autofill") {
                    skipped += 1;
                    continue;
                }

                const selector = field?.selector;
                if (!selector) {
                    skipped += 1;
                    continue;
                }

                const nameMatch = selector.match(/^\[name="(.+)"\]$/);
                let nodes = [];
                if (nameMatch) {
                    const name = cssEscape(nameMatch[1]);
                    nodes = Array.from(document.querySelectorAll(`[name="${name}"]`));
                } else {
                    const node = document.querySelector(selector);
                    if (node) nodes = [node];
                }

                if (!nodes.length) {
                    skipped += 1;
                    continue;
                }

                try {
                    const inputType = field?.input_type;
                    const value = field?.value;
                    let applied = false;

                    if (inputType === "select") {
                        applied = selectOption(nodes[0], value);
                    } else if (inputType === "radio") {
                        applied = fillRadioGroup(nodes, value);
                    } else if (inputType === "checkbox") {
                        applied = fillCheckboxGroup(nodes, value);
                    } else {
                        applied = fillTextInput(nodes[0], value);
                    }

                    if (applied) {
                        filled += 1;
                    } else {
                        skipped += 1;
                    }
                } catch (err) {
                    errors.push(String(err?.message || err));
                    skipped += 1;
                }
            }

            return { filled, skipped, errors };
        },
        args: [planJson]
    });

    return result || { filled: 0, skipped: 0, errors: [] };
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

            /**
             * New: Generate Autofill Plan + Apply
             */
            if (message?.type === "APPLYAI_AUTOFILL_PLAN") {
                const progress = (stage) => {
                    chrome.runtime.sendMessage({ type: "APPLYAI_AUTOFILL_PROGRESS", stage }, () => {
                        void chrome.runtime.lastError;
                    });
                };

                progress("starting");

                const { extensionToken, lastIngest } = await storageGet(["extensionToken", "lastIngest"]);
                if (!extensionToken) {
                    sendResponse({ ok: false, error: "Not connected. Please connect first." });
                    return;
                }

                const jobApplicationId = message?.job_application_id || lastIngest?.job_application_id;
                if (!jobApplicationId) {
                    sendResponse({ ok: false, error: "Missing job application ID. Extract a job description first." });
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
                if (!url) url = tabUrl;
                if (!dom_html) dom_html = "";

                const MAX_HTML_CHARS = 2_500_000;
                if (dom_html.length > MAX_HTML_CHARS) {
                    sendResponse({ ok: false, error: "Page is too large to process for autofill." });
                    return;
                }

                progress("planning");

                const planRes = await fetch(`${API_BASE_URL}/extension/autofill/plan`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${extensionToken}`
                    },
                    body: JSON.stringify({
                        job_application_id: jobApplicationId,
                        page_url: url,
                        dom_html
                    })
                });

                if (planRes.status === 401) {
                    await storageSet({ extensionToken: null });
                    sendResponse({ ok: false, error: "Session expired. Please connect again." });
                    return;
                }

                if (!planRes.ok) {
                    const text = await planRes.text().catch(() => "");
                    sendResponse({ ok: false, error: `Autofill plan failed: ${planRes.status} ${text}` });
                    return;
                }

                const planData = await planRes.json().catch(() => ({}));
                const planJson = planData?.plan_json;
                if (!planJson) {
                    sendResponse({ ok: false, error: "No autofill plan returned." });
                    return;
                }

                progress("autofilling");

                const applyResult = await applyAutofillPlanToTab(tab.id, planJson);

                chrome.runtime.sendMessage(
                    {
                        type: "APPLYAI_AUTOFILL_RESULT",
                        ok: true,
                        run_id: planData?.run_id || null,
                        plan_summary: planData?.plan_summary || null,
                        filled: applyResult?.filled || 0,
                        skipped: applyResult?.skipped || 0,
                        errors: applyResult?.errors || []
                    },
                    () => void chrome.runtime.lastError
                );

                sendResponse({
                    ok: true,
                    run_id: planData?.run_id || null,
                    filled: applyResult?.filled || 0,
                    skipped: applyResult?.skipped || 0
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

            const errorMessageType =
                message?.type === "APPLYAI_AUTOFILL_PLAN"
                    ? "APPLYAI_AUTOFILL_RESULT"
                    : "APPLYAI_EXTRACT_JD_RESULT";

            chrome.runtime.sendMessage(
                { type: errorMessageType, ok: false, error: msg },
                () => void chrome.runtime.lastError
            );

            sendResponse({ ok: false, error: msg });
        }
    })();

    return true; // keep channel open for async sendResponse
});
