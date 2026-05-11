import { Cell } from '@jupyterlab/cells';
import { ModuleEntry } from './viewPlugin';

const META_KEY = 'notebook_mod';

export interface CellModMeta {
  enabled: boolean;
  modules: ModuleEntry[];
}

export function readMeta(cell: Cell): CellModMeta | null {
  try {
    // JupyterLab 4: cell.model.getMetadata(key) 또는 cell.model.metadata[key]
    const meta =
      (cell.model as any).getMetadata?.(META_KEY) ??
      (cell.model.metadata as any)?.[META_KEY];
    if (!meta) return null;
    return meta as CellModMeta;
  } catch {
    return null;
  }
}

export function writeMeta(cell: Cell, data: CellModMeta): void {
  try {
    (cell.model as any).setMetadata?.(META_KEY, data) ??
      ((cell.model.metadata as any)[META_KEY] = data);
  } catch {
    // ignore
  }
}

export function isModularized(cell: Cell): boolean {
  return readMeta(cell)?.enabled === true;
}

export function registerModules(cell: Cell, modules: ModuleEntry[]): void {
  writeMeta(cell, { enabled: true, modules });
}

export function unregisterModules(cell: Cell): void {
  writeMeta(cell, { enabled: false, modules: [] });
}
