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
            
            // Add each event to the list (newest first)
            recentEvents.forEach(event => {
                // Create message property if missing in log data
                if (!event.message) {
                    event.message = event.status === 'success' 
                        ? 'Access granted: Pattern recognized correctly' 
                        : 'Access denied: Incorrect pattern';
                }
                addEventToList(event);
            });
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
        console.log('Setting up auth_event listener');
        socket.on('auth_event', function(data) {
            console.log('Received auth event:', data);
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

            // Add event to the live events list (sorting happens inside this function)
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
    console.log('Adding event:', event);
    const eventsContainer = document.getElementById('live-events');
    
    // Create the new event element
    const newEvent = document.createElement('li');
    newEvent.classList.add(event.status);
    
    // Ensure timestamp is properly formatted
    let timestamp;
    try {
        timestamp = new Date(event.timestamp);
        if (isNaN(timestamp.getTime())) {
            // If timestamp is invalid, use current time
            console.warn('Invalid timestamp in event, using current time instead');
            timestamp = new Date();
        }
    } catch (e) {
        console.warn('Error parsing timestamp, using current time instead');
        timestamp = new Date();
    }
    
    // Store the timestamp as numeric value for sorting
    newEvent.dataset.timestamp = timestamp.getTime();
    
    // Format the time for display
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
    
    // Add the event to the list
    eventsContainer.appendChild(newEvent);
    
    // Get all events and convert timestamps to numbers for reliable sorting
    const allEvents = Array.from(eventsContainer.children).map(el => {
        // Ensure timestamp is a number
        if (!el.dataset.timestamp) {
            el.dataset.timestamp = Date.now();
        }
        return el;
    });
    
    // Sort by timestamp (newest first)
    allEvents.sort((a, b) => {
        return Number(b.dataset.timestamp) - Number(a.dataset.timestamp);
    });
    
    // Clear and rebuild the list in sorted order
    eventsContainer.innerHTML = '';
    allEvents.forEach(event => {
        eventsContainer.appendChild(event);
        // Re-add the visible class for animation
        setTimeout(() => {
            event.classList.add('visible');
        }, 10);
    });
    
    // Limit the number of displayed events
    const maxEvents = 50;
    while (eventsContainer.children.length > maxEvents) {
        eventsContainer.removeChild(eventsContainer.lastChild);
    }
}

// Function to update UI based on the current sensor mode
function updateSensorModeUI(mode) {
    console.log('Sensor mode changed to:', mode);
    
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