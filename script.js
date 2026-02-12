document.addEventListener('DOMContentLoaded', () => {
    const SETTINGS_VERSION = 1;

    let settings = {
        version: SETTINGS_VERSION,
        exams: [],
        lectures: [],
        assignments: [],
        quizzes: [],
        projects: [],
        breaks: []
    };

    let parsedEvents = [];
    let currentCalendarEvents = [];

    if (localStorage.getItem('bootlegSettings')) {
        const stored = JSON.parse(localStorage.getItem('bootlegSettings'));
        if (stored.version === SETTINGS_VERSION) {
            settings = { ...settings, ...stored };
            delete settings.apiKeys;
        } else {
            localStorage.removeItem('bootlegSettings');
        }
        renderSettings();
    }

    const eventsContainer = document.getElementById('events-list-container');
    const btnRefresh = document.getElementById('btn-refresh');
    const toggleAll = document.getElementById('toggle-all-events');
    const emailDisplay = document.getElementById('user-email-display');
    const authBtn = document.getElementById('auth-btn');

    let selectAllState = false;

    function escapeHtml(text) {
        if (!text) return text;
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async function checkAuthStatus() {
        try {
            const res = await fetch('/api/user');
            const data = await res.json();
            
            if (data.loggedIn && data.email) {
                if (emailDisplay) {
                    emailDisplay.textContent = data.email;
                    emailDisplay.style.display = 'inline-block';
                }
                if (authBtn) {
                    authBtn.textContent = 'Logout';
                    authBtn.href = '/logout';
                }
            } else {
                if (emailDisplay) emailDisplay.style.display = 'none';
                if (authBtn) {
                    authBtn.textContent = 'Login';
                    authBtn.href = '/login';
                }
            }
        } catch (err) {
            console.error("Auth check failed:", err);
        }
    }
    
    checkAuthStatus();

    async function fetchEvents() {
        eventsContainer.innerHTML = '<div class="empty-state">Loading...</div>';
        try {
            const res = await fetch('/api/events');
            
            if (res.status === 401) {
                eventsContainer.innerHTML = '<div class="empty-state"><span>Please&nbsp;<a href="/login" style="color: var(--primary-blue)">login</a>&nbsp;to view events.</span></div>';
                checkAuthStatus();
                return;
            }

            const events = await res.json();
            currentCalendarEvents = events;
            
            checkAuthStatus();
            
            if (events.length === 0) {
                eventsContainer.innerHTML = '<div class="empty-state">No events loaded yet.</div>';
                return;
            }

            eventsContainer.innerHTML = events.map(e => `
                <div style="background: rgba(55,65,81,0.5); padding: 0.75rem; border-radius: 0.25rem; margin-bottom: 0.5rem; border: 1px solid var(--border-color); display: flex; gap: 10px; align-items: center;">
                    <input type="checkbox" class="event-checkbox" value="${e.id}" style="width: 1.2em; height: 1.2em;">
                    <div>
                        <div style="font-weight: 600;">${escapeHtml(e.summary)}</div>
                        <div class="small-text" style="color: var(--text-muted);">${new Date(e.start.dateTime || e.start.date).toLocaleString()}</div>
                    </div>
                </div>
            `).join('');
            
            if (selectAllState) {
                const checkboxes = eventsContainer.querySelectorAll('.event-checkbox');
                checkboxes.forEach(cb => { cb.checked = true; });
            }
        } catch (err) {
            eventsContainer.innerHTML = '<div class="empty-state" style="color: var(--danger-red)">Failed to fetch events</div>';
            console.error(err);
        }
    }

    if (toggleAll) {
        const updateToggleLabel = () => {
            toggleAll.textContent = selectAllState ? 'Unselect all' : 'Select all';
        };

        toggleAll.addEventListener('click', () => {
            selectAllState = !selectAllState;
            const checkboxes = eventsContainer.querySelectorAll('.event-checkbox');
            checkboxes.forEach(cb => { cb.checked = selectAllState; });
            updateToggleLabel();
        });

        updateToggleLabel();
    }

    btnRefresh.addEventListener('click', fetchEvents);
    fetchEvents();


    const fileInput = document.getElementById('file-input');
    const btnBrowse = document.getElementById('btn-browse');
    const dropZone = document.getElementById('drop-zone');
    const fileNameDisplay = document.getElementById('file-name-display');
    const btnParse = document.getElementById('btn-parse');
    const previewList = document.getElementById('preview-list');
    const btnSync = document.getElementById('btn-sync-calendar');
    const previewActions = document.getElementById('preview-actions');

    btnBrowse.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
            fileNameDisplay.style.color = 'var(--text-main)';
        }
    });

    btnParse.addEventListener('click', async () => {
        if (fileInput.files.length === 0) return alert("Please select a file first.");

        const checkboxes = Array.from(document.querySelectorAll('#extract-checkboxes input:checked'));
        if (checkboxes.length === 0) {
            alert('Please choose at least one event type to extract.');
            return;
        }

        const colorSelect = document.getElementById('event-color-select');
        let selectedColorId = colorSelect.value;
        
        if (selectedColorId === 'random') {
            const allColors = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'];
            const usedColors = new Set(currentCalendarEvents.map(e => e.colorId).filter(c => c));
            const availableColors = allColors.filter(c => !usedColors.has(c));
            
            if (availableColors.length > 0) {
                selectedColorId = availableColors[Math.floor(Math.random() * availableColors.length)];
            } else {
                selectedColorId = allColors[Math.floor(Math.random() * allColors.length)];
            }
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('colorId', selectedColorId);

        checkboxes.forEach(cb => formData.append('categories', cb.value));

        previewList.innerHTML = '<div class="empty-state">Analyzing...</div>';

        try {
            const res = await fetch('/api/analyze', { method: 'POST', body: formData });
            const data = await res.json();
            parsedEvents = data;
            renderPreview();
        } catch (err) {
            previewList.innerHTML = '<div class="small-text" style="color: var(--danger-red)">Error parsing syllabus. Check console.</div>';
            console.error(err);
        }
    });

    function renderPreview() {
        if (parsedEvents.length === 0) {
            previewList.innerHTML = '<div class="small-text">No events found.</div>';
            previewActions.style.display = 'none';
            return;
        }

        previewList.innerHTML = parsedEvents.map((e, index) => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border-bottom: 1px solid var(--border-color);">
                <div>
                    <div style="font-weight: bold; font-size: 0.85rem;">${escapeHtml(e.summary)}</div>
                    <div class="small-text">${e.start.dateTime || e.start.date}</div>
                </div>
                <button onclick="removeParsedEvent(${index})" style="color: var(--danger-red); background: none; border: none; cursor: pointer;">✕</button>
            </div>
        `).join('');
        
        previewActions.style.display = 'block';
    }

    window.removeParsedEvent = (index) => {
        parsedEvents.splice(index, 1);
        renderPreview();
    };

    btnSync.addEventListener('click', async () => {
        if (confirm(`Add ${parsedEvents.length} events to Google Calendar with default reminders?`)) {
            try {
                const processedEvents = parsedEvents.map(event => {
                    const e = { ...event };
                    const lowerSummary = e.summary.toLowerCase();
                    
                    let remindersToAdd = [];
                    if (lowerSummary.includes('exam') || lowerSummary.includes('midterm')) {
                        remindersToAdd = settings.exams;
                    } else if (lowerSummary.includes('lecture') || lowerSummary.includes('class')) {
                        remindersToAdd = settings.lectures;
                    } else if (lowerSummary.includes('quiz')) {
                        remindersToAdd = settings.quizzes;
                    } else if (lowerSummary.includes('project')) {
                        remindersToAdd = settings.projects;
                    } else if (lowerSummary.includes('assignment') || lowerSummary.includes('homework')) {
                        remindersToAdd = settings.assignments;
                    } else if (lowerSummary.includes('break')) {
                        remindersToAdd = settings.breaks;
                    }

                    if (remindersToAdd.length > 0) {
                        e.reminders = {
                            useDefault: false,
                            overrides: remindersToAdd.map(r => {
                                let min = parseInt(r.val);
                                if (r.unit === 'hours') min *= 60;
                                else if (r.unit === 'days') min *= 60 * 24;
                                else if (r.unit === 'weeks') min *= 60 * 24 * 7;
                                return { method: 'popup', minutes: min };
                            })
                        };
                    }
                    return e;
                });

                const payload = {
                    events: processedEvents
                };

                const res = await fetch('/api/add-events', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const result = await res.json();
                if (result.status === 'success') {
                    alert('Events added successfully!');
                    parsedEvents = [];
                    renderPreview();
                    fetchEvents();
                }
            } catch (err) {
                alert('Failed to sync.');
                console.error(err);
            }
        }
    });


    function createReminderRow(val, unit, type, index) {
        return `
        <li class="reminder-item" data-index="${index}" data-type="${type}">
            <span class="reminder-label">Reminder:</span>
            <input type="number" value="${val}" class="input-sm" onchange="updateSetting('${type}', ${index}, 'val', this.value)">
            <select class="select-flex" onchange="updateSetting('${type}', ${index}, 'unit', this.value)">
                <option value="minutes" ${unit === 'minutes' ? 'selected' : ''}>Minutes</option>
                <option value="hours" ${unit === 'hours' ? 'selected' : ''}>Hours</option>
                <option value="days" ${unit === 'days' ? 'selected' : ''}>Days</option>
                <option value="weeks" ${unit === 'weeks' ? 'selected' : ''}>Weeks</option>
            </select>
            <button class="btn btn-icon" onclick="removeReminder('${type}', ${index})">✕</button>
        </li>`;
    }

    function renderSettings() {
        const settingsContainer = document.getElementById('reminder-settings-container');
        if (!settingsContainer) return;
        
        settingsContainer.innerHTML = '';

        const categories = [
            { id: 'exams', label: 'Exams', color: 'text-purple' },
            { id: 'lectures', label: 'Lectures / Classes', color: 'text-purple' },
            { id: 'assignments', label: 'Assignments', color: 'text-purple' },
            { id: 'quizzes', label: 'Quizzes', color: 'text-purple' },
            { id: 'projects', label: 'Projects', color: 'text-purple' },
            { id: 'breaks', label: 'Breaks', color: 'text-purple' }, 
        ];

        categories.forEach(cat => {
            if (settings[cat.id] === undefined) settings[cat.id] = [];

            settings[cat.id].sort((a, b) => {
                const getDur = (r) => {
                    let v = parseInt(r.val) || 0;
                    if (r.unit === 'hours') return v * 60;
                    if (r.unit === 'days') return v * 60 * 24;
                    if (r.unit === 'weeks') return v * 60 * 24 * 7;
                    return v;
                };
                return getDur(a) - getDur(b);
            });

            const groupDiv = document.createElement('div');
            groupDiv.className = 'reminder-group';
            groupDiv.innerHTML = `
                <div class="group-title ${cat.color}">${cat.label}</div>
                <ul class="reminder-list" id="list-reminders-${cat.id}">
                    ${settings[cat.id].map((r, i) => createReminderRow(r.val, r.unit, cat.id, i)).join('')}
                </ul>
                <button class="btn btn-add" onclick="addReminder('${cat.id}')"><span>+</span> Add ${cat.label} Reminder</button>
            `;
            settingsContainer.appendChild(groupDiv);
        });

        settings.version = SETTINGS_VERSION;
        localStorage.setItem('bootlegSettings', JSON.stringify(settings));
    }

    window.addReminder = (type) => {
        if (!settings[type]) settings[type] = [];
        settings[type].push({ val: 1, unit: 'days' });
        renderSettings();
    };

    window.updateSetting = (type, index, field, value) => {
        if (!settings[type] || !settings[type][index]) return;

        const item = settings[type][index];
        const limits = { 'minutes': 40320, 'hours': 672, 'days': 28, 'weeks': 4 };

        if (field === 'val') {
            let parsed = parseInt(value, 10);
            parsed = isNaN(parsed) ? 0 : parsed;
            
            const max = limits[item.unit] || 40320;
            if (parsed > max) parsed = max;
            if (parsed < 0) parsed = 0;
            
            item.val = parsed;
        } else {
            item[field] = value;
            if (field === 'unit') {
                const max = limits[value] || 40320;
                if (item.val > max) item.val = max;
            }
        }
        renderSettings();
    };

    window.removeReminder = (type, index) => {
        if (!settings[type]) return;
        settings[type].splice(index, 1);
        renderSettings();
    };

    document.getElementById('btn-save-settings').addEventListener('click', () => {
        settings.version = SETTINGS_VERSION;
        localStorage.setItem('bootlegSettings', JSON.stringify(settings));
        alert('Settings saved!');
    });
    
    window.bulkDelete = async () => {
        const checkboxes = document.querySelectorAll('.event-checkbox:checked');
        const idsToDelete = Array.from(checkboxes).map(cb => cb.value);

        if (idsToDelete.length === 0) {
            alert('Please select events to delete.');
            return;
        }

        if (!confirm(`Are you sure you want to delete ${idsToDelete.length} events?`)) {
            return;
        }

        const deleteBtn = document.querySelector('button[onclick="bulkDelete()"]');
        const originalText = deleteBtn ? deleteBtn.innerText : 'Delete selected';
        if (deleteBtn) {
            deleteBtn.innerText = 'Deleting...';
            deleteBtn.disabled = true;
        }

        try {
            const response = await fetch('/api/delete-events', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ eventIds: idsToDelete })
            });

            const data = await response.json();

            if (data.status === 'success') {
                fetchEvents();
            } else {
                alert('Error deleting events: ' + data.message);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to delete events.');
        } finally {
            if (deleteBtn) {
                deleteBtn.innerText = originalText;
                deleteBtn.disabled = false;
            }
        }
    };

    renderSettings();
});