// Retrieve the saved data from Chrome's local storage
chrome.storage.local.get(["web_url", "isConnected"], (data) => {
    
    // 1. Update the Web URL link
    const dashboardLink = document.getElementById("dashboard-link");
    if (data.web_url) {
        dashboardLink.href = data.web_url;
    } else {
        // Fallback just in case the server hasn't sent a URL yet
        dashboardLink.href = "https://google.com"; 
    }

    // 2. Update the status indicator (Optional, but good for debugging!)
    const statusText = document.getElementById("status-text");
    const statusDot = document.getElementById("status-dot");
    const statusContainer = document.getElementById("status-display");

    if (data.isConnected) {
        statusText.innerText = "Connected!";
        statusContainer.style.color = "#0f9d58"; // Green
        statusDot.style.backgroundColor = "#0f9d58";
    } else {
        statusText.innerText = "Disconnected";
        statusContainer.style.color = "#ea4335"; // Red
        statusDot.style.backgroundColor = "#ea4335";
    }
});