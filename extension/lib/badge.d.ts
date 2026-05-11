import { WidgetType } from '@codemirror/view';
/**
 * 모듈화된 함수/클래스를 대체하는 인라인 뱃지 위젯.
 * - hover  → 원본 코드 툴팁 표시
 * - click  → 연결된 .py 파일 열기
 * - dblclick → 뱃지 해제 (인라인 전개)
 */
export declare class ModuleBadgeWidget extends WidgetType {
    private readonly funcName;
    private readonly filePath;
    private readonly sourceCode;
    private readonly onOpen;
    private readonly onExpand;
    constructor(funcName: string, filePath: string, sourceCode: string, onOpen: (path: string) => void, onExpand: () => void);
    toDOM(): HTMLElement;
    private _showTooltip;
    eq(other: ModuleBadgeWidget): boolean;
    ignoreEvent(): boolean;
}
//# sourceMappingURL=badge.d.ts.map