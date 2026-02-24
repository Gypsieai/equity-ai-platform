/* ================================================
   AI EQUITY PLATFORM - APPLICATION LOGIC
   ================================================ */

// Stock Data Store
let stockData = [];
let portfolio = {};
let currentFilter = 'All';

// DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
    await loadStockData();
    initTicker();
    renderRankingsTable();
    initPortfolioBuilder();
    initModals();
    initFilters();
    initSearch();
    animateCounters();
});

// Load Stock Data
async function loadStockData() {
    try {
        const response = await fetch('data/stocks.json');
        stockData = await response.json();
        stockData.sort((a, b) => b.aiScore - a.aiScore);
    } catch (error) {
        console.error('Failed to load stock data:', error);
        // Fallback data
        stockData = [
            { ticker: 'NVDA', name: 'NVIDIA Corporation', sector: 'Technology', aiScore: 98, price: 875.42, change1D: 2.34, change1W: 8.12, change1M: 15.67, sentiment: 'Bullish', marketCap: '2.15T' },
            { ticker: 'AAPL', name: 'Apple Inc.', sector: 'Technology', aiScore: 94, price: 227.85, change1D: 0.87, change1W: 3.21, change1M: 7.89, sentiment: 'Bullish', marketCap: '3.48T' },
            { ticker: 'MSFT', name: 'Microsoft Corporation', sector: 'Technology', aiScore: 92, price: 415.60, change1D: 1.12, change1W: 4.56, change1M: 9.34, sentiment: 'Bullish', marketCap: '3.09T' }
        ];
    }
}

// Initialize Ticker Tape
function initTicker() {
    const tickerContent = document.getElementById('tickerContent');
    if (!tickerContent) return;

    let tickerHTML = '';
    stockData.forEach(stock => {
        const changeClass = stock.change1D >= 0 ? 'positive' : 'negative';
        const changeSign = stock.change1D >= 0 ? '+' : '';
        tickerHTML += `
            <div class="ticker-item">
                <span class="symbol">${stock.ticker}</span>
                <span class="price">$${stock.price.toFixed(2)}</span>
                <span class="change ${changeClass}">${changeSign}${stock.change1D.toFixed(2)}%</span>
            </div>
        `;
    });
    // Duplicate for seamless loop
    tickerContent.innerHTML = tickerHTML + tickerHTML;
}

// Render Rankings Table
function renderRankingsTable(filter = 'All', searchTerm = '') {
    const tbody = document.getElementById('rankingsBody');
    if (!tbody) return;

    let filteredData = stockData;

    // Apply sector filter
    if (filter !== 'All') {
        filteredData = filteredData.filter(s => s.sector === filter);
    }

    // Apply search
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filteredData = filteredData.filter(s => 
            s.ticker.toLowerCase().includes(term) || 
            s.name.toLowerCase().includes(term)
        );
    }

    tbody.innerHTML = filteredData.map((stock, index) => {
        const scoreClass = stock.aiScore >= 85 ? 'high' : stock.aiScore >= 70 ? 'medium' : 'low';
        const change1DClass = stock.change1D >= 0 ? 'positive' : 'negative';
        const change1WClass = stock.change1W >= 0 ? 'positive' : 'negative';
        const change1MClass = stock.change1M >= 0 ? 'positive' : 'negative';
        const sentimentClass = stock.sentiment.toLowerCase();

        return `
            <tr>
                <td>${index + 1}</td>
                <td>
                    <div class="stock-info">
                        <div class="stock-icon">${stock.ticker.slice(0, 2)}</div>
                        <div>
                            <div class="stock-name">${stock.name}</div>
                            <div class="stock-ticker">${stock.ticker}</div>
                        </div>
                    </div>
                </td>
                <td><span class="ai-score ${scoreClass}">${stock.aiScore}</span></td>
                <td>$${stock.price.toFixed(2)}</td>
                <td><span class="change-badge ${change1DClass}">${stock.change1D >= 0 ? '↑' : '↓'} ${Math.abs(stock.change1D).toFixed(2)}%</span></td>
                <td><span class="change-badge ${change1WClass}">${stock.change1W >= 0 ? '↑' : '↓'} ${Math.abs(stock.change1W).toFixed(2)}%</span></td>
                <td><span class="change-badge ${change1MClass}">${stock.change1M >= 0 ? '↑' : '↓'} ${Math.abs(stock.change1M).toFixed(2)}%</span></td>
                <td><span class="sentiment-badge ${sentimentClass}">${stock.sentiment}</span></td>
            </tr>
        `;
    }).join('');
}

// Initialize Filter Tabs
function initFilters() {
    const filterTabs = document.querySelectorAll('.filter-tab');
    filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = tab.dataset.filter;
            const searchInput = document.getElementById('stockSearch');
            renderRankingsTable(currentFilter, searchInput ? searchInput.value : '');
        });
    });
}

// Initialize Search
function initSearch() {
    const searchInput = document.getElementById('stockSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        renderRankingsTable(currentFilter, e.target.value);
    });
}

// Portfolio Builder
let portfolioChart = null;

function initPortfolioBuilder() {
    const stockList = document.getElementById('stockSelectList');
    if (!stockList) return;

    // Render stock selector
    stockList.innerHTML = stockData.slice(0, 8).map(stock => `
        <div class="stock-select-item" data-ticker="${stock.ticker}">
            <div class="stock-info">
                <div class="stock-icon">${stock.ticker.slice(0, 2)}</div>
                <div>
                    <div class="stock-name">${stock.ticker}</div>
                    <div class="stock-ticker">${stock.name}</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
                <input type="range" min="0" max="100" value="0" class="allocation-slider">
                <span class="allocation-value" style="color: var(--accent-primary); font-weight: 600; min-width: 40px;">0%</span>
            </div>
        </div>
    `).join('');

    // Add event listeners
    document.querySelectorAll('.allocation-slider').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const item = e.target.closest('.stock-select-item');
            const ticker = item.dataset.ticker;
            const value = parseInt(e.target.value);
            item.querySelector('.allocation-value').textContent = value + '%';
            
            if (value > 0) {
                item.classList.add('selected');
                portfolio[ticker] = value;
            } else {
                item.classList.remove('selected');
                delete portfolio[ticker];
            }
            
            updatePortfolioChart();
            updatePortfolioSummary();
        });
    });

    // Initialize chart
    initPortfolioChart();
}

function initPortfolioChart() {
    const ctx = document.getElementById('portfolioChart');
    if (!ctx) return;

    portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Not Allocated'],
            datasets: [{
                data: [100],
                backgroundColor: ['rgba(107, 114, 128, 0.3)'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#9ca3af',
                        font: { family: 'Inter', size: 12 },
                        padding: 20
                    }
                }
            }
        }
    });
}

function updatePortfolioChart() {
    if (!portfolioChart) return;

    const labels = Object.keys(portfolio);
    const data = Object.values(portfolio);
    const total = data.reduce((a, b) => a + b, 0);

    if (total < 100) {
        labels.push('Unallocated');
        data.push(100 - total);
    }

    const colors = [
        '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
        '#6366f1', '#14b8a6', '#f97316', 'rgba(107, 114, 128, 0.3)'
    ];

    portfolioChart.data.labels = labels.length ? labels : ['Not Allocated'];
    portfolioChart.data.datasets[0].data = data.length ? data : [100];
    portfolioChart.data.datasets[0].backgroundColor = labels.length ? colors.slice(0, labels.length) : ['rgba(107, 114, 128, 0.3)'];
    portfolioChart.update();
}

function updatePortfolioSummary() {
    const totalAllocation = Object.values(portfolio).reduce((a, b) => a + b, 0);
    const stockCount = Object.keys(portfolio).length;
    
    // Calculate projected return (simulated)
    let projectedReturn = 0;
    Object.entries(portfolio).forEach(([ticker, allocation]) => {
        const stock = stockData.find(s => s.ticker === ticker);
        if (stock) {
            projectedReturn += (stock.change1M / 100) * (allocation / 100);
        }
    });

    const summaryItems = document.querySelectorAll('.portfolio-summary .summary-item .value');
    if (summaryItems.length >= 4) {
        summaryItems[0].textContent = totalAllocation + '%';
        summaryItems[1].textContent = stockCount;
        summaryItems[2].textContent = (projectedReturn * 100).toFixed(1) + '%';
        summaryItems[3].textContent = totalAllocation === 100 ? 'Moderate' : 'Low';
    }
}

// Modals
function initModals() {
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const loginModal = document.getElementById('loginModal');
    const signupModal = document.getElementById('signupModal');

    if (loginBtn && loginModal) {
        loginBtn.addEventListener('click', () => loginModal.classList.add('active'));
    }
    if (signupBtn && signupModal) {
        signupBtn.addEventListener('click', () => signupModal.classList.add('active'));
    }

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').classList.remove('active');
        });
    });
}

// Animate Counters
function animateCounters() {
    const counters = document.querySelectorAll('.stat-value[data-target]');
    
    counters.forEach(counter => {
        const target = parseFloat(counter.dataset.target);
        const suffix = counter.dataset.suffix || '';
        const duration = 2000;
        const start = 0;
        const startTime = performance.now();

        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = start + (target - start) * easeOut;
            
            counter.textContent = (target >= 1000000) 
                ? (current / 1000000).toFixed(1) + 'M' + suffix 
                : current.toFixed(target % 1 === 0 ? 0 : 1) + suffix;

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }

        requestAnimationFrame(updateCounter);
    });
}

// Smooth scroll for nav links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});
