async function hashDomain(domain) {
    const msgBuffer = new TextEncoder().encode(domain);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

const socket = new WebSocket('ws://localhost:9999');

async function processUrl(urlStr) {
    if (!urlStr || urlStr.startsWith('about:') || urlStr.startsWith('moz-extension:')) return;
    try {
        const url = new URL(urlStr);
        const domain = url.hostname; 
        const hashedContext = await hashDomain(domain);
        console.log("👀 User is looking at:", domain);
        console.log("🔒 Hashed to:", hashedContext);
        
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "web_context", hash: hashedContext }));
        }
    } catch (e) {}
}

chrome.tabs.onActivated.addListener((activeInfo) => {
    chrome.tabs.get(activeInfo.tabId, (tab) => {
        if (tab.url) processUrl(tab.url);
    });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.url) processUrl(changeInfo.url);
});
