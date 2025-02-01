// Initialize floating elements
function createFloatingElements() {
    const container = document.querySelector('.floating-elements');
    const elementCount = 15;

    for (let i = 0; i < elementCount; i++) {
        const element = document.createElement('div');
        element.className = 'floating-element';
        
        // Random size between 10px and 50px
        const size = Math.random() * 40 + 10;
        element.style.width = `${size}px`;
        element.style.height = `${size}px`;
        
        // Random position
        element.style.left = `${Math.random() * 100}%`;
        element.style.top = `${Math.random() * 100}%`;
        
        // Random animation delay
        element.style.animationDelay = `${Math.random() * 5}s`;
        
        container.appendChild(element);
    }
}

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Stock price animation
function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start).toFixed(2);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Chart animations
function initializeChartAnimations() {
    const charts = document.querySelectorAll('.chart-container');
    charts.forEach(chart => {
        const overlay = document.createElement('div');
        overlay.className = 'chart-overlay';
        chart.appendChild(overlay);
    });
}

// Initialize all animations
document.addEventListener('DOMContentLoaded', () => {
    createFloatingElements();
    initializeChartAnimations();
    
    // Animate numbers on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const numberElement = entry.target;
                const finalValue = parseFloat(numberElement.dataset.value);
                animateValue(numberElement, 0, finalValue, 2000);
                observer.unobserve(numberElement);
            }
        });
    });

    document.querySelectorAll('.animate-number').forEach((element) => {
        observer.observe(element);
    });
}); 