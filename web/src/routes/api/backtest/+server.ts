import { spawn } from 'child_process';
import { env } from '$env/dynamic/private';

export const POST = async ({ request }) => {
    const { symbols, fromDate, toDate, strategy } = await request.json();
    const pythonPath = env.PYTHON_PATH || 'python3';

    const stream = new ReadableStream({
        async start(controller) {
            const runForSymbol = (symbol: string) => {
                return new Promise((resolve) => {
                    const args = ['../backtest/run_backtest.py'];
                    if (strategy) args.push('--strategy', strategy);
                    if (symbol) args.push('--symbol', symbol);
                    if (fromDate) args.push('--from-date', fromDate.replace(/-/g, ''));
                    if (toDate) args.push('--to-date', toDate.replace(/-/g, ''));

                    const child = spawn(pythonPath, args, { cwd: '..' });

                    child.stdout.on('data', (data) => {
                        controller.enqueue(`data: ${data.toString()}\n\n`);
                    });

                    child.stderr.on('data', (data) => {
                        controller.enqueue(`data: [ERROR] ${data.toString()}\n\n`);
                    });

                    child.on('close', (code) => {
                        resolve(code);
                    });
                });
            };

            if (symbols && symbols.length > 0) {
                for (const symbol of symbols) {
                    controller.enqueue(`data: [SYSTEM] Running backtest for ${symbol}...\n\n`);
                    await runForSymbol(symbol);
                }
            } else {
                // Run for all enabled indices in options.yaml (default behavior of run_backtest.py)
                await runForSymbol('');
            }

            controller.enqueue(`data: [DONE] All processes completed\n\n`);
            controller.close();
        }
    });

    return new Response(stream, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    });
};
