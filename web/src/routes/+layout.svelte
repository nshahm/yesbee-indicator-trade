<script lang="ts">
	import '../app.css';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { page } from '$app/state';
	import { mode } from '$lib/mode.svelte';
	import { theme } from '$lib/theme.svelte';
	import { Sun, Moon } from 'lucide-svelte';
	
	let { children } = $props();

	const titles: Record<string, string> = {
		'/': 'Dashboard',
		'/analytics': 'Analytics',
		'/backtest': 'Backtest',
		'/history': 'Trade History',
		'/backtest/history': 'Backtest History',
		'/settings': 'Settings'
	};
</script>

<svelte:head>
	<title>Yesbee Indicator Trade | {titles[page.url.pathname] || 'Dashboard'}</title>
</svelte:head>

<div class="flex min-h-screen bg-white dark:bg-[#09090b] text-[#18181b] dark:text-[#fafafa] selection:bg-indigo-500/10 font-sans antialiased">
	<Sidebar />
	<main class="flex-1 flex flex-col min-w-0">
		<header class="h-14 border-b border-black/5 dark:border-white/5 flex items-center justify-between px-8 sticky top-0 bg-white/80 dark:bg-[#09090b]/80 backdrop-blur-md z-10">
			<h1 class="text-sm font-medium text-[#71717a] dark:text-[#a1a1aa]">{titles[page.url.pathname] || 'Dashboard'}</h1>
			
			<div class="flex items-center gap-4">
				<button 
					onclick={() => theme.toggle()}
					class="p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 text-[#71717a] dark:text-[#a1a1aa] transition-colors"
					aria-label="Toggle Theme"
				>
					{#if theme.current === 'dark'}
						<Sun size={18} />
					{:else}
						<Moon size={18} />
					{/if}
				</button>

				<div class="h-6 w-px bg-black/5 dark:bg-white/10"></div>

				<div class="flex items-center gap-2">
					<button 
						onclick={() => mode.isLive = !mode.isLive}
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/20 {mode.isLive ? 'bg-red-500' : 'bg-black/10 dark:bg-white/10'}"
					>
						<span class="sr-only">Toggle Live Mode</span>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {mode.isLive ? 'translate-x-6' : 'translate-x-1'}"
						></span>
					</button>
					<span class="text-xs font-medium {mode.isLive ? 'text-red-500' : 'text-[#71717a] dark:text-[#a1a1aa]'}">
						{mode.isLive ? 'LIVE' : 'TEST'}
					</span>
				</div>
			</div>
		</header>
		<div class="p-8">
			{@render children()}
		</div>
	</main>
</div>
