/* TradingAgents Web - Frontend JavaScript */

const API = '';
let providers = [];
let currentRunId = null;
let eventSource = null;
let currentSettings = null;

// Providers that require an API key (ollama/bedrock excluded)
const PROVIDERS_NEEDING_KEY = new Set([
    'openai', 'anthropic', 'google', 'xai', 'deepseek', 'qwen', 'qwen-cn',
    'glm', 'glm-cn', 'minimax', 'minimax-cn', 'openrouter', 'mistral',
    'kimi', 'groq', 'nvidia', 'openai_compatible',
]);

// Display names for API key fields
const KEY_DISPLAY_NAMES = {
    openai: 'OpenAI', anthropic: 'Anthropic', google: 'Google Gemini',
    xai: 'xAI (Grok)', deepseek: 'DeepSeek', qwen: 'Qwen (International)',
    'qwen-cn': 'Qwen (China)', glm: 'GLM (Z.AI International)',
    'glm-cn': 'GLM (BigModel China)', minimax: 'MiniMax (International)',
    'minimax-cn': 'MiniMax (China)', openrouter: 'OpenRouter', mistral: 'Mistral',
    kimi: 'Kimi', groq: 'Groq', nvidia: 'NVIDIA',
    openai_compatible: 'OpenAI-Compatible', FRED_API_KEY: 'FRED API Key',
};

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    initDateField();
    initProviders();
    initFormHandlers();
    initTabs();
    initSettings();
});

function initDateField() {
    const dateInput = document.getElementById('date');
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    dateInput.max = today;
}

async function initProviders() {
    try {
        const resp = await fetch(`${API}/api/providers`);
        providers = await resp.json();
        populateProviderDropdown();
        updateModelDropdowns();
    } catch (e) {
        console.error('Failed to load providers:', e);
    }
    await loadSettings();
}

function populateProviderDropdown() {
    const sel = document.getElementById('provider');
    sel.innerHTML = '';
    providers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.provider;
        opt.textContent = p.display_name;
        sel.appendChild(opt);
    });
    // Default to openai if available
    const openai = providers.find(p => p.provider === 'openai');
    if (openai) sel.value = 'openai';
}

function updateModelDropdowns() {
    const providerKey = document.getElementById('provider').value;
    const provider = providers.find(p => p.provider === providerKey);
    if (!provider) return;

    const quickSel = document.getElementById('quick-model');
    const deepSel = document.getElementById('deep-model');

    quickSel.innerHTML = '';
    provider.quick_models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.value;
        opt.textContent = m.label;
        quickSel.appendChild(opt);
    });

    deepSel.innerHTML = '';
    provider.deep_models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.value;
        opt.textContent = m.label;
        deepSel.appendChild(opt);
    });
}

// --- Settings ---

function initSettings() {
    document.getElementById('settings-btn').addEventListener('click', openSettingsModal);
    document.getElementById('settings-close').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-cancel').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-save').addEventListener('click', saveSettings);
    document.getElementById('settings-overlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeSettingsModal();
    });

    // Settings provider change → update model dropdowns in settings modal
    document.getElementById('s-provider').addEventListener('change', updateSettingsModelDropdowns);

    // Missing API key modal
    document.querySelectorAll('.apikey-cancel').forEach(btn => {
        btn.addEventListener('click', closeApiKeyModal);
    });
    document.getElementById('apikey-modal-overlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeApiKeyModal();
    });
    document.getElementById('apikey-toggle').addEventListener('click', () => {
        const inp = document.getElementById('apikey-input');
        inp.type = inp.type === 'password' ? 'text' : 'password';
    });
    document.getElementById('apikey-save-run').addEventListener('click', saveApiKeyAndRun);
}

async function loadSettings() {
    try {
        const resp = await fetch(`${API}/api/settings`);
        currentSettings = await resp.json();
    } catch (e) {
        console.error('Failed to load settings:', e);
        currentSettings = null;
    }
}

function openSettingsModal() {
    if (!currentSettings) return;
    renderApiKeys();
    populateSettingsForm();
    document.getElementById('settings-overlay').style.display = '';
}

function closeSettingsModal() {
    document.getElementById('settings-overlay').style.display = 'none';
}

function renderApiKeys() {
    const grid = document.getElementById('api-keys-grid');
    grid.innerHTML = '';
    const keys = currentSettings.api_keys || {};
    for (const [key, displayName] of Object.entries(KEY_DISPLAY_NAMES)) {
        const val = keys[key] || '';
        const div = document.createElement('div');
        div.className = 'form-group';
        div.innerHTML = `
            <label>${displayName}</label>
            <div class="apikey-row">
                <input type="password" data-key="${key}" value="${val === '***' ? '' : val}"
                       placeholder="${val === '***' ? 'Configured' : 'Not set'}">
                <button class="btn-icon toggle-key" title="Show/Hide">&#128065;</button>
            </div>
        `;
        grid.appendChild(div);
    }
    // Toggle visibility buttons
    grid.querySelectorAll('.toggle-key').forEach(btn => {
        btn.addEventListener('click', () => {
            const inp = btn.previousElementSibling;
            inp.type = inp.type === 'password' ? 'text' : 'password';
        });
    });
}

function populateSettingsForm() {
    const llm = currentSettings.llm || {};
    const analysis = currentSettings.analysis || {};
    const data = currentSettings.data || {};
    const vendors = data.data_vendors || {};

    // Provider
    const provSel = document.getElementById('s-provider');
    provSel.innerHTML = '';
    providers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.provider;
        opt.textContent = p.display_name;
        provSel.appendChild(opt);
    });
    provSel.value = llm.provider || 'openai';

    updateSettingsModelDropdowns();
    document.getElementById('s-quick-model').value = llm.quick_think_model || '';
    document.getElementById('s-deep-model').value = llm.deep_think_model || '';
    document.getElementById('s-temperature').value = llm.temperature ?? '';
    document.getElementById('s-backend-url').value = llm.backend_url || '';
    document.getElementById('s-google-thinking').value = llm.google_thinking_level || '';
    document.getElementById('s-openai-effort').value = llm.openai_reasoning_effort || '';
    document.getElementById('s-anthropic-effort').value = llm.anthropic_effort || '';

    document.getElementById('s-language').value = analysis.output_language || 'English';
    document.getElementById('s-depth').value = String(analysis.research_depth || 1);
    document.getElementById('s-risk-rounds').value = String(analysis.max_risk_discuss_rounds || 1);

    document.getElementById('s-vendor-core').value = vendors.core_stock_apis || 'yfinance';
    document.getElementById('s-vendor-technical').value = vendors.technical_indicators || 'yfinance';
    document.getElementById('s-vendor-fundamental').value = vendors.fundamental_data || 'yfinance';
    document.getElementById('s-vendor-news').value = vendors.news_data || 'yfinance';
    document.getElementById('s-vendor-macro').value = vendors.macro_data || 'fred';
    document.getElementById('s-vendor-prediction').value = vendors.prediction_markets || 'polymarket';
}

function updateSettingsModelDropdowns() {
    const providerKey = document.getElementById('s-provider').value;
    const provider = providers.find(p => p.provider === providerKey);
    if (!provider) return;

    const quickSel = document.getElementById('s-quick-model');
    const deepSel = document.getElementById('s-deep-model');

    quickSel.innerHTML = '';
    provider.quick_models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.value;
        opt.textContent = m.label;
        quickSel.appendChild(opt);
    });

    deepSel.innerHTML = '';
    provider.deep_models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.value;
        opt.textContent = m.label;
        deepSel.appendChild(opt);
    });
}

async function saveSettings() {
    const apiKeys = {};
    document.querySelectorAll('#api-keys-grid input[data-key]').forEach(inp => {
        const key = inp.dataset.key;
        const val = inp.value.trim();
        // If field is empty and was originally masked, keep as "***"
        if (!val && inp.placeholder === 'Configured') {
            apiKeys[key] = '***';
        } else if (val) {
            apiKeys[key] = val;
        } else {
            apiKeys[key] = '';
        }
    });

    const tempVal = document.getElementById('s-temperature').value;
    const backendUrl = document.getElementById('s-backend-url').value.trim();
    const googleThinking = document.getElementById('s-google-thinking').value;
    const openaiEffort = document.getElementById('s-openai-effort').value;
    const anthropicEffort = document.getElementById('s-anthropic-effort').value;
    const body = {
        api_keys: apiKeys,
        llm: {
            provider: document.getElementById('s-provider').value,
            quick_think_model: document.getElementById('s-quick-model').value,
            deep_think_model: document.getElementById('s-deep-model').value,
            temperature: tempVal ? parseFloat(tempVal) : null,
            backend_url: backendUrl || null,
            google_thinking_level: googleThinking || null,
            openai_reasoning_effort: openaiEffort || null,
            anthropic_effort: anthropicEffort || null,
        },
        analysis: {
            output_language: document.getElementById('s-language').value,
            research_depth: parseInt(document.getElementById('s-depth').value),
            max_risk_discuss_rounds: parseInt(document.getElementById('s-risk-rounds').value),
        },
        data: {
            data_vendors: {
                core_stock_apis: document.getElementById('s-vendor-core').value,
                technical_indicators: document.getElementById('s-vendor-technical').value,
                fundamental_data: document.getElementById('s-vendor-fundamental').value,
                news_data: document.getElementById('s-vendor-news').value,
                macro_data: document.getElementById('s-vendor-macro').value,
                prediction_markets: document.getElementById('s-vendor-prediction').value,
            },
        },
    };

    try {
        const resp = await fetch(`${API}/api/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            alert(`Failed to save settings: ${err.detail || resp.statusText}`);
            return;
        }
        currentSettings = await resp.json();
        closeSettingsModal();
        // Sync main form provider/models if changed
        const mainProv = document.getElementById('provider');
        if (mainProv.value !== body.llm.provider) {
            mainProv.value = body.llm.provider;
            updateModelDropdowns();
        }
    } catch (e) {
        alert(`Failed to save settings: ${e.message}`);
    }
}

// --- Missing API Key Modal ---

let _pendingAnalysisBody = null;

function showApiKeyModal(providerKey, displayName) {
    document.getElementById('apikey-message').textContent =
        `Please provide an API key for ${displayName}.`;
    document.getElementById('apikey-input').value = '';
    document.getElementById('apikey-input').type = 'password';
    document.getElementById('apikey-modal-overlay').dataset.providerKey = providerKey;
    document.getElementById('apikey-modal-overlay').style.display = '';
}

function closeApiKeyModal() {
    document.getElementById('apikey-modal-overlay').style.display = 'none';
    _pendingAnalysisBody = null;
}

async function saveApiKeyAndRun() {
    const providerKey = document.getElementById('apikey-modal-overlay').dataset.providerKey;
    const apiKey = document.getElementById('apikey-input').value.trim();
    if (!apiKey) return;

    // Save just this API key
    const body = { api_keys: { [providerKey]: apiKey } };
    try {
        const resp = await fetch(`${API}/api/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            alert(`Failed to save: ${err.detail || resp.statusText}`);
            return;
        }
        currentSettings = await resp.json();
        closeApiKeyModal();
        // Resume analysis
        if (_pendingAnalysisBody) {
            executeAnalysis(_pendingAnalysisBody);
            _pendingAnalysisBody = null;
        }
    } catch (e) {
        alert(`Failed to save API key: ${e.message}`);
    }
}

// --- Event Handlers ---

function initFormHandlers() {
    document.getElementById('provider').addEventListener('change', updateModelDropdowns);

    document.getElementById('ticker').addEventListener('input', (e) => {
        const hint = document.getElementById('asset-type-hint');
        const type = detectAssetType(e.target.value);
        hint.textContent = type !== 'stock' ? `Detected: ${type}` : '';
    });

    document.getElementById('analysis-form').addEventListener('submit', (e) => {
        e.preventDefault();
        startAnalysis();
    });
}

function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const section = tab.dataset.tab;
            const content = reportSections[section];
            document.getElementById('report-content').textContent = content || 'Waiting for data...';
        });
    });
}

// --- Asset Type Detection ---

function detectAssetType(ticker) {
    if (!ticker) return 'stock';
    const t = ticker.toUpperCase().trim();
    const cryptoPatterns = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', '-USD'];
    if (cryptoPatterns.some(p => t.includes(p))) return 'crypto';
    return 'stock';
}

// --- Analysis ---

function isProviderKeyConfigured(providerKey) {
    // Providers that don't need API keys
    if (!PROVIDERS_NEEDING_KEY.has(providerKey)) return true;
    // Check settings
    if (!currentSettings || !currentSettings.api_keys) return false;
    const val = currentSettings.api_keys[providerKey];
    return val && val !== '';
}

async function startAnalysis() {
    const ticker = document.getElementById('ticker').value.trim();
    if (!ticker) return;

    const analystCheckboxes = document.querySelectorAll('input[name="analyst"]:checked');
    const analysts = Array.from(analystCheckboxes).map(cb => cb.value);
    if (analysts.length === 0) {
        alert('Please select at least one analyst.');
        return;
    }

    const body = {
        ticker: ticker,
        date: document.getElementById('date').value,
        asset_type: detectAssetType(ticker),
        analysts: analysts,
        llm_provider: document.getElementById('provider').value,
        deep_think_model: document.getElementById('deep-model').value,
        quick_think_model: document.getElementById('quick-model').value,
        research_depth: parseInt(document.getElementById('depth').value),
        output_language: document.getElementById('language').value,
    };

    // Check if API key is configured for the selected provider
    const providerKey = body.llm_provider;
    if (!isProviderKeyConfigured(providerKey)) {
        const display = KEY_DISPLAY_NAMES[providerKey] || providerKey;
        _pendingAnalysisBody = body;
        showApiKeyModal(providerKey, display);
        return;
    }

    executeAnalysis(body);
}

async function executeAnalysis(body) {
    const ticker = body.ticker;

    // Disable form
    document.getElementById('start-btn').disabled = true;
    document.getElementById('start-btn').textContent = 'Running...';

    // Reset state
    reportSections = {};
    document.getElementById('progress-panel').style.display = '';
    document.getElementById('results-panel').style.display = '';
    document.getElementById('signal-display').style.display = 'none';
    document.getElementById('log-entries').innerHTML = '';
    document.getElementById('report-content').textContent = 'Waiting for data...';
    initAgentGrid(body.analysts);

    try {
        const resp = await fetch(`${API}/api/runs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (resp.status === 409) {
            alert('An analysis is already running. Please wait for it to complete.');
            resetUI();
            return;
        }

        if (!resp.ok) {
            const err = await resp.json();
            alert(`Error: ${err.detail || resp.statusText}`);
            resetUI();
            return;
        }

        const data = await resp.json();
        currentRunId = data.run_id;
        appendLog(`Analysis started: ${ticker} on ${body.date}`);
        startSSE(currentRunId);
    } catch (e) {
        alert(`Failed to start analysis: ${e.message}`);
        resetUI();
    }
}

// --- SSE ---

function startSSE(runId) {
    if (eventSource) eventSource.close();
    eventSource = new EventSource(`${API}/api/runs/${runId}/events`);

    eventSource.addEventListener('agent_status', (e) => {
        const d = JSON.parse(e.data);
        updateAgentStatus(d.agent, d.status);
    });

    eventSource.addEventListener('report_update', (e) => {
        const d = JSON.parse(e.data);
        reportSections[d.section] = d.content;
        // Update tab if this section is active
        const activeTab = document.querySelector('.tab.active');
        if (activeTab && activeTab.dataset.tab === d.section) {
            document.getElementById('report-content').textContent = d.content;
        }
    });

    eventSource.addEventListener('progress', (e) => {
        const d = JSON.parse(e.data);
        if (d.message) appendLog(d.message);
        if (d.tool_call) appendLog(`Tool: ${d.tool_call}`);
    });

    eventSource.addEventListener('complete', (e) => {
        const d = JSON.parse(e.data);
        appendLog(`Analysis complete. Signal: ${d.signal || 'N/A'}`);
        showSignal(d.signal);
        eventSource.close();
        eventSource = null;
        resetUI();
    });

    eventSource.addEventListener('error', (e) => {
        if (eventSource && eventSource.readyState === EventSource.CLOSED) return;
        try {
            const d = JSON.parse(e.data);
            appendLog(`Error: ${d.message}`);
        } catch {
            appendLog('Connection error');
        }
        eventSource.close();
        eventSource = null;
        resetUI();
    });
}

// --- Agent Grid ---

const ALL_TEAMS = {
    'Analyst Team': ['Market Analyst', 'Sentiment Analyst', 'News Analyst', 'Fundamentals Analyst'],
    'Research Team': ['Bull Researcher', 'Bear Researcher', 'Research Manager'],
    'Trading Team': ['Trader'],
    'Risk Management': ['Aggressive Analyst', 'Neutral Analyst', 'Conservative Analyst'],
    'Portfolio Management': ['Portfolio Manager'],
};

const ANALYST_MAP = {
    market: 'Market Analyst',
    social: 'Sentiment Analyst',
    news: 'News Analyst',
    fundamentals: 'Fundamentals Analyst',
};

function initAgentGrid(selectedAnalysts) {
    const grid = document.getElementById('agent-grid');
    grid.innerHTML = '';

    for (const [team, agents] of Object.entries(ALL_TEAMS)) {
        const teamAgents = agents.filter(a => {
            // Always show non-analyst agents
            if (!Object.values(ANALYST_MAP).includes(a)) return true;
            // Show selected analysts
            return selectedAnalysts.some(sel => ANALYST_MAP[sel] === a);
        });

        for (const agent of teamAgents) {
            const card = document.createElement('div');
            card.className = 'agent-card';
            card.id = `agent-${agent.replace(/\s+/g, '-')}`;
            card.innerHTML = `
                <span class="agent-name">${agent}</span>
                <span class="status status-pending">pending</span>
            `;
            grid.appendChild(card);
        }
    }
}

function updateAgentStatus(agent, status) {
    const card = document.getElementById(`agent-${agent.replace(/\s+/g, '-')}`);
    if (!card) return;
    const statusEl = card.querySelector('.status');
    statusEl.className = `status status-${status}`;
    if (status === 'in_progress') {
        statusEl.innerHTML = `<span class="spinner"></span>running`;
    } else {
        statusEl.textContent = status;
    }
}

// --- Signal Display ---

function showSignal(signal) {
    if (!signal) return;
    const box = document.getElementById('signal-display');
    box.style.display = '';
    const lower = signal.toLowerCase();
    let cls = 'signal-hold';
    if (lower.includes('buy') || lower.includes('overweight')) cls = 'signal-buy';
    else if (lower.includes('sell') || lower.includes('underweight')) cls = 'signal-sell';
    box.className = `signal-box ${cls}`;
    box.textContent = `Signal: ${signal}`;
}

// --- Activity Log ---

function appendLog(message) {
    const container = document.getElementById('log-entries');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const time = new Date().toLocaleTimeString();
    entry.textContent = `[${time}] ${message}`;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
}

// --- UI Reset ---

function resetUI() {
    document.getElementById('start-btn').disabled = false;
    document.getElementById('start-btn').textContent = 'Start Analysis';
}

// --- Report Sections State ---

let reportSections = {};
