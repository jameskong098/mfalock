// Authentication logs specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Fetch log data from the server and populate the table
    fetch('/api/logs')
        .then(response => response.json())
        .then(data => {
            // Sort logs by timestamp in descending order (newest first)
            const sortedLogs = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            populateLogs(sortedLogs);

            // Set today's date as default end date
            const today = new Date();
            const endDateInput = document.getElementById('end-date');
            endDateInput.valueAsDate = today;

            // Set one week ago as default start date
            const oneWeekAgo = new Date();
            oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
            const startDateInput = document.getElementById('start-date');
            startDateInput.valueAsDate = oneWeekAgo;
            
            // Add responsive classes for mobile
            addResponsiveListeners();
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
        });

    // Filter logs by search term and date range
    document.getElementById('filter-button').addEventListener('click', () => {
        const searchTerm = document.getElementById('log-search').value.toLowerCase();
        const startDate = document.getElementById('start-date').valueAsDate;
        const endDate = document.getElementById('end-date').valueAsDate;

        // Set end date to end of day
        if (endDate) {
            endDate.setHours(23, 59, 59, 999);
        }

        // Fetch logs again and apply filters
        fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                const filteredLogs = data.filter(log => {
                    const logTimestamp = new Date(log.timestamp);

                    const matchesSearch = !searchTerm ||
                        log.user.toLowerCase().includes(searchTerm) ||
                        log.location.toLowerCase().includes(searchTerm) ||
                        log.details.toLowerCase().includes(searchTerm);

                    const matchesDateRange = (!startDate || logTimestamp >= startDate) &&
                                             (!endDate || logTimestamp <= endDate);

                    return matchesSearch && matchesDateRange;
                }).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

                populateLogs(filteredLogs);
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
            });
    });

    // Listen for real-time auth events
    if (typeof socket !== 'undefined') {
        socket.on('auth_event', function(data) {
            // Fetch logs again to reflect the new event
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    const sortedLogs = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                    populateLogs(sortedLogs);
                })
                .catch(error => {
                    console.error('Error fetching logs:', error);
                });
        });
    }
    
    // Add responsive event listeners for mobile devices
    function addResponsiveListeners() {
        // Handle orientation changes to refresh table layout
        window.addEventListener('orientationchange', function() {
            setTimeout(function() {
                // Give browser time to repaint before potentially re-populating logs
                const tableBody = document.getElementById('log-table-body');
                if (tableBody.children.length > 0) {
                    fetch('/api/logs')
                        .then(response => response.json())
                        .then(data => {
                            const sortedLogs = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                            populateLogs(sortedLogs);
                        })
                        .catch(error => {
                            console.error('Error refreshing logs after orientation change:', error);
                        });
                }
            }, 200);
        });
    }
});

// Populate log table
function populateLogs(logs) {
    const tableBody = document.getElementById('log-table-body');
    tableBody.innerHTML = '';

    logs.forEach(log => {
        const row = document.createElement('tr');

        const timestampCell = document.createElement('td');
        timestampCell.textContent = formatDate(log.timestamp);

        const userCell = document.createElement('td');
        userCell.textContent = log.user;

        const locationCell = document.createElement('td');
        locationCell.textContent = log.location;

        const statusCell = document.createElement('td');
        statusCell.innerHTML = log.status === 'success' 
            ? '<span class="success"><i class="fas fa-check-circle"></i> Success</span>' 
            : '<span class="failure"><i class="fas fa-times-circle"></i> Failed</span>';

        const detailsCell = document.createElement('td');
        detailsCell.textContent = log.details;

        const deleteCell = document.createElement('td');
        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.className = 'btn delete-btn';
        deleteButton.setAttribute('aria-label', 'Delete log entry');
        deleteButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this log?')) {
                // Send a DELETE request to the server to remove the log
                fetch(`/api/logs/${log.id}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // Show feedback on mobile
                            if (window.innerWidth <= 768) {
                                showNotification('Log entry deleted successfully', 'success');
                            }
                            
                            // Fetch logs again to update the table
                            fetch('/api/logs')
                                .then(response => response.json())
                                .then(updatedLogs => {
                                    const sortedLogs = updatedLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                                    populateLogs(sortedLogs);
                                })
                                .catch(error => {
                                    console.error('Error fetching logs:', error);
                                });
                        } else {
                            showNotification(`Error: ${data.message}`, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error deleting log:', error);
                        showNotification('An error occurred while deleting the log.', 'error');
                    });
            }
        });
        deleteCell.appendChild(deleteButton);

        row.appendChild(timestampCell);
        row.appendChild(userCell);
        row.appendChild(locationCell);
        row.appendChild(statusCell);
        row.appendChild(detailsCell);
        row.appendChild(deleteCell);

        tableBody.appendChild(row);
    });
    
    // If no logs found
    if (logs.length === 0) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 6;
        emptyCell.textContent = 'No logs found matching your criteria';
        emptyCell.style.textAlign = 'center';
        emptyCell.style.padding = '20px';
        emptyRow.appendChild(emptyCell);
        tableBody.appendChild(emptyRow);
    }
}

// Display notification for mobile feedback
function showNotification(message, type) {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create and add the new notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add to the top of the auth-logs section
    const authLogsSection = document.getElementById('auth-logs');
    authLogsSection.insertBefore(notification, authLogsSection.firstChild);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 3000);
}

// If formatDate function is missing, define it
if (typeof formatDate !== 'function') {
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}