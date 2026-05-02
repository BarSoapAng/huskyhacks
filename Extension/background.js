function connectToPython() {
    const socket = new WebSocket("ws://localhost:8765");

    socket.onopen = () => {
        console.log("Connected to Python Server");
        // Save connection status as true
        chrome.storage.local.set({ isConnected: true });
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // If Python sends a web_url, save it to local storage for the popup to use
        if (data.web_url) {
            chrome.storage.local.set({ web_url: data.web_url });
        }
        
        // If there's an action (block, timer, etc.), send it to the active tab
        if (data.action) {
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                if (tabs.length > 0) {
                    chrome.tabs.sendMessage(tabs[0].id, data);
                }
            });
        }
    };

    socket.onclose = () => {
        // Save connection status as false
        chrome.storage.local.set({ isConnected: false });
        setTimeout(connectToPython, 5000);
    };
}

connectToPython();