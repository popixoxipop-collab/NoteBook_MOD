import { ViewPlugin, ViewUpdate, DecorationSet, EditorView } from '@codemirror/view';
/** 셀 메타데이터에서 읽어오는 모듈 정보 */
export interface ModuleEntry {
    funcName: string;
    filePath: string;
    sourceCode: string;
}
/**
 * def/class 키워드를 감지해 모듈화된 함수 블록을
 * ModuleBadgeWidget으로 교체하는 CodeMirror ViewPlugin.
 */
export declare function makeModuleViewPlugin(entries: ModuleEntry[], onOpen: (path: string) => void, onExpand: (funcName: string, view: EditorView) => void): ViewPlugin<{
    decorations: DecorationSet;
    update(update: ViewUpdate): void;
    buildDecorations(view: EditorView): DecorationSet;
    /**
     * 들여쓰기 기준으로 함수/클래스 블록의 마지막 줄 번호 반환.
     * 첫 줄의 들여쓰기 이상인 줄이 계속되면 블록 내부로 판단.
     */
    findBlockEnd(doc: any, startLine: number): number;
}, undefined>;
/**
 * 특정 함수 뱃지를 해제하고 원본 코드를 복원 (더블클릭 핸들러용).
 */
export declare function expandFunction(funcName: string, sourceCode: string, view: EditorView): void;
//# sourceMappingURL=viewPlugin.d.ts.map