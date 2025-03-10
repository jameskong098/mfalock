// Common JavaScript functions used across all pages

// Function to format date for display
function formatDate(date) {
    return new Date(date).toLocaleString();
}

// WebSocket connection for real-time updates
let socket;

document.addEventListener('DOMContentLoaded', function() {
    // Setup WebSocket connection if SocketIO is available
    if (typeof io !== 'undefined') {
        socket = io.connect(window.location.origin);
        
        socket.on('connect', function() {
            console.log('WebSocket connected');
        });
        
        socket.on('status_update', function(data) {
            updateStatusIndicators(data);
        });
    }
});

// Update status indicators based on data from server
function updateStatusIndicators(data) {
    const picoStatus = document.getElementById('pico-status');
    if (picoStatus) {
        picoStatus.textContent = data.pico_connected ? 'Connected' : 'Disconnected';
        picoStatus.className = data.pico_connected ? 'success' : 'failure';
    }
    
    // Update auth counts if available on the current page
    const successCount = document.getElementById('successful-auth-count');
    if (successCount) {
        successCount.textContent = data.auth_success_count;
    }
    
    const failCount = document.getElementById('failed-auth-count');
    if (failCount) {
        failCount.textContent = data.auth_failure_count;
    }
}