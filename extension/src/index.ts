import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { CodeCell } from '@jupyterlab/cells';
import { EditorView } from '@codemirror/view';

import { makeModuleViewPlugin, expandFunction } from './viewPlugin';
import { readMeta } from './metadata';

import '../style/index.css';

// ── JupyterLab 플러그인 선언 ─────────────────────────────────
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'notebook-mod:plugin',
  description: 'Inline module viewer for modularized notebooks',
  autoStart: true,
  requires: [INotebookTracker, IDocumentManager],

  activate(
    _app: JupyterFrontEnd,
    tracker: INotebookTracker,
    docManager: IDocumentManager
  ) {
    console.log('[NoteBook_MOD] extension activated');

    // 노트북이 열릴 때마다 실행
    tracker.widgetAdded.connect((_tracker, panel: NotebookPanel) => {
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
function _attachToNotebook(
  panel: NotebookPanel,
  docManager: IDocumentManager
): void {
  const notebook = panel.content;

  // 셀 추가/변경 시 재적용
  notebook.model?.cells.changed.connect(() => {
    _applyToAllCells(notebook, docManager);
  });

  _applyToAllCells(notebook, docManager);
}

function _applyToAllCells(notebook: any, docManager: IDocumentManager): void {
  notebook.widgets.forEach((cell: any) => {
    if (!(cell instanceof CodeCell)) return;

    const meta = readMeta(cell);
    if (!meta?.enabled || meta.modules.length === 0) return;

    _attachViewPlugin(cell, meta.modules, docManager);
  });
}

// ── 개별 셀에 CodeMirror ViewPlugin 주입 ─────────────────────
function _attachViewPlugin(
  cell: CodeCell,
  modules: any[],
  docManager: IDocumentManager
): void {
  const editorView = (cell.editor as any)?.editor as EditorView | undefined;
  if (!editorView) return;

  // 이미 적용됐으면 스킵 (중복 방지)
  if ((editorView as any)._nbmod_attached) return;
  (editorView as any)._nbmod_attached = true;

  const onOpen = (filePath: string) => {
    // 파일을 JupyterLab 우측 split panel에서 열기
    docManager.openOrReveal(filePath, 'default', undefined, {
      mode: 'split-right',
    });
  };

  const onExpand = (funcName: string, view: EditorView) => {
    const entry = modules.find((m) => m.funcName === funcName);
    if (entry) {
      expandFunction(funcName, entry.sourceCode, view);
    }
  };

  const viewPlugin = makeModuleViewPlugin(modules, onOpen, onExpand);

  editorView.dispatch({
    effects: EditorView.scrollIntoView(0), // dummy — ViewPlugin 등록 트리거
  });

  // CodeMirror 6 에 ViewPlugin 동적 추가
  editorView.dispatch({
    effects: (EditorView as any).reconfigure?.of([viewPlugin]) ?? [],
  });
}

export default plugin;
