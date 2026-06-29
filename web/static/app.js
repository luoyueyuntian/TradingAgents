/* TradingAgents Web - Frontend JavaScript */

const API = '';
let providers = [];
let currentRunId = null;
let eventSource = null;
let currentSettings = null;
let reportSections = {};
let autoRefreshTimer = null;
const TENANT_STORAGE_KEY = 'tradingagents.tenantId';
const API_TOKEN_STORAGE_KEY = 'tradingagents.apiToken';

// Providers that require an API key (ollama/bedrock and generic local servers excluded)
const PROVIDERS_NEEDING_KEY = new Set([
    'openai', 'anthropic', 'google', 'xai', 'deepseek', 'qwen', 'qwen-cn',
    'glm', 'glm-cn', 'minimax', 'minimax-cn', 'openrouter', 'mistral',
    'kimi', 'groq', 'nvidia',
]);

// Display names for API key fields
const KEY_DISPLAY_NAMES = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google Gemini',
    xai: 'xAI (Grok)',
    deepseek: 'DeepSeek',
    qwen: 'Qwen (International)',
    'qwen-cn': 'Qwen (China)',
    glm: 'GLM (Z.AI International)',
    'glm-cn': 'GLM (BigModel China)',
    minimax: 'MiniMax (International)',
    'minimax-cn': 'MiniMax (China)',
    openrouter: 'OpenRouter',
    mistral: 'Mistral',
    kimi: 'Kimi',
    groq: 'Groq',
    nvidia: 'NVIDIA',
    openai_compatible: 'OpenAI-Compatible API Key (optional)',
    FRED_API_KEY: 'FRED API Key',
    AWS_DEFAULT_REGION: 'AWS Region',
    AWS_PROFILE: 'AWS Profile',
    OLLAMA_BASE_URL: 'Ollama Base URL',
};

document.addEventListener('DOMContentLoaded', () => {
    initDateField();
    initTenantField();
    initApiTokenField();
    initSettings();
    initFormHandlers();
    initTabs();
    initDownloads();
    startAutoRefresh();
    void loadSystemStatus();
    void initProviders();
});

function initTenantField() {
    const input = document.getElementById('tenant-id');
    input.value = window.localStorage.getItem(TENANT_STORAGE_KEY) || '';
    input.addEventListener('change', async () => {
        window.localStorage.setItem(TENANT_STORAGE_KEY, input.value.trim());
        closeSSE();
        currentRunId = null;
        reportSections = {};
        document.getElementById('progress-panel').style.display = 'none';
        document.getElementById('results-panel').style.display = 'none';
        await loadSystemStatus();
        await loadRunHistory();
    });
}

function initApiTokenField() {
    const input = document.getElementById('api-token');
    input.value = window.localStorage.getItem(API_TOKEN_STORAGE_KEY) || '';
    input.addEventListener('change', async () => {
        window.localStorage.setItem(API_TOKEN_STORAGE_KEY, input.value.trim());
        closeSSE();
        currentRunId = null;
        reportSections = {};
        document.getElementById('progress-panel').style.display = 'none';
        document.getElementById('results-panel').style.display = 'none';
        await loadSystemStatus();
        await loadRunHistory();
    });
}

function getTenantId() {
    const value = document.getElementById('tenant-id')?.value.trim() || '';
    return value || null;
}

function getApiToken() {
    const value = document.getElementById('api-token')?.value.trim() || '';
    return value || null;
}

function buildApiUrl(path) {
    const url = new URL(`${API}${path}`, window.location.origin);
    const tenantId = getTenantId();
    if (tenantId) {
        url.searchParams.set('tenant_id', tenantId);
    }
    const apiToken = getApiToken();
    if (apiToken) {
        url.searchParams.set('api_token', apiToken);
    }
    return `${url.pathname}${url.search}`;
}

function apiHeaders(extraHeaders = {}) {
    const tenantId = getTenantId();
    const apiToken = getApiToken();
    return {
        ...(tenantId ? { 'X-TradingAgents-Tenant': tenantId } : {}),
        ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
        ...extraHeaders,
    };
}

function startAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
    }
    autoRefreshTimer = window.setInterval(() => {
        void loadSystemStatus();
        if (!isOverlayVisible('settings-overlay') && !isOverlayVisible('apikey-modal-overlay')) {
            void loadRunHistory();
        }
    }, 5000);
}

function isOverlayVisible(id) {
    return document.getElementById(id).style.display !== 'none';
}

function initDateField() {
    const dateInput = document.getElementById('date');
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    dateInput.max = today;
}

async function initProviders() {
    try {
        const resp = await fetch(buildApiUrl('/api/providers'));
        providers = await resp.json();
        populateProviderDropdown();
    } catch (e) {
        console.error('Failed to load providers:', e);
    }

    await loadSettings();
    applySettingsToMainForm();
    await loadRunHistory();
    await loadSystemStatus();
}

async function loadSystemStatus() {
    const el = document.getElementById('system-status');
    try {
        const resp = await fetch(buildApiUrl('/api/system/status'));
        if (!resp.ok) throw new Error(resp.statusText);
        const status = await resp.json();
        const lastSeen = status.worker_last_seen
            ? new Date(status.worker_last_seen).toLocaleTimeString()
            : 'n/a';
        el.innerHTML = `
            <span class="system-pill">${status.execution_mode}</span>
            <span class="system-pill">${status.state_backend}</span>
            <span>Queue: ${status.queue_depth}</span>
            <span>Runs: ${status.run_count}</span>
            <span>Worker: ${status.worker_running ? 'on' : 'off'}</span>
            <span>Mode: ${status.worker_mode || 'n/a'}</span>
            <span>Last seen: ${lastSeen}</span>
            <span class="system-location" title="${status.state_location}">${status.state_location}</span>
        `;
    } catch {
        el.textContent = '';
    }
}

function getProvider(providerKey) {
    return providers.find(p => p.provider === providerKey);
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
    if (providers.length > 0 && !sel.value) {
        const openai = providers.find(p => p.provider === 'openai');
        sel.value = openai ? 'openai' : providers[0].provider;
    }
}

function renderModelOptions(selectEl, options) {
    selectEl.innerHTML = '';
    options.forEach(model => {
        const opt = document.createElement('option');
        opt.value = model.value;
        opt.textContent = model.label;
        selectEl.appendChild(opt);
    });
}

function syncCustomModelInput(selectId, inputId) {
    const select = document.getElementById(selectId);
    const input = document.getElementById(inputId);
    const isCustom = select.value === 'custom';
    input.style.display = isCustom ? '' : 'none';
    input.required = isCustom;
    if (!isCustom) {
        input.value = '';
    }
}

function setModelSelection(selectId, inputId, options, selectedValue = null) {
    const select = document.getElementById(selectId);
    const input = document.getElementById(inputId);

    renderModelOptions(select, options);

    const knownValues = new Set(options.map(option => option.value));
    if (selectedValue && knownValues.has(selectedValue)) {
        select.value = selectedValue;
        input.value = '';
    } else if (selectedValue) {
        select.value = knownValues.has('custom') ? 'custom' : (options[0]?.value || '');
        input.value = selectedValue;
    } else {
        select.value = options[0]?.value || '';
        input.value = '';
    }

    syncCustomModelInput(selectId, inputId);
}

function resolveModelValue(selectId, inputId) {
    const select = document.getElementById(selectId);
    if (select.value !== 'custom') {
        return select.value || null;
    }

    const customValue = document.getElementById(inputId).value.trim();
    return customValue || null;
}

function parseOptionalInt(inputId, fallbackValue) {
    const raw = document.getElementById(inputId).value.trim();
    if (!raw) return fallbackValue;
    const parsed = parseInt(raw, 10);
    return Number.isNaN(parsed) ? fallbackValue : parsed;
}

function updateModelDropdowns(selectedQuick = null, selectedDeep = null) {
    const providerKey = document.getElementById('provider').value;
    const provider = getProvider(providerKey);
    if (!provider) return;

    setModelSelection('quick-model', 'quick-model-custom', provider.quick_models, selectedQuick);
    setModelSelection('deep-model', 'deep-model-custom', provider.deep_models, selectedDeep);
}

function updateSettingsModelDropdowns(selectedQuick = null, selectedDeep = null) {
    const providerKey = document.getElementById('s-provider').value;
    const provider = getProvider(providerKey);
    if (!provider) return;

    setModelSelection('s-quick-model', 's-quick-model-custom', provider.quick_models, selectedQuick);
    setModelSelection('s-deep-model', 's-deep-model-custom', provider.deep_models, selectedDeep);
}

async function loadSettings() {
    try {
        const resp = await fetch(buildApiUrl('/api/settings'));
        currentSettings = await resp.json();
    } catch (e) {
        console.error('Failed to load settings:', e);
        currentSettings = null;
    }
}

function applySettingsToMainForm() {
    if (!currentSettings || providers.length === 0) {
        updateModelDropdowns();
        return;
    }

    const llm = currentSettings.llm || {};
    const analysis = currentSettings.analysis || {};
    const provider = llm.provider || 'openai';
    const providerSelect = document.getElementById('provider');
    if (getProvider(provider)) {
        providerSelect.value = provider;
    }

    updateModelDropdowns(llm.quick_think_model || null, llm.deep_think_model || null);
    document.getElementById('language').value = analysis.output_language || 'English';
    document.getElementById('depth').value = String(analysis.research_depth || 1);
}

function initSettings() {
    document.getElementById('settings-btn').addEventListener('click', openSettingsModal);
    document.getElementById('settings-close').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-cancel').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-save').addEventListener('click', saveSettings);
    document.getElementById('settings-overlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeSettingsModal();
    });

    document.getElementById('s-provider').addEventListener('change', () => updateSettingsModelDropdowns());
    document.getElementById('s-quick-model').addEventListener('change', () => syncCustomModelInput('s-quick-model', 's-quick-model-custom'));
    document.getElementById('s-deep-model').addEventListener('change', () => syncCustomModelInput('s-deep-model', 's-deep-model-custom'));
    document.getElementById('s-web-api-token-toggle').addEventListener('click', () => {
        const inp = document.getElementById('s-web-api-token');
        inp.type = inp.type === 'password' ? 'text' : 'password';
    });

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

    grid.querySelectorAll('.toggle-key').forEach(btn => {
        btn.addEventListener('click', () => {
            const inp = btn.previousElementSibling;
            inp.type = inp.type === 'password' ? 'text' : 'password';
        });
    });
}

function setSelectValueIfPresent(selectId, value, fallbackValue) {
    const select = document.getElementById(selectId);
    const targetValue = value || fallbackValue;
    if ([...select.options].some(option => option.value === targetValue)) {
        select.value = targetValue;
    } else if (fallbackValue && [...select.options].some(option => option.value === fallbackValue)) {
        select.value = fallbackValue;
    }
}

function populateSettingsForm() {
    const llm = currentSettings.llm || {};
    const analysis = currentSettings.analysis || {};
    const data = currentSettings.data || {};
    const security = currentSettings.security || {};
    const vendors = data.data_vendors || {};

    const provSel = document.getElementById('s-provider');
    provSel.innerHTML = '';
    providers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.provider;
        opt.textContent = p.display_name;
        provSel.appendChild(opt);
    });
    provSel.value = llm.provider || 'openai';

    updateSettingsModelDropdowns(
        llm.quick_think_model || null,
        llm.deep_think_model || null,
    );
    document.getElementById('s-temperature').value = llm.temperature ?? '';
    document.getElementById('s-backend-url').value = llm.backend_url || '';
    document.getElementById('s-google-thinking').value = llm.google_thinking_level || '';
    document.getElementById('s-openai-effort').value = llm.openai_reasoning_effort || '';
    document.getElementById('s-anthropic-effort').value = llm.anthropic_effort || '';

    document.getElementById('s-language').value = analysis.output_language || 'English';
    document.getElementById('s-market-profile').value = analysis.market_profile || 'default';
    document.getElementById('s-depth').value = String(analysis.research_depth || 1);
    document.getElementById('s-risk-rounds').value = String(analysis.max_risk_discuss_rounds || 1);
    document.getElementById('s-max-recur').value = String(analysis.max_recur_limit || 100);
    document.getElementById('s-checkpoint-enabled').checked = Boolean(analysis.checkpoint_enabled);

    setSelectValueIfPresent('s-vendor-core', vendors.core_stock_apis, 'yfinance');
    setSelectValueIfPresent('s-vendor-technical', vendors.technical_indicators, 'yfinance');
    setSelectValueIfPresent('s-vendor-fundamental', vendors.fundamental_data, 'yfinance');
    setSelectValueIfPresent('s-vendor-news', vendors.news_data, 'yfinance');
    setSelectValueIfPresent('s-vendor-macro', vendors.macro_data, 'fred');
    setSelectValueIfPresent('s-vendor-prediction', vendors.prediction_markets, 'polymarket');

    document.getElementById('s-news-limit').value = String(data.news_article_limit || 20);
    document.getElementById('s-global-news-limit').value = String(data.global_news_article_limit || 10);
    document.getElementById('s-global-news-lookback').value = String(data.global_news_lookback_days || 7);
    document.getElementById('s-web-api-token').value = '';
    document.getElementById('s-web-api-token').placeholder = security.web_api_token === '***' ? 'Configured' : 'Not set';
}

async function saveSettings() {
    const apiKeys = {};
    document.querySelectorAll('#api-keys-grid input[data-key]').forEach(inp => {
        const key = inp.dataset.key;
        const val = inp.value.trim();
        if (!val && inp.placeholder === 'Configured') {
            apiKeys[key] = '***';
        } else if (val) {
            apiKeys[key] = val;
        } else {
            apiKeys[key] = '';
        }
    });

    const quickModel = resolveModelValue('s-quick-model', 's-quick-model-custom');
    const deepModel = resolveModelValue('s-deep-model', 's-deep-model-custom');
    if (!quickModel || !deepModel) {
        alert('Please enter a custom model ID when using the custom model option.');
        return;
    }

    const tempVal = document.getElementById('s-temperature').value;
    const backendUrl = document.getElementById('s-backend-url').value.trim();
    const body = {
        api_keys: apiKeys,
        security: {
            web_api_token: (() => {
                const value = document.getElementById('s-web-api-token').value.trim();
                const placeholder = document.getElementById('s-web-api-token').placeholder;
                if (!value && placeholder === 'Configured') return '***';
                return value || null;
            })(),
        },
        llm: {
            provider: document.getElementById('s-provider').value,
            quick_think_model: quickModel,
            deep_think_model: deepModel,
            temperature: tempVal ? parseFloat(tempVal) : null,
            backend_url: backendUrl || null,
            google_thinking_level: document.getElementById('s-google-thinking').value || null,
            openai_reasoning_effort: document.getElementById('s-openai-effort').value || null,
            anthropic_effort: document.getElementById('s-anthropic-effort').value || null,
        },
        analysis: {
            output_language: document.getElementById('s-language').value,
            market_profile: document.getElementById('s-market-profile').value,
            research_depth: parseInt(document.getElementById('s-depth').value, 10),
            max_risk_discuss_rounds: parseInt(document.getElementById('s-risk-rounds').value, 10),
            max_recur_limit: parseOptionalInt('s-max-recur', 100),
            checkpoint_enabled: document.getElementById('s-checkpoint-enabled').checked,
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
            news_article_limit: parseOptionalInt('s-news-limit', 20),
            global_news_article_limit: parseOptionalInt('s-global-news-limit', 10),
            global_news_lookback_days: parseOptionalInt('s-global-news-lookback', 7),
        },
    };

    try {
        const resp = await fetch(buildApiUrl('/api/settings'), {
            method: 'PUT',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            alert(`Failed to save settings: ${err.detail || resp.statusText}`);
            return;
        }
        currentSettings = await resp.json();
        closeSettingsModal();
        applySettingsToMainForm();
    } catch (e) {
        alert(`Failed to save settings: ${e.message}`);
    }
}

let pendingAnalysisBody = null;

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
    pendingAnalysisBody = null;
}

async function saveApiKeyAndRun() {
    const providerKey = document.getElementById('apikey-modal-overlay').dataset.providerKey;
    const apiKey = document.getElementById('apikey-input').value.trim();
    if (!apiKey) return;

    const resumeBody = pendingAnalysisBody;
    try {
        const resp = await fetch(buildApiUrl('/api/settings'), {
            method: 'PUT',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ api_keys: { [providerKey]: apiKey } }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            alert(`Failed to save API key: ${err.detail || resp.statusText}`);
            return;
        }
        currentSettings = await resp.json();
        document.getElementById('apikey-modal-overlay').style.display = 'none';
        pendingAnalysisBody = null;
        if (resumeBody) {
            executeAnalysis(resumeBody);
        }
    } catch (e) {
        alert(`Failed to save API key: ${e.message}`);
    }
}

function initFormHandlers() {
    document.getElementById('provider').addEventListener('change', () => updateModelDropdowns());
    document.getElementById('quick-model').addEventListener('change', () => syncCustomModelInput('quick-model', 'quick-model-custom'));
    document.getElementById('deep-model').addEventListener('change', () => syncCustomModelInput('deep-model', 'deep-model-custom'));
    document.getElementById('refresh-history').addEventListener('click', () => {
        void loadRunHistory();
    });
    document.getElementById('cancel-run').addEventListener('click', () => {
        void requestRunCancellation();
    });

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
            updateVisibleReport();
        });
    });
}

function initDownloads() {
    updateDownloadLinksFromArtifacts([]);
}

function updateVisibleReport(fallbackText = 'Waiting for data...') {
    const activeTab = document.querySelector('.tab.active');
    const section = activeTab ? activeTab.dataset.tab : null;
    const content = section ? reportSections[section] : null;
    document.getElementById('report-content').textContent = content || fallbackText;
}

function renderRunSummary(summary) {
    const container = document.getElementById('run-summary');
    if (!summary || Object.keys(summary).length === 0) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    const cards = [
        ['Provider', summary.llm_provider],
        ['Quick Model', summary.quick_think_model],
        ['Deep Model', summary.deep_think_model],
        ['Language', summary.output_language],
        ['Market Profile', summary.market_profile],
        ['Research Depth', summary.research_depth],
        ['Risk Rounds', summary.max_risk_discuss_rounds],
        ['Checkpoint', summary.checkpoint_enabled],
        ['Analysts', (summary.selected_analysts || []).join(', ')],
    ].filter(([, value]) => value !== undefined && value !== null && value !== '');

    container.innerHTML = cards.map(([label, value]) => `
        <div class="summary-card">
            <span class="summary-label">${label}</span>
            <span class="summary-value">${String(value)}</span>
        </div>
    `).join('');
    container.style.display = cards.length > 0 ? '' : 'none';
}

function formatTimelineEvent(record) {
    const data = record.data || {};
    switch (record.event) {
    case 'progress':
        if (data.message) return data.message;
        if (data.tool_call) return `Tool: ${data.tool_call}`;
        break;
    case 'agent_status':
        return `${data.agent}: ${data.status}`;
    case 'report_update':
        return `Updated ${data.section}`;
    case 'complete':
        return `Analysis complete. Signal: ${data.signal || 'N/A'}`;
    case 'cancelled':
        return data.message || 'Analysis cancelled';
    case 'error':
        return `Error: ${data.message || 'Analysis failed'}`;
    default:
        break;
    }
    return record.event;
}

function renderTimeline(records) {
    const container = document.getElementById('log-entries');
    container.innerHTML = '';
    records.forEach(record => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        const ts = record.timestamp ? new Date(record.timestamp).toLocaleTimeString() : '';
        const prefix = ts ? `[${ts}] ` : '';
        entry.textContent = `${prefix}${formatTimelineEvent(record)}`;
        container.appendChild(entry);
    });
    container.scrollTop = container.scrollHeight;
}

function updateDownloadLinksFromArtifacts(artifacts) {
    const reportLink = document.getElementById('download-report');
    const stateLink = document.getElementById('download-state');
    const artifactLinks = document.getElementById('artifact-links');

    const reportArtifact = artifacts.find(item => item.name === 'complete-report');
    const stateArtifact = artifacts.find(item => item.name === 'full-state');

    setDownloadLink(reportLink, reportArtifact?.download_url || '#', Boolean(reportArtifact));
    setDownloadLink(stateLink, stateArtifact?.download_url || '#', Boolean(stateArtifact));

    artifactLinks.innerHTML = '';
    artifacts
        .filter(item => item.name !== 'complete-report' && item.name !== 'full-state')
        .forEach(item => {
            const link = document.createElement('a');
            link.className = 'btn-secondary link-btn artifact-link';
            link.href = '#';
            link.textContent = item.label;
            link.addEventListener('click', (e) => {
                e.preventDefault();
                if (currentRunId) {
                    void previewArtifact(currentRunId, item.name, item.label);
                }
            });
            artifactLinks.appendChild(link);
        });
}

function setDownloadLink(linkEl, href, enabled) {
    linkEl.href = href && href !== '#' ? buildApiUrl(href) : '#';
    linkEl.classList.toggle('disabled', !enabled);
    linkEl.setAttribute('aria-disabled', enabled ? 'false' : 'true');
}

async function refreshArtifactLinks(runId) {
    if (!runId) {
        updateDownloadLinksFromArtifacts([]);
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}/artifacts`));
        if (!resp.ok) {
            updateDownloadLinksFromArtifacts([]);
            return;
        }
        updateDownloadLinksFromArtifacts(await resp.json());
    } catch {
        updateDownloadLinksFromArtifacts([]);
    }
}

async function loadRunTimeline(runId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}/timeline`));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        const records = await resp.json();
        renderTimeline(records);
    } catch {
        document.getElementById('log-entries').innerHTML = '';
    }
}

async function previewArtifact(runId, name, label) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}/artifacts/content?name=${encodeURIComponent(name)}`));
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById('report-content').textContent = payload.content;
        appendLog(`Previewing artifact: ${label}`);
    } catch (e) {
        alert(`Failed to preview artifact: ${e.message}`);
    }
}

function toggleCancelButton(visible) {
    const button = document.getElementById('cancel-run');
    button.style.display = visible ? '' : 'none';
    button.disabled = !visible;
}

function detectAssetType(ticker) {
    if (!ticker) return 'stock';
    const t = ticker.toUpperCase().trim();
    const cryptoPatterns = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', '-USD'];
    if (cryptoPatterns.some(p => t.includes(p))) return 'crypto';
    return 'stock';
}

function isProviderKeyConfigured(providerKey) {
    if (!PROVIDERS_NEEDING_KEY.has(providerKey)) return true;
    if (!currentSettings || !currentSettings.api_keys) return false;
    const val = currentSettings.api_keys[providerKey];
    return Boolean(val && val !== '');
}

async function loadRunHistory() {
    const listEl = document.getElementById('history-list');
    const emptyEl = document.getElementById('history-empty');

    try {
        const resp = await fetch(buildApiUrl('/api/runs'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        const runs = await resp.json();
        listEl.innerHTML = '';

        if (runs.length === 0) {
            emptyEl.style.display = '';
            return;
        }

        emptyEl.style.display = 'none';
        runs.forEach(run => {
            const item = document.createElement('div');
            const canDelete = ['completed', 'failed', 'cancelled'].includes(run.status);
            const canRetry = ['completed', 'failed', 'cancelled'].includes(run.status);
            const queueSuffix = run.status === 'queued' && run.queue_position
                ? ` (#${run.queue_position})`
                : '';
            item.className = 'history-item';
            item.innerHTML = `
                <div class="history-meta">
                    <div class="history-title">${run.ticker} · ${run.date}</div>
                    <div class="history-subtitle">${run.asset_type} · created ${run.created_at}</div>
                    <div class="history-signal">${run.signal || run.error || 'No final signal yet'}</div>
                </div>
                <div class="history-actions">
                    <span class="history-status status-${run.status}">${run.status}${queueSuffix}</span>
                    <button class="btn-secondary history-open" type="button" data-run-id="${run.run_id}">Open</button>
                    ${canRetry ? `<button class="btn-secondary history-retry" type="button" data-run-id="${run.run_id}">Retry</button>` : ''}
                    ${canDelete ? `<button class="btn-secondary history-delete" type="button" data-run-id="${run.run_id}">Delete</button>` : ''}
                </div>
            `;
            item.querySelector('.history-open').addEventListener('click', () => {
                void openRunDetails(run.run_id);
            });
            const retryButton = item.querySelector('.history-retry');
            if (retryButton) {
                retryButton.addEventListener('click', () => {
                    void requestRunRetry(run.run_id);
                });
            }
            const deleteButton = item.querySelector('.history-delete');
            if (deleteButton) {
                deleteButton.addEventListener('click', () => {
                    void requestRunDeletion(run.run_id);
                });
            }
            listEl.appendChild(item);
        });
    } catch (e) {
        emptyEl.style.display = '';
        emptyEl.textContent = `Failed to load runs: ${e.message}`;
    }
}

function initAgentGrid(selectedAnalysts) {
    const includedAgents = new Set();
    for (const agents of Object.values(ALL_TEAMS)) {
        agents.forEach(agent => {
            if (!Object.values(ANALYST_MAP).includes(agent)) {
                includedAgents.add(agent);
                return;
            }
            if (selectedAnalysts.some(sel => ANALYST_MAP[sel] === agent)) {
                includedAgents.add(agent);
            }
        });
    }
    renderAgentGrid(includedAgents);
}

function initAgentGridFromAgentNames(agentNames) {
    renderAgentGrid(new Set(agentNames));
}

function renderAgentGrid(includedAgents) {
    const grid = document.getElementById('agent-grid');
    grid.innerHTML = '';

    for (const agents of Object.values(ALL_TEAMS)) {
        for (const agent of agents) {
            if (!includedAgents.has(agent)) continue;
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

async function startAnalysis() {
    const ticker = document.getElementById('ticker').value.trim();
    if (!ticker) return;

    const analystCheckboxes = document.querySelectorAll('input[name="analyst"]:checked');
    const analysts = Array.from(analystCheckboxes).map(cb => cb.value);
    if (analysts.length === 0) {
        alert('Please select at least one analyst.');
        return;
    }

    const quickModel = resolveModelValue('quick-model', 'quick-model-custom');
    const deepModel = resolveModelValue('deep-model', 'deep-model-custom');
    if (!quickModel || !deepModel) {
        alert('Please enter a custom model ID when using the custom model option.');
        return;
    }

    const body = {
        ticker: ticker,
        date: document.getElementById('date').value,
        asset_type: detectAssetType(ticker),
        analysts: analysts,
        llm_provider: document.getElementById('provider').value,
        deep_think_model: deepModel,
        quick_think_model: quickModel,
        research_depth: parseInt(document.getElementById('depth').value, 10),
        output_language: document.getElementById('language').value,
    };

    const providerKey = body.llm_provider;
    if (!isProviderKeyConfigured(providerKey)) {
        const display = KEY_DISPLAY_NAMES[providerKey] || providerKey;
        pendingAnalysisBody = body;
        showApiKeyModal(providerKey, display);
        return;
    }

    await executeAnalysis(body);
}

async function executeAnalysis(body) {
    document.getElementById('start-btn').disabled = true;
    document.getElementById('start-btn').textContent = 'Running...';

    reportSections = {};
    document.getElementById('progress-panel').style.display = '';
    document.getElementById('results-panel').style.display = '';
    document.getElementById('signal-display').style.display = 'none';
    document.getElementById('log-entries').innerHTML = '';
    document.getElementById('report-content').textContent = 'Waiting for data...';
    initAgentGrid(body.analysts);
    updateDownloadLinksFromArtifacts([]);
    toggleCancelButton(false);

    try {
        const resp = await fetch(buildApiUrl('/api/runs'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
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
        appendLog(`Analysis queued: ${body.ticker} on ${body.date}`);
        toggleCancelButton(true);
        await loadRunHistory();
        await loadSystemStatus();
        startSSE(currentRunId);
    } catch (e) {
        alert(`Failed to start analysis: ${e.message}`);
        resetUI();
    }
}

async function openRunDetails(runId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}`));
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const run = await resp.json();
        currentRunId = runId;
        renderRunStatus(run);
    } catch (e) {
        alert(`Failed to load run: ${e.message}`);
    }
}

function renderRunStatus(run) {
    reportSections = run.report_sections || {};
    document.getElementById('progress-panel').style.display = '';
    document.getElementById('results-panel').style.display = '';
    renderRunSummary(run.config_summary || {});
    initAgentGridFromAgentNames(Object.keys(run.agents || {}));
    for (const [agent, status] of Object.entries(run.agents || {})) {
        updateAgentStatus(agent, status);
    }

    if (run.signal) {
        showSignal(run.signal);
    } else {
        document.getElementById('signal-display').style.display = 'none';
    }

    const fallback = run.final_report || run.current_report || 'No report available yet.';
    updateVisibleReport(fallback);
    toggleCancelButton(run.status === 'running' || run.status === 'cancelling');
    void loadRunTimeline(run.run_id);

    if (run.status === 'running' || run.status === 'cancelling') {
        startSSE(run.run_id);
        updateDownloadLinksFromArtifacts([]);
    } else {
        closeSSE();
        void refreshArtifactLinks(run.run_id);
        resetUI();
    }
}

function closeSSE() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

function startSSE(runId) {
    closeSSE();
    eventSource = new EventSource(buildApiUrl(`/api/runs/${runId}/events`));

    eventSource.addEventListener('agent_status', (e) => {
        const d = JSON.parse(e.data);
        updateAgentStatus(d.agent, d.status);
    });

    eventSource.addEventListener('report_update', (e) => {
        const d = JSON.parse(e.data);
        reportSections[d.section] = d.content;
        updateVisibleReport('Waiting for data...');
    });

    eventSource.addEventListener('progress', (e) => {
        const d = JSON.parse(e.data);
        if (d.message) appendLog(d.message);
        if (d.tool_call) appendLog(`Tool: ${d.tool_call}`);
    });

    eventSource.addEventListener('queued', (e) => {
        const d = JSON.parse(e.data);
        if (d.message) appendLog(d.message);
    });

    eventSource.addEventListener('complete', (e) => {
        const d = JSON.parse(e.data);
        appendLog(`Analysis complete. Signal: ${d.signal || 'N/A'}`);
        showSignal(d.signal);
        closeSSE();
        toggleCancelButton(false);
        resetUI();
        void loadRunHistory();
        void openRunDetails(runId);
    });

    eventSource.addEventListener('cancelled', () => {
        appendLog('Analysis cancelled.');
        closeSSE();
        toggleCancelButton(false);
        resetUI();
        void loadRunHistory();
        void openRunDetails(runId);
    });

    eventSource.addEventListener('error', (e) => {
        if (eventSource && eventSource.readyState === EventSource.CLOSED) return;
        try {
            const d = JSON.parse(e.data);
            appendLog(`Error: ${d.message}`);
            closeSSE();
            toggleCancelButton(false);
            resetUI();
            void loadRunHistory();
            void openRunDetails(runId);
            return;
        } catch {
            appendLog('Connection error');
        }
        closeSSE();
        toggleCancelButton(false);
        resetUI();
    });
}

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

function updateAgentStatus(agent, status) {
    const card = document.getElementById(`agent-${agent.replace(/\s+/g, '-')}`);
    if (!card) return;
    const statusEl = card.querySelector('.status');
    statusEl.className = `status status-${status}`;
    if (status === 'in_progress') {
        statusEl.innerHTML = '<span class="spinner"></span>running';
    } else {
        statusEl.textContent = status;
    }
}

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

function appendLog(message) {
    const container = document.getElementById('log-entries');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const time = new Date().toLocaleTimeString();
    entry.textContent = `[${time}] ${message}`;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
}

async function requestRunCancellation() {
    if (!currentRunId) return;

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${currentRunId}/cancel`), {
            method: 'POST',
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const run = await resp.json();
        appendLog('Cancellation requested.');
        toggleCancelButton(false);
        await loadRunHistory();
        await loadSystemStatus();
        renderRunStatus(run);
    } catch (e) {
        alert(`Failed to cancel run: ${e.message}`);
    }
}

async function requestRunDeletion(runId) {
    const confirmed = window.confirm('Delete this run and its saved artifacts?');
    if (!confirmed) return;

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}`), {
            method: 'DELETE',
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }

        if (currentRunId === runId) {
            currentRunId = null;
            reportSections = {};
            closeSSE();
            updateDownloadLinksFromArtifacts([]);
            document.getElementById('progress-panel').style.display = 'none';
            document.getElementById('results-panel').style.display = 'none';
            resetUI();
        }
        await loadRunHistory();
        await loadSystemStatus();
    } catch (e) {
        alert(`Failed to delete run: ${e.message}`);
    }
}

async function requestRunRetry(runId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}/retry`), {
            method: 'POST',
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const run = await resp.json();
        await loadRunHistory();
        await loadSystemStatus();
        await openRunDetails(run.run_id);
    } catch (e) {
        alert(`Failed to retry run: ${e.message}`);
    }
}

function resetUI() {
    document.getElementById('start-btn').disabled = false;
    document.getElementById('start-btn').textContent = 'Start Analysis';
}
