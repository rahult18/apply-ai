// Listen for messages from the web page
window.addEventListener("message", (event) => {
    // Only accept messages from the same origin as the page
    if (event.origin !== window.location.origin) return;

    if (event.data?.type === "APPLYAI_EXTENSION_CONNECT" && event.data?.code) {
        console.log("[ApplyAI ext] Received one-time code from page, forwarding to extension.");
        // Forward the message to the extension's background script
        chrome.runtime.sendMessage(event.data, (resp) => {
            if (chrome.runtime.lastError) {
                console.error("[ApplyAI ext] sendMessage error:", chrome.runtime.lastError.message);
                return;
            }
            console.log("[ApplyAI ext] Background response:", resp);
        });
    }
});
