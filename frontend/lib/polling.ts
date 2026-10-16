const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

export function isTerminalState(state: string): boolean {
  return TERMINAL_STATES.has(state);
}

export function shouldKeepPolling(states: string[]): boolean {
  return states.some((state) => !isTerminalState(state));
}

export async function pollUntilTerminal<T extends { state: string }>(
  load: () => Promise<T>,
  options: {
    wait: (ms: number) => Promise<void>;
    intervalMs: number;
    shouldContinue: () => boolean;
  },
): Promise<T> {
  for (;;) {
    const job = await load();
    if (isTerminalState(job.state)) return job;
    if (!options.shouldContinue()) {
      throw new DOMException("The poll was stopped", "AbortError");
    }
    await options.wait(options.intervalMs);
    if (!options.shouldContinue()) {
      throw new DOMException("The poll was stopped", "AbortError");
    }
  }
}
