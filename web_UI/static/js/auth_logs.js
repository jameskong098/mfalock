// Authentication logs specific JavaScript

// Store logs globally
let authLogs = [];

document.addEventListener('DOMContentLoaded', function() {
    // Fetch log data
    fetch('/api/logs')
        .then(response => response.json())
        .then(data => {
            // Sort logs by timestamp in descending order (newest first)
            authLogs = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            populateLogs(authLogs);
            
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
        
        // Make sure filtered logs are also sorted by date (newest first)
        const filteredLogs = authLogs.filter(log => {
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
    });
    
    // Listen for real-time auth events
    if (typeof socket !== 'undefined') {
        socket.on('auth_event', function(data) {
            // Add to logs
            authLogs.unshift(data);
            
            // Re-apply current filters if any
            document.getElementById('filter-button').click();
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
        
        row.appendChild(timestampCell);
        row.appendChild(userCell);
        row.appendChild(locationCell);
        row.appendChild(statusCell);
        row.appendChild(detailsCell);
        
        tableBody.appendChild(row);
    });
}