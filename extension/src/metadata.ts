import { Cell } from '@jupyterlab/cells';
// @jupyterlab/cells는 @jupyterlab/notebook의 peer dep으로 포함됨
import { ModuleEntry } from './viewPlugin';

/** 셀 metadata 키 */
const META_KEY = 'notebook_mod';

export interface CellModMeta {
  enabled: boolean;
  modules: ModuleEntry[];  // 이 셀에 포함된 모듈화된 함수 목록
}

/** 셀에서 모듈화 메타데이터 읽기 */
export function readMeta(cell: Cell): CellModMeta | null {
  const meta = cell.model.getMetadata(META_KEY) as CellModMeta | undefined;
  return meta ?? null;
}

/** 셀에 모듈화 메타데이터 쓰기 */
export function writeMeta(cell: Cell, data: CellModMeta): void {
  cell.model.setMetadata(META_KEY, data);
}

/** 셀의 모듈화 활성화 여부 확인 */
export function isModularized(cell: Cell): boolean {
  return readMeta(cell)?.enabled === true;
}

/**
 * 모듈화된 함수 목록을 셀 메타데이터에 등록.
 * NoteBook_MOD 서버가 모듈화 완료 후 이 함수를 호출.
 */
export function registerModules(cell: Cell, modules: ModuleEntry[]): void {
  writeMeta(cell, { enabled: true, modules });
}

/** 셀의 모듈화 해제 (원본 코드 복원 시) */
export function unregisterModules(cell: Cell): void {
  writeMeta(cell, { enabled: false, modules: [] });
}
