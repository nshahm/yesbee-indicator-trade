<script lang="ts">
  import tradesData from '$lib/data/trades.json';
  import { Search, Filter, ArrowUpDown, Download, Calendar } from 'lucide-svelte';

  let searchQuery = $state('');
  let symbolFilter = $state('All');
  
  const trades = [...tradesData].sort((a, b) => new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime());
  
  const filteredTrades = $derived(trades.filter(t => {
    const matchesSearch = t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) || 
                         t.pattern.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSymbol = symbolFilter === 'All' || t.symbol === symbolFilter;
    return matchesSearch && matchesSymbol;
  }));

  const symbols = ['All', ...new Set(trades.map(t => t.symbol))];

  const getStatusColor = (pnl: number) => pnl > 0 ? 'text-emerald-500 bg-emerald-500/10' : 'text-rose-500 bg-rose-500/10';
</script>

<div class="space-y-6">
  <!-- Header Actions -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div class="flex items-center gap-4 flex-1">
      <div class="relative flex-1 max-w-sm">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" size={16} />
        <input 
          bind:value={searchQuery}
          type="text" 
          placeholder="Search by symbol or pattern..." 
          class="w-full pl-10 pr-4 py-2 bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-[#a1a1aa] dark:placeholder:text-[#52525b] text-[#18181b] dark:text-white"
        />
      </div>
      <div class="flex items-center bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-1">
        {#each symbols as symbol}
          <button 
            onclick={() => symbolFilter = symbol}
            class="px-3 py-1.5 text-xs font-medium rounded-md transition-all {symbolFilter === symbol ? 'bg-black/10 dark:bg-white/10 text-[#18181b] dark:text-white shadow-sm' : 'text-[#71717a] hover:text-[#18181b] dark:hover:text-[#a1a1aa]'}"
          >
            {symbol}
          </button>
        {/each}
      </div>
    </div>
    
    <div class="flex items-center gap-2">
      <button class="flex items-center gap-2 px-3 py-2 bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg text-xs font-medium text-[#71717a] dark:text-[#a1a1aa] hover:text-[#18181b] dark:hover:text-white hover:bg-black/10 dark:hover:bg-white/10 transition-all">
        <Calendar size={14} />
        Last 30 Days
      </button>
      <button class="flex items-center gap-2 px-3 py-2 bg-indigo-500 hover:bg-indigo-600 rounded-lg text-xs font-medium text-white transition-all">
        <Download size={14} />
        Export CSV
      </button>
    </div>
  </div>

  <!-- Table -->
  <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-[#09090b] overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="text-xs font-medium text-[#71717a] border-b border-black/5 dark:border-white/5 uppercase tracking-wider">
            <th class="px-6 py-4">
              <div class="flex items-center gap-2 cursor-pointer hover:text-[#18181b] dark:hover:text-white transition-colors">
                Date & Time <ArrowUpDown size={12} />
              </div>
            </th>
            <th class="px-6 py-4">Symbol</th>
            <th class="px-6 py-4">Type</th>
            <th class="px-6 py-4">Pattern</th>
            <th class="px-6 py-4">Entry</th>
            <th class="px-6 py-4 text-right">P&L</th>
            <th class="px-6 py-4 text-center">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-black/5 dark:divide-white/5">
          {#each filteredTrades as trade}
            <tr class="text-sm hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors group cursor-default">
              <td class="px-6 py-4">
                <div class="flex flex-col">
                  <span class="text-[#18181b] dark:text-[#fafafa] font-medium">{new Date(trade.entry_time).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                  <span class="text-[10px] text-[#71717a] uppercase tracking-wide">{new Date(trade.entry_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </td>
              <td class="px-6 py-4 font-medium text-[#18181b] dark:text-[#fafafa]">{trade.symbol}</td>
              <td class="px-6 py-4">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold {trade.option_type === 'CALL' ? 'text-emerald-500 dark:text-emerald-400 bg-emerald-500/10 dark:bg-emerald-400/10' : 'text-orange-500 dark:text-orange-400 bg-orange-500/10 dark:bg-orange-400/10'}">
                  {trade.option_type}
                </span>
              </td>
              <td class="px-6 py-4 text-[#71717a] dark:text-[#a1a1aa] font-mono text-xs capitalize">{trade.pattern.replace('is_', '').replace(/_/g, ' ')}</td>
              <td class="px-6 py-4">
                <div class="flex flex-col">
                  <span class="text-[#71717a] dark:text-[#a1a1aa]">₹{trade.entry_price.toFixed(2)}</span>
                  <span class="text-[10px] text-[#71717a]">Exit: ₹{trade.exit_price.toFixed(2)}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-right font-medium {trade.pnl > 0 ? 'text-emerald-500' : 'text-rose-500'}">
                {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
              </td>
              <td class="px-6 py-4">
                <div class="flex justify-center">
                  <span class="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider {getStatusColor(trade.pnl)}">
                    {trade.pnl > 0 ? 'Win' : 'Loss'}
                  </span>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    
    <!-- Empty State -->
    {#if filteredTrades.length === 0}
      <div class="p-20 flex flex-col items-center justify-center text-center">
        <div class="w-12 h-12 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-4">
          <Search size={20} class="text-[#71717a] dark:text-[#3f3f46]" />
        </div>
        <h4 class="text-sm font-medium text-[#71717a] dark:text-[#a1a1aa]">No trades found</h4>
        <p class="text-xs text-[#71717a] mt-1">Try adjusting your filters or search query.</p>
      </div>
    {/if}

    <!-- Pagination -->
    <div class="p-4 border-t border-black/5 dark:border-white/5 flex items-center justify-between">
      <span class="text-xs text-[#71717a]">Showing 1 to {filteredTrades.length} of {filteredTrades.length} entries</span>
      <div class="flex items-center gap-1">
        <button disabled class="px-3 py-1.5 text-xs font-medium text-[#71717a] dark:text-[#3f3f46] cursor-not-allowed">Previous</button>
        <button class="px-3 py-1.5 text-xs font-medium bg-black/5 dark:bg-white/5 text-[#18181b] dark:text-white rounded-md border border-black/10 dark:border-white/10 hover:bg-black/10 dark:hover:bg-white/10 transition-all">Next</button>
      </div>
    </div>
  </div>
</div>
