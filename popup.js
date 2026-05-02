// Wait for the user to click the button
document.getElementById("colorBtn").addEventListener("click", async () => {
    
  // Get the current active tab in the browser
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Execute a script on that specific tab
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    function: changePageBackgroundColor,
  });
});

// The function that actually changes the color
function changePageBackgroundColor() {
  // Generates a random hex color
  const randomColor = '#' + Math.floor(Math.random()*16777215).toString(16);
  
  // Changes the background of the webpage
  document.body.style.backgroundColor = randomColor;
}