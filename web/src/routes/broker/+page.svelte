<script lang="ts">
  import { onMount } from 'svelte';
  import { mode } from '$lib/mode.svelte';
  import { 
    Shield, ExternalLink, Key, User, CheckCircle2, XCircle, 
    Loader2, RefreshCw, Settings, Zap, Globe, Activity,
    Database, Lock, Sliders, Bell, LayoutGrid, AlertTriangle
  } from 'lucide-svelte';

  let config: any = null;
  let options: any = null;
  let activeTab = 'auth';
  let requestToken = '';
  let loading = true;
  let saving = false;
  let authenticating = false;
  let message = { text: '', type: '' };

  const tabs = [
    { id: 'auth', name: 'Authentication', icon: Lock },
    { id: 'trading', name: 'Trading', icon: Zap },
    { id: 'indices', name: 'Indices', icon: LayoutGrid },
    { id: 'connectivity', name: 'Connectivity', icon: Globe },
    { id: 'advanced', name: 'Advanced', icon: Sliders },
    { id: 'live', name: 'Live Trading', icon: Activity }
  ];

  onMount(async () => {
    await Promise.all([fetchConfig(), fetchOptions()]);
  });

  async function fetchConfig() {
    try {
      const res = await fetch('/api/broker/zerodha');
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      config = data;
    } catch (e: any) {
      message = { text: e.message, type: 'error' };
    }
  }

  async function fetchOptions() {
    try {
      const res = await fetch('/api/options');
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      options = data;
    } catch (e: any) {
      message = { text: e.message, type: 'error' };
    } finally {
      loading = false;
    }
  }

  async function saveConfig() {
    saving = true;
    message = { text: '', type: '' };
    try {
      const [configRes, optionsRes] = await Promise.all([
        fetch('/api/broker/zerodha', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config)
        }),
        fetch('/api/options', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(options)
        })
      ]);

      const configData = await configRes.json();
      const optionsData = await optionsRes.json();

      if (configData.error) throw new Error(configData.error);
      if (optionsData.error) throw new Error(optionsData.error);

      message = { text: 'Configuration and Options saved successfully', type: 'success' };
    } catch (e: any) {
      message = { text: e.message, type: 'error' };
    } finally {
      saving = false;
    }
  }

  async function authenticate() {
    if (!requestToken) {
      message = { text: 'Please enter a request token', type: 'error' };
      return;
    }
    authenticating = true;
    message = { text: '', type: '' };
    try {
      const res = await fetch('/api/broker/zerodha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_token: requestToken })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      
      message = { text: 'Authenticated successfully!', type: 'success' };
      requestToken = '';
      await fetchConfig();
    } catch (e: any) {
      message = { text: e.message, type: 'error' };
    } finally {
      authenticating = false;
    }
  }

  function openKiteLogin() {
    if (!config?.kite?.api?.key) {
      message = { text: 'Please save API Key first', type: 'error' };
      return;
    }
    window.open(`https://kite.zerodha.com/connect/login?v=3&api_key=${config.kite.api.key}`, '_blank');
  }
</script>

<div class="p-8 max-w-6xl mx-auto space-y-8">
  {#if mode.isLive}
    <div class="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-4 text-red-500">
      <AlertTriangle size={24} />
      <div>
        <h3 class="font-bold uppercase tracking-wider text-sm">Caution: Live Trading Mode Active</h3>
        <p class="text-xs opacity-80">All actions performed in this mode will execute real trades on your broker account. Please proceed with extreme caution.</p>
      </div>
    </div>
  {/if}

  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-semibold text-white">
        {mode.isLive ? 'Live Broker Management' : 'Test Broker Management'}
      </h1>
      <p class="text-[#a1a1aa] mt-1">
        {mode.isLive 
          ? 'Configure your production Zerodha Kite Connect settings for real trading.' 
          : 'Configure your sandbox/test Zerodha Kite Connect settings for paper trading.'}
      </p>
    </div>
    
    <div class="flex items-center gap-3">
      {#if config}
        <div class="px-3 py-1 rounded-full bg-white/5 border border-white/10 flex items-center gap-2">
          <div class="w-2 h-2 rounded-full {config?.kite?.api?.access_token ? 'bg-emerald-500' : 'bg-rose-500'}"></div>
          <span class="text-xs font-medium text-white uppercase tracking-wider">
            {config?.kite?.api?.access_token ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      {/if}
      <button 
        on:click={saveConfig}
        disabled={saving || loading}
        class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
      >
        {#if saving}
          <Loader2 class="animate-spin" size={14} />
        {/if}
        Save Changes
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <Loader2 class="animate-spin text-indigo-500" size={40} />
    </div>
  {:else if config}
    <div class="flex gap-8">
      <!-- Sidebar Tabs -->
      <div class="w-64 flex flex-col gap-1">
        {#each tabs as tab}
          <button
            on:click={() => activeTab = tab.id}
            class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all {activeTab === tab.id ? 'bg-white/10 text-white border border-white/10' : 'text-[#a1a1aa] hover:text-white hover:bg-white/5 border border-transparent'}"
          >
            <tab.icon size={18} class={activeTab === tab.id ? 'text-indigo-400' : ''} />
            {tab.name}
          </button>
        {/each}
      </div>

      <!-- Tab Content -->
      <div class="flex-1 min-w-0">
        <div class="bg-white/5 border border-white/10 rounded-2xl p-8 space-y-8">
          
          {#if activeTab === 'auth'}
            <div class="space-y-6">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg font-medium text-white">API Credentials</h3>
                  <p class="text-sm text-[#a1a1aa] mt-1">Manage your Kite Connect API keys and authentication.</p>
                </div>
                <button 
                  on:click={openKiteLogin}
                  class="flex items-center gap-2 bg-[#ef4444] hover:bg-[#dc2626] text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  <ExternalLink size={14} />
                  Login to Kite
                </button>
              </div>

              <div class="grid grid-cols-2 gap-6 pt-4">
                <div class="space-y-2">
                  <label class="text-sm text-[#a1a1aa]">API Key</label>
                  <input 
                    type="text" 
                    bind:value={config.kite.api.key}
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all font-mono"
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-sm text-[#a1a1aa]">API Secret</label>
                  <input 
                    type="password" 
                    bind:value={config.kite.api.secret}
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all font-mono"
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-sm text-[#a1a1aa]">User ID</label>
                  <input 
                    type="text" 
                    bind:value={config.kite.api.user_id}
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all font-mono"
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-sm text-[#a1a1aa]">Access Token</label>
                  <input 
                    type="text" 
                    readonly
                    value={config.kite.api.access_token ? `${config.kite.api.access_token.substring(0, 8)}...` : 'Not Authenticated'}
                    class="w-full bg-black/20 border border-white/5 rounded-lg px-4 py-2.5 text-[#71717a] text-sm font-mono cursor-not-allowed"
                  />
                </div>
              </div>

              <div class="mt-8 p-6 bg-indigo-500/5 border border-indigo-500/10 rounded-xl space-y-4">
                <div class="flex items-center gap-2 text-indigo-400">
                  <RefreshCw size={18} />
                  <h4 class="font-medium">Daily Token Exchange</h4>
                </div>
                <p class="text-sm text-[#a1a1aa]">
                  After logging into Kite, you will be redirected to your redirect URL with a <code>request_token</code>. Paste it below to generate a new session access token.
                </p>
                <div class="flex gap-3">
                  <input 
                    type="text" 
                    bind:value={requestToken}
                    placeholder="Enter request_token..."
                    class="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 transition-all font-mono"
                  />
                  <button 
                    on:click={authenticate}
                    disabled={authenticating || !requestToken}
                    class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
                  >
                    {#if authenticating}
                      <Loader2 class="animate-spin" size={14} />
                    {/if}
                    Exchange Token
                  </button>
                </div>
              </div>
            </div>
          {/if}

          {#if activeTab === 'trading'}
            <div class="space-y-8">
              <div>
                <h3 class="text-lg font-medium text-white">Default Trading Parameters</h3>
                <p class="text-sm text-[#a1a1aa] mt-1">Global settings for orders and products.</p>
              </div>

              <div class="grid grid-cols-2 gap-8">
                <div class="space-y-4">
                  <div class="space-y-2">
                    <label class="text-sm text-[#a1a1aa]">Default Exchange</label>
                    <select 
                      bind:value={config.kite.trading.exchange}
                      class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none"
                    >
                      <option value="NSE">NSE</option>
                      <option value="BSE">BSE</option>
                      <option value="NFO">NFO</option>
                      <option value="MCX">MCX</option>
                    </select>
                  </div>
                  <div class="space-y-2">
                    <label class="text-sm text-[#a1a1aa]">Order Type</label>
                    <select 
                      bind:value={config.kite.trading.order_type}
                      class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none"
                    >
                      <option value="MARKET">Market</option>
                      <option value="LIMIT">Limit</option>
                      <option value="SL">SL</option>
                      <option value="SL-M">SL-M</option>
                    </select>
                  </div>
                </div>

                <div class="space-y-4">
                  <div class="space-y-2">
                    <label class="text-sm text-[#a1a1aa]">Product Type</label>
                    <select 
                      bind:value={config.kite.trading.product}
                      class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none"
                    >
                      <option value="MIS">Intraday (MIS)</option>
                      <option value="CNC">Delivery (CNC)</option>
                      <option value="NRML">Normal (NRML)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div class="pt-8 border-t border-white/5">
                <h3 class="text-lg font-medium text-white">Instruments Management</h3>
                <div class="mt-4 p-4 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <LayoutGrid class="text-indigo-400" size={20} />
                    <div>
                      <span class="text-white text-sm font-medium">Selected Symbols</span>
                      <p class="text-xs text-[#a1a1aa]">
                        {config.kite.instruments.symbols.filter(s => options?.indices?.[s.toLowerCase()]?.enabled).length} active symbols in watchlist
                      </p>
                    </div>
                  </div>
                  <span class="text-xs text-[#71717a] font-mono">
                    {config.kite.instruments.symbols.filter(s => options?.indices?.[s.toLowerCase()]?.enabled).join(', ')}
                  </span>
                </div>
              </div>
            </div>
          {/if}

          {#if activeTab === 'indices'}
            <div class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-white">Market Indices</h3>
                <p class="text-sm text-[#a1a1aa] mt-1">Enable or disable indices for scanning and trading.</p>
              </div>

              {#if options && options.indices}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {#each Object.entries(options.indices) as [id, index]}
                    <div class="p-4 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between hover:bg-white/[0.04] transition-colors">
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                          <Activity size={20} />
                        </div>
                        <div>
                          <div class="text-sm font-medium text-white">{index.symbol || id.toUpperCase()}</div>
                          <div class="text-xs text-[#a1a1aa]">{index.description || ''}</div>
                        </div>
                      </div>
                      <label class="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" bind:checked={index.enabled} class="sr-only peer">
                        <div class="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                      </label>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          {#if activeTab === 'connectivity'}
            <div class="space-y-8">
              <div>
                <h3 class="text-lg font-medium text-white">Connectivity & Real-time</h3>
                <p class="text-sm text-[#a1a1aa] mt-1">Configure WebSocket and Polling behavior.</p>
              </div>

              <div class="grid grid-cols-1 gap-8">
                <!-- WebSocket Section -->
                <div class="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-6">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <Activity class="text-emerald-400" size={20} />
                      <h4 class="text-white font-medium">WebSocket Ticker</h4>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" bind:checked={config.kite.websocket.enabled} class="sr-only peer">
                      <div class="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                    </label>
                  </div>
                  
                  <div class="grid grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <label class="text-sm text-[#a1a1aa]">Reconnect Delay (sec)</label>
                      <input type="number" bind:value={config.kite.websocket.reconnect_delay_seconds} class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                    </div>
                    <div class="space-y-2">
                      <label class="text-sm text-[#a1a1aa]">Max Reconnect Attempts</label>
                      <input type="number" bind:value={config.kite.websocket.max_reconnect_attempts} class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                    </div>
                  </div>
                </div>

                <!-- Rate Limiting -->
                <div class="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-6">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <Database class="text-amber-400" size={20} />
                      <h4 class="text-white font-medium">Rate Limiting</h4>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" bind:checked={config.kite.rate_limiting.enabled} class="sr-only peer">
                      <div class="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                    </label>
                  </div>
                  
                  <div class="grid grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <label class="text-sm text-[#a1a1aa]">Requests Per Second</label>
                      <input type="number" bind:value={config.kite.rate_limiting.requests_per_second} class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                    </div>
                    <div class="space-y-2">
                      <label class="text-sm text-[#a1a1aa]">Burst Size</label>
                      <input type="number" bind:value={config.kite.rate_limiting.burst_size} class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          {/if}

          {#if activeTab === 'advanced'}
            <div class="space-y-8">
              <div>
                <h3 class="text-lg font-medium text-white">Advanced System Settings</h3>
                <p class="text-sm text-[#a1a1aa] mt-1">Timeouts, logging, and internal data retention.</p>
              </div>

              <div class="grid grid-cols-2 gap-8">
                <div class="space-y-6">
                  <h4 class="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                    <RefreshCw size={14} /> Timeouts (seconds)
                  </h4>
                  <div class="space-y-4">
                    <div class="flex items-center justify-between">
                      <label class="text-sm text-[#a1a1aa]">Connection</label>
                      <input type="number" bind:value={config.kite.timeouts.connection_timeout_seconds} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                    </div>
                    <div class="flex items-center justify-between">
                      <label class="text-sm text-[#a1a1aa]">Request</label>
                      <input type="number" bind:value={config.kite.timeouts.request_timeout_seconds} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                    </div>
                    <div class="flex items-center justify-between">
                      <label class="text-sm text-[#a1a1aa]">WebSocket</label>
                      <input type="number" bind:value={config.kite.timeouts.websocket_timeout_seconds} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                    </div>
                  </div>
                </div>

                <div class="space-y-6">
                  <h4 class="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                    <Database size={14} /> Data Retention
                  </h4>
                  <div class="space-y-4">
                    <div class="flex items-center justify-between">
                      <label class="text-sm text-[#a1a1aa]">Order History (Days)</label>
                      <input type="number" bind:value={config.kite.data_retention.order_history_days} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                    </div>
                    <div class="flex items-center justify-between">
                      <label class="text-sm text-[#a1a1aa]">Trade History (Days)</label>
                      <input type="number" bind:value={config.kite.data_retention.trade_history_days} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                    </div>
                    <div class="flex items-center justify-between">
                      <label class="text-sm text-[#a1a1aa]">Max Cache (MB)</label>
                      <input type="number" bind:value={config.kite.data_retention.max_cache_size_mb} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                    </div>
                  </div>
                </div>
              </div>

              <div class="pt-8 border-t border-white/5">
                <h4 class="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Settings size={14} /> Logging Configuration
                </h4>
                <div class="grid grid-cols-2 gap-6">
                  <div class="space-y-2">
                    <label class="text-sm text-[#a1a1aa]">Log Level</label>
                    <select bind:value={config.kite.logging.level} class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white text-sm">
                      <option value="DEBUG">Debug</option>
                      <option value="INFO">Info</option>
                      <option value="WARNING">Warning</option>
                      <option value="ERROR">Error</option>
                    </select>
                  </div>
                  <div class="space-y-2">
                    <label class="text-sm text-[#a1a1aa]">Log File Path</label>
                    <input type="text" bind:value={config.kite.logging.file} class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white text-sm font-mono" />
                  </div>
                </div>
              </div>
            </div>
          {/if}

          {#if activeTab === 'live'}
            {#if !mode.isLive}
              <div class="space-y-6">
                <div class="flex items-center gap-3 text-[#a1a1aa]">
                  <Activity size={24} />
                  <h3 class="text-xl font-semibold uppercase tracking-tight">Live Trading Configuration</h3>
                </div>
                
                <div class="p-12 border-2 border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center text-center space-y-4">
                  <div class="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-[#a1a1aa]">
                    <Lock size={24} />
                  </div>
                  <div>
                    <h4 class="text-white font-medium">Live Settings Locked</h4>
                    <p class="text-sm text-[#a1a1aa] max-w-sm mt-1">Enable <strong>LIVE MODE</strong> using the toggle at the top right to access and modify production trading parameters.</p>
                  </div>
                  <button 
                    on:click={() => mode.isLive = true}
                    class="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Enable Live Mode
                  </button>
                </div>
              </div>
            {:else}
              <div class="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3 text-red-500">
                    <Activity size={24} />
                    <h3 class="text-xl font-semibold uppercase tracking-tight">Live Trading Configuration</h3>
                  </div>
                  <div class="flex items-center gap-4">
                    <span class="text-sm font-medium {config.live_trading.enabled ? 'text-emerald-500' : 'text-[#71717a]'}">
                      {config.live_trading.enabled ? 'System Live' : 'System Paused'}
                    </span>
                    <label class="relative inline-flex items-center cursor-pointer scale-110">
                      <input type="checkbox" bind:checked={config.live_trading.enabled} class="sr-only peer">
                      <div class="w-14 h-7 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-rose-600"></div>
                    </label>
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-8">
                  <div class="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-4">
                    <h4 class="text-white font-medium flex items-center gap-2">
                      <Shield class="text-indigo-400" size={18} /> Risk Management
                    </h4>
                    <div class="space-y-3 pt-2">
                      <div class="flex items-center justify-between">
                        <label class="text-sm text-[#a1a1aa]">Max Daily Loss</label>
                        <input type="number" bind:value={config.live_trading.risk_management.max_daily_loss} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                      </div>
                      <div class="flex items-center justify-between">
                        <label class="text-sm text-[#a1a1aa]">Max Loss/Trade</label>
                        <input type="number" bind:value={config.live_trading.risk_management.max_loss_per_trade} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                      </div>
                      <div class="flex items-center justify-between">
                        <label class="text-sm text-[#a1a1aa]">Max Pos Size</label>
                        <input type="number" bind:value={config.live_trading.risk_management.max_position_size} class="w-24 bg-black/40 border border-white/10 rounded px-2 py-1 text-right text-white text-sm" />
                      </div>
                    </div>
                  </div>

                  <div class="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-4">
                    <h4 class="text-white font-medium flex items-center gap-2">
                      <Bell class="text-emerald-400" size={18} /> Notifications
                    </h4>
                    <div class="space-y-4 pt-2">
                      <div class="flex items-center justify-between">
                        <label class="text-sm text-[#a1a1aa]">Enable Alerts</label>
                        <input type="checkbox" bind:checked={config.live_trading.notifications.enabled} class="accent-indigo-500" />
                      </div>
                      <div class="space-y-2">
                        <label class="text-sm text-[#a1a1aa]">Webhook URL</label>
                        <input type="text" bind:value={config.live_trading.notifications.webhook_url} placeholder="https://..." class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm" />
                      </div>
                    </div>
                  </div>
                </div>

                <div class="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-4">
                  <h4 class="text-white font-medium flex items-center gap-2">
                    <Activity class="text-rose-400" size={18} /> Active Live Symbols
                  </h4>
                  <div class="flex flex-wrap gap-2 pt-2">
                    {#each config.live_trading.symbols as symbol}
                      {@const isEnabled = options?.indices?.[symbol.toLowerCase()]?.enabled}
                      <div class="px-3 py-1.5 rounded-lg border flex items-center gap-2 {isEnabled ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-white/5 border-white/10 text-[#71717a]'}">
                        <div class="w-1.5 h-1.5 rounded-full {isEnabled ? 'bg-emerald-500' : 'bg-[#71717a]'}"></div>
                        <span class="text-xs font-medium uppercase">{symbol}</span>
                        {#if !isEnabled}
                          <span class="text-[10px] opacity-50 font-normal">(Disabled in Indices)</span>
                        {/if}
                      </div>
                    {/each}
                  </div>
                  <p class="text-xs text-[#a1a1aa]">Only symbols that are enabled in the <strong>Indices</strong> tab will be active for live trading.</p>
                </div>

                <div class="pt-4">
                  <div class="p-4 rounded-xl bg-rose-500/5 border border-rose-500/10 flex gap-4">
                    <AlertTriangle class="text-rose-500 shrink-0" size={20} />
                    <div>
                      <h5 class="text-rose-500 text-sm font-semibold uppercase tracking-wider">Caution: Live Trading Active</h5>
                      <p class="text-xs text-[#a1a1aa] mt-1">Changes here directly affect live execution. Ensure all risk management rules are vetted before enabling.</p>
                    </div>
                  </div>
                </div>
              </div>
            {/if}
          {/if}

        </div>

        {#if message.text}
          <div class="mt-4 p-4 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2 {message.type === 'success' ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-500' : 'bg-rose-500/10 border border-rose-500/20 text-rose-500'}">
            {#if message.type === 'success'}
              <CheckCircle2 size={18} />
            {:else}
              <XCircle size={18} />
            {/if}
            <span class="text-sm font-medium">{message.text}</span>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
