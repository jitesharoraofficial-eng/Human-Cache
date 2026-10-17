/**
 * Human Cache Extension — Background Service Worker (Manifest V3)
 * Handles context menu creation, selected text capture, and communication with backend.
 */

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";

// Helper to retrieve configurable API base URL
async function getApiBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["humancache_api_url"], (result) => {
      let url = result.humancache_api_url || DEFAULT_API_BASE_URL;
      // Strip trailing slashes
      url = url.replace(/\/+$/, "");
      if (!url.endsWith("/api/v1")) {
        url = `${url}/api/v1`;
      }
      resolve(url);
    });
  });
}

// 1. Create Context Menu item on extension install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-to-human-cache",
    title: "Save to Human Cache",
    contexts: ["selection", "page", "link"]
  });
});

// 2. Handle Context Menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "save-to-human-cache") {
    const sessionToken = await getStoredSessionToken();
    if (!sessionToken) {
      try {
        if (chrome.action && typeof chrome.action.openPopup === "function") {
          await chrome.action.openPopup();
        } else {
          notifyUser("Sign In Required", "Please click the Human Cache extension icon to log in.");
        }
      } catch {
        notifyUser("Sign In Required", "Please click the Human Cache extension icon to log in.");
      }
      return;
    }

    if (info.selectionText) {
      // Capture selection
      await sendCaptureToBackend({
        endpoint: "/capture/text",
        payload: {
          content_text: info.selectionText,
          title: tab?.title ? `Excerpt: ${tab.title}` : "Web Selection",
          source_type: "extension",
          source_url: tab?.url || info.pageUrl
        },
        sessionToken
      });
    } else if (info.linkUrl) {
      // Capture linked URL
      await sendCaptureToBackend({
        endpoint: "/capture/url",
        payload: {
          url: info.linkUrl,
          source_type: "extension"
        },
        sessionToken
      });
    } else if (tab?.url) {
      // Capture active page URL
      await sendCaptureToBackend({
        endpoint: "/capture/url",
        payload: {
          url: tab.url,
          source_type: "extension"
        },
        sessionToken
      });
    }
  }
});

// 3. Helper to retrieve stored session token from chrome.storage.local
async function getStoredSessionToken() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["humancache_token"], (result) => {
      resolve(result.humancache_token || null);
    });
  });
}

function notifyUser(title, message) {
  try {
    chrome.notifications?.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: title,
      message: message
    });
  } catch (err) {
    console.warn("Could not display Chrome notification:", err);
  }
}

// 4. Send capture to backend API
async function sendCaptureToBackend({ endpoint, payload, sessionToken }) {
  try {
    const apiBase = await getApiBaseUrl();
    const res = await fetch(`${apiBase}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${sessionToken}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      notifyUser(
        "Saved to Human Cache Inbox",
        `"${data.title || 'Resource'}" is ready in your Capture Inbox with AI category suggestion.`
      );
    } else {
      let errMsg = `Server returned HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errMsg = errJson.detail;
      } catch {
        // ignore parse error
      }
      notifyUser("Capture Failed", errMsg);
    }
  } catch (err) {
    console.error("Capture network request failed:", err);
    notifyUser("Network Error", "Could not reach Human Cache backend. Is the server running?");
  }
}
