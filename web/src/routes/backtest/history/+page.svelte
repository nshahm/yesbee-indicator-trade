<script lang="ts">
  import { Search, Filter, ArrowUpDown, ExternalLink, Calendar, CheckCircle2, XCircle } from 'lucide-svelte';

  const backtests = [
    { id: 'bt-001', date: '2026-01-03 11:20', range: '2025-01-01 to 2025-12-31', symbols: ['NIFTY50'], trades: 145, winRate: '62.4%', pnl: '₹12,450.00', status: 'Completed' },
    { id: 'bt-002', date: '2026-01-02 15:45', range: '2025-11-01 to 2025-11-30', symbols: ['BANKNIFTY', 'SENSEX'], trades: 84, winRate: '54.2%', pnl: '-₹3,210.00', status: 'Completed' },
    { id: 'bt-003', date: '2026-01-02 10:15', range: '2025-01-01 to 2025-12-31', symbols: ['NIFTY50'], trades: 0, winRate: '0%', pnl: '₹0.00', status: 'Failed' },
  ];
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div class="relative max-w-sm flex-1">
      <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" size={16} />
      <input 
        type="text" 
        placeholder="Filter backtest history..." 
        class="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
      />
    </div>
  </div>

  <div class="rounded-xl border border-white/5 bg-[#0c0c0e] overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="text-xs font-medium text-[#71717a] border-b border-white/5 uppercase tracking-wider">
            <th class="px-6 py-4">Execution Date</th>
            <th class="px-6 py-4">Parameters</th>
            <th class="px-6 py-4">Trades</th>
            <th class="px-6 py-4">Win Rate</th>
            <th class="px-6 py-4">Net P&L</th>
            <th class="px-6 py-4">Status</th>
            <th class="px-6 py-4"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-white/5">
          {#each backtests as bt}
            <tr class="text-sm hover:bg-white/[0.02] transition-colors group">
              <td class="px-6 py-4">
                <div class="flex flex-col">
                  <span class="text-[#fafafa] font-medium">{bt.date}</span>
                  <span class="text-[10px] text-[#71717a] uppercase tracking-wide">ID: {bt.id}</span>
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="flex flex-col gap-1">
                  <div class="flex flex-wrap gap-1">
                    {#each bt.symbols as s}
                      <span class="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-[#a1a1aa] font-medium">{s}</span>
                    {/each}
                  </div>
                  <span class="text-xs text-[#71717a]">{bt.range}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-[#a1a1aa] font-mono">{bt.trades}</td>
              <td class="px-6 py-4 font-medium">{bt.winRate}</td>
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
                <button class="p-2 hover:bg-white/5 rounded-lg text-[#71717a] hover:text-white transition-all">
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
