// Human Cache Web Push Service Worker
// Standards-compliant Push & NotificationClick event handling

self.addEventListener("push", (event) => {
  let data = {
    title: "Human Cache — Review Due",
    body: "A concept requires active reinforcement to maintain retention.",
    url: "/",
    icon: "/file.svg",
    badge: "/file.svg"
  };

  if (event.data) {
    try {
      data = { ...data, ...event.data.json() };
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || "/file.svg",
    badge: data.badge || "/file.svg",
    data: {
      url: data.url || "/",
      notification_id: data.notification_id || null,
      topic_id: data.topic_id || null
    },
    actions: [
      { action: "start", title: "Start Now" },
      { action: "dismiss", title: "Dismiss" }
    ],
    vibrate: [100, 50, 100],
    requireInteraction: true
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const notifData = event.notification.data || {};
  const targetUrl = notifData.url || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      // Focus existing window if open
      for (const client of clientList) {
        if (client.url && "focus" in client) {
          return client.focus();
        }
      }
      // Or open new window
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
