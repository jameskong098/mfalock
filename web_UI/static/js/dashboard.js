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

            // Add event to the live events list
            addEventToList(data);
        });
    }

    // Auth method selector functionality
    const authButtons = document.querySelectorAll('.auth-button');
    
    // Fetch current auth method
    fetch('/api/auth/method')
        .then(response => response.json())
        .then(data => {
            // Mark the active button
            authButtons.forEach(button => {
                if (button.dataset.method === data.method) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
                
                // Disable methods that aren't available
                if (!data.methods_available.includes(button.dataset.method)) {
                    button.classList.add('disabled');
                }
            });
        });
    
    // Handle auth method button clicks
    authButtons.forEach(button => {
        button.addEventListener('click', function() {
            const method = this.dataset.method;
            
            // Don't do anything if the button is disabled
            if (this.classList.contains('disabled')) {
                const notification = document.createElement('div');
                notification.className = 'notification error';
                notification.textContent = `${this.textContent} is not yet implemented`;
                document.querySelector('.auth-method-selector').insertAdjacentElement('beforebegin', notification);
                
                // Remove notification after 3 seconds
                setTimeout(() => notification.remove(), 3000);
                return;
            }
            
            // Update UI immediately
            authButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Send request to change auth method
            fetch('/api/auth/method', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ method: method })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const notification = document.createElement('div');
                    notification.className = 'notification success';
                    notification.textContent = `Switched to ${this.textContent}`;
                    document.querySelector('.auth-method-selector').insertAdjacentElement('beforebegin', notification);
                    
                    // Remove notification after 3 seconds
                    setTimeout(() => notification.remove(), 3000);
                } else {
                    throw new Error(data.message || 'Failed to change authentication method');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const notification = document.createElement('div');
                notification.className = 'notification error';
                notification.textContent = error.message;
                document.querySelector('.auth-method-selector').insertAdjacentElement('beforebegin', notification);
                
                // Remove notification after 3 seconds
                setTimeout(() => notification.remove(), 3000);
                
                // Revert UI
                this.classList.remove('active');
                fetch('/api/auth/method')
                    .then(response => response.json())
                    .then(data => {
                        document.querySelector(`.auth-button[data-method="${data.method}"]`).classList.add('active');
                    });
            });
        });
    });
});

// Modified function to add events to the live events list
function addEventToList(event) {
    const eventsContainer = document.getElementById('live-events');
    
    // Create the new event element
    const newEvent = document.createElement('li');
    newEvent.classList.add(event.status);
    
    // Format the time
    const timestamp = new Date(event.timestamp);
    const formattedTime = timestamp.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
    
    // Set the content
    newEvent.innerHTML = `
        <div class="event-time">${formattedTime}</div>
        <div class="event-message">${event.message}</div>
    `;
    
    // Add to the beginning of the list (newest on top)
    eventsContainer.insertBefore(newEvent, eventsContainer.firstChild);
    
    // Add fade-in effect
    setTimeout(() => {
        newEvent.classList.add('visible');
    }, 10);
    
    // Limit the number of displayed events (keep the list manageable)
    const maxEvents = 50;
    while (eventsContainer.children.length > maxEvents) {
        eventsContainer.removeChild(eventsContainer.lastChild);
    }
}