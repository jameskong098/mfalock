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
            
            // Populate the live events list with the 10 most recent events
            const recentEvents = [...data]
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                .slice(0, 10);
                
            // Clear any existing events
            const eventsContainer = document.getElementById('live-events');
            eventsContainer.innerHTML = '';
            
            // Loop through events in reverse order so the newest appears at the top when using prepend
            // This preserves the same order as the real-time events
            for (let i = recentEvents.length - 1; i >= 0; i--) {
                addEventToList(recentEvents[i]);
            }
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
        });

    // Fetch initial sensor mode from server
    fetch('/api/sensor_mode')
        .then(response => response.json())
        .then(data => {
            updateSensorModeUI(data.mode);
        })
        .catch(error => console.error('Error fetching sensor mode:', error));
    
    // Set up socket event listeners
    if (typeof socket !== 'undefined') {
        // Listen for sensor mode change events
        socket.on('sensor_mode_change', function(data) {
            updateSensorModeUI(data.mode);
        });
        
        // Listen for rotary angle updates
        socket.on('rotary_update', function(data) {
            const rotaryDisplay = document.getElementById('rotary-angle-display');
            if (rotaryDisplay) {
                rotaryDisplay.textContent = `${data.angle}°`;
                
                // Animate a dial or other visual
                const rotaryDial = document.getElementById('rotary-dial');
                if (rotaryDial) {
                    rotaryDial.style.transform = `rotate(${data.angle}deg)`;
                }
            }
        });
    }

    // Listen for real-time auth events
    if (typeof socket !== 'undefined') {      
        // Add tracking for last event to prevent duplicates
        let lastEventTime = null;
        let lastEventStatus = null;
        const DUPLICATE_THRESHOLD_MS = 2000; // 2 seconds
        
        socket.on('auth_event', function(data) {
            const eventDate = new Date(data.timestamp).toISOString().split('T')[0];
            const today = new Date().toISOString().split('T')[0];
            const currentTime = new Date().getTime();
            
            // Update tracking variables
            lastEventTime = currentTime;
            lastEventStatus = data.status;

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

    // Fetch initial sensor mode from server
    fetch('/api/sensor_mode')
        .then(response => response.json())
        .then(data => {
            updateSensorModeUI(data.mode);
        })
        .catch(error => console.error('Error fetching sensor mode:', error));
    
    // Set up socket event listeners
    if (typeof socket !== 'undefined') {
        // Listen for sensor mode change events
        socket.on('sensor_mode_change', function(data) {
            updateSensorModeUI(data.mode);
        });
        
        // Listen for rotary angle updates
        socket.on('rotary_update', function(data) {
            const rotaryDisplay = document.getElementById('rotary-angle-display');
            if (rotaryDisplay) {
                rotaryDisplay.textContent = `${data.angle}°`;
                
                // Optional: animate a dial or other visual
                const rotaryDial = document.getElementById('rotary-dial');
                if (rotaryDial) {
                    rotaryDial.style.transform = `rotate(${data.angle}deg)`;
                }
            }
        });
    }
});

// Modified function to add events to the live events list
function addEventToList(event) {
    const eventsContainer = document.getElementById('live-events');

    // Create the new event element
    const newEvent = document.createElement('li');
    newEvent.classList.add(event.status);

    // Ensure timestamp is properly formatted
    let timestamp;
    try {
        timestamp = new Date(event.timestamp);
        if (isNaN(timestamp.getTime())) {
            console.warn('Invalid timestamp in event, using current time instead');
            timestamp = new Date();
        }
    } catch (e) {
        console.warn('Error parsing timestamp, using current time instead');
        timestamp = new Date();
    }

    // Format the time for display
    const formattedTime = `${timestamp.toLocaleDateString('en-US')} ${timestamp.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    })}`;

    // Create a visual status indicator
    const statusBadge = `<div class="event-status-badge ${event.status}">${event.status}</div>`;

    // Set the content
    newEvent.innerHTML = `
    <div class="event-time">${formattedTime}</div>
    <div class="event-content">
        <div class="event-message">${event.message || 'Authentication attempt'}</div>
        ${statusBadge}
    </div>
    `;

    // Add the new event to the top of the container
    eventsContainer.prepend(newEvent);

    // Limit the number of displayed events
    const maxEvents = 50;
    while (eventsContainer.children.length > maxEvents) {
        eventsContainer.removeChild(eventsContainer.lastChild);
    }
}

// Function to update UI based on the current sensor mode
function updateSensorModeUI(mode) {
    // Update authentication method buttons/displays
    const touchMethodElem = document.getElementById('touch-method');
    const rotaryMethodElem = document.getElementById('rotary-method');
    
    if (touchMethodElem && rotaryMethodElem) {
        if (mode === 'touch') {
            touchMethodElem.classList.add('active');
            rotaryMethodElem.classList.remove('active');
            document.querySelectorAll('.touch-instructions').forEach(el => el.style.display = 'block');
            document.querySelectorAll('.rotary-instructions').forEach(el => el.style.display = 'none');
        } else if (mode === 'rotary') {
            touchMethodElem.classList.remove('active');
            rotaryMethodElem.classList.add('active');
            document.querySelectorAll('.touch-instructions').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.rotary-instructions').forEach(el => el.style.display = 'block');
        }
    }
    
    // Update any other UI elements that should change based on sensor mode
    const sensorModeIndicator = document.getElementById('current-sensor-mode');
    if (sensorModeIndicator) {
        sensorModeIndicator.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
        sensorModeIndicator.className = `mode-indicator ${mode}-mode`;
    }
}