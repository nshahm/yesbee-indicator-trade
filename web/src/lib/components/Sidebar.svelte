<script lang="ts">
  import { LayoutDashboard, TrendingUp, History, Settings, ChevronRight, PlayCircle, Library, Briefcase } from 'lucide-svelte';
  import { page } from '$app/state';

  const menuItems = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/' },
    { name: 'Analytics', icon: TrendingUp, href: '/analytics' },
    { name: 'Backtest', icon: PlayCircle, href: '/backtest' },
    { name: 'Trade History', icon: History, href: '/history' },
    { name: 'Broker', icon: Briefcase, href: '/broker' },
    { name: 'Settings', icon: Settings, href: '/settings' },
  ];
</script>

<div class="flex flex-col w-64 border-r border-black/5 dark:border-white/5 bg-white dark:bg-[#09090b] h-screen sticky top-0">
  <div class="p-4 flex items-center gap-2 mb-4">
    <div class="w-6 h-6 bg-gradient-to-br from-indigo-500 to-purple-500 rounded flex items-center justify-center">
      <TrendingUp size={14} class="text-white" />
    </div>
    <span class="font-semibold tracking-tight text-[#09090b] dark:text-[#fafafa]">Yesbee Trade</span>
  </div>

  <nav class="flex-1 px-2 space-y-0.5">
    {#each menuItems as item}
      <a
        href={item.href}
        class="flex items-center gap-3 px-2 py-1.5 text-sm font-medium rounded-md transition-colors group {page.url.pathname === item.href ? 'bg-black/5 dark:bg-white/5 text-[#09090b] dark:text-white' : 'text-[#71717a] dark:text-[#a1a1aa] hover:text-[#09090b] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'}"
      >
        <item.icon size={16} />
        <span class="flex-1">{item.name}</span>
        {#if page.url.pathname === item.href}
          <div class="w-1.5 h-1.5 rounded-full bg-indigo-500"></div>
        {/if}
      </a>
    {/each}
  </nav>

  <div class="p-4 border-t border-black/5 dark:border-white/5 mt-auto">
    <button class="w-full flex items-center gap-3 px-2 py-1.5 text-sm font-medium text-[#71717a] dark:text-[#a1a1aa] hover:text-[#09090b] dark:hover:text-white transition-colors group rounded-md hover:bg-black/5 dark:hover:bg-white/5">
      <div class="w-6 h-6 rounded-full bg-gradient-to-tr from-orange-400 to-rose-400"></div>
      <span class="flex-1 text-left">User Profile</span>
      <ChevronRight size={14} class="opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  </div>
</div>
