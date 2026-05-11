"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.expandFunction = exports.makeModuleViewPlugin = void 0;
const view_1 = require("@codemirror/view");
const state_1 = require("@codemirror/state");
const badge_1 = require("./badge");
/**
 * def/class 키워드를 감지해 모듈화된 함수 블록을
 * ModuleBadgeWidget으로 교체하는 CodeMirror ViewPlugin.
 */
function makeModuleViewPlugin(entries, onOpen, onExpand) {
    // funcName → entry 빠른 조회
    const entryMap = new Map(entries.map(e => [e.funcName, e]));
    // "def funcName" 또는 "class funcName" 패턴
    const FUNC_PATTERN = /^(def|class)\s+(\w+)/;
    return view_1.ViewPlugin.fromClass(class {
        constructor(view) {
            this.decorations = this.buildDecorations(view);
        }
        update(update) {
            if (update.docChanged || update.viewportChanged) {
                this.decorations = this.buildDecorations(update.view);
            }
        }
        buildDecorations(view) {
            const builder = new state_1.RangeSetBuilder();
            const doc = view.state.doc;
            let lineIdx = 1;
            while (lineIdx <= doc.lines) {
                const line = doc.line(lineIdx);
                const match = FUNC_PATTERN.exec(line.text);
                if (match) {
                    const funcName = match[2];
                    const entry = entryMap.get(funcName);
                    if (entry) {
                        // 함수 블록 끝 줄 탐색 (들여쓰기 기준)
                        const blockEnd = this.findBlockEnd(doc, lineIdx);
                        const from = line.from;
                        const to = doc.line(blockEnd).to;
                        // "def " 또는 "class " 까지는 그대로, 함수명부터 블록 끝까지 교체
                        const defEnd = line.from + match[0].indexOf(funcName);
                        builder.add(defEnd, to, view_1.Decoration.replace({
                            widget: new badge_1.ModuleBadgeWidget(entry.funcName, entry.filePath, entry.sourceCode, onOpen, () => onExpand(funcName, view)),
                            inclusive: false,
                        }));
                        lineIdx = blockEnd + 1;
                        continue;
                    }
                }
                lineIdx++;
            }
            return builder.finish();
        }
        /**
         * 들여쓰기 기준으로 함수/클래스 블록의 마지막 줄 번호 반환.
         * 첫 줄의 들여쓰기 이상인 줄이 계속되면 블록 내부로 판단.
         */
        findBlockEnd(doc, startLine) {
            var _a, _b, _c, _d;
            const firstLine = doc.line(startLine);
            const baseIndent = (_b = (_a = firstLine.text.match(/^(\s*)/)) === null || _a === void 0 ? void 0 : _a[1].length) !== null && _b !== void 0 ? _b : 0;
            let lastBlock = startLine;
            for (let i = startLine + 1; i <= doc.lines; i++) {
                const line = doc.line(i);
                if (line.text.trim() === '')
                    continue; // 빈 줄은 스킵
                const indent = (_d = (_c = line.text.match(/^(\s*)/)) === null || _c === void 0 ? void 0 : _c[1].length) !== null && _d !== void 0 ? _d : 0;
                if (indent <= baseIndent)
                    break; // 들여쓰기 감소 → 블록 종료
                lastBlock = i;
            }
            return lastBlock;
        }
    }, {
        decorations: (v) => v.decorations,
    });
}
exports.makeModuleViewPlugin = makeModuleViewPlugin;
/**
 * 특정 함수 뱃지를 해제하고 원본 코드를 복원 (더블클릭 핸들러용).
 */
function expandFunction(funcName, sourceCode, view) {
    const doc = view.state.doc;
    const FUNC_PATTERN = new RegExp(`^(def|class)\\s+${funcName}`);
    for (let i = 1; i <= doc.lines; i++) {
        const line = doc.line(i);
        if (FUNC_PATTERN.test(line.text)) {
            // 현재 뱃지가 차지하는 범위 → sourceCode로 교체
            // (뱃지 범위는 def/class 이후 ~ 블록 끝이므로 줄 전체를 교체)
            view.dispatch({
                changes: { from: line.from, to: line.to, insert: sourceCode },
            });
            return;
        }
    }
}
exports.expandFunction = expandFunction;
//# sourceMappingURL=viewPlugin.js.map