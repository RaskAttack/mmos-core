const SERVER_URL = "https://mmos.retrotechspecs.com/context";

async function sendDomainToServer(domain) {
    try {
        const response = await fetch(SERVER_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            // Sending the clean domain exactly as requested
            body: JSON.stringify({ domain: domain })
        });
        console.log("✅ Sent context to MMOS Server:", domain);
    } catch (error) {
        console.log("❌ Server not reached. Is it online?", error);
    }
}

function processUrl(urlStr) {
    if (!urlStr || urlStr.startsWith('about:') || urlStr.startsWith('moz-extension:')) return;
    try {
        const url = new URL(urlStr);
        const cleanDomain = url.hostname; 
        sendDomainToServer(cleanDomain);
    } catch (e) {}
}

// Listens for switching between open tabs
chrome.tabs.onActivated.addListener((activeInfo) => {
    chrome.tabs.get(activeInfo.tabId, (tab) => {
        if (tab.url) processUrl(tab.url);
    });
});

// Listens for a tab loading a new website
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.url) processUrl(changeInfo.url);
});
