/*************************************************
 * 🔒 HARD CLICK BLOCK (FINAL FIX)
 * Prevent ANY navigation from dashboard buttons
 *************************************************/
document.addEventListener(
    "click",
    function (e) {
        const btn = e.target.closest("button");
        if (!btn) return;

        // dashboard buttons only
        if (btn.classList.contains("btn")) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    },
    true // 👈 CAPTURE PHASE (VERY IMPORTANT)
);

/************************
 * CONFIG
 ************************/
const API_BASE = "http://127.0.0.1:8000/api";
const WS_URL = "ws://127.0.0.1:8000/ws/dashboard";

/************************
 * USERS
 ************************/
const users = [
    { username: "1111", password: "1111", location: "Modan", role: "operator" },
    { username: "2222", password: "2222", location: "Baldeya", role: "operator" },
    { username: "3333", password: "3333", location: "Al-Khraj", role: "operator" },
    { username: "Admin", password: "12345", location: "all", role: "admin" }
];

let currentUser = null;
let socket = null;

/************************
 * 🔒 GLOBAL SAFETY (FIXES RELOAD ISSUE)
 ************************/
document.addEventListener("submit", e => {
    if (e.target.id !== "login-form") {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }
});

/************************
 * LOGIN
 ************************/
document.getElementById("login-form").addEventListener("submit", e => {
    e.preventDefault();

    const u = document.getElementById("username").value.trim();
    const p = document.getElementById("password").value.trim();

    const user = users.find(x => x.username === u && x.password === p);
    if (!user) {
        alert("Invalid login");
        return;
    }

    currentUser = user;

    document.getElementById("login-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.remove("hidden");

    initWebSocket();
    loadDashboard();
});

/************************
 * WEBSOCKET (SAFE SINGLE INSTANCE)
 ************************/
function initWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) return;

    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("✅ WebSocket connected");
        socket.send("ready");
    };

    socket.onmessage = e => {
        try {
            renderDashboard(JSON.parse(e.data));
        } catch (err) {
            console.error("WS data error", err);
        }
    };

    socket.onclose = () => {
        console.log("❌ WebSocket closed, retrying...");
        socket = null;
        setTimeout(initWebSocket, 3000);
    };

    socket.onerror = err => {
        console.error("WebSocket error", err);
        socket.close();
    };
}

/************************
 * HTTP BACKUP
 ************************/
async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        renderDashboard(await res.json());
    } catch {
        console.error("Backend not reachable");
    }
}

/************************
 * RENDER DASHBOARD
 ************************/
function renderDashboard(data) {
    const container = document.getElementById("locations");
    container.innerHTML = "";

    const locations =
        currentUser.location === "all"
            ? Object.keys(data)
            : [currentUser.location];

    locations.forEach(loc => {
        if (data[loc]) renderLocation(loc, data[loc]);
    });
}

function renderLocation(location, machines) {
    const wrap = document.createElement("div");
    wrap.className = "location-card";
    wrap.innerHTML = `<h2>${location}</h2><div class="machines-grid"></div>`;
    document.getElementById("locations").appendChild(wrap);

    const grid = wrap.querySelector(".machines-grid");

    machines.forEach(m => {
        const card = document.createElement("div");
        card.className = `machine-card status-${m.status}`;

        card.innerHTML = `
            <h3>${m.name}</h3>
            <p>Status: <b>${m.status.toUpperCase()}</b></p>

            <div class="job-card">
                <p>Target: ${m.target}</p>
                <p>Produced: ${m.produced}</p>
                <p>Remaining: ${m.remaining}</p>
            </div>

            ${
                currentUser.role === "operator"
                    ? `
            <div class="controls">
                <button type="button" class="btn start"
                    onclick="machineAction(event,'start','${location}',${m.id})">▶ Start</button>
                <button type="button" class="btn pause"
                    onclick="machineAction(event,'pause','${location}',${m.id})">⏸ Pause</button>
                <button type="button" class="btn stop"
                    onclick="machineAction(event,'stop','${location}',${m.id})">⛔ Stop</button>
            </div>`
                    : ""
            }
        `;
        grid.appendChild(card);
    });
}

/************************
 * MACHINE ACTION (SAFE)
 ************************/
async function machineAction(e, action, location, id) {
    e.preventDefault();
    e.stopPropagation();

    try {
        await fetch(
            `${API_BASE}/machine/${action}?location=${location}&machine_id=${id}`,
            { method: "POST" }
        );
    } catch (err) {
        console.error("Machine action failed", err);
    }
}
