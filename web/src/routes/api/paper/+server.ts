import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const PYTHON_API_URL = env.PYTHON_API_URL || 'http://localhost:8000';

export const GET = async ({ url }) => {
    const endpoint = url.searchParams.get('endpoint') || 'status';
    const symbol = url.searchParams.get('symbol');
    
    let targetUrl = `${PYTHON_API_URL}/api/paper/${endpoint}`;
    if (symbol) {
        targetUrl += `?symbol=${symbol}`;
    }

    try {
        const response = await fetch(targetUrl);
        const data = await response.json();
        return json(data);
    } catch (error) {
        console.error('Error proxying to paper API:', error);
        return json({ error: 'Failed to fetch from paper API' }, { status: 500 });
    }
};
