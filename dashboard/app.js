// IFSA Market Monitor Dashboard - Frontend Logic
const API_BASE = window.location.hostname.includes('netlify') || window.location.hostname.includes('localhost:8888')
    ? '/api'
    : ''; // For FastAPI, API is at root, but we try /api first then fallback

// For local dev with FastAPI on :8000, dashboard served from :8000/dashboard
// API calls should go to :8000
const getApiUrl = (path) => {
    // If served from Netlify, use /api prefix
    if (window.location.pathname.includes('/dashboard') && !window.location.hostname.includes('netlify')) {
        // Hostinger / FastAPI - API is at root
        return path;
    }
    // Netlify
    if (path.startsWith('/')) {
        // Try /api + path, but for health etc we have redirects
        return `/api${path}`;
    }
    return `/api/${path}`;
};

// Fallback logic for dual deployment
async function apiFetch(path, options = {}) {
    const urlsToTry = [
        `/api${path}`,           // Netlify style
        path,                    // FastAPI root style
        `/.netlify/functions/api${path}`, // Direct Netlify function
    ];

    let lastError;
    for (const url of urlsToTry) {
        try {
            const res = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...(options.headers || {})
                }
            });
            if (res.ok || res.status < 500) {
                // If 404, try next
                if (res.status === 404) {
                    lastError = new Error(`404 for ${url}`);
                    continue;
                }
                const text = await res.text();
                try {
                    return JSON.parse(text);
                } catch {
                    return text;
                }
            }
        } catch (e) {
            lastError = e;
        }
    }
    throw lastError || new Error('All API endpoints failed');
}

async function loadStatus() {
    try {
        const data = await apiFetch('/status');
        updateStats(data.stats || data);
        updateAssets(data.assets || []);
        updateConfig(data.config);

        document.getElementById('statusBadge').textContent = 'Healthy';
        document.getElementById('statusBadge').className = 'badge healthy';
        document.getElementById('lastUpdate').textContent = `Updated: ${new Date().toLocaleTimeString()}`;
        document.getElementById('healthStatus').textContent = 'Healthy';
    } catch (e) {
        console.error('Failed to load status', e);
        document.getElementById('statusBadge').textContent = 'Degraded';
        document.getElementById('statusBadge').className = 'badge degraded';
        document.getElementById('healthStatus').textContent = 'Degraded';
        // Load mock data for demo if API fails
        loadMockData();
    }
}

function updateStats(stats) {
    document.getElementById('totalAssets').textContent = stats.tracked_symbols?.length || stats.tracked_symbols?.length || '-';
    document.getElementById('totalAlerts').textContent = stats.total_alerts_sent || 0;
    document.getElementById('uptime').textContent = stats.uptime_human || '-';
}

function updateAssets(assets) {
    const tbody = document.getElementById('assetsTableBody');
    if (!assets || assets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No assets configured</td></tr>';
        return;
    }

    tbody.innerHTML = assets.map(asset => {
        const ind = asset.last_indicator;
        const price = asset.last_price || ind?.price || 0;
        const rsi = ind?.rsi;
        const rsiClass = rsi ? (rsi >= 70 ? 'overbought' : rsi <= 30 ? 'oversold' : 'neutral') : 'neutral';

        const smaFast = ind?.sma_fast?.toFixed(2) || '-';
        const smaSlow = ind?.sma_slow?.toFixed(2) || '-';
        const emaFast = ind?.ema_fast?.toFixed(2) || '-';
        const emaSlow = ind?.ema_slow?.toFixed(2) || '-';
        const macd = ind?.macd?.toFixed(4) || '-';
        const macdSignal = ind?.macd_signal?.toFixed(4) || '-';

        // Determine MA trend
        let smaTrend = '';
        if (ind?.sma_fast && ind?.sma_slow) {
            smaTrend = ind.sma_fast > ind.sma_slow ? '<span class="ma-bull">▲ Bull</span>' : '<span class="ma-bear">▼ Bear</span>';
        }

        return `
            <tr>
                <td><strong>${asset.symbol}</strong><br><small style="color:#64748b">${asset.name || asset.type || ''}</small></td>
                <td class="price">$${Number(price).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:4})}</td>
                <td><span class="rsi ${rsiClass}">${rsi ? rsi.toFixed(1) : '-'}</span></td>
                <td>${smaFast} / ${smaSlow} ${smaTrend}</td>
                <td>${emaFast} / ${emaSlow}</td>
                <td>${macd}</td>
                <td>${macdSignal}</td>
            </tr>
        `;
    }).join('');
}

function updateConfig(config) {
    if (!config) return;

    const tgEnabled = config.telegram_enabled || config.alerts?.channels?.telegram?.enabled;
    const discordEnabled = config.discord_enabled || config.alerts?.channels?.discord?.enabled;

    const tgEl = document.getElementById('telegramStatus');
    tgEl.className = `status-dot ${tgEnabled ? 'enabled' : 'disabled'}`;
    tgEl.title = tgEnabled ? 'Enabled' : 'Disabled';

    const dcEl = document.getElementById('discordStatus');
    dcEl.className = `status-dot ${discordEnabled ? 'enabled' : 'disabled'}`;
    dcEl.title = discordEnabled ? 'Enabled' : 'Disabled';

    const indicators = config.indicators || {};
    const indList = document.getElementById('indicatorsList');
    indList.innerHTML = `
        RSI: ${indicators.rsi?.enabled ? '✅' : '❌'} (${indicators.rsi?.period || 14})<br>
        MA: ${indicators.moving_averages?.enabled ? '✅' : '❌'}<br>
        MACD: ${indicators.macd?.enabled ? '✅' : '❌'}<br>
        BB: ${indicators.bollinger?.enabled ? '✅' : '❌'}
    `;
}

async function loadAlerts() {
    const container = document.getElementById('alertsList');
    container.innerHTML = '<div class="loading">Loading alerts...</div>';

    try {
        const data = await apiFetch('/alerts/history?limit=20');
        const alerts = data.history || data || [];

        if (alerts.length === 0) {
            container.innerHTML = '<div class="loading">No alerts yet. Markets are calm... 😴</div>';
            return;
        }

        container.innerHTML = alerts.map(alert => {
            const time = new Date(alert.timestamp).toLocaleString();
            const severity = alert.severity || 'info';
            return `
                <div class="alert-item ${severity}">
                    <div class="alert-item-header">
                        <span class="alert-title">${alert.title || alert.type}</span>
                        <span class="alert-symbol">${alert.symbol}</span>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                    <div style="display:flex; justify-content:space-between; margin-top:8px;">
                        <span class="alert-price">$${Number(alert.price).toLocaleString()}</span>
                        <span class="alert-time">${time}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load alerts', e);
        container.innerHTML = `<div class="loading">Failed to load alerts: ${e.message}</div>`;
    }
}

function loadMockData() {
    // Demo data when API not available (e.g., opening file directly)
    const mockAssets = [
        {symbol: 'XAUUSD', name: 'Gold Spot', type: 'FOREX', last_price: 2035.42, last_indicator: {price: 2035.42, rsi: 62.3, sma_fast: 2010.5, sma_slow: 1985.2, ema_fast: 2030.1, ema_slow: 2020.3, macd: 1.23, macd_signal: 0.98}},
        {symbol: 'BTCUSDT', name: 'Bitcoin', type: 'CRYPTO', last_price: 67342.12, last_indicator: {price: 67342.12, rsi: 71.5, sma_fast: 65000, sma_slow: 60000, ema_fast: 67000, ema_slow: 66500, macd: 250, macd_signal: 200}},
        {symbol: 'ETHUSDT', name: 'Ethereum', type: 'CRYPTO', last_price: 3421.89, last_indicator: {price: 3421.89, rsi: 45.2, sma_fast: 3300, sma_slow: 3100, ema_fast: 3400, ema_slow: 3380, macd: 15, macd_signal: 12}},
    ];
    updateAssets(mockAssets);
    document.getElementById('totalAssets').textContent = mockAssets.length;
    document.getElementById('totalAlerts').textContent = '127';
    document.getElementById('uptime').textContent = '2h 15m';
}

// Event Listeners
document.getElementById('triggerBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('triggerBtn');
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
    btn.disabled = true;

    try {
        const result = await apiFetch('/trigger', {method: 'POST'});
        alert(`Scan completed! Processed ${result.assets_processed || 0} assets`);
        await loadStatus();
        await loadAlerts();
    } catch (e) {
        alert(`Trigger failed: ${e.message}`);
    } finally {
        btn.innerHTML = original;
        btn.disabled = false;
    }
});

document.getElementById('testAlertBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('testAlertBtn');
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    btn.disabled = true;

    try {
        const result = await apiFetch('/alerts/test?symbol=BTCUSDT', {method: 'POST'});
        alert(`Test alert sent! ${result.message || 'Check Telegram/Discord'}`);
    } catch (e) {
        alert(`Test alert failed: ${e.message}`);
    } finally {
        btn.innerHTML = original;
        btn.disabled = false;
    }
});

document.getElementById('refreshAlerts')?.addEventListener('click', loadAlerts);

// Auto-refresh
setInterval(loadStatus, 30000); // 30s
setInterval(loadAlerts, 60000); // 60s

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadStatus();
    loadAlerts();
});
