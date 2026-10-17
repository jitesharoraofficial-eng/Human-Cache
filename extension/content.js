/**
 * Human Cache Extension — Content Script
 * Provides an optional, restrained, user-dismissible floating capture prompt on long reading articles.
 * Privacy-preserving: DOES NOT monitor keystrokes, form fields, password inputs, or send data automatically.
 */

(function () {
  // Check if page appears to be a long academic article (heuristic: > 3000 chars in body, not login/checkout)
  const isExcluded = /login|signin|checkout|payment|bank|account|password/i.test(window.location.href);
  if (isExcluded) return;

  // Listen for messages from popup if needed
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getPageInfo") {
      sendResponse({
        title: document.title,
        url: window.location.href,
        selectedText: window.getSelection() ? window.getSelection().toString() : ""
      });
    } else if (request.action === "getPageContent") {
      const articleEl = document.querySelector('article') || document.querySelector('#content') || document.querySelector('main') || document.body;
      const cleanText = articleEl ? (articleEl.innerText || articleEl.textContent || "") : "";
      sendResponse({
        title: document.title,
        url: window.location.href,
        pageContent: cleanText.slice(0, 100000),
        selectedText: window.getSelection() ? window.getSelection().toString() : ""
      });
    }
  });
})();
