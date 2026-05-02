import { EXTENSION_PORT } from './config.js';

const BACKEND_URL = `${EXTENSION_PORT}/health`;
const POPUP_URL = `${EXTENSION_PORT}/check-url`;

async function checkBackendStatus() {
    try {
        const response = await fetch(POPUP_URL);
        const data = await response.json();

        // Save the Vite web URL and connection status
        chrome.storage.local.set({ 
            isConnected: true, 
            web_url: data.web_url 
        });

        // If the backend has a pending action (e.g., "block"), send it to the active tab
        if (data.action) {
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                if (tabs.length > 0) {
                    chrome.tabs.sendMessage(tabs[0].id, data);
                }
            });
        }
    } catch (error) {
        // If the fetch fails, the server is off
        chrome.storage.local.set({ isConnected: false });
    }
}

// Poll the backend every 2 seconds
setInterval(checkBackendStatus, 2000);
checkBackendStatus(); // Run once immediately

// Listen for messages from content.js (e.g. if the user clicks "Close Tab" on a block prompt)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.closeTab && sender.tab) {
        chrome.tabs.remove(sender.tab.id);
    }
});