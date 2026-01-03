<script lang="ts">
  import tradesData from '$lib/data/trades.json';
  import StatsCard from '$lib/components/StatsCard.svelte';
  import PnLChart from '$lib/components/PnLChart.svelte';
  import DailyPnLChart from '$lib/components/DailyPnLChart.svelte';
  import { ArrowUpRight, ArrowDownRight, Search } from 'lucide-svelte';

  const trades = tradesData.sort((a, b) => new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime());
  
  const totalPnL = trades.reduce((acc, t) => acc + t.pnl, 0);
  const wins = trades.filter(t => t.pnl > 0).length;
  const losses = trades.filter(t => t.pnl <= 0).length;
  const winRate = (wins / trades.length * 100).toFixed(1);
  const totalTrades = trades.length;
  
  const formattedPnL = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    signDisplay: 'always'
  }).format(totalPnL);

  const getStatusColor = (pnl: number) => pnl > 0 ? 'text-emerald-500 bg-emerald-500/10' : 'text-rose-500 bg-rose-500/10';

  // Process data for Cumulative PnL Chart
  let runningPnL = 0;
  const cumulativeData = trades.map(t => {
    runningPnL += t.pnl;
    return {
      date: new Date(t.entry_time),
      value: runningPnL
    };
  });

  // Process data for Daily PnL Chart
  const dailyPnLMap = new Map<string, number>();
  trades.forEach(t => {
    const date = t.entry_time.split('T')[0];
    dailyPnLMap.set(date, (dailyPnLMap.get(date) || 0) + t.pnl);
  });
  const dailyData = Array.from(dailyPnLMap.entries()).map(([date, value]) => ({
    date: new Date(date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
    value
  }));
</script>

<div class="space-y-8">
  <!-- Stats Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <StatsCard 
      title="Total Net P&L" 
      value={formattedPnL} 
      trend={totalPnL > 0 ? 'up' : 'down'} 
      trendValue="12.5%" 
      subValue="vs last month"
    />
    <StatsCard 
      title="Win Rate" 
      value="{winRate}%" 
      subValue="{wins} wins, {losses} losses"
    />
    <StatsCard 
      title="Total Trades" 
      value={totalTrades.toString()} 
      subValue="Active system"
    />
    <StatsCard 
      title="Avg. Profit/Trade" 
      value="₹{(totalPnL / totalTrades).toFixed(2)}" 
      subValue="Net per execution"
    />
  </div>

  <!-- Charts -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="h-80 rounded-xl border border-white/5 bg-[#0c0c0e] p-6 flex flex-col">
      <h3 class="text-sm font-medium text-[#a1a1aa] mb-4">Cumulative P&L</h3>
      <div class="flex-1 min-h-0">
        <PnLChart data={cumulativeData} />
      </div>
    </div>
    <div class="h-80 rounded-xl border border-white/5 bg-[#0c0c0e] p-6 flex flex-col">
      <h3 class="text-sm font-medium text-[#a1a1aa] mb-4">Daily P&L</h3>
      <div class="flex-1 min-h-0">
        <DailyPnLChart data={dailyData} />
      </div>
    </div>
  </div>

  <!-- Recent Trades -->
  <div class="rounded-xl border border-white/5 bg-[#0c0c0e] overflow-hidden">
    <div class="p-6 border-b border-white/5 flex items-center justify-between">
      <h3 class="text-sm font-medium">Recent Trades</h3>
      <div class="relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" size={14} />
        <input 
          type="text" 
          placeholder="Filter trades..." 
          class="pl-9 pr-4 py-1.5 bg-white/5 border-none rounded-md text-xs focus:ring-1 focus:ring-indigo-500 w-64 placeholder:text-[#52525b]"
        />
      </div>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="text-xs font-medium text-[#71717a] border-b border-white/5 uppercase tracking-wider">
            <th class="px-6 py-4">Symbol</th>
            <th class="px-6 py-4">Type</th>
            <th class="px-6 py-4">Pattern</th>
            <th class="px-6 py-4">Entry Time</th>
            <th class="px-6 py-4">Exit Price</th>
            <th class="px-6 py-4 text-right">P&L</th>
            <th class="px-6 py-4 text-center">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-white/5">
          {#each [...trades].reverse() as trade}
            <tr class="text-sm hover:bg-white/[0.02] transition-colors group">
              <td class="px-6 py-4 font-medium text-[#fafafa]">{trade.symbol}</td>
              <td class="px-6 py-4">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold {trade.option_type === 'CALL' ? 'text-emerald-400 bg-emerald-400/10' : 'text-orange-400 bg-orange-400/10'}">
                  {trade.option_type}
                </span>
              </td>
              <td class="px-6 py-4 text-[#a1a1aa] font-mono text-xs">{trade.pattern}</td>
              <td class="px-6 py-4 text-[#71717a]">{new Date(trade.entry_time).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
              <td class="px-6 py-4 text-[#a1a1aa]">₹{trade.exit_price.toFixed(2)}</td>
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
  </div>
</div>
