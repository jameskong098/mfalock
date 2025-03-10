// Dashboard specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Fetch initial status
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicators(data);
        })
        .catch(error => {
            console.error('Error fetching status:', error);
        });
        
    // Listen for real-time auth events
    if (typeof socket !== 'undefined') {
        socket.on('auth_event', function(data) {
            // Update counters
            const successCount = document.getElementById('successful-auth-count');
            const failCount = document.getElementById('failed-auth-count');
            
            if (data.status === 'success') {
                successCount.textContent = parseInt(successCount.textContent) + 1;
            } else {
                failCount.textContent = parseInt(failCount.textContent) + 1;
            }
        });
    }
});