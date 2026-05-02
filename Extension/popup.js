import { EXTENSION_PORT } from './config.js';

const BACKEND_URL = `${EXTENSION_PORT}/status`;

async function updatePopup() {
    const statusText = document.getElementById("status-text");
    const statusDot = document.getElementById("status-dot");
    const statusContainer = document.getElementById("status-display");
    const dashboardLink = document.getElementById("dashboard-link");

    try {
        const response = await fetch(BACKEND_URL);
        const data = await response.json();

        dashboardLink.href = data.web_url;
        statusText.innerText = "Connected!";
        statusContainer.style.color = "#0f9d58"; // Green
        statusDot.style.backgroundColor = "#0f9d58";
        
    } catch (error) {
        dashboardLink.href = "#"; 
        statusText.innerText = "Disconnected";
        statusContainer.style.color = "#ea4335"; // Red
        statusDot.style.backgroundColor = "#ea4335";
    }
}

updatePopup();