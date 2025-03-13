// Common JavaScript functions used across all pages

// Function to format date for display
function formatDate(date) {
    return new Date(date).toLocaleString();
}

// WebSocket connection for real-time updates
let socket;
// Status check interval (in milliseconds)
const STATUS_CHECK_INTERVAL = 2000;
let statusCheckTimer;

document.addEventListener('DOMContentLoaded', function() {
    // Initial status check
    checkPicoStatus();
    
    // Setup periodic status checking
    statusCheckTimer = setInterval(checkPicoStatus, STATUS_CHECK_INTERVAL);
    
    // Setup WebSocket connection if SocketIO is available
    if (typeof io !== 'undefined') {
        socket = io.connect(window.location.origin);
        
        socket.on('connect', function() {
            console.log('WebSocket connected');
        });
        
        socket.on('disconnect', function() {
            console.log('WebSocket disconnected');
        });
        
        socket.on('status_update', function(data) {
            updateStatusIndicators(data);
        });
        
        socket.on('auth_event', function(data) {
            displayLiveEvent(data);
        });
    }
});

// Check Pico status via API endpoint
function checkPicoStatus() {
    fetch('/api/pico_status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicators(data);
        })
        .catch(error => {
            console.error('Error fetching Pico status:', error);
        });
}

// Update status indicators based on data from server
function updateStatusIndicators(data) {
    const picoStatus = document.getElementById('pico-status');
    if (picoStatus) {
        const wasConnected = picoStatus.classList.contains('success');
        const isNowConnected = data.pico_connected;
        
        picoStatus.className = 'status-indicator ' + (isNowConnected ? 'success' : 'failure');
        picoStatus.querySelector('.status-text').textContent = isNowConnected ? 'Pico Connected' : 'Pico Disconnected';
        
        if (wasConnected !== isNowConnected) {
            picoStatus.classList.add('status-changed');
            setTimeout(() => {
                picoStatus.classList.remove('status-changed');
            }, 600);
        }
    }
    
    // Update auth counts if available on the current page
    const successCount = document.getElementById('successful-auth-count');
    if (successCount && data.auth_success_count !== undefined) {
        successCount.textContent = data.auth_success_count;
    }
    
    const failCount = document.getElementById('failed-auth-count');
    if (failCount && data.auth_failure_count !== undefined) {
        failCount.textContent = data.auth_failure_count;
    }
}

// Display live authentication events
function displayLiveEvent(event) {
    const liveEventsList = document.getElementById('live-events');
    if (liveEventsList) {
        const eventItem = document.createElement('li');
        eventItem.className = event.status === 'success' ? 'success-event' : 'failure-event';
        eventItem.textContent = `${formatDate(event.timestamp)}: ${event.status.toUpperCase()} - ${event.details}`;
        
        // Add to the beginning of the list
        if (liveEventsList.firstChild) {
            liveEventsList.insertBefore(eventItem, liveEventsList.firstChild);
        } else {
            liveEventsList.appendChild(eventItem);
        }
        
        // Limit the number of visible events
        if (liveEventsList.children.length > 100) {
            liveEventsList.removeChild(liveEventsList.lastChild);
        }
    }
}