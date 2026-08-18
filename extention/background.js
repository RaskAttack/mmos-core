// Function to hash the domain using SHA-256
async function hashDomain(domain) {
    const msgBuffer = new TextEncoder().encode(domain);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// Connect to the future local Linux daemon
const socket = new WebSocket('ws://localhost:9999');

// Listen for when the user switches tabs
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    chrome.tabs.get(activeInfo.tabId, async (tab) => {
        if (tab.url) {
            const url = new URL(tab.url);
            const domain = url.hostname; // e.g., "github.com"
            
            const hashedContext = await hashDomain(domain);
            console.log("User is looking at:", domain, "-> Hash:", hashedContext);
            
            // Send the hash to the local MMOS daemon
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: "web_context", hash: hashedContext }));
            }
        }
    });
});
