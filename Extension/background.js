function connectToPython() {
    const socket = new WebSocket("ws://localhost:8765");

    socket.onopen = () => console.log("Connected to Python Server");

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Find the active tab and send the data to it
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            if (tabs.length > 0) {
                chrome.tabs.sendMessage(tabs[0].id, data);
            }
        });
    };

    // If the connection drops, try to reconnect after 5 seconds
    socket.onclose = () => {
        setTimeout(connectToPython, 5000);
    };
}

connectToPython();