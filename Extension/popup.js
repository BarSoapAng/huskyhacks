import { EXTENSION_PORT, WEB_URL } from './config.js';

const BACKEND_URL = `${EXTENSION_PORT}/health`;

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
        if (storage.lastCheckUrl && storage.lastCheckResult) {
            const result = storage.lastCheckResult;
            
            // Populate the check result section
            document.getElementById("last-url").innerText = storage.lastCheckUrl;
            document.getElementById("action-result").innerText = result.action || 'N/A';
            document.getElementById("score-result").innerText = result.procrastinationScore !== null ? `${result.procrastinationScore}/100` : 'N/A';
            document.getElementById("reason-result").innerText = result.reason || 'No reason provided';
            document.getElementById("confidence-result").innerText = result.confidence !== null ? `${(result.confidence * 100).toFixed(1)}%` : 'N/A';
            
            // Set color based on action
            const actionEl = document.getElementById("action-result");
            if (result.action === 'hard_block') {
                actionEl.style.color = '#ea4335'; // Red
            } else if (result.action === 'soft_alert') {
                actionEl.style.color = '#f57c00'; // Orange
            } else {
                actionEl.style.color = '#0f9d58'; // Green
            }
            
            checkResultDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading check result:', error);
    }
}

updatePopup();

// Refresh data every 2 seconds
setInterval(updatePopup, 2000);