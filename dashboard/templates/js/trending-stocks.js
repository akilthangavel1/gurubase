document.addEventListener('DOMContentLoaded', function() {
    const sectorGrid = document.querySelector('.sector-grid');
    const scrollLeftBtn = document.querySelector('.scroll-left');
    const scrollRightBtn = document.querySelector('.scroll-right');
    
    if (scrollLeftBtn && scrollRightBtn && sectorGrid) {
        const scrollAmount = 300; // Adjust based on card width
        
        scrollLeftBtn.addEventListener('click', () => {
            sectorGrid.scrollBy({
                left: -scrollAmount,
                behavior: 'smooth'
            });
        });
        
        scrollRightBtn.addEventListener('click', () => {
            sectorGrid.scrollBy({
                left: scrollAmount,
                behavior: 'smooth'
            });
        });
        
        // Show/hide scroll buttons based on scroll position
        sectorGrid.addEventListener('scroll', () => {
            scrollLeftBtn.style.opacity = sectorGrid.scrollLeft > 0 ? '1' : '0.5';
            scrollRightBtn.style.opacity = 
                sectorGrid.scrollLeft < (sectorGrid.scrollWidth - sectorGrid.clientWidth) 
                ? '1' : '0.5';
        });
    }
}); 