import { spawn } from "child_process";
import fs from "fs";
import path from "path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USER_DATA_DIR = path.resolve("./scratch_chrome_test");

if (fs.existsSync(USER_DATA_DIR)) {
  fs.rmSync(USER_DATA_DIR, { recursive: true, force: true });
}
fs.mkdirSync(USER_DATA_DIR, { recursive: true });

const chrome = spawn(CHROME_PATH, [
  "--headless=new",
  "--remote-debugging-port=9223",
  `--user-data-dir=${USER_DATA_DIR}`,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-gpu",
  "about:blank"
], { stdio: "ignore" });

await new Promise(r => setTimeout(r, 2000));

async function getWsUrl() {
  const res = await fetch("http://127.0.0.1:9223/json");
  const pages = await res.json();
  return pages[0].webSocketDebuggerUrl;
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
  }

  async init() {
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
      this.ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        if (data.id && this.pending.has(data.id)) {
          const { resolve, reject } = this.pending.get(data.id);
          this.pending.delete(data.id);
          if (data.error) reject(data.error);
          else resolve(data.result);
        }
      };
    });
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expr) {
    const res = await this.send("Runtime.evaluate", {
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (res.exceptionDetails) {
      console.error("Exception:", res.exceptionDetails);
    }
    return res.result?.value;
  }

  async close() {
    this.ws.close();
  }
}

try {
  const wsUrl = await getWsUrl();
  const client = new CDPClient(wsUrl);
  await client.init();
  await client.send("Page.enable");
  await client.send("Runtime.enable");

  console.log("Navigating to http://localhost:3000 ...");
  await client.send("Page.navigate", { url: "http://localhost:3000" });
  await new Promise(r => setTimeout(r, 3500));

  const pageHtml = await client.eval("document.body.innerText");
  console.log("PAGE TEXT PREVIEW:\n", pageHtml ? pageHtml.substring(0, 400) : "EMPTY");

  // Check login buttons
  const buttons = await client.eval(`Array.from(document.querySelectorAll('button')).map(b => b.innerText)`);
  console.log("BUTTONS FOUND:", buttons);

  await client.close();
} catch (e) {
  console.error("ERROR:", e);
} finally {
  chrome.kill();
  try { fs.rmSync(USER_DATA_DIR, { recursive: true, force: true }); } catch {}
}
