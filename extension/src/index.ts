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
import { PageConfig } from '@jupyterlab/coreutils';

import { makeModuleStateField, expandFunction, ModuleEntry } from './viewPlugin';
import { inferFilePath } from './algorithm';
import { readMeta } from './metadata';

import '../style/index.css';

const attached = new WeakSet<CodeCell>();

const FUNC_RE = /^(\s*)(def|class)\s+(\w+)/gm;

// ── 노트북에서 모든 함수 목록 수집 ──────────────────────
interface FuncInfo {
  funcName:   string;
  isClass:    boolean;
  sourceCode: string;
}

function collectFunctions(panel: NotebookPanel): FuncInfo[] {
  const result: FuncInfo[] = [];
  panel.content.widgets.forEach((cell) => {
    if (!(cell instanceof CodeCell)) return;
    const src = (cell as CodeCell).model.sharedModel.getSource();
    let m: RegExpExecArray | null;
    FUNC_RE.lastIndex = 0;
    while ((m = FUNC_RE.exec(src)) !== null) {
      const funcName = m[3];
      if (funcName.startsWith('__')) continue;
      result.push({
        funcName,
        isClass:    m[2] === 'class',
        sourceCode: src,
      });
    }
  });
  return result;
}

// ── 백엔드 RAG 분석 호출 ────────────────────────────────
async function fetchModuleMapping(
  panel: NotebookPanel
): Promise<Map<string, string>> {
  const funcs = collectFunctions(panel);
  if (funcs.length === 0) return new Map();

  const baseUrl = PageConfig.getBaseUrl();
  try {
    const res = await fetch(`${baseUrl}notebook-mod/analyze`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json',
                 'X-XSRFToken': getCookie('_xsrf') ?? '' },
      body: JSON.stringify({ functions: funcs, threshold: 0.95 }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const mapping: Record<string, string> = await res.json();
    console.log('[NoteBook_MOD] RAG 매핑 수신:', mapping);
    return new Map(Object.entries(mapping));
  } catch (e) {
    console.warn('[NoteBook_MOD] 백엔드 연결 실패, 규칙 기반 폴백:', e);
    // 폴백: 규칙 기반으로 직접 생성
    const fallback = new Map<string, string>();
    funcs.forEach(f => fallback.set(f.funcName, inferFilePath(f.funcName, f.isClass)));
    return fallback;
  }
}

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|;)\\s*${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

// ── Plugin ───────────────────────────────────────────────
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'notebook-mod:plugin',
  description: 'Auto modularization viewer — RAG-based similarity merging',
  autoStart: true,
  requires: [INotebookTracker, IDocumentManager],

  activate(
    _app: JupyterFrontEnd,
    tracker: INotebookTracker,
    docManager: IDocumentManager
  ) {
    console.log('[NoteBook_MOD] activated ✅  (RAG + rule-based fallback)');

    tracker.widgetAdded.connect((_t, panel: NotebookPanel) => {
      panel.context.ready.then(() => {
        setTimeout(() => _processPanel(panel, docManager), 1000);
      });
    });

    tracker.forEach((panel) => {
      panel.context.ready.then(() => {
        setTimeout(() => _processPanel(panel, docManager), 1000);
      });
    });
  },
};

async function _processPanel(panel: NotebookPanel, docManager: IDocumentManager) {
  // 노트북 전체 함수 분석 → RAG 매핑 취득
  const moduleMap = await fetchModuleMapping(panel);
  _applyToAllCells(panel, docManager, moduleMap);
}

function _applyToAllCells(
  panel: NotebookPanel,
  docManager: IDocumentManager,
  moduleMap: Map<string, string>
): void {
  panel.content.widgets.forEach((cell) => {
    if (!(cell instanceof CodeCell)) return;
    if (attached.has(cell)) return;

    const src = (cell as CodeCell).model.sharedModel.getSource();
    if (!/^\s*(def|class)\s/m.test(src)) return;

    // 메타데이터 오버라이드 (있으면 우선)
    const meta      = readMeta(cell);
    const overrides: ModuleEntry[] = meta?.enabled ? meta.modules : [];

    _inject(cell, overrides, moduleMap, docManager);
  });
}

function _inject(
  cell: CodeCell,
  overrides: ModuleEntry[],
  moduleMap: Map<string, string>,
  docManager: IDocumentManager
): void {
  const cmEditor   = cell.editor as unknown as CodeMirrorEditor;
  const editorView = cmEditor?.editor as EditorView | undefined;
  if (!editorView) return;

  attached.add(cell);

  const onOpen = (filePath: string) => {
    docManager.openOrReveal(filePath, 'default', undefined, { mode: 'split-right' });
  };

  const onExpand = (funcName: string, view: EditorView) => {
    const entry = overrides.find(m => m.funcName === funcName);
    if (entry) expandFunction(funcName, entry.sourceCode, view);
  };

  // overrides → 메타데이터 우선, 없으면 RAG 매핑, 없으면 규칙 기반
  const mergedOverrides: ModuleEntry[] = overrides.length > 0
    ? overrides
    : [...moduleMap.entries()].map(([funcName, filePath]) => ({
        funcName, filePath, sourceCode: '',
      }));

  const stateField = makeModuleStateField(mergedOverrides, onOpen, onExpand);
  editorView.dispatch({ effects: StateEffect.appendConfig.of(stateField) });
}

export default plugin;
