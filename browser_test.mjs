import { spawn } from "child_process";
import fs from "fs";
import path from "path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USER_DATA_DIR = path.resolve("./scratch_chrome_profile");

if (fs.existsSync(USER_DATA_DIR)) {
  fs.rmSync(USER_DATA_DIR, { recursive: true, force: true });
}
fs.mkdirSync(USER_DATA_DIR, { recursive: true });

console.log("Starting Headless Chrome on port 9222...");
const chrome = spawn(CHROME_PATH, [
  "--headless=new",
  "--remote-debugging-port=9222",
  `--user-data-dir=${USER_DATA_DIR}`,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-gpu",
  "about:blank"
], { stdio: "ignore" });

// Wait for Chrome to be ready
await new Promise(r => setTimeout(r, 2000));

async function getWsUrl() {
  const res = await fetch("http://127.0.0.1:9222/json");
  const pages = await res.json();
  return pages[0].webSocketDebuggerUrl;
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
    this.events = new Map();
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
      console.error("Evaluation Exception:", res.exceptionDetails);
    }
    return res.result?.value !== undefined ? res.result.value : res;
  }

  async close() {
    this.ws.close();
  }
}

try {
  const wsUrl = await getWsUrl();
  console.log("Connected to CDP:", wsUrl);
  const client = new CDPClient(wsUrl);
  await client.init();
  await client.send("Page.enable");
  await client.send("Runtime.enable");

  console.log("Navigating to http://localhost:3000 ...");
  await client.send("Page.navigate", { url: "http://localhost:3000" });
  await new Promise(r => setTimeout(r, 3000));

  console.log("Checking page title and state...");
  const pageTitle = await client.eval("document.title");
  console.log("Page Title:", pageTitle);

  // Run comprehensive browser test scenarios
  const testResults = await client.eval(`(async () => {
    const results = [];
    
    // Scenario 1: Verify Registration & B.Com Onboarding in Real Browser
    console.log("Testing B.Com Learner flow...");
    const uid = Math.random().toString(36).substring(2, 7);
    const bcomEmail = "jitesh_browser_" + uid + "@example.com";
    
    // 1. Register via API from browser context
    const regRes = await fetch("http://127.0.0.1:8000/api/v1/auth/register", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: bcomEmail,
        password: "password123",
        name: "Jitesh Sharma"
      })
    });
    const regData = await regRes.json();
    results.push({ test: "Registration", status: regRes.ok ? "PASS" : "FAIL" });

    // 2. Submit B.Com Onboarding preferences
    const onboardRes = await fetch("http://127.0.0.1:8000/api/v1/users/preferences", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_roles: ["college_student"],
        learning_goals_list: ["commerce_business"],
        learning_goals: "Business, Finance & Entrepreneurship",
        target_exam: "",
        learning_context: {
          college_degree: "B.Com",
          college_field: "Business Management"
        },
        subjects_of_interest: ["Business Studies & Management", "Accountancy & Bookkeeping"],
        onboarding_completed: true
      })
    });
    results.push({ test: "B.Com Onboarding PUT", status: onboardRes.ok ? "PASS" : "FAIL" });

    // 3. Fetch dashboard overview as this user
    const dashRes = await fetch("http://127.0.0.1:8000/api/v1/dashboard/overview", {
      credentials: "include"
    });
    const dashData = await dashRes.json();
    
    const bcomPass = dashData.welcome_name === "Jitesh" &&
                     dashData.daily_study_focus === "Business Management & Commerce" &&
                     !dashData.daily_study_focus.includes("JEE") &&
                     !dashData.daily_study_focus.includes("High-Yield");
    results.push({
      test: "B.Com Dashboard Greeting & Cognitive Focus",
      status: bcomPass ? "PASS" : "FAIL",
      welcome_name: dashData.welcome_name,
      focus: dashData.daily_study_focus,
      prompt: dashData.cognitive_focus_prompt
    });

    // Scenario 2: JEE Learner
    const jeeEmail = "rohit_jee_browser_" + uid + "@example.com";
    await fetch("http://127.0.0.1:8000/api/v1/auth/register", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: jeeEmail,
        password: "password123",
        name: "Rohit Kumar"
      })
    });
    await fetch("http://127.0.0.1:8000/api/v1/users/preferences", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_roles: ["competitive_aspirant"],
        learning_goals_list: ["competitive_exam"],
        target_exam: "JEE Advanced & Main",
        onboarding_completed: true
      })
    });
    const jeeDash = await (await fetch("http://127.0.0.1:8000/api/v1/dashboard/overview", { credentials: "include" })).json();
    results.push({
      test: "JEE Dashboard Focus",
      status: (jeeDash.welcome_name === "Rohit" && jeeDash.daily_study_focus === "JEE Main & Advanced") ? "PASS" : "FAIL",
      welcome_name: jeeDash.welcome_name,
      focus: jeeDash.daily_study_focus,
      prompt: jeeDash.cognitive_focus_prompt
    });

    // Scenario 3: Law Learner
    const lawEmail = "kavita_law_browser_" + uid + "@example.com";
    await fetch("http://127.0.0.1:8000/api/v1/auth/register", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: lawEmail,
        password: "password123",
        name: "Kavita Rao"
      })
    });
    await fetch("http://127.0.0.1:8000/api/v1/users/preferences", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_roles: ["college_student"],
        learning_goals_list: ["college_university"],
        learning_context: { college_degree: "LL.B", college_field: "Constitutional Law" },
        onboarding_completed: true
      })
    });
    const lawDash = await (await fetch("http://127.0.0.1:8000/api/v1/dashboard/overview", { credentials: "include" })).json();
    results.push({
      test: "Law Dashboard Focus",
      status: (lawDash.welcome_name === "Kavita" && lawDash.daily_study_focus === "Legal Studies") ? "PASS" : "FAIL",
      welcome_name: lawDash.welcome_name,
      focus: lawDash.daily_study_focus,
      prompt: lawDash.cognitive_focus_prompt
    });

    // Scenario 4: User Profile Preference Update (from Law to Arts/History)
    await fetch("http://127.0.0.1:8000/api/v1/users/preferences", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_roles: ["college_student"],
        learning_goals_list: ["creative_arts"],
        learning_context: { college_degree: "B.A. History", college_field: "Modern History" },
        onboarding_completed: true
      })
    });
    const updatedDash = await (await fetch("http://127.0.0.1:8000/api/v1/dashboard/overview", { credentials: "include" })).json();
    results.push({
      test: "Profile Settings Update Reflection",
      status: updatedDash.daily_study_focus === "History & Humanities" ? "PASS" : "FAIL",
      focus: updatedDash.daily_study_focus
    });

    // Scenario 5: User Isolation (Re-login as B.Com user, verify isolation from Law user)
    await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: bcomEmail, password: "password123" })
    });
    const reDash = await (await fetch("http://127.0.0.1:8000/api/v1/dashboard/overview", { credentials: "include" })).json();
    results.push({
      test: "Cross-User Isolation on Account Switch",
      status: (reDash.welcome_name === "Jitesh" && reDash.daily_study_focus === "Business Management & Commerce") ? "PASS" : "FAIL",
      welcome_name: reDash.welcome_name,
      focus: reDash.daily_study_focus
    });

    return results;
  })()`);

  console.log("\n=======================================================");
  console.log("       REAL BROWSER AUTOMATION TEST RESULTS            ");
  console.log("=======================================================");
  console.log(JSON.stringify(testResults, null, 2));

  await client.close();
} catch (err) {
  console.error("Test execution error:", err);
} finally {
  chrome.kill();
  if (fs.existsSync(USER_DATA_DIR)) {
    try { fs.rmSync(USER_DATA_DIR, { recursive: true, force: true }); } catch {}
  }
}
