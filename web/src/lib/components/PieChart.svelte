<script lang="ts">
  import { Chart, Svg, Pie, Tooltip } from 'layerchart';
  import { scaleOrdinal } from 'd3-scale';

  let { data } = $props<{ data: { label: string; value: number }[] }>();

  const colors = [
    '#6366f1', // Indigo
    '#ec4899', // Pink
    '#f59e0b', // Amber
    '#10b981', // Emerald
    '#3b82f6', // Blue
    '#8b5cf6', // Violet
  ];

  const colorScale = scaleOrdinal(colors);
</script>

<div class="h-full w-full">
  <Chart
    {data}
    key="label"
    value="value"
    padding={{ top: 20, right: 20, bottom: 20, left: 20 }}
    tooltip={{ mode: 'none' }}
  >
    <Svg>
      <Pie
        innerRadius={0.6}
        cornerRadius={4}
        padAngle={0.02}
        fill={(d) => colorScale(d.label)}
        let:data
      >
        <!-- Optional labels can go here -->
      </Pie>
    </Svg>
    <Tooltip.Root let:data>
      {#if data}
        <div class="flex items-center gap-2 p-1">
          <div class="w-2 h-2 rounded-full" style="background-color: {colorScale(data.label)}"></div>
          <span class="text-xs text-[#71717a] dark:text-[#a1a1aa] font-medium">{data.label}</span>
          <span class="text-xs font-semibold text-[#18181b] dark:text-white">{data.value}</span>
        </div>
      {/if}
    </Tooltip.Root>
  </Chart>
</div>
