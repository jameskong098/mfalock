// Dashboard specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const successCountElement = document.getElementById('successful-auth-count');
    const failCountElement = document.getElementById('failed-auth-count');
    const currentDateElement = document.getElementById('current-date');

    // Display the current date in the header
    const currentDate = new Date().toLocaleDateString();
    currentDateElement.textContent = currentDate;

    // Fetch logs for the current day and update counters
    fetch('/api/logs')
        .then(response => response.json())
        .then(data => {
            const today = new Date().toISOString().split('T')[0]; // Get today's date in YYYY-MM-DD format
            let successCount = 0;
            let failCount = 0;

            // Filter logs for the current day
            data.forEach(log => {
                const logDate = new Date(log.timestamp).toISOString().split('T')[0];
                if (logDate === today) {
                    if (log.status === 'success') {
                        successCount++;
                    } else if (log.status === 'failure') {
                        failCount++;
                    }
                }
            });

            // Update the dashboard counters
            successCountElement.textContent = successCount;
            failCountElement.textContent = failCount;
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
        });

    // Listen for real-time auth events
    if (typeof socket !== 'undefined') {
        socket.on('auth_event', function(data) {
            const eventDate = new Date(data.timestamp).toISOString().split('T')[0];
            const today = new Date().toISOString().split('T')[0];

            // Update counters only if the event is for the current day
            if (eventDate === today) {
                if (data.status === 'success') {
                    successCountElement.textContent = parseInt(successCountElement.textContent) + 1;
                } else if (data.status === 'failure') {
                    failCountElement.textContent = parseInt(failCountElement.textContent) + 1;
                }
            }
        });
    }
});