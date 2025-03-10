// Pattern demonstration animation

document.addEventListener('DOMContentLoaded', function() {
    // Pattern demonstration
    document.getElementById('demo-button').addEventListener('click', () => {
        const sensor = document.getElementById('touch-sensor');
        const sequence = [
            { action: 'tap', duration: 200 },
            { action: 'wait', duration: 200 },
            { action: 'tap', duration: 200 },
            { action: 'wait', duration: 500 },
            { action: 'hold', duration: 1200 },
            { action: 'wait', duration: 300 },
            { action: 'tap', duration: 200 },
            { action: 'success', duration: 1000 }
        ];
        
        let currentStep = 0;
        
        function runSequence() {
            if (currentStep >= sequence.length) {
                return;
            }
            
            const step = sequence[currentStep];
            
            switch (step.action) {
                case 'tap':
                    sensor.classList.add('active');
                    setTimeout(() => {
                        sensor.classList.remove('active');
                        currentStep++;
                        setTimeout(runSequence, 10);
                    }, step.duration);
                    break;
                case 'hold':
                    sensor.classList.add('active');
                    setTimeout(() => {
                        sensor.classList.remove('active');
                        currentStep++;
                        setTimeout(runSequence, 10);
                    }, step.duration);
                    break;
                case 'wait':
                    setTimeout(() => {
                        currentStep++;
                        runSequence();
                    }, step.duration);
                    break;
                case 'success':
                    sensor.style.backgroundColor = '#27ae60';
                    setTimeout(() => {
                        sensor.style.backgroundColor = '';
                        currentStep++;
                        runSequence();
                    }, step.duration);
                    break;
            }
        }
        
        runSequence();
    });
});