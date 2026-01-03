<script lang="ts">
  import { Chart, Svg, Axis, Area, Tooltip, LinearGradient } from 'layerchart';
  import { scaleTime } from 'd3-scale';
  import { curveMonotoneX } from 'd3-shape';

  let { data } = $props<{ data: { date: Date; value: number }[] }>();
</script>

<div class="h-full w-full">
  <Chart
    {data}
    x="date"
    xScale={scaleTime()}
    y="value"
    padding={{ top: 10, right: 10, bottom: 20, left: 10 }}
    tooltip={{ mode: 'bisect-x' }}
  >
    <Svg>
      <LinearGradient class="from-emerald-500/20 to-transparent" vertical let:gradient>
        <Area line={{ class: 'stroke-emerald-500 stroke-2', curve: curveMonotoneX }} fill={gradient} curve={curveMonotoneX} />
      </LinearGradient>
      <Axis placement="bottom" grid={{ class: 'stroke-white/5' }} ticks={5} class="text-[10px] fill-[#71717a]" />
      <Axis placement="left" grid={{ class: 'stroke-white/5' }} ticks={5} class="text-[10px] fill-[#71717a]" />
    </Svg>
    <Tooltip.Root header={(d) => d?.date?.toLocaleDateString() ?? ''} let:data>
      {#if data}
        <Tooltip.Item label="PnL" value={data.value.toFixed(2)} />
      {/if}
    </Tooltip.Root>
  </Chart>
</div>
