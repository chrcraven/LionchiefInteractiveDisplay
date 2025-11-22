// Global state
let userId = null;
let username = null;
let eventSource = null;  // Changed from websocket to eventSource for SSE
let hasControl = false;
let reconnectInterval = null;

// DOM Elements
const elements = {
    loginSection: document.getElementById('loginSection'),
    queueSection: document.getElementById('queueSection'),
    controlsSection: document.getElementById('controlsSection'),
    usernameInput: document.getElementById('usernameInput'),
    joinQueueBtn: document.getElementById('joinQueueBtn'),
    leaveQueueBtn: document.getElementById('leaveQueueBtn'),
    connectionStatus: document.getElementById('connectionStatus'),
    userPosition: document.getElementById('userPosition'),
    queueLength: document.getElementById('queueLength'),
    timeRemaining: document.getElementById('timeRemaining'),
    queueList: document.getElementById('queueList'),
    speedSlider: document.getElementById('speedSlider'),
    speedValue: document.getElementById('speedValue'),
    stopBtn: document.getElementById('stopBtn'),
    slowBtn: document.getElementById('slowBtn'),
    mediumBtn: document.getElementById('mediumBtn'),
    fastBtn: document.getElementById('fastBtn'),
    forwardBtn: document.getElementById('forwardBtn'),
    reverseBtn: document.getElementById('reverseBtn'),
    toggleDirectionBtn: document.getElementById('toggleDirectionBtn'),
    directionValue: document.getElementById('directionValue'),
    hornBtn: document.getElementById('hornBtn'),
    bellOnBtn: document.getElementById('bellOnBtn'),
    bellOffBtn: document.getElementById('bellOffBtn'),
    emergencyStopBtn: document.getElementById('emergencyStopBtn'),
    trainConnected: document.getElementById('trainConnected'),
    trainSpeed: document.getElementById('trainSpeed'),
    trainDirection: document.getElementById('trainDirection'),
    queueTimeoutInput: document.getElementById('queueTimeoutInput'),
    updateConfigBtn: document.getElementById('updateConfigBtn')
};

// Initialize
function init() {
    // Generate random user ID
    userId = 'user_' + Math.random().toString(36).substr(2, 9);

    // Setup event listeners
    setupEventListeners();

    // Connect to SSE stream for real-time updates
    connectEventSource();

    // Load initial config
    loadConfig();

    // Load train status periodically
    setInterval(loadTrainStatus, 5000);
}

function setupEventListeners() {
    elements.joinQueueBtn.addEventListener('click', joinQueue);
    elements.leaveQueueBtn.addEventListener('click', leaveQueue);

    // Speed controls
    elements.speedSlider.addEventListener('input', (e) => {
        elements.speedValue.textContent = e.target.value;
    });

    elements.speedSlider.addEventListener('change', (e) => {
        setSpeed(parseInt(e.target.value));
    });

    elements.stopBtn.addEventListener('click', () => setSpeed(0));
    elements.slowBtn.addEventListener('click', () => setSpeed(8));
    elements.mediumBtn.addEventListener('click', () => setSpeed(16));
    elements.fastBtn.addEventListener('click', () => setSpeed(24));

    // Direction controls
    elements.forwardBtn.addEventListener('click', () => setDirection('forward'));
    elements.reverseBtn.addEventListener('click', () => setDirection('reverse'));
    elements.toggleDirectionBtn.addEventListener('click', () => setDirection('toggle'));

    // Sound controls
    elements.hornBtn.addEventListener('click', blowHorn);
    elements.bellOnBtn.addEventListener('click', () => controlBell(true));
    elements.bellOffBtn.addEventListener('click', () => controlBell(false));

    // Emergency stop
    elements.emergencyStopBtn.addEventListener('click', emergencyStop);

    // Config
    elements.updateConfigBtn.addEventListener('click', updateConfig);

    // Enter key in username input
    elements.usernameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            joinQueue();
        }
    });
}

// Server-Sent Events (SSE) connection for real-time updates
function connectEventSource() {
    try {
        // Close existing connection if any
        if (eventSource) {
            eventSource.close();
        }

        // Connect to SSE endpoint (relative URL - no CORS issues!)
        eventSource = new EventSource('/api/events');

        eventSource.onopen = () => {
            console.log('SSE connected');
            updateConnectionStatus(true);
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
        };

        eventSource.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleRealtimeMessage(message);
            } catch (error) {
                console.error('Error parsing SSE message:', error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            updateConnectionStatus(false);
            eventSource.close();

            // Try to reconnect
            if (!reconnectInterval) {
                reconnectInterval = setInterval(connectEventSource, 5000);
            }
        };
    } catch (error) {
        console.error('Failed to connect SSE:', error);
        updateConnectionStatus(false);
    }
}

function updateConnectionStatus(connected) {
    const statusDot = elements.connectionStatus.querySelector('.status-dot');
    const statusText = elements.connectionStatus.querySelector('.status-text');

    if (connected) {
        statusDot.classList.add('connected');
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('connected');
        statusDot.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

function handleRealtimeMessage(message) {
    if (message.type === 'queue_update') {
        updateQueueDisplay(message.data);
    } else if (message.type === 'connection_status') {
        // Handle connection status updates from the API
        console.log('API connection status:', message.connected ? 'connected' : 'disconnected');
    }
}

// API calls (using Flask proxy - no CORS issues!)
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        // Use relative URL to Flask proxy instead of direct API call
        const response = await fetch('/api' + endpoint, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API call failed:', error);
        alert('Error: ' + error.message);
        throw error;
    }
}

// Queue functions
async function joinQueue() {
    username = elements.usernameInput.value.trim();

    if (!username) {
        alert('Please enter your name');
        return;
    }

    try {
        const result = await apiCall('/queue/join', 'POST', { user_id: userId, username });

        if (result.success) {
            elements.loginSection.style.display = 'none';
            elements.queueSection.style.display = 'block';
            loadQueueStatus();
        }
    } catch (error) {
        console.error('Failed to join queue:', error);
    }
}

async function leaveQueue() {
    try {
        const result = await apiCall('/queue/leave', 'POST', { user_id: userId });

        if (result.success) {
            elements.queueSection.style.display = 'none';
            elements.controlsSection.style.display = 'none';
            elements.loginSection.style.display = 'block';
            hasControl = false;
        }
    } catch (error) {
        console.error('Failed to leave queue:', error);
    }
}

async function loadQueueStatus() {
    try {
        const status = await apiCall('/queue/status');
        updateQueueDisplay(status);
    } catch (error) {
        console.error('Failed to load queue status:', error);
    }
}

function updateQueueDisplay(status) {
    // Update queue info
    const userInQueue = status.queue.find(u => u.user_id === userId);

    if (userInQueue) {
        elements.userPosition.textContent = userInQueue.position;
        elements.queueLength.textContent = status.queue_length;

        if (userInQueue.time_remaining !== null) {
            if (userInQueue.time_remaining === -1) {
                elements.timeRemaining.textContent = '∞ (Unlimited)';
                elements.timeRemaining.className = 'info-value time-unlimited';
            } else {
                const minutes = Math.floor(userInQueue.time_remaining / 60);
                const seconds = Math.floor(userInQueue.time_remaining % 60);
                elements.timeRemaining.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

                // Apply color coding based on time remaining
                elements.timeRemaining.className = 'info-value';
                if (userInQueue.time_remaining > 120) {
                    elements.timeRemaining.classList.add('time-safe');
                } else if (userInQueue.time_remaining > 60) {
                    elements.timeRemaining.classList.add('time-warning');
                } else if (userInQueue.time_remaining > 30) {
                    elements.timeRemaining.classList.add('time-danger');
                } else {
                    elements.timeRemaining.classList.add('time-critical');
                }
            }
        } else {
            elements.timeRemaining.textContent = 'Waiting...';
            elements.timeRemaining.className = 'info-value';
        }

        // Check if user has control
        hasControl = userInQueue.is_active;

        if (hasControl) {
            elements.controlsSection.style.display = 'block';
        } else {
            elements.controlsSection.style.display = 'none';
        }
    }

    // Update queue list
    elements.queueList.innerHTML = '';
    status.queue.forEach(user => {
        const item = document.createElement('div');
        item.className = 'queue-item' + (user.is_active ? ' active' : '');

        const info = document.createElement('div');
        info.className = 'queue-item-info';

        const badge = document.createElement('div');
        badge.className = 'position-badge';
        badge.textContent = user.position;

        const name = document.createElement('span');
        name.textContent = user.username + (user.user_id === userId ? ' (You)' : '');

        info.appendChild(badge);
        info.appendChild(name);

        if (user.is_active) {
            const activeBadge = document.createElement('span');
            activeBadge.className = 'active-badge';
            activeBadge.textContent = 'CONTROLLING';
            info.appendChild(activeBadge);
        }

        item.appendChild(info);
        elements.queueList.appendChild(item);
    });
}

// Train control functions
async function setSpeed(speed) {
    if (!hasControl) {
        alert('You do not have control');
        return;
    }

    try {
        await apiCall('/train/speed', 'POST', { user_id: userId, speed });
        elements.speedSlider.value = speed;
        elements.speedValue.textContent = speed;
    } catch (error) {
        console.error('Failed to set speed:', error);
    }
}

async function setDirection(direction) {
    if (!hasControl) {
        alert('You do not have control');
        return;
    }

    try {
        const result = await apiCall('/train/direction', 'POST', { user_id: userId, direction });
        if (result.direction) {
            elements.directionValue.textContent = result.direction.charAt(0).toUpperCase() + result.direction.slice(1);
        }
    } catch (error) {
        console.error('Failed to set direction:', error);
    }
}

async function blowHorn() {
    if (!hasControl) {
        alert('You do not have control');
        return;
    }

    try {
        await apiCall('/train/horn', 'POST', { user_id: userId });
    } catch (error) {
        console.error('Failed to blow horn:', error);
    }
}

async function controlBell(state) {
    if (!hasControl) {
        alert('You do not have control');
        return;
    }

    try {
        await apiCall('/train/bell', 'POST', { user_id: userId, state });
    } catch (error) {
        console.error('Failed to control bell:', error);
    }
}

async function emergencyStop() {
    try {
        await apiCall('/train/emergency-stop', 'POST', { user_id: userId });
        elements.speedSlider.value = 0;
        elements.speedValue.textContent = 0;
    } catch (error) {
        console.error('Failed to emergency stop:', error);
    }
}

async function loadTrainStatus() {
    try {
        const status = await apiCall('/train/status');
        elements.trainConnected.textContent = status.connected ? '✓ Yes' : '✗ No' + (status.mock_mode ? ' (Mock Mode)' : '');
        elements.trainSpeed.textContent = status.speed;
        elements.trainDirection.textContent = status.direction.charAt(0).toUpperCase() + status.direction.slice(1);
    } catch (error) {
        console.error('Failed to load train status:', error);
    }
}

// Config functions
async function loadConfig() {
    try {
        const config = await apiCall('/config');
        elements.queueTimeoutInput.value = config.queue_timeout;
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

async function updateConfig() {
    const newTimeout = parseInt(elements.queueTimeoutInput.value);

    if (newTimeout < 10 || newTimeout > 3600) {
        alert('Queue timeout must be between 10 and 3600 seconds');
        return;
    }

    try {
        await apiCall('/config', 'POST', { queue_timeout: newTimeout });
        alert('Configuration updated successfully');
    } catch (error) {
        console.error('Failed to update config:', error);
    }
}

// Start the app
init();
