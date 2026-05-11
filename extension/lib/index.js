"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const notebook_1 = require("@jupyterlab/notebook");
const docmanager_1 = require("@jupyterlab/docmanager");
const cells_1 = require("@jupyterlab/cells");
const view_1 = require("@codemirror/view");
const viewPlugin_1 = require("./viewPlugin");
const metadata_1 = require("./metadata");
require("../style/index.css");
// ── JupyterLab 플러그인 선언 ─────────────────────────────────
const plugin = {
    id: 'notebook-mod:plugin',
    description: 'Inline module viewer for modularized notebooks',
    autoStart: true,
    requires: [notebook_1.INotebookTracker, docmanager_1.IDocumentManager],
    activate(_app, tracker, docManager) {
        console.log('[NoteBook_MOD] extension activated');
        // 노트북이 열릴 때마다 실행
        tracker.widgetAdded.connect((_tracker, panel) => {
            panel.context.ready.then(() => {
                _attachToNotebook(panel, docManager);
            });
        });
        // 현재 열려있는 노트북에도 즉시 적용
        tracker.forEach((panel) => {
            panel.context.ready.then(() => {
                _attachToNotebook(panel, docManager);
            });
        });
    },
};
// ── 노트북의 모든 셀에 Extension 부착 ────────────────────────
function _attachToNotebook(panel, docManager) {
    var _a;
    const notebook = panel.content;
    // 셀 추가/변경 시 재적용
    (_a = notebook.model) === null || _a === void 0 ? void 0 : _a.cells.changed.connect(() => {
        _applyToAllCells(notebook, docManager);
    });
    _applyToAllCells(notebook, docManager);
}
function _applyToAllCells(notebook, docManager) {
    notebook.widgets.forEach((cell) => {
        if (!(cell instanceof cells_1.CodeCell))
            return;
        const meta = (0, metadata_1.readMeta)(cell);
        if (!(meta === null || meta === void 0 ? void 0 : meta.enabled) || meta.modules.length === 0)
            return;
        _attachViewPlugin(cell, meta.modules, docManager);
    });
}
// ── 개별 셀에 CodeMirror ViewPlugin 주입 ─────────────────────
function _attachViewPlugin(cell, modules, docManager) {
    var _a, _b, _c;
    const editorView = (_a = cell.editor) === null || _a === void 0 ? void 0 : _a.editor;
    if (!editorView)
        return;
    // 이미 적용됐으면 스킵 (중복 방지)
    if (editorView._nbmod_attached)
        return;
    editorView._nbmod_attached = true;
    const onOpen = (filePath) => {
        // 파일을 JupyterLab 우측 split panel에서 열기
        docManager.openOrReveal(filePath, 'default', undefined, {
            mode: 'split-right',
        });
    };
    const onExpand = (funcName, view) => {
        const entry = modules.find((m) => m.funcName === funcName);
        if (entry) {
            (0, viewPlugin_1.expandFunction)(funcName, entry.sourceCode, view);
        }
    };
    const viewPlugin = (0, viewPlugin_1.makeModuleViewPlugin)(modules, onOpen, onExpand);
    editorView.dispatch({
        effects: view_1.EditorView.scrollIntoView(0), // dummy — ViewPlugin 등록 트리거
    });
    // CodeMirror 6 에 ViewPlugin 동적 추가
    editorView.dispatch({
        effects: (_c = (_b = view_1.EditorView.reconfigure) === null || _b === void 0 ? void 0 : _b.of([viewPlugin])) !== null && _c !== void 0 ? _c : [],
    });
}
exports.default = plugin;
//# sourceMappingURL=index.js.map