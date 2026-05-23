// ============================================================
// login.js — All JavaScript for the MacroLens login page
// ============================================================

// ---- SWITCH BETWEEN LOGIN AND SIGNUP TABS ----
// Shows/hides forms without reloading the page
function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));
    if (tab === 'login') {
        document.querySelectorAll('.tab')[0].classList.add('active');
        document.getElementById('loginForm').classList.add('active');
    } else {
        document.querySelectorAll('.tab')[1].classList.add('active');
        document.getElementById('signupForm').classList.add('active');
    }
}

// ---- TOGGLE PASSWORD VISIBILITY ----
// Switches between showing and hiding password
// Eye icon changes to crossed eye when password is visible
function togglePassword(inputId, icon) {
    const input = document.getElementById(inputId);
    const eyeOpen = icon.querySelector('.eye-open');
    const eyeClosed = icon.querySelector('.eye-closed');
    if (input.type === 'password') {
        input.type = 'text';
        eyeOpen.style.display = 'none';
        eyeClosed.style.display = 'block';
        icon.style.opacity = '0.9';
    } else {
        input.type = 'password';
        eyeOpen.style.display = 'block';
        eyeClosed.style.display = 'none';
        icon.style.opacity = '0.35';
    }
}

// ---- LOGIN ----
// Sends email and password to Flask /login route
// On success redirects to dashboard
async function login() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const message = document.getElementById('loginMessage');
    const btn = event.target;

    if (!email || !password) {
        showMessage(message, 'Please fill in all fields', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Logging in...';

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(message, 'Welcome back! Redirecting...', 'success');
            setTimeout(() => window.location.href = '/dashboard', 1000);
        } else {
            showMessage(message, data.message || 'Login failed', 'error');
            btn.disabled = false;
            btn.textContent = 'Login';
        }
    } catch (err) {
        showMessage(message, 'Connection error. Try again.', 'error');
        btn.disabled = false;
        btn.textContent = 'Login';
    }
}

// ---- SIGNUP ----
// Sends name, email and password to Flask /signup route
// On success switches to login tab
async function signup() {
    const name = document.getElementById('signupName').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    const message = document.getElementById('signupMessage');
    const btn = event.target;

    if (!name || !email || !password) {
        showMessage(message, 'Please fill in all fields', 'error');
        return;
    }

    if (password.length < 6) {
        showMessage(message, 'Password must be at least 6 characters', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Creating account...';

    try {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await response.json();
        if (data.success) {
            showMessage(message, 'Account created! Please login.', 'success');
            setTimeout(() => switchTab('login'), 1500);
        } else {
            showMessage(message, data.message || 'Signup failed', 'error');
        }
    } catch (err) {
        showMessage(message, 'Connection error. Try again.', 'error');
    }

    btn.disabled = false;
    btn.textContent = 'Create Account';
}

// ---- SHOW MESSAGE ----
// Helper to display success or error messages below buttons
function showMessage(element, text, type) {
    element.textContent = text;
    element.className = 'message ' + type;
}

// ---- ENTER KEY TO SUBMIT ----
// Lets user press Enter instead of clicking the button
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        const activeForm = document.querySelector('.form.active').id;
        if (activeForm === 'loginForm') login();
        else signup();
    }
});