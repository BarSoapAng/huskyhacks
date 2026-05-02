import { EXTENSION_PORT, WEB_URL } from './config.js';

const BACKEND_URL = `${EXTENSION_PORT}/health`;
const CHECK_URL = `${EXTENSION_PORT}/api/check-url`;

// Track recent tab sequence
let recentTabs = [];
const MAX_RECENT_TABS = 5;

// Filter function to skip extension URLs
function isValidWebUrl(url) {
    if (!url) return false;
    // Skip extension URLs, chrome URLs, and local file URLs
    const invalidPatterns = ['chrome://', 'chrome-extension://', 'about:', 'file://'];
    return !invalidPatterns.some(pattern => url.startsWith(pattern));
}

// Function to check URL and react
async function checkUrl(tabId, url) {
    // Skip checking extension and system URLs
    if (!isValidWebUrl(url)) {
        console.log(`Skipping non-web URL: ${url}`);
        return;
    }
    
    console.log(`[FocusBuddy] Checking URL: ${url}`);
    try {
        // Get tab title
        let pageTitle = "";
        try {
            const tab = await chrome.tabs.get(tabId);
            pageTitle = tab.title || "";
        } catch (err) {
            console.warn('Could not get tab info:', err);
        }

        // Build request body
        const requestBody = {
            url: url,
            pageTitle: pageTitle,
            recentTabSequence: recentTabs.slice(-MAX_RECENT_TABS),
            sessionDurationMinutes: 30, // You can track actual session time
            timeOfDay: new Date().toTimeString().slice(0, 5)
        };

        const response = await fetch(CHECK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`[FocusBuddy] Response for ${url}:`, data);

        // Update connection status and store last check result
        chrome.storage.local.set({
            isConnected: true,
            web_url: WEB_URL,
            lastCheckUrl: url,
            lastCheckResult: data,
            lastCheckTime: new Date().toLocaleTimeString()
        });
        console.log('[FocusBuddy] Storage updated with check result');

        // If action is not "allow", send message to content script
        if (data.action && data.action !== "allow") {
            try {
                chrome.tabs.sendMessage(tabId, {
                    action: data.action,
                    web_url: WEB_URL,
                    reason: data.reason,
                    procrastinationScore: data.procrastinationScore
                });
            } catch (err) {
                console.warn('Could not send message to content script:', err);
            }
        }
    } catch (error) {
        console.error('Error checking URL:', error);
        chrome.storage.local.set({ isConnected: false });
    }
}

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        console.log(`[FocusBuddy] Tab ${tabId} updated: ${tab.url}`);
        
        // Only process web URLs
        if (isValidWebUrl(tab.url)) {
            // Add to recent tabs
            if (!recentTabs.includes(tab.url)) {
                recentTabs.push(tab.url);
                if (recentTabs.length > MAX_RECENT_TABS) {
                    recentTabs.shift();
                }
            }

            // Check the URL
            checkUrl(tabId, tab.url);
        }
    }
});

// Also check when tab becomes active
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    try {
        const tab = await chrome.tabs.get(activeInfo.tabId);
        if (tab.url && isValidWebUrl(tab.url)) {
            console.log(`[FocusBuddy] Tab ${activeInfo.tabId} activated: ${tab.url}`);
            checkUrl(activeInfo.tabId, tab.url);
        }
    } catch (err) {
        console.warn('[FocusBuddy] Error handling tab activation:', err);
    }
});

// Listen for messages from content.js (e.g. if the user clicks "Close Tab" on a block prompt)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.closeTab && sender.tab) {
        chrome.tabs.remove(sender.tab.id);
    }
});