document.addEventListener('DOMContentLoaded', function() {
    initializePortfolio();
    setupCharts();
    setupEventListeners();
    startLiveUpdates();
    initializeBenchmarkChart();
    initializePortfolioChart();
});

// Initialize Portfolio Data
function initializePortfolio() {
    const mockHoldings = [
        {
            symbol: 'RELIANCE',
            quantity: 100,
            avgCost: 2450.75,
            ltp: 2890.30,
            currentValue: 289030,
            pnl: 43955,
            returns: 17.93
        },
        {
            symbol: 'TCS',
            quantity: 50,
            avgCost: 3450.00,
            ltp: 3890.60,
            currentValue: 194530,
            pnl: 22030,
            returns: 12.75
        },
        {
            symbol: 'INFY',
            quantity: 75,
            avgCost: 1580.25,
            ltp: 1690.80,
            currentValue: 126810,
            pnl: 8291,
            returns: 6.99
        }
    ];

    updateHoldingsTable(mockHoldings);
}

// Setup Charts
function setupCharts() {
    // Portfolio Performance Chart
    const performanceCtx = document.getElementById('portfolioChart').getContext('2d');
    new Chart(performanceCtx, {
        type: 'line',
        data: {
            labels: generateDateLabels(30),
            datasets: [{
                label: 'Portfolio Value',
                data: generatePerformanceData(30),
                borderColor: '#4a90e2',
                backgroundColor: 'rgba(74, 144, 226, 0.1)',
                tension: 0.4,
                fill: true
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
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });

    // Sector Distribution Chart
    const sectorCtx = document.getElementById('sectorChart').getContext('2d');
    new Chart(sectorCtx, {
        type: 'doughnut',
        data: {
            labels: ['IT', 'Banking', 'Pharma', 'Auto', 'FMCG'],
            datasets: [{
                data: [30, 25, 15, 20, 10],
                backgroundColor: [
                    '#4a90e2',
                    '#67b26f',
                    '#f953c6',
                    '#f9d423',
                    '#8e44ad'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// Event Listeners
function setupEventListeners() {
    // Time Filter Buttons
    document.querySelectorAll('.time-filter').forEach(button => {
        button.addEventListener('click', function() {
            document.querySelector('.time-filter.active').classList.remove('active');
            this.classList.add('active');
            updateChartData(this.textContent);
        });
    });

    // Add Stock Modal
    const modal = document.getElementById('addStockModal');
    const addStockBtn = document.getElementById('addStockBtn');
    const closeBtn = document.querySelector('.close');

    addStockBtn.onclick = () => modal.style.display = 'block';
    closeBtn.onclick = () => modal.style.display = 'none';
    window.onclick = (e) => {
        if (e.target == modal) modal.style.display = 'none';
    };

    // Add Stock Form
    document.getElementById('addStockForm').onsubmit = function(e) {
        e.preventDefault();
        const formData = {
            symbol: document.getElementById('stockSymbol').value,
            quantity: document.getElementById('quantity').value,
            purchasePrice: document.getElementById('purchasePrice').value,
            purchaseDate: document.getElementById('purchaseDate').value
        };
        addNewStock(formData);
        modal.style.display = 'none';
        this.reset();
    };

    // Holdings Table Sorting
    document.querySelectorAll('.holdings-table th').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.textContent.trim();
            sortHoldings(column);
        });
    });
}

// Helper Functions
function generateDateLabels(days) {
    const labels = [];
    const today = new Date();
    for (let i = days; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
    return labels;
}

function generatePerformanceData(days) {
    const data = [];
    let value = 1500000;
    for (let i = 0; i <= days; i++) {
        value *= (1 + (Math.random() * 0.02 - 0.01));
        data.push(value);
    }
    return data;
}

function updateHoldingsTable(holdings) {
    const tableBody = document.getElementById('holdingsTableBody');
    tableBody.innerHTML = holdings.map(stock => `
        <tr>
            <td>${stock.symbol}</td>
            <td>${stock.quantity}</td>
            <td>₹${stock.avgCost.toFixed(2)}</td>
            <td>₹${stock.ltp.toFixed(2)}</td>
            <td>₹${stock.currentValue.toLocaleString()}</td>
            <td class="${stock.pnl >= 0 ? 'up' : 'down'}">
                ₹${Math.abs(stock.pnl).toLocaleString()}
            </td>
            <td class="${stock.returns >= 0 ? 'up' : 'down'}">
                ${stock.returns.toFixed(2)}%
            </td>
            <td>
                <button class="btn-icon" onclick="editHolding('${stock.symbol}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon" onclick="deleteHolding('${stock.symbol}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Live Updates
function startLiveUpdates() {
    setInterval(() => {
        updateStockPrices();
        updatePortfolioMetrics();
    }, 5000);
}

function updateStockPrices() {
    // Simulate live price updates
    const holdings = document.querySelectorAll('.holdings-table tbody tr');
    holdings.forEach(row => {
        const ltpCell = row.cells[3];
        const currentPrice = parseFloat(ltpCell.textContent.replace('₹', ''));
        const newPrice = currentPrice * (1 + (Math.random() * 0.02 - 0.01));
        ltpCell.textContent = `₹${newPrice.toFixed(2)}`;
        updateRowCalculations(row, newPrice);
    });
}

function updateRowCalculations(row, newPrice) {
    const quantity = parseInt(row.cells[1].textContent);
    const avgCost = parseFloat(row.cells[2].textContent.replace('₹', ''));
    
    const currentValue = quantity * newPrice;
    const pnl = currentValue - (quantity * avgCost);
    const returns = (pnl / (quantity * avgCost)) * 100;

    row.cells[4].textContent = `₹${currentValue.toLocaleString()}`;
    row.cells[5].textContent = `₹${Math.abs(pnl).toLocaleString()}`;
    row.cells[5].className = pnl >= 0 ? 'up' : 'down';
    row.cells[6].textContent = `${returns.toFixed(2)}%`;
    row.cells[6].className = returns >= 0 ? 'up' : 'down';
}

function initializeBenchmarkChart() {
    const ctx = document.getElementById('benchmarkChart');
    
    if (!ctx) {
        console.error('Benchmark chart canvas not found');
        return;
    }

    try {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: [
                    {
                        label: 'Portfolio',
                        data: [65, 67, 70, 68, 72, 75, 73, 78, 80, 82, 85, 88],
                        borderColor: '#4a90e2',
                        tension: 0.4,
                        fill: false
                    },
                    {
                        label: 'NIFTY 50',
                        data: [60, 62, 65, 63, 68, 70, 69, 73, 75, 76, 78, 80],
                        borderColor: '#22c55e',
                        tension: 0.4,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#8a8aa0',
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#8a8aa0',
                            font: {
                                size: 11
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#8a8aa0',
                            font: {
                                size: 11
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error initializing benchmark chart:', error);
    }
}

function initializePortfolioChart() {
    const ctx = document.getElementById('portfolioChart');
    
    if (!ctx) {
        console.error('Portfolio chart canvas not found');
        return;
    }

    try {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: [{
                    label: 'Portfolio Value',
                    data: [100000, 105000, 103000, 106000, 108000, 115000, 112000, 118000, 122000, 125000, 128000, 130000],
                    borderColor: '#4a90e2',
                    backgroundColor: 'rgba(74, 144, 226, 0.1)',
                    tension: 0.4,
                    fill: true
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
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#8a8aa0',
                            font: {
                                size: 11
                            },
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#8a8aa0',
                            font: {
                                size: 11
                            }
                        }
                    }
                }
            }
        });

        // Add click handlers for time filters
        document.querySelectorAll('.time-filter').forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons
                document.querySelectorAll('.time-filter').forEach(btn => 
                    btn.classList.remove('active'));
                // Add active class to clicked button
                this.classList.add('active');
                // TODO: Update chart data based on selected time period
            });
        });

    } catch (error) {
        console.error('Error initializing portfolio chart:', error);
    }
}