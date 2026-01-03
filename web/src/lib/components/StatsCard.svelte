<script lang="ts">
  import { TrendingUp, TrendingDown } from 'lucide-svelte';
  
  let { title, value, subValue, trend, trendValue } = $props<{
    title: string;
    value: string;
    subValue?: string;
    trend?: 'up' | 'down';
    trendValue?: string;
  }>();
</script>

<div class="p-6 rounded-xl border border-white/5 bg-[#0c0c0e] flex flex-col gap-1">
  <span class="text-xs font-medium text-[#a1a1aa] uppercase tracking-wider">{title}</span>
  <div class="flex items-baseline gap-2">
    <span class="text-2xl font-semibold tracking-tight">{value}</span>
    {#if trend}
      <span class="text-xs font-medium flex items-center gap-0.5 {trend === 'up' ? 'text-emerald-500' : 'text-rose-500'}">
        {#if trend === 'up'}
          <TrendingUp size={12} />
        {:else}
          <TrendingDown size={12} />
        {/if}
        {trendValue}
      </span>
    {/if}
  </div>
  {#if subValue}
    <span class="text-xs text-[#71717a] mt-1">{subValue}</span>
  {/if}
</div>
