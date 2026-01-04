<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { 
        Activity, 
        TrendingUp, 
        TrendingDown, 
        Clock, 
        BarChart3, 
        AlertCircle,
        History,
        LineChart,
        Monitor,
        ArrowUpRight,
        ArrowDownRight,
        Filter,
        RefreshCw,
        Play,
        Square,
        Settings
    } from 'lucide-svelte';
    import { fade, slide } from 'svelte/transition';
    import StatsCard from '$lib/components/StatsCard.svelte';
    import DailyPnLChart from '$lib/components/DailyPnLChart.svelte';

    interface IndexSummary {
        symbol: string;
        current_price: number;
        total_trades: number;
        wins: number;
        losses: number;
        win_rate: number;
        total_pnl: number;
        unrealized_pnl: number;
        net_pnl: number;
        active_trades: number;
        last_update: string;
    }

    interface PaperStatus {
        status: string;
        symbols: string[];
        timeframes: string[];
        completed_trades_count: number;
        active_trades_count: number;
    }

    interface PerformanceData {
        total_trades: number;
        win_rate: number;
        wins: number;
        losses: number;
        total_pnl: number;
        daily_pnl: Record<string, number>;
    }

    // Svelte 5 State
    let status = $state<PaperStatus | null>(null);
    let summaries = $state<Record<string, IndexSummary>>({});
    let trades = $state<any[]>([]);
    let performance = $state<PerformanceData | null>(null);
    let loading = $state(true);
    let activeTab = $state<'monitoring' | 'history' | 'performance'>('monitoring');
    let pollingInterval: any;

    const activeTrades = $derived(trades.filter(t => t.status === 'OPEN'));
    const closedTrades = $derived(trades.filter(t => t.status === 'CLOSED'));

    async function fetchData() {
        try {
            const statusRes = await fetch('/api/paper?endpoint=status');
            status = await statusRes.json();
            
            if (status?.status === 'running') {
                const [summaryRes, tradesRes, perfRes] = await Promise.all([
                    fetch('/api/paper?endpoint=summary'),
                    fetch('/api/paper?endpoint=trades'),
                    fetch('/api/paper?endpoint=performance')
                ]);

                const summaryData = await summaryRes.json();
                summaries = summaryData.indices || {};
                
                trades = await tradesRes.json();
                performance = await perfRes.json();
            }
        } catch (e) {
            console.error('Failed to fetch data', e);
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        fetchData();
        pollingInterval = setInterval(fetchData, 3000); // Poll every 3 seconds
    });

    onDestroy(() => {
        if (pollingInterval) clearInterval(pollingInterval);
    });

    function getPnlColor(pnl: number) {
        if (pnl > 0) return 'text-green-500';
        if (pnl < 0) return 'text-red-500';
        return 'text-[#71717a]';
    }

    function formatDate(dateStr: string) {
        if (!dateStr) return '---';
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    const chartData = $derived(
        performance?.daily_pnl 
            ? Object.entries(performance.daily_pnl)
                .map(([date, value]) => ({ date, value }))
                .sort((a, b) => a.date.localeCompare(b.date))
            : []
    );
    async function handleExit(symbol: string, entryTime: string) {
        if (!confirm(`Are you sure you want to exit the ${symbol} trade?`)) return;
        
        try {
            const res = await fetch(`/api/paper/exit?symbol=${symbol}&entry_time=${entryTime}`, {
                method: 'POST'
            });
            const result = await res.json();
            if (result.success) {
                // Refresh data immediately
                fetchData();
            } else {
                alert(`Failed to exit trade: ${result.message}`);
            }
        } catch (e) {
            console.error('Failed to exit trade', e);
            alert('Failed to exit trade due to network error');
        }
    }
    async function toggleSystem() {
        const action = status?.status === 'running' ? 'stop' : 'start';
        try {
            const res = await fetch(`/api/paper/${action}`, { method: 'POST' });
            const result = await res.json();
            if (result.success) {
                await fetchData();
            } else {
                alert(`Failed to ${action} system: ${result.message}`);
            }
        } catch (e) {
            console.error(`Failed to ${action} system`, e);
        }
    }
</script>

<div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h2 class="text-2xl font-semibold tracking-tight">Paper Trading</h2>
            <p class="text-sm text-[#71717a] dark:text-[#a1a1aa]">Real-time strategy execution on live market data.</p>
        </div>
        
        <div class="flex items-center gap-3">
            <button 
                onclick={toggleSystem}
                class="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all {status?.status === 'running' ? 'bg-rose-500/10 text-rose-500 hover:bg-rose-500/20 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/20'}"
            >
                {#if status?.status === 'running'}
                    <Square size={16} fill="currentColor" />
                    Stop System
                {:else}
                    <Play size={16} fill="currentColor" />
                    Start System
                {/if}
            </button>

            <div class="flex items-center gap-2 bg-black/5 dark:bg-white/5 px-4 py-2 rounded-lg border border-black/5 dark:border-white/5">
                <div class="w-2 h-2 rounded-full {status?.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}"></div>
                <span class="text-xs font-medium uppercase tracking-wider">
                    {status?.status === 'running' ? 'System Live' : 'System Offline'}
                </span>
            </div>
            {#if status?.status === 'running'}
                <button 
                    onclick={fetchData}
                    class="p-2 rounded-lg bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                    title="Refresh Data"
                >
                    <RefreshCw size={16} class={loading ? 'animate-spin' : ''} />
                </button>
            {/if}
        </div>
    </div>

    {#if loading && !status}
        <div class="flex items-center justify-center h-64">
            <Activity class="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
    {:else if !status || status.status !== 'running'}
        <div class="flex flex-col items-center justify-center h-96 bg-black/5 dark:bg-white/5 rounded-3xl border border-dashed border-black/10 dark:border-white/10" in:fade>
            <div class="p-4 bg-white dark:bg-[#09090b] rounded-2xl shadow-sm border border-black/5 dark:border-white/5 mb-6">
                <Monitor size={48} class="text-[#71717a]" />
            </div>
            <h3 class="text-xl font-semibold">Paper Trading Offline</h3>
            <p class="text-sm text-[#71717a] mt-2 text-center max-w-md px-6">
                The simulation engine is currently idle. Start the system to begin tracking live market signals based on your strategy settings.
            </p>
            
            <div class="flex items-center gap-3 mt-8">
                <button 
                    onclick={toggleSystem}
                    class="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold transition-all shadow-lg shadow-indigo-500/20"
                >
                    <Play size={18} fill="currentColor" />
                    Start Paper Trading
                </button>
                <a 
                    href="/settings"
                    class="flex items-center gap-2 px-6 py-3 rounded-xl bg-white dark:bg-[#09090b] border border-black/10 dark:border-white/10 hover:bg-black/5 dark:hover:bg-white/5 font-semibold transition-all"
                >
                    <Settings size={18} />
                    Configure Indices
                </a>
            </div>
        </div>
    {:else}
        <!-- Tabs Navigation -->
        <div class="flex items-center gap-1 p-1 bg-black/5 dark:bg-white/5 rounded-xl w-fit">
            <button 
                onclick={() => activeTab = 'monitoring'}
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all {activeTab === 'monitoring' ? 'bg-white dark:bg-[#09090b] shadow-sm text-indigo-600 dark:text-indigo-400' : 'text-[#71717a] hover:text-[#09090b] dark:hover:text-white'}"
            >
                <Monitor size={16} />
                Monitoring
                {#if activeTrades.length > 0}
                    <span class="ml-1 px-1.5 py-0.5 rounded-full bg-indigo-500 text-white text-[10px]">{activeTrades.length}</span>
                {/if}
            </button>
            <button 
                onclick={() => activeTab = 'history'}
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all {activeTab === 'history' ? 'bg-white dark:bg-[#09090b] shadow-sm text-indigo-600 dark:text-indigo-400' : 'text-[#71717a] hover:text-[#09090b] dark:hover:text-white'}"
            >
                <History size={16} />
                History
            </button>
            <button 
                onclick={() => activeTab = 'performance'}
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all {activeTab === 'performance' ? 'bg-white dark:bg-[#09090b] shadow-sm text-indigo-600 dark:text-indigo-400' : 'text-[#71717a] hover:text-[#09090b] dark:hover:text-white'}"
            >
                <LineChart size={16} />
                Performance
            </button>
        </div>

        {#if activeTab === 'monitoring'}
            <div class="space-y-6" in:fade>
                <!-- Multi-index Cards -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {#each Object.values(summaries) as summary (summary.symbol)}
                        <div class="bg-white dark:bg-[#09090b] rounded-2xl border border-black/5 dark:border-white/5 overflow-hidden transition-all hover:border-indigo-500/30">
                            <div class="p-6 space-y-4">
                                <div class="flex items-start justify-between">
                                    <div>
                                        <h3 class="text-lg font-bold tracking-tight">{summary.symbol}</h3>
                                        <div class="flex items-center gap-2 mt-1">
                                            <span class="text-xs font-medium text-[#71717a]">LTP</span>
                                            <span class="text-sm font-mono font-medium">₹{summary.current_price.toLocaleString()}</span>
                                        </div>
                                    </div>
                                    <div class="p-2 bg-indigo-500/10 rounded-lg">
                                        <Activity size={20} class="text-indigo-500" />
                                    </div>
                                </div>

                                <div class="grid grid-cols-2 gap-4">
                                    <div class="space-y-1">
                                        <span class="text-[10px] uppercase font-bold tracking-wider text-[#71717a]">Active Trades</span>
                                        <p class="text-xl font-semibold">{summary.active_trades}</p>
                                    </div>
                                    <div class="space-y-1">
                                        <span class="text-[10px] uppercase font-bold tracking-wider text-[#71717a]">Unrealized P&L</span>
                                        <p class="text-xl font-semibold {getPnlColor(summary.unrealized_pnl)}">
                                            {summary.unrealized_pnl > 0 ? '+' : ''}{summary.unrealized_pnl.toFixed(2)}
                                        </p>
                                    </div>
                                </div>

                                <div class="pt-4 border-t border-black/5 dark:border-white/5 flex items-center justify-between text-xs text-[#71717a]">
                                    <div class="flex items-center gap-1">
                                        <BarChart3 size={12} />
                                        <span>{summary.total_trades} Completed</span>
                                    </div>
                                    <div class="flex items-center gap-1">
                                        <TrendingUp size={12} class={getPnlColor(summary.total_pnl)} />
                                        <span class={getPnlColor(summary.total_pnl)}>₹{summary.total_pnl.toFixed(0)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>

                <!-- Active Trades Table -->
                <div class="bg-white dark:bg-[#09090b] rounded-2xl border border-black/5 dark:border-white/5 overflow-hidden shadow-sm">
                    <div class="px-6 py-4 border-b border-black/5 dark:border-white/5 flex items-center justify-between bg-black/[0.01] dark:bg-white/[0.01]">
                        <div class="flex items-center gap-2">
                            <Monitor size={18} class="text-indigo-500" />
                            <h3 class="font-semibold">Active Positions</h3>
                        </div>
                        <span class="text-xs font-medium px-2 py-1 rounded-full bg-indigo-500/10 text-indigo-500">
                            {activeTrades.length} Active
                        </span>
                    </div>
                    
                    {#if activeTrades.length === 0}
                        <div class="p-12 text-center">
                            <p class="text-[#71717a] text-sm">No active paper trades at the moment.</p>
                        </div>
                    {:else}
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm text-left">
                                <thead>
                                    <tr class="bg-black/[0.02] dark:bg-white/[0.02] text-[#71717a]">
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider">Symbol</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider">Type</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider">Entry Time</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-right">Entry Price</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-right">Current LTP</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-right">P&L</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-center">Actions</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-black/5 dark:divide-white/5">
                                    {#each activeTrades as trade}
                                        <tr class="hover:bg-black/[0.01] dark:hover:bg-white/[0.01] transition-colors">
                                            <td class="px-6 py-4 font-medium">{trade.symbol}</td>
                                            <td class="px-6 py-4">
                                                <div class="flex flex-col gap-0.5">
                                                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold w-fit {trade.option_type === 'CALL' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}">
                                                        {trade.option_type}
                                                    </span>
                                                    <span class="text-[10px] text-[#71717a] ml-1">{trade.pattern}</span>
                                                </div>
                                            </td>
                                            <td class="px-6 py-4 text-[#71717a] font-mono text-xs">{formatDate(trade.entry_time)}</td>
                                            <td class="px-6 py-4 text-right font-mono text-xs">₹{trade.entry_price.toFixed(2)}</td>
                                            <td class="px-6 py-4 text-right font-mono text-xs">₹{trade.ltp.toFixed(2)}</td>
                                            <td class="px-6 py-4 text-right font-bold {getPnlColor(trade.pnl)}">
                                                {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                                            </td>
                                            <td class="px-6 py-4 text-center">
                                                <button 
                                                    onclick={() => handleExit(trade.symbol, trade.entry_time)}
                                                    class="text-[10px] font-bold text-red-500 hover:bg-red-500/10 px-2 py-1 rounded transition-colors border border-red-500/20"
                                                >
                                                    EXIT
                                                </button>
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                </div>
            </div>
        {:else if activeTab === 'history'}
            <div class="space-y-6" in:fade>
                <div class="bg-white dark:bg-[#09090b] rounded-2xl border border-black/5 dark:border-white/5 overflow-hidden shadow-sm">
                    <div class="px-6 py-4 border-b border-black/5 dark:border-white/5 flex items-center justify-between bg-black/[0.01] dark:bg-white/[0.01]">
                        <div class="flex items-center gap-2">
                            <History size={18} class="text-indigo-500" />
                            <h3 class="font-semibold">Trade History</h3>
                        </div>
                        <div class="flex items-center gap-2">
                            <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-black/5 dark:border-white/5 bg-white dark:bg-[#0c0c0e] hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                                <Filter size={14} />
                                Filter
                            </button>
                        </div>
                    </div>
                    
                    {#if closedTrades.length === 0}
                        <div class="p-12 text-center">
                            <p class="text-[#71717a] text-sm">No completed paper trades found.</p>
                        </div>
                    {:else}
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm text-left">
                                <thead>
                                    <tr class="bg-black/[0.02] dark:bg-white/[0.02] text-[#71717a]">
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider">Symbol</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider">Type</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider">Entry/Exit Time</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-right">Entry Price</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-right">Exit Price</th>
                                        <th class="px-6 py-3 font-medium uppercase text-[10px] tracking-wider text-right">Net P&L</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-black/5 dark:divide-white/5">
                                    {#each closedTrades as trade}
                                        <tr class="hover:bg-black/[0.01] dark:hover:bg-white/[0.01] transition-colors">
                                            <td class="px-6 py-4 font-medium">{trade.symbol}</td>
                                            <td class="px-6 py-4">
                                                <div class="flex flex-col gap-0.5">
                                                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold w-fit {trade.option_type === 'CALL' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}">
                                                        {trade.option_type}
                                                    </span>
                                                    <span class="text-[10px] text-[#71717a] ml-1">{trade.pattern}</span>
                                                </div>
                                            </td>
                                            <td class="px-6 py-4">
                                                <div class="flex flex-col gap-1 font-mono text-[10px] text-[#71717a]">
                                                    <div class="flex items-center gap-1">
                                                        <ArrowUpRight size={10} class="text-green-500" />
                                                        {formatDate(trade.entry_time)}
                                                    </div>
                                                    <div class="flex items-center gap-1">
                                                        <ArrowDownRight size={10} class="text-red-500" />
                                                        {formatDate(trade.exit_time)}
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="px-6 py-4 text-right font-mono text-xs">₹{trade.entry_price.toFixed(2)}</td>
                                            <td class="px-6 py-4 text-right font-mono text-xs">₹{trade.exit_price ? trade.exit_price.toFixed(2) : '---'}</td>
                                            <td class="px-6 py-4 text-right font-bold {getPnlColor(trade.pnl)}">
                                                {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                </div>
            </div>
        {:else if activeTab === 'performance'}
            <div class="space-y-6" in:fade>
                <!-- Performance Overview -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <StatsCard 
                        title="Total P&L" 
                        value="₹{(performance?.total_pnl || 0).toFixed(2)}"
                        subValue="From {performance?.total_trades || 0} trades"
                        trend={performance?.total_pnl && performance.total_pnl >= 0 ? 'up' : 'down'}
                    />
                    <StatsCard 
                        title="Win Rate" 
                        value="{(performance?.win_rate || 0).toFixed(1)}%"
                        subValue="{performance?.wins || 0} Wins / {performance?.losses || 0} Losses"
                    />
                    <StatsCard 
                        title="Avg Trade P&L" 
                        value="₹{(performance?.total_trades ? (performance.total_pnl / performance.total_trades) : 0).toFixed(2)}"
                    />
                    <StatsCard 
                        title="System Status" 
                        value={status?.status === 'running' ? 'Active' : 'Offline'}
                        subValue="Monitoring {status?.symbols.length || 0} symbols"
                    />
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <!-- Daily P&L Chart -->
                    <div class="lg:col-span-2 bg-white dark:bg-[#09090b] rounded-2xl border border-black/5 dark:border-white/5 p-6 space-y-4">
                        <div class="flex items-center justify-between">
                            <h3 class="font-semibold">Daily Performance</h3>
                            <div class="flex items-center gap-2">
                                <span class="w-3 h-3 rounded-sm bg-emerald-500/50"></span>
                                <span class="text-[10px] text-[#71717a]">Profit</span>
                                <span class="w-3 h-3 rounded-sm bg-rose-500/50 ml-2"></span>
                                <span class="text-[10px] text-[#71717a]">Loss</span>
                            </div>
                        </div>
                        <div class="h-64">
                            {#if chartData.length > 0}
                                <DailyPnLChart data={chartData} />
                            {:else}
                                <div class="w-full h-full flex items-center justify-center border border-dashed border-black/10 dark:border-white/10 rounded-xl">
                                    <p class="text-[#71717a] text-sm">Insufficient data for charting</p>
                                </div>
                            {/if}
                        </div>
                    </div>

                    <!-- Strategy Performance -->
                    <div class="bg-white dark:bg-[#09090b] rounded-2xl border border-black/5 dark:border-white/5 p-6 space-y-4">
                        <h3 class="font-semibold">Strategy Stats</h3>
                        <div class="space-y-4">
                            <div class="p-4 rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/5 dark:border-white/5">
                                <span class="text-[10px] uppercase font-bold tracking-wider text-[#71717a]">Active Strategy</span>
                                <p class="text-lg font-semibold mt-1">{status?.strategy || 'Unknown'}</p>
                            </div>
                            
                            <div class="space-y-2">
                                <div class="flex items-center justify-between text-xs">
                                    <span class="text-[#71717a]">Efficiency</span>
                                    <span class="font-medium">{(performance?.win_rate || 0).toFixed(1)}%</span>
                                </div>
                                <div class="w-full h-2 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
                                    <div 
                                        class="h-full bg-indigo-500 transition-all duration-1000" 
                                        style="width: {performance?.win_rate || 0}%"
                                    ></div>
                                </div>
                            </div>

                            <div class="pt-2 grid grid-cols-2 gap-3">
                                <div class="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                                    <span class="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold uppercase tracking-tighter">Wins</span>
                                    <p class="text-xl font-bold text-emerald-600 dark:text-emerald-400">{performance?.wins || 0}</p>
                                </div>
                                <div class="p-3 rounded-lg bg-rose-500/5 border border-rose-500/10">
                                    <span class="text-[10px] text-rose-600 dark:text-rose-400 font-bold uppercase tracking-tighter">Losses</span>
                                    <p class="text-xl font-bold text-rose-600 dark:text-rose-400">{performance?.losses || 0}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    /* Add any custom styles here if needed */
    :global(body) {
        @apply bg-[#fafafa] dark:bg-[#000000];
    }
</style>
