// AI Resume Analyzer Main JavaScript File

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initUploadDropzone();
    initAuthForms();
});

// --- 1. THEME SWITCHER (DARK / LIGHT) ---
function initTheme() {
    const themeToggle = document.getElementById("themeToggle");
    if (!themeToggle) return;
    
    // Check local storage or system preferences
    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    
    if (savedTheme === "light") {
        document.documentElement.setAttribute("data-theme", "light");
        themeToggle.innerHTML = "🌙"; // Show moon icon in light mode
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
        themeToggle.innerHTML = "☀️"; // Show sun icon in dark mode
    }
    
    themeToggle.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        if (currentTheme === "light") {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
            themeToggle.innerHTML = "☀️";
        } else {
            document.documentElement.setAttribute("data-theme", "light");
            localStorage.setItem("theme", "light");
            themeToggle.innerHTML = "🌙";
        }
    });
}

// --- 2. DRAG & DROP UPLOAD SYSTEM ---
function initUploadDropzone() {
    const dropzone = document.getElementById("uploadDropzone");
    const fileInput = document.getElementById("resumeFile");
    const fileInfo = document.getElementById("fileInfo");
    
    if (!dropzone || !fileInput) return;
    
    // Clicking the dropzone opens file dialog
    dropzone.addEventListener("click", () => fileInput.click());
    
    // Highlight dropzone on dragover
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dragover");
        }, false);
    });
    
    // Remove highlights on dragleave
    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dragover");
        }, false);
    });
    
    // Handle dropped files
    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            displayFileInfo(files[0]);
        }
    });
    
    // Handle dialog picked files
    fileInput.addEventListener("change", (e) => {
        if (fileInput.files.length > 0) {
            displayFileInfo(fileInput.files[0]);
        }
    });
    
    function displayFileInfo(file) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileInfo.innerHTML = `
            <div class="mt-3 p-3 bg-secondary rounded border">
                <strong>📄 Selected File:</strong> ${file.name} (${sizeMB} MB)
            </div>
        `;
    }
}

// --- 3. AUTHENTICATION & FORM SUBMITS ---
function initAuthForms() {
    // Register Form Handler
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fullName = document.getElementById("fullName").value;
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            const errorAlert = document.getElementById("errorAlert");
            
            errorAlert.classList.add("d-none");
            
            try {
                const response = await fetch("/api/auth/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ full_name: fullName, email, password })
                });
                
                const data = await response.json();
                if (response.ok) {
                    // Auto redirect to login or dashboard
                    // Let's redirect to login for confirmation
                    window.location.href = "/login?registered=true";
                } else {
                    errorAlert.innerText = data.detail || "Registration failed.";
                    errorAlert.classList.remove("d-none");
                }
            } catch (err) {
                errorAlert.innerText = "Network connection error. Try again.";
                errorAlert.classList.remove("d-none");
            }
        });
    }
    
    // Login Form Handler
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            const errorAlert = document.getElementById("errorAlert");
            
            errorAlert.classList.add("d-none");
            
            // Format form data for OAuth2 spec
            const formData = new URLSearchParams();
            formData.append("username", email);
            formData.append("password", password);
            
            try {
                const response = await fetch("/api/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: formData
                });
                
                const data = await response.json();
                if (response.ok) {
                    // Cookie is set HTTPOnly, redirect to dashboard
                    window.location.href = "/dashboard";
                } else {
                    errorAlert.innerText = data.detail || "Invalid email or password.";
                    errorAlert.classList.remove("d-none");
                }
            } catch (err) {
                errorAlert.innerText = "Network connection error. Try again.";
                errorAlert.classList.remove("d-none");
            }
        });
    }
}

// --- 4. LOGOUT HANDLER ---
async function logoutUser() {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
        window.location.href = "/login";
    } catch (err) {
        console.error("Logout failed", err);
        window.location.href = "/login";
    }
}

// --- 5. ANIMATE GAUGES AND COUNTERS ---
function animateScoreGauge(targetScore) {
    const gaugeBar = document.getElementById("gaugeBar");
    const scoreText = document.getElementById("scoreValue");
    if (!gaugeBar || !scoreText) return;
    
    // Circumference of 150px circular gauge with radius=60 (2 * pi * r = 376.99)
    const circumference = 377;
    gaugeBar.style.strokeDasharray = circumference;
    
    let currentScore = 0;
    const duration = 1200; // ms
    const stepTime = Math.abs(Math.floor(duration / targetScore));
    
    const timer = setInterval(() => {
        currentScore++;
        scoreText.innerText = currentScore;
        
        // Calculate dashoffset (377 to 0 corresponding to 0% to 100%)
        const offset = circumference - (currentScore / 100) * circumference;
        gaugeBar.style.strokeDashoffset = offset;
        
        if (currentScore >= targetScore) {
            clearInterval(timer);
            // Dynamic color shift based on target score
            if (targetScore >= 75) {
                gaugeBar.style.stroke = "#10b981"; // Success
            } else if (targetScore >= 50) {
                gaugeBar.style.stroke = "#f59e0b"; // Warning
            } else {
                gaugeBar.style.stroke = "#ef4444"; // Danger
            }
        }
    }, stepTime);
}

// --- 6. RESUME DELETIONS ---
async function deleteResume(resumeId, elementId) {
    if (!confirm("Are you sure you want to delete this resume? All associated evaluations will be permanently removed.")) return;
    
    try {
        const response = await fetch(`/api/resumes/${resumeId}`, { method: "DELETE" });
        if (response.ok) {
            const row = document.getElementById(elementId);
            if (row) {
                row.classList.add("fade-out");
                setTimeout(() => row.remove(), 400);
            }
            // If we're on the dashboard, reload the page to refresh stats
            if (window.location.pathname === "/dashboard") {
                window.location.reload();
            }
        } else {
            const data = await response.json();
            alert(data.detail || "Could not delete resume.");
        }
    } catch (err) {
        alert("Network connection error. Try again.");
    }
}

// --- 7. ANALYSIS DELETIONS ---
async function deleteAnalysis(analysisId, elementId) {
    if (!confirm("Are you sure you want to delete this evaluation run?")) return;
    
    try {
        const response = await fetch(`/api/analysis/${analysisId}`, { method: "DELETE" });
        if (response.ok) {
            const cardOrRow = document.getElementById(elementId);
            if (cardOrRow) {
                cardOrRow.classList.add("fade-out");
                setTimeout(() => cardOrRow.remove(), 400);
            }
            if (window.location.pathname === "/dashboard") {
                window.location.reload();
            }
        } else {
            const data = await response.json();
            alert(data.detail || "Could not delete evaluation.");
        }
    } catch (err) {
        alert("Network connection error. Try again.");
    }
}

// --- 8. ADMIN OPERATIONS ---
async function deleteUserAdmin(userId, elementId) {
    if (!confirm("WARNING: Are you sure you want to delete this user? All their uploaded resumes, reports, and evaluations will be permanently wiped out.")) return;
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, { method: "DELETE" });
        const data = await response.json();
        if (response.ok) {
            const row = document.getElementById(elementId);
            if (row) {
                row.classList.add("fade-out");
                setTimeout(() => row.remove(), 400);
            }
            alert("User deleted successfully.");
        } else {
            alert(data.detail || "Could not delete user.");
        }
    } catch (err) {
        alert("Network connection error. Try again.");
    }
}
