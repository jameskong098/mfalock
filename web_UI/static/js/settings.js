// Settings page functionality

document.addEventListener('DOMContentLoaded', function() {
    // Make patternSteps accessible to form submission handler
    window.patternSteps = [];
    let isRecording = false;
    let isTouching = false;
    let touchStartTime = 0;
    let recordButton = document.getElementById('record-pattern');
    let clearButton = document.getElementById('clear-pattern');
    let patternSensor = document.getElementById('pattern-sensor');
    
    // Load current settings
    fetch('/api/settings')
        .then(response => {
            if (!response.ok) {
                throw new Error('Settings not available');
            }
            return response.json();
        })
        .then(settings => {
            // Populate form with current settings
            document.getElementById('security-level').value = settings.securityLevel || 'high';
            document.getElementById('notification-email').value = settings.notificationEmail || '';
            document.getElementById('notify-success').checked = settings.notifySuccess || false;
            document.getElementById('notify-failure').checked = settings.notifyFailure || true;
            
            // Load custom pattern
            if (settings.customPattern && settings.customPattern.length > 0) {
                // Remove the initial default step
                const patternContainer = document.getElementById('pattern-container');
                patternContainer.innerHTML = '';
                
                // Add each step from the saved pattern
                settings.customPattern.forEach((step, index) => {
                    addPatternStep(step.action, step.duration);
                });
                
                // Show pattern in the visual representation
                updatePatternStepsDisplay(settings.customPattern);
            }
        })
        .catch(error => {
            console.warn('Could not load settings:', error);
        });
    
    // Toggle between interactive and manual pattern creation
    document.getElementById('toggle-manual-entry').addEventListener('click', function() {
        const manualContainer = document.getElementById('manual-pattern-container');
        const patternRecorder = document.getElementById('pattern-recorder');
        
        if (manualContainer.style.display === 'none') {
            manualContainer.style.display = 'block';
            patternRecorder.style.display = 'none';
            this.textContent = 'Interactive Entry';
        } else {
            manualContainer.style.display = 'none';
            patternRecorder.style.display = 'block';
            this.textContent = 'Manual Entry';
        }
    });
    
    // Handle adding pattern steps
    document.getElementById('add-step').addEventListener('click', function() {
        addPatternStep();
    });
    
    // Handle removing pattern steps
    document.getElementById('pattern-container').addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-step')) {
            const stepElement = event.target.closest('.pattern-step');
            
            // Don't remove if it's the only step
            if (document.querySelectorAll('.pattern-step').length > 1) {
                stepElement.remove();
                // Update indices
                updateStepIndices();
                // Update interactive pattern display
                syncManualToInteractive();
            } else {
                alert('Pattern must have at least one step');
            }
        }
    });
    
    // Interactive pattern recording variables
    
    // Start/stop recording pattern
    recordButton.addEventListener('click', function() {
        if (!isRecording) {
            // Start recording
            window.patternSteps = []; // Use window.patternSteps instead of local patternSteps
            updatePatternStepsDisplay(window.patternSteps);
            isRecording = true;
            patternSensor.classList.add('recording');
            this.textContent = 'Stop Recording';
            this.classList.add('active');
        } else {
            // Stop recording
            isRecording = false;
            patternSensor.classList.remove('recording');
            this.textContent = 'Start Recording';
            this.classList.remove('active');
            
            // Sync to manual inputs
            syncInteractiveToManual();
        }
    });
    
    // Clear recorded pattern
    clearButton.addEventListener('click', function() {
        window.patternSteps = [];
        updatePatternStepsDisplay(window.patternSteps);
        
        // If in manual mode, clear that too
        const patternContainer = document.getElementById('pattern-container');
        patternContainer.innerHTML = '';
        addPatternStep(); // Add default empty step
    });
    
    // Handle pattern sensor touch start
    patternSensor.addEventListener('mousedown', function(e) {
        if (!isRecording) return;
        
        isTouching = true;
        touchStartTime = Date.now();
        patternSensor.classList.add('touching');
    });
    
    // Handle pattern sensor touch end
    patternSensor.addEventListener('mouseup', function(e) {
        if (!isRecording || !isTouching) return;
        
        const touchDuration = Date.now() - touchStartTime;
        isTouching = false;
        patternSensor.classList.remove('touching');
        
        // Determine if this was a tap or hold
        const action = touchDuration < 500 ? 'tap' : 'hold';
        const duration = action === 'tap' ? 0 : touchDuration;
        
        // Add this step to our pattern
        window.patternSteps.push({ action, duration });
        updatePatternStepsDisplay(window.patternSteps);
    });
    
    // Touch events for mobile devices
    patternSensor.addEventListener('touchstart', function(e) {
        e.preventDefault();
        if (!isRecording) return;
        
        isTouching = true;
        touchStartTime = Date.now();
        patternSensor.classList.add('touching');
    });
    
    patternSensor.addEventListener('touchend', function(e) {
        e.preventDefault();
        if (!isRecording || !isTouching) return;
        
        const touchDuration = Date.now() - touchStartTime;
        isTouching = false;
        patternSensor.classList.remove('touching');
        
        // Determine if this was a tap or hold
        const action = touchDuration < 500 ? 'tap' : 'hold';
        const duration = action === 'tap' ? 0 : touchDuration;
        
        // Add this step to our pattern
        window.patternSteps.push({ action, duration });
        updatePatternStepsDisplay(window.patternSteps);
    });
    
    // Update the visual pattern steps display
    function updatePatternStepsDisplay(steps) {
        const container = document.getElementById('pattern-steps');
        container.innerHTML = '';
        
        if (steps.length === 0) {
            container.innerHTML = '<p class="empty-pattern">No steps recorded</p>';
            return;
        }
        
        steps.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = `pattern-step-visual ${step.action}`;
            
            const iconSpan = document.createElement('span');
            iconSpan.className = 'step-icon';
            iconSpan.textContent = step.action === 'tap' ? '👆' : '👇';
            
            const textSpan = document.createElement('span');
            textSpan.className = 'step-text';
            textSpan.textContent = step.action === 'tap' 
                ? `Step ${index + 1}: Tap` 
                : `Step ${index + 1}: Hold (${step.duration}ms)`;
            
            stepElement.appendChild(iconSpan);
            stepElement.appendChild(textSpan);
            container.appendChild(stepElement);
        });
    }
    
    // Sync interactive pattern to manual form inputs
    function syncInteractiveToManual() {
        // Clear existing manual steps
        const patternContainer = document.getElementById('pattern-container');
        patternContainer.innerHTML = '';
        
        // If no steps, add a default one
        if (window.patternSteps.length === 0) {
            addPatternStep();
            return;
        }
        
        // Add each recorded step to the manual form
        window.patternSteps.forEach(step => {
            addPatternStep(step.action, step.duration);
        });
    }
    
    // Sync manual form inputs to interactive pattern
    function syncManualToInteractive() {
        window.patternSteps = [];
        
        document.querySelectorAll('.pattern-step').forEach(step => {
            const action = step.querySelector('.pattern-action').value;
            const duration = parseInt(step.querySelector('.pattern-duration').value) || 0;
            window.patternSteps.push({ action, duration });
        });
        
        updatePatternStepsDisplay(window.patternSteps);
    }
    
    // When manual inputs change, update interactive display
    document.getElementById('pattern-container').addEventListener('change', function(event) {
        if (event.target.classList.contains('pattern-action') || 
            event.target.classList.contains('pattern-duration')) {
            syncManualToInteractive();
        }
    });
    
    // Handle settings form submission
    document.getElementById('settings-form').addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Show a loading indicator
        const submitButton = this.querySelector('button[type="submit"]');
        if (submitButton) {
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Saving...';
            submitButton.disabled = true;
        }
        
        let formPatternSteps = [];
        
        // Check which mode is active
        const manualContainer = document.getElementById('manual-pattern-container');
        const isManualMode = manualContainer.style.display !== 'none';
        
        if (isManualMode) {
            // Get pattern from manual inputs
            document.querySelectorAll('.pattern-step').forEach(step => {
                const actionElement = step.querySelector('.pattern-action');
                const durationElement = step.querySelector('.pattern-duration');
                
                if (actionElement && durationElement) {
                    const action = actionElement.value;
                    const duration = parseInt(durationElement.value) || 0;
                    formPatternSteps.push({ action, duration });
                }
            });
        } else {
            // Get pattern from interactive recording
            formPatternSteps = window.patternSteps.slice();
        }
        
        // If no steps, use default pattern
        if (formPatternSteps.length === 0) {
            formPatternSteps = [
                { action: 'tap', duration: 0 },
                { action: 'hold', duration: 1000 },
                { action: 'tap', duration: 0 }
            ];
        }
        
        const formData = {
            securityLevel: document.getElementById('security-level')?.value || 'high',
            notificationEmail: document.getElementById('notification-email')?.value || '',
            notifySuccess: document.getElementById('notify-success')?.checked || false,
            notifyFailure: document.getElementById('notify-failure')?.checked || true,
            customPattern: formPatternSteps
        };
        
        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.message || 'Could not save settings');
                });
            }
            return response.json();
        })
        .then(data => {
            // Create a notification element
            const notification = document.createElement('div');
            notification.className = 'notification success';
            
            let message = 'Settings saved successfully!';
            
            // Add additional details if available
            if (data.pattern_saved === true) {
                message += ' Pattern saved to JSON file.';
            }
            
            if (data.pico_connected === false) {
                message += ' Note: Pico device is not connected. Pattern will update when connected.';
            } else if (data.pattern_updated_on_device === true) {
                message += ' Pattern updated on device.';
            } else if (data.pattern_updated_on_device === false) {
                message += ' Warning: Failed to update pattern on device.';
            }
            
            notification.textContent = message;
            
            // Add the notification to the page
            const settingsCard = document.querySelector('#settings .card');
            if (settingsCard) {
                settingsCard.insertBefore(notification, settingsCard.firstChild);
                
                // Remove the notification after 5 seconds
                setTimeout(() => {
                    notification.classList.add('fade-out');
                    setTimeout(() => notification.remove(), 500);
                }, 5000);
            }
            
            console.log('Settings saved:', data);
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            
            // Create an error notification
            const notification = document.createElement('div');
            notification.className = 'notification error';
            notification.textContent = 'Error saving settings: ' + error.message;
            
            // Add the notification to the page
            const settingsCard = document.querySelector('#settings .card');
            if (settingsCard) {
                settingsCard.insertBefore(notification, settingsCard.firstChild);
                
                // Remove the notification after 5 seconds
                setTimeout(() => {
                    notification.classList.add('fade-out');
                    setTimeout(() => notification.remove(), 500);
                }, 5000);
            }
        })
        .finally(() => {
            // Restore the button
            if (submitButton) {
                submitButton.textContent = 'Save Settings';
                submitButton.disabled = false;
            }
        });
    });
    
    // Function to add a new pattern step
    function addPatternStep(action = 'tap', duration = 0) {
        const patternContainer = document.getElementById('pattern-container');
        const index = document.querySelectorAll('.pattern-step').length;
        
        const stepElement = document.createElement('div');
        stepElement.className = 'pattern-step';
        stepElement.dataset.index = index;
        
        stepElement.innerHTML = `
            <select class="pattern-action">
                <option value="tap" ${action === 'tap' ? 'selected' : ''}>Tap</option>
                <option value="hold" ${action === 'hold' ? 'selected' : ''}>Hold</option>
            </select>
            <input type="number" class="pattern-duration" min="0" max="5000" step="1" value="${duration}" placeholder="Duration (ms)">
            <button type="button" class="btn small remove-step">Remove</button>
        `;
        
        patternContainer.appendChild(stepElement);
        
        // Add event listener to show/hide duration input based on action
        const actionSelect = stepElement.querySelector('.pattern-action');
        const durationInput = stepElement.querySelector('.pattern-duration');
        
        actionSelect.addEventListener('change', function() {
            if (this.value === 'tap') {
                durationInput.value = '0';
                durationInput.disabled = true;
            } else {
                durationInput.disabled = false;
                if (durationInput.value === '0') {
                    durationInput.value = '1000';
                }
            }
        });
        
        // Initially set duration input state based on action
        if (action === 'tap') {
            durationInput.disabled = true;
        }
    }
    
    // Function to update step indices after removal
    function updateStepIndices() {
        document.querySelectorAll('.pattern-step').forEach((step, index) => {
            step.dataset.index = index;
        });
    }
});