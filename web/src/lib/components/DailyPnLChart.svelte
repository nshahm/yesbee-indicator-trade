<script lang="ts">
  import { Chart, Svg, Axis, Bars, Tooltip } from 'layerchart';
  import { scaleBand } from 'd3-scale';

  let { data } = $props<{ data: { date: string; value: number }[] }>();
</script>

<div class="h-full w-full">
  <Chart
    {data}
    x="date"
    xScale={scaleBand().padding(0.4)}
    y="value"
    padding={{ top: 10, right: 10, bottom: 20, left: 10 }}
    tooltip={{ mode: 'band' }}
  >
    <Svg>
      <Axis placement="bottom" grid={{ class: 'stroke-black/5 dark:stroke-white/5' }} class="text-[10px] fill-[#71717a]" />
      <Axis placement="left" grid={{ class: 'stroke-black/5 dark:stroke-white/5' }} ticks={5} class="text-[10px] fill-[#71717a]" />
      <Bars class={(d) => d.value >= 0 ? 'fill-emerald-500/50' : 'fill-rose-500/50'} radius={4} />
    </Svg>
    <Tooltip.Root header={(d) => d?.date ?? ''} let:data>
      {#if data}
        <Tooltip.Item label="Daily PnL" value={data.value.toFixed(2)} valueClass={data.value >= 0 ? 'text-emerald-500' : 'text-rose-500'} />
      {/if}
    </Tooltip.Root>
  </Chart>
</div>
