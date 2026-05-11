import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { CodeCell } from '@jupyterlab/cells';
import { CodeMirrorEditor } from '@jupyterlab/codemirror';
import { EditorView } from '@codemirror/view';
import { StateEffect } from '@codemirror/state';

import { makeModuleStateField, expandFunction, ModuleEntry } from './viewPlugin';
import { readMeta } from './metadata';

import '../style/index.css';

const attached = new WeakSet<CodeCell>();

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'notebook-mod:plugin',
  description: 'Auto modularization viewer for Jupyter notebooks',
  autoStart: true,
  requires: [INotebookTracker, IDocumentManager],

  activate(
    _app: JupyterFrontEnd,
    tracker: INotebookTracker,
    docManager: IDocumentManager
  ) {
    console.log('[NoteBook_MOD] activated ✅  (rule-based auto mode)');

    tracker.widgetAdded.connect((_t, panel: NotebookPanel) => {
      panel.context.ready.then(() => {
        setTimeout(() => _applyToAllCells(panel, docManager), 800);
        panel.content.model?.cells.changed.connect(() => {
          setTimeout(() => _applyToAllCells(panel, docManager), 400);
        });
      });
    });

    tracker.forEach((panel) => {
      panel.context.ready.then(() => {
        setTimeout(() => _applyToAllCells(panel, docManager), 800);
      });
    });
  },
};

/**
 * 노트북의 모든 code cell에 자동 모듈화 뷰를 적용.
 * 메타데이터가 있으면 filePath/sourceCode 오버라이드로만 사용.
 * 메타데이터 없어도 알고리즘이 자동으로 경로를 추론.
 */
function _applyToAllCells(panel: NotebookPanel, docManager: IDocumentManager): void {
  panel.content.widgets.forEach((cell) => {
    if (!(cell instanceof CodeCell)) return;
    if (attached.has(cell)) return;

    // 셀 소스에 def/class가 하나라도 있는 경우만 처리 (빈 셀, import 전용 셀 등 스킵)
    const src = (cell as CodeCell).model.sharedModel.getSource();
    if (!/^\s*(def|class)\s/m.test(src)) return;

    // 메타데이터는 선택적 오버라이드
    const meta      = readMeta(cell);
    const overrides: ModuleEntry[] = meta?.enabled ? meta.modules : [];

    _inject(cell, overrides, docManager);
  });
}

function _inject(
  cell: CodeCell,
  overrides: ModuleEntry[],
  docManager: IDocumentManager
): void {
  const cmEditor   = cell.editor as unknown as CodeMirrorEditor;
  const editorView = cmEditor?.editor as EditorView | undefined;

  if (!editorView) {
    console.warn('[NoteBook_MOD] EditorView 없음');
    return;
  }

  attached.add(cell);

  const onOpen = (filePath: string) => {
    docManager.openOrReveal(filePath, 'default', undefined, { mode: 'split-right' });
  };

  const onExpand = (funcName: string, view: EditorView) => {
    const entry = overrides.find(m => m.funcName === funcName);
    if (entry) expandFunction(funcName, entry.sourceCode, view);
  };

  const stateField = makeModuleStateField(overrides, onOpen, onExpand);

  editorView.dispatch({
    effects: StateEffect.appendConfig.of(stateField),
  });
}

export default plugin;
