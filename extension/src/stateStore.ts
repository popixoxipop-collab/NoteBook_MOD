import { PageConfig } from '@jupyterlab/coreutils';

/** Confirmed mapping entry, source can be llm-suggested or human-confirmed. */
export interface ConfirmedMapping {
  path: string;
  source: 'llm' | 'human';
  confidence: number;
}

/** Category definition for module organization. */
export interface CategoryEntry {
  name: string;
  description: string;
}

/** Local cache of backend State. */
export interface StateStore {
  mappings: Map<string, ConfirmedMapping>;
  categories: CategoryEntry[];
}

// ── helpers ─────────────────────────────────────────────────
function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|;)\\s*${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

function jsonHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-XSRFToken': getCookie('_xsrf') ?? '',
  };
}

export function getBaseUrl(): string {
  return `${PageConfig.getBaseUrl()}notebook-mod`;
}

// ── shapes returned by backend ──────────────────────────────
interface RawStateResponse {
  mappings?: Record<string, ConfirmedMapping>;
  categories?: CategoryEntry[];
}

// ── API ─────────────────────────────────────────────────────

/** Load full backend state. Returns an empty store on failure. */
export async function loadState(baseUrl: string): Promise<StateStore> {
  const empty: StateStore = { mappings: new Map(), categories: [] };
  try {
    const res = await fetch(`${baseUrl}/state`, {
      method: 'GET',
      headers: jsonHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: RawStateResponse = await res.json();
    const mappings = new Map<string, ConfirmedMapping>();
    if (data.mappings) {
      for (const [funcName, entry] of Object.entries(data.mappings)) {
        mappings.set(funcName, entry);
      }
    }
    return {
      mappings,
      categories: data.categories ?? [],
    };
  } catch (e) {
    console.warn('[NoteBook_MOD] loadState 실패:', e);
    return empty;
  }
}

/** Confirm a mapping (user approved the suggested badge). */
export async function confirmMapping(
  baseUrl: string,
  funcName: string,
  path: string
): Promise<void> {
  const res = await fetch(`${baseUrl}/state`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ funcName, path, action: 'confirm' }),
  });
  if (!res.ok) {
    throw new Error(`confirmMapping failed: HTTP ${res.status}`);
  }
}

/** Correct a mapping (user changed the suggested path). */
export async function correctMapping(
  baseUrl: string,
  funcName: string,
  fromPath: string,
  toPath: string
): Promise<void> {
  const res = await fetch(`${baseUrl}/state`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ funcName, path: toPath, fromPath, action: 'correct' }),
  });
  if (!res.ok) {
    throw new Error(`correctMapping failed: HTTP ${res.status}`);
  }
}

/** Add a new category to backend state. */
export async function addCategory(
  baseUrl: string,
  name: string,
  description: string
): Promise<void> {
  const res = await fetch(`${baseUrl}/categories`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ name, description, action: 'add' }),
  });
  if (!res.ok) {
    throw new Error(`addCategory failed: HTTP ${res.status}`);
  }
}
