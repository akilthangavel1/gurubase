const API_KEY = "ctp7b79r01qhpppjorbgctp7b79r01qhpppjorc0";
const API_URL = "https://finnhub.io/api/v1/quote";

const symbols = ["AAPL", "GOOGL", "TSLA", "MSFT", "EXCOF",]; // Example companies

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
    responses.forEach((data, i) => {
      const price = data.c.toFixed(2); // Current price
      const change = data.d.toFixed(2); // Change
      const className = change >= 0 ? "up" : "down";
      tickerContent.innerHTML += `<span class="${className}">${symbols[i]}: $${price} (${change >= 0 ? "+" : ""}${change})</span> | `;
    });
  } catch (error) {
    console.error("Error fetching real-time stock data:", error);
    tickerContent.innerHTML = "Error loading stock data.";
  }
}

fetchRealTimeData();
setInterval(fetchRealTimeData, 60000); // Refresh every 60 seconds


function searchStock(companyName) {
  const output = document.getElementById('output');

  if (!companyName) {
      companyName = document.getElementById('search').value;
  }

  if (companyName.trim() === '') {
      alert('Please enter a company name.');
      return;
  }

  // Mockup output (Replace this with an API call to fetch real stock data)
  output.innerHTML = `
      <h2>Stock Overview for ${companyName}</h2>
      <p><strong>Stock Value:</strong> ₹${(Math.random() * 1000 + 500).toFixed(2)}</p>
      <p><strong>Heatmap:</strong> Positive</p>
      <p><strong>Description:</strong> ${companyName} is performing well in the current market.</p>
  `;
}

class StockTracker {
  constructor() {
      this.stockData = {
          gainers: [],
          losers: [],
          mostTraded: [],
          week52High: [],
          week52Low: []
      };
      this.init();
  }

  async init() {
      await this.fetchStockData();
      this.setupEventListeners();
      this.renderTables();
  }

  async fetchStockData() {
      // Simulated data - Replace with actual API call
      this.stockData = {
          gainers: [
              {
                  name: "Empower Broking Ltd",
                  ltp: "₹7.10",
                  change: "+14.51%",
                  volume: "₹12.44M",
                  mcap: "743.51",
                  pe: "45.65",
                  roe: "13.05",
                  roce: "8.48"
              },
              // Add more stocks...
          ],
          losers: [
              {
                  name: "PT Ltd",
                  ltp: "₹240.85",
                  change: "-5.23%",
                  volume: "₹20.3M",
                  mcap: "235.45",
                  pe: "34.65",
                  roe: "8.75",
                  roce: "7.65"
              },
              // Add more stocks...
          ]
          // Add other categories...
      };
  }

  setupEventListeners() {
      // Category filter
      document.getElementById('categoryFilter').addEventListener('change', (e) => {
          this.filterStocks(e.target.value);
      });

      // Search functionality
      document.getElementById('searchStocks').addEventListener('input', (e) => {
          this.searchStocks(e.target.value);
      });
  }

  renderTables() {
      const container = document.querySelector('.stock-tables');
      container.innerHTML = ''; // Clear existing tables

      Object.entries(this.stockData).forEach(([category, stocks]) => {
          const table = this.createTable(category, stocks);
          container.appendChild(table);
      });
  }

  createTable(category, stocks) {
      const section = document.createElement('div');
      section.className = 'stock-section';
      
      const title = document.createElement('h2');
      title.textContent = this.formatCategoryName(category);
      section.appendChild(title);

      const table = document.createElement('table');
      table.className = 'stock-table';

      // Create table header
      const thead = document.createElement('thead');
      thead.innerHTML = `
          <tr>
              <th>Company Name</th>
              <th>LTP</th>
              <th>Volume</th>
              <th>MCAP (Cr)</th>
              <th>PE (TTM)</th>
              <th>ROE (%)</th>
              <th>ROCE (%)</th>
          </tr>
      `;

      // Create table body
      const tbody = document.createElement('tbody');
      stocks.forEach(stock => {
          const row = document.createElement('tr');
          row.innerHTML = `
              <td>${stock.name}</td>
              <td class="${stock.change.includes('+') ? 'green' : 'red'}">${stock.ltp} (${stock.change})</td>
              <td>${stock.volume}</td>
              <td>${stock.mcap}</td>
              <td>${stock.pe}</td>
              <td>${stock.roe}</td>
              <td>${stock.roce}</td>
          `;
          tbody.appendChild(row);
      });

      table.appendChild(thead);
      table.appendChild(tbody);
      section.appendChild(table);

      return section;
  }

  formatCategoryName(category) {
      return category
          .split(/(?=[A-Z])/)
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
  }

  filterStocks(category) {
      const sections = document.querySelectorAll('.stock-section');
      if (category === 'all') {
          sections.forEach(section => section.style.display = 'block');
      } else {
          sections.forEach(section => {
              section.style.display = section.querySelector('h2').textContent.toLowerCase().includes(category) ? 'block' : 'none';
          });
      }
  }

  searchStocks(query) {
      const rows = document.querySelectorAll('.stock-table tbody tr');
      rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query.toLowerCase()) ? '' : 'none';
      });
  }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  new StockTracker();
});

// Navbar Scroll Effect
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Animate elements when they come into view
const observerOptions = {
    threshold: 0.1
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'fadeInUp 0.6s ease-out forwards';
        }
    });
}, observerOptions);

document.querySelectorAll('.stock-card, .analysis-card, .feature-card').forEach(el => {
    observer.observe(el);
});

// Market Overview Animations and Interactivity
class MarketOverview {
    constructor() {
        this.initSentimentMeter();
        this.initVolumeChart();
        this.initMarketCapPie();
        this.setupInteractions();
    }

    initSentimentMeter() {
        const meter = document.querySelector('.meter-fill');
        // Animate sentiment meter on load
        setTimeout(() => {
            meter.style.width = '65%';
            meter.style.transition = 'width 1s ease-out';
        }, 500);
    }

    initVolumeChart() {
        const bars = document.querySelectorAll('.volume-chart .bar');
        // Animate volume bars on load
        bars.forEach((bar, index) => {
            setTimeout(() => {
                bar.style.height = bar.style.height;
                bar.style.transition = 'height 0.6s ease-out';
            }, index * 100);
        });
    }

    initMarketCapPie() {
        const pie = document.querySelector('.distribution-pie');
        if (pie) {
            this.updatePieChart([60, 25, 15]); // Initial values
        }
    }

    updatePieChart(values) {
        const total = values.reduce((a, b) => a + b, 0);
        let startAngle = 0;
        
        values.forEach((value, index) => {
            const segment = document.querySelector(`.pie-segment:nth-child(${index + 1})`);
            const angle = (value / total) * 360;
            segment.style.transform = `rotate(${startAngle}deg)`;
            segment.style.clipPath = `polygon(0 0, 100% 0, 100% 100%, 0 100%)`;
            startAngle += angle;
        });
    }

    setupInteractions() {
        // Market cards hover effect
        const cards = document.querySelectorAll('.market-card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-10px)';
                card.style.transition = 'transform 0.3s ease';
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
    }
}

// News Section Enhancement
class NewsSection {
    constructor() {
        this.initNewsCards();
        this.setupNewsFilter();
    }

    initNewsCards() {
        const newsCards = document.querySelectorAll('.news-card');
        newsCards.forEach((card, index) => {
            // Stagger animation on load
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 200);
        });
    }

    setupNewsFilter() {
        const newsContainer = document.querySelector('.news-grid');
        if (!newsContainer) return;

        // Add filter buttons
        const filterButtons = document.createElement('div');
        filterButtons.className = 'news-filters';
        filterButtons.innerHTML = `
            <button class="active" data-filter="all">All</button>
            <button data-filter="market">Market</button>
            <button data-filter="tech">Technology</button>
            <button data-filter="analysis">Analysis</button>
        `;
        newsContainer.parentNode.insertBefore(filterButtons, newsContainer);

        // Filter functionality
        filterButtons.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const filter = e.target.dataset.filter;
                this.filterNews(filter);
                
                // Update active button
                filterButtons.querySelectorAll('button').forEach(btn => 
                    btn.classList.remove('active'));
                e.target.classList.add('active');
            }
        });
    }

    filterNews(category) {
        const newsCards = document.querySelectorAll('.news-card');
        newsCards.forEach(card => {
            if (category === 'all') {
                card.style.display = 'block';
            } else {
                const cardCategory = card.dataset.category;
                card.style.display = cardCategory === category ? 'block' : 'none';
            }
        });
    }
}

// Education Section Enhancement
class EducationSection {
    constructor() {
        this.initEducationCards();
        this.setupProgressTracking();
    }

    initEducationCards() {
        const cards = document.querySelectorAll('.education-card');
        cards.forEach(card => {
            // Add progress bar
            const progress = document.createElement('div');
            progress.className = 'progress-bar';
            progress.innerHTML = `
                <div class="progress-fill"></div>
                <span class="progress-text">0% Complete</span>
            `;
            card.appendChild(progress);
        });
    }

    setupProgressTracking() {
        const eduLinks = document.querySelectorAll('.edu-link');
        eduLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const card = link.closest('.education-card');
                const progress = card.querySelector('.progress-fill');
                const text = card.querySelector('.progress-text');
                
                // Simulate progress update
                let currentProgress = parseInt(progress.style.width) || 0;
                const newProgress = Math.min(currentProgress + 20, 100);
                
                progress.style.width = `${newProgress}%`;
                text.textContent = `${newProgress}% Complete`;
            });
        });
    }
}

// Initialize all enhancements when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MarketOverview();
    new NewsSection();
    new EducationSection();
    
    // Add smooth scrolling for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger');
    const navbar = document.querySelector('.navbar');
    const navLinks = document.querySelectorAll('.navbar nav a');

    // Toggle menu
    hamburger?.addEventListener('click', function() {
        navbar.classList.toggle('active');
    });

    // Close menu when clicking a link
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navbar.classList.remove('active');
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!navbar.contains(e.target)) {
            navbar.classList.remove('active');
        }
    });
});