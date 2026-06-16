// ReviewGuard AI - Main Frontend JavaScript

const API_BASE = 'https://reviewguard-ai-84oc.onrender.com/api';

// Initialize Theme & Sidebar
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    checkAuthStatus();
    setupEventListeners();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeToggleIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeToggleIcon(newTheme);
    
    // Trigger chart refresh if on results page
    if (typeof window.refreshChartsTheme === 'function') {
        window.refreshChartsTheme(newTheme);
    }
}

function updateThemeToggleIcon(theme) {
    const icon = document.querySelector('.theme-toggle-btn i');
    if (icon) {
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
    }
}

// Sidebar Management
function initSidebar() {
    const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar && mainContent) {
        if (isCollapsed && window.innerWidth >= 992) {
            sidebar.classList.add('collapsed');
            mainContent.classList.add('expanded');
        }
    }
}

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar && mainContent) {
        if (window.innerWidth < 992) {
            // Mobile layout toggle
            sidebar.classList.toggle('active');
        } else {
            // Desktop layout toggle
            const willCollapse = !sidebar.classList.contains('collapsed');
            if (willCollapse) {
                sidebar.classList.add('collapsed');
                mainContent.classList.add('expanded');
            } else {
                sidebar.classList.remove('collapsed');
                mainContent.classList.remove('expanded');
            }
            localStorage.setItem('sidebar-collapsed', willCollapse ? 'true' : 'false');
        }
    }
}

// Authentication Helpers
function checkAuthStatus() {
    const path = window.location.pathname;
    const token = localStorage.getItem('access_token');
    const username = localStorage.getItem('username');
    
    // Pages requiring auth
    const authPages = ['/dashboard.html', '/analyze.html', '/result.html', '/history.html'];
    const isAuthPage = authPages.some(page => path.includes(page));
    
    if (isAuthPage && !token) {
        window.location.href = 'login.html';
    }
    
    // Update Profile Username UI
    const usernamePlaceholder = document.getElementById('userProfileName');
    if (usernamePlaceholder && username) {
        usernamePlaceholder.innerText = username;
    }
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    window.location.href = 'login.html';
}

// Setup Global Event Listeners
function setupEventListeners() {
    // Theme toggles
    const themeBtn = document.querySelector('.theme-toggle-btn');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }
    
    // Sidebar toggles
    const sidebarBtn = document.getElementById('sidebarToggle');
    if (sidebarBtn) {
        sidebarBtn.addEventListener('click', (e) => {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    // Close sidebar on mobile when clicking outside
    document.addEventListener('click', (e) => {
        const sidebar = document.querySelector('.sidebar');
        const toggleBtn = document.getElementById('sidebarToggle');
        if (sidebar && sidebar.classList.contains('active') && window.innerWidth < 992) {
            if (!sidebar.contains(e.target) && toggleBtn && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        }
    });
    
    // Logout buttons
    const logoutBtn = document.getElementById('logoutLink');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    }
}

// Register user
async function registerUser(username, email, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Registration failed');
        }
        return { success: true, message: data.message };
    } catch (err) {
        return { success: false, error: err.message };
    }
}

// Login user
async function loginUser(email, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }
        
        // Save to storage
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('username', data.username);
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
}

// Submit Manual Review Analysis
async function submitManualAnalysis(productName, category, reviewsList) {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_BASE}/analyze/manual`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_name: productName,
                category: category,
                reviews: reviewsList
            })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Analysis failed');
        }
        return { success: true, data };
    } catch (err) {
        return { success: false, error: err.message };
    }
}

// Submit CSV Review Analysis
async function submitCSVAnalysis(productName, category, file) {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('product_name', productName);
    formData.append('category', category);
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/analyze/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'CSV upload analysis failed');
        }
        return { success: true, data };
    } catch (err) {
        return { success: false, error: err.message };
    }
}

// Fetch History items
async function fetchHistory(searchQuery = '') {
    const token = localStorage.getItem('access_token');
    let url = `${API_BASE}/history`;
    if (searchQuery) {
        url += `?search=${encodeURIComponent(searchQuery)}`;
    }
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch history');
        return await response.json();
    } catch (err) {
        console.error(err);
        return [];
    }
}

// Fetch single historical run details
async function fetchHistoryDetail(historyId) {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_BASE}/history/${historyId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch history detail');
        return await response.json();
    } catch (err) {
        console.error(err);
        return null;
    }
}

// Trigger Report Downloads
function downloadReportFile(historyId, format) {
    const token = localStorage.getItem('access_token');
    const url = `${API_BASE}/report/${historyId}/download?format=${format}`;
    
    // We can open the URL in a new window or trigger download via tag
    const link = document.createElement('a');
    link.href = url;
    link.download = `reviewguard_report_${historyId}.${format === 'excel' ? 'xlsx' : format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
