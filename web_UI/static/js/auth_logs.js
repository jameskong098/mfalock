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
        deleteButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this log?')) {
                // Send a DELETE request to the server to remove the log
                fetch(`/api/logs/${log.id}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
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
                            alert(`Error: ${data.message}`);
                        }
                    })
                    .catch(error => {
                        console.error('Error deleting log:', error);
                        alert('An error occurred while deleting the log.');
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
}