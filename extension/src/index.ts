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
import {
  loadState,
  confirmMapping,
  correctMapping,
  getBaseUrl,
  ConfirmedMapping,
} from './stateStore';
import {
  CorrectionDropdown,
  positionDropdownBelow,
} from './correctionWidget';

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

// ── 백엔드 응답 타입 ────────────────────────────────────
interface AnalyzeResponseEntry {
  path: string;
  source: 'llm' | 'human';
  confidence: number;
}

type AnalyzeResponse = Record<string, AnalyzeResponseEntry | string>;

// ── 백엔드 RAG 분석 호출 (state-aware) ─────────────────
async function fetchModuleMapping(
  panel: NotebookPanel
): Promise<Map<string, ConfirmedMapping>> {
  const funcs = collectFunctions(panel);
  const merged = new Map<string, ConfirmedMapping>();
  if (funcs.length === 0) return merged;

  const baseUrl = getBaseUrl();

  // 1) Pull confirmed mappings from backend state.
  const state = await loadState(baseUrl);
  for (const [fn, entry] of state.mappings.entries()) {
    merged.set(fn, entry);
  }

  // 2) Find functions still needing LLM/RAG analysis.
  const unresolved = funcs.filter((f) => !merged.has(f.funcName));
  if (unresolved.length === 0) return merged;

  // 3) Ask backend to analyze the remainder.
  try {
    const res = await fetch(`${baseUrl}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-XSRFToken': getCookie('_xsrf') ?? '',
      },
      body: JSON.stringify({ functions: unresolved, threshold: 0.95 }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const mapping: AnalyzeResponse = await res.json();
    console.log('[NoteBook_MOD] RAG 매핑 수신:', mapping);

    for (const [funcName, raw] of Object.entries(mapping)) {
      if (typeof raw === 'string') {
        // Backwards-compatible: string path only.
        merged.set(funcName, { path: raw, source: 'llm', confidence: 0.5 });
      } else if (raw && typeof raw === 'object') {
        merged.set(funcName, {
          path: raw.path,
          source: raw.source ?? 'llm',
          confidence: typeof raw.confidence === 'number' ? raw.confidence : 0.5,
        });
      }
    }
  } catch (e) {
    console.warn('[NoteBook_MOD] 백엔드 연결 실패, 규칙 기반 폴백:', e);
    // Fallback: rule-based path inference, low confidence.
    unresolved.forEach((f) => {
      if (!merged.has(f.funcName)) {
        merged.set(f.funcName, {
          path: inferFilePath(f.funcName, f.isClass),
          source: 'llm',
          confidence: 0.3,
        });
      }
    });
  }

  return merged;
}

export function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|;)\\s*${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

// ── Plugin ───────────────────────────────────────────────
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'notebook-mod:plugin',
  description: 'Auto modularization viewer — RAG + human-in-the-loop state',
  autoStart: true,
  requires: [INotebookTracker, IDocumentManager],

  activate(
    _app: JupyterFrontEnd,
    tracker: INotebookTracker,
    docManager: IDocumentManager
  ) {
    console.log('[NoteBook_MOD] activated ✅  (state-aware + correction UI)');

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
  const moduleMap = await fetchModuleMapping(panel);
  _applyToAllCells(panel, docManager, moduleMap);
}

function _applyToAllCells(
  panel: NotebookPanel,
  docManager: IDocumentManager,
  moduleMap: Map<string, ConfirmedMapping>
): void {
  panel.content.widgets.forEach((cell) => {
    if (!(cell instanceof CodeCell)) return;
    if (attached.has(cell)) return;

    const src = (cell as CodeCell).model.sharedModel.getSource();
    if (!/^\s*(def|class)\s/m.test(src)) return;

    const meta      = readMeta(cell);
    const overrides: ModuleEntry[] = meta?.enabled ? meta.modules : [];

    _inject(cell, overrides, moduleMap, docManager);
  });
}

/** Re-style a badge DOM node based on the latest mapping metadata. */
function styleBadge(
  badgeEl: HTMLElement,
  mapping: ConfirmedMapping
): void {
  badgeEl.classList.toggle(
    'nbmod-uncertain',
    mapping.confidence < 0.8 && mapping.source !== 'human'
  );
  badgeEl.classList.toggle('nbmod-confirmed', mapping.source === 'human');
}

function applyBadgeStyles(
  root: HTMLElement,
  moduleMap: Map<string, ConfirmedMapping>
): void {
  // Run on next frame so CodeMirror has rendered the widgets.
  requestAnimationFrame(() => {
    const badges = root.querySelectorAll<HTMLElement>('.nbmod-badge[data-func]');
    badges.forEach((b) => {
      const fn = b.getAttribute('data-func');
      if (!fn) return;
      const mapping = moduleMap.get(fn);
      if (mapping) styleBadge(b, mapping);
    });
  });
}

function _inject(
  cell: CodeCell,
  overrides: ModuleEntry[],
  moduleMap: Map<string, ConfirmedMapping>,
  docManager: IDocumentManager
): void {
  const cmEditor   = cell.editor as unknown as CodeMirrorEditor;
  const editorView = cmEditor?.editor as EditorView | undefined;
  if (!editorView) return;

  attached.add(cell);

  const baseUrl = getBaseUrl();

  /** Badge click handler — shows a correction dropdown anchored to the badge. */
  const onOpen = (filePath: string) => {
    // Find the badge element that was just clicked.
    const badgeEl = document.activeElement instanceof HTMLElement
      ? document.activeElement.closest<HTMLElement>('.nbmod-badge')
      : null;
    const anchor: HTMLElement =
      badgeEl ?? findBadgeByPath(editorView.dom, filePath) ?? editorView.dom;

    const funcName = anchor.getAttribute('data-func') ?? '';
    const current  = moduleMap.get(funcName) ?? {
      path: filePath,
      source: 'llm' as const,
      confidence: 0.5,
    };

    const dropdown = new CorrectionDropdown({
      funcName,
      currentPath: current.path,
      source: current.source,
      confidence: current.confidence,
      onConfirm: async (p) => {
        try {
          await confirmMapping(baseUrl, funcName, p);
          const next: ConfirmedMapping = {
            path: p,
            source: 'human',
            confidence: 1.0,
          };
          moduleMap.set(funcName, next);
          styleBadge(anchor, next);
          // Also open the file after confirmation.
          docManager.openOrReveal(p, 'default', undefined, { mode: 'split-right' });
        } catch (e) {
          console.error('[NoteBook_MOD] confirm 실패:', e);
        }
      },
      onCorrect: async (newPath) => {
        try {
          await correctMapping(baseUrl, funcName, current.path, newPath);
          const next: ConfirmedMapping = {
            path: newPath,
            source: 'human',
            confidence: 1.0,
          };
          moduleMap.set(funcName, next);
          styleBadge(anchor, next);
          // Refresh badge label text in DOM.
          const hint = anchor.querySelector<HTMLElement>('.nbmod-badge__hint');
          if (hint) hint.textContent = ` · ${newPath}`;
        } catch (e) {
          console.error('[NoteBook_MOD] correct 실패:', e);
        }
      },
    });

    positionDropdownBelow(dropdown, anchor);
    document.body.appendChild(dropdown.getElement());
  };

  const onExpand = (funcName: string, view: EditorView) => {
    const entry = overrides.find((m) => m.funcName === funcName);
    if (entry) expandFunction(funcName, entry.sourceCode, view);
  };

  // overrides → 메타데이터 우선, 없으면 state/RAG 매핑
  const mergedOverrides: ModuleEntry[] = overrides.length > 0
    ? overrides
    : [...moduleMap.entries()].map(([funcName, info]) => ({
        funcName,
        filePath: info.path,
        sourceCode: '',
      }));

  const stateField = makeModuleStateField(mergedOverrides, onOpen, onExpand);
  editorView.dispatch({ effects: StateEffect.appendConfig.of(stateField) });

  applyBadgeStyles(editorView.dom, moduleMap);
}

/** Locate a badge DOM whose hint contains the given path (fallback anchor). */
function findBadgeByPath(root: HTMLElement, path: string): HTMLElement | null {
  const badges = root.querySelectorAll<HTMLElement>('.nbmod-badge');
  for (const b of Array.from(badges)) {
    const hint = b.querySelector('.nbmod-badge__hint');
    if (hint && hint.textContent && hint.textContent.includes(path)) {
      return b;
    }
  }
  return null;
}

export default plugin;
