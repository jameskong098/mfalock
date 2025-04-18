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
                updateRotaryPosition(data.angle);
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
                
                // Ensure we pass the angle to our rotary lock system
                if (typeof updateRotaryPosition === 'function') {
                    updateRotaryPosition(data.angle);
                }
            }
        });
    }

    // Initialize rotary lock system
    initRotaryLock();
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

// Rotary Lock System
function initRotaryLock() {
    // Default color sequence password (can be changed in settings)
    let colorSequencePassword = localStorage.getItem('colorSequencePassword') || 
        JSON.stringify(['red', 'blue', 'green', 'yellow']);
    
    // Parse the stored password
    try {
        colorSequencePassword = JSON.parse(colorSequencePassword);
    } catch(e) {
        colorSequencePassword = ['red', 'blue', 'green', 'yellow'];
    }
    
    // State variables
    let currentPosition = 0; // 0-359 degrees
    let selectedQuadrant = null;
    let selectedColors = [];
    let selectionTimer = null;
    const SELECTION_DELAY = 3000; // 2 seconds to confirm selection
    const COLOR_POSITIONS = {
        'red': 0,       // Top
        'blue': 60,     // Top right
        'green': 120,   // Bottom right
        'purple': 180,  // Bottom
        'orange': 240,  // Bottom left
        'yellow': 300   // Top left
    };
    
    // Get quadrants
    const quadrants = document.querySelectorAll('.quadrant');
    const pointer = document.querySelector('.pointer');
    const colorPlaceholders = document.querySelectorAll('.color-placeholder');
    const rotaryStatus = document.getElementById('rotary-status');
    
    // Remove manual testing with mouse - only use rotary sensor input
    // Initialize the rotary position
    updateRotaryPosition(0);
    
    // Make updateRotaryPosition accessible globally for socket events
    window.updateRotaryPosition = function(angle) {
        // Update the pointer position
        if(pointer) {
            pointer.style.transform = `rotate(${angle}deg)`;
            currentPosition = angle;
        }
        
        // Determine which quadrant is selected
        const newSelectedQuadrant = getSelectedQuadrant(angle);
        
        // If quadrant changed, reset timer
        if(newSelectedQuadrant !== selectedQuadrant) {
            if(selectionTimer) {
                clearTimeout(selectionTimer);
                selectionTimer = null;
            }
            
            // Reset all quadrant highlight styles
            quadrants.forEach(q => q.classList.remove('selected'));
            
            // Highlight the new selected quadrant
            if(newSelectedQuadrant !== null) {
                quadrants[getQuadrantIndex(newSelectedQuadrant)].classList.add('selected');
                selectedQuadrant = newSelectedQuadrant;
                
                // Start timer for selection
                selectionTimer = setTimeout(() => {
                    selectCurrentQuadrant();
                }, SELECTION_DELAY);
            }
        }
    };
    
    // Function to update the rotary position and handle quadrant selection
    function updateRotaryPosition(angle) {
        // Update the pointer position
        if(pointer) {
            pointer.style.transform = `rotate(${angle}deg)`;
            currentPosition = angle;
        }
        
        // Determine which quadrant is selected
        const newSelectedQuadrant = getSelectedQuadrant(angle);
        
        // If quadrant changed, reset timer
        if(newSelectedQuadrant !== selectedQuadrant) {
            if(selectionTimer) {
                clearTimeout(selectionTimer);
                selectionTimer = null;
            }
            
            // Reset all quadrant highlight styles
            quadrants.forEach(q => q.classList.remove('selected'));
            
            // Highlight the new selected quadrant
            if(newSelectedQuadrant !== null) {
                quadrants[getQuadrantIndex(newSelectedQuadrant)].classList.add('selected');
                selectedQuadrant = newSelectedQuadrant;
                
                // Start timer for selection
                selectionTimer = setTimeout(() => {
                    selectCurrentQuadrant();
                }, SELECTION_DELAY);
            }
        }
    }
    
    // Function to get the quadrant index based on color name
    function getQuadrantIndex(colorName) {
        const colorArray = ['red', 'blue', 'green', 'yellow', 'purple', 'orange'];
        return colorArray.indexOf(colorName);
    }
    
    // Function to determine which quadrant is selected based on angle
    function getSelectedQuadrant(angle) {
        // Normalize angle to 0-360 range
        const normalizedAngle = (angle % 360 + 360) % 360;
        
        // Map angle to color quadrants
        if(normalizedAngle >= 330 || normalizedAngle < 30) return 'red';
        if(normalizedAngle >= 30 && normalizedAngle < 90) return 'blue';
        if(normalizedAngle >= 90 && normalizedAngle < 150) return 'green';
        if(normalizedAngle >= 150 && normalizedAngle < 210) return 'yellow';
        if(normalizedAngle >= 210 && normalizedAngle < 270) return 'purple';
        if(normalizedAngle >= 270 && normalizedAngle < 330) return 'orange';
        
        return null;
    }
    
    // Function to select the current quadrant and add its color to the sequence
    function selectCurrentQuadrant() {
        if(!selectedQuadrant) return;
        
        // Add color to selected sequence
        if(selectedColors.length < colorPlaceholders.length) {
            const colorIndex = selectedColors.length;
            selectedColors.push(selectedQuadrant);
            
            // Update the UI
            if(colorPlaceholders[colorIndex]) {
                colorPlaceholders[colorIndex].style.backgroundColor = getComputedStyle(
                    quadrants[getQuadrantIndex(selectedQuadrant)]
                ).backgroundColor;
                colorPlaceholders[colorIndex].classList.add('filled');
            }
            
            // Show animation
            quadrants[getQuadrantIndex(selectedQuadrant)].classList.remove('selected');
            setTimeout(() => {
                quadrants[getQuadrantIndex(selectedQuadrant)].classList.add('selected');
            }, 50);
            
            // Play a sound or give feedback 
            // (this would depend on your available sound API)
            
            // Check if sequence is complete
            if(selectedColors.length === colorPlaceholders.length) {
                setTimeout(() => {
                    checkColorSequence();
                }, 500);
            }
        }
        
        // Reset selection timer
        if(selectionTimer) {
            clearTimeout(selectionTimer);
            selectionTimer = null;
        }
    }
    
    // Function to check if the entered color sequence is correct
    function checkColorSequence() {
        let isCorrect = true;
        
        // Compare each color in the sequence
        for(let i = 0; i < colorSequencePassword.length; i++) {
            if(i >= selectedColors.length || colorSequencePassword[i] !== selectedColors[i]) {
                isCorrect = false;
                break;
            }
        }
        
        // Handle authentication result
        if(isCorrect) {
            // Success!
            rotaryStatus.textContent = "Authentication successful!";
            rotaryStatus.className = "status-message success";
            
            // Add to event log with Socket.IO
            if(typeof socket !== 'undefined') {
                socket.emit('auth_event', {
                    timestamp: new Date().toISOString(),
                    status: 'success',
                    message: 'Access granted: Rotary color sequence correct',
                    method: 'Rotary Lock',
                    user: 'User',
                    location: 'Main Entrance',
                    details: `Correct color sequence entered: ${selectedColors.join(', ')}`
                });
                
                // Increment authentication counter
                const successCountElement = document.getElementById('successful-auth-count');
                if(successCountElement) {
                    const currentCount = parseInt(successCountElement.textContent);
                    successCountElement.textContent = currentCount + 1;
                }
            }
            
            // Animate success
            quadrants.forEach(q => q.classList.remove('selected', 'correct', 'wrong'));
            colorPlaceholders.forEach(p => p.classList.add('correct'));
            
            setTimeout(() => resetColorSequence(), 2000);
        } else {
            // Failed!
            rotaryStatus.textContent = "Incorrect sequence, try again";
            rotaryStatus.className = "status-message error";
            
            // Add to event log with Socket.IO
            if(typeof socket !== 'undefined') {
                socket.emit('auth_event', {
                    timestamp: new Date().toISOString(),
                    status: 'failure',
                    message: 'Access denied: Incorrect rotary color sequence',
                    method: 'Rotary Lock',
                    user: 'Unknown',
                    location: 'Main Entrance',
                    details: `Incorrect color sequence: ${selectedColors.join(', ')}`
                });
                
                // Increment failure counter
                const failCountElement = document.getElementById('failed-auth-count');
                if(failCountElement) {
                    const currentCount = parseInt(failCountElement.textContent);
                    failCountElement.textContent = currentCount + 1;
                }
            }
            
            // Animate failure
            quadrants.forEach(q => q.classList.remove('selected', 'correct', 'wrong'));
            colorPlaceholders.forEach(p => p.classList.add('wrong'));
            
            setTimeout(() => resetColorSequence(), 2000);
        }
    }
    
    // Function to reset the color sequence for a new attempt
    function resetColorSequence() {
        selectedColors = [];
        
        // Reset UI
        colorPlaceholders.forEach(p => {
            p.style.backgroundColor = '';
            p.classList.remove('filled', 'correct', 'wrong');
        });
        
        quadrants.forEach(q => q.classList.remove('selected', 'correct', 'wrong'));
        
        rotaryStatus.textContent = "";
        rotaryStatus.className = "status-message";
    }
}