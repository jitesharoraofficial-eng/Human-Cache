const DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", async () => {
  const statusDot = document.getElementById("statusDot");
  const statusLabel = document.getElementById("statusLabel");
  const pageTitleInput = document.getElementById("pageTitle");
  const pageUrlInput = document.getElementById("pageUrl");
  const btnCapture = document.getElementById("btnCaptureCurrentPage");
  const btnOpenWebApp = document.getElementById("btnOpenWebApp");
  const captureForm = document.getElementById("captureForm");
  const authBox = document.getElementById("authBox");
  const btnLogin = document.getElementById("btnLogin");
  const authEmail = document.getElementById("authEmail");
  const authPassword = document.getElementById("authPassword");
  const alertBox = document.getElementById("alertBox");

  const btnToggleSettings = document.getElementById("btnToggleSettings");
  const settingsPanel = document.getElementById("settingsPanel");
  const settingApiUrl = document.getElementById("settingApiUrl");
  const btnSaveSettings = document.getElementById("btnSaveSettings");

  function showAlert(msg, isSuccess = true) {
    alertBox.style.display = "block";
    alertBox.className = `alert ${isSuccess ? "alert-success" : "alert-error"}`;
    alertBox.textContent = msg;
    setTimeout(() => {
      alertBox.style.display = "none";
    }, 4000);
  }

  // Load backend URL configuration
  let backendOrigin = await getStoredBackendOrigin();
  settingApiUrl.value = backendOrigin;

  function getApiBase() {
    return `${backendOrigin}/api/v1`;
  }

  // Settings toggle
  btnToggleSettings?.addEventListener("click", () => {
    const isVisible = settingsPanel.style.display === "block";
    settingsPanel.style.display = isVisible ? "none" : "block";
  });

  // Save Settings
  btnSaveSettings?.addEventListener("click", async () => {
    let raw = settingApiUrl.value.trim() || DEFAULT_BACKEND_ORIGIN;
    raw = raw.replace(/\/+$/, "");
    if (raw.endsWith("/api/v1")) {
      raw = raw.replace(/\/api\/v1$/, "");
    }
    await setStoredBackendOrigin(raw);
    backendOrigin = raw;
    showAlert("Settings saved! Re-checking connection...");
    settingsPanel.style.display = "none";
    await checkConnectivity();
  });

  // 1. Get active tab info
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0]) {
      pageTitleInput.value = tabs[0].title || "Web Resource";
      pageUrlInput.value = tabs[0].url || "";
    }
  });

  // 2. Check token in storage & connection
  let token = await getStoredToken();
  await checkConnectivity();

  async function checkConnectivity() {
    try {
      const healthRes = await fetch(`${backendOrigin}/health`);
      if (healthRes.ok) {
        if (token) {
          const meRes = await fetch(`${getApiBase()}/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
          });
          if (meRes.ok) {
            const user = await meRes.json();
            statusDot.className = "status-dot";
            statusLabel.textContent = `Connected as ${user.email}`;
            captureForm.style.display = "block";
            authBox.style.display = "none";
          } else {
            showLoginState();
          }
        } else {
          showLoginState();
        }
      } else {
        showOfflineState();
      }
    } catch {
      showOfflineState();
    }
  }

  function showOfflineState() {
    statusDot.className = "status-dot offline";
    statusLabel.textContent = `Backend offline (${backendOrigin})`;
  }

  function showLoginState() {
    statusDot.className = "status-dot";
    statusLabel.textContent = "Please log in to Human Cache";
    captureForm.style.display = "none";
    authBox.style.display = "block";
  }

  // Handle Login
  btnLogin?.addEventListener("click", async () => {
    const email = authEmail.value.trim();
    const password = authPassword.value;
    if (!email || !password) return;

    try {
      const res = await fetch(`${getApiBase()}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.session_token) {
          await setStoredToken(data.session_token);
          token = data.session_token;
          showAlert("Logged in successfully!");
          statusDot.className = "status-dot";
          statusLabel.textContent = `Connected as ${data.user.email}`;
          captureForm.style.display = "block";
          authBox.style.display = "none";
        }
      } else {
        showAlert("Invalid email or password", false);
      }
    } catch {
      showAlert("Login failed: could not connect to backend", false);
    }
  });

  // Handle Capture Current Page
  btnCapture?.addEventListener("click", async () => {
    const url = pageUrlInput.value;
    if (!url) return;

    btnCapture.disabled = true;
    btnCapture.textContent = "Analyzing & Saving...";

    try {
      let pageContent = "";
      let pageTitle = pageTitleInput.value || "";

      // Try to obtain rendered text directly from content script in active tab
      try {
        const tabs = await new Promise((resolve) => chrome.tabs.query({ active: true, currentWindow: true }, resolve));
        if (tabs && tabs[0]?.id) {
          const tabRes = await new Promise((resolve) => {
            chrome.tabs.sendMessage(tabs[0].id, { action: "getPageContent" }, (resp) => {
              if (chrome.runtime.lastError || !resp) {
                resolve(null);
              } else {
                resolve(resp);
              }
            });
          });
          if (tabRes) {
            if (tabRes.pageContent) pageContent = tabRes.pageContent;
            if (tabRes.title) pageTitle = tabRes.title;
          }
        }
      } catch (e) {
        // Tab message not available
      }

      const res = await fetch(`${getApiBase()}/capture/url`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          url,
          source_type: "extension",
          title: pageTitle,
          page_content: pageContent
        })
      });

      if (res.ok) {
        const data = await res.json();
        showAlert(`Saved to Inbox! Suggested: "${data.recommended_category_name}"`);
      } else {
        const err = await res.json();
        showAlert(err.detail || "Capture failed", false);
      }
    } catch {
      showAlert("Error saving capture", false);
    } finally {
      btnCapture.disabled = false;
      btnCapture.textContent = "⚡ Save Page to Human Cache";
    }
  });

  btnOpenWebApp?.addEventListener("click", () => {
    chrome.tabs.create({ url: "http://localhost:3000" });
  });

  async function getStoredToken() {
    return new Promise((resolve) => {
      chrome.storage.local.get(["humancache_token"], (r) => {
        resolve(r.humancache_token || null);
      });
    });
  }

  async function setStoredToken(t) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ humancache_token: t }, resolve);
    });
  }

  async function getStoredBackendOrigin() {
    return new Promise((resolve) => {
      chrome.storage.local.get(["humancache_api_url"], (r) => {
        resolve(r.humancache_api_url || DEFAULT_BACKEND_ORIGIN);
      });
    });
  }

  async function setStoredBackendOrigin(origin) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ humancache_api_url: origin }, resolve);
    });
  }
});
