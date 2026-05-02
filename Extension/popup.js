import { EXTENSION_PORT, WEB_URL } from './config.js';

const BACKEND_URL = `${EXTENSION_PORT}/health`;
const MARK_UNPRODUCTIVE_URL = `${EXTENSION_PORT}/api/demo/mark-current-session-unproductive`;

async function updatePopup() {
    const statusText = document.getElementById("status-text");
    const statusDot = document.getElementById("status-dot");
    const statusContainer = document.getElementById("status-display");
    const dashboardLink = document.getElementById("dashboard-link");
    const checkResultDiv = document.getElementById("check-result");

    try {
        const response = await fetch(BACKEND_URL);
        
        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}`);
        }
        
        await response.json();

        dashboardLink.href = WEB_URL;
        statusText.innerText = "Connected!";
        statusContainer.style.color = "#0f9d58"; // Green
        statusDot.style.backgroundColor = "#0f9d58";
        
    } catch (error) {
        console.error('Status check failed:', error);
        dashboardLink.href = WEB_URL;
        statusText.innerText = "Disconnected";
        statusContainer.style.color = "#ea4335"; // Red
        statusDot.style.backgroundColor = "#ea4335";
    }
    
    // Load and display the last check URL result
    try {
        const storage = await chrome.storage.local.get(['lastCheckUrl', 'lastCheckResult']);
        console.log('[FocusBuddy Popup] Storage data:', storage);
        
        if (storage.lastCheckUrl && storage.lastCheckResult) {
            const result = storage.lastCheckResult;
            console.log('[FocusBuddy Popup] Displaying result:', result);
            
            // Populate the check result section
                document.getElementById("last-url").innerText = storage.lastCheckUrl;
            document.getElementById("action-result").innerText = result.action || 'N/A';
            document.getElementById("session-type-result").innerText = result.sessionType || 'N/A';
            document.getElementById("classification-result").innerText = result.classification || 'N/A';
            document.getElementById("reason-result").innerText = result.reason || 'No reason provided';
            document.getElementById("confidence-result").innerText =
                result.confidence != null
                    ? `${(result.confidence * 100).toFixed(1)}%`
                    : 'N/A';
            
            // Set color based on action
            const actionEl = document.getElementById("action-result");
            if (result.action === 'hard_ban') {
                actionEl.style.color = '#ea4335'; // Red
            } else if (result.action === 'ask_user') {
                actionEl.style.color = '#f57c00'; // Orange
            } else {
                actionEl.style.color = '#0f9d58'; // Green
            }
            
            checkResultDiv.style.display = 'block';
        } else {
            console.log('[FocusBuddy Popup] No check result yet - navigate to a web page');
            checkResultDiv.style.display = 'none';
        }
    } catch (error) {
        console.error('[FocusBuddy Popup] Error loading check result:', error);
    }
}

async function markCurrentSessionUnproductive() {
    const button = document.getElementById("mark-unproductive-button");
    const status = document.getElementById("mark-unproductive-status");

    button.disabled = true;
    status.classList.remove("error");
    status.innerText = "Marking session...";

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.url || !isWebUrl(tab.url)) {
            throw new Error("Open a web page before marking a session.");
        }

        const response = await fetch(MARK_UNPRODUCTIVE_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                url: tab.url,
                pageTitle: tab.title || "",
            }),
        });
        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(data?.message || `Backend returned ${response.status}`);
        }

        await chrome.storage.local.set({
            lastManualSessionResult: data,
            lastManualSessionTime: new Date().toLocaleTimeString(),
        });
        status.innerText = "Session marked as unproductive.";
    } catch (error) {
        console.error("[FocusBuddy Popup] Unable to mark session:", error);
        status.classList.add("error");
        status.innerText = "Unable to mark session.";
    } finally {
        button.disabled = false;
    }
}

function isWebUrl(url) {
    return /^https?:\/\//i.test(url);
}

updatePopup();

document
    .getElementById("mark-unproductive-button")
    .addEventListener("click", markCurrentSessionUnproductive);

// Refresh data every 2 seconds
setInterval(updatePopup, 2000);
