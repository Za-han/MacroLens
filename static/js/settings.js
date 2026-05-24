// ============================================================
// settings.js — Profile settings page
// ============================================================

let currentHeightUnit = 'cm';

// ---- ON PAGE LOAD ----
// Load existing profile data and pre-fill the form
window.onload = async function() {
    await loadProfile();
    setupLivePreview();
}

// ---- LOAD PROFILE ----
// Fetches current profile and fills in all the inputs
async function loadProfile() {
    try {
        const res = await fetch('/get_profile');
        const data = await res.json();
        if (!data.success) return;

        const p = data.profile;

        // Pre-fill all fields with current values
        document.getElementById('settingsName').value = p.name || '';
        document.getElementById('settingsEmail').value = p.email || '';
        document.getElementById('settingsAge').value = p.age || '';
        document.getElementById('settingsGender').value = p.gender || 'male';
        document.getElementById('settingsWeight').value = p.weight_kg || '';
        document.getElementById('settingsGoal').value = p.goal || 'maintain';

        // Height in cm
        if (p.height_cm) {
            document.getElementById('settingsHeightCm').value = p.height_cm;
        }

        // Show current calorie target
        if (p.daily_calories) {
            document.getElementById('previewCalories').textContent = p.daily_calories;
        }

    } catch(e) {
        console.error('Load profile error:', e);
    }
}

// ---- LIVE CALORIE PREVIEW ----
// Updates the calorie preview as user changes inputs
function setupLivePreview() {
    const inputs = ['settingsAge', 'settingsGender', 'settingsHeightCm',
                    'settingsFeet', 'settingsInches', 'settingsWeight', 'settingsGoal'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updatePreview);
        if (el) el.addEventListener('change', updatePreview);
    });
}

function updatePreview() {
    try {
        const age = parseFloat(document.getElementById('settingsAge').value) || 0;
        const gender = document.getElementById('settingsGender').value;
        const weight = parseFloat(document.getElementById('settingsWeight').value) || 0;
        const goal = document.getElementById('settingsGoal').value;

        let height = 0;
        if (currentHeightUnit === 'cm') {
            height = parseFloat(document.getElementById('settingsHeightCm').value) || 0;
        } else {
            const feet = parseFloat(document.getElementById('settingsFeet').value) || 0;
            const inches = parseFloat(document.getElementById('settingsInches').value) || 0;
            height = Math.round((feet * 30.48) + (inches * 2.54));
        }

        if (!age || !height || !weight) return;

        // Mifflin-St Jeor formula
        let bmr;
        if (gender === 'male') {
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5;
        } else {
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161;
        }

        let tdee = bmr * 1.55;
        let calories;
        if (goal === 'cut') calories = Math.round(tdee - 500);
        else if (goal === 'bulk') calories = Math.round(tdee + 300);
        else calories = Math.round(tdee);

        document.getElementById('previewCalories').textContent = calories;

    } catch(e) {}
}

// ---- HEIGHT UNIT TOGGLE ----
function switchHeightUnit(unit) {
    currentHeightUnit = unit;
    if (unit === 'cm') {
        document.getElementById('settingsHeightCm').style.display = 'block';
        document.getElementById('settingsHeightFt').style.display = 'none';
        document.getElementById('unitCm').classList.add('active');
        document.getElementById('unitFt').classList.remove('active');
    } else {
        document.getElementById('settingsHeightCm').style.display = 'none';
        document.getElementById('settingsHeightFt').style.display = 'block';
        document.getElementById('unitFt').classList.add('active');
        document.getElementById('unitCm').classList.remove('active');
    }
    updatePreview();
}

// ---- SAVE SETTINGS ----
async function saveSettings() {
    const name = document.getElementById('settingsName').value;
    const age = document.getElementById('settingsAge').value;
    const gender = document.getElementById('settingsGender').value;
    const weight = document.getElementById('settingsWeight').value;
    const goal = document.getElementById('settingsGoal').value;
    const message = document.getElementById('saveMessage');
    const btn = document.getElementById('saveBtn');

    let height;
    if (currentHeightUnit === 'cm') {
        height = document.getElementById('settingsHeightCm').value;
    } else {
        const feet = parseFloat(document.getElementById('settingsFeet').value) || 0;
        const inches = parseFloat(document.getElementById('settingsInches').value) || 0;
        height = Math.round((feet * 30.48) + (inches * 2.54));
    }

    if (!age || !height || !weight) {
        message.textContent = 'Please fill in all fields';
        message.className = 'save-message error';
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const res = await fetch('/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, age, gender, height, weight, goal })
        });

        const data = await res.json();

        if (data.success) {
            message.textContent = '✅ Profile updated successfully!';
            message.className = 'save-message success';
            updatePreview();
        } else {
            message.textContent = data.message || 'Something went wrong';
            message.className = 'save-message error';
        }

    } catch(e) {
        message.textContent = 'Connection error. Try again.';
        message.className = 'save-message error';
    }

    btn.disabled = false;
    btn.textContent = 'Save Changes';
}