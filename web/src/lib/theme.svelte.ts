const STORAGE_KEY = 'app-theme';

type Theme = 'light' | 'dark';

const initialTheme = typeof localStorage !== 'undefined' 
	? (localStorage.getItem(STORAGE_KEY) as Theme) || 'dark'
	: 'dark';

export const theme = $state({
	current: initialTheme,
	toggle() {
		this.current = this.current === 'dark' ? 'light' : 'dark';
	}
});

$effect.root(() => {
	$effect(() => {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(STORAGE_KEY, theme.current);
			if (theme.current === 'dark') {
				document.documentElement.classList.add('dark');
			} else {
				document.documentElement.classList.remove('dark');
			}
		}
	});
});
