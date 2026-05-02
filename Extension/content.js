// Listen for messages from background.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    showPopup(request.action, request.web_url);
});

function showPopup(action, web_url) {
    // 1. Remove existing popups to prevent duplicates
    const existing = document.getElementById("focus-buddy-overlay");
    if (existing) existing.remove();

    // 2. Define text and styles based on the action
    let title = "";
    let message = "";
    let buttonText = "";
    let isBlocking = false;

    if (action === "block") {
        title = "Time to Focus";
        message = "This tab has been blocked. Let's get back to work!";
        buttonText = "Close Tab";
        isBlocking = true;
    } else if (action === "timer") {
        title = "Taking a break?";
        message = "This looks like a break. Would you like to start a 5-minute timer?";
        buttonText = "Start Timer";
    } else if (action === "procrastinate") {
        title = "Are you procrastinating?";
        message = "You've been scrolling for a while. Is this productive?";
        buttonText = "Back to Work";
    }

    // 3. Create the UI Overlay
    const overlay = document.createElement("div");
    overlay.id = "focus-buddy-overlay";
    
    // CSS to dim the background. If "blocking", it's opaque. If just a prompt, it's slightly transparent.
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: ${isBlocking ? 'rgba(255,255,255,0.95)' : 'rgba(0,0,0,0.4)'};
        backdrop-filter: blur(4px);
        display: flex; align-items: center; justify-content: center;
        z-index: 2147483647; /* Maximum z-index to stay on top */
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    `;

    // 4. Create the Card (Google Style)
    const card = document.createElement("div");
    card.style.cssText = `
        background: white; padding: 30px; border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15); width: 350px;
        text-align: center; display: flex; flex-direction: column; gap: 15px;
        color: #202124;
    `;

    // Inner HTML of the card
    card.innerHTML = `
        <h2 style="margin: 0; font-size: 22px; font-weight: 500;">${title}</h2>
        <p style="margin: 0; font-size: 14px; color: #5f6368; line-height: 1.5;">${message}</p>
        
        <button id="fb-action-btn" style="
            background: #1a73e8; color: white; border: none; 
            padding: 10px 20px; border-radius: 8px; font-weight: 600; 
            cursor: pointer; margin-top: 10px; font-size: 14px; transition: 0.2s;">
            ${buttonText}
        </button>

        <hr style="border: 0; border-top: 1px solid #e8eaed; width: 100%; margin: 10px 0;">
        
        <!-- The Web URL Link / Icon -->
        <a href="${web_url}" target="_blank" style="
            text-decoration: none; color: #1a73e8; font-size: 13px; font-weight: 500;
            display: flex; align-items: center; justify-content: center; gap: 5px;">
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
            Open Dashboard
        </a>
        
        ${!isBlocking ? `<span id="fb-dismiss" style="color: #5f6368; font-size: 12px; cursor: pointer; margin-top: 5px;">Dismiss</span>` : ''}
    `;

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    // 5. Add Button Functionality
    document.getElementById("fb-action-btn").addEventListener("click", () => {
        if (action === "block") {
            // Closes the current tab
            chrome.runtime.sendMessage({ closeTab: true }); 
            window.close(); // Fallback
        } else {
            // Logic for starting a timer goes here
            overlay.remove();
        }
    });

    // Hover effect for the main button
    document.getElementById("fb-action-btn").addEventListener("mouseover", function() { this.style.background = "#1557b0"; });
    document.getElementById("fb-action-btn").addEventListener("mouseout", function() { this.style.background = "#1a73e8"; });

    // Dismiss button for non-blocking prompts
    if (!isBlocking) {
        document.getElementById("fb-dismiss").addEventListener("click", () => overlay.remove());
    }
}