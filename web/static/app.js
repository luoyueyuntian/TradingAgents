/* TradingAgents Web - Frontend JavaScript */

const API = '';
const PANEL_VISIBILITY_IDS = [
    'config-panel',
    'history-panel',
    'artifacts-library-panel',
    'recently-viewed-panel',
    'ticker-home-panel',
    'watchlist-panel',
    'alert-panel',
    'portfolio-panel',
    'dashboard-panel',
    'analytics-panel',
    'screener-panel',
    'notifications-panel',
    'automations-panel',
    'preset-panel',
    'timeline-panel',
    'search-panel',
    'members-panel',
    'member-workspace-panel',
    'saved-views-panel',
    'public-shares-panel',
    'pinned-runs-panel',
    'annotation-panel',
    'review-panel',
    'comments-panel',
    'notes-panel',
    'briefing-panel',
    'compare-panel',
];
let providers = [];
let currentRunId = null;
let eventSource = null;
let currentSettings = null;
let reportSections = {};
let autoRefreshTimer = null;
let tickerHomeTimer = null;
let currentTickerHomeTicker = null;
let runHistory = [];
let currentComparison = null;
let followUpRunId = null;
let followUpMessages = [];
let initialRouteApplied = false;
let notesContext = { ticker: null, runId: null };
let editingNoteId = null;
let currentWorkspaceMembers = [];
let currentCommentsRunId = null;
let currentRunComments = [];
let currentMemberWorkspaceId = null;
let currentRunReview = null;
let currentPresets = [];
let currentSavedSearches = [];
let currentSavedViews = [];
let currentPublicShares = [];
let currentRunAnnotation = null;
let currentPublicRunShare = null;
let currentDashboardSectionOrder = [...DASHBOARD_SECTION_IDS];
let currentCommandPaletteResults = [];
let currentCommandPaletteIndex = 0;
let desktopNotificationsPrimed = false;
let deferredInstallPrompt = null;
const TENANT_STORAGE_KEY = 'tradingagents.tenantId';
const API_TOKEN_STORAGE_KEY = 'tradingagents.apiToken';
const CURRENT_MEMBER_STORAGE_KEY = 'tradingagents.currentMemberId';
const RECENTLY_VIEWED_LIMIT = 12;
const WORKSPACE_SEARCH_KIND_DEFINITIONS = [
    ['search-kind-run', 'run'],
    ['search-kind-note', 'note'],
    ['search-kind-watchlist', 'watchlist'],
    ['search-kind-portfolio', 'portfolio'],
    ['search-kind-preset', 'preset'],
    ['search-kind-search', 'search'],
    ['search-kind-view', 'view'],
    ['search-kind-member', 'member'],
    ['search-kind-share', 'share'],
    ['search-kind-alert', 'alert'],
    ['search-kind-comment', 'comment'],
    ['search-kind-review', 'review'],
];
const TIMELINE_KIND_DEFINITIONS = [
    ['timeline-kind-run', 'run'],
    ['timeline-kind-note', 'note'],
    ['timeline-kind-watchlist', 'watchlist'],
    ['timeline-kind-alert', 'alert'],
    ['timeline-kind-portfolio', 'portfolio'],
    ['timeline-kind-preset', 'preset'],
    ['timeline-kind-search', 'search'],
    ['timeline-kind-view', 'view'],
    ['timeline-kind-member', 'member'],
    ['timeline-kind-share', 'share'],
    ['timeline-kind-pin', 'pin'],
    ['timeline-kind-annotation', 'annotation'],
    ['timeline-kind-comment', 'comment'],
    ['timeline-kind-review', 'review'],
];
const DASHBOARD_SECTION_IDS = [
    'bullish_focus',
    'needs_attention',
    'active_alerts',
    'portfolio_focus',
    'pinned_actions',
    'pending_reviews',
    'automations',
    'saved_shortcuts',
    'operational_runs',
];
const DASHBOARD_SECTION_LABELS = {
    bullish_focus: 'Bullish Focus',
    needs_attention: 'Needs Attention',
    active_alerts: 'Active Alerts',
    portfolio_focus: 'Portfolio Focus',
    pinned_actions: 'Pinned Actions',
    pending_reviews: 'Pending Reviews',
    automations: 'Automations',
    saved_shortcuts: 'Saved Shortcuts',
    operational_runs: 'Operational Issues',
};

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

const TOOL_VENDOR_DEFINITIONS = [
    { key: 'get_stock_data', label: 'Stock Data', placeholder: 'default or yfinance,alpha_vantage' },
    { key: 'get_indicators', label: 'Technical Indicators', placeholder: 'default or yfinance,alpha_vantage' },
    { key: 'get_fundamentals', label: 'Fundamentals', placeholder: 'default or yfinance,alpha_vantage' },
    { key: 'get_balance_sheet', label: 'Balance Sheet', placeholder: 'default or yfinance,alpha_vantage' },
    { key: 'get_cashflow', label: 'Cashflow', placeholder: 'default or yfinance,alpha_vantage' },
    { key: 'get_income_statement', label: 'Income Statement', placeholder: 'default or yfinance,alpha_vantage' },
    { key: 'get_news', label: 'Ticker News', placeholder: 'default or yfinance,alpha_vantage,cn_news' },
    { key: 'get_global_news', label: 'Global News', placeholder: 'default or yfinance,alpha_vantage,cn_news' },
    { key: 'get_insider_transactions', label: 'Insider Transactions', placeholder: 'default or yfinance,alpha_vantage,cn_news' },
    { key: 'get_macro_indicators', label: 'Macro Indicators', placeholder: 'default or fred,cn_macro' },
    { key: 'get_prediction_markets', label: 'Prediction Markets', placeholder: 'default or polymarket,cn_market_signals' },
];

const REPORT_SECTION_LABELS = {
    market_report: 'Market',
    sentiment_report: 'Sentiment',
    news_report: 'News',
    fundamentals_report: 'Fundamentals',
    investment_plan: 'Research',
    trader_investment_plan: 'Trading',
    final_trade_decision: 'Decision',
};

document.addEventListener('DOMContentLoaded', () => {
    registerServiceWorker();
    initInstallPrompt();
    initDateField();
    initTenantField();
    initApiTokenField();
    initCurrentMemberField();
    updateDesktopNotificationControls();
    initCommandPalette();
    initKeyboardShortcuts();
    initSettings();
    initFormHandlers();
    initTabs();
    initDownloads();
    startAutoRefresh();
    void loadSystemStatus();
    void loadTenantSuggestions();
    void initProviders();
});

function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
        return;
    }
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js').catch((error) => {
            console.warn('Service worker registration failed:', error);
        });
    });
}

function updateInstallPromptVisibility() {
    const button = document.getElementById('install-app-btn');
    if (!button) return;
    const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    button.style.display = (!standalone && deferredInstallPrompt) ? '' : 'none';
}

function initInstallPrompt() {
    const button = document.getElementById('install-app-btn');
    if (!button) return;
    button.addEventListener('click', () => {
        void promptInstallApp();
    });
    updateInstallPromptVisibility();
    window.addEventListener('beforeinstallprompt', (event) => {
        event.preventDefault();
        deferredInstallPrompt = event;
        updateInstallPromptVisibility();
    });
    window.addEventListener('appinstalled', () => {
        deferredInstallPrompt = null;
        updateInstallPromptVisibility();
        appendLog('Installed TradingAgents app shell.');
    });
}

async function promptInstallApp() {
    if (!deferredInstallPrompt) {
        updateInstallPromptVisibility();
        return;
    }
    deferredInstallPrompt.prompt();
    try {
        await deferredInstallPrompt.userChoice;
    } catch {
        // Some browsers do not expose a settled userChoice promise reliably.
    }
    deferredInstallPrompt = null;
    updateInstallPromptVisibility();
}

function initCommandPalette() {
    const overlay = document.getElementById('command-palette-overlay');
    const input = document.getElementById('command-palette-input');
    const closeButton = document.getElementById('command-palette-close');
    const openButton = document.getElementById('command-palette-btn');
    const results = document.getElementById('command-palette-results');

    openButton.addEventListener('click', openCommandPalette);
    closeButton.addEventListener('click', closeCommandPalette);
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) {
            closeCommandPalette();
        }
    });
    input.addEventListener('input', () => {
        updateCommandPaletteResults();
    });
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            event.preventDefault();
            closeCommandPalette();
            return;
        }
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            moveCommandPaletteSelection(1);
            return;
        }
        if (event.key === 'ArrowUp') {
            event.preventDefault();
            moveCommandPaletteSelection(-1);
            return;
        }
        if (event.key === 'Enter') {
            event.preventDefault();
            const command = currentCommandPaletteResults[currentCommandPaletteIndex];
            if (command) {
                void executeCommandPaletteCommand(command);
            }
        }
    });
    results.addEventListener('mousemove', (event) => {
        const target = event.target.closest('[data-command-index]');
        if (!target) return;
        currentCommandPaletteIndex = Number(target.dataset.commandIndex) || 0;
        renderCommandPaletteResults(currentCommandPaletteResults);
    });
}

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (event) => {
        const activeTag = document.activeElement?.tagName || '';
        const typingInField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag) || document.activeElement?.isContentEditable;
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            if (document.getElementById('command-palette-overlay').style.display === 'none') {
                openCommandPalette();
            } else {
                closeCommandPalette();
            }
            return;
        }
        if (event.key === 'Escape' && document.getElementById('command-palette-overlay').style.display !== 'none') {
            event.preventDefault();
            closeCommandPalette();
            return;
        }
        if (!typingInField && event.key === '/') {
            event.preventDefault();
            openCommandPalette();
        }
    });
}

function openCommandPalette() {
    document.getElementById('command-palette-overlay').style.display = '';
    document.getElementById('command-palette-input').value = '';
    updateCommandPaletteResults();
    window.setTimeout(() => {
        document.getElementById('command-palette-input').focus();
    }, 0);
}

function closeCommandPalette() {
    document.getElementById('command-palette-overlay').style.display = 'none';
}

function moveCommandPaletteSelection(delta) {
    if (!currentCommandPaletteResults.length) return;
    currentCommandPaletteIndex = (currentCommandPaletteIndex + delta + currentCommandPaletteResults.length) % currentCommandPaletteResults.length;
    renderCommandPaletteResults(currentCommandPaletteResults);
}

function scrollToPanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showSettings() {
    void openSettingsModal();
}

function buildCommandPaletteCommands() {
    const currentTicker = (currentTickerHomeTicker || document.getElementById('ticker').value || '').trim().toUpperCase();
    const commands = [
        { id: 'dashboard', label: 'Open Dashboard', meta: 'Jump to workspace dashboard', keywords: 'dashboard home overview', action: async () => { await loadDashboard(); scrollToPanel('dashboard-panel'); } },
        { id: 'artifacts-library', label: 'Open Reports Library', meta: 'Browse downloadable reports across saved runs', keywords: 'reports library artifacts downloads', action: async () => { await loadArtifactLibrary(); scrollToPanel('artifacts-library-panel'); } },
        { id: 'recently-viewed', label: 'Open Recently Viewed', meta: 'Jump to your recent workspace context', keywords: 'recently viewed recent history context', action: async () => { loadRecentlyViewed(); scrollToPanel('recently-viewed-panel'); } },
        { id: 'briefing', label: 'Open Briefing', meta: 'Jump to daily briefing', keywords: 'briefing daily summary', action: async () => { await loadBriefing(); scrollToPanel('briefing-panel'); } },
        { id: 'notifications', label: 'Open Notifications', meta: 'Review unread alerts and mentions', keywords: 'notifications inbox alerts mentions', action: async () => { await loadNotifications(); scrollToPanel('notifications-panel'); } },
        { id: 'watchlist', label: 'Open Watchlist', meta: 'Jump to saved watchlist', keywords: 'watchlist tickers saved', action: async () => { await loadWatchlist(); scrollToPanel('watchlist-panel'); } },
        { id: 'portfolio', label: 'Open Portfolio', meta: 'Jump to saved portfolio positions', keywords: 'portfolio positions holdings', action: async () => { await loadPortfolio(); scrollToPanel('portfolio-panel'); } },
        { id: 'search', label: 'Open Workspace Search', meta: 'Jump to unified workspace search', keywords: 'search find notes runs', action: async () => { scrollToPanel('search-panel'); } },
        { id: 'automations', label: 'Open Automations', meta: 'Jump to scheduled automation rules', keywords: 'automations schedules jobs', action: async () => { await loadAutomations(); scrollToPanel('automations-panel'); } },
        { id: 'analytics', label: 'Open Analytics', meta: 'Jump to workspace analytics', keywords: 'analytics metrics trends', action: async () => { await loadAnalytics(); scrollToPanel('analytics-panel'); } },
        { id: 'reviews', label: 'Open Reviews', meta: 'Jump to run review history', keywords: 'reviews approvals pending', action: async () => { await loadRunReviewHistory(); scrollToPanel('review-panel'); } },
        { id: 'timeline', label: 'Open Timeline', meta: 'Jump to workspace timeline', keywords: 'timeline history events', action: async () => { await loadTimeline(); scrollToPanel('timeline-panel'); } },
        { id: 'members', label: 'Open Members', meta: 'Jump to workspace collaborators', keywords: 'members team collaborators', action: async () => { await loadWorkspaceMembers(); scrollToPanel('members-panel'); } },
        { id: 'public-shares', label: 'Open Shared Snapshots', meta: 'Manage public read-only run links', keywords: 'shared snapshots public share links', action: async () => { await loadPublicRunShares(); scrollToPanel('public-shares-panel'); } },
        { id: 'settings', label: 'Open Settings', meta: 'Configure providers, workspace, and data', keywords: 'settings config preferences', action: async () => { showSettings(); } },
        { id: 'refresh-runs', label: 'Refresh Runs', meta: 'Reload recent analysis history', keywords: 'refresh runs history reload', action: async () => { await loadRunHistory(); scrollToPanel('history-panel'); } },
        { id: 'start-analysis', label: 'Start Analysis', meta: 'Run the current analysis form', keywords: 'start analysis run execute', action: async () => { startAnalysis(); scrollToPanel('config-panel'); } },
    ];

    if (currentTicker) {
        commands.push({
            id: 'ticker-home',
            label: `Open Ticker Home: ${currentTicker}`,
            meta: 'Load saved research for the current ticker',
            keywords: `ticker home ${currentTicker.toLowerCase()}`,
            action: async () => {
                await loadTickerHome(currentTicker);
                scrollToPanel('ticker-home-panel');
            },
        });
    }

    if (getCurrentMember()) {
        commands.push({
            id: 'member-workspace',
            label: 'Open Member Workspace',
            meta: 'Jump to the current member inbox',
            keywords: 'member workspace inbox assigned mentions',
            action: async () => {
                currentMemberWorkspaceId = getCurrentMember().id;
                document.getElementById('member-workspace-filter').value = getCurrentMember().id;
                await loadMemberWorkspace();
                scrollToPanel('member-workspace-panel');
            },
        });
    }

    return commands;
}

function getFilteredCommandPaletteCommands(query) {
    const normalized = query.trim().toLowerCase();
    const commands = buildCommandPaletteCommands();
    if (!normalized) {
        return commands;
    }
    return commands.filter((command) => {
        return [
            command.label,
            command.meta,
            command.keywords,
        ].some((part) => String(part || '').toLowerCase().includes(normalized));
    });
}

function updateCommandPaletteResults() {
    const query = document.getElementById('command-palette-input').value;
    currentCommandPaletteResults = getFilteredCommandPaletteCommands(query);
    currentCommandPaletteIndex = 0;
    renderCommandPaletteResults(currentCommandPaletteResults);
}

function renderCommandPaletteResults(commands) {
    const container = document.getElementById('command-palette-results');
    container.innerHTML = '';
    if (!commands.length) {
        const empty = document.createElement('div');
        empty.className = 'hint';
        empty.textContent = 'No matching commands.';
        container.appendChild(empty);
        return;
    }
    commands.forEach((command, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `command-palette-item${index === currentCommandPaletteIndex ? ' active' : ''}`;
        button.dataset.commandIndex = String(index);
        button.innerHTML = `
            <span class="command-palette-label">${command.label}</span>
            <span class="command-palette-meta">${command.meta} · ${command.keywords}</span>
        `;
        button.addEventListener('click', () => {
            currentCommandPaletteIndex = index;
            void executeCommandPaletteCommand(command);
        });
        container.appendChild(button);
    });
}

async function executeCommandPaletteCommand(command) {
    closeCommandPalette();
    await command.action();
}

function initTenantField() {
    const input = document.getElementById('tenant-id');
    input.value = window.localStorage.getItem(TENANT_STORAGE_KEY) || '';
    input.addEventListener('change', async () => {
        window.localStorage.setItem(TENANT_STORAGE_KEY, input.value.trim());
        await handleRuntimeContextChange({ refreshTenants: true });
    });
}

function initApiTokenField() {
    const input = document.getElementById('api-token');
    input.value = window.localStorage.getItem(API_TOKEN_STORAGE_KEY) || '';
    input.addEventListener('change', async () => {
        window.localStorage.setItem(API_TOKEN_STORAGE_KEY, input.value.trim());
        await handleRuntimeContextChange();
    });
}

function initCurrentMemberField() {
    const select = document.getElementById('current-member');
    select.value = window.localStorage.getItem(CURRENT_MEMBER_STORAGE_KEY) || '';
    select.addEventListener('change', async () => {
        const value = select.value || '';
        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, value);
        applyCurrentMemberContext();
        await loadNotifications();
        await loadMemberWorkspace();
        if (value) {
            document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
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

function getCurrentMemberId() {
    const value = document.getElementById('current-member')?.value || '';
    return value || null;
}

function getCurrentMember() {
    const memberId = getCurrentMemberId();
    return currentWorkspaceMembers.find((member) => member.id === memberId) || null;
}

function recentlyViewedStorageKey() {
    return `tradingagents.recentlyViewed.${getTenantId() || 'default'}`;
}

function readRecentlyViewedItems() {
    try {
        const raw = window.localStorage.getItem(recentlyViewedStorageKey());
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item === 'object') : [];
    } catch {
        return [];
    }
}

function writeRecentlyViewedItems(items) {
    window.localStorage.setItem(recentlyViewedStorageKey(), JSON.stringify(items.slice(0, RECENTLY_VIEWED_LIMIT)));
}

function rememberRecentlyViewedItem(item) {
    if (!item || !item.kind || !item.id) return;
    const deduped = readRecentlyViewedItems().filter((existing) => !(existing.kind === item.kind && existing.id === item.id));
    const next = [{ ...item, viewed_at: new Date().toISOString() }, ...deduped];
    writeRecentlyViewedItems(next);
}

function desktopNotificationsEnabledStorageKey() {
    return `tradingagents.desktopNotifications.enabled.${getTenantId() || 'default'}`;
}

function desktopNotificationsSeenStorageKey() {
    return `tradingagents.desktopNotifications.seen.${getTenantId() || 'default'}`;
}

function notificationApiSupported() {
    return 'Notification' in window;
}

function desktopNotificationsEnabled() {
    return window.localStorage.getItem(desktopNotificationsEnabledStorageKey()) === '1';
}

function setDesktopNotificationsEnabled(enabled) {
    if (enabled) {
        window.localStorage.setItem(desktopNotificationsEnabledStorageKey(), '1');
    } else {
        window.localStorage.removeItem(desktopNotificationsEnabledStorageKey());
    }
}

function readSeenDesktopNotificationIds() {
    try {
        const raw = window.localStorage.getItem(desktopNotificationsSeenStorageKey());
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : [];
    } catch {
        return [];
    }
}

function writeSeenDesktopNotificationIds(ids) {
    window.localStorage.setItem(desktopNotificationsSeenStorageKey(), JSON.stringify(ids.slice(-200)));
}

function rememberSeenDesktopNotifications(ids) {
    if (!ids.length) return;
    const merged = [...new Set([...readSeenDesktopNotificationIds(), ...ids])];
    writeSeenDesktopNotificationIds(merged);
}

function updateDesktopNotificationControls() {
    const button = document.getElementById('notifications-browser-toggle');
    const status = document.getElementById('notifications-browser-status');
    if (!button || !status) return;

    if (!notificationApiSupported()) {
        button.disabled = true;
        button.textContent = 'Desktop Alerts Unavailable';
        status.textContent = 'Desktop alerts are unavailable in this browser.';
        return;
    }

    const permission = Notification.permission;
    const enabled = desktopNotificationsEnabled();
    button.disabled = permission === 'denied';
    button.textContent = enabled ? 'Disable Desktop Alerts' : 'Enable Desktop Alerts';

    if (permission === 'denied') {
        status.textContent = 'Desktop alerts are blocked in this browser. Update browser settings to re-enable them.';
        return;
    }
    if (enabled && permission === 'granted') {
        status.textContent = 'Desktop alerts are enabled for new unread notifications while this workspace is open.';
        return;
    }
    status.textContent = 'Desktop alerts are off. Enable them to get system notifications for new unread items.';
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

function setImportFileStatus(statusId, message, tone = '') {
    const statusEl = document.getElementById(statusId);
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.toggle('is-ready', tone === 'ready');
    statusEl.classList.toggle('is-error', tone === 'error');
}

async function loadImportFileIntoTextarea(config, file) {
    const textarea = document.getElementById(config.textareaId);
    if (!textarea || !file) return;

    const filename = String(file.name || 'selected file').trim() || 'selected file';
    const normalizedName = filename.toLowerCase();
    if (config.acceptedExtensions.length && !config.acceptedExtensions.some((ext) => normalizedName.endsWith(ext))) {
        setImportFileStatus(
            config.statusId,
            `Unsupported file type for ${config.label}. Use ${config.acceptedExtensions.join(', ')}.`,
            'error'
        );
        return;
    }

    try {
        const text = await file.text();
        textarea.value = text;
        const lineCount = text ? text.split(/\r?\n/).length : 0;
        setImportFileStatus(
            config.statusId,
            `Loaded ${filename} (${lineCount} line(s)). Review the text below, then click Import.`,
            'ready'
        );
        appendLog(`Loaded ${filename} into ${config.label}.`);
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Could not read file.';
        setImportFileStatus(
            config.statusId,
            `Failed to read ${filename}: ${message}`,
            'error'
        );
        alert(`Failed to read ${filename}: ${message}`);
    }
}

function bindImportFileSurface(config) {
    const dropzone = document.getElementById(config.dropzoneId);
    const fileInput = document.getElementById(config.fileInputId);
    if (!dropzone || !fileInput) return;

    const openPicker = () => {
        fileInput.click();
    };
    const clearActive = () => {
        dropzone.classList.remove('is-active');
    };

    setImportFileStatus(config.statusId, config.defaultStatus);

    dropzone.addEventListener('click', () => {
        openPicker();
    });
    dropzone.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openPicker();
        }
    });
    fileInput.addEventListener('change', () => {
        const [file] = Array.from(fileInput.files || []);
        if (!file) return;
        void loadImportFileIntoTextarea(config, file);
        fileInput.value = '';
    });
    ['dragenter', 'dragover'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add('is-active');
        });
    });
    ['dragleave', 'dragend'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            clearActive();
        });
    });
    dropzone.addEventListener('drop', (event) => {
        event.preventDefault();
        clearActive();
        const [file] = Array.from(event.dataTransfer?.files || []);
        if (!file) return;
        void loadImportFileIntoTextarea(config, file);
    });
}

async function handleRuntimeContextChange({ refreshTenants = false } = {}) {
    closeSSE();
    desktopNotificationsPrimed = false;
    currentRunId = null;
    reportSections = {};
    document.getElementById('progress-panel').style.display = 'none';
    document.getElementById('results-panel').style.display = 'none';
    resetRunAnnotationForm();
    resetRunReviewForm();
    resetRunComments();
    resetFollowUpChat('Open a saved run, then ask follow-up questions about that analysis.');
    await loadSettings();
    applySettingsToMainForm();
    updateDesktopNotificationControls();
    await loadSystemStatus();
    await loadRunHistory();
    loadRecentlyViewed();
    await loadWorkspaceMembers();
    if (refreshTenants) {
        await loadTenantSuggestions();
    }
}

async function refreshWorkspaceAfterImport() {
    await loadSettings();
    applySettingsToMainForm();
    syncPanelVisibilityControls();
    await loadRunHistory();
    await loadWorkspaceMembers();
    await loadRunReviewHistory();
    await loadSavedSearches();
    await loadSavedViews();
    await loadNotes();
    await loadMemberWorkspace();
}

async function loadTenantSuggestions() {
    const container = document.getElementById('tenant-suggestions');
    if (!container) return;

    try {
        const resp = await fetch(buildApiUrl('/api/system/tenants'));
        if (!resp.ok) throw new Error(resp.statusText);
        renderTenantSuggestions(await resp.json());
    } catch {
        container.innerHTML = '';
    }
}

function renderTenantSuggestions(tenants) {
    const container = document.getElementById('tenant-suggestions');
    container.innerHTML = '';
    tenants.forEach((tenant) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `tenant-chip${tenant.active ? ' active' : ''}`;
        button.textContent = tenant.label;
        button.addEventListener('click', async () => {
            const value = tenant.tenant_id || '';
            document.getElementById('tenant-id').value = value;
            window.localStorage.setItem(TENANT_STORAGE_KEY, value);
            await handleRuntimeContextChange({ refreshTenants: true });
        });
        container.appendChild(button);
    });
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
        populateRunHistoryProviderFilter();
        populateScreenerProviderFilter();
    } catch (e) {
        console.error('Failed to load providers:', e);
    }

    await loadSettings();
    applySettingsToMainForm();
    syncPanelVisibilityControls();
    await loadRunHistory();
    await loadArtifactLibrary();
    loadRecentlyViewed();
    await loadWatchlist();
    await loadNotifications();
    await loadAutomations();
    await loadAnalytics();
    await loadScreener();
    await loadWorkspaceMembers();
    await loadRunReviewHistory();
    await loadPresets();
    await loadSavedSearches();
    await loadSavedViews();
    await loadPublicRunShares();
    await loadSystemStatus();
    await loadAutomations();
    syncAutomationFields();
    await applyInitialRouteState();
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

function populateScreenerProviderFilter() {
    const sel = document.getElementById('screener-provider-filter');
    if (!sel) return;
    const currentValue = sel.value || 'all';
    sel.innerHTML = '';

    const allOpt = document.createElement('option');
    allOpt.value = 'all';
    allOpt.textContent = 'All';
    sel.appendChild(allOpt);

    providers.forEach((provider) => {
        const opt = document.createElement('option');
        opt.value = provider.provider;
        opt.textContent = provider.display_name;
        sel.appendChild(opt);
    });

    sel.value = Array.from(sel.options).some((opt) => opt.value === currentValue) ? currentValue : 'all';
}

function populateRunHistoryProviderFilter() {
    const sel = document.getElementById('history-provider-filter');
    if (!sel) return;
    const currentValue = sel.value || '';
    sel.innerHTML = '';

    const allOpt = document.createElement('option');
    allOpt.value = '';
    allOpt.textContent = 'All';
    sel.appendChild(allOpt);

    providers.forEach((provider) => {
        const opt = document.createElement('option');
        opt.value = provider.provider;
        opt.textContent = provider.display_name;
        sel.appendChild(opt);
    });

    sel.value = Array.from(sel.options).some((opt) => opt.value === currentValue) ? currentValue : '';
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

function parseOptionalFloat(inputId) {
    const raw = document.getElementById(inputId).value.trim();
    if (!raw) return null;
    const parsed = parseFloat(raw);
    return Number.isNaN(parsed) ? null : parsed;
}

function parseTextareaLines(inputId) {
    return document.getElementById(inputId).value
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean);
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
        if (!resp.ok) throw new Error(resp.statusText);
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
    document.getElementById('run-market-profile').value = analysis.market_profile || 'default';
    document.getElementById('run-risk-rounds').value = String(analysis.max_risk_discuss_rounds || 1);
    document.getElementById('run-max-recur').value = String(analysis.max_recur_limit || 100);
    document.getElementById('run-checkpoint-enabled').checked = Boolean(analysis.checkpoint_enabled);
    document.getElementById('run-benchmark-ticker').value = analysis.benchmark_ticker || '';
    document.getElementById('run-temperature').value = llm.temperature ?? '';
    document.getElementById('run-backend-url').value = llm.backend_url || '';
    document.getElementById('run-google-thinking').value = llm.google_thinking_level || '';
    document.getElementById('run-openai-effort').value = llm.openai_reasoning_effort || '';
    document.getElementById('run-anthropic-effort').value = llm.anthropic_effort || '';
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
    document.getElementById('s-default-home-view').addEventListener('change', syncDefaultHomeSettings);
    document.getElementById('s-web-api-token-toggle').addEventListener('click', () => {
        const inp = document.getElementById('s-web-api-token');
        inp.type = inp.type === 'password' ? 'text' : 'password';
    });
    document.getElementById('s-webhook-token-toggle').addEventListener('click', () => {
        const inp = document.getElementById('s-webhook-token');
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
    document.getElementById('runtime-refresh').addEventListener('click', () => {
        void loadRuntimeMaintenance();
    });
    document.getElementById('runtime-clear-checkpoints').addEventListener('click', () => {
        void clearRuntimeCheckpoints();
    });
    document.getElementById('runtime-clear-memory').addEventListener('click', () => {
        void clearRuntimeMemory();
    });
}

async function openSettingsModal() {
    await loadSettings();
    if (!currentSettings) return;
    renderApiKeys();
    populateSettingsForm();
    document.getElementById('settings-overlay').style.display = '';
    void loadRuntimeMaintenance();
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

function renderToolVendorFields(toolVendors = {}) {
    const grid = document.getElementById('tool-vendors-grid');
    if (!grid) return;
    grid.innerHTML = '';

    TOOL_VENDOR_DEFINITIONS.forEach(({ key, label, placeholder }) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'form-group';
        wrapper.innerHTML = `
            <label for="tool-vendor-${key}">${label}</label>
            <input type="text" id="tool-vendor-${key}" data-tool-vendor="${key}" placeholder="${placeholder}">
        `;
        grid.appendChild(wrapper);
        const input = wrapper.querySelector('input');
        input.value = toolVendors[key] || '';
    });
}

function collectToolVendorSettings() {
    const toolVendors = {};
    document.querySelectorAll('#tool-vendors-grid [data-tool-vendor]').forEach((input) => {
        const value = input.value.trim();
        if (value) {
            toolVendors[input.dataset.toolVendor] = value;
        }
    });
    return toolVendors;
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

function populateDefaultSavedViewOptions(selectedValue = null) {
    const select = document.getElementById('s-default-saved-view');
    if (!select) return;
    select.innerHTML = '';
    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = 'None';
    select.appendChild(emptyOpt);
    currentSavedViews.forEach((item) => {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item.name;
        select.appendChild(opt);
    });
    if ([...select.options].some((option) => option.value === (selectedValue || ''))) {
        select.value = selectedValue || '';
    } else {
        select.value = '';
    }
}

function syncDefaultHomeSettings() {
    const surface = document.getElementById('s-default-home-view').value;
    const savedViewSelect = document.getElementById('s-default-saved-view');
    savedViewSelect.disabled = surface !== 'saved-view';
}

function populateSettingsForm() {
    const llm = currentSettings.llm || {};
    const analysis = currentSettings.analysis || {};
    const workspace = currentSettings.workspace || {};
    const data = currentSettings.data || {};
    const security = currentSettings.security || {};
    const integrations = currentSettings.integrations || {};
    const webhook = integrations.webhook || {};
    const vendors = data.data_vendors || {};
    const toolVendors = data.tool_vendors || {};

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
    document.getElementById('s-benchmark-ticker').value = analysis.benchmark_ticker || '';
    document.getElementById('s-memory-log-max-entries').value = analysis.memory_log_max_entries ?? '';
    document.getElementById('s-default-home-view').value = workspace.default_home_view || 'auto';
    populateDefaultSavedViewOptions(workspace.default_saved_view_id || null);
    syncDefaultHomeSettings();

    document.getElementById('s-vendor-core').value = vendors.core_stock_apis || 'yfinance';
    document.getElementById('s-vendor-technical').value = vendors.technical_indicators || 'yfinance';
    document.getElementById('s-vendor-fundamental').value = vendors.fundamental_data || 'yfinance';
    document.getElementById('s-vendor-news').value = vendors.news_data || 'yfinance';
    document.getElementById('s-vendor-macro').value = vendors.macro_data || 'fred';
    document.getElementById('s-vendor-prediction').value = vendors.prediction_markets || 'polymarket';

    document.getElementById('s-news-limit').value = String(data.news_article_limit || 20);
    document.getElementById('s-global-news-limit').value = String(data.global_news_article_limit || 10);
    document.getElementById('s-global-news-lookback').value = String(data.global_news_lookback_days || 7);
    document.getElementById('s-global-news-queries').value = (data.global_news_queries || []).join('\n');
    document.getElementById('s-web-api-token').value = '';
    document.getElementById('s-web-api-token').placeholder = security.web_api_token === '***' ? 'Configured' : 'Not set';
    document.getElementById('s-webhook-enabled').checked = Boolean(webhook.enabled);
    document.getElementById('s-webhook-url').value = webhook.url || '';
    document.getElementById('s-webhook-token').value = '';
    document.getElementById('s-webhook-token').placeholder = webhook.bearer_token === '***' ? 'Configured' : 'Not set';
    const webhookKinds = new Set(webhook.event_kinds || ['run', 'alert', 'action']);
    document.getElementById('s-webhook-kind-run').checked = webhookKinds.has('run');
    document.getElementById('s-webhook-kind-alert').checked = webhookKinds.has('alert');
    document.getElementById('s-webhook-kind-action').checked = webhookKinds.has('action');
    document.getElementById('s-webhook-kind-comment').checked = webhookKinds.has('comment');
    document.getElementById('s-webhook-kind-review').checked = webhookKinds.has('review');
    const statusParts = [
        webhook.last_delivery_at ? `Last delivery: ${new Date(webhook.last_delivery_at).toLocaleString()}` : 'No deliveries yet.',
        webhook.last_error ? `Last error: ${webhook.last_error}` : null,
    ].filter(Boolean);
    document.getElementById('s-webhook-status').textContent = statusParts.join(' · ');
    renderToolVendorFields(toolVendors);
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
    const toolVendors = collectToolVendorSettings();
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
        integrations: {
            webhook: {
                enabled: document.getElementById('s-webhook-enabled').checked,
                url: document.getElementById('s-webhook-url').value.trim() || null,
                bearer_token: (() => {
                    const value = document.getElementById('s-webhook-token').value.trim();
                    const placeholder = document.getElementById('s-webhook-token').placeholder;
                    if (!value && placeholder === 'Configured') return '***';
                    return value || null;
                })(),
                event_kinds: [
                    document.getElementById('s-webhook-kind-run').checked ? 'run' : null,
                    document.getElementById('s-webhook-kind-alert').checked ? 'alert' : null,
                    document.getElementById('s-webhook-kind-action').checked ? 'action' : null,
                    document.getElementById('s-webhook-kind-comment').checked ? 'comment' : null,
                    document.getElementById('s-webhook-kind-review').checked ? 'review' : null,
                ].filter(Boolean),
            },
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
            benchmark_ticker: document.getElementById('s-benchmark-ticker').value.trim() || null,
            memory_log_max_entries: (() => {
                const raw = document.getElementById('s-memory-log-max-entries').value.trim();
                if (!raw) return null;
                const parsed = parseInt(raw, 10);
                return Number.isNaN(parsed) ? null : parsed;
            })(),
        },
        workspace: {
            default_home_view: document.getElementById('s-default-home-view').value,
            default_saved_view_id: document.getElementById('s-default-home-view').value === 'saved-view'
                ? (document.getElementById('s-default-saved-view').value || null)
                : null,
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
            tool_vendors: toolVendors,
            news_article_limit: parseOptionalInt('s-news-limit', 20),
            global_news_article_limit: parseOptionalInt('s-global-news-limit', 10),
            global_news_lookback_days: parseOptionalInt('s-global-news-lookback', 7),
            global_news_queries: parseTextareaLines('s-global-news-queries'),
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

async function updateWorkspaceSettingsPatch(workspacePatch) {
    const resp = await fetch(buildApiUrl('/api/settings'), {
        method: 'PUT',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ workspace: workspacePatch }),
    });
    if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || resp.statusText);
    }
    currentSettings = await resp.json();
    return currentSettings;
}

async function loadRuntimeMaintenance() {
    const checkpointsEl = document.getElementById('runtime-checkpoints-list');
    const memoryEl = document.getElementById('runtime-memory-list');
    if (!checkpointsEl || !memoryEl) return;

    setRuntimeEmpty(checkpointsEl, 'Loading checkpoints...');
    setRuntimeEmpty(memoryEl, 'Loading decision memory...');

    try {
        const [checkpointsResp, memoryResp] = await Promise.all([
            fetch(buildApiUrl('/api/system/checkpoints')),
            fetch(buildApiUrl('/api/system/memory')),
        ]);
        if (!checkpointsResp.ok) throw new Error(checkpointsResp.statusText);
        if (!memoryResp.ok) throw new Error(memoryResp.statusText);

        renderRuntimeCheckpoints(await checkpointsResp.json());
        renderRuntimeMemoryEntries(await memoryResp.json());
    } catch (e) {
        setRuntimeEmpty(checkpointsEl, `Failed to load checkpoints: ${e.message}`);
        setRuntimeEmpty(memoryEl, `Failed to load memory: ${e.message}`);
    }
}

function setRuntimeEmpty(container, message) {
    container.innerHTML = '';
    const emptyEl = document.createElement('div');
    emptyEl.className = 'runtime-empty';
    emptyEl.textContent = message;
    container.appendChild(emptyEl);
}

function renderRuntimeCheckpoints(items) {
    const container = document.getElementById('runtime-checkpoints-list');
    container.innerHTML = '';

    if (!items.length) {
        setRuntimeEmpty(container, 'No checkpoints found for this tenant.');
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'runtime-item';
        const scope = item.run_id ? `Run ${item.run_id}` : 'Shared tenant state';

        const titleEl = document.createElement('div');
        titleEl.className = 'runtime-item-title';
        titleEl.textContent = item.ticker;

        const metaEl = document.createElement('div');
        metaEl.className = 'runtime-item-meta';
        metaEl.textContent = `${scope} · ${item.size_bytes} bytes`;

        const pathEl = document.createElement('div');
        pathEl.className = 'runtime-item-path';
        pathEl.title = item.path;
        pathEl.textContent = item.path;

        row.appendChild(titleEl);
        row.appendChild(metaEl);
        row.appendChild(pathEl);
        container.appendChild(row);
    });
}

function renderRuntimeMemoryEntries(items) {
    const container = document.getElementById('runtime-memory-list');
    container.innerHTML = '';

    if (!items.length) {
        setRuntimeEmpty(container, 'No decision-memory entries found for this tenant.');
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'runtime-item';
        const status = item.pending ? 'pending' : 'resolved';
        const reflection = item.reflection || 'No reflection yet.';
        const scope = item.run_id ? `Run ${item.run_id}` : 'Shared tenant memory';

        const titleEl = document.createElement('div');
        titleEl.className = 'runtime-item-title';
        titleEl.textContent = `${item.ticker} · ${item.date}`;

        const metaEl = document.createElement('div');
        metaEl.className = 'runtime-item-meta';
        metaEl.textContent = `${scope} · ${item.rating} · ${status}`;

        const decisionEl = document.createElement('div');
        decisionEl.className = 'runtime-item-body';
        decisionEl.textContent = item.decision;

        const reflectionEl = document.createElement('div');
        reflectionEl.className = 'runtime-item-body runtime-reflection';
        reflectionEl.textContent = reflection;

        row.appendChild(titleEl);
        row.appendChild(metaEl);
        row.appendChild(decisionEl);
        row.appendChild(reflectionEl);
        container.appendChild(row);
    });
}

async function clearRuntimeCheckpoints() {
    const confirmed = window.confirm('Clear all checkpoint files for the current tenant?');
    if (!confirmed) return;

    try {
        const resp = await fetch(buildApiUrl('/api/system/checkpoints'), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        appendLog(`Cleared ${payload.deleted} checkpoint file(s).`);
        await loadRuntimeMaintenance();
    } catch (e) {
        alert(`Failed to clear checkpoints: ${e.message}`);
    }
}

async function clearRuntimeMemory() {
    const confirmed = window.confirm('Clear all decision-memory logs for the current tenant?');
    if (!confirmed) return;

    try {
        const resp = await fetch(buildApiUrl('/api/system/memory'), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        appendLog(`Cleared ${payload.deleted} decision-memory log file(s).`);
        await loadRuntimeMaintenance();
    } catch (e) {
        alert(`Failed to clear decision memory: ${e.message}`);
    }
}

let pendingAnalysisAction = null;

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
    pendingAnalysisAction = null;
}

async function saveApiKeyAndRun() {
    const providerKey = document.getElementById('apikey-modal-overlay').dataset.providerKey;
    const apiKey = document.getElementById('apikey-input').value.trim();
    if (!apiKey) return;

    const resumeAction = pendingAnalysisAction;
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
        pendingAnalysisAction = null;
        if (resumeAction?.kind === 'single' && resumeAction.body) {
            executeAnalysis(resumeAction.body);
        } else if (resumeAction?.kind === 'batch' && resumeAction.body) {
            executeBatchAnalysis(resumeAction.body);
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
    document.getElementById('refresh-artifacts-library').addEventListener('click', () => {
        void loadArtifactLibrary();
    });
    document.getElementById('artifacts-library-query').addEventListener('input', () => {
        void loadArtifactLibrary();
    });
    document.getElementById('refresh-recently-viewed').addEventListener('click', () => {
        loadRecentlyViewed();
    });
    document.getElementById('clear-recently-viewed').addEventListener('click', () => {
        clearRecentlyViewed();
    });
    document.getElementById('history-query').addEventListener('input', () => {
        void loadRunHistory();
    });
    document.getElementById('history-archived-filter').addEventListener('change', () => {
        void loadRunHistory();
    });
    document.getElementById('history-status-filter').addEventListener('change', () => {
        void loadRunHistory();
    });
    document.getElementById('history-provider-filter').addEventListener('change', () => {
        void loadRunHistory();
    });
    document.getElementById('history-asset-filter').addEventListener('change', () => {
        void loadRunHistory();
    });
    document.getElementById('history-select-all').addEventListener('change', () => {
        toggleVisibleHistorySelection(document.getElementById('history-select-all').checked);
    });
    document.getElementById('history-bulk-archive').addEventListener('click', () => {
        void bulkUpdateRuns('archive');
    });
    document.getElementById('history-bulk-restore').addEventListener('click', () => {
        void bulkUpdateRuns('restore');
    });
    document.getElementById('history-bulk-retry').addEventListener('click', () => {
        void bulkUpdateRuns('retry');
    });
    document.getElementById('history-bulk-delete').addEventListener('click', () => {
        void bulkUpdateRuns('delete');
    });
    document.getElementById('refresh-ticker-home').addEventListener('click', () => {
        void loadTickerHome();
    });
    document.getElementById('refresh-watchlist').addEventListener('click', () => {
        void loadWatchlist();
    });
    document.getElementById('add-watchlist').addEventListener('click', () => {
        void addCurrentTickerToWatchlist();
    });
    document.getElementById('import-watchlist').addEventListener('click', () => {
        void importWatchlist();
    });
    bindImportFileSurface({
        dropzoneId: 'watchlist-import-dropzone',
        fileInputId: 'watchlist-import-file',
        statusId: 'watchlist-import-file-status',
        textareaId: 'watchlist-import-text',
        acceptedExtensions: ['.csv', '.tsv', '.txt'],
        defaultStatus: 'No file selected yet. Supported formats: CSV, TSV, TXT.',
        label: 'watchlist import box',
    });
    document.getElementById('refresh-alerts').addEventListener('click', () => {
        void loadAlerts();
    });
    document.getElementById('add-alert-rule').addEventListener('click', () => {
        void addCurrentAlertRule();
    });
    document.getElementById('refresh-portfolio').addEventListener('click', () => {
        void loadPortfolio();
    });
    document.getElementById('add-portfolio-position').addEventListener('click', () => {
        void addCurrentPortfolioPosition();
    });
    document.getElementById('import-portfolio').addEventListener('click', () => {
        void importPortfolio();
    });
    bindImportFileSurface({
        dropzoneId: 'portfolio-import-dropzone',
        fileInputId: 'portfolio-import-file',
        statusId: 'portfolio-import-file-status',
        textareaId: 'portfolio-import-text',
        acceptedExtensions: ['.csv', '.tsv', '.txt'],
        defaultStatus: 'No file selected yet. Supported formats: CSV, TSV, TXT.',
        label: 'portfolio import box',
    });
    document.getElementById('refresh-dashboard').addEventListener('click', () => {
        void loadDashboard();
    });
    document.getElementById('import-workspace-json').addEventListener('click', () => {
        void importWorkspaceSnapshot();
    });
    bindImportFileSurface({
        dropzoneId: 'workspace-import-dropzone',
        fileInputId: 'workspace-import-file',
        statusId: 'workspace-import-file-status',
        textareaId: 'workspace-import-text',
        acceptedExtensions: ['.json'],
        defaultStatus: 'No file selected yet. Supported format: JSON.',
        label: 'workspace import box',
    });
    DASHBOARD_SECTION_IDS.forEach((sectionId) => {
        const checkbox = document.getElementById(`dashboard-section-${sectionId}`);
        if (!checkbox) return;
        checkbox.addEventListener('change', () => {
            void saveDashboardPreferences();
        });
        const upButton = document.getElementById(`dashboard-move-up-${sectionId}`);
        const downButton = document.getElementById(`dashboard-move-down-${sectionId}`);
        if (upButton) {
            upButton.addEventListener('click', () => {
                void moveDashboardSection(sectionId, -1);
            });
        }
        if (downButton) {
            downButton.addEventListener('click', () => {
                void moveDashboardSection(sectionId, 1);
            });
        }
    });
    document.getElementById('reset-dashboard-layout').addEventListener('click', () => {
        void resetDashboardPreferences();
    });
    document.getElementById('refresh-analytics').addEventListener('click', () => {
        void loadAnalytics();
    });
    document.getElementById('refresh-screener').addEventListener('click', () => {
        void loadScreener();
    });
    document.getElementById('screener-scope').addEventListener('change', () => {
        void loadScreener();
    });
    document.getElementById('screener-query').addEventListener('input', () => {
        void loadScreener();
    });
    document.getElementById('screener-signal-filter').addEventListener('change', () => {
        void loadScreener();
    });
    document.getElementById('screener-status-filter').addEventListener('change', () => {
        void loadScreener();
    });
    document.getElementById('screener-asset-filter').addEventListener('change', () => {
        void loadScreener();
    });
    document.getElementById('screener-provider-filter').addEventListener('change', () => {
        void loadScreener();
    });
    document.getElementById('refresh-notifications').addEventListener('click', () => {
        void loadNotifications();
    });
    document.getElementById('mark-all-notifications-read').addEventListener('click', () => {
        void markAllNotificationsRead();
    });
    document.getElementById('notifications-unread-only').addEventListener('change', () => {
        void loadNotifications();
    });
    document.getElementById('notifications-member-filter').addEventListener('change', () => {
        void loadNotifications();
    });
    document.getElementById('notifications-kind-filter').addEventListener('change', () => {
        void loadNotifications();
    });
    document.getElementById('notifications-severity-filter').addEventListener('change', () => {
        void loadNotifications();
    });
    document.getElementById('notifications-browser-toggle').addEventListener('click', () => {
        void toggleDesktopNotifications();
    });
    document.getElementById('notifications-btn').addEventListener('click', () => {
        document.getElementById('notifications-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        void loadNotifications();
    });
    document.getElementById('member-workspace-btn').addEventListener('click', () => {
        const member = getCurrentMember();
        if (!member) {
            alert('Select a current member first.');
            return;
        }
        document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        currentMemberWorkspaceId = member.id;
        document.getElementById('member-workspace-filter').value = member.id;
        void loadMemberWorkspace();
    });
    document.getElementById('refresh-automations').addEventListener('click', () => {
        void loadAutomations();
    });
    document.getElementById('save-automation').addEventListener('click', () => {
        void saveAutomation();
    });
    document.getElementById('automation-cadence').addEventListener('change', () => {
        syncAutomationFields();
    });
    document.getElementById('automation-source').addEventListener('change', () => {
        syncAutomationFields();
    });
    document.getElementById('refresh-presets').addEventListener('click', () => {
        void loadPresets();
    });
    document.getElementById('save-preset').addEventListener('click', () => {
        void saveCurrentPreset();
    });
    document.getElementById('refresh-timeline').addEventListener('click', () => {
        void loadTimeline();
    });
    document.getElementById('refresh-calendar').addEventListener('click', () => {
        void loadCalendar();
    });
    document.getElementById('timeline-kind-run').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-note').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-watchlist').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-alert').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-portfolio').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-preset').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-search').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-view').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-member').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-share').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-pin').addEventListener('change', () => {
        void loadTimeline();
    });
    document.getElementById('timeline-kind-annotation').addEventListener('change', () => {
        void loadTimeline();
    });
    const timelineComment = document.getElementById('timeline-kind-comment');
    if (timelineComment) {
        timelineComment.addEventListener('change', () => {
            void loadTimeline();
        });
    }
    const timelineReview = document.getElementById('timeline-kind-review');
    if (timelineReview) {
        timelineReview.addEventListener('change', () => {
            void loadTimeline();
        });
    }
    document.getElementById('save-note').addEventListener('click', () => {
        void saveNote();
    });
    document.getElementById('notes-mode').addEventListener('change', () => {
        void loadNotes();
    });
    document.getElementById('save-comment').addEventListener('click', () => {
        void saveRunComment();
    });
    document.getElementById('save-review').addEventListener('click', () => {
        void saveRunReview();
    });
    document.getElementById('clear-review').addEventListener('click', () => {
        void clearRunReview();
    });
    document.getElementById('review-history-reviewer-filter').addEventListener('change', () => {
        void loadRunReviewHistory();
    });
    document.getElementById('review-history-status-filter').addEventListener('change', () => {
        void loadRunReviewHistory();
    });
    document.getElementById('review-history-query').addEventListener('input', () => {
        void loadRunReviewHistory();
    });
    document.getElementById('comments-hide-resolved').addEventListener('change', () => {
        renderRunComments(currentRunComments);
    });
    document.getElementById('run-search').addEventListener('click', () => {
        void runWorkspaceSearch();
    });
    document.getElementById('save-search').addEventListener('click', () => {
        void saveCurrentSearch();
    });
    document.getElementById('saved-search-filter-group').addEventListener('input', () => {
        renderSavedSearches(currentSavedSearches);
    });
    document.getElementById('saved-search-filter-status').addEventListener('change', () => {
        renderSavedSearches(currentSavedSearches);
    });
    document.getElementById('saved-search-filter-pinned').addEventListener('change', () => {
        renderSavedSearches(currentSavedSearches);
    });
    document.getElementById('saved-search-select-all').addEventListener('change', () => {
        toggleVisibleSavedSearchSelection(document.getElementById('saved-search-select-all').checked);
    });
    document.getElementById('saved-search-bulk-archive').addEventListener('click', () => {
        void bulkUpdateSavedSearches('archive');
    });
    document.getElementById('saved-search-bulk-restore').addEventListener('click', () => {
        void bulkUpdateSavedSearches('restore');
    });
    document.getElementById('saved-search-bulk-delete').addEventListener('click', () => {
        void bulkUpdateSavedSearches('delete');
    });
    document.getElementById('refresh-members').addEventListener('click', () => {
        void loadWorkspaceMembers();
    });
    document.getElementById('save-member').addEventListener('click', () => {
        void saveWorkspaceMember();
    });
    document.getElementById('refresh-member-workspace').addEventListener('click', () => {
        void loadMemberWorkspace();
    });
    document.getElementById('member-workspace-filter').addEventListener('change', () => {
        const value = document.getElementById('member-workspace-filter').value || '';
        currentMemberWorkspaceId = value || null;
        document.getElementById('current-member').value = value;
        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, value);
        applyCurrentMemberContext();
        void loadMemberWorkspace();
    });
    document.getElementById('refresh-views').addEventListener('click', () => {
        void loadSavedViews();
    });
    document.getElementById('refresh-public-shares').addEventListener('click', () => {
        void loadPublicRunShares();
    });
    document.getElementById('public-shares-query').addEventListener('input', () => {
        void loadPublicRunShares();
    });
    document.getElementById('public-shares-availability-filter').addEventListener('change', () => {
        void loadPublicRunShares();
    });
    document.getElementById('save-view').addEventListener('click', () => {
        void saveCurrentView();
    });
    document.getElementById('saved-view-filter-group').addEventListener('input', () => {
        renderSavedViews(currentSavedViews);
    });
    document.getElementById('saved-view-filter-status').addEventListener('change', () => {
        renderSavedViews(currentSavedViews);
    });
    document.getElementById('saved-view-filter-pinned').addEventListener('change', () => {
        renderSavedViews(currentSavedViews);
    });
    document.getElementById('saved-view-display-mode').addEventListener('change', () => {
        renderSavedViews(currentSavedViews);
    });
    document.getElementById('saved-view-select-all').addEventListener('change', () => {
        toggleVisibleSavedViewSelection(document.getElementById('saved-view-select-all').checked);
    });
    document.getElementById('saved-view-bulk-archive').addEventListener('click', () => {
        void bulkUpdateSavedViews('archive');
    });
    document.getElementById('saved-view-bulk-restore').addEventListener('click', () => {
        void bulkUpdateSavedViews('restore');
    });
    document.getElementById('saved-view-bulk-delete').addEventListener('click', () => {
        void bulkUpdateSavedViews('delete');
    });
    PANEL_VISIBILITY_IDS.forEach((panelId) => {
        const checkbox = document.getElementById(`panel-toggle-${panelId}`);
        if (!checkbox) return;
        checkbox.addEventListener('change', () => {
            applyPanelVisibility(collectVisiblePanels());
        });
    });
    document.getElementById('refresh-pinned-runs').addEventListener('click', () => {
        void loadPinnedRuns();
    });
    document.getElementById('refresh-action-board').addEventListener('click', () => {
        void loadActionBoard();
    });
    document.getElementById('pinned-action-status-filter').addEventListener('change', () => {
        void loadPinnedRuns();
    });
    document.getElementById('pinned-assignee-filter').addEventListener('change', () => {
        void loadPinnedRuns();
    });
    document.getElementById('pin-current-run').addEventListener('click', () => {
        void pinCurrentRun();
    });
    document.getElementById('pinned-category-filter').addEventListener('change', () => {
        void loadPinnedRuns();
    });
    document.getElementById('save-annotation').addEventListener('click', () => {
        void saveRunAnnotation();
    });
    document.getElementById('clear-annotation').addEventListener('click', () => {
        void clearRunAnnotation();
    });
    document.getElementById('notes-search').addEventListener('input', () => {
        void loadNotes();
    });
    document.getElementById('refresh-briefing').addEventListener('click', () => {
        void loadBriefing();
    });
    document.getElementById('compare-run-button').addEventListener('click', () => {
        void compareSelectedRuns();
    });
    document.getElementById('compare-section').addEventListener('change', () => {
        renderComparisonSection();
    });
    document.getElementById('follow-up-ask').addEventListener('click', () => {
        void askFollowUpQuestion();
    });
    document.getElementById('cancel-run').addEventListener('click', () => {
        void requestRunCancellation();
    });
    document.getElementById('run-batch-tickers').addEventListener('click', () => {
        void runBatchAnalysis('manual');
    });
    document.getElementById('run-watchlist-batch').addEventListener('click', () => {
        void runBatchAnalysis('watchlist');
    });

    document.getElementById('ticker').addEventListener('input', (e) => {
        const hint = document.getElementById('asset-type-hint');
        const type = detectAssetType(e.target.value);
        hint.textContent = type !== 'stock' ? `Detected: ${type}` : '';
        scheduleTickerHomeRefresh(e.target.value);
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
    document.getElementById('export-artifacts-library-csv').addEventListener('click', () => {
        void downloadArtifactLibraryCsv();
    });
    document.getElementById('export-analytics-csv').addEventListener('click', () => {
        void downloadAnalyticsCsv();
    });
    document.getElementById('export-history-csv').addEventListener('click', () => {
        void downloadRunHistoryCsv();
    });
    document.getElementById('export-workspace-json').addEventListener('click', () => {
        void downloadWorkspaceExport('json');
    });
    document.getElementById('export-workspace-md').addEventListener('click', () => {
        void downloadWorkspaceExport('markdown');
    });
    document.getElementById('export-screener-csv').addEventListener('click', () => {
        void downloadScreenerCsv();
    });
    document.getElementById('export-timeline-csv').addEventListener('click', () => {
        void downloadTimelineCsv();
    });
    document.getElementById('export-search-csv').addEventListener('click', () => {
        void downloadWorkspaceSearchCsv();
    });
    document.getElementById('export-notifications-csv').addEventListener('click', () => {
        void downloadNotificationsCsv();
    });
    document.getElementById('export-review-history-csv').addEventListener('click', () => {
        void downloadReviewHistoryCsv();
    });
    document.getElementById('export-public-shares-csv').addEventListener('click', () => {
        void downloadPublicRunSharesCsv();
    });
    document.getElementById('share-run-link').addEventListener('click', () => {
        void copyShareLink(() => currentRunId ? `/api/share/runs/${encodeURIComponent(currentRunId)}` : null, 'Open a saved run before copying its link.');
    });
    document.getElementById('share-ticker-link').addEventListener('click', () => {
        const ticker = (currentTickerHomeTicker || document.getElementById('ticker').value || '').trim().toUpperCase();
        void copyShareLink(() => ticker ? `/api/share/tickers/${encodeURIComponent(ticker)}` : null, 'Enter or open a ticker before copying its link.');
    });
    document.getElementById('share-public-run-link').addEventListener('click', () => {
        void copyPublicRunShareLink();
    });
    document.getElementById('revoke-public-run-link').addEventListener('click', () => {
        void revokePublicRunShare();
    });
    document.getElementById('share-compare-link').addEventListener('click', () => {
        const left = document.getElementById('compare-left-run').value;
        const right = document.getElementById('compare-right-run').value;
        void copyShareLink(
            () => (left && right) ? `/api/share/compare?left_run_id=${encodeURIComponent(left)}&right_run_id=${encodeURIComponent(right)}` : null,
            'Select two runs before copying a compare link.',
        );
    });
    document.getElementById('share-briefing-link').addEventListener('click', () => {
        void copyShareLink(() => '/api/share/briefing/daily');
    });
}

async function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return;
    }

    const input = document.createElement('textarea');
    input.value = text;
    input.setAttribute('readonly', '');
    input.style.position = 'absolute';
    input.style.left = '-9999px';
    document.body.appendChild(input);
    input.select();
    document.execCommand('copy');
    document.body.removeChild(input);
}

async function copyShareLink(pathFactory, emptyMessage = 'Nothing to share yet.') {
    const path = typeof pathFactory === 'function' ? pathFactory() : pathFactory;
    if (!path) {
        alert(emptyMessage);
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        const absoluteUrl = new URL(payload.url, window.location.origin).toString();
        await copyToClipboard(absoluteUrl);
        appendLog(`Copied ${payload.label}.`);
    } catch (e) {
        alert(`Failed to copy share link: ${e.message}`);
    }
}

function syncPublicShareActions(run) {
    currentPublicRunShare = run.public_share || null;
    const shareButton = document.getElementById('share-public-run-link');
    const revokeButton = document.getElementById('revoke-public-run-link');
    shareButton.disabled = !run.run_id;
    revokeButton.style.display = currentPublicRunShare ? '' : 'none';
}

async function copyPublicRunShareLink() {
    if (!currentRunId) {
        alert('Open a saved run before creating a public snapshot.');
        return;
    }
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(currentRunId)}/public-share`), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        currentPublicRunShare = payload;
        syncPublicShareActions({ run_id: currentRunId, public_share: payload });
        await copyToClipboard(new URL(payload.url, window.location.origin).toString());
        appendLog('Copied public run snapshot link.');
        await loadPublicRunShares();
    } catch (e) {
        alert(`Failed to create public snapshot: ${e.message}`);
    }
}

async function revokePublicRunShare() {
    if (!currentRunId) {
        return;
    }
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(currentRunId)}/public-share`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        currentPublicRunShare = null;
        syncPublicShareActions({ run_id: currentRunId, public_share: null });
        appendLog('Revoked public run snapshot.');
        await loadPublicRunShares();
    } catch (e) {
        alert(`Failed to revoke public snapshot: ${e.message}`);
    }
}

async function revokePublicRunShareByRunId(runId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(runId)}/public-share`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        if (currentRunId === runId) {
            currentPublicRunShare = null;
            syncPublicShareActions({ run_id: currentRunId, public_share: null });
        }
        appendLog('Revoked public run snapshot.');
        await loadPublicRunShares();
    } catch (e) {
        alert(`Failed to revoke public snapshot: ${e.message}`);
    }
}

async function updatePublicRunShareExpiry(runId, expiresInDays) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(runId)}/public-share`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ expires_in_days: expiresInDays }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(expiresInDays == null ? 'Cleared public snapshot expiry.' : 'Updated public snapshot expiry.');
        await loadPublicRunShares();
        if (currentRunId === runId) {
            await openRunDetails(runId);
        }
    } catch (e) {
        alert(`Failed to update public snapshot expiry: ${e.message}`);
    }
}

async function updatePublicRunSharePresentation(runId, body) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(runId)}/public-share`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Updated public snapshot details.');
        await loadPublicRunShares();
        if (currentRunId === runId) {
            await openRunDetails(runId);
        }
    } catch (e) {
        alert(`Failed to update public snapshot details: ${e.message}`);
    }
}

async function downloadWorkspaceExport(format) {
    const extension = format === 'json' ? 'json' : 'md';
    await downloadFileFromApi(
        `/api/workspace/export?format=${encodeURIComponent(format)}`,
        `tradingagents-workspace.${extension}`,
        `Downloaded workspace export`,
        `Failed to export workspace`,
    );
}

async function downloadRunHistoryCsv() {
    const params = new URLSearchParams();
    const query = document.getElementById('history-query').value.trim();
    const archived = document.getElementById('history-archived-filter').value;
    const status = document.getElementById('history-status-filter').value;
    const provider = document.getElementById('history-provider-filter').value;
    const assetType = document.getElementById('history-asset-filter').value;
    if (query) params.set('q', query);
    if (archived && archived !== 'active') params.set('archived', archived);
    if (status) params.set('status', status);
    if (provider) params.set('provider', provider);
    if (assetType) params.set('asset_type', assetType);
    const path = params.toString() ? `/api/runs/export?${params.toString()}` : '/api/runs/export';
    await downloadFileFromApi(path, 'tradingagents-run-history.csv', 'Downloaded run history CSV', 'Failed to export run history CSV');
}

async function downloadAnalyticsCsv() {
    await downloadFileFromApi('/api/analytics/export', 'tradingagents-workspace-analytics.csv', 'Downloaded analytics CSV', 'Failed to export analytics CSV');
}

async function downloadArtifactLibraryCsv() {
    const params = new URLSearchParams();
    const query = document.getElementById('artifacts-library-query').value.trim();
    if (query) params.set('q', query);
    const path = params.toString() ? `/api/artifacts/library/export?${params.toString()}` : '/api/artifacts/library/export';
    await downloadFileFromApi(path, 'tradingagents-artifact-library.csv', 'Downloaded reports library CSV', 'Failed to export reports library CSV');
}

async function downloadFileFromApi(path, fallbackFilename, successMessage, failureMessage) {
    try {
        const resp = await fetch(buildApiUrl(path), { headers: apiHeaders() });
        if (!resp.ok) {
            let err = null;
            try {
                err = await resp.json();
            } catch {
                err = null;
            }
            throw new Error(err?.detail || resp.statusText);
        }

        const blob = await resp.blob();
        const disposition = resp.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename=\"([^\"]+)\"/);
        const filename = match?.[1] || fallbackFilename;
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.setTimeout(() => window.URL.revokeObjectURL(url), 0);
        appendLog(`${successMessage}: ${filename}`);
    } catch (e) {
        alert(`${failureMessage}: ${e.message}`);
    }
}

async function downloadScreenerCsv() {
    const params = new URLSearchParams();
    const scope = document.getElementById('screener-scope').value;
    const query = document.getElementById('screener-query').value.trim();
    const signal = document.getElementById('screener-signal-filter').value;
    const status = document.getElementById('screener-status-filter').value;
    const asset = document.getElementById('screener-asset-filter').value;
    const provider = document.getElementById('screener-provider-filter').value;
    if (scope && scope !== 'all') params.set('scope', scope);
    if (query) params.set('q', query);
    if (signal && signal !== 'all') params.set('signal', signal);
    if (status && status !== 'all') params.set('status', status);
    if (asset && asset !== 'all') params.set('asset_type', asset);
    if (provider && provider !== 'all') params.set('provider', provider);
    const path = params.toString() ? `/api/screener/export?${params.toString()}` : '/api/screener/export';
    await downloadFileFromApi(path, 'tradingagents-workspace-screener.csv', 'Downloaded screener CSV', 'Failed to export screener CSV');
}

async function downloadTimelineCsv() {
    const kinds = collectTimelineKinds();
    const params = new URLSearchParams();
    if (kinds.length > 0 && kinds.length < TIMELINE_KIND_DEFINITIONS.length) {
        params.set('kinds', kinds.join(','));
    }
    const path = params.toString() ? `/api/timeline/export?${params.toString()}` : '/api/timeline/export';
    await downloadFileFromApi(path, 'tradingagents-workspace-timeline.csv', 'Downloaded timeline CSV', 'Failed to export timeline CSV');
}

async function downloadWorkspaceSearchCsv() {
    const query = document.getElementById('workspace-search').value.trim();
    if (!query) {
        alert('Enter a workspace search query before exporting CSV.');
        return;
    }
    const kinds = collectWorkspaceSearchKinds();
    const params = new URLSearchParams();
    params.set('q', query);
    if (kinds.length > 0 && kinds.length < WORKSPACE_SEARCH_KIND_DEFINITIONS.length) {
        params.set('kinds', kinds.join(','));
    }
    await downloadFileFromApi(`/api/search/export?${params.toString()}`, 'tradingagents-workspace-search.csv', 'Downloaded workspace search CSV', 'Failed to export workspace search CSV');
}

async function downloadPublicRunSharesCsv() {
    const params = new URLSearchParams();
    const query = document.getElementById('public-shares-query').value.trim();
    const availability = document.getElementById('public-shares-availability-filter').value;
    if (query) params.set('q', query);
    if (availability && availability !== 'all') params.set('availability', availability);
    const path = params.toString() ? `/api/public-shares/export?${params.toString()}` : '/api/public-shares/export';
    await downloadFileFromApi(path, 'tradingagents-public-shares.csv', 'Downloaded public shares CSV', 'Failed to export public shares CSV');
}

async function downloadNotificationsCsv() {
    const params = new URLSearchParams();
    const unreadOnly = document.getElementById('notifications-unread-only').checked;
    const member = document.getElementById('notifications-member-filter').value;
    const kind = document.getElementById('notifications-kind-filter').value;
    const severity = document.getElementById('notifications-severity-filter').value;
    if (unreadOnly) params.set('unread_only', 'true');
    if (member) params.set('member', member);
    if (kind && kind !== 'all') params.set('kind', kind);
    if (severity && severity !== 'all') params.set('severity', severity);
    const path = params.toString() ? `/api/notifications/export?${params.toString()}` : '/api/notifications/export';
    await downloadFileFromApi(path, 'tradingagents-notifications.csv', 'Downloaded notifications CSV', 'Failed to export notifications CSV');
}

async function downloadReviewHistoryCsv() {
    const params = new URLSearchParams();
    const reviewer = document.getElementById('review-history-reviewer-filter').value;
    const status = document.getElementById('review-history-status-filter').value;
    const query = document.getElementById('review-history-query').value.trim();
    if (reviewer) params.set('reviewer', reviewer);
    if (status && status !== 'all') params.set('status', status);
    if (query) params.set('q', query);
    const path = params.toString() ? `/api/reviews/export?${params.toString()}` : '/api/reviews/export';
    await downloadFileFromApi(path, 'tradingagents-review-history.csv', 'Downloaded review history CSV', 'Failed to export review history CSV');
}

async function applyInitialRouteState() {
    if (initialRouteApplied) return;
    initialRouteApplied = true;

    const params = new URLSearchParams(window.location.search);
    const runId = params.get('run_id');
    const ticker = params.get('ticker');
    const compareLeft = params.get('compare_left_run_id');
    const compareRight = params.get('compare_right_run_id');
    const searchQuery = params.get('search_q');
    const searchKinds = params.get('search_kinds');
    const panels = params.get('panels');
    const view = params.get('view');
    const memberId = params.get('member_id');
    const notificationsMember = params.get('notifications_member');
    const notificationsUnread = params.get('notifications_unread') === 'true';
    const notificationsKind = params.get('notifications_kind');
    const notificationsSeverity = params.get('notifications_severity');
    const notesMode = params.get('notes_mode');
    const notesQuery = params.get('notes_q');
    const artifactsQuery = params.get('artifacts_q');
    const historyQuery = params.get('history_q');
    const historyStatus = params.get('history_status');
    const historyProvider = params.get('history_provider');
    const historyAsset = params.get('history_asset');
    const historyArchived = params.get('history_archived');
    const screenerScope = params.get('screener_scope');
    const screenerQuery = params.get('screener_q');
    const screenerSignal = params.get('screener_signal');
    const screenerStatus = params.get('screener_status');
    const screenerAsset = params.get('screener_asset');
    const screenerProvider = params.get('screener_provider');
    const reviewReviewer = params.get('review_reviewer');
    const reviewStatus = params.get('review_status');
    const reviewQuery = params.get('review_q');
    const dashboardSections = params.get('dashboard_sections');
    const dashboardOrder = params.get('dashboard_order');
    const hasExplicitContext = Boolean(
        runId
        || ticker
        || (compareLeft && compareRight)
        || searchQuery
        || view,
    );

    if (panels) {
        applyPanelVisibility(panels.split(',').filter(Boolean));
    } else {
        applyPanelVisibility(PANEL_VISIBILITY_IDS);
    }

    if (notesMode !== null) document.getElementById('notes-mode').value = notesMode;
    if (notesQuery !== null) document.getElementById('notes-search').value = notesQuery;
    if (artifactsQuery !== null) document.getElementById('artifacts-library-query').value = artifactsQuery;

    if (ticker) {
        focusTicker(ticker);
    }

    if (runId) {
        await openRunDetails(runId);
        return;
    }

    if (compareLeft && compareRight) {
        document.getElementById('compare-left-run').value = compareLeft;
        document.getElementById('compare-right-run').value = compareRight;
        await compareSelectedRuns();
    }

    if (searchQuery) {
        document.getElementById('workspace-search').value = searchQuery;
        applyWorkspaceSearchKinds(searchKinds ? searchKinds.split(',') : []);
        await runWorkspaceSearch();
    }

    if (memberId) {
        document.getElementById('current-member').value = memberId;
        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, memberId);
        applyCurrentMemberContext();
    }
    if (notificationsMember !== null) {
        document.getElementById('notifications-member-filter').value = notificationsMember;
    }
    document.getElementById('notifications-unread-only').checked = notificationsUnread;
    if (notificationsKind !== null) document.getElementById('notifications-kind-filter').value = notificationsKind;
    if (notificationsSeverity !== null) document.getElementById('notifications-severity-filter').value = notificationsSeverity;
    if (historyQuery !== null) document.getElementById('history-query').value = historyQuery;
    if (historyStatus !== null) document.getElementById('history-status-filter').value = historyStatus;
    if (historyProvider !== null) document.getElementById('history-provider-filter').value = historyProvider;
    if (historyAsset !== null) document.getElementById('history-asset-filter').value = historyAsset;
    if (historyArchived !== null) document.getElementById('history-archived-filter').value = historyArchived;
    if (screenerScope) document.getElementById('screener-scope').value = screenerScope;
    if (screenerQuery) document.getElementById('screener-query').value = screenerQuery;
    if (screenerSignal) document.getElementById('screener-signal-filter').value = screenerSignal;
    if (screenerStatus) document.getElementById('screener-status-filter').value = screenerStatus;
    if (screenerAsset) document.getElementById('screener-asset-filter').value = screenerAsset;
    if (screenerProvider) document.getElementById('screener-provider-filter').value = screenerProvider;
    if (reviewReviewer) document.getElementById('review-history-reviewer-filter').value = reviewReviewer;
    if (reviewStatus) document.getElementById('review-history-status-filter').value = reviewStatus;
    if (reviewQuery) document.getElementById('review-history-query').value = reviewQuery;
    await applyDashboardRoutePreferences(
        dashboardSections ? dashboardSections.split(',').filter(Boolean) : null,
        dashboardOrder ? dashboardOrder.split(',').filter(Boolean) : null,
    );

    if (view === 'briefing') {
        await loadBriefing();
        document.getElementById('briefing-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'notifications') {
        await loadNotifications();
        document.getElementById('notifications-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'notes') {
        await loadNotes();
        document.getElementById('notes-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'artifacts') {
        await loadArtifactLibrary();
        document.getElementById('artifacts-library-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'history') {
        await loadRunHistory();
        document.getElementById('history-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'automations') {
        await loadAutomations();
        document.getElementById('automations-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'analytics') {
        await loadAnalytics();
        document.getElementById('analytics-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'dashboard') {
        await loadDashboard();
        document.getElementById('dashboard-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'screener') {
        await loadScreener();
        document.getElementById('screener-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'member-workspace') {
        await loadMemberWorkspace();
        document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (view === 'reviews') {
        await loadRunReviewHistory();
        document.getElementById('review-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (!hasExplicitContext) {
        await openDefaultHomeSurface();
    }
}

async function openDefaultHomeSurface() {
    const defaultView = currentSettings?.workspace?.default_home_view || 'auto';
    const defaultSavedViewId = currentSettings?.workspace?.default_saved_view_id || null;

    if (defaultView === 'auto') {
        if (getCurrentMemberId()) {
            await loadMemberWorkspace();
            document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }
        await loadDashboard();
        document.getElementById('dashboard-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (defaultView === 'member-workspace') {
        if (getCurrentMemberId()) {
            await loadMemberWorkspace();
            document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }
        await loadDashboard();
        document.getElementById('dashboard-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (defaultView === 'saved-view') {
        const target = currentSavedViews.find((item) => item.id === defaultSavedViewId);
        if (target) {
            applySavedViewItem(target);
            return;
        }
        await loadDashboard();
        document.getElementById('dashboard-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    if (defaultView === 'dashboard') {
        await loadDashboard();
        document.getElementById('dashboard-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'notifications') {
        await loadNotifications();
        document.getElementById('notifications-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'briefing') {
        await loadBriefing();
        document.getElementById('briefing-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'analytics') {
        await loadAnalytics();
        document.getElementById('analytics-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'screener') {
        await loadScreener();
        document.getElementById('screener-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'automations') {
        await loadAutomations();
        document.getElementById('automations-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'reviews') {
        await loadRunReviewHistory();
        document.getElementById('review-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    if (defaultView === 'search') {
        document.getElementById('search-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function buildCurrentViewUrl() {
    const params = new URLSearchParams();
    const tenantId = getTenantId();
    if (tenantId) {
        params.set('tenant_id', tenantId);
    }
    const memberId = getCurrentMemberId();
    if (memberId) {
        params.set('member_id', memberId);
    }
    if (currentRunId) {
        params.set('run_id', currentRunId);
    } else if (currentTickerHomeTicker) {
        params.set('ticker', currentTickerHomeTicker);
    }

    const compareLeft = document.getElementById('compare-left-run').value;
    const compareRight = document.getElementById('compare-right-run').value;
    if (compareLeft && compareRight) {
        params.set('compare_left_run_id', compareLeft);
        params.set('compare_right_run_id', compareRight);
    }

    const searchQuery = document.getElementById('workspace-search').value.trim();
    if (searchQuery) {
        params.set('search_q', searchQuery);
    }
    const kinds = collectWorkspaceSearchKinds();
    if (kinds.length > 0 && kinds.length < WORKSPACE_SEARCH_KIND_DEFINITIONS.length) {
        params.set('search_kinds', kinds.join(','));
    }
    const visiblePanels = collectVisiblePanels();
    if (visiblePanels.length > 0 && visiblePanels.length < PANEL_VISIBILITY_IDS.length) {
        params.set('panels', visiblePanels.join(','));
    }
    const notificationsMember = document.getElementById('notifications-member-filter').value;
    const notificationsUnread = document.getElementById('notifications-unread-only').checked;
    const notificationsKind = document.getElementById('notifications-kind-filter').value;
    const notificationsSeverity = document.getElementById('notifications-severity-filter').value;
    if (notificationsMember) {
        params.set('notifications_member', notificationsMember);
    }
    if (notificationsUnread) {
        params.set('notifications_unread', 'true');
    }
    if (notificationsKind && notificationsKind !== 'all') {
        params.set('notifications_kind', notificationsKind);
    }
    if (notificationsSeverity && notificationsSeverity !== 'all') {
        params.set('notifications_severity', notificationsSeverity);
    }
    const notesMode = document.getElementById('notes-mode').value;
    const notesQuery = document.getElementById('notes-search').value.trim();
    const artifactsQuery = document.getElementById('artifacts-library-query').value.trim();
    if (notesMode && notesMode !== 'context') {
        params.set('notes_mode', notesMode);
    }
    if (notesQuery) {
        params.set('notes_q', notesQuery);
    }
    if (artifactsQuery) {
        params.set('artifacts_q', artifactsQuery);
    }
    const historyQuery = document.getElementById('history-query').value.trim();
    const historyStatus = document.getElementById('history-status-filter').value;
    const historyProvider = document.getElementById('history-provider-filter').value;
    const historyAsset = document.getElementById('history-asset-filter').value;
    const historyArchived = document.getElementById('history-archived-filter').value;
    if (historyQuery) params.set('history_q', historyQuery);
    if (historyStatus) params.set('history_status', historyStatus);
    if (historyProvider) params.set('history_provider', historyProvider);
    if (historyAsset) params.set('history_asset', historyAsset);
    if (historyArchived && historyArchived !== 'active') params.set('history_archived', historyArchived);
    const screenerScope = document.getElementById('screener-scope').value;
    const screenerQuery = document.getElementById('screener-query').value.trim();
    const screenerSignal = document.getElementById('screener-signal-filter').value;
    const screenerStatus = document.getElementById('screener-status-filter').value;
    const screenerAsset = document.getElementById('screener-asset-filter').value;
    const screenerProvider = document.getElementById('screener-provider-filter').value;
    if (screenerScope && screenerScope !== 'all') params.set('screener_scope', screenerScope);
    if (screenerQuery) params.set('screener_q', screenerQuery);
    if (screenerSignal && screenerSignal !== 'all') params.set('screener_signal', screenerSignal);
    if (screenerStatus && screenerStatus !== 'all') params.set('screener_status', screenerStatus);
    if (screenerAsset && screenerAsset !== 'all') params.set('screener_asset', screenerAsset);
    if (screenerProvider && screenerProvider !== 'all') params.set('screener_provider', screenerProvider);
    const reviewReviewer = document.getElementById('review-history-reviewer-filter').value;
    const reviewStatus = document.getElementById('review-history-status-filter').value;
    const reviewQuery = document.getElementById('review-history-query').value.trim();
    if (reviewReviewer) params.set('review_reviewer', reviewReviewer);
    if (reviewStatus && reviewStatus !== 'all') params.set('review_status', reviewStatus);
    if (reviewQuery) params.set('review_q', reviewQuery);
    const dashboardSections = collectDashboardVisibleSections();
    const dashboardOrder = collectDashboardSectionOrder();
    if (dashboardLayoutIsCustomized(dashboardSections, dashboardOrder)) {
        params.set('dashboard_sections', dashboardSections.join(','));
        params.set('dashboard_order', dashboardOrder.join(','));
    }

    const hasPrimaryContext = Boolean(currentRunId || currentTickerHomeTicker || (compareLeft && compareRight) || searchQuery);
    if (!hasPrimaryContext) {
        if (currentMemberWorkspaceId) {
            params.set('view', 'member-workspace');
        } else if (dashboardLayoutIsCustomized(dashboardSections, dashboardOrder)) {
            params.set('view', 'dashboard');
        } else if (reviewReviewer || reviewStatus !== 'all' || reviewQuery) {
            params.set('view', 'reviews');
        } else if (notificationsMember || notificationsUnread || (notificationsKind && notificationsKind !== 'all') || (notificationsSeverity && notificationsSeverity !== 'all')) {
            params.set('view', 'notifications');
        } else if ((notesMode && notesMode !== 'context') || notesQuery) {
            params.set('view', 'notes');
        } else if (artifactsQuery) {
            params.set('view', 'artifacts');
        } else if (historyQuery || historyStatus || historyProvider || historyAsset || (historyArchived && historyArchived !== 'active')) {
            params.set('view', 'history');
        } else if (
            (screenerScope && screenerScope !== 'all')
            || screenerQuery
            || (screenerSignal && screenerSignal !== 'all')
            || (screenerStatus && screenerStatus !== 'all')
            || (screenerAsset && screenerAsset !== 'all')
            || (screenerProvider && screenerProvider !== 'all')
        ) {
            params.set('view', 'screener');
        }
    }
    return `/?${params.toString()}`;
}

function collectVisiblePanels() {
    return PANEL_VISIBILITY_IDS.filter((panelId) => {
        const checkbox = document.getElementById(`panel-toggle-${panelId}`);
        return checkbox ? checkbox.checked : true;
    });
}

function syncPanelVisibilityControls() {
    PANEL_VISIBILITY_IDS.forEach((panelId) => {
        const checkbox = document.getElementById(`panel-toggle-${panelId}`);
        if (!checkbox) return;
        const panel = document.getElementById(panelId);
        checkbox.checked = panel ? panel.style.display !== 'none' : true;
    });
}

function applyPanelVisibility(visiblePanels) {
    const visible = new Set(visiblePanels || PANEL_VISIBILITY_IDS);
    PANEL_VISIBILITY_IDS.forEach((panelId) => {
        const panel = document.getElementById(panelId);
        if (!panel) return;
        panel.style.display = visible.has(panelId) ? '' : 'none';
        const checkbox = document.getElementById(`panel-toggle-${panelId}`);
        if (checkbox) {
            checkbox.checked = visible.has(panelId);
        }
    });
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
        ['Benchmark', summary.benchmark_ticker],
        ['Temperature', summary.temperature],
        ['Memory Cap', summary.memory_log_max_entries],
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

function resetRunAnnotationForm() {
    currentRunAnnotation = null;
    document.getElementById('annotation-label').value = '';
    document.getElementById('annotation-summary').value = '';
    document.getElementById('annotation-next-step').value = '';
}

function resetRunReviewForm() {
    currentRunReview = null;
    document.getElementById('review-scope').textContent = 'Open a run to assign a reviewer and track review status.';
    document.getElementById('reviewer-member').value = '';
    document.getElementById('review-status').value = 'pending';
    document.getElementById('review-note').value = '';
}

function prepareReviewContext(run) {
    currentRunReview = run.review || null;
    document.getElementById('review-scope').textContent = `Reviewing run ${run.run_id}${run.ticker ? ` · ${run.ticker}` : ''}${run.date ? ` · ${run.date}` : ''}.`;
    document.getElementById('reviewer-member').value = run.review?.reviewer || '';
    document.getElementById('review-status').value = run.review?.status || 'pending';
    document.getElementById('review-note').value = run.review?.note || '';
    void loadRunReviewHistory();
}

function resetRunReviewHistory(message = 'Saved run reviews will appear here.') {
    document.getElementById('review-history-summary').innerHTML = '';
    document.getElementById('review-history-empty').textContent = message;
    document.getElementById('review-history-empty').style.display = '';
    document.getElementById('review-history-list').innerHTML = '';
}

function renderRunReviewHistorySummary(summary) {
    const container = document.getElementById('review-history-summary');
    const cards = [
        ['Total', summary.total_reviews],
        ['Pending', summary.pending_count],
        ['Approved', summary.approved_count],
        ['Changes Requested', summary.changes_requested_count],
    ];
    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';
        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;
        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);
        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function renderRunReviewHistory(payload) {
    const listEl = document.getElementById('review-history-list');
    listEl.innerHTML = '';
    if (!payload.items.length) {
        resetRunReviewHistory('No reviews match the current filters.');
        return;
    }
    document.getElementById('review-history-empty').style.display = 'none';
    renderRunReviewHistorySummary(payload.summary);
    payload.items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.ticker ? `${item.ticker} · ${item.date || 'n/a'}` : item.run_id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [item.reviewer, item.status, item.updated_at].filter(Boolean).join(' · ');
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = item.note || item.signal || 'No review note';
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);
        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open Run';
        openButton.addEventListener('click', () => {
            void openRunDetails(item.run_id);
        });
        actionsEl.appendChild(openButton);
        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        listEl.appendChild(row);
    });
}

async function loadRunReviewHistory() {
    try {
        const params = new URLSearchParams();
        const reviewer = document.getElementById('review-history-reviewer-filter').value;
        const status = document.getElementById('review-history-status-filter').value;
        const query = document.getElementById('review-history-query').value.trim();
        if (reviewer) params.set('reviewer', reviewer);
        if (status && status !== 'all') params.set('status', status);
        if (query) params.set('q', query);
        const path = params.toString() ? `/api/reviews?${params.toString()}` : '/api/reviews';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderRunReviewHistory(await resp.json());
    } catch (e) {
        resetRunReviewHistory(`Failed to load review history: ${e.message}`);
    }
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

function resetRecentlyViewed(message = 'Recently opened runs, tickers, and views will appear here.') {
    document.getElementById('recently-viewed-empty').textContent = message;
    document.getElementById('recently-viewed-empty').style.display = '';
    document.getElementById('recently-viewed-list').innerHTML = '';
}

function removeRecentlyViewedItem(kind, id) {
    const kept = readRecentlyViewedItems().filter((item) => !(item.kind === kind && item.id === id));
    writeRecentlyViewedItems(kept);
    loadRecentlyViewed();
}

function openRecentlyViewedItem(item) {
    if (item.kind === 'run' && item.run_id) {
        void openRunDetails(item.run_id);
        return;
    }
    if (item.kind === 'ticker' && item.ticker) {
        focusTicker(item.ticker);
        return;
    }
    if (item.kind === 'view') {
        applySavedViewItem(item);
    }
}

function renderRecentlyViewed(items) {
    const emptyEl = document.getElementById('recently-viewed-empty');
    const listEl = document.getElementById('recently-viewed-list');
    listEl.innerHTML = '';

    if (!items.length) {
        resetRecentlyViewed();
        return;
    }

    emptyEl.style.display = 'none';
    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.title || item.id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [item.kind, item.subtitle, item.viewed_at].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open';
        openButton.addEventListener('click', () => {
            openRecentlyViewedItem(item);
        });
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            removeRecentlyViewedItem(item.kind, item.id);
        });
        actionsEl.appendChild(openButton);
        actionsEl.appendChild(removeButton);

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        listEl.appendChild(row);
    });
}

function loadRecentlyViewed() {
    renderRecentlyViewed(readRecentlyViewedItems());
}

function clearRecentlyViewed() {
    window.localStorage.removeItem(recentlyViewedStorageKey());
    loadRecentlyViewed();
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

function collectSelectedHistoryRunIds() {
    return Array.from(document.querySelectorAll('#history-list input[data-history-run-id]:checked'))
        .map((input) => input.dataset.historyRunId)
        .filter(Boolean);
}

function toggleVisibleHistorySelection(checked) {
    document.querySelectorAll('#history-list input[data-history-run-id]').forEach((input) => {
        input.checked = checked;
    });
}

function resetArtifactLibrary(message = 'Completed run reports and full-state files will appear here.') {
    document.getElementById('artifacts-library-empty').textContent = message;
    document.getElementById('artifacts-library-empty').style.display = '';
    document.getElementById('artifacts-library-list').innerHTML = '';
}

function renderArtifactLibrary(items) {
    const emptyEl = document.getElementById('artifacts-library-empty');
    const listEl = document.getElementById('artifacts-library-list');
    listEl.innerHTML = '';

    if (!items.length) {
        resetArtifactLibrary();
        return;
    }

    emptyEl.style.display = 'none';
    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = `${item.ticker} · ${item.date}`;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = `${item.status} · ${item.created_at}`;
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = [
            item.signal || item.error || 'Saved artifacts available',
            `${item.artifact_count} artifact(s)`,
        ].join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open Run';
        openButton.addEventListener('click', () => {
            void openRunDetails(item.run_id);
        });
        actionsEl.appendChild(openButton);

        if (item.report_download_url) {
            const reportLink = document.createElement('a');
            reportLink.className = 'btn-secondary link-btn';
            reportLink.href = buildApiUrl(item.report_download_url);
            reportLink.textContent = 'Report';
            actionsEl.appendChild(reportLink);
        }
        if (item.state_download_url) {
            const stateLink = document.createElement('a');
            stateLink.className = 'btn-secondary link-btn';
            stateLink.href = buildApiUrl(item.state_download_url);
            stateLink.textContent = 'Full State';
            actionsEl.appendChild(stateLink);
        }

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        listEl.appendChild(row);
    });
}

async function loadArtifactLibrary() {
    try {
        const params = new URLSearchParams();
        const query = document.getElementById('artifacts-library-query').value.trim();
        if (query) params.set('q', query);
        const path = params.toString() ? `/api/artifacts/library?${params.toString()}` : '/api/artifacts/library';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderArtifactLibrary(await resp.json());
    } catch (e) {
        resetArtifactLibrary(`Failed to load reports library: ${e.message}`);
    }
}

async function loadRunHistory() {
    const listEl = document.getElementById('history-list');
    const emptyEl = document.getElementById('history-empty');
    document.getElementById('history-select-all').checked = false;

    try {
        const params = new URLSearchParams();
        const query = document.getElementById('history-query').value.trim();
        const archived = document.getElementById('history-archived-filter').value;
        const status = document.getElementById('history-status-filter').value;
        const provider = document.getElementById('history-provider-filter').value;
        const assetType = document.getElementById('history-asset-filter').value;
        if (query) params.set('q', query);
        if (archived && archived !== 'active') params.set('archived', archived);
        if (status) params.set('status', status);
        if (provider) params.set('provider', provider);
        if (assetType) params.set('asset_type', assetType);
        const path = params.toString() ? `/api/runs?${params.toString()}` : '/api/runs';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        const runs = await resp.json();
        runHistory = runs;
        populateCompareRunOptions();
        listEl.innerHTML = '';

        if (runs.length === 0) {
            emptyEl.style.display = '';
            emptyEl.textContent = (query || archived !== 'active' || status || provider || assetType)
                ? 'No runs match the current history filters.'
                : 'No runs yet.';
            void loadTickerHome();
            void loadWatchlist();
            void loadAlerts();
            void loadPortfolio();
            void loadDashboard();
            void loadArtifactLibrary();
            void loadAnalytics();
            void loadScreener();
            void loadNotifications();
            void loadAutomations();
            void loadPresets();
            void loadPublicRunShares();
            void loadTimeline();
            void loadCalendar();
            void loadPinnedRuns();
            void loadActionBoard();
            void loadBriefing();
            resetComparePanel('Choose two saved runs to compare their signals, settings, and report sections.');
            resetRunComments();
            resetFollowUpChat('Open a saved run, then ask follow-up questions about that analysis.');
            return;
        }

        emptyEl.style.display = 'none';
        runs.forEach(run => {
            const item = document.createElement('div');
            const canDelete = ['completed', 'failed', 'cancelled'].includes(run.status);
            const canRetry = ['completed', 'failed', 'cancelled'].includes(run.status);
            const canArchive = ['completed', 'failed', 'cancelled'].includes(run.status);
            const queueSuffix = run.status === 'queued' && run.queue_position
                ? ` (#${run.queue_position})`
                : '';
            const annotationLine = run.annotation
                ? `<div class="history-signal">Annotation: ${run.annotation.label}${run.annotation.summary ? ` · ${run.annotation.summary}` : ''}</div>`
                : '';
            item.className = 'history-item';
            item.innerHTML = `
                <div class="history-actions">
                    <label class="inline-toggle">
                        <input type="checkbox" data-history-run-id="${run.run_id}">
                        Select
                    </label>
                </div>
                <div class="history-meta">
                    <div class="history-title">${run.archived ? '[Archived] ' : ''}${run.ticker} · ${run.date}</div>
                    <div class="history-subtitle">${run.asset_type} · ${run.llm_provider || 'unknown'} · created ${run.created_at}</div>
                    <div class="history-signal">${run.signal || run.error || 'No final signal yet'}</div>
                    ${annotationLine}
                </div>
                <div class="history-actions">
                    <span class="history-status status-${run.status}">${run.status}${queueSuffix}</span>
                    <button class="btn-secondary history-open" type="button" data-run-id="${run.run_id}">Open</button>
                    ${canArchive ? `<button class="btn-secondary history-archive" type="button" data-run-id="${run.run_id}">${run.archived ? 'Restore' : 'Archive'}</button>` : ''}
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
            const archiveButton = item.querySelector('.history-archive');
            if (archiveButton) {
                archiveButton.addEventListener('click', () => {
                    void bulkUpdateRuns(run.archived ? 'restore' : 'archive', [run.run_id]);
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
        void loadTickerHome();
        void loadWatchlist();
        void loadAlerts();
        void loadPortfolio();
        void loadDashboard();
        void loadArtifactLibrary();
        void loadAnalytics();
        void loadScreener();
        void loadNotifications();
        void loadAutomations();
        void loadPresets();
        void loadPublicRunShares();
        void loadTimeline();
        void loadCalendar();
        void loadPinnedRuns();
        void loadActionBoard();
        void loadBriefing();
    } catch (e) {
        runHistory = [];
        populateCompareRunOptions();
        emptyEl.style.display = '';
        emptyEl.textContent = `Failed to load runs: ${e.message}`;
        void loadWatchlist();
        void loadAlerts();
        void loadPortfolio();
        void loadDashboard();
        void loadArtifactLibrary();
        void loadAnalytics();
        void loadScreener();
        void loadNotifications();
        void loadAutomations();
        void loadPresets();
        void loadPublicRunShares();
        void loadTimeline();
        void loadCalendar();
        void loadPinnedRuns();
        void loadActionBoard();
        void loadBriefing();
        resetComparePanel(`Failed to load runs for comparison: ${e.message}`);
        resetRunComments();
        resetFollowUpChat('Open a saved run, then ask follow-up questions about that analysis.');
    }
}

async function bulkUpdateRuns(action, explicitIds = null) {
    const ids = explicitIds && explicitIds.length ? explicitIds : collectSelectedHistoryRunIds();
    if (!ids.length) {
        alert('Select at least one visible run first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/runs/bulk'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ ids, action }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        const summary = [
            action === 'delete' ? `Deleted ${payload.deleted}` : null,
            action === 'retry' ? `Retried ${payload.retried}` : null,
            action === 'archive' ? `Archived ${payload.archived}` : null,
            action === 'restore' ? `Restored ${payload.restored}` : null,
            payload.skipped ? `skipped ${payload.skipped}` : null,
        ].filter(Boolean).join(', ');
        const label = {
            delete: 'Bulk delete',
            retry: 'Bulk retry',
            archive: 'Bulk archive',
            restore: 'Bulk restore',
        }[action] || 'Bulk update';
        appendLog(`${label} complete: ${summary}.`);
        await loadRunHistory();
        await loadSystemStatus();
    } catch (e) {
        alert(`Failed to ${action} runs: ${e.message}`);
    }
}

function scheduleTickerHomeRefresh(rawTicker) {
    if (tickerHomeTimer) {
        window.clearTimeout(tickerHomeTimer);
    }
    tickerHomeTimer = window.setTimeout(() => {
        void loadTickerHome(rawTicker);
    }, 250);
}

function resetTickerHome(message = 'Enter a ticker or open a past run to see saved research for that symbol.') {
    const emptyEl = document.getElementById('ticker-home-empty');
    const contentEl = document.getElementById('ticker-home-content');
    const titleEl = document.getElementById('ticker-home-title');
    const summaryEl = document.getElementById('ticker-home-summary');
    const runsEl = document.getElementById('ticker-home-runs');

    emptyEl.textContent = message;
    emptyEl.style.display = '';
    contentEl.style.display = 'none';
    titleEl.textContent = '';
    summaryEl.innerHTML = '';
    runsEl.innerHTML = '';
    currentTickerHomeTicker = null;
}

function renderTickerHome(overview) {
    const emptyEl = document.getElementById('ticker-home-empty');
    const contentEl = document.getElementById('ticker-home-content');
    const titleEl = document.getElementById('ticker-home-title');
    const summaryEl = document.getElementById('ticker-home-summary');
    const runsEl = document.getElementById('ticker-home-runs');

    if (!overview.run_count) {
        resetTickerHome(`No saved research yet for ${overview.ticker}. Run an analysis to start building this ticker's history.`);
        return;
    }

    emptyEl.style.display = 'none';
    contentEl.style.display = '';
    titleEl.textContent = `${overview.ticker} Research Home`;
    currentTickerHomeTicker = overview.ticker;

    const cards = [
        ['Saved Runs', overview.run_count],
        ['Latest Signal', overview.latest_signal || 'Pending / none'],
        ['Latest Status', overview.latest_status || 'unknown'],
        ['Latest Analysis Date', overview.latest_date || 'n/a'],
        ['Latest Created', overview.latest_created_at || 'n/a'],
    ];

    summaryEl.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        summaryEl.appendChild(cardEl);
    });

    runsEl.innerHTML = '';
    overview.recent_runs.forEach((run) => {
        const item = document.createElement('div');
        const queueSuffix = run.status === 'queued' && run.queue_position
            ? ` (#${run.queue_position})`
            : '';
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';

        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = `${run.ticker} · ${run.date}`;

        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = `${run.asset_type} · created ${run.created_at}`;

        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = run.signal || run.error || 'No final signal yet';

        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';

        const statusEl = document.createElement('span');
        statusEl.className = `history-status status-${run.status}`;
        statusEl.textContent = `${run.status}${queueSuffix}`;

        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary ticker-home-open';
        openButton.type = 'button';
        openButton.dataset.runId = run.run_id;
        openButton.textContent = 'Open';
        openButton.addEventListener('click', () => {
            void openRunDetails(run.run_id);
        });

        actionsEl.appendChild(statusEl);
        actionsEl.appendChild(openButton);
        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        runsEl.appendChild(item);
    });
}

async function loadTickerHome(ticker = null) {
    const normalized = (ticker ?? document.getElementById('ticker').value ?? '').trim().toUpperCase();
    if (!normalized) {
        resetTickerHome();
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/tickers/${encodeURIComponent(normalized)}`));
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        renderTickerHome(await resp.json());
    } catch (e) {
        resetTickerHome(`Failed to load saved research for ${normalized}: ${e.message}`);
    }
}

function resetWatchlist(message = 'Save tickers here to keep an eye on their latest research signal.') {
    const emptyEl = document.getElementById('watchlist-empty');
    const listEl = document.getElementById('watchlist-list');
    emptyEl.textContent = message;
    emptyEl.style.display = '';
    listEl.innerHTML = '';
}

function focusTicker(ticker) {
    document.getElementById('ticker').value = ticker;
    document.getElementById('asset-type-hint').textContent = detectAssetType(ticker) !== 'stock'
        ? `Detected: ${detectAssetType(ticker)}`
        : '';
    rememberRecentlyViewedItem({
        kind: 'ticker',
        id: ticker,
        title: ticker,
        subtitle: 'Ticker Home',
        ticker,
    });
    loadRecentlyViewed();
    void loadTickerHome(ticker);
    prepareNotesContext({ ticker, run_id: null, date: null });
    resetRunComments();
}

function formatImportErrors(errors) {
    if (!Array.isArray(errors) || !errors.length) {
        return '';
    }
    const preview = errors.slice(0, 3).map((item) => `Line ${item.line_number}: ${item.message}`);
    const suffix = errors.length > 3 ? `\n+ ${errors.length - 3} more row(s)` : '';
    return `${preview.join('\n')}${suffix}`;
}

function renderWatchlist(entries) {
    const emptyEl = document.getElementById('watchlist-empty');
    const listEl = document.getElementById('watchlist-list');
    listEl.innerHTML = '';

    if (!entries.length) {
        resetWatchlist();
        return;
    }

    emptyEl.style.display = 'none';
    entries.forEach((entry) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';

        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = entry.ticker;

        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = entry.run_count
            ? `${entry.run_count} saved run(s) · latest ${entry.latest_date || 'n/a'}`
            : 'No saved research yet';

        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = entry.latest_signal || entry.latest_status || 'No final signal yet';

        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';

        if (entry.latest_status) {
            const statusEl = document.createElement('span');
            statusEl.className = `history-status status-${entry.latest_status}`;
            statusEl.textContent = entry.latest_status;
            actionsEl.appendChild(statusEl);
        }

        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open';
        openButton.addEventListener('click', () => {
            focusTicker(entry.ticker);
        });

        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removeWatchlistTicker(entry.ticker);
        });

        actionsEl.appendChild(openButton);
        actionsEl.appendChild(removeButton);
        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        listEl.appendChild(item);
    });
}

async function loadWatchlist() {
    try {
        const resp = await fetch(buildApiUrl('/api/watchlist'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderWatchlist(await resp.json());
    } catch (e) {
        resetWatchlist(`Failed to load watchlist: ${e.message}`);
    }
}

async function addCurrentTickerToWatchlist() {
    const ticker = (currentTickerHomeTicker || document.getElementById('ticker').value || '').trim().toUpperCase();
    if (!ticker) {
        alert('Enter or open a ticker before adding it to the watchlist.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/watchlist'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ ticker }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Saved ${ticker} to watchlist.`);
        await loadWatchlist();
    } catch (e) {
        alert(`Failed to save watchlist ticker: ${e.message}`);
    }
}

async function importWatchlist() {
    const textarea = document.getElementById('watchlist-import-text');
    const content = textarea.value.trim();
    if (!content) {
        alert('Paste watchlist content before importing.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/watchlist/import'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ content }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        const summary = [
            `Imported ${payload.imported_count} watchlist ticker(s)`,
            payload.skipped_count ? `skipped ${payload.skipped_count} duplicate(s)` : null,
            payload.error_count ? `${payload.error_count} row(s) had issues` : null,
        ].filter(Boolean).join(', ');
        appendLog(`${summary}.`);
        if (!payload.error_count) {
            textarea.value = '';
            setImportFileStatus('watchlist-import-file-status', 'No file selected yet. Supported formats: CSV, TSV, TXT.');
        }
        await loadWatchlist();
        if (payload.error_count) {
            alert(`${summary}.\n${formatImportErrors(payload.errors)}`);
        }
    } catch (e) {
        alert(`Failed to import watchlist: ${e.message}`);
    }
}

async function removeWatchlistTicker(ticker) {
    try {
        const resp = await fetch(buildApiUrl(`/api/watchlist/${encodeURIComponent(ticker)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Removed ${ticker} from watchlist.`);
        await loadWatchlist();
    } catch (e) {
        alert(`Failed to remove watchlist ticker: ${e.message}`);
    }
}

function resetAlerts(message = 'Create signal or status rules for the current ticker, then review the latest hits here.') {
    document.getElementById('alert-empty').textContent = message;
    document.getElementById('alert-empty').style.display = '';
    document.getElementById('alert-rules-list').innerHTML = '';
    document.getElementById('alert-hits-list').innerHTML = '';
}

function renderAlertRuleItem(rule) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';

    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = `${rule.ticker} · ${rule.field}`;

    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = `Trigger when ${rule.field} = ${rule.value}`;

    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';

    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = 'Open';
    openButton.addEventListener('click', () => {
        focusTicker(rule.ticker);
    });

    const removeButton = document.createElement('button');
    removeButton.className = 'btn-secondary';
    removeButton.type = 'button';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => {
        void removeAlertRule(rule.id);
    });

    actionsEl.appendChild(openButton);
    actionsEl.appendChild(removeButton);
    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderAlertHitItem(hit) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';

    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = `${hit.ticker} · ${hit.field}`;

    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = hit.message;

    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    signalEl.textContent = `Run ${hit.run_date} · actual ${hit.actual_value}`;

    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';

    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = 'Open Run';
    openButton.addEventListener('click', () => {
        void openRunDetails(hit.run_id);
    });

    actionsEl.appendChild(openButton);
    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderAlerts(payload) {
    const emptyEl = document.getElementById('alert-empty');
    const rulesEl = document.getElementById('alert-rules-list');
    const hitsEl = document.getElementById('alert-hits-list');
    rulesEl.innerHTML = '';
    hitsEl.innerHTML = '';

    const hasRules = payload.rules && payload.rules.length > 0;
    const hasHits = payload.hits && payload.hits.length > 0;
    if (!hasRules && !hasHits) {
        resetAlerts();
        return;
    }

    emptyEl.style.display = 'none';
    if (hasRules) {
        payload.rules.forEach((rule) => {
            rulesEl.appendChild(renderAlertRuleItem(rule));
        });
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'hint';
        placeholder.textContent = 'No saved rules yet.';
        rulesEl.appendChild(placeholder);
    }

    if (hasHits) {
        payload.hits.forEach((hit) => {
            hitsEl.appendChild(renderAlertHitItem(hit));
        });
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'hint';
        placeholder.textContent = 'No active hits right now.';
        hitsEl.appendChild(placeholder);
    }
}

async function loadAlerts() {
    try {
        const resp = await fetch(buildApiUrl('/api/alerts'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderAlerts(await resp.json());
    } catch (e) {
        resetAlerts(`Failed to load alerts: ${e.message}`);
    }
}

async function addCurrentAlertRule() {
    const ticker = (currentTickerHomeTicker || document.getElementById('ticker').value || '').trim().toUpperCase();
    const field = document.getElementById('alert-field').value;
    const value = document.getElementById('alert-value').value.trim();

    if (!ticker) {
        alert('Enter or open a ticker before creating an alert.');
        return;
    }
    if (!value) {
        alert('Enter an alert target value first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/alerts/rules'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ ticker, field, value }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Saved alert for ${ticker}: ${field} = ${value}`);
        document.getElementById('alert-value').value = '';
        await loadAlerts();
    } catch (e) {
        alert(`Failed to save alert rule: ${e.message}`);
    }
}

async function removeAlertRule(ruleId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/alerts/rules/${encodeURIComponent(ruleId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed alert rule.');
        await loadAlerts();
    } catch (e) {
        alert(`Failed to remove alert rule: ${e.message}`);
    }
}

function resetPortfolio(message = 'Save positions here to track holdings alongside the latest research signal.') {
    document.getElementById('portfolio-empty').textContent = message;
    document.getElementById('portfolio-empty').style.display = '';
    document.getElementById('portfolio-summary').innerHTML = '';
    document.getElementById('portfolio-list').innerHTML = '';
}

function renderPortfolioSummary(summary) {
    const container = document.getElementById('portfolio-summary');
    const cards = [
        ['Positions', summary.position_count],
        ['Unique Tickers', summary.unique_ticker_count],
        ['Cost Basis', summary.total_cost_basis],
        ['Signals', Object.entries(summary.signal_breakdown || {}).map(([key, count]) => `${key}: ${count}`).join(', ') || 'None'],
    ];

    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function renderPortfolio(payload) {
    const emptyEl = document.getElementById('portfolio-empty');
    const listEl = document.getElementById('portfolio-list');
    listEl.innerHTML = '';

    if (!payload.positions.length) {
        resetPortfolio();
        return;
    }

    emptyEl.style.display = 'none';
    renderPortfolioSummary(payload.summary);
    payload.positions.forEach((position) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';

        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = `${position.ticker} · qty ${position.quantity}`;

        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = `Avg cost ${position.average_cost} · cost basis ${position.cost_basis}`;

        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = position.latest_signal || position.latest_status || 'No saved signal yet';

        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';

        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open';
        openButton.addEventListener('click', () => {
            focusTicker(position.ticker);
        });

        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removePortfolioPosition(position.id);
        });

        actionsEl.appendChild(openButton);
        actionsEl.appendChild(removeButton);
        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        listEl.appendChild(item);
    });
}

async function loadPortfolio() {
    try {
        const resp = await fetch(buildApiUrl('/api/portfolio'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderPortfolio(await resp.json());
    } catch (e) {
        resetPortfolio(`Failed to load portfolio: ${e.message}`);
    }
}

async function addCurrentPortfolioPosition() {
    const ticker = (currentTickerHomeTicker || document.getElementById('ticker').value || '').trim().toUpperCase();
    const quantity = document.getElementById('portfolio-quantity').value.trim();
    const averageCost = document.getElementById('portfolio-average-cost').value.trim();

    if (!ticker) {
        alert('Enter or open a ticker before adding a position.');
        return;
    }
    if (!quantity || !averageCost) {
        alert('Enter both quantity and average cost first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/portfolio/positions'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                ticker,
                quantity: Number(quantity),
                average_cost: Number(averageCost),
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Saved portfolio position for ${ticker}.`);
        document.getElementById('portfolio-quantity').value = '';
        document.getElementById('portfolio-average-cost').value = '';
        await loadPortfolio();
    } catch (e) {
        alert(`Failed to save portfolio position: ${e.message}`);
    }
}

async function importPortfolio() {
    const textarea = document.getElementById('portfolio-import-text');
    const content = textarea.value.trim();
    if (!content) {
        alert('Paste portfolio content before importing.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/portfolio/import'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ content }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        const summary = [
            `Imported ${payload.imported_count} portfolio position(s)`,
            payload.skipped_count ? `skipped ${payload.skipped_count} row(s)` : null,
            payload.error_count ? `${payload.error_count} row(s) had issues` : null,
        ].filter(Boolean).join(', ');
        appendLog(`${summary}.`);
        if (!payload.error_count) {
            textarea.value = '';
            setImportFileStatus('portfolio-import-file-status', 'No file selected yet. Supported formats: CSV, TSV, TXT.');
        }
        await loadPortfolio();
        if (payload.error_count) {
            alert(`${summary}.\n${formatImportErrors(payload.errors)}`);
        }
    } catch (e) {
        alert(`Failed to import portfolio: ${e.message}`);
    }
}

async function importWorkspaceSnapshot() {
    const textarea = document.getElementById('workspace-import-text');
    const mode = document.getElementById('workspace-import-mode').value;
    const content = textarea.value.trim();
    if (!content) {
        alert('Paste exported workspace JSON before importing.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/workspace/import'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ content, mode }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        const summary = [
            `Workspace import finished in ${payload.mode} mode`,
            `watchlist ${payload.watchlist_count}`,
            `portfolio ${payload.portfolio_position_count}`,
            `notes ${payload.note_count}`,
            `views ${payload.saved_view_count}`,
            `members ${payload.member_count}`,
        ].join(', ');
        appendLog(`${summary}.`);
        textarea.value = '';
        setImportFileStatus('workspace-import-file-status', 'No file selected yet. Supported format: JSON.');
        await refreshWorkspaceAfterImport();
    } catch (e) {
        alert(`Failed to import workspace snapshot: ${e.message}`);
    }
}

async function removePortfolioPosition(positionId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/portfolio/positions/${encodeURIComponent(positionId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed portfolio position.');
        await loadPortfolio();
    } catch (e) {
        alert(`Failed to remove portfolio position: ${e.message}`);
    }
}

function resetAnalytics(message = 'Run-level analytics for status, providers, signals, and activity trends will appear here.') {
    document.getElementById('analytics-empty').textContent = message;
    document.getElementById('analytics-empty').style.display = '';
    document.getElementById('analytics-content').style.display = 'none';
    document.getElementById('analytics-summary').innerHTML = '';
    document.getElementById('analytics-status').innerHTML = '';
    document.getElementById('analytics-providers').innerHTML = '';
    document.getElementById('analytics-signals').innerHTML = '';
    document.getElementById('analytics-assets').innerHTML = '';
    document.getElementById('analytics-tickers').innerHTML = '';
    document.getElementById('analytics-daily').innerHTML = '';
}

function renderAnalyticsSummary(summary) {
    const container = document.getElementById('analytics-summary');
    const cards = [
        ['Generated', summary.generated_at],
        ['Total Runs', summary.total_runs],
        ['Terminal', summary.terminal_runs],
        ['Queued', summary.queued_runs],
        ['Running', summary.running_runs],
        ['Success Rate', `${Math.round((summary.success_rate || 0) * 100)}%`],
        ['Avg Duration (s)', summary.avg_duration_seconds ?? 'n/a'],
        ['Unique Tickers', summary.unique_ticker_count],
    ];

    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function renderAnalyticsBuckets(containerId, items, emptyMessage) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    if (!items.length) {
        appendBriefingPlaceholder(container, emptyMessage);
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.label;
        metaEl.appendChild(titleEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const valueEl = document.createElement('span');
        valueEl.className = 'history-status status-completed';
        valueEl.textContent = String(item.value);
        actionsEl.appendChild(valueEl);

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

function renderAnalyticsDailyActivity(items) {
    const container = document.getElementById('analytics-daily');
    container.innerHTML = '';
    if (!items.length) {
        appendBriefingPlaceholder(container, 'No daily activity yet.');
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.date;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = `${item.total_runs} run(s)`;
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = `Completed ${item.completed_runs} · Failed ${item.failed_runs} · Cancelled ${item.cancelled_runs}`;
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        row.appendChild(metaEl);
        container.appendChild(row);
    });
}

function renderAnalytics(payload) {
    if (!payload.summary.total_runs) {
        resetAnalytics();
        return;
    }

    document.getElementById('analytics-empty').style.display = 'none';
    document.getElementById('analytics-content').style.display = '';
    renderAnalyticsSummary(payload.summary);
    renderAnalyticsBuckets('analytics-status', payload.status_breakdown, 'No status data yet.');
    renderAnalyticsBuckets('analytics-providers', payload.provider_breakdown, 'No provider usage yet.');
    renderAnalyticsBuckets('analytics-signals', payload.signal_breakdown, 'No signal data yet.');
    renderAnalyticsBuckets('analytics-assets', payload.asset_type_breakdown, 'No asset mix yet.');
    renderAnalyticsBuckets('analytics-tickers', payload.top_tickers, 'No ticker activity yet.');
    renderAnalyticsDailyActivity(payload.daily_activity);
}

async function loadAnalytics() {
    try {
        const resp = await fetch(buildApiUrl('/api/analytics'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderAnalytics(await resp.json());
    } catch (e) {
        resetAnalytics(`Failed to load analytics: ${e.message}`);
    }
}

function resetScreener(message = 'Explore saved tickers across watchlist, portfolio, pinned actions, and recent research outcomes.') {
    document.getElementById('screener-empty').textContent = message;
    document.getElementById('screener-empty').style.display = '';
    document.getElementById('screener-content').style.display = 'none';
    document.getElementById('screener-summary').innerHTML = '';
    document.getElementById('screener-list').innerHTML = '';
}

function renderScreenerSummary(summary) {
    const container = document.getElementById('screener-summary');
    const cards = [
        ['Candidates', summary.total_candidates],
        ['Bullish', summary.bullish_count],
        ['Bearish', summary.bearish_count],
        ['Alert Hits', summary.alert_hit_count],
        ['Watchlist', summary.watchlist_count],
        ['Portfolio', summary.portfolio_count],
        ['Pinned', summary.pinned_count],
    ];

    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function renderScreenerRow(row) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = row.ticker;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = [
        row.asset_type || 'n/a',
        row.llm_provider || 'n/a',
        row.research_depth ? `depth ${row.research_depth}` : null,
        row.latest_date || 'no latest date',
    ].filter(Boolean).join(' · ');
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    const flags = [
        row.latest_signal || row.latest_status || 'No signal yet',
        row.has_alert_hit ? 'alert hit' : null,
        row.is_pinned ? `${row.pinned_priority || 'pinned'}${row.pinned_category ? ` · ${row.pinned_category}` : ''}` : null,
        row.annotation_label ? `annotation: ${row.annotation_label}` : null,
        row.on_watchlist ? 'watchlist' : null,
        row.in_portfolio ? 'portfolio' : null,
    ].filter(Boolean);
    signalEl.textContent = flags.join(' · ');
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    if (row.latest_status) {
        const statusEl = document.createElement('span');
        statusEl.className = `history-status status-${row.latest_status}`;
        statusEl.textContent = row.latest_status;
        actionsEl.appendChild(statusEl);
    }
    if (row.needs_attention) {
        const attentionEl = document.createElement('span');
        attentionEl.className = 'history-status status-failed';
        attentionEl.textContent = 'review';
        actionsEl.appendChild(attentionEl);
    }
    if (row.latest_run_id) {
        const runButton = document.createElement('button');
        runButton.className = 'btn-secondary';
        runButton.type = 'button';
        runButton.textContent = 'Open Run';
        runButton.addEventListener('click', () => {
            void openRunDetails(row.latest_run_id);
        });
        actionsEl.appendChild(runButton);
    }
    const tickerButton = document.createElement('button');
    tickerButton.className = 'btn-secondary';
    tickerButton.type = 'button';
    tickerButton.textContent = 'Open Ticker';
    tickerButton.addEventListener('click', () => {
        focusTicker(row.ticker);
    });
    actionsEl.appendChild(tickerButton);

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderScreener(payload) {
    const listEl = document.getElementById('screener-list');
    listEl.innerHTML = '';

    if (!payload.rows.length) {
        resetScreener('No saved candidates match the current screener filters.');
        return;
    }

    document.getElementById('screener-empty').style.display = 'none';
    document.getElementById('screener-content').style.display = '';
    renderScreenerSummary(payload.summary);
    payload.rows.forEach((row) => {
        listEl.appendChild(renderScreenerRow(row));
    });
}

async function loadScreener() {
    try {
        const params = new URLSearchParams();
        const scope = document.getElementById('screener-scope').value;
        const query = document.getElementById('screener-query').value.trim();
        const signal = document.getElementById('screener-signal-filter').value;
        const status = document.getElementById('screener-status-filter').value;
        const asset = document.getElementById('screener-asset-filter').value;
        const provider = document.getElementById('screener-provider-filter').value;
        if (scope && scope !== 'all') params.set('scope', scope);
        if (query) params.set('q', query);
        if (signal && signal !== 'all') params.set('signal', signal);
        if (status && status !== 'all') params.set('status', status);
        if (asset && asset !== 'all') params.set('asset_type', asset);
        if (provider && provider !== 'all') params.set('provider', provider);
        const path = params.toString() ? `/api/screener?${params.toString()}` : '/api/screener';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderScreener(await resp.json());
    } catch (e) {
        resetScreener(`Failed to load screener: ${e.message}`);
    }
}

function updateNotificationBadge(unreadCount) {
    const badge = document.getElementById('notifications-unread-badge');
    badge.textContent = String(unreadCount);
    badge.style.display = unreadCount > 0 ? '' : 'none';
}

async function toggleDesktopNotifications() {
    if (!notificationApiSupported()) {
        alert('Desktop alerts are unavailable in this browser.');
        return;
    }

    if (desktopNotificationsEnabled()) {
        setDesktopNotificationsEnabled(false);
        desktopNotificationsPrimed = false;
        updateDesktopNotificationControls();
        appendLog('Disabled desktop alerts.');
        return;
    }

    if (Notification.permission === 'denied') {
        alert('Browser notification permission is blocked. Update your browser settings to enable desktop alerts.');
        updateDesktopNotificationControls();
        return;
    }

    let permission = Notification.permission;
    if (permission !== 'granted') {
        permission = await Notification.requestPermission();
    }

    if (permission === 'granted') {
        setDesktopNotificationsEnabled(true);
        desktopNotificationsPrimed = false;
        updateDesktopNotificationControls();
        appendLog('Enabled desktop alerts.');
        void loadNotifications();
        return;
    }

    updateDesktopNotificationControls();
    alert('Desktop notification permission was not granted.');
}

function maybeSendDesktopNotifications(payload) {
    if (
        !notificationApiSupported()
        || !desktopNotificationsEnabled()
        || Notification.permission !== 'granted'
    ) {
        return;
    }

    const unreadIds = (payload.items || [])
        .filter((item) => item && item.is_read === false)
        .map((item) => item.id);
    if (!desktopNotificationsPrimed) {
        rememberSeenDesktopNotifications(unreadIds);
        desktopNotificationsPrimed = true;
        return;
    }

    const seen = new Set(readSeenDesktopNotificationIds());
    const freshItems = (payload.items || []).filter((item) => item && item.is_read === false && !seen.has(item.id));
    if (!freshItems.length) {
        return;
    }

    rememberSeenDesktopNotifications(freshItems.map((item) => item.id));
    if (document.visibilityState === 'visible' && document.hasFocus && document.hasFocus()) {
        return;
    }

    freshItems.slice(0, 3).forEach((item) => {
        const notification = new Notification(item.title, {
            body: item.message,
            tag: item.id,
            icon: '/static/icons/app-icon.svg',
        });
        notification.onclick = () => {
            window.focus();
            if (item.target_url) {
                window.location.assign(item.target_url);
            }
            notification.close();
        };
    });
}

function resetNotifications(message = 'Run results, alert hits, and due actions will appear here as in-app notifications.') {
    document.getElementById('notifications-empty').textContent = message;
    document.getElementById('notifications-empty').style.display = '';
    document.getElementById('notifications-list').innerHTML = '';
    updateNotificationBadge(0);
}

function renderNotificationItem(item) {
    const row = document.createElement('div');
    row.className = `history-item notification-item${item.is_read ? '' : ' notification-unread'}`;

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';

    const topEl = document.createElement('div');
    topEl.className = 'notification-meta';

    const chipEl = document.createElement('span');
    chipEl.className = `notification-chip severity-${item.severity}`;
    chipEl.textContent = item.kind;

    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = item.title;

    topEl.appendChild(chipEl);
    topEl.appendChild(titleEl);

    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = [
        new Date(item.created_at).toLocaleString(),
        item.member ? `for @${item.member}` : null,
    ].filter(Boolean).join(' · ');

    const messageEl = document.createElement('div');
    messageEl.className = 'history-signal';
    messageEl.textContent = item.message;

    metaEl.appendChild(topEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(messageEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';

    if (item.run_id || item.ticker || item.target_url) {
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = item.run_id ? 'Open Run' : 'Open';
        openButton.addEventListener('click', async () => {
            if (!item.is_read) {
                await markNotificationRead(item.id, false);
            }
            if (item.run_id) {
                await openRunDetails(item.run_id);
                return;
            }
            if (item.ticker) {
                focusTicker(item.ticker);
                return;
            }
            if (item.target_url) {
                window.location.assign(item.target_url);
            }
        });
        actionsEl.appendChild(openButton);
    }

    if (!item.is_read) {
        const readButton = document.createElement('button');
        readButton.className = 'btn-secondary';
        readButton.type = 'button';
        readButton.textContent = 'Mark Read';
        readButton.addEventListener('click', () => {
            void markNotificationRead(item.id, true);
        });
        actionsEl.appendChild(readButton);
    }

    row.appendChild(metaEl);
    row.appendChild(actionsEl);
    return row;
}

function renderNotifications(payload) {
    const emptyEl = document.getElementById('notifications-empty');
    const listEl = document.getElementById('notifications-list');
    updateNotificationBadge(payload.unread_count);
    updateDesktopNotificationControls();
    listEl.innerHTML = '';

    if (!payload.items.length) {
        const emptyMessage = payload.unread_only
            ? 'No unread notifications right now.'
            : 'Run results, alert hits, and due actions will appear here as in-app notifications.';
        resetNotifications(emptyMessage);
        return;
    }

    emptyEl.style.display = 'none';
    payload.items.forEach((item) => {
        listEl.appendChild(renderNotificationItem(item));
    });
}

async function loadNotifications() {
    try {
        const unreadOnly = document.getElementById('notifications-unread-only').checked;
        const member = document.getElementById('notifications-member-filter').value
            || (currentMemberScopedView() ? (getCurrentMember()?.name || '') : '');
        const kind = document.getElementById('notifications-kind-filter').value;
        const severity = document.getElementById('notifications-severity-filter').value;
        const params = new URLSearchParams();
        if (unreadOnly) params.set('unread_only', 'true');
        if (member) params.set('member', member);
        if (kind && kind !== 'all') params.set('kind', kind);
        if (severity && severity !== 'all') params.set('severity', severity);
        const path = params.toString() ? `/api/notifications?${params.toString()}` : '/api/notifications';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        const payload = await resp.json();
        renderNotifications(payload);
        maybeSendDesktopNotifications(payload);
    } catch (e) {
        resetNotifications(`Failed to load notifications: ${e.message}`);
    }
}

async function markNotificationRead(notificationId, reload = true) {
    try {
        const resp = await fetch(buildApiUrl(`/api/notifications/${encodeURIComponent(notificationId)}/read`), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        updateNotificationBadge(payload.unread_count);
        if (reload) {
            await loadNotifications();
        }
    } catch (e) {
        alert(`Failed to update notification: ${e.message}`);
    }
}

async function markAllNotificationsRead() {
    try {
        const params = new URLSearchParams();
        const member = document.getElementById('notifications-member-filter').value;
        const kind = document.getElementById('notifications-kind-filter').value;
        const severity = document.getElementById('notifications-severity-filter').value;
        if (member) params.set('member', member);
        if (kind && kind !== 'all') params.set('kind', kind);
        if (severity && severity !== 'all') params.set('severity', severity);
        const path = params.toString() ? `/api/notifications/read-all?${params.toString()}` : '/api/notifications/read-all';
        const resp = await fetch(buildApiUrl(path), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Marked all notifications as read.');
        await loadNotifications();
    } catch (e) {
        alert(`Failed to mark notifications as read: ${e.message}`);
    }
}

function resetAutomations(message = 'Schedule daily or weekly watchlist sweeps using the current analysis settings from the form above.') {
    document.getElementById('automations-empty').textContent = message;
    document.getElementById('automations-empty').style.display = '';
    document.getElementById('automations-list').innerHTML = '';
}

function renderAutomationRule(rule) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = rule.name;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    const cadenceLabel = rule.cadence === 'weekly'
        ? `weekly · ${rule.weekday} · ${rule.time_of_day}`
        : `daily · ${rule.time_of_day}`;
    subtitleEl.textContent = `${rule.source} · ${cadenceLabel}`;
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    const bits = [
        rule.next_run_at ? `Next: ${new Date(rule.next_run_at).toLocaleString()}` : null,
        rule.last_triggered_at ? `Last: ${new Date(rule.last_triggered_at).toLocaleString()}` : null,
        `Last queued: ${rule.last_queued_count}`,
    ].filter(Boolean);
    signalEl.textContent = bits.join(' · ');
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';

    const statusEl = document.createElement('span');
    statusEl.className = `history-status ${rule.enabled ? 'status-completed' : 'status-cancelled'}`;
    statusEl.textContent = rule.enabled ? 'enabled' : 'disabled';
    actionsEl.appendChild(statusEl);

    const runButton = document.createElement('button');
    runButton.className = 'btn-secondary';
    runButton.type = 'button';
    runButton.textContent = 'Run Now';
    runButton.addEventListener('click', () => {
        void runAutomationNow(rule.id);
    });
    actionsEl.appendChild(runButton);

    const toggleButton = document.createElement('button');
    toggleButton.className = 'btn-secondary';
    toggleButton.type = 'button';
    toggleButton.textContent = rule.enabled ? 'Disable' : 'Enable';
    toggleButton.addEventListener('click', () => {
        void toggleAutomation(rule.id, !rule.enabled);
    });
    actionsEl.appendChild(toggleButton);

    const deleteButton = document.createElement('button');
    deleteButton.className = 'btn-secondary';
    deleteButton.type = 'button';
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', () => {
        void removeAutomation(rule.id);
    });
    actionsEl.appendChild(deleteButton);

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderAutomations(rules) {
    const emptyEl = document.getElementById('automations-empty');
    const listEl = document.getElementById('automations-list');
    listEl.innerHTML = '';

    if (!rules.length) {
        resetAutomations();
        return;
    }

    emptyEl.style.display = 'none';
    rules.forEach((rule) => {
        listEl.appendChild(renderAutomationRule(rule));
    });
}

async function loadAutomations() {
    try {
        const resp = await fetch(buildApiUrl('/api/automations'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderAutomations(await resp.json());
    } catch (e) {
        resetAutomations(`Failed to load automations: ${e.message}`);
    }
}

async function saveAutomation() {
    const name = document.getElementById('automation-name').value.trim();
    if (!name) {
        alert('Enter an automation name first.');
        return;
    }
    if (getSelectedAnalysts().length === 0) {
        alert('Please select at least one analyst.');
        return;
    }

    const source = document.getElementById('automation-source').value;
    const tickers = parseBatchTickers(document.getElementById('automation-tickers').value);
    if (source === 'manual' && tickers.length === 0) {
        alert('Enter at least one manual ticker for this automation.');
        return;
    }

    let analysisConfig;
    try {
        analysisConfig = buildSharedAnalysisConfig();
    } catch (e) {
        alert(e.message);
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/automations'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                name,
                enabled: document.getElementById('automation-enabled').checked,
                source,
                tickers,
                cadence: document.getElementById('automation-cadence').value,
                weekday: document.getElementById('automation-weekday').value,
                time_of_day: document.getElementById('automation-time').value,
                analysis_config: analysisConfig,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Saved automation: ${name}`);
        document.getElementById('automation-name').value = '';
        document.getElementById('automation-tickers').value = '';
        document.getElementById('automation-enabled').checked = true;
        syncAutomationFields();
        await loadAutomations();
    } catch (e) {
        alert(`Failed to save automation: ${e.message}`);
    }
}

async function toggleAutomation(ruleId, enabled) {
    try {
        const resp = await fetch(buildApiUrl(`/api/automations/${encodeURIComponent(ruleId)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ enabled }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`${enabled ? 'Enabled' : 'Disabled'} automation.`);
        await loadAutomations();
    } catch (e) {
        alert(`Failed to update automation: ${e.message}`);
    }
}

async function runAutomationNow(ruleId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/automations/${encodeURIComponent(ruleId)}/run-now`), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        appendLog(`Automation queued ${payload.created_count} run(s): ${payload.tickers.join(', ')}`);
        await loadAutomations();
        await loadRunHistory();
        await loadSystemStatus();
    } catch (e) {
        alert(`Failed to run automation: ${e.message}`);
    }
}

async function removeAutomation(ruleId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/automations/${encodeURIComponent(ruleId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed automation.');
        await loadAutomations();
    } catch (e) {
        alert(`Failed to remove automation: ${e.message}`);
    }
}

function resetDashboard(message = 'Your saved watchlist, alerts, portfolio, and recent runs will roll up into a persistent dashboard here.') {
    document.getElementById('dashboard-empty').textContent = message;
    document.getElementById('dashboard-empty').style.display = '';
    document.getElementById('dashboard-content').style.display = 'none';
    document.getElementById('dashboard-summary').innerHTML = '';
    document.getElementById('dashboard-getting-started').style.display = 'none';
    document.getElementById('dashboard-getting-started-summary').textContent = '';
    document.getElementById('dashboard-getting-started-list').innerHTML = '';
    document.getElementById('dashboard-widget-controls').style.display = '';
    document.getElementById('dashboard-grid').style.display = '';
    document.getElementById('dashboard-bullish').innerHTML = '';
    document.getElementById('dashboard-attention').innerHTML = '';
    document.getElementById('dashboard-alerts').innerHTML = '';
    document.getElementById('dashboard-portfolio').innerHTML = '';
    document.getElementById('dashboard-reviews').innerHTML = '';
    document.getElementById('dashboard-automations').innerHTML = '';
    document.getElementById('dashboard-shortcuts').innerHTML = '';
    document.getElementById('dashboard-runs').innerHTML = '';
}

function syncDashboardControls(visibleSections, sectionOrder = null) {
    const order = sectionOrder
        ? [...sectionOrder]
        : [...DASHBOARD_SECTION_IDS];
    const normalizedOrder = [
        ...order.filter((sectionId) => DASHBOARD_SECTION_IDS.includes(sectionId)),
        ...DASHBOARD_SECTION_IDS.filter((sectionId) => !order.includes(sectionId)),
    ];
    currentDashboardSectionOrder = normalizedOrder;
    const active = new Set((visibleSections && visibleSections.length) ? visibleSections : DASHBOARD_SECTION_IDS);
    const grid = document.getElementById('dashboard-grid');
    DASHBOARD_SECTION_IDS.forEach((sectionId) => {
        const checkbox = document.getElementById(`dashboard-section-${sectionId}`);
        const pane = document.getElementById(`dashboard-pane-${sectionId}`);
        const upButton = document.getElementById(`dashboard-move-up-${sectionId}`);
        const downButton = document.getElementById(`dashboard-move-down-${sectionId}`);
        if (checkbox) {
            checkbox.checked = active.has(sectionId);
        }
        if (pane) {
            pane.style.display = active.has(sectionId) ? '' : 'none';
        }
        const index = normalizedOrder.indexOf(sectionId);
        if (upButton) {
            upButton.disabled = index <= 0;
        }
        if (downButton) {
            downButton.disabled = index === -1 || index >= normalizedOrder.length - 1;
        }
    });
    if (grid) {
        normalizedOrder.forEach((sectionId) => {
            const pane = document.getElementById(`dashboard-pane-${sectionId}`);
            if (pane) {
                grid.appendChild(pane);
            }
        });
    }
}

function collectDashboardVisibleSections() {
    return DASHBOARD_SECTION_IDS.filter((sectionId) => {
        const checkbox = document.getElementById(`dashboard-section-${sectionId}`);
        return checkbox ? checkbox.checked : true;
    });
}

function collectDashboardSectionOrder() {
    return [...currentDashboardSectionOrder];
}

function dashboardLayoutIsCustomized(visibleSections, sectionOrder) {
    const sections = visibleSections || collectDashboardVisibleSections();
    const order = sectionOrder || collectDashboardSectionOrder();
    const sameVisible = sections.length === DASHBOARD_SECTION_IDS.length
        && DASHBOARD_SECTION_IDS.every((sectionId) => sections.includes(sectionId));
    const sameOrder = order.length === DASHBOARD_SECTION_IDS.length
        && DASHBOARD_SECTION_IDS.every((sectionId, index) => order[index] === sectionId);
    return !(sameVisible && sameOrder);
}

async function applyDashboardRoutePreferences(visibleSections, sectionOrder) {
    if (!visibleSections && !sectionOrder) {
        return;
    }
    const sections = visibleSections && visibleSections.length
        ? visibleSections.filter((sectionId) => DASHBOARD_SECTION_IDS.includes(sectionId))
        : DASHBOARD_SECTION_IDS;
    const order = sectionOrder && sectionOrder.length
        ? [
            ...sectionOrder.filter((sectionId) => DASHBOARD_SECTION_IDS.includes(sectionId)),
            ...DASHBOARD_SECTION_IDS.filter((sectionId) => !sectionOrder.includes(sectionId)),
        ]
        : DASHBOARD_SECTION_IDS;
    currentDashboardSectionOrder = order;
    syncDashboardControls(sections, order);
    await saveDashboardPreferences();
}

function renderDashboardSummary(summary) {
    const container = document.getElementById('dashboard-summary');
    const cards = [
        ['Generated', summary.generated_at],
        ['Watchlist', summary.watchlist_count],
        ['Bullish Focus', summary.bullish_focus_count],
        ['Needs Attention', summary.needs_attention_count],
        ['Alert Hits', summary.alert_hit_count],
        ['Portfolio Positions', summary.portfolio_position_count],
        ['Pending Reviews', summary.pending_review_count],
        ['Automations', summary.automation_count],
        ['Shortcuts', summary.saved_shortcut_count],
        ['Recent Runs', summary.recent_run_count],
    ];

    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function renderWatchlistFocusItem(entry) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = entry.ticker;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = `${entry.run_count} saved run(s)`;
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    signalEl.textContent = entry.latest_signal || entry.latest_status || 'No saved signal yet';
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = 'Open';
    openButton.addEventListener('click', () => focusTicker(entry.ticker));
    actionsEl.appendChild(openButton);

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderOperationalRunItem(run) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = `${run.ticker} · ${run.date}`;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = run.status;
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    signalEl.textContent = run.error || run.signal || 'No detail';
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = 'Open Run';
    openButton.addEventListener('click', () => void openRunDetails(run.run_id));
    actionsEl.appendChild(openButton);

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderDashboardReviewItem(review) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = review.ticker ? `${review.ticker} · ${review.date || 'n/a'}` : review.run_id;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = `${review.reviewer} · ${review.status}`;
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    signalEl.textContent = review.note || review.signal || 'Review requested.';
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = 'Open Run';
    openButton.addEventListener('click', () => void openRunDetails(review.run_id));
    actionsEl.appendChild(openButton);

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderDashboardAutomationItem(rule) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = rule.name;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = `${rule.source} · ${rule.cadence}`;
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    signalEl.textContent = rule.next_run_at
        ? `Next: ${new Date(rule.next_run_at).toLocaleString()}`
        : 'No next run scheduled';
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = 'Manage';
    openButton.addEventListener('click', () => {
        document.getElementById('automations-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    actionsEl.appendChild(openButton);

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderDashboardShortcutItem(item) {
    const row = document.createElement('div');
    row.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = item.name;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = [
        item.kind,
        item.group ? `group ${item.group}` : null,
        item.member_name ? `@${item.member_name}` : null,
    ].filter(Boolean).join(' · ');
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    const openButton = document.createElement('button');
    openButton.className = 'btn-secondary';
    openButton.type = 'button';
    openButton.textContent = item.kind === 'view' ? 'Apply' : 'Search';
    openButton.addEventListener('click', () => {
        if (item.member_id) {
            document.getElementById('current-member').value = item.member_id;
            window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, item.member_id);
            applyCurrentMemberContext();
        }
        if (item.kind === 'view' && item.url) {
            window.location.assign(item.url);
            return;
        }
        if (item.kind === 'search') {
            document.getElementById('workspace-search').value = item.query || '';
            applyWorkspaceSearchKinds(item.kinds || []);
            void runWorkspaceSearch();
        }
    });
    actionsEl.appendChild(openButton);

    row.appendChild(metaEl);
    row.appendChild(actionsEl);
    return row;
}

async function openGettingStartedTarget(targetPanel) {
    if (targetPanel === 'watchlist-panel') {
        await loadWatchlist();
    } else if (targetPanel === 'portfolio-panel') {
        await loadPortfolio();
    } else if (targetPanel === 'automations-panel') {
        await loadAutomations();
    } else if (targetPanel === 'members-panel') {
        await loadWorkspaceMembers();
    } else if (targetPanel === 'search-panel') {
        await loadSavedSearches();
        await loadSavedViews();
    }
    scrollToPanel(targetPanel);
}

function renderDashboardGettingStartedItem(item) {
    const row = document.createElement('div');
    row.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = `${item.completed ? '[Done] ' : ''}${item.title}`;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = item.description;
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    if (item.action_label && item.target_panel) {
        const button = document.createElement('button');
        button.className = 'btn-secondary';
        button.type = 'button';
        button.textContent = item.action_label;
        button.addEventListener('click', () => {
            void openGettingStartedTarget(item.target_panel);
        });
        actionsEl.appendChild(button);
    }

    row.appendChild(metaEl);
    row.appendChild(actionsEl);
    return row;
}

function renderDashboard(payload) {
    const gettingStartedWrap = document.getElementById('dashboard-getting-started');
    const gettingStartedSummary = document.getElementById('dashboard-getting-started-summary');
    const gettingStartedList = document.getElementById('dashboard-getting-started-list');
    const widgetControls = document.getElementById('dashboard-widget-controls');
    const dashboardGrid = document.getElementById('dashboard-grid');
    const bullishEl = document.getElementById('dashboard-bullish');
    const attentionEl = document.getElementById('dashboard-attention');
    const alertsEl = document.getElementById('dashboard-alerts');
    const portfolioEl = document.getElementById('dashboard-portfolio');
    const pinnedEl = document.getElementById('dashboard-pinned-actions');
    const reviewsEl = document.getElementById('dashboard-reviews');
    const automationsEl = document.getElementById('dashboard-automations');
    const shortcutsEl = document.getElementById('dashboard-shortcuts');
    const runsEl = document.getElementById('dashboard-runs');
    gettingStartedSummary.textContent = '';
    gettingStartedList.innerHTML = '';
    bullishEl.innerHTML = '';
    attentionEl.innerHTML = '';
    alertsEl.innerHTML = '';
    portfolioEl.innerHTML = '';
    pinnedEl.innerHTML = '';
    reviewsEl.innerHTML = '';
    automationsEl.innerHTML = '';
    shortcutsEl.innerHTML = '';
    runsEl.innerHTML = '';

    const hasActivityData = !(
        payload.summary.watchlist_count === 0 &&
        payload.summary.alert_hit_count === 0 &&
        payload.summary.portfolio_position_count === 0 &&
        payload.summary.pinned_action_count === 0 &&
        payload.summary.pending_review_count === 0 &&
        payload.summary.automation_count === 0 &&
        payload.summary.saved_shortcut_count === 0 &&
        payload.summary.recent_run_count === 0
    );
    const checklist = payload.getting_started || { completed_count: 0, remaining_count: 0, total_count: 0, items: [] };

    if (!hasActivityData && checklist.total_count === 0) {
        resetDashboard();
        return;
    }

    document.getElementById('dashboard-empty').style.display = 'none';
    document.getElementById('dashboard-content').style.display = '';
    renderDashboardSummary(payload.summary);
    if (checklist.total_count > 0 && checklist.remaining_count > 0) {
        gettingStartedWrap.style.display = '';
        gettingStartedSummary.textContent = `${checklist.completed_count}/${checklist.total_count} workspace foundations completed.`;
        checklist.items.forEach((item) => {
            gettingStartedList.appendChild(renderDashboardGettingStartedItem(item));
        });
    } else {
        gettingStartedWrap.style.display = 'none';
    }
    widgetControls.style.display = hasActivityData ? '' : 'none';
    dashboardGrid.style.display = hasActivityData ? '' : 'none';
    if (!hasActivityData) {
        return;
    }
    syncDashboardControls(
        payload.visible_sections || DASHBOARD_SECTION_IDS,
        payload.section_order || DASHBOARD_SECTION_IDS,
    );

    if (payload.bullish_focus.length) {
        payload.bullish_focus.forEach((entry) => bullishEl.appendChild(renderWatchlistFocusItem(entry)));
    } else {
        appendBriefingPlaceholder(bullishEl, 'No bullish focus yet.');
    }

    if (payload.needs_attention.length) {
        payload.needs_attention.forEach((entry) => attentionEl.appendChild(renderWatchlistFocusItem(entry)));
    } else {
        appendBriefingPlaceholder(attentionEl, 'Nothing urgent right now.');
    }

    if (payload.active_alerts.length) {
        payload.active_alerts.forEach((hit) => alertsEl.appendChild(renderAlertHitItem(hit)));
    } else {
        appendBriefingPlaceholder(alertsEl, 'No active alert hits.');
    }

    if (payload.portfolio_focus.length) {
        payload.portfolio_focus.forEach((position) => {
            const item = document.createElement('div');
            item.className = 'history-item';

            const metaEl = document.createElement('div');
            metaEl.className = 'history-meta';
            const titleEl = document.createElement('div');
            titleEl.className = 'history-title';
            titleEl.textContent = `${position.ticker} · qty ${position.quantity}`;
            const subtitleEl = document.createElement('div');
            subtitleEl.className = 'history-subtitle';
            subtitleEl.textContent = `Cost basis ${position.cost_basis}`;
            const signalEl = document.createElement('div');
            signalEl.className = 'history-signal';
            signalEl.textContent = position.latest_signal || position.latest_status || 'No saved signal yet';
            metaEl.appendChild(titleEl);
            metaEl.appendChild(subtitleEl);
            metaEl.appendChild(signalEl);

            const actionsEl = document.createElement('div');
            actionsEl.className = 'history-actions';
            const openButton = document.createElement('button');
            openButton.className = 'btn-secondary';
            openButton.type = 'button';
            openButton.textContent = 'Open';
            openButton.addEventListener('click', () => focusTicker(position.ticker));
            actionsEl.appendChild(openButton);

            item.appendChild(metaEl);
            item.appendChild(actionsEl);
            portfolioEl.appendChild(item);
        });
    } else {
        appendBriefingPlaceholder(portfolioEl, 'No saved positions yet.');
    }

    if (payload.pinned_actions.length) {
        payload.pinned_actions.forEach((item) => {
            const row = document.createElement('div');
            row.className = 'history-item';

            const metaEl = document.createElement('div');
            metaEl.className = 'history-meta';
            const titleEl = document.createElement('div');
            titleEl.className = 'history-title';
            titleEl.textContent = item.ticker
                ? `${item.ticker} · ${item.date || 'n/a'}`
                : item.run_id;
            const subtitleEl = document.createElement('div');
            subtitleEl.className = 'history-subtitle';
            subtitleEl.textContent = [item.category, item.priority, item.action_status, item.assignee ? `@${item.assignee}` : null].filter(Boolean).join(' · ') || 'Pinned action';
            const signalEl = document.createElement('div');
            signalEl.className = 'history-signal';
            signalEl.textContent = item.next_action || item.note || item.signal || item.status || 'No action note';
            metaEl.appendChild(titleEl);
            metaEl.appendChild(subtitleEl);
            metaEl.appendChild(signalEl);

            const actionsEl = document.createElement('div');
            actionsEl.className = 'history-actions';
            const openButton = document.createElement('button');
            openButton.className = 'btn-secondary';
            openButton.type = 'button';
            openButton.textContent = 'Open';
            openButton.addEventListener('click', () => {
                void openRunDetails(item.run_id);
            });
            actionsEl.appendChild(openButton);

            row.appendChild(metaEl);
            row.appendChild(actionsEl);
            pinnedEl.appendChild(row);
        });
    } else {
        appendBriefingPlaceholder(pinnedEl, 'No pinned actions yet.');
    }

    if (payload.pending_reviews.length) {
        payload.pending_reviews.forEach((item) => reviewsEl.appendChild(renderDashboardReviewItem(item)));
    } else {
        appendBriefingPlaceholder(reviewsEl, 'No pending reviews.');
    }

    if (payload.automations.length) {
        payload.automations.forEach((item) => automationsEl.appendChild(renderDashboardAutomationItem(item)));
    } else {
        appendBriefingPlaceholder(automationsEl, 'No enabled automations.');
    }

    if (payload.saved_shortcuts.length) {
        payload.saved_shortcuts.forEach((item) => shortcutsEl.appendChild(renderDashboardShortcutItem(item)));
    } else {
        appendBriefingPlaceholder(shortcutsEl, 'No pinned shortcuts yet.');
    }

    if (payload.operational_runs.length) {
        payload.operational_runs.forEach((run) => runsEl.appendChild(renderOperationalRunItem(run)));
    } else {
        appendBriefingPlaceholder(runsEl, 'No operational issues right now.');
    }
}

async function loadDashboard() {
    try {
        const resp = await fetch(buildApiUrl('/api/dashboard'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderDashboard(await resp.json());
    } catch (e) {
        resetDashboard(`Failed to load dashboard: ${e.message}`);
    }
}

async function saveDashboardPreferences() {
    try {
        const resp = await fetch(buildApiUrl('/api/dashboard/preferences'), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                visible_sections: collectDashboardVisibleSections(),
                section_order: collectDashboardSectionOrder(),
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const prefs = await resp.json();
        syncDashboardControls(prefs.visible_sections || DASHBOARD_SECTION_IDS);
    } catch (e) {
        alert(`Failed to save dashboard layout: ${e.message}`);
    }
}

async function resetDashboardPreferences() {
    try {
        const resp = await fetch(buildApiUrl('/api/dashboard/preferences'), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                visible_sections: DASHBOARD_SECTION_IDS,
                section_order: DASHBOARD_SECTION_IDS,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const prefs = await resp.json();
        syncDashboardControls(prefs.visible_sections || DASHBOARD_SECTION_IDS);
    } catch (e) {
        alert(`Failed to reset dashboard layout: ${e.message}`);
    }
}

async function moveDashboardSection(sectionId, delta) {
    const order = collectDashboardSectionOrder();
    const index = order.indexOf(sectionId);
    if (index === -1) return;
    const nextIndex = index + delta;
    if (nextIndex < 0 || nextIndex >= order.length) return;
    const updated = [...order];
    const [moved] = updated.splice(index, 1);
    updated.splice(nextIndex, 0, moved);
    currentDashboardSectionOrder = updated;
    syncDashboardControls(collectDashboardVisibleSections(), updated);
    await saveDashboardPreferences();
}

function resetPresets(message = 'Save the current analysis configuration so you can reuse it later with one click.') {
    currentPresets = [];
    document.getElementById('preset-empty').textContent = message;
    document.getElementById('preset-empty').style.display = '';
    document.getElementById('preset-list').innerHTML = '';
}

function buildCurrentPresetPayload() {
    return {
        ticker: document.getElementById('ticker').value.trim() || null,
        llm_provider: document.getElementById('provider').value || null,
        quick_think_model: resolveModelValue('quick-model', 'quick-model-custom'),
        deep_think_model: resolveModelValue('deep-model', 'deep-model-custom'),
        research_depth: parseInt(document.getElementById('depth').value, 10),
        output_language: document.getElementById('language').value || null,
        market_profile: document.getElementById('run-market-profile').value || null,
        max_risk_discuss_rounds: parseInt(document.getElementById('run-risk-rounds').value, 10),
        max_recur_limit: parseOptionalInt('run-max-recur', 100),
        checkpoint_enabled: document.getElementById('run-checkpoint-enabled').checked,
        benchmark_ticker: document.getElementById('run-benchmark-ticker').value.trim() || null,
        temperature: parseOptionalFloat('run-temperature'),
        backend_url: document.getElementById('run-backend-url').value.trim() || null,
        google_thinking_level: document.getElementById('run-google-thinking').value || null,
        openai_reasoning_effort: document.getElementById('run-openai-effort').value || null,
        anthropic_effort: document.getElementById('run-anthropic-effort').value || null,
    };
}

function applyPresetToForm(preset) {
    const config = preset.analysis_request || {};
    if (config.ticker) {
        document.getElementById('ticker').value = config.ticker;
        document.getElementById('asset-type-hint').textContent = detectAssetType(config.ticker) !== 'stock'
            ? `Detected: ${detectAssetType(config.ticker)}`
            : '';
        void loadTickerHome(config.ticker);
    }
    if (config.llm_provider && getProvider(config.llm_provider)) {
        document.getElementById('provider').value = config.llm_provider;
        updateModelDropdowns(config.quick_think_model || null, config.deep_think_model || null);
    }
    if (config.research_depth) {
        document.getElementById('depth').value = String(config.research_depth);
    }
    if (config.output_language) {
        document.getElementById('language').value = config.output_language;
    }
    if (config.market_profile) {
        document.getElementById('run-market-profile').value = config.market_profile;
    }
    if (config.max_risk_discuss_rounds) {
        document.getElementById('run-risk-rounds').value = String(config.max_risk_discuss_rounds);
    }
    if (config.max_recur_limit !== undefined && config.max_recur_limit !== null) {
        document.getElementById('run-max-recur').value = String(config.max_recur_limit);
    }
    document.getElementById('run-checkpoint-enabled').checked = Boolean(config.checkpoint_enabled);
    document.getElementById('run-benchmark-ticker').value = config.benchmark_ticker || '';
    document.getElementById('run-temperature').value = config.temperature ?? '';
    document.getElementById('run-backend-url').value = config.backend_url || '';
    document.getElementById('run-google-thinking').value = config.google_thinking_level || '';
    document.getElementById('run-openai-effort').value = config.openai_reasoning_effort || '';
    document.getElementById('run-anthropic-effort').value = config.anthropic_effort || '';
}

function renderPresets(items) {
    currentPresets = items;
    const emptyEl = document.getElementById('preset-empty');
    const listEl = document.getElementById('preset-list');
    listEl.innerHTML = '';

    if (!items.length) {
        resetPresets();
        return;
    }

    emptyEl.style.display = 'none';
    items.forEach((preset) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = preset.name;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            preset.analysis_request.ticker,
            preset.analysis_request.llm_provider,
            preset.analysis_request.market_profile,
        ].filter(Boolean).join(' · ') || 'Saved analysis configuration';
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const applyButton = document.createElement('button');
        applyButton.className = 'btn-secondary';
        applyButton.type = 'button';
        applyButton.textContent = 'Apply';
        applyButton.addEventListener('click', () => {
            applyPresetToForm(preset);
            appendLog(`Applied preset: ${preset.name}`);
        });
        const renameButton = document.createElement('button');
        renameButton.className = 'btn-secondary';
        renameButton.type = 'button';
        renameButton.textContent = 'Rename';
        renameButton.addEventListener('click', () => {
            void renamePreset(preset.id, preset.name);
        });
        const duplicateButton = document.createElement('button');
        duplicateButton.className = 'btn-secondary';
        duplicateButton.type = 'button';
        duplicateButton.textContent = 'Duplicate';
        duplicateButton.addEventListener('click', () => {
            void duplicatePreset(preset.id);
        });
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removePreset(preset.id);
        });
        actionsEl.appendChild(applyButton);
        actionsEl.appendChild(renameButton);
        actionsEl.appendChild(duplicateButton);
        actionsEl.appendChild(removeButton);

        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        listEl.appendChild(item);
    });
}

async function loadPresets() {
    try {
        const resp = await fetch(buildApiUrl('/api/presets'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderPresets(await resp.json());
    } catch (e) {
        resetPresets(`Failed to load presets: ${e.message}`);
    }
}

async function saveCurrentPreset() {
    const name = document.getElementById('preset-name').value.trim();
    if (!name) {
        alert('Enter a preset name first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/presets'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                name,
                analysis_request: buildCurrentPresetPayload(),
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        document.getElementById('preset-name').value = '';
        appendLog(`Saved preset: ${name}`);
        await loadPresets();
    } catch (e) {
        alert(`Failed to save preset: ${e.message}`);
    }
}

async function renamePreset(presetId, currentName) {
    const nextName = window.prompt('Rename preset', currentName || '');
    if (nextName === null) return;
    const trimmed = nextName.trim();
    if (!trimmed) {
        alert('Preset name cannot be blank.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/presets/${encodeURIComponent(presetId)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ name: trimmed }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        await loadPresets();
    } catch (e) {
        alert(`Failed to rename preset: ${e.message}`);
    }
}

async function duplicatePreset(presetId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/presets/${encodeURIComponent(presetId)}/duplicate`), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Duplicated preset.');
        await loadPresets();
    } catch (e) {
        alert(`Failed to duplicate preset: ${e.message}`);
    }
}

async function removePreset(presetId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/presets/${encodeURIComponent(presetId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed preset.');
        await loadPresets();
    } catch (e) {
        alert(`Failed to remove preset: ${e.message}`);
    }
}

function resetTimeline(message = 'Saved runs and workspace actions will appear here in reverse chronological order.') {
    document.getElementById('timeline-empty').textContent = message;
    document.getElementById('timeline-empty').style.display = '';
    document.getElementById('timeline-list').innerHTML = '';
}

function collectTimelineKinds() {
    return TIMELINE_KIND_DEFINITIONS
        .filter(([id]) => document.getElementById(id).checked)
        .map(([, kind]) => kind);
}

function renderTimelineEventItem(event) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = event.title;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = `${event.kind} · ${event.occurred_at}`;
    const detailEl = document.createElement('div');
    detailEl.className = 'history-signal';
    detailEl.textContent = event.detail;
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(detailEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    if (event.run_id) {
        const openRunButton = document.createElement('button');
        openRunButton.className = 'btn-secondary';
        openRunButton.type = 'button';
        openRunButton.textContent = 'Open Run';
        openRunButton.addEventListener('click', () => void openRunDetails(event.run_id));
        actionsEl.appendChild(openRunButton);
    } else if (event.ticker) {
        const openTickerButton = document.createElement('button');
        openTickerButton.className = 'btn-secondary';
        openTickerButton.type = 'button';
        openTickerButton.textContent = 'Open';
        openTickerButton.addEventListener('click', () => focusTicker(event.ticker));
        actionsEl.appendChild(openTickerButton);
    }

    item.appendChild(metaEl);
    item.appendChild(actionsEl);
    return item;
}

function renderWorkspaceTimeline(payload) {
    const emptyEl = document.getElementById('timeline-empty');
    const listEl = document.getElementById('timeline-list');
    listEl.innerHTML = '';

    if (!payload.events.length) {
        resetTimeline();
        return;
    }

    emptyEl.style.display = 'none';
    payload.events.forEach((event) => {
        listEl.appendChild(renderTimelineEventItem(event));
    });
}

async function loadTimeline() {
    try {
        const kinds = collectTimelineKinds();
        const params = new URLSearchParams();
        if (kinds.length > 0 && kinds.length < TIMELINE_KIND_DEFINITIONS.length) {
            params.set('kinds', kinds.join(','));
        }
        const path = params.toString() ? `/api/timeline?${params.toString()}` : '/api/timeline';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderWorkspaceTimeline(await resp.json());
    } catch (e) {
        resetTimeline(`Failed to load timeline: ${e.message}`);
    }
}

function resetCalendar(message = 'Workspace events will be grouped by day here.') {
    document.getElementById('calendar-empty').textContent = message;
    document.getElementById('calendar-empty').style.display = '';
    document.getElementById('calendar-list').innerHTML = '';
}

function renderWorkspaceCalendar(payload) {
    const emptyEl = document.getElementById('calendar-empty');
    const listEl = document.getElementById('calendar-list');
    listEl.innerHTML = '';

    if (!payload.days.length) {
        resetCalendar();
        return;
    }

    emptyEl.style.display = 'none';
    payload.days.forEach((day) => {
        const section = document.createElement('div');
        section.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = day.date;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = `${day.events.length} event(s)`;
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);

        const detailEl = document.createElement('div');
        detailEl.className = 'history-signal';
        detailEl.textContent = day.events.map((event) => `${event.kind}: ${event.title}`).join(' · ');
        metaEl.appendChild(detailEl);

        section.appendChild(metaEl);
        listEl.appendChild(section);
    });
}

async function loadCalendar() {
    try {
        const resp = await fetch(buildApiUrl('/api/calendar'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderWorkspaceCalendar(await resp.json());
    } catch (e) {
        resetCalendar(`Failed to load calendar: ${e.message}`);
    }
}

function resetWorkspaceSearch(message = 'Search across your saved workspace context from one place.') {
    document.getElementById('search-empty').textContent = message;
    document.getElementById('search-empty').style.display = '';
    document.getElementById('search-results').innerHTML = '';
}

function collectWorkspaceSearchKinds() {
    return WORKSPACE_SEARCH_KIND_DEFINITIONS
        .filter(([id]) => document.getElementById(id).checked)
        .map(([, kind]) => kind);
}

function applyWorkspaceSearchKinds(kinds) {
    const active = new Set((kinds || []).map((kind) => String(kind).toLowerCase()));
    WORKSPACE_SEARCH_KIND_DEFINITIONS.forEach(([id, kind]) => {
        document.getElementById(id).checked = active.size === 0 || active.has(kind);
    });
}

function applySavedViewItem(item) {
    rememberRecentlyViewedItem({
        kind: 'view',
        id: item.id,
        title: item.name,
        subtitle: item.group || 'Saved View',
        url: item.url,
        visible_panels: item.visible_panels,
        member_id: item.member_id,
        member_name: item.member_name,
    });
    loadRecentlyViewed();
    if (item.member_id) {
        document.getElementById('current-member').value = item.member_id;
        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, item.member_id);
        applyCurrentMemberContext();
    }
    applyPanelVisibility(item.visible_panels && item.visible_panels.length ? item.visible_panels : PANEL_VISIBILITY_IDS);
    if (item.url) {
        window.location.assign(item.url);
    }
}

function renderSavedViewCard(item, { isDefaultHome = false } = {}) {
    const row = document.createElement('div');
    row.className = 'saved-view-card';

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    const titleEl = document.createElement('div');
    titleEl.className = 'history-title';
    titleEl.textContent = `${item.pinned ? '[Pinned] ' : ''}${isDefaultHome ? '[Home] ' : ''}${item.archived ? '[Archived] ' : ''}${item.name}`;
    const subtitleEl = document.createElement('div');
    subtitleEl.className = 'history-subtitle';
    subtitleEl.textContent = [
        item.group ? `group ${item.group}` : null,
        item.member_name ? `@${item.member_name}` : null,
        item.visible_panels && item.visible_panels.length ? `${item.visible_panels.length} panels` : null,
    ].filter(Boolean).join(' · ') || 'Saved workspace view';
    const signalEl = document.createElement('div');
    signalEl.className = 'history-signal';
    signalEl.textContent = item.url || 'No route stored';
    metaEl.appendChild(titleEl);
    metaEl.appendChild(subtitleEl);
    metaEl.appendChild(signalEl);

    const actionsEl = document.createElement('div');
    actionsEl.className = 'history-actions';
    const applyButton = document.createElement('button');
    applyButton.className = 'btn-secondary';
    applyButton.type = 'button';
    applyButton.textContent = 'Apply';
    applyButton.addEventListener('click', () => {
        applySavedViewItem(item);
    });
    const renameButton = document.createElement('button');
    renameButton.className = 'btn-secondary';
    renameButton.type = 'button';
    renameButton.textContent = 'Rename';
    renameButton.addEventListener('click', () => {
        void renameSavedView(item.id, item.name);
    });
    const duplicateButton = document.createElement('button');
    duplicateButton.className = 'btn-secondary';
    duplicateButton.type = 'button';
    duplicateButton.textContent = 'Duplicate';
    duplicateButton.addEventListener('click', () => {
        void duplicateSavedView(item.id);
    });
    const pinButton = document.createElement('button');
    pinButton.className = 'btn-secondary';
    pinButton.type = 'button';
    pinButton.textContent = item.pinned ? 'Unpin' : 'Pin';
    pinButton.addEventListener('click', () => {
        void updateSavedView(item.id, { pinned: !item.pinned });
    });
    const archiveButton = document.createElement('button');
    archiveButton.className = 'btn-secondary';
    archiveButton.type = 'button';
    archiveButton.textContent = item.archived ? 'Restore' : 'Archive';
    archiveButton.addEventListener('click', () => {
        void updateSavedView(item.id, { archived: !item.archived });
    });
    const homeButton = document.createElement('button');
    homeButton.className = 'btn-secondary';
    homeButton.type = 'button';
    homeButton.textContent = isDefaultHome ? 'Clear Home' : 'Set Home';
    homeButton.addEventListener('click', () => {
        void setDefaultHomeSavedView(isDefaultHome ? null : item.id);
    });
    const removeButton = document.createElement('button');
    removeButton.className = 'btn-secondary';
    removeButton.type = 'button';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => {
        void removeSavedView(item.id);
    });
    actionsEl.appendChild(applyButton);
    actionsEl.appendChild(renameButton);
    actionsEl.appendChild(duplicateButton);
    actionsEl.appendChild(pinButton);
    actionsEl.appendChild(archiveButton);
    actionsEl.appendChild(homeButton);
    actionsEl.appendChild(removeButton);

    row.appendChild(metaEl);
    row.appendChild(actionsEl);
    return row;
}

function renderWorkspaceSearchResults(payload) {
    const emptyEl = document.getElementById('search-empty');
    const listEl = document.getElementById('search-results');
    listEl.innerHTML = '';

    if (!payload.results.length) {
        resetWorkspaceSearch(`No matches found for "${payload.query}".`);
        return;
    }

    emptyEl.style.display = 'none';
    payload.results.forEach((result) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = result.title;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = `${result.kind} · ${result.subtitle}`;
        const excerptEl = document.createElement('div');
        excerptEl.className = 'history-signal';
        excerptEl.textContent = result.excerpt;
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(excerptEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = (
            result.kind === 'preset'
            || result.kind === 'search'
            || result.kind === 'view'
        ) ? 'Apply'
            : result.kind === 'member' ? 'Open Member'
                : result.kind === 'share' ? 'Open Share'
                    : 'Open';
        openButton.addEventListener('click', () => {
            if ((result.kind === 'run' || result.kind === 'comment' || result.kind === 'review') && result.run_id) {
                void openRunDetails(result.run_id);
                return;
            }
            if (result.kind === 'preset') {
                const preset = currentPresets.find((item) => item.id === result.entity_id);
                if (preset) {
                    applyPresetToForm(preset);
                    appendLog(`Applied preset: ${preset.name}`);
                }
                return;
            }
            if (result.kind === 'search') {
                const savedSearch = currentSavedSearches.find((item) => item.id === result.entity_id);
                if (savedSearch) {
                    if (savedSearch.member_id) {
                        document.getElementById('current-member').value = savedSearch.member_id;
                        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, savedSearch.member_id);
                        applyCurrentMemberContext();
                    }
                    document.getElementById('workspace-search').value = savedSearch.query || '';
                    applyWorkspaceSearchKinds(savedSearch.kinds || []);
                    void runWorkspaceSearch();
                }
                return;
            }
            if (result.kind === 'view') {
                const savedView = currentSavedViews.find((item) => item.id === result.entity_id);
                if (savedView) {
                    applySavedViewItem(savedView);
                }
                return;
            }
            if (result.kind === 'member') {
                const member = currentWorkspaceMembers.find((item) => item.id === result.entity_id);
                if (member) {
                    currentMemberWorkspaceId = member.id;
                    document.getElementById('current-member').value = member.id;
                    window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, member.id);
                    populateMemberFilterOptions(member.id);
                    applyCurrentMemberContext();
                    document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
                    void loadMemberWorkspace();
                }
                return;
            }
            if (result.kind === 'share') {
                const shared = currentPublicShares.find((item) => item.share_id === result.entity_id);
                const url = shared ? shared.url : `/shared/${encodeURIComponent(result.entity_id)}`;
                window.open(url, '_blank', 'noopener');
                return;
            }
            if (result.ticker) {
                focusTicker(result.ticker);
            }
        });
        actionsEl.appendChild(openButton);

        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        listEl.appendChild(item);
    });
}

async function runWorkspaceSearch() {
    const query = document.getElementById('workspace-search').value.trim();
    const kinds = collectWorkspaceSearchKinds();
    if (!query) {
        resetWorkspaceSearch();
        return;
    }

    try {
        const params = new URLSearchParams();
        params.set('q', query);
        if (kinds.length > 0 && kinds.length < WORKSPACE_SEARCH_KIND_DEFINITIONS.length) {
            params.set('kinds', kinds.join(','));
        }
        const resp = await fetch(buildApiUrl(`/api/search?${params.toString()}`));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderWorkspaceSearchResults(await resp.json());
    } catch (e) {
        resetWorkspaceSearch(`Failed to search workspace: ${e.message}`);
    }
}

function renderSavedViews(items) {
    currentSavedViews = items;
    const container = document.getElementById('saved-views-list');
    container.innerHTML = '';
    const displayMode = document.getElementById('saved-view-display-mode').value || 'gallery';
    const groupFilter = document.getElementById('saved-view-filter-group').value.trim().toLowerCase();
    const statusFilter = document.getElementById('saved-view-filter-status').value;
    const pinnedOnly = document.getElementById('saved-view-filter-pinned').checked;
    const filteredItems = items.filter((item) => {
        if (pinnedOnly && !item.pinned) return false;
        if (groupFilter && !(item.group || '').toLowerCase().includes(groupFilter)) return false;
        if (statusFilter === 'active' && item.archived) return false;
        if (statusFilter === 'archived' && !item.archived) return false;
        return true;
    });
    if (!filteredItems.length) {
        return;
    }

    container.className = displayMode === 'gallery' ? 'saved-view-gallery' : 'history-list';

    filteredItems.forEach((item) => {
        const isDefaultHome = currentSettings?.workspace?.default_home_view === 'saved-view'
            && currentSettings?.workspace?.default_saved_view_id === item.id;
        if (displayMode === 'gallery') {
            container.appendChild(renderSavedViewCard(item, { isDefaultHome }));
            return;
        }
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = `${item.pinned ? '[Pinned] ' : ''}${isDefaultHome ? '[Home] ' : ''}${item.archived ? '[Archived] ' : ''}${item.name}`;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            item.group ? `group ${item.group}` : null,
            item.visible_panels && item.visible_panels.length
                ? `${item.url} · panels ${item.visible_panels.length}`
                : item.url,
            item.member_name ? `@${item.member_name}` : null,
        ].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const applyButton = document.createElement('button');
        applyButton.className = 'btn-secondary';
        applyButton.type = 'button';
        applyButton.textContent = 'Apply';
        applyButton.addEventListener('click', () => {
            applySavedViewItem(item);
        });
        const renameButton = document.createElement('button');
        renameButton.className = 'btn-secondary';
        renameButton.type = 'button';
        renameButton.textContent = 'Rename';
        renameButton.addEventListener('click', () => {
            void renameSavedView(item.id, item.name);
        });
        const duplicateButton = document.createElement('button');
        duplicateButton.className = 'btn-secondary';
        duplicateButton.type = 'button';
        duplicateButton.textContent = 'Duplicate';
        duplicateButton.addEventListener('click', () => {
            void duplicateSavedView(item.id);
        });
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removeSavedView(item.id);
        });
        const pinButton = document.createElement('button');
        pinButton.className = 'btn-secondary';
        pinButton.type = 'button';
        pinButton.textContent = item.pinned ? 'Unpin' : 'Pin';
        pinButton.addEventListener('click', () => {
            void updateSavedView(item.id, { pinned: !item.pinned });
        });
        const groupButton = document.createElement('button');
        groupButton.className = 'btn-secondary';
        groupButton.type = 'button';
        groupButton.textContent = 'Set Group';
        groupButton.addEventListener('click', () => {
            const nextGroup = window.prompt('Set view group', item.group || '');
            if (nextGroup === null) return;
            void updateSavedView(item.id, { group: nextGroup.trim() || null });
        });
        const archiveButton = document.createElement('button');
        archiveButton.className = 'btn-secondary';
        archiveButton.type = 'button';
        archiveButton.textContent = item.archived ? 'Restore' : 'Archive';
        archiveButton.addEventListener('click', () => {
            void updateSavedView(item.id, { archived: !item.archived });
        });
        const homeButton = document.createElement('button');
        homeButton.className = 'btn-secondary';
        homeButton.type = 'button';
        homeButton.textContent = isDefaultHome ? 'Clear Home' : 'Set Home';
        homeButton.addEventListener('click', () => {
            void setDefaultHomeSavedView(isDefaultHome ? null : item.id);
        });
        actionsEl.appendChild(applyButton);
        actionsEl.appendChild(renameButton);
        actionsEl.appendChild(duplicateButton);
        actionsEl.appendChild(pinButton);
        actionsEl.appendChild(groupButton);
        actionsEl.appendChild(archiveButton);
        actionsEl.appendChild(homeButton);
        actionsEl.appendChild(removeButton);
        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

async function loadSavedViews() {
    try {
        const resp = await fetch(buildApiUrl('/api/views'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderSavedViews(await resp.json());
    } catch {
        currentSavedViews = [];
        document.getElementById('saved-views-list').innerHTML = '';
    }
}

async function renameSavedView(viewId, currentName) {
    const nextName = window.prompt('Rename saved view', currentName || '');
    if (nextName === null) return;
    const trimmed = nextName.trim();
    if (!trimmed) {
        alert('Saved view name cannot be blank.');
        return;
    }
    try {
        const resp = await fetch(buildApiUrl(`/api/views/${encodeURIComponent(viewId)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ name: trimmed }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        await loadSavedViews();
    } catch (e) {
        alert(`Failed to rename view: ${e.message}`);
    }
}

async function duplicateSavedView(viewId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/views/${encodeURIComponent(viewId)}/duplicate`), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Duplicated saved view.');
        await loadSavedViews();
    } catch (e) {
        alert(`Failed to duplicate view: ${e.message}`);
    }
}

function resetPublicRunShares(message = 'Public read-only run snapshots will appear here after you share a result.') {
    currentPublicShares = [];
    document.getElementById('public-shares-empty').textContent = message;
    document.getElementById('public-shares-empty').style.display = '';
    document.getElementById('public-shares-list').innerHTML = '';
}

function renderPublicRunShares(items) {
    currentPublicShares = items;
    const emptyEl = document.getElementById('public-shares-empty');
    const listEl = document.getElementById('public-shares-list');
    listEl.innerHTML = '';

    if (!items.length) {
        resetPublicRunShares();
        return;
    }

    emptyEl.style.display = 'none';
    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.share_title || `${item.ticker} · ${item.date}`;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            item.status,
            `shared ${item.created_at}`,
            `views ${item.view_count || 0}`,
            item.expires_at ? `expires ${item.expires_at}` : 'no expiry',
            item.last_viewed_at ? `last viewed ${item.last_viewed_at}` : null,
        ].filter(Boolean).join(' · ');
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = item.share_summary || item.signal || 'Shared read-only snapshot';
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const copyButton = document.createElement('button');
        copyButton.className = 'btn-secondary';
        copyButton.type = 'button';
        copyButton.textContent = 'Copy Link';
        copyButton.addEventListener('click', async () => {
            await copyToClipboard(new URL(item.url, window.location.origin).toString());
            appendLog('Copied public run snapshot link.');
        });
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open';
        openButton.addEventListener('click', () => {
            window.open(item.url, '_blank', 'noopener');
        });
        const revokeButton = document.createElement('button');
        revokeButton.className = 'btn-secondary';
        revokeButton.type = 'button';
        revokeButton.textContent = 'Revoke';
        revokeButton.addEventListener('click', () => {
            void revokePublicRunShareByRunId(item.run_id);
        });
        const expiryButton = document.createElement('button');
        expiryButton.className = 'btn-secondary';
        expiryButton.type = 'button';
        expiryButton.textContent = 'Set Expiry';
        expiryButton.addEventListener('click', () => {
            const nextDays = window.prompt('Set public snapshot expiry in days', '7');
            if (nextDays === null) return;
            const parsed = Number.parseInt(nextDays, 10);
            if (!Number.isFinite(parsed) || parsed <= 0) {
                alert('Enter a positive whole number of days.');
                return;
            }
            void updatePublicRunShareExpiry(item.run_id, parsed);
        });
        const clearExpiryButton = document.createElement('button');
        clearExpiryButton.className = 'btn-secondary';
        clearExpiryButton.type = 'button';
        clearExpiryButton.textContent = 'Clear Expiry';
        clearExpiryButton.addEventListener('click', () => {
            void updatePublicRunShareExpiry(item.run_id, null);
        });
        const titleButton = document.createElement('button');
        titleButton.className = 'btn-secondary';
        titleButton.type = 'button';
        titleButton.textContent = 'Set Title';
        titleButton.addEventListener('click', () => {
            const next = window.prompt('Set public snapshot title', item.share_title || '');
            if (next === null) return;
            void updatePublicRunSharePresentation(item.run_id, { share_title: next.trim() || null });
        });
        const summaryButton = document.createElement('button');
        summaryButton.className = 'btn-secondary';
        summaryButton.type = 'button';
        summaryButton.textContent = 'Set Summary';
        summaryButton.addEventListener('click', () => {
            const next = window.prompt('Set public snapshot summary', item.share_summary || '');
            if (next === null) return;
            void updatePublicRunSharePresentation(item.run_id, { share_summary: next.trim() || null });
        });
        actionsEl.appendChild(copyButton);
        actionsEl.appendChild(openButton);
        actionsEl.appendChild(expiryButton);
        actionsEl.appendChild(clearExpiryButton);
        actionsEl.appendChild(titleButton);
        actionsEl.appendChild(summaryButton);
        actionsEl.appendChild(revokeButton);

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        listEl.appendChild(row);
    });
}

async function loadPublicRunShares() {
    try {
        const params = new URLSearchParams();
        const query = document.getElementById('public-shares-query').value.trim();
        const availability = document.getElementById('public-shares-availability-filter').value;
        if (query) params.set('q', query);
        if (availability && availability !== 'all') params.set('availability', availability);
        const path = params.toString() ? `/api/public-shares?${params.toString()}` : '/api/public-shares';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderPublicRunShares(await resp.json());
    } catch (e) {
        resetPublicRunShares(`Failed to load shared snapshots: ${e.message}`);
    }
}

async function saveCurrentView() {
    const name = document.getElementById('saved-view-name').value.trim();
    if (!name) {
        alert('Enter a saved view name first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/views'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                name,
                url: buildCurrentViewUrl(),
                visible_panels: collectVisiblePanels(),
                group: document.getElementById('saved-view-group').value.trim() || null,
                pinned: document.getElementById('saved-view-pinned').checked,
                member_id: getCurrentMemberId(),
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        document.getElementById('saved-view-name').value = '';
        document.getElementById('saved-view-group').value = '';
        document.getElementById('saved-view-pinned').checked = false;
        appendLog(`Saved view: ${name}`);
        await loadSavedViews();
    } catch (e) {
        alert(`Failed to save view: ${e.message}`);
    }
}

async function removeSavedView(viewId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/views/${encodeURIComponent(viewId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        if (currentSettings?.workspace?.default_saved_view_id === viewId) {
            await updateWorkspaceSettingsPatch({ default_home_view: 'auto', default_saved_view_id: null });
        }
        appendLog('Removed saved view.');
        await loadSavedViews();
    } catch (e) {
        alert(`Failed to remove view: ${e.message}`);
    }
}

async function setDefaultHomeSavedView(viewId) {
    try {
        await updateWorkspaceSettingsPatch({
            default_home_view: viewId ? 'saved-view' : 'auto',
            default_saved_view_id: viewId || null,
        });
        await loadSavedViews();
    } catch (e) {
        alert(`Failed to update default home: ${e.message}`);
    }
}

async function updateSavedView(viewId, body) {
    try {
        const resp = await fetch(buildApiUrl(`/api/views/${encodeURIComponent(viewId)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        await loadSavedViews();
    } catch (e) {
        alert(`Failed to update view: ${e.message}`);
    }
}

function renderSavedSearches(items) {
    currentSavedSearches = items;
    const container = document.getElementById('saved-searches-list');
    container.innerHTML = '';

    const groupFilter = document.getElementById('saved-search-filter-group').value.trim().toLowerCase();
    const statusFilter = document.getElementById('saved-search-filter-status').value;
    const pinnedOnly = document.getElementById('saved-search-filter-pinned').checked;
    const filteredItems = items.filter((item) => {
        if (pinnedOnly && !item.pinned) return false;
        if (groupFilter && !(item.group || '').toLowerCase().includes(groupFilter)) return false;
        if (statusFilter === 'active' && item.archived) return false;
        if (statusFilter === 'archived' && !item.archived) return false;
        return true;
    });

    if (!filteredItems.length) {
        return;
    }

    filteredItems.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = `${item.pinned ? '[Pinned] ' : ''}${item.archived ? '[Archived] ' : ''}${item.name}`;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            item.group ? `group ${item.group}` : null,
            item.kinds && item.kinds.length
                ? `${item.query} · ${item.kinds.join(', ')}`
                : item.query,
            item.member_name ? `@${item.member_name}` : null,
        ].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const applyButton = document.createElement('button');
        applyButton.className = 'btn-secondary';
        applyButton.type = 'button';
        applyButton.textContent = 'Apply';
        applyButton.addEventListener('click', () => {
            if (item.member_id) {
                document.getElementById('current-member').value = item.member_id;
                window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, item.member_id);
                applyCurrentMemberContext();
            }
            document.getElementById('workspace-search').value = item.query;
            applyWorkspaceSearchKinds(item.kinds || []);
            void runWorkspaceSearch();
        });
        const renameButton = document.createElement('button');
        renameButton.className = 'btn-secondary';
        renameButton.type = 'button';
        renameButton.textContent = 'Rename';
        renameButton.addEventListener('click', () => {
            void renameSavedSearch(item.id, item.name);
        });
        const duplicateButton = document.createElement('button');
        duplicateButton.className = 'btn-secondary';
        duplicateButton.type = 'button';
        duplicateButton.textContent = 'Duplicate';
        duplicateButton.addEventListener('click', () => {
            void duplicateSavedSearch(item.id);
        });
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removeSavedSearch(item.id);
        });
        const pinButton = document.createElement('button');
        pinButton.className = 'btn-secondary';
        pinButton.type = 'button';
        pinButton.textContent = item.pinned ? 'Unpin' : 'Pin';
        pinButton.addEventListener('click', () => {
            void updateSavedSearch(item.id, { pinned: !item.pinned });
        });
        const groupButton = document.createElement('button');
        groupButton.className = 'btn-secondary';
        groupButton.type = 'button';
        groupButton.textContent = 'Set Group';
        groupButton.addEventListener('click', () => {
            const nextGroup = window.prompt('Set search group', item.group || '');
            if (nextGroup === null) return;
            void updateSavedSearch(item.id, { group: nextGroup.trim() || null });
        });
        const archiveButton = document.createElement('button');
        archiveButton.className = 'btn-secondary';
        archiveButton.type = 'button';
        archiveButton.textContent = item.archived ? 'Restore' : 'Archive';
        archiveButton.addEventListener('click', () => {
            void updateSavedSearch(item.id, { archived: !item.archived });
        });
        actionsEl.appendChild(applyButton);
        actionsEl.appendChild(renameButton);
        actionsEl.appendChild(duplicateButton);
        actionsEl.appendChild(pinButton);
        actionsEl.appendChild(groupButton);
        actionsEl.appendChild(archiveButton);
        actionsEl.appendChild(removeButton);

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

async function loadSavedSearches() {
    try {
        const resp = await fetch(buildApiUrl('/api/searches'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderSavedSearches(await resp.json());
    } catch {
        currentSavedSearches = [];
        document.getElementById('saved-searches-list').innerHTML = '';
    }
}

function resetPinnedRuns(message = 'Open a saved run and pin the ones you want to keep at the top of the workspace.') {
    document.getElementById('pinned-runs-empty').textContent = message;
    document.getElementById('pinned-runs-empty').style.display = '';
    document.getElementById('pinned-runs-list').innerHTML = '';
}

function renderPinnedRuns(items) {
    const emptyEl = document.getElementById('pinned-runs-empty');
    const listEl = document.getElementById('pinned-runs-list');
    listEl.innerHTML = '';

    if (!items.length) {
        resetPinnedRuns();
        return;
    }

    emptyEl.style.display = 'none';
    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.ticker
            ? `${item.ticker} · ${item.date || 'n/a'}`
            : item.run_id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            item.category,
            item.priority,
            item.action_status,
            item.assignee ? `@${item.assignee}` : null,
            item.note || 'Pinned for quick access',
        ]
            .filter(Boolean)
            .join(' · ');
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = [
            item.signal || item.status || item.run_id,
            item.next_action ? `Next: ${item.next_action}` : null,
            item.due_date ? `Due: ${item.due_date}` : null,
            item.snoozed_until ? `Snoozed: ${item.snoozed_until}` : null,
        ].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open';
        openButton.addEventListener('click', () => {
            void openRunDetails(item.run_id);
        });
        actionsEl.appendChild(buildAssigneeSelect(item.assignee, (assignee) => {
            void updatePinnedRunAssignee(item.run_id, assignee);
        }));
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removePinnedRun(item.run_id);
        });
        actionsEl.appendChild(openButton);
        actionsEl.appendChild(removeButton);

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        listEl.appendChild(row);
    });
}

async function loadPinnedRuns() {
    try {
        const category = document.getElementById('pinned-category-filter').value;
        const actionStatus = document.getElementById('pinned-action-status-filter').value;
        const assignee = document.getElementById('pinned-assignee-filter').value;
        const params = new URLSearchParams();
        if (category) params.set('category', category);
        if (actionStatus) params.set('action_status', actionStatus);
        if (assignee) params.set('assignee', assignee);
        const path = params.toString()
            ? `/api/pinned-runs?${params.toString()}`
            : '/api/pinned-runs';
        const resp = await fetch(buildApiUrl(path));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderPinnedRuns(await resp.json());
    } catch (e) {
        resetPinnedRuns(`Failed to load pinned runs: ${e.message}`);
    }
}

async function pinCurrentRun() {
    if (!currentRunId) {
        alert('Open a saved run before pinning it.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/pinned-runs'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                run_id: currentRunId,
                note: document.getElementById('pin-run-note').value.trim() || null,
                category: document.getElementById('pin-run-category').value || null,
                priority: document.getElementById('pin-run-priority').value || null,
                next_action: document.getElementById('pin-run-next-action').value.trim() || null,
                action_status: document.getElementById('pin-run-action-status').value || null,
                assignee: document.getElementById('pin-run-assignee').value || null,
                due_date: document.getElementById('pin-run-due-date').value || null,
                snoozed_until: document.getElementById('pin-run-snoozed-until').value || null,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        document.getElementById('pin-run-note').value = '';
        document.getElementById('pin-run-category').value = '';
        document.getElementById('pin-run-priority').value = '';
        document.getElementById('pin-run-next-action').value = '';
        document.getElementById('pin-run-action-status').value = '';
        document.getElementById('pin-run-assignee').value = '';
        document.getElementById('pin-run-due-date').value = '';
        document.getElementById('pin-run-snoozed-until').value = '';
        appendLog('Pinned current run.');
        void loadPinnedRuns();
        void loadActionBoard();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to pin run: ${e.message}`);
    }
}

async function removePinnedRun(runId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/pinned-runs/${encodeURIComponent(runId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed pinned run.');
        void loadPinnedRuns();
        void loadActionBoard();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to remove pinned run: ${e.message}`);
    }
}

async function updatePinnedRunAssignee(runId, assignee) {
    try {
        const resp = await fetch(buildApiUrl(`/api/pinned-runs/${encodeURIComponent(runId)}/assignee`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ assignee }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Updated pinned assignee${assignee ? ` to ${assignee}` : ''}.`);
        void loadPinnedRuns();
        void loadActionBoard();
        void loadDashboard();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to update pinned assignee: ${e.message}`);
    }
}

function renderActionBoardColumn(containerId, items) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (!items.length) {
        appendBriefingPlaceholder(container, 'No items.');
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.ticker
            ? `${item.ticker} · ${item.date || 'n/a'}`
            : item.run_id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [item.category, item.priority, item.assignee ? `@${item.assignee}` : null].filter(Boolean).join(' · ') || 'Pinned action';
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = [
            item.next_action || item.note || 'No next action',
            item.due_date ? `Due: ${item.due_date}` : null,
            item.snoozed_until ? `Snoozed: ${item.snoozed_until}` : null,
        ].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        ['todo', 'doing', 'done'].forEach((status) => {
            if (item.action_status === status) return;
            const button = document.createElement('button');
            button.className = 'btn-secondary';
            button.type = 'button';
            button.textContent = status;
            button.addEventListener('click', () => {
                void updatePinnedRunActionStatus(item.run_id, status);
            });
            actionsEl.appendChild(button);
        });
        actionsEl.appendChild(buildAssigneeSelect(item.assignee, (assignee) => {
            void updatePinnedRunAssignee(item.run_id, assignee);
        }));

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

function renderActionBoard(payload) {
    renderActionBoardColumn('action-board-todo', payload.todo || []);
    renderActionBoardColumn('action-board-doing', payload.doing || []);
    renderActionBoardColumn('action-board-done', payload.done || []);
}

async function loadActionBoard() {
    try {
        const resp = await fetch(buildApiUrl('/api/action-board'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderActionBoard(await resp.json());
    } catch (e) {
        appendBriefingPlaceholder(document.getElementById('action-board-todo'), `Failed to load: ${e.message}`);
        document.getElementById('action-board-doing').innerHTML = '';
        document.getElementById('action-board-done').innerHTML = '';
    }
}

async function updatePinnedRunActionStatus(runId, actionStatus) {
    try {
        const resp = await fetch(buildApiUrl(`/api/pinned-runs/${encodeURIComponent(runId)}/status`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ action_status: actionStatus }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`Updated pinned action to ${actionStatus}.`);
        void loadPinnedRuns();
        void loadActionBoard();
        void loadDashboard();
    } catch (e) {
        alert(`Failed to update pinned action status: ${e.message}`);
    }
}

async function saveRunAnnotation() {
    if (!currentRunId) {
        alert('Open a saved run before saving an annotation.');
        return;
    }

    const label = document.getElementById('annotation-label').value.trim();
    if (!label) {
        alert('Enter an annotation label first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${currentRunId}/annotation`), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                label,
                summary: document.getElementById('annotation-summary').value.trim() || null,
                next_step: document.getElementById('annotation-next-step').value.trim() || null,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Saved run annotation.');
        await loadRunHistory();
        await openRunDetails(currentRunId);
        void loadTimeline();
    } catch (e) {
        alert(`Failed to save annotation: ${e.message}`);
    }
}

async function clearRunAnnotation() {
    if (!currentRunId) {
        resetRunAnnotationForm();
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${currentRunId}/annotation`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        resetRunAnnotationForm();
        appendLog('Cleared run annotation.');
        await loadRunHistory();
        await openRunDetails(currentRunId);
        void loadTimeline();
    } catch (e) {
        alert(`Failed to clear annotation: ${e.message}`);
    }
}

async function saveRunReview() {
    if (!currentRunId) {
        alert('Open a saved run before saving a review.');
        return;
    }

    const reviewer = document.getElementById('reviewer-member').value;
    if (!reviewer) {
        alert('Select a workspace member as reviewer first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${currentRunId}/review`), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                reviewer,
                status: document.getElementById('review-status').value,
                note: document.getElementById('review-note').value.trim() || null,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Saved run review.');
        await loadRunHistory();
        await openRunDetails(currentRunId);
        void loadTimeline();
        void loadNotifications();
        void loadMemberWorkspace();
        void loadRunReviewHistory();
    } catch (e) {
        alert(`Failed to save review: ${e.message}`);
    }
}

async function clearRunReview() {
    if (!currentRunId) {
        resetRunReviewForm();
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${currentRunId}/review`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        resetRunReviewForm();
        appendLog('Cleared run review.');
        await loadRunHistory();
        await openRunDetails(currentRunId);
        void loadTimeline();
        void loadNotifications();
        void loadMemberWorkspace();
        void loadRunReviewHistory();
    } catch (e) {
        alert(`Failed to clear review: ${e.message}`);
    }
}

async function saveCurrentSearch() {
    const name = document.getElementById('saved-search-name').value.trim();
    const query = document.getElementById('workspace-search').value.trim();
    const kinds = collectWorkspaceSearchKinds();

    if (!name) {
        alert('Enter a saved search name first.');
        return;
    }
    if (!query) {
        alert('Enter a search query first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/searches'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                name,
                query,
                kinds,
                group: document.getElementById('saved-search-group').value.trim() || null,
                pinned: document.getElementById('saved-search-pinned').checked,
                member_id: getCurrentMemberId(),
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        document.getElementById('saved-search-name').value = '';
        document.getElementById('saved-search-group').value = '';
        document.getElementById('saved-search-pinned').checked = false;
        appendLog(`Saved search: ${name}`);
        await loadSavedSearches();
    } catch (e) {
        alert(`Failed to save search: ${e.message}`);
    }
}

async function removeSavedSearch(searchId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/searches/${encodeURIComponent(searchId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed saved search.');
        await loadSavedSearches();
    } catch (e) {
        alert(`Failed to remove saved search: ${e.message}`);
    }
}

async function renameSavedSearch(searchId, currentName) {
    const nextName = window.prompt('Rename saved search', currentName || '');
    if (nextName === null) return;
    const trimmed = nextName.trim();
    if (!trimmed) {
        alert('Saved search name cannot be blank.');
        return;
    }
    try {
        const resp = await fetch(buildApiUrl(`/api/searches/${encodeURIComponent(searchId)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ name: trimmed }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        await loadSavedSearches();
    } catch (e) {
        alert(`Failed to rename saved search: ${e.message}`);
    }
}

async function duplicateSavedSearch(searchId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/searches/${encodeURIComponent(searchId)}/duplicate`), {
            method: 'POST',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Duplicated saved search.');
        await loadSavedSearches();
    } catch (e) {
        alert(`Failed to duplicate saved search: ${e.message}`);
    }
}

async function updateSavedSearch(searchId, body) {
    try {
        const resp = await fetch(buildApiUrl(`/api/searches/${encodeURIComponent(searchId)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        await loadSavedSearches();
    } catch (e) {
        alert(`Failed to update saved search: ${e.message}`);
    }
}

function populateMemberFilterOptions(selectedValue = '') {
    const targets = [
        { id: 'pin-run-assignee', defaultLabel: 'Unassigned', valueField: 'name' },
        { id: 'pinned-assignee-filter', defaultLabel: 'All', valueField: 'name' },
        { id: 'comment-author', defaultLabel: 'Select member', valueField: 'name' },
        { id: 'reviewer-member', defaultLabel: 'Select member', valueField: 'name' },
        { id: 'review-history-reviewer-filter', defaultLabel: 'All', valueField: 'name' },
        { id: 'notifications-member-filter', defaultLabel: 'All', valueField: 'name' },
        { id: 'member-workspace-filter', defaultLabel: 'Select member', valueField: 'id' },
        { id: 'current-member', defaultLabel: 'None', valueField: 'id' },
    ];

    targets.forEach(({ id, defaultLabel, valueField }) => {
        const select = document.getElementById(id);
        if (!select) return;
        const keepValue = select.value || selectedValue;
        select.innerHTML = '';
        const emptyOpt = document.createElement('option');
        emptyOpt.value = '';
        emptyOpt.textContent = defaultLabel;
        select.appendChild(emptyOpt);
        currentWorkspaceMembers.forEach((member) => {
            const opt = document.createElement('option');
            opt.value = valueField === 'id' ? member.id : member.name;
            opt.textContent = member.role ? `${member.name} · ${member.role}` : member.name;
            select.appendChild(opt);
        });
        if ([...select.options].some((option) => option.value === keepValue)) {
            select.value = keepValue;
        }
    });
}

function applyCurrentMemberContext() {
    const member = getCurrentMember();
    const notificationsFilter = document.getElementById('notifications-member-filter');
    const workspaceFilter = document.getElementById('member-workspace-filter');
    if (!member) {
        if (notificationsFilter && notificationsFilter.value) {
            notificationsFilter.value = '';
        }
        if (workspaceFilter && workspaceFilter.value) {
            workspaceFilter.value = '';
        }
        currentMemberWorkspaceId = null;
        return;
    }

    if (notificationsFilter) {
        notificationsFilter.value = member.name;
    }
    if (workspaceFilter) {
        workspaceFilter.value = member.id;
    }
    if (!document.getElementById('comment-author').value) {
        document.getElementById('comment-author').value = member.name;
    }
    if (!document.getElementById('reviewer-member').value) {
        document.getElementById('reviewer-member').value = member.name;
    }
    currentMemberWorkspaceId = member.id;
}

function currentMemberScopedView() {
    return Boolean(getCurrentMemberId() && !currentRunId && !currentTickerHomeTicker);
}

function buildAssigneeSelect(selectedValue, onChange) {
    const select = document.createElement('select');
    select.className = 'btn-secondary';

    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = 'Unassigned';
    select.appendChild(emptyOpt);

    currentWorkspaceMembers.forEach((member) => {
        const opt = document.createElement('option');
        opt.value = member.name;
        opt.textContent = member.role ? `${member.name} · ${member.role}` : member.name;
        select.appendChild(opt);
    });

    select.value = [...select.options].some((option) => option.value === (selectedValue || ''))
        ? (selectedValue || '')
        : '';
    select.addEventListener('change', () => {
        onChange(select.value || null);
    });
    return select;
}

function resetWorkspaceMembers(message = 'Add lightweight workspace members so pinned actions can be assigned.') {
    currentWorkspaceMembers = [];
    window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, '');
    document.getElementById('current-member').value = '';
    document.getElementById('members-empty').textContent = message;
    document.getElementById('members-empty').style.display = '';
    document.getElementById('members-list').innerHTML = '';
    populateMemberFilterOptions();
}

function renderWorkspaceMembers(items) {
    currentWorkspaceMembers = items;
    const emptyEl = document.getElementById('members-empty');
    const listEl = document.getElementById('members-list');
    listEl.innerHTML = '';
    populateMemberFilterOptions();

    const currentMemberId = getCurrentMemberId();
    if (currentMemberId && !currentWorkspaceMembers.some((member) => member.id === currentMemberId)) {
        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, '');
        document.getElementById('current-member').value = '';
    }
    if (!document.getElementById('current-member').value && currentWorkspaceMembers.length) {
        document.getElementById('current-member').value = currentWorkspaceMembers[0].id;
        window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, currentWorkspaceMembers[0].id);
    }
    applyCurrentMemberContext();

    if (!items.length) {
        resetWorkspaceMembers();
        return;
    }

    emptyEl.style.display = 'none';
    items.forEach((member) => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = member.name;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            member.role || null,
            member.created_at ? `Added ${member.created_at}` : 'Workspace member',
        ].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const viewButton = document.createElement('button');
        viewButton.className = 'btn-secondary';
        viewButton.type = 'button';
        viewButton.textContent = 'View Work';
        viewButton.addEventListener('click', () => {
            currentMemberWorkspaceId = member.id;
            document.getElementById('current-member').value = member.id;
            window.localStorage.setItem(CURRENT_MEMBER_STORAGE_KEY, member.id);
            populateMemberFilterOptions(member.id);
            applyCurrentMemberContext();
            document.getElementById('member-workspace-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
            void loadMemberWorkspace();
        });
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removeWorkspaceMember(member.id);
        });
        actionsEl.appendChild(viewButton);
        actionsEl.appendChild(removeButton);

        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        listEl.appendChild(row);
    });
}

async function loadWorkspaceMembers() {
    try {
        const resp = await fetch(buildApiUrl('/api/members'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderWorkspaceMembers(await resp.json());
        void loadPinnedRuns();
        void loadActionBoard();
        void loadDashboard();
        void loadMemberWorkspace();
        void loadRunReviewHistory();
    } catch (e) {
        resetWorkspaceMembers(`Failed to load members: ${e.message}`);
    }
}

async function saveWorkspaceMember() {
    const name = document.getElementById('member-name').value.trim();
    const role = document.getElementById('member-role').value || null;
    if (!name) {
        alert('Enter a member name first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl('/api/members'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ name, role }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        document.getElementById('member-name').value = '';
        document.getElementById('member-role').value = '';
        appendLog(`Saved workspace member: ${name}`);
        await loadWorkspaceMembers();
        void loadPinnedRuns();
        void loadActionBoard();
    } catch (e) {
        alert(`Failed to save workspace member: ${e.message}`);
    }
}

async function removeWorkspaceMember(memberId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/members/${encodeURIComponent(memberId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed workspace member.');
        await loadWorkspaceMembers();
        void loadPinnedRuns();
        void loadActionBoard();
        void loadDashboard();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to remove workspace member: ${e.message}`);
    }
}

function resetMemberWorkspace(message = 'Pick a workspace member to see their assigned actions, mentions, and recent discussion.') {
    currentMemberWorkspaceId = document.getElementById('member-workspace-filter').value || null;
    document.getElementById('member-workspace-empty').textContent = message;
    document.getElementById('member-workspace-empty').style.display = '';
    document.getElementById('member-workspace-content').style.display = 'none';
    document.getElementById('member-workspace-summary').innerHTML = '';
    document.getElementById('member-workspace-actions').innerHTML = '';
    document.getElementById('member-workspace-reviews').innerHTML = '';
    document.getElementById('member-workspace-mentions').innerHTML = '';
    document.getElementById('member-workspace-comments').innerHTML = '';
}

function renderMemberWorkspaceSummary(summary) {
    const container = document.getElementById('member-workspace-summary');
    const cards = [
        ['Assigned', summary.assigned_action_count],
        ['Overdue', summary.overdue_action_count],
        ['Pending Reviews', summary.pending_review_count],
        ['Mentions', summary.mention_count],
        ['Unread Mentions', summary.unread_mention_count],
        ['Recent Comments', summary.recent_comment_count],
    ];
    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';
        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;
        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);
        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function renderMemberWorkspaceReviews(items) {
    const container = document.getElementById('member-workspace-reviews');
    container.innerHTML = '';
    if (!items.length) {
        appendBriefingPlaceholder(container, 'No pending reviews.');
        return;
    }
    items.forEach((review) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = review.run_id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = review.status;
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = review.note || 'Review requested.';
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);
        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open Run';
        openButton.addEventListener('click', () => {
            void openRunDetails(review.run_id);
        });
        actionsEl.appendChild(openButton);
        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

function renderMemberWorkspaceActions(items) {
    const container = document.getElementById('member-workspace-actions');
    container.innerHTML = '';
    if (!items.length) {
        appendBriefingPlaceholder(container, 'No assigned actions.');
        return;
    }
    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = item.ticker ? `${item.ticker} · ${item.date || 'n/a'}` : item.run_id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [item.category, item.priority, item.action_status].filter(Boolean).join(' · ') || 'Assigned action';
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = [item.next_action || item.note || 'No next action', item.due_date ? `Due: ${item.due_date}` : null].filter(Boolean).join(' · ');
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);
        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open Run';
        openButton.addEventListener('click', () => {
            void openRunDetails(item.run_id);
        });
        actionsEl.appendChild(openButton);
        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

function renderMemberWorkspaceComments(items) {
    const container = document.getElementById('member-workspace-comments');
    container.innerHTML = '';
    if (!items.length) {
        appendBriefingPlaceholder(container, 'No recent comments.');
        return;
    }
    items.forEach((comment) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = comment.run_id;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            comment.created_at,
            comment.resolved ? `resolved by ${comment.resolved_by || 'unknown'}` : 'open',
        ].filter(Boolean).join(' · ');
        const signalEl = document.createElement('div');
        signalEl.className = 'history-signal';
        signalEl.textContent = comment.content;
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(signalEl);
        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const openButton = document.createElement('button');
        openButton.className = 'btn-secondary';
        openButton.type = 'button';
        openButton.textContent = 'Open Run';
        openButton.addEventListener('click', () => {
            void openRunDetails(comment.run_id);
        });
        actionsEl.appendChild(openButton);
        row.appendChild(metaEl);
        row.appendChild(actionsEl);
        container.appendChild(row);
    });
}

function renderMemberWorkspace(payload) {
    if (!payload.member) {
        resetMemberWorkspace();
        return;
    }
    document.getElementById('member-workspace-empty').style.display = 'none';
    document.getElementById('member-workspace-content').style.display = '';
    renderMemberWorkspaceSummary(payload.summary);
    renderMemberWorkspaceActions(payload.assigned_actions || []);
    renderMemberWorkspaceReviews(payload.pending_reviews || []);
    const mentionsEl = document.getElementById('member-workspace-mentions');
    mentionsEl.innerHTML = '';
    if ((payload.mention_notifications || []).length) {
        payload.mention_notifications.forEach((item) => {
            mentionsEl.appendChild(renderNotificationItem(item));
        });
    } else {
        appendBriefingPlaceholder(mentionsEl, 'No mentions yet.');
    }
    renderMemberWorkspaceComments(payload.recent_comments || []);
}

async function loadMemberWorkspace() {
    const memberId = document.getElementById('member-workspace-filter').value || currentMemberWorkspaceId;
    currentMemberWorkspaceId = memberId || null;
    if (!memberId) {
        resetMemberWorkspace();
        return;
    }
    try {
        const resp = await fetch(buildApiUrl(`/api/members/${encodeURIComponent(memberId)}/workspace`));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderMemberWorkspace(await resp.json());
    } catch (e) {
        resetMemberWorkspace(`Failed to load member workspace: ${e.message}`);
    }
}

function resetRunComments(message = 'Comments for the current run will appear here.') {
    currentCommentsRunId = null;
    currentRunComments = [];
    document.getElementById('comments-scope').textContent = 'Open a run to collaborate on its discussion thread.';
    document.getElementById('comments-empty').textContent = message;
    document.getElementById('comments-empty').style.display = '';
    document.getElementById('comments-list').innerHTML = '';
    document.getElementById('comment-content').value = '';
}

function prepareCommentsContext(run) {
    currentCommentsRunId = run?.run_id || null;
    const scopeEl = document.getElementById('comments-scope');
    document.getElementById('comment-content').value = '';
    if (run?.run_id) {
        scopeEl.textContent = `Discussing run ${run.run_id}${run.ticker ? ` · ${run.ticker}` : ''}${run.date ? ` · ${run.date}` : ''}.`;
        void loadRunComments();
    } else {
        resetRunComments();
    }
}

function renderRunComments(comments) {
    currentRunComments = comments;
    const emptyEl = document.getElementById('comments-empty');
    const listEl = document.getElementById('comments-list');
    listEl.innerHTML = '';
    const visibleComments = document.getElementById('comments-hide-resolved').checked
        ? comments.filter((comment) => !comment.resolved)
        : comments;

    if (!visibleComments.length) {
        emptyEl.textContent = comments.length
            ? 'No open comments match the current view.'
            : 'No comments on this run yet.';
        emptyEl.style.display = '';
        return;
    }

    emptyEl.style.display = 'none';
    visibleComments.forEach((comment) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = comment.author;
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = [
            comment.created_at,
            comment.resolved ? `resolved by ${comment.resolved_by || 'unknown'}` : 'open',
        ].filter(Boolean).join(' · ');
        const contentEl = document.createElement('div');
        contentEl.className = 'history-signal';
        contentEl.textContent = comment.content;
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        metaEl.appendChild(contentEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removeRunComment(comment.id);
        });
        const toggleButton = document.createElement('button');
        toggleButton.className = 'btn-secondary';
        toggleButton.type = 'button';
        toggleButton.textContent = comment.resolved ? 'Reopen' : 'Resolve';
        toggleButton.addEventListener('click', () => {
            void updateRunCommentResolution(comment, !comment.resolved);
        });
        actionsEl.appendChild(toggleButton);
        actionsEl.appendChild(removeButton);

        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        listEl.appendChild(item);
    });
}

async function loadRunComments() {
    if (!currentCommentsRunId) {
        resetRunComments();
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(currentCommentsRunId)}/comments`));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderRunComments(await resp.json());
    } catch (e) {
        resetRunComments(`Failed to load comments: ${e.message}`);
    }
}

async function saveRunComment() {
    if (!currentCommentsRunId) {
        alert('Open a saved run before posting a comment.');
        return;
    }
    const author = document.getElementById('comment-author').value;
    const content = document.getElementById('comment-content').value.trim();
    if (!author) {
        alert('Select a workspace member as the comment author.');
        return;
    }
    if (!content) {
        alert('Enter a comment first.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(currentCommentsRunId)}/comments`), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ author, content }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        document.getElementById('comment-content').value = '';
        appendLog('Posted run comment.');
        void loadRunComments();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to post comment: ${e.message}`);
    }
}

async function updateRunCommentResolution(comment, resolved) {
    if (!currentCommentsRunId) return;
    const resolvedBy = document.getElementById('comment-author').value || null;
    if (resolved && !resolvedBy) {
        alert('Select a workspace member before resolving a comment.');
        return;
    }
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(currentCommentsRunId)}/comments/${encodeURIComponent(comment.id)}`), {
            method: 'PATCH',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ resolved, resolved_by: resolved ? resolvedBy : null }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog(`${resolved ? 'Resolved' : 'Reopened'} run comment.`);
        void loadRunComments();
    } catch (e) {
        alert(`Failed to update comment: ${e.message}`);
    }
}

async function removeRunComment(commentId) {
    if (!currentCommentsRunId) return;
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${encodeURIComponent(currentCommentsRunId)}/comments/${encodeURIComponent(commentId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed run comment.');
        void loadRunComments();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to remove comment: ${e.message}`);
    }
}

function resetNotes(message = 'Notes for the current run or ticker will appear here.') {
    editingNoteId = null;
    document.getElementById('save-note').textContent = 'Save Note';
    document.getElementById('notes-empty').textContent = message;
    document.getElementById('notes-empty').style.display = '';
    document.getElementById('notes-tag-cloud').innerHTML = '';
    document.getElementById('notes-list').innerHTML = '';
    document.getElementById('note-tags').value = '';
    document.getElementById('note-content').value = '';
}

function prepareNotesContext({ ticker = null, run_id = null, date = null } = {}) {
    notesContext = {
        ticker: ticker ? ticker.toUpperCase() : null,
        runId: run_id || null,
    };

    const scopeEl = document.getElementById('notes-scope');
    editingNoteId = null;
    document.getElementById('save-note').textContent = 'Save Note';
    document.getElementById('note-tags').value = '';
    document.getElementById('note-content').value = '';
    if (document.getElementById('notes-mode').value === 'workspace') {
        scopeEl.textContent = 'Browsing notes across the whole workspace.';
    } else if (run_id) {
        scopeEl.textContent = `Saving notes for run ${run_id}${ticker ? ` · ${ticker}` : ''}${date ? ` · ${date}` : ''}.`;
    } else if (ticker) {
        scopeEl.textContent = `Saving notes for ticker ${ticker.toUpperCase()}.`;
    } else {
        scopeEl.textContent = 'Open a run or focus a ticker to attach notes.';
    }

    void loadNotes();
}

function applyNotesTagFilter(tag) {
    document.getElementById('notes-search').value = tag || '';
    void loadNotes();
}

function renderNotes(notes) {
    const emptyEl = document.getElementById('notes-empty');
    const listEl = document.getElementById('notes-list');
    const tagCloud = document.getElementById('notes-tag-cloud');
    listEl.innerHTML = '';
    tagCloud.innerHTML = '';

    const tags = [...new Set(
        notes.flatMap((note) => (note.tags || []).filter(Boolean))
    )].sort();
    tags.forEach((tag) => {
        const button = document.createElement('button');
        button.className = 'tag-chip';
        button.type = 'button';
        button.textContent = `#${tag}`;
        button.addEventListener('click', () => {
            applyNotesTagFilter(tag);
        });
        tagCloud.appendChild(button);
    });

    if (!notes.length) {
        resetNotes('No notes saved for this scope yet.');
        return;
    }

    emptyEl.style.display = 'none';
    notes.forEach((note) => {
        const item = document.createElement('div');
        item.className = 'history-item';

        const metaEl = document.createElement('div');
        metaEl.className = 'history-meta';
        const titleEl = document.createElement('div');
        titleEl.className = 'history-title';
        titleEl.textContent = note.ticker || note.run_id || 'Workspace Note';
        const subtitleEl = document.createElement('div');
        subtitleEl.className = 'history-subtitle';
        subtitleEl.textContent = note.created_at;
        const tagsEl = document.createElement('div');
        tagsEl.className = 'note-tag-row';
        (note.tags || []).forEach((tag) => {
            const button = document.createElement('button');
            button.className = 'tag-chip';
            button.type = 'button';
            button.textContent = `#${tag}`;
            button.addEventListener('click', () => {
                applyNotesTagFilter(tag);
            });
            tagsEl.appendChild(button);
        });
        const contentEl = document.createElement('div');
        contentEl.className = 'history-signal';
        contentEl.textContent = note.content;
        metaEl.appendChild(titleEl);
        metaEl.appendChild(subtitleEl);
        if ((note.tags || []).length) {
            metaEl.appendChild(tagsEl);
        }
        metaEl.appendChild(contentEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'history-actions';
        const editButton = document.createElement('button');
        editButton.className = 'btn-secondary';
        editButton.type = 'button';
        editButton.textContent = 'Edit';
        editButton.addEventListener('click', () => {
            editingNoteId = note.id;
            document.getElementById('note-content').value = note.content;
            document.getElementById('note-tags').value = (note.tags || []).join(', ');
            document.getElementById('save-note').textContent = 'Update Note';
        });
        const removeButton = document.createElement('button');
        removeButton.className = 'btn-secondary';
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            void removeNote(note.id);
        });
        actionsEl.appendChild(editButton);
        actionsEl.appendChild(removeButton);

        item.appendChild(metaEl);
        item.appendChild(actionsEl);
        listEl.appendChild(item);
    });
}

async function loadNotes() {
    const mode = document.getElementById('notes-mode').value;
    const scopeEl = document.getElementById('notes-scope');
    if (mode === 'workspace') {
        scopeEl.textContent = 'Browsing notes across the whole workspace.';
    } else if (notesContext.runId) {
        scopeEl.textContent = `Saving notes for run ${notesContext.runId}${notesContext.ticker ? ` · ${notesContext.ticker}` : ''}.`;
    } else if (notesContext.ticker) {
        scopeEl.textContent = `Saving notes for ticker ${notesContext.ticker}.`;
    } else {
        scopeEl.textContent = 'Open a run or focus a ticker to attach notes.';
    }

    if (mode !== 'workspace' && !notesContext.runId && !notesContext.ticker) {
        resetNotes();
        return;
    }

    const params = new URLSearchParams();
    if (mode !== 'workspace' && notesContext.runId) {
        params.set('run_id', notesContext.runId);
    } else if (mode !== 'workspace' && notesContext.ticker) {
        params.set('ticker', notesContext.ticker);
    }
    const query = document.getElementById('notes-search').value.trim();
    if (query) {
        params.set('q', query);
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/notes?${params.toString()}`));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderNotes(await resp.json());
    } catch (e) {
        resetNotes(`Failed to load notes: ${e.message}`);
    }
}

async function saveNote() {
    const content = document.getElementById('note-content').value.trim();
    const tags = document.getElementById('note-tags').value
        .split(',')
        .map(tag => tag.trim())
        .filter(Boolean);
    if (!content) {
        alert('Enter a note first.');
        return;
    }
    if (!notesContext.runId && !notesContext.ticker) {
        alert('Open a run or focus a ticker before saving a note.');
        return;
    }

    try {
        const target = editingNoteId
            ? buildApiUrl(`/api/notes/${encodeURIComponent(editingNoteId)}`)
            : buildApiUrl('/api/notes');
        const resp = await fetch(target, {
            method: editingNoteId ? 'PUT' : 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                content,
                tags,
                ticker: notesContext.ticker,
                run_id: notesContext.runId,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        editingNoteId = null;
        document.getElementById('save-note').textContent = 'Save Note';
        document.getElementById('note-content').value = '';
        document.getElementById('note-tags').value = '';
        appendLog('Saved note.');
        void loadNotes();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to save note: ${e.message}`);
    }
}

async function removeNote(noteId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/notes/${encodeURIComponent(noteId)}`), {
            method: 'DELETE',
            headers: apiHeaders(),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        appendLog('Removed note.');
        void loadNotes();
        void loadTimeline();
    } catch (e) {
        alert(`Failed to remove note: ${e.message}`);
    }
}

function resetBriefing(message = 'Your saved runs, alerts, watchlist, and portfolio will roll up into a daily workspace briefing here.') {
    document.getElementById('briefing-empty').textContent = message;
    document.getElementById('briefing-empty').style.display = '';
    document.getElementById('briefing-content').style.display = 'none';
    document.getElementById('briefing-summary').innerHTML = '';
    document.getElementById('briefing-alerts').innerHTML = '';
    document.getElementById('briefing-watchlist').innerHTML = '';
    document.getElementById('briefing-portfolio').innerHTML = '';
    document.getElementById('briefing-runs').innerHTML = '';
}

function renderBriefingSummary(summary) {
    const container = document.getElementById('briefing-summary');
    const cards = [
        ['Generated', summary.generated_at],
        ['Headline', summary.headline],
        ['Alert Hits', summary.alert_hit_count],
        ['Watchlist', summary.watchlist_count],
        ['Portfolio Positions', summary.portfolio_position_count],
        ['Recent Runs', summary.recent_run_count],
    ];

    container.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        container.appendChild(cardEl);
    });
}

function appendBriefingPlaceholder(container, message) {
    const placeholder = document.createElement('div');
    placeholder.className = 'hint';
    placeholder.textContent = message;
    container.appendChild(placeholder);
}

function renderBriefing(payload) {
    const alertsEl = document.getElementById('briefing-alerts');
    const watchlistEl = document.getElementById('briefing-watchlist');
    const portfolioEl = document.getElementById('briefing-portfolio');
    const runsEl = document.getElementById('briefing-runs');

    alertsEl.innerHTML = '';
    watchlistEl.innerHTML = '';
    portfolioEl.innerHTML = '';
    runsEl.innerHTML = '';

    if (
        payload.summary.alert_hit_count === 0 &&
        payload.summary.watchlist_count === 0 &&
        payload.summary.portfolio_position_count === 0 &&
        payload.summary.recent_run_count === 0
    ) {
        resetBriefing();
        return;
    }

    document.getElementById('briefing-empty').style.display = 'none';
    document.getElementById('briefing-content').style.display = '';
    renderBriefingSummary(payload.summary);

    if (payload.alert_hits.length) {
        payload.alert_hits.forEach((hit) => {
            alertsEl.appendChild(renderAlertHitItem(hit));
        });
    } else {
        appendBriefingPlaceholder(alertsEl, 'No active alert hits.');
    }

    if (payload.watchlist_focus.length) {
        payload.watchlist_focus.forEach((entry) => {
            const item = document.createElement('div');
            item.className = 'history-item';

            const metaEl = document.createElement('div');
            metaEl.className = 'history-meta';
            const titleEl = document.createElement('div');
            titleEl.className = 'history-title';
            titleEl.textContent = entry.ticker;
            const subtitleEl = document.createElement('div');
            subtitleEl.className = 'history-subtitle';
            subtitleEl.textContent = `${entry.run_count} saved run(s)`;
            const signalEl = document.createElement('div');
            signalEl.className = 'history-signal';
            signalEl.textContent = entry.latest_signal || entry.latest_status || 'No saved signal yet';
            metaEl.appendChild(titleEl);
            metaEl.appendChild(subtitleEl);
            metaEl.appendChild(signalEl);

            const actionsEl = document.createElement('div');
            actionsEl.className = 'history-actions';
            const openButton = document.createElement('button');
            openButton.className = 'btn-secondary';
            openButton.type = 'button';
            openButton.textContent = 'Open';
            openButton.addEventListener('click', () => focusTicker(entry.ticker));
            actionsEl.appendChild(openButton);
            item.appendChild(metaEl);
            item.appendChild(actionsEl);
            watchlistEl.appendChild(item);
        });
    } else {
        appendBriefingPlaceholder(watchlistEl, 'No watchlist focus yet.');
    }

    if (payload.portfolio_focus.length) {
        payload.portfolio_focus.forEach((position) => {
            const item = document.createElement('div');
            item.className = 'history-item';

            const metaEl = document.createElement('div');
            metaEl.className = 'history-meta';
            const titleEl = document.createElement('div');
            titleEl.className = 'history-title';
            titleEl.textContent = `${position.ticker} · qty ${position.quantity}`;
            const subtitleEl = document.createElement('div');
            subtitleEl.className = 'history-subtitle';
            subtitleEl.textContent = `Cost basis ${position.cost_basis}`;
            const signalEl = document.createElement('div');
            signalEl.className = 'history-signal';
            signalEl.textContent = position.latest_signal || position.latest_status || 'No saved signal yet';
            metaEl.appendChild(titleEl);
            metaEl.appendChild(subtitleEl);
            metaEl.appendChild(signalEl);

            const actionsEl = document.createElement('div');
            actionsEl.className = 'history-actions';
            const openButton = document.createElement('button');
            openButton.className = 'btn-secondary';
            openButton.type = 'button';
            openButton.textContent = 'Open';
            openButton.addEventListener('click', () => focusTicker(position.ticker));
            actionsEl.appendChild(openButton);
            item.appendChild(metaEl);
            item.appendChild(actionsEl);
            portfolioEl.appendChild(item);
        });
    } else {
        appendBriefingPlaceholder(portfolioEl, 'No saved positions yet.');
    }

    if (payload.recent_runs.length) {
        payload.recent_runs.forEach((run) => {
            const item = document.createElement('div');
            item.className = 'history-item';

            const metaEl = document.createElement('div');
            metaEl.className = 'history-meta';
            const titleEl = document.createElement('div');
            titleEl.className = 'history-title';
            titleEl.textContent = `${run.ticker} · ${run.date}`;
            const subtitleEl = document.createElement('div');
            subtitleEl.className = 'history-subtitle';
            subtitleEl.textContent = run.asset_type;
            const signalEl = document.createElement('div');
            signalEl.className = 'history-signal';
            signalEl.textContent = run.signal || run.error || run.status;
            metaEl.appendChild(titleEl);
            metaEl.appendChild(subtitleEl);
            metaEl.appendChild(signalEl);

            const actionsEl = document.createElement('div');
            actionsEl.className = 'history-actions';
            const openButton = document.createElement('button');
            openButton.className = 'btn-secondary';
            openButton.type = 'button';
            openButton.textContent = 'Open Run';
            openButton.addEventListener('click', () => void openRunDetails(run.run_id));
            actionsEl.appendChild(openButton);
            item.appendChild(metaEl);
            item.appendChild(actionsEl);
            runsEl.appendChild(item);
        });
    } else {
        appendBriefingPlaceholder(runsEl, 'No recent runs yet.');
    }
}

async function loadBriefing() {
    try {
        const resp = await fetch(buildApiUrl('/api/briefing/daily'));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        renderBriefing(await resp.json());
    } catch (e) {
        resetBriefing(`Failed to load briefing: ${e.message}`);
    }
}

function resetComparePanel(message = 'Choose two saved runs to compare their signals, settings, and report sections.') {
    currentComparison = null;
    document.getElementById('compare-empty').textContent = message;
    document.getElementById('compare-empty').style.display = '';
    document.getElementById('compare-content').style.display = 'none';
    document.getElementById('compare-summary').innerHTML = '';
    document.getElementById('compare-left-title').textContent = '';
    document.getElementById('compare-right-title').textContent = '';
    document.getElementById('compare-left-content').textContent = '';
    document.getElementById('compare-right-content').textContent = '';
    populateCompareSectionOptions([]);
}

function resetFollowUpChat(message = 'Open a saved run, then ask follow-up questions about that analysis.') {
    followUpRunId = null;
    followUpMessages = [];
    document.getElementById('follow-up-empty').textContent = message;
    document.getElementById('follow-up-empty').style.display = '';
    document.getElementById('follow-up-transcript').innerHTML = '';
    document.getElementById('follow-up-question').value = '';
}

function renderFollowUpTranscript() {
    const emptyEl = document.getElementById('follow-up-empty');
    const transcriptEl = document.getElementById('follow-up-transcript');
    transcriptEl.innerHTML = '';

    if (!followUpMessages.length) {
        emptyEl.style.display = '';
        return;
    }

    emptyEl.style.display = 'none';
    followUpMessages.forEach((message) => {
        const item = document.createElement('div');
        item.className = 'follow-up-message';

        const roleEl = document.createElement('span');
        roleEl.className = 'follow-up-role';
        roleEl.textContent = message.role === 'user' ? 'You' : 'Assistant';

        const contentEl = document.createElement('div');
        contentEl.className = 'follow-up-content';
        contentEl.textContent = message.content;

        item.appendChild(roleEl);
        item.appendChild(contentEl);
        transcriptEl.appendChild(item);
    });
}

function prepareFollowUpChat(run) {
    if (followUpRunId !== run.run_id) {
        followUpRunId = run.run_id;
        followUpMessages = [];
        document.getElementById('follow-up-question').value = '';
    }

    const emptyEl = document.getElementById('follow-up-empty');
    emptyEl.textContent = `Ask follow-up questions about ${run.ticker} on ${run.date}.`;
    renderFollowUpTranscript();
}

function formatCompareRunOption(run) {
    const signal = run.signal || run.error || run.status;
    return `${run.ticker} · ${run.date} · ${signal}`;
}

function populateCompareRunOptions() {
    const leftSelect = document.getElementById('compare-left-run');
    const rightSelect = document.getElementById('compare-right-run');
    const previousLeft = leftSelect.value;
    const previousRight = rightSelect.value;

    [leftSelect, rightSelect].forEach((selectEl) => {
        selectEl.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Select a saved run';
        selectEl.appendChild(placeholder);

        runHistory.forEach((run) => {
            const option = document.createElement('option');
            option.value = run.run_id;
            option.textContent = formatCompareRunOption(run);
            selectEl.appendChild(option);
        });
    });

    if (runHistory.some((run) => run.run_id === previousLeft)) {
        leftSelect.value = previousLeft;
    } else if (runHistory.length > 0) {
        leftSelect.value = runHistory[0].run_id;
    }

    if (runHistory.some((run) => run.run_id === previousRight)) {
        rightSelect.value = previousRight;
    } else if (runHistory.length > 1) {
        rightSelect.value = runHistory[1].run_id;
    } else {
        rightSelect.value = '';
    }
}

function populateCompareSectionOptions(sectionKeys) {
    const select = document.getElementById('compare-section');
    const previous = select.value;
    select.innerHTML = '';

    if (!sectionKeys.length) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No sections';
        select.appendChild(option);
        return;
    }

    sectionKeys.forEach((key) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = REPORT_SECTION_LABELS[key] || key;
        select.appendChild(option);
    });

    if (sectionKeys.includes(previous)) {
        select.value = previous;
        return;
    }

    if (sectionKeys.includes('final_trade_decision')) {
        select.value = 'final_trade_decision';
        return;
    }

    select.value = sectionKeys[0];
}

function renderComparisonSection() {
    if (!currentComparison) return;

    const section = document.getElementById('compare-section').value;
    const leftText = currentComparison.left.report_sections[section] || 'No content for this section.';
    const rightText = currentComparison.right.report_sections[section] || 'No content for this section.';

    document.getElementById('compare-left-title').textContent = `${currentComparison.left.ticker} · ${currentComparison.left.date} · ${currentComparison.left.signal || currentComparison.left.status}`;
    document.getElementById('compare-right-title').textContent = `${currentComparison.right.ticker} · ${currentComparison.right.date} · ${currentComparison.right.signal || currentComparison.right.status}`;
    document.getElementById('compare-left-content').textContent = leftText;
    document.getElementById('compare-right-content').textContent = rightText;
}

function renderComparisonSummary(payload) {
    const summaryEl = document.getElementById('compare-summary');
    const cards = [
        ['Left Signal', payload.left.signal || payload.left.status],
        ['Right Signal', payload.right.signal || payload.right.status],
        ['Left Provider', payload.left.config_summary.llm_provider || 'n/a'],
        ['Right Provider', payload.right.config_summary.llm_provider || 'n/a'],
        ['Differing Fields', payload.differing_summary_fields.join(', ') || 'None'],
        ['Differing Sections', payload.differing_sections.join(', ') || 'None'],
    ];

    summaryEl.innerHTML = '';
    cards.forEach(([label, value]) => {
        const cardEl = document.createElement('div');
        cardEl.className = 'summary-card';

        const labelEl = document.createElement('span');
        labelEl.className = 'summary-label';
        labelEl.textContent = label;

        const valueEl = document.createElement('span');
        valueEl.className = 'summary-value';
        valueEl.textContent = String(value);

        cardEl.appendChild(labelEl);
        cardEl.appendChild(valueEl);
        summaryEl.appendChild(cardEl);
    });
}

function renderRunComparison(payload) {
    currentComparison = payload;
    document.getElementById('compare-empty').style.display = 'none';
    document.getElementById('compare-content').style.display = '';
    renderComparisonSummary(payload);
    populateCompareSectionOptions(payload.available_sections || []);
    renderComparisonSection();
}

async function compareSelectedRuns() {
    const leftRunId = document.getElementById('compare-left-run').value;
    const rightRunId = document.getElementById('compare-right-run').value;

    if (!leftRunId || !rightRunId) {
        alert('Select two saved runs before comparing.');
        return;
    }
    if (leftRunId === rightRunId) {
        alert('Choose two different runs to compare.');
        return;
    }

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/compare?left_run_id=${encodeURIComponent(leftRunId)}&right_run_id=${encodeURIComponent(rightRunId)}`));
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        renderRunComparison(await resp.json());
    } catch (e) {
        resetComparePanel(`Failed to compare runs: ${e.message}`);
        alert(`Failed to compare runs: ${e.message}`);
    }
}

async function askFollowUpQuestion() {
    const question = document.getElementById('follow-up-question').value.trim();
    if (!followUpRunId) {
        alert('Open a saved run before asking follow-up questions.');
        return;
    }
    if (!question) {
        alert('Enter a follow-up question first.');
        return;
    }

    const history = followUpMessages.map((message) => ({
        role: message.role,
        content: message.content,
    }));

    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${followUpRunId}/chat`), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ question, history }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        followUpMessages.push({ role: 'user', content: question });
        followUpMessages.push({ role: 'assistant', content: payload.answer });
        document.getElementById('follow-up-question').value = '';
        renderFollowUpTranscript();
    } catch (e) {
        alert(`Failed to ask follow-up question: ${e.message}`);
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

function getSelectedAnalysts() {
    const analystCheckboxes = document.querySelectorAll('input[name="analyst"]:checked');
    return Array.from(analystCheckboxes).map(cb => cb.value);
}

function buildSharedAnalysisConfig() {
    const quickModel = resolveModelValue('quick-model', 'quick-model-custom');
    const deepModel = resolveModelValue('deep-model', 'deep-model-custom');
    if (!quickModel || !deepModel) {
        throw new Error('Please enter a custom model ID when using the custom model option.');
    }

    return {
        analysts: getSelectedAnalysts(),
        llm_provider: document.getElementById('provider').value,
        deep_think_model: deepModel,
        quick_think_model: quickModel,
        research_depth: parseInt(document.getElementById('depth').value, 10),
        output_language: document.getElementById('language').value,
        market_profile: document.getElementById('run-market-profile').value || null,
        max_risk_discuss_rounds: parseInt(document.getElementById('run-risk-rounds').value, 10),
        max_recur_limit: parseOptionalInt('run-max-recur', 100),
        checkpoint_enabled: document.getElementById('run-checkpoint-enabled').checked,
        benchmark_ticker: document.getElementById('run-benchmark-ticker').value.trim() || null,
        temperature: parseOptionalFloat('run-temperature'),
        backend_url: document.getElementById('run-backend-url').value.trim() || null,
        google_thinking_level: document.getElementById('run-google-thinking').value || null,
        openai_reasoning_effort: document.getElementById('run-openai-effort').value || null,
        anthropic_effort: document.getElementById('run-anthropic-effort').value || null,
    };
}

function buildAnalysisBody(ticker) {
    return {
        ticker: ticker.trim(),
        date: document.getElementById('date').value,
        asset_type: detectAssetType(ticker),
        ...buildSharedAnalysisConfig(),
    };
}

function parseBatchTickers(raw) {
    const values = String(raw || '')
        .split(/[\s,]+/)
        .map(item => item.trim().toUpperCase())
        .filter(Boolean);
    return Array.from(new Set(values));
}

function syncAutomationFields() {
    const cadence = document.getElementById('automation-cadence').value;
    const source = document.getElementById('automation-source').value;
    document.getElementById('automation-weekday').disabled = cadence !== 'weekly';
    document.getElementById('automation-tickers').disabled = source !== 'manual';
}

async function startAnalysis() {
    const ticker = document.getElementById('ticker').value.trim();
    if (!ticker) return;

    const analysts = getSelectedAnalysts();
    if (analysts.length === 0) {
        alert('Please select at least one analyst.');
        return;
    }

    let body;
    try {
        body = buildAnalysisBody(ticker);
    } catch (e) {
        alert(e.message);
        return;
    }

    const providerKey = body.llm_provider;
    if (!isProviderKeyConfigured(providerKey)) {
        const display = KEY_DISPLAY_NAMES[providerKey] || providerKey;
        pendingAnalysisAction = { kind: 'single', body };
        showApiKeyModal(providerKey, display);
        return;
    }

    await executeAnalysis(body);
}

async function runBatchAnalysis(source) {
    const analysts = getSelectedAnalysts();
    if (analysts.length === 0) {
        alert('Please select at least one analyst.');
        return;
    }

    const manualTickers = parseBatchTickers(document.getElementById('batch-tickers').value);
    if (source === 'manual' && manualTickers.length === 0) {
        alert('Enter at least one ticker for the batch queue.');
        return;
    }

    let baseBody;
    try {
        baseBody = buildAnalysisBody((document.getElementById('ticker').value || manualTickers[0] || 'AAPL').trim());
    } catch (e) {
        alert(e.message);
        return;
    }

    const body = {
        source,
        tickers: source === 'manual' ? manualTickers : [],
        date: baseBody.date,
        analysts: baseBody.analysts,
        llm_provider: baseBody.llm_provider,
        deep_think_model: baseBody.deep_think_model,
        quick_think_model: baseBody.quick_think_model,
        research_depth: baseBody.research_depth,
        output_language: baseBody.output_language,
        market_profile: baseBody.market_profile,
        max_risk_discuss_rounds: baseBody.max_risk_discuss_rounds,
        max_recur_limit: baseBody.max_recur_limit,
        checkpoint_enabled: baseBody.checkpoint_enabled,
        benchmark_ticker: baseBody.benchmark_ticker,
        temperature: baseBody.temperature,
        backend_url: baseBody.backend_url,
        google_thinking_level: baseBody.google_thinking_level,
        openai_reasoning_effort: baseBody.openai_reasoning_effort,
        anthropic_effort: baseBody.anthropic_effort,
    };

    const providerKey = body.llm_provider;
    if (!isProviderKeyConfigured(providerKey)) {
        const display = KEY_DISPLAY_NAMES[providerKey] || providerKey;
        pendingAnalysisAction = { kind: 'batch', body };
        showApiKeyModal(providerKey, display);
        return;
    }

    await executeBatchAnalysis(body);
}

async function executeBatchAnalysis(body) {
    const manualButton = document.getElementById('run-batch-tickers');
    const watchlistButton = document.getElementById('run-watchlist-batch');
    manualButton.disabled = true;
    watchlistButton.disabled = true;

    try {
        const resp = await fetch(buildApiUrl('/api/runs/batch'), {
            method: 'POST',
            headers: apiHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }
        const payload = await resp.json();
        if (body.source === 'manual') {
            document.getElementById('batch-tickers').value = '';
        }
        appendLog(`Queued ${payload.created_count} run(s): ${payload.tickers.join(', ')}`);
        await loadRunHistory();
        await loadSystemStatus();
        await loadDashboard();
        await loadTimeline();
        await loadBriefing();
    } catch (e) {
        alert(`Failed to queue batch runs: ${e.message}`);
    } finally {
        manualButton.disabled = false;
        watchlistButton.disabled = false;
    }
}

async function executeAnalysis(body) {
    document.getElementById('start-btn').disabled = true;
    document.getElementById('start-btn').textContent = 'Running...';

    reportSections = {};
    resetRunAnnotationForm();
    resetFollowUpChat('Open a saved run, then ask follow-up questions about that analysis.');
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
        rememberRecentlyViewedItem({
            kind: 'run',
            id: run.run_id,
            title: `${run.ticker} · ${run.date}`,
            subtitle: run.signal || run.status,
            run_id: run.run_id,
            ticker: run.ticker,
        });
        loadRecentlyViewed();
        document.getElementById('ticker').value = run.ticker;
        document.getElementById('asset-type-hint').textContent = detectAssetType(run.ticker) !== 'stock'
            ? `Detected: ${detectAssetType(run.ticker)}`
            : '';
        renderRunStatus(run);
        void loadTickerHome(run.ticker);
        void loadPinnedRuns();
        loadRunAnnotation(run.run_id);
        prepareReviewContext(run);
        prepareFollowUpChat(run);
        prepareNotesContext(run);
        prepareCommentsContext(run);
    } catch (e) {
        alert(`Failed to load run: ${e.message}`);
    }
}

function renderRunStatus(run) {
    reportSections = run.report_sections || {};
    syncPublicShareActions(run);
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

    currentRunAnnotation = run.annotation || null;
    document.getElementById('annotation-label').value = run.annotation?.label || '';
    document.getElementById('annotation-summary').value = run.annotation?.summary || '';
    document.getElementById('annotation-next-step').value = run.annotation?.next_step || '';

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

async function loadRunAnnotation(runId) {
    try {
        const resp = await fetch(buildApiUrl(`/api/runs/${runId}`));
        if (!resp.ok) {
            throw new Error(resp.statusText);
        }
        const run = await resp.json();
        currentRunAnnotation = run.annotation || null;
        document.getElementById('annotation-label').value = run.annotation?.label || '';
        document.getElementById('annotation-summary').value = run.annotation?.summary || '';
        document.getElementById('annotation-next-step').value = run.annotation?.next_step || '';
    } catch {
        resetRunAnnotationForm();
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
            resetRunAnnotationForm();
            resetFollowUpChat('Open a saved run, then ask follow-up questions about that analysis.');
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
    currentPublicRunShare = null;
    document.getElementById('revoke-public-run-link').style.display = 'none';
    document.getElementById('start-btn').disabled = false;
    document.getElementById('start-btn').textContent = 'Start Analysis';
}
