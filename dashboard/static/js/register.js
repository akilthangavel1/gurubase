document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    
    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const fullName = document.getElementById('fullName').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const terms = document.getElementById('terms').checked;
        
        // Basic validation
        if (!fullName || !email || !password || !confirmPassword) {
            showError('Please fill in all fields');
            return;
        }
        
        // Email validation
        if (!isValidEmail(email)) {
            showError('Please enter a valid email address');
            return;
        }
        
        // Password validation
        if (password.length < 8) {
            showError('Password must be at least 8 characters long');
            return;
        }
        
        // Password match validation
        if (password !== confirmPassword) {
            showError('Passwords do not match');
            return;
        }
        
        // Terms validation
        if (!terms) {
            showError('Please accept the Terms & Conditions');
            return;
        }
        
        // Here you would typically make an API call to your backend
        // For now, we'll simulate a successful registration
        simulateRegistration({ fullName, email, password });
    });
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    function showError(message) {
        // Create error element if it doesn't exist
        let errorDiv = document.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            registerForm.insertBefore(errorDiv, registerForm.firstChild);
        }
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
    
    function simulateRegistration(data) {
        // Simulate API call
        setTimeout(() => {
            // Store user data in localStorage
            localStorage.setItem('user', JSON.stringify({ 
                fullName: data.fullName,
                email: data.email 
            }));
            
            // Redirect to login page
            window.location.href = 'login.html';
        }, 1000);
    }
}); 