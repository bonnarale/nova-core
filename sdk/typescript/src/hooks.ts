type HookCallback = (...args: unknown[]) => unknown;

export class HookManager {
  private hooks: Map<string, Set<HookCallback>> = new Map();

  register(event: string, callback: HookCallback): void {
    if (!this.hooks.has(event)) {
      this.hooks.set(event, new Set());
    }
    this.hooks.get(event)!.add(callback);
  }

  unregister(event: string, callback: HookCallback): void {
    this.hooks.get(event)?.delete(callback);
  }

  emit(event: string, ...args: unknown[]): unknown[] {
    const results: unknown[] = [];
    this.hooks.get(event)?.forEach((callback) => {
      results.push(callback(...args));
    });
    return results;
  }

  clear(event?: string): void {
    if (event) {
      this.hooks.delete(event);
    } else {
      this.hooks.clear();
    }
  }
}
