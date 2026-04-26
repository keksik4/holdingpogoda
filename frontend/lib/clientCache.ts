const TTL_MS = 15 * 60 * 1000;
const STORAGE_PREFIX = "pwl-cache:";

interface Entry<T> {
  data: T;
  timestamp: number;
}

const memory = new Map<string, Entry<unknown>>();
const inflight = new Map<string, Promise<unknown>>();

function readSession<T>(key: string): Entry<T> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_PREFIX + key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Entry<T>;
    if (!parsed || typeof parsed.timestamp !== "number") return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeSession<T>(key: string, entry: Entry<T>): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(entry));
  } catch {
    // sessionStorage can fail in private mode or when full — silently drop.
  }
}

export function getCached<T>(key: string): T | null {
  const now = Date.now();
  const memHit = memory.get(key) as Entry<T> | undefined;
  if (memHit && now - memHit.timestamp < TTL_MS) return memHit.data;

  const sessionHit = readSession<T>(key);
  if (sessionHit && now - sessionHit.timestamp < TTL_MS) {
    memory.set(key, sessionHit);
    return sessionHit.data;
  }
  return null;
}

export function setCached<T>(key: string, data: T): void {
  const entry: Entry<T> = { data, timestamp: Date.now() };
  memory.set(key, entry);
  writeSession(key, entry);
}

export async function cachedFetchJson<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  const cached = getCached<T>(key);
  if (cached !== null) return cached;

  const existing = inflight.get(key) as Promise<T> | undefined;
  if (existing) return existing;

  const promise = fetcher()
    .then((data) => {
      setCached(key, data);
      return data;
    })
    .finally(() => {
      inflight.delete(key);
    });
  inflight.set(key, promise);
  return promise;
}

export function primeCache<T>(key: string, data: T): void {
  if (getCached<T>(key) !== null) return;
  setCached(key, data);
}
