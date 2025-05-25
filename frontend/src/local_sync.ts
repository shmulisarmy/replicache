export class LocalStorageWithIndex<T = any> {
  private prefix: string;
  private indexKey: string;

  constructor(prefix: string) {
    this.prefix = prefix;
    this.indexKey = `__index__:${prefix}`;
  }

  private getIndex(): string[] {
    const raw = localStorage.getItem(this.indexKey);
    return raw ? JSON.parse(raw) as string[] : [];
  }

  private setIndex(index: string[]): void {
    localStorage.setItem(this.indexKey, JSON.stringify(index));
  }

  private getFullKey(id: string): string {
    return `${this.prefix}-${id}`;
  }

  setItem(id: string, value: T): void {
    const fullKey = this.getFullKey(id);
    localStorage.setItem(fullKey, JSON.stringify(value));

    const index = new Set(this.getIndex());
    index.add(fullKey);
    this.setIndex(Array.from(index));
  }

  getItem(id: string): T | null {
    const fullKey = this.getFullKey(id);
    const raw = localStorage.getItem(fullKey);
    return raw ? JSON.parse(raw) as T : null;
  }

  getAllItems(): Record<string, T> {
    const index = this.getIndex();
    const items: Record<string, T> = {};

    for (const key of index) {
      const value = localStorage.getItem(key);
      if (value !== null) {
        items[key] = JSON.parse(value) as T;
      }
    }

    return items;
  }

  removeItem(id: string): void {
    const fullKey = this.getFullKey(id);
    localStorage.removeItem(fullKey);

    const index = new Set(this.getIndex());
    index.delete(fullKey);
    this.setIndex(Array.from(index));
  }

  clearAll(): void {
    const index = this.getIndex();
    for (const key of index) {
      localStorage.removeItem(key);
    }
    localStorage.removeItem(this.indexKey);
  }
}



(window as any).users_store = new LocalStorageWithIndex("users")