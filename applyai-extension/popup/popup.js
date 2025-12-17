// Change this if your Next.js dev server uses a different port.
const APP_BASE_URL = "http://localhost:3000";

document.addEventListener("DOMContentLoaded", () => {
    const connectBtn = document.getElementById("connectBtn");

    connectBtn.addEventListener("click", async () => {
        const url = `${APP_BASE_URL}/extension/connect`;
        chrome.tabs.create({ url });
        window.close();
    });
});
