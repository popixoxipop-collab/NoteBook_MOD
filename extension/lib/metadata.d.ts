import { Cell } from '@jupyterlab/cells';
import { ModuleEntry } from './viewPlugin';
export interface CellModMeta {
    enabled: boolean;
    modules: ModuleEntry[];
}
/** 셀에서 모듈화 메타데이터 읽기 */
export declare function readMeta(cell: Cell): CellModMeta | null;
/** 셀에 모듈화 메타데이터 쓰기 */
export declare function writeMeta(cell: Cell, data: CellModMeta): void;
/** 셀의 모듈화 활성화 여부 확인 */
export declare function isModularized(cell: Cell): boolean;
/**
 * 모듈화된 함수 목록을 셀 메타데이터에 등록.
 * NoteBook_MOD 서버가 모듈화 완료 후 이 함수를 호출.
 */
export declare function registerModules(cell: Cell, modules: ModuleEntry[]): void;
/** 셀의 모듈화 해제 (원본 코드 복원 시) */
export declare function unregisterModules(cell: Cell): void;
//# sourceMappingURL=metadata.d.ts.map