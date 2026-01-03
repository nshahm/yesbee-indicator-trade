<script lang="ts">
  import tradesData from '$lib/data/trades.json';
  import StatsCard from '$lib/components/StatsCard.svelte';
  import PieChart from '$lib/components/PieChart.svelte';
  import DailyPnLChart from '$lib/components/DailyPnLChart.svelte';
  import { Shield, Target, Zap, Activity } from 'lucide-svelte';

  const trades = tradesData;
  
  // Basic Metrics
  const totalPnL = trades.reduce((acc, t) => acc + t.pnl, 0);
  const wins = trades.filter(t => t.pnl > 0).length;
  const losses = trades.filter(t => t.pnl <= 0).length;
  const winRate = (wins / trades.length * 100);
  
  const totalProfit = trades.filter(t => t.pnl > 0).reduce((acc, t) => acc + t.pnl, 0);
  const totalLoss = Math.abs(trades.filter(t => t.pnl <= 0).reduce((acc, t) => acc + t.pnl, 0));
  const profitFactor = totalLoss === 0 ? totalProfit : (totalProfit / totalLoss).toFixed(2);

  // Distribution by Symbol
  const symbolCount = new Map<string, number>();
  trades.forEach(t => symbolCount.set(t.symbol, (symbolCount.get(t.symbol) || 0) + 1));
  const symbolData = Array.from(symbolCount.entries()).map(([label, value]) => ({ label, value }));

  // Pattern Performance
  const patternStats = new Map<string, { wins: number, total: number }>();
  trades.forEach(t => {
    const stats = patternStats.get(t.pattern) || { wins: 0, total: 0 };
    if (t.pnl > 0) stats.wins += 1;
    stats.total += 1;
    patternStats.set(t.pattern, stats);
  });
  const patternPerformance = Array.from(patternStats.entries())
    .map(([pattern, stats]) => ({
      pattern: pattern.replace('is_', '').replace(/_/g, ' '),
      winRate: (stats.wins / stats.total * 100).toFixed(1),
      total: stats.total
    }))
    .sort((a, b) => Number(b.winRate) - Number(a.winRate));

</script>

<div class="space-y-8">
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <StatsCard title="Profit Factor" value={profitFactor.toString()} subValue="Gross Profit / Gross Loss" />
    <StatsCard title="Avg Win" value="₹{(totalProfit / wins).toFixed(2)}" subValue="Based on {wins} wins" />
    <StatsCard title="Avg Loss" value="₹{(totalLoss / losses).toFixed(2)}" subValue="Based on {losses} losses" />
    <StatsCard title="Expectancy" value="₹{(totalPnL / trades.length).toFixed(2)}" subValue="Per trade" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Symbol Distribution -->
    <div class="lg:col-span-1 rounded-xl border border-white/5 bg-[#0c0c0e] p-6 flex flex-col">
      <div class="flex items-center gap-2 mb-6">
        <Activity size={16} class="text-indigo-500" />
        <h3 class="text-sm font-medium">Trade Distribution</h3>
      </div>
      <div class="flex-1 min-h-[240px]">
        <PieChart data={symbolData} />
      </div>
      <div class="mt-4 space-y-2">
        {#each symbolData as item}
          <div class="flex items-center justify-between text-xs">
            <span class="text-[#71717a]">{item.label}</span>
            <span class="font-medium">{item.value} trades</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Pattern Analysis -->
    <div class="lg:col-span-2 rounded-xl border border-white/5 bg-[#0c0c0e] p-6">
      <div class="flex items-center gap-2 mb-6">
        <Target size={16} class="text-emerald-500" />
        <h3 class="text-sm font-medium">Pattern Performance</h3>
      </div>
      <div class="space-y-4">
        {#each patternPerformance as item}
          <div class="space-y-1.5">
            <div class="flex justify-between text-xs">
              <span class="text-[#a1a1aa] capitalize">{item.pattern}</span>
              <span class="font-medium">{item.winRate}% Win Rate ({item.total} trades)</span>
            </div>
            <div class="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
              <div 
                class="h-full bg-indigo-500 rounded-full transition-all duration-500" 
                style="width: {item.winRate}%"
              ></div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Detailed Metrics Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="rounded-xl border border-white/5 bg-[#0c0c0e] p-6">
      <div class="flex items-center gap-2 mb-4">
        <Shield size={16} class="text-orange-500" />
        <h3 class="text-sm font-medium">Risk Metrics</h3>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="p-4 rounded-lg bg-white/[0.02] border border-white/5">
          <span class="text-[10px] text-[#71717a] uppercase font-bold">Max Drawdown</span>
          <p class="text-lg font-semibold text-rose-500 mt-1">-₹1,500.00</p>
        </div>
        <div class="p-4 rounded-lg bg-white/[0.02] border border-white/5">
          <span class="text-[10px] text-[#71717a] uppercase font-bold">Sharpe Ratio</span>
          <p class="text-lg font-semibold text-emerald-500 mt-1">1.84</p>
        </div>
      </div>
    </div>
    <div class="rounded-xl border border-white/5 bg-[#0c0c0e] p-6">
      <div class="flex items-center gap-2 mb-4">
        <Zap size={16} class="text-yellow-500" />
        <h3 class="text-sm font-medium">System Efficiency</h3>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="p-4 rounded-lg bg-white/[0.02] border border-white/5">
          <span class="text-[10px] text-[#71717a] uppercase font-bold">Avg Duration</span>
          <p class="text-lg font-semibold mt-1">52m</p>
        </div>
        <div class="p-4 rounded-lg bg-white/[0.02] border border-white/5">
          <span class="text-[10px] text-[#71717a] uppercase font-bold">Recovery Factor</span>
          <p class="text-lg font-semibold mt-1">2.4</p>
        </div>
      </div>
    </div>
  </div>
</div>
