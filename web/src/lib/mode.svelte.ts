const STORAGE_KEY = 'trading-mode';

const initialLive = typeof localStorage !== 'undefined' 
	? localStorage.getItem(STORAGE_KEY) === 'true'
	: false;

export const mode = $state({
	isLive: initialLive
});

$effect.root(() => {
	$effect(() => {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(STORAGE_KEY, mode.isLive.toString());
		}
	});
});
