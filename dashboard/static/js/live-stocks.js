// Live Stocks Page JavaScript
document.addEventListener('DOMContentLoaded', () => {
    initializeStockData();
    setupEventListeners();
    startLiveUpdates();
    createMiniCharts();
});

// Initialize stock data
function initializeStockData() {
    const stocksData = [
        {
            symbol: 'RELIANCE',
            company: 'Reliance Industries',
            ltp: 2890.30,
            change: 2.15,
            volume: '3.4M',
            high52: 2950.00,
            low52: 1987.00,
            marketCap: '1,856,789',
            pe: 22.5
        },
        {
            symbol: 'TCS',
            company: 'Tata Consultancy Services',
            ltp: 3890.60,
            change: 1.65,
            volume: '980K',
            high52: 4045.00,
            low52: 3120.00,
            marketCap: '1,234,567',
            pe: 28.4
        },
        // Add more stock data here
    ];

    updateStocksTable(stocksData);
}

// Update stocks table
function updateStocksTable(data) {
    const tableBody = document.getElementById('stocksTableBody');
    tableBody.innerHTML = data.map(stock => `
        <tr data-symbol="${stock.symbol}">
            <td>${stock.symbol}</td>
            <td>${stock.company}</td>
            <td class="price">${stock.ltp.toFixed(2)}</td>
            <td class="${stock.change >= 0 ? 'up' : 'down'}">
                ${stock.change >= 0 ? '+' : ''}${stock.change}%
            </td>
            <td>${stock.volume}</td>
            <td>${stock.high52.toFixed(2)}</td>
            <td>${stock.low52.toFixed(2)}</td>
            <td>${stock.marketCap}</td>
            <td>${stock.pe}</td>
        </tr>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Search functionality
    document.getElementById('stockSearch').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#stocksTableBody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    });

    // Filter by sector
    document.getElementById('sectorFilter').addEventListener('change', (e) => {
        // Implement sector filtering
    });

    // Filter by market cap
    document.getElementById('marketCapFilter').addEventListener('change', (e) => {
        // Implement market cap filtering
    });

    // View options
    document.querySelectorAll('.view-options button').forEach(button => {
        button.addEventListener('click', (e) => {
            document.querySelectorAll('.view-options button').forEach(btn => {
                btn.classList.remove('active');
            });
            e.target.classList.add('active');
            // Implement view change logic
        });
    });
}

// Simulate live updates
function startLiveUpdates() {
    setInterval(() => {
        const prices = document.querySelectorAll('.price');
        prices.forEach(price => {
            const currentPrice = parseFloat(price.textContent);
            const change = (Math.random() - 0.5) * 10;
            const newPrice = currentPrice + change;
            price.textContent = newPrice.toFixed(2);
            
            const changeCell = price.nextElementSibling;
            const changePercent = (change / currentPrice * 100).toFixed(2);
            changeCell.textContent = `${changePercent >= 0 ? '+' : ''}${changePercent}%`;
            changeCell.className = changePercent >= 0 ? 'up' : 'down';
        });
    }, 5000);
}

// Function to update market depth data
function updateMarketDepth() {
    const buyDepth = document.getElementById('buyDepth');
    const sellDepth = document.getElementById('sellDepth');

    // Buy Orders Data
    const buyOrders = [
        { price: 2890.50, quantity: 1250, orders: 45, total: "3,613,125" },
        { price: 2889.75, quantity: 850, orders: 32, total: "2,456,287" },
        { price: 2888.90, quantity: 1500, orders: 28, total: "4,333,350" },
        { price: 2887.25, quantity: 950, orders: 39, total: "2,742,887" },
        { price: 2886.60, quantity: 2100, orders: 52, total: "6,061,860" }
    ];

    // Sell Orders Data
    const sellOrders = [
        { price: 2891.20, quantity: 980, orders: 41, total: "2,833,376" },
        { price: 2892.15, quantity: 1450, orders: 37, total: "4,193,617" },
        { price: 2893.40, quantity: 750, orders: 29, total: "2,170,050" },
        { price: 2894.60, quantity: 1800, orders: 48, total: "5,210,280" },
        { price: 2895.30, quantity: 1100, orders: 35, total: "3,184,830" }
    ];

    // Update Buy Orders
    buyDepth.innerHTML = `
        <table class="depth-table">
            <thead>
                <tr>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Orders</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                ${buyOrders.map(order => `
                    <tr>
                        <td class="price-up">₹${order.price.toFixed(2)}</td>
                        <td>${order.quantity}</td>
                        <td>${order.orders}</td>
                        <td>₹${order.total}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    // Update Sell Orders
    sellDepth.innerHTML = `
        <table class="depth-table">
            <thead>
                <tr>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Orders</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                ${sellOrders.map(order => `
                    <tr>
                        <td class="price-down">₹${order.price.toFixed(2)}</td>
                        <td>${order.quantity}</td>
                        <td>${order.orders}</td>
                        <td>₹${order.total}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Call the function when page loads
document.addEventListener('DOMContentLoaded', updateMarketDepth);

const API_KEY = "ctp7b79r01qhpppjorbgctp7b79r01qhpppjorc0";
const API_URL = "https://finnhub.io/api/v1/quote";

const symbols = ["AAPL", "GOOGL", "TSLA", "MSFT", "AMZN", "META", "NFLX"];

async function fetchRealTimeData() {
    const tickerContent = document.getElementById("ticker-content");
    tickerContent.innerHTML = "Loading...";

    try {
        const responses = await Promise.all(
            symbols.map(symbol =>
                fetch(`${API_URL}?symbol=${symbol}&token=${API_KEY}`).then(res => res.json())
            )
        );

        tickerContent.innerHTML = "";
        
        // Create ticker items with proper formatting
        responses.forEach((data, i) => {
            const price = data.c.toFixed(2);
            const change = data.d.toFixed(2);
            const changePercent = ((data.d / (data.c - data.d)) * 100).toFixed(2);
            const className = change >= 0 ? "up" : "down";
            
            const tickerItem = document.createElement('div');
            tickerItem.className = 'ticker-item';
            tickerItem.innerHTML = `
                <span class="symbol">${symbols[i]}</span>
                <span class="price">$${price}</span>
                <span class="change ${className}">${change >= 0 ? '+' : ''}${change} (${changePercent}%)</span>
            `;
            
            tickerContent.appendChild(tickerItem);
            
            // Add divider except for last item
            if (i < responses.length - 1) {
                const divider = document.createElement('span');
                divider.className = 'ticker-divider';
                divider.textContent = '|';
                tickerContent.appendChild(divider);
            }
        });

    } catch (error) {
        console.error("Error fetching real-time stock data:", error);
        tickerContent.innerHTML = "Error loading stock data.";
    }
}

// Initial fetch
fetchRealTimeData();

// Refresh every 60 seconds
setInterval(fetchRealTimeData, 60000);

// Add hover pause functionality
const tickerContent = document.getElementById("ticker-content");
if (tickerContent) {
    tickerContent.addEventListener('mouseover', () => {
        tickerContent.style.animationPlayState = 'paused';
    });
    
    tickerContent.addEventListener('mouseout', () => {
        tickerContent.style.animationPlayState = 'running';
    });
}

// Add this function to your existing live-stocks.js
function createMiniCharts() {
    const chartElements = document.querySelectorAll('.chart-mini');
    
    chartElements.forEach((element) => {
        const canvas = document.createElement('canvas');
        element.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        
        // Generate random data points
        const dataPoints = Array.from({length: 20}, () => 
            Math.random() * 40 + 30
        );
        
        // Create gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 60);
        const parentCard = element.closest('.market-card');
        const changeElement = parentCard.querySelector('.change');
        const isUp = changeElement && changeElement.classList.contains('up');
        
        if (isUp) {
            gradient.addColorStop(0, 'rgba(239, 68, 68, 0.2)');   // Red with opacity
            gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
        } else {
            gradient.addColorStop(0, 'rgba(34, 197, 94, 0.2)');   // Green with opacity
            gradient.addColorStop(1, 'rgba(34, 197, 94, 0)');
        }

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 20}, (_, i) => ''),
                datasets: [{
                    data: dataPoints,
                    borderColor: isUp ? '#ef4444' : '#22c55e',
                    borderWidth: 2,
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: false,
                        min: Math.min(...dataPoints) * 0.95,
                        max: Math.max(...dataPoints) * 1.05
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        });
    });
}

// Call the function when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    createMiniCharts();
    // ... your other existing code ...
}); 