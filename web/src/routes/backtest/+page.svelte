<script lang="ts">
  import { 
    Play, Square, Trash2, Download, AlertCircle, ChevronRight, Terminal, 
    Settings, Sliders, Calendar as CalendarIcon, Info, Search, Filter, 
    ArrowUpDown, ExternalLink, CheckCircle2, XCircle, History
  } from 'lucide-svelte';
  import { onMount } from 'svelte';

  let activeTab = $state('new'); // 'new' or 'history'

  const backtests = [
    { id: 'bt-001', date: '2026-01-03 11:20', range: '2025-01-01 to 2025-12-31', symbols: ['NIFTY50'], trades: 145, winRate: '62.4%', pnl: '₹12,450.00', status: 'Completed' },
    { id: 'bt-002', date: '2026-01-02 15:45', range: '2025-11-01 to 2025-11-30', symbols: ['BANKNIFTY', 'SENSEX'], trades: 84, winRate: '54.2%', pnl: '-₹3,210.00', status: 'Completed' },
    { id: 'bt-003', date: '2026-01-02 10:15', range: '2025-01-01 to 2025-12-31', symbols: ['NIFTY50'], trades: 0, winRate: '0%', pnl: '₹0.00', status: 'Failed' },
  ];

  let symbols = $state([
    { id: 'nifty50', name: 'NIFTY 50', enabled: true, capital: 100000, risk: 1.0, multiplier: 2.0 },
    { id: 'banknifty', name: 'BANK NIFTY', enabled: false, capital: 100000, risk: 1.0, multiplier: 2.0 },
    { id: 'sensex', name: 'SENSEX', enabled: false, capital: 100000, risk: 1.0, multiplier: 2.5 },
  ]);

  let fromDate = $state('2025-01-01');
  let toDate = $state('2025-12-31');
  let strategy = $state('option');
  let isRunning = $state(false);
  let logs = $state<string[]>([]);
  let consoleElement: HTMLDivElement;

  async function runBacktest() {
    if (isRunning) return;
    
    isRunning = true;
    logs = [`[SYSTEM] Starting ${strategy} backtest...`, '---------------------------------------'];
    
    const config = {
      symbols: symbols.filter(s => s.enabled).map(s => s.id),
      fromDate,
      toDate,
      strategy
    };
    
    try {
      const response = await fetch('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      if (!response.body) return;
      
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const lines = value.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const logLine = line.replace('data: ', '').trim();
            if (logLine) {
              logs = [...logs, logLine];
              setTimeout(() => {
                if (consoleElement) consoleElement.scrollTop = consoleElement.scrollHeight;
              }, 0);
              
              if (logLine.startsWith('[DONE]')) {
                isRunning = false;
              }
            }
          }
        }
      }
    } catch (err) {
      logs = [...logs, `[ERROR] Failed to execute backtest: ${err}`];
      isRunning = false;
    }
  }

  function clearLogs() {
    logs = [];
  }
</script>

<div class="space-y-6">
  <!-- Tabs Navigation -->
  <div class="flex items-center gap-1 p-1 bg-black/5 dark:bg-white/5 rounded-xl w-fit">
    <button 
      onclick={() => activeTab = 'new'}
      class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all {activeTab === 'new' ? 'bg-white dark:bg-[#09090b] text-indigo-500 shadow-sm' : 'text-[#71717a] hover:text-[#18181b] dark:hover:text-white'}"
    >
      <Play size={14} fill={activeTab === 'new' ? 'currentColor' : 'none'} />
      New Backtest
    </button>
    <button 
      onclick={() => activeTab = 'history'}
      class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all {activeTab === 'history' ? 'bg-white dark:bg-[#09090b] text-indigo-500 shadow-sm' : 'text-[#71717a] hover:text-[#18181b] dark:hover:text-white'}"
    >
      <History size={14} />
      History
    </button>
  </div>

  {#if activeTab === 'new'}
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Sidebar: Config -->
      <div class="lg:col-span-4 space-y-6">
        <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-[#09090b] p-6 space-y-6">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium flex items-center gap-2 text-[#18181b] dark:text-white">
              <Settings size={16} class="text-[#71717a]" />
              Backtest Setup
            </h3>
            <span class="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 text-[10px] font-bold uppercase tracking-wider">
              v1.0
            </span>
          </div>
          
          <div class="space-y-4">
            <!-- Strategy Selection -->
            <div class="space-y-2">
              <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider">Strategy</label>
              <select bind:value={strategy} class="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm text-[#18181b] dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 appearance-none">
                <option value="option">Option Strategy</option>
                <option value="market_structure">Market Structure</option>
                <option value="trend_momentum">Trend Momentum</option>
              </select>
            </div>

            <!-- Date Range -->
            <div class="space-y-2">
              <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider flex items-center gap-1">
                <CalendarIcon size={12} />
                Date Range
              </label>
              <div class="grid grid-cols-2 gap-2">
                <input type="date" bind:value={fromDate} class="bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-md px-3 py-1.5 text-xs text-[#18181b] dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                <input type="date" bind:value={toDate} class="bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-md px-3 py-1.5 text-xs text-[#18181b] dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
            </div>

            <!-- Indices Config -->
            <div class="space-y-3">
              <label class="text-[10px] uppercase font-bold text-[#71717a] tracking-wider">Indices & Parameters</label>
              {#each symbols as symbol}
                <div class="p-4 rounded-xl border border-black/5 dark:border-white/5 bg-black/[0.01] dark:bg-white/[0.01] space-y-4">
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-[#18181b] dark:text-white">{symbol.name}</span>
                    <label class="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" bind:checked={symbol.enabled} class="sr-only peer">
                      <div class="w-8 h-4 bg-black/10 dark:bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-indigo-500"></div>
                    </label>
                  </div>
                  
                  {#if symbol.enabled}
                    <div class="grid grid-cols-2 gap-3 pt-2">
                      <div class="space-y-1">
                        <span class="text-[10px] text-[#71717a]">Capital</span>
                        <input type="number" bind:value={symbol.capital} class="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded px-2 py-1 text-xs text-[#18181b] dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                      </div>
                      <div class="space-y-1">
                        <span class="text-[10px] text-[#71717a]">ATR Mult.</span>
                        <input type="number" step="0.1" bind:value={symbol.multiplier} class="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded px-2 py-1 text-xs text-[#18181b] dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                      </div>
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </div>

          <button 
            onclick={runBacktest}
            disabled={isRunning || !symbols.some(s => s.enabled)}
            class="w-full flex items-center justify-center gap-2 py-3 bg-indigo-500 hover:bg-indigo-600 disabled:bg-black/10 dark:disabled:bg-[#27272a] disabled:text-[#71717a] rounded-xl text-sm font-bold text-white transition-all shadow-lg shadow-indigo-500/20 active:scale-[0.98]"
          >
            {#if isRunning}
              <div class="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
              Executing...
            {:else}
              <Play size={16} fill="currentColor" />
              Execute Backtest
            {/if}
          </button>
        </div>

        <div class="p-4 rounded-xl border border-indigo-500/10 bg-indigo-500/[0.05] dark:bg-indigo-500/[0.02] flex gap-3">
          <Info size={18} class="text-indigo-500 shrink-0" />
          <p class="text-[11px] text-[#71717a] dark:text-[#a1a1aa] leading-relaxed">
            Results will be logged below. You can view the full combined performance summary in the console once the execution finishes.
          </p>
        </div>
      </div>

      <!-- Main Content: Console -->
      <div class="lg:col-span-8 flex flex-col h-[750px]">
        <div class="flex-1 rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-[#09090b] overflow-hidden flex flex-col shadow-2xl dark:shadow-none">
          <div class="px-6 py-4 border-b border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-[#0c0c0e] flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="flex gap-1.5">
                <div class="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                <div class="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                <div class="w-3 h-3 rounded-full bg-[#27c93f]"></div>
              </div>
              <div class="h-4 w-px bg-black/10 dark:bg-white/10 mx-2"></div>
              <Terminal size={14} class="text-[#71717a]" />
              <span class="text-xs font-mono text-[#71717a] dark:text-[#a1a1aa] tracking-tight">backtest_session_{strategy}.log</span>
            </div>
            <div class="flex items-center gap-2">
              <button onclick={clearLogs} class="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg text-[#71717a] hover:text-[#18181b] dark:hover:text-white transition-all group" title="Clear Console">
                <Trash2 size={14} class="group-active:scale-90" />
              </button>
              <button class="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg text-[#71717a] hover:text-[#18181b] dark:hover:text-white transition-all group" title="Save Session">
                <Download size={14} class="group-active:scale-90" />
              </button>
            </div>
          </div>
          
          <div 
            bind:this={consoleElement}
            class="flex-1 overflow-y-auto p-8 font-mono text-[11px] leading-6 selection:bg-indigo-500/30 scroll-smooth"
          >
            {#if logs.length === 0}
              <div class="h-full flex flex-col items-center justify-center text-[#3f3f46] space-y-4">
                <div class="p-4 rounded-full bg-black/[0.02] dark:bg-white/[0.02] border border-black/5 dark:border-white/5">
                  <Terminal size={32} class="opacity-10" />
                </div>
                <p class="text-sm font-medium opacity-40">Awaiting execution parameters...</p>
              </div>
            {/if}
            {#each logs as log}
              <div class="flex gap-4 group">
                <span class="text-[#a1a1aa] dark:text-[#3f3f46] shrink-0 select-none w-4 text-right">{logs.indexOf(log) + 1}</span>
                <div class="whitespace-pre-wrap flex-1 {log.startsWith('[ERROR]') ? 'text-rose-500 dark:text-rose-400 font-bold' : log.startsWith('[SYSTEM]') ? 'text-indigo-600 dark:text-indigo-400 font-bold' : log.includes('WIN') ? 'text-emerald-600 dark:text-emerald-400' : log.includes('LOSS') ? 'text-rose-600 dark:text-rose-400' : 'text-[#18181b] dark:text-[#d1d1d6]'}">
                  {log}
                </div>
              </div>
            {/each}
          </div>
          
          <div class="px-6 py-2 border-t border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-[#0c0c0e] flex items-center justify-between">
            <div class="flex items-center gap-4 text-[10px] text-[#71717a] dark:text-[#52525b] font-medium uppercase tracking-widest">
              <span class="flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 rounded-full {isRunning ? 'bg-indigo-500 animate-pulse' : 'bg-[#71717a] dark:bg-[#52525b]'}"></div>
                {isRunning ? 'Status: Processing' : 'Status: Ready'}
              </span>
              <span>UTF-8</span>
            </div>
            <span class="text-[10px] text-[#71717a] dark:text-[#52525b] font-mono">Lines: {logs.length}</span>
          </div>
        </div>
      </div>
    </div>
  {:else}
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="relative max-w-sm flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" size={16} />
          <input 
            type="text" 
            placeholder="Filter backtest history..." 
            class="w-full pl-10 pr-4 py-2 bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg text-sm text-[#18181b] dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-[#a1a1aa] dark:placeholder:text-[#52525b]"
          />
        </div>
      </div>

      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-[#09090b] overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="text-xs font-medium text-[#71717a] border-b border-black/5 dark:border-white/5 uppercase tracking-wider">
                <th class="px-6 py-4">Execution Date</th>
                <th class="px-6 py-4">Parameters</th>
                <th class="px-6 py-4">Trades</th>
                <th class="px-6 py-4">Win Rate</th>
                <th class="px-6 py-4">Net P&L</th>
                <th class="px-6 py-4">Status</th>
                <th class="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-black/5 dark:divide-white/5">
              {#each backtests as bt}
                <tr class="text-sm hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors group">
                  <td class="px-6 py-4">
                    <div class="flex flex-col">
                      <span class="text-[#18181b] dark:text-[#fafafa] font-medium">{bt.date}</span>
                      <span class="text-[10px] text-[#71717a] uppercase tracking-wide">ID: {bt.id}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex flex-col gap-1">
                      <div class="flex flex-wrap gap-1">
                        {#each bt.symbols as s}
                          <span class="px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/5 text-[10px] text-[#71717a] dark:text-[#a1a1aa] font-medium">{s}</span>
                        {/each}
                      </div>
                      <span class="text-xs text-[#71717a]">{bt.range}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4 text-[#71717a] dark:text-[#a1a1aa] font-mono">{bt.trades}</td>
                  <td class="px-6 py-4 font-medium text-[#18181b] dark:text-white">{bt.winRate}</td>
                  <td class="px-6 py-4 font-medium {bt.pnl.startsWith('-') ? 'text-rose-500' : 'text-emerald-500'}">
                    {bt.pnl}
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-1.5 {bt.status === 'Completed' ? 'text-emerald-500' : 'text-rose-500'}">
                      {#if bt.status === 'Completed'}
                        <CheckCircle2 size={14} />
                      {:else}
                        <XCircle size={14} />
                      {/if}
                      <span class="text-xs font-medium">{bt.status}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4 text-right">
                    <button class="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg text-[#71717a] hover:text-[#18181b] dark:hover:text-white transition-all">
                      <ExternalLink size={16} />
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  div::-webkit-scrollbar {
    width: 6px;
  }
  div::-webkit-scrollbar-track {
    background: transparent;
  }
  div::-webkit-scrollbar-thumb {
    background: rgba(0,0,0,0.1);
    border-radius: 10px;
  }
  :global(.dark) div::-webkit-scrollbar-thumb {
    background: #27272a;
  }
  div::-webkit-scrollbar-thumb:hover {
    background: rgba(0,0,0,0.2);
  }
  :global(.dark) div::-webkit-scrollbar-thumb:hover {
    background: #3f3f46;
  }
  select option {
    background: white;
    color: #18181b;
  }
  :global(.dark) select option {
    background: #0c0c0e;
    color: white;
  }
</style>
