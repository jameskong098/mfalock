// Settings page functionality

document.addEventListener('DOMContentLoaded', function() {
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
        })
        .catch(error => {
            console.warn('Could not load settings:', error);
        });
    
    // Handle settings form submission
    document.getElementById('settings-form').addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = {
            securityLevel: document.getElementById('security-level').value,
            notificationEmail: document.getElementById('notification-email').value,
            notifySuccess: document.getElementById('notify-success').checked,
            notifyFailure: document.getElementById('notify-failure').checked
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
                throw new Error('Could not save settings');
            }
            return response.json();
        })
        .then(data => {
            alert('Settings saved successfully!');
        })
        .catch(error => {
            alert('Error saving settings: ' + error.message);
        });
    });
});