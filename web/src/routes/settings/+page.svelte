<script lang="ts">
  import { Settings, Shield, Globe, Bell, CreditCard, ChevronRight, Save } from 'lucide-svelte';

  let activeTab = $state('General');
  const tabs = ['General', 'Risk Management', 'Indices', 'Notifications'];

  const config = {
    nifty50: {
      enabled: true,
      capital: 100000,
      risk_per_trade: 1.0,
      max_trades_per_day: 10,
      stop_loss_atr: 2.0
    },
    banknifty: {
      enabled: false,
      capital: 100000,
      risk_per_trade: 1.0,
      max_trades_per_day: 10,
      stop_loss_atr: 2.0
    }
  };
</script>

<div class="flex flex-col lg:flex-row gap-8">
  <!-- Sidebar Navigation -->
  <div class="w-full lg:w-64 space-y-1">
    {#each tabs as tab}
      <button 
        onclick={() => activeTab = tab}
        class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all {activeTab === tab ? 'bg-white/10 text-white' : 'text-[#71717a] hover:text-[#a1a1aa] hover:bg-white/5'}"
      >
        <div class="flex items-center gap-3">
          {#if tab === 'General'}<Globe size={16} />
          {:else if tab === 'Risk Management'}<Shield size={16} />
          {:else if tab === 'Indices'}<Settings size={16} />
          {:else if tab === 'Notifications'}<Bell size={16} />
          {/if}
          {tab}
        </div>
        {#if activeTab === tab}
          <ChevronRight size={14} class="text-[#a1a1aa]" />
        {/if}
      </button>
    {/each}
  </div>

  <!-- Content Area -->
  <div class="flex-1 max-w-2xl">
    <div class="rounded-xl border border-white/5 bg-[#0c0c0e] overflow-hidden">
      <div class="p-6 border-b border-white/5 flex items-center justify-between">
        <h3 class="text-sm font-medium">{activeTab} Settings</h3>
        <button class="flex items-center gap-2 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 rounded-md text-xs font-medium text-white transition-all">
          <Save size={14} />
          Save Changes
        </button>
      </div>
      
      <div class="p-6 space-y-6">
        {#if activeTab === 'General'}
          <div class="space-y-4">
            <div class="space-y-1.5">
              <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider" for="system-name">System Name</label>
              <input 
                id="system-name"
                type="text" 
                value="Yesbee Indicator Trade"
                class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider" for="api-key">Broker API Key</label>
              <input 
                id="api-key"
                type="password" 
                value="••••••••••••••••"
                class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
              />
            </div>
          </div>
        {:else if activeTab === 'Risk Management'}
          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
              <div>
                <h4 class="text-sm font-medium">Auto Stop-Loss</h4>
                <p class="text-xs text-[#71717a]">Automatically apply ATR based stop-loss</p>
              </div>
              <div class="w-10 h-5 bg-indigo-500 rounded-full relative cursor-pointer">
                <div class="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow-sm"></div>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider">Default Capital</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a] text-sm">₹</span>
                  <input type="number" value="100000" class="w-full pl-7 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all" />
                </div>
              </div>
              <div class="space-y-1.5">
                <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider">Max Risk %</label>
                <div class="relative">
                  <input type="number" value="1.0" class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all" />
                  <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[#71717a] text-sm">%</span>
                </div>
              </div>
            </div>
          </div>
        {:else if activeTab === 'Indices'}
          <div class="space-y-4">
            {#each Object.entries(config) as [key, value]}
              <div class="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5 group hover:border-white/10 transition-all">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-500 font-bold text-[10px]">
                    {key.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h4 class="text-sm font-medium capitalize">{key}</h4>
                    <p class="text-[10px] text-[#71717a]">ATR Multiplier: {value.stop_loss_atr}</p>
                  </div>
                </div>
                <div class="flex items-center gap-4">
                  <span class="text-[10px] font-bold uppercase tracking-wider {value.enabled ? 'text-emerald-500' : 'text-[#71717a]'}">
                    {value.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  <div class="w-10 h-5 {value.enabled ? 'bg-indigo-500' : 'bg-white/10'} rounded-full relative cursor-pointer transition-all">
                    <div class="absolute {value.enabled ? 'right-0.5' : 'left-0.5'} top-0.5 w-4 h-4 bg-white rounded-full shadow-sm"></div>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div class="p-20 text-center">
            <Bell size={32} class="mx-auto text-white/5 mb-4" />
            <p class="text-xs text-[#71717a]">Notification settings coming soon.</p>
          </div>
        {/if}
      </div>
    </div>

    <!-- Danger Zone -->
    {#if activeTab === 'General'}
      <div class="mt-8 p-6 rounded-xl border border-rose-500/10 bg-rose-500/[0.02] space-y-4">
        <h3 class="text-sm font-medium text-rose-500">Danger Zone</h3>
        <p class="text-xs text-[#71717a]">Resetting the system will clear all trade logs and history. This action cannot be undone.</p>
        <button class="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 rounded-lg text-xs font-semibold transition-all">
          Reset System Data
        </button>
      </div>
    {/if}
  </div>
</div>
