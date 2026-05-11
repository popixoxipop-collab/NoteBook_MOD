import {
  EditorView,
  Decoration,
  DecorationSet,
} from '@codemirror/view';
import { StateField, RangeSetBuilder, Text } from '@codemirror/state';
import { ModuleBadgeWidget } from './badge';
import { inferFilePath } from './algorithm';

export interface ModuleEntry {
  funcName: string;
  filePath: string;
  sourceCode: string;
}

const FUNC_PATTERN      = /^(\s*)(def|class)\s+(\w+)/;
const WRITEFILE_PATTERN = /^%%writefile\s+(\S+)/;

/** 함수/클래스 블록의 마지막 줄 인덱스 반환 */
function findBlockEnd(doc: Text, startLine: number): number {
  const baseIndent = (doc.line(startLine).text.match(/^(\s*)/) ?? ['', ''])[1].length;
  let last = startLine;
  for (let i = startLine + 1; i <= doc.lines; i++) {
    const txt = doc.line(i).text;
    if (txt.trim() === '') continue;
    const indent = (txt.match(/^(\s*)/) ?? ['', ''])[1].length;
    if (indent <= baseIndent) break;
    last = i;
  }
  return last;
}

function buildDecorations(
  doc: Text,
  overrideMap: Map<string, ModuleEntry>,  // 메타데이터 오버라이드 (선택)
  onOpen: (path: string) => void,
  onExpand: (funcName: string, view: EditorView) => void
): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  let lineIdx = 1;

  while (lineIdx <= doc.lines) {
    const line = doc.line(lineIdx);

    // ── %%writefile 라벨 ────────────────────────────
    if (WRITEFILE_PATTERN.test(line.text)) {
      builder.add(line.from, line.to, Decoration.mark({ class: 'nbmod-writefile-label' }));
      lineIdx++;
      continue;
    }

    // ── def / class ─────────────────────────────────
    const funcMatch = FUNC_PATTERN.exec(line.text);
    if (funcMatch) {
      const isClass  = funcMatch[2] === 'class';
      const funcName = funcMatch[3];

      // @decorator 줄 포함 (블록 시작 역방향 탐색)
      let blockStart = lineIdx;
      while (blockStart > 1 && doc.line(blockStart - 1).text.trim().startsWith('@')) {
        blockStart--;
      }

      const startLine   = doc.line(blockStart);
      const blockEndIdx = findBlockEnd(doc, lineIdx);
      const endLine     = doc.line(blockEndIdx);
      const rawSource   = doc.sliceString(startLine.from, endLine.to);

      // 메타데이터 오버라이드 우선, 없으면 알고리즘으로 추론
      const override   = overrideMap.get(funcName);
      const filePath   = override?.filePath   ?? inferFilePath(funcName, isClass);
      const sourceCode = override?.sourceCode ?? rawSource;

      builder.add(
        startLine.from,
        endLine.to,
        Decoration.replace({
          widget: new ModuleBadgeWidget(
            funcName, filePath, sourceCode,
            onOpen, (view) => onExpand(funcName, view)
          ),
          block: true,
        })
      );

      lineIdx = blockEndIdx + 1;
      continue;
    }

    lineIdx++;
  }

  return builder.finish();
}

export function makeModuleStateField(
  overrides: ModuleEntry[],
  onOpen: (path: string) => void,
  onExpand: (funcName: string, view: EditorView) => void
) {
  const overrideMap = new Map(overrides.map(e => [e.funcName, e]));

  return StateField.define<DecorationSet>({
    create(state) {
      return buildDecorations(state.doc, overrideMap, onOpen, onExpand);
    },
    update(deco, tr) {
      if (tr.docChanged) {
        return buildDecorations(tr.newDoc, overrideMap, onOpen, onExpand);
      }
      return deco.map(tr.changes);
    },
    provide: field => EditorView.decorations.from(field),
  });
}

export function expandFunction(
  funcName: string,
  sourceCode: string,
  view: EditorView
): void {
  const doc = view.state.doc;
  const pat = new RegExp(`^\\s*(def|class)\\s+${funcName}`);
  for (let i = 1; i <= doc.lines; i++) {
    const line = doc.line(i);
    if (pat.test(line.text)) {
      view.dispatch({ changes: { from: line.from, to: line.to, insert: sourceCode } });
      return;
    }
  }
}
