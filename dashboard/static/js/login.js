document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');

    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const remember = document.getElementById('remember').checked;

        // Basic validation
        if (!email || !password) {
            showError('Please fill in all fields');
            return;
        }

        // Email validation
        if (!isValidEmail(email)) {
            showError('Please enter a valid email address');
            return;
        }

        // Here you would typically make an API call to your backend
        // For now, we'll simulate a successful login
        simulateLogin({ email, password, remember });
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
            loginForm.insertBefore(errorDiv, loginForm.firstChild);
        }
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }

    function simulateLogin(data) {
        // Simulate API call
        setTimeout(() => {
            // Store user data in localStorage
            if (data.remember) {
                localStorage.setItem('user', JSON.stringify({ email: data.email }));
            }
            
            // Redirect to dashboard/portfolio
            window.location.href = 'portfolio.html';
        }, 1000);
    }
}); 