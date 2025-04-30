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
    let currentPatternStepsContainer = document.getElementById('current-pattern-steps'); 
    let recordingPatternStepsContainer = document.getElementById('pattern-steps'); 

    // Initialize the manual pattern entry with one default step
    const patternContainer = document.getElementById('pattern-container');
    if (patternContainer) {
        patternContainer.innerHTML = ''; // Clear any default HTML
        addPatternStep(); // Add a single default step for manual entry
    } else {
        console.error("Manual pattern container ('#pattern-container') not found!");
    }

    // Load current settings
    fetch('/api/settings')
        .then(response => {
            if (!response.ok) {
                response.text().then(text => console.error("API Error Response:", text));
                throw new Error(`Settings not available: ${response.statusText}`);
            }
            return response.json();
        })
        .then(settings => {
            // Load custom pattern
            console.log("Attempting to load custom pattern:", settings.customPattern);
            if (!currentPatternStepsContainer) {
                console.error("Element with ID 'current-pattern-steps' not found!");
            } else {
                if (settings.customPattern && settings.customPattern.length > 0) {
                    console.log("Calling updatePatternStepsDisplay for current pattern");
                    updatePatternStepsDisplay(settings.customPattern, currentPatternStepsContainer); // Updates the display
                } else {
                    console.log("No custom pattern found or empty, updating display.");
                    updatePatternStepsDisplay([], currentPatternStepsContainer); // Show empty state in the display
                }
            }
            
            // Load rotary color sequence if available
            console.log("Attempting to load color sequence:", settings.colorSequence);
            const currentSequenceContainer = document.getElementById('current-color-sequence');
            if (!currentSequenceContainer) {
                 console.error("Element with ID 'current-color-sequence' not found! Was the card added dynamically?");
            }

            if (settings.colorSequence && settings.colorSequence.length > 0) {
                console.log("Calling populateEditableColorSequence");
                populateEditableColorSequence(settings.colorSequence); // Populate the editor
                console.log("Calling updateCurrentColorSequenceDisplay");
                updateCurrentColorSequenceDisplay(settings.colorSequence); // Populate the display
            } else {
                console.log("No color sequence found or empty, using default.");
                const defaultColorSequence = ['red', 'blue', 'green', 'yellow'];
                populateEditableColorSequence(defaultColorSequence);
                updateCurrentColorSequenceDisplay(defaultColorSequence);
            }
        })
        .catch(error => {
            console.error('Error fetching or processing settings:', error);
            // Attempt to clear displays even on error
            if (currentPatternStepsContainer) updatePatternStepsDisplay([], currentPatternStepsContainer);
            const currentSequenceContainer = document.getElementById('current-color-sequence');
            if (currentSequenceContainer) updateCurrentColorSequenceDisplay([]);
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
            updatePatternStepsDisplay(window.patternSteps, recordingPatternStepsContainer); // Update recording preview
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
        updatePatternStepsDisplay(window.patternSteps, recordingPatternStepsContainer); // Clear recording preview
        
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
        updatePatternStepsDisplay(window.patternSteps, recordingPatternStepsContainer); // Update recording preview
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
        updatePatternStepsDisplay(window.patternSteps, recordingPatternStepsContainer); // Update recording preview
    });
    
    // Update the visual pattern steps display
    function updatePatternStepsDisplay(steps, container) {
        if (!container) {
            console.error("Target container for pattern display not provided.");
            return;
        }
        container.innerHTML = ''; // Clear previous content

        if (!steps || steps.length === 0) {
            container.innerHTML = `<p class="empty-pattern">${container.id === 'current-pattern-steps' ? 'No pattern saved.' : 'No steps recorded'}</p>`;
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
    function syncInteractiveToManual(patternToSync = window.patternSteps) { // Accept optional pattern
        // Clear existing manual steps
        const patternContainer = document.getElementById('pattern-container');
        patternContainer.innerHTML = '';

        // If no steps, add a default one
        if (patternToSync.length === 0) {
            addPatternStep();
            return;
        }

        // Add each recorded step to the manual form
        patternToSync.forEach(step => {
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
        
        updatePatternStepsDisplay(window.patternSteps, recordingPatternStepsContainer); // Update recording preview
    }
    
    // When manual inputs change, update interactive display
    document.getElementById('pattern-container').addEventListener('change', function(event) {
        if (event.target.classList.contains('pattern-action') || 
            event.target.classList.contains('pattern-duration')) {
            syncManualToInteractive();
        }
    });
    
    // === Rotary Color Sequence Configuration ===
    
    // Add color sequence section to the settings form if it doesn't exist
    const settingsForm = document.getElementById('settings-form'); // Target the global save form
    const colorSettingsCard = document.createElement('div'); // Create a new card for color settings
    colorSettingsCard.className = 'card settings-section'; // Use card styling

    if (settingsForm && !document.querySelector('.color-sequence-card')) { // Check for a unique class
        colorSettingsCard.classList.add('color-sequence-card'); // Add unique class
        colorSettingsCard.innerHTML = `
            <h3>Rotary Color Sequence</h3>
            <div class="form-group">
                <!-- Display Current Sequence -->
                <div id="current-color-sequence-display-container">
                    <h4>Current Saved Sequence:</h4>
                    <div id="current-color-sequence" class="color-sequence-display">
                        <!-- Loaded sequence will be displayed here -->
                        <p class="empty-pattern">Loading sequence...</p>
                    </div>
                </div>
                <hr> <!-- Separator -->

                <label>Configure New Sequence:</label>
                <p class="help-text">Select up to 4 colors in order. Click a color below to add it to the sequence. Click '✕' to remove.</p>
                <div class="color-sequence-container">
                    <div class="color-sequence editable" id="editable-color-sequence">
                        <!-- Editable color sequence will be populated here -->
                    </div>
                    <div class="color-select-grid">
                        <div class="color-select" data-color="red">
                            <div class="color-circle" style="background-color: #FF6B6B;"></div>
                            <span>Red</span>
                        </div>
                        <div class="color-select" data-color="blue">
                            <div class="color-circle" style="background-color: #4ECDC4;"></div>
                            <span>Blue</span>
                        </div>
                        <div class="color-select" data-color="green">
                            <div class="color-circle" style="background-color: #59CD90;"></div>
                            <span>Green</span>
                        </div>
                        <div class="color-select" data-color="yellow">
                            <div class="color-circle" style="background-color: #EAC435;"></div>
                            <span>Yellow</span>
                        </div>
                        <div class="color-select" data-color="purple">
                            <div class="color-circle" style="background-color: #9370DB;"></div>
                            <span>Purple</span>
                        </div>
                        <div class="color-select" data-color="orange">
                            <div class="color-circle" style="background-color: #FF9F1C;"></div>
                            <span>Orange</span>
                        </div>
                    </div>
                    <button type="button" id="reset-sequence" class="btn small">Reset Sequence</button>
                </div>
            </div>
        `;

        // Insert the new card before the global save button card
        const globalSaveCard = settingsForm.closest('.card'); // Find the card containing the save button
        if (globalSaveCard && globalSaveCard.parentNode) {
             globalSaveCard.parentNode.insertBefore(colorSettingsCard, globalSaveCard);
        } else {
             // Fallback: append to the main settings section if structure is different
             const settingsSection = document.getElementById('settings');
             if (settingsSection) {
                 settingsSection.appendChild(colorSettingsCard);
             } else {
                 console.error("Could not find suitable location to insert color settings card.");
             }
        }


        // Add event listeners for color selection (targets the editable sequence)
        document.querySelectorAll('.color-select').forEach(colorSelect => {
            colorSelect.addEventListener('click', function() {
                const color = this.dataset.color;
                const editableColorSequence = document.getElementById('editable-color-sequence');
                const currentPositions = editableColorSequence.querySelectorAll('.sequence-position');

                // Maximum of 4 colors in the sequence
                if (currentPositions.length < 4) {
                    addColorToEditableSequence(color);
                }
            });
        });

        // Add event listener for resetting the editable sequence
        document.getElementById('reset-sequence').addEventListener('click', function() {
            const editableColorSequence = document.getElementById('editable-color-sequence');
            editableColorSequence.innerHTML = ''; // Clear only the editable sequence
        });
    }

    // Function to populate the *editable* color sequence from settings
    function populateEditableColorSequence(colors) {
        const editableColorSequence = document.getElementById('editable-color-sequence');
        if (!editableColorSequence) return;

        // Clear existing sequence
        editableColorSequence.innerHTML = '';

        // Add each color to the sequence
        colors.forEach(color => {
            addColorToEditableSequence(color);
        });
    }

    // Function to add a color to the *editable* sequence
    function addColorToEditableSequence(color) {
        const editableColorSequence = document.getElementById('editable-color-sequence');
        if (!editableColorSequence) return;
        const currentPositions = editableColorSequence.querySelectorAll('.sequence-position');
        const position = currentPositions.length + 1;

        // Get the background color for this color name
        const colorElement = document.querySelector(`.color-select[data-color="${color}"]`);
        const colorCircle = colorElement ? colorElement.querySelector('.color-circle') : null;
        const backgroundColor = colorCircle ?
            getComputedStyle(colorCircle).backgroundColor :
            getColorValue(color); // Fallback

        // Create the sequence position element
        const sequencePosition = document.createElement('div');
        sequencePosition.className = 'sequence-position editable'; // Add class for styling/selection
        sequencePosition.dataset.color = color;
        sequencePosition.innerHTML = `
            <div class="color-circle" style="background-color: ${backgroundColor}"></div>
            <span class="sequence-position-label">Position ${position}</span>
            <button type="button" class="remove-color-btn">✕</button>
        `;

        // Add remove button handler
        sequencePosition.querySelector('.remove-color-btn').addEventListener('click', function() {
            sequencePosition.remove();
            updateEditableSequencePositions(); // Update labels in the editable sequence
        });

        // Add to the editable sequence
        editableColorSequence.appendChild(sequencePosition);
    }

    // Function to update position numbers after removing colors in the *editable* sequence
    function updateEditableSequencePositions() {
        const positions = document.querySelectorAll('#editable-color-sequence .sequence-position');
        positions.forEach((position, index) => {
            const positionLabel = position.querySelector('.sequence-position-label');
            if (positionLabel) {
                positionLabel.textContent = `Position ${index + 1}`;
            }
        });
    }

    // Display the current saved color sequence
    function updateCurrentColorSequenceDisplay(colors) {
        const displayContainer = document.getElementById('current-color-sequence');
        if (!displayContainer) return;
        displayContainer.innerHTML = ''; // Clear previous

        if (!colors || colors.length === 0) {
            displayContainer.innerHTML = '<p class="empty-pattern">No sequence saved.</p>';
            return;
        }

        colors.forEach((color, index) => {
            const colorElement = document.querySelector(`.color-select[data-color="${color}"]`);
            const colorCircle = colorElement ? colorElement.querySelector('.color-circle') : null;
            const backgroundColor = colorCircle ?
                getComputedStyle(colorCircle).backgroundColor :
                getColorValue(color); // Fallback

            const sequencePosition = document.createElement('div');
            sequencePosition.className = 'sequence-position display-only'; // Class for styling
            sequencePosition.dataset.color = color;
            sequencePosition.innerHTML = `
                <div class="color-circle" style="background-color: ${backgroundColor}"></div>
                <span class="sequence-position-label">${index + 1}. ${color.charAt(0).toUpperCase() + color.slice(1)}</span>
            `;
            displayContainer.appendChild(sequencePosition);
        });
    }

    // Helper function to get color value by name
    function getColorValue(colorName) {
        const colorMap = {
            'red': '#FF6B6B',
            'blue': '#4ECDC4',
            'green': '#59CD90',
            'yellow': '#EAC435',
            'purple': '#9370DB',
            'orange': '#FF9F1C'
        };
        return colorMap[colorName] || '#cccccc';
    }
    
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
                    // Basic validation: ensure hold has duration > 0 if selected
                    if (action === 'hold' && duration <= 0) {
                         alert(`Step ${formPatternSteps.length + 1}: Hold action must have a duration greater than 0ms.`);
                         formPatternSteps.push({ action, duration: 500 });
                    } else if (action === 'tap') {
                         formPatternSteps.push({ action, duration: 0 }); // Ensure tap duration is 0
                    }
                     else {
                        formPatternSteps.push({ action, duration });
                    }
                }
            });
             // Validate minimum steps for manual entry
             if (formPatternSteps.length < 1) { // Or your desired minimum
                alert("Manual pattern must have at least 1 step.");
                // Restore button and return
                if (submitButton) {
                    submitButton.textContent = originalText;
                    submitButton.disabled = false;
                }
                return;
             }

        } else {
            // Get pattern from interactive recording (use window.patternSteps)
            formPatternSteps = window.patternSteps.slice();
             // Validate minimum steps for interactive entry
             if (formPatternSteps.length < 1) { // Or your desired minimum
                alert("Recorded pattern must have at least 1 step.");
                 // Restore button and return
                if (submitButton) {
                    submitButton.textContent = originalText;
                    submitButton.disabled = false;
                }
                return;
             }
        }

        // Get rotary color sequence from the *editable* container
        let colorSequence = [];
        document.querySelectorAll('#editable-color-sequence .sequence-position').forEach(position => {
            colorSequence.push(position.dataset.color);
        });

        // Validate color sequence length (e.g., require 4 colors)
        if (colorSequence.length > 0 && colorSequence.length < 4) {
             alert("Color sequence must contain exactly 4 colors.");
             // Restore button and return
             if (submitButton) {
                 submitButton.textContent = originalText;
                 submitButton.disabled = false;
             }
             return;
        } else if (colorSequence.length === 0) {
             // If user cleared it, maybe use default or prompt? For now, use default.
             console.log("No color sequence configured, using default.");
             colorSequence = ['red', 'blue', 'green', 'yellow'];
        }

        const formData = {
            customPattern: formPatternSteps,
            colorSequence: colorSequence
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

            // Update the "Current Saved" displays after successful save
            updatePatternStepsDisplay(formData.customPattern, currentPatternStepsContainer);
            updateCurrentColorSequenceDisplay(formData.colorSequence);
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