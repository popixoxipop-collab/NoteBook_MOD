import { WidgetType, EditorView } from '@codemirror/view';

let activeTooltip: HTMLElement | null = null;

function removeTooltip() {
  activeTooltip?.remove();
  activeTooltip = null;
}

export class ModuleBadgeWidget extends WidgetType {
  constructor(
    private readonly funcName: string,
    private readonly filePath: string,
    private readonly sourceCode: string,
    private readonly onOpen: (path: string) => void,
    private readonly onExpand: (view: EditorView) => void
  ) {
    super();
  }

  toDOM(view: EditorView): HTMLElement {
    const wrap = document.createElement('span');
    wrap.className = 'nbmod-badge';
    wrap.setAttribute('data-func', this.funcName);

    const icon = document.createElement('span');
    icon.textContent = '📄';
    icon.style.marginRight = '3px';

    const label = document.createElement('span');
    label.className = 'nbmod-badge__label';
    label.textContent = this.funcName;

    const hint = document.createElement('span');
    hint.className = 'nbmod-badge__hint';
    hint.textContent = ` · ${this.filePath}`;

    wrap.appendChild(icon);
    wrap.appendChild(label);
    wrap.appendChild(hint);

    wrap.addEventListener('mouseenter', () => this._showTooltip(wrap));
    wrap.addEventListener('mouseleave', () => {
      setTimeout(() => { if (!activeTooltip?.matches(':hover')) removeTooltip(); }, 120);
    });
    wrap.addEventListener('click', (e) => {
      e.stopPropagation();
      removeTooltip();
      this.onOpen(this.filePath);
    });
    wrap.addEventListener('dblclick', (e) => {
      e.stopPropagation();
      removeTooltip();
      this.onExpand(view);
    });

    return wrap;
  }

  private _showTooltip(anchor: HTMLElement): void {
    removeTooltip();
    const t = document.createElement('div');
    t.className = 'nbmod-tooltip';

    const header = document.createElement('div');
    header.className = 'nbmod-tooltip__header';
    header.innerHTML = `<span>📄</span> <span class="nbmod-tooltip__path">${this.filePath}</span>`;

    const pre = document.createElement('pre');
    pre.className = 'nbmod-tooltip__code';
    pre.textContent = this.sourceCode;

    const footer = document.createElement('div');
    footer.className = 'nbmod-tooltip__footer';
    footer.textContent = 'click: 파일 열기  •  dblclick: 인라인 전개';

    t.appendChild(header);
    t.appendChild(pre);
    t.appendChild(footer);

    const rect = anchor.getBoundingClientRect();
    t.style.position = 'fixed';
    t.style.top  = `${rect.bottom + 6}px`;
    t.style.left = `${rect.left}px`;
    t.style.zIndex = '9999';

    document.body.appendChild(t);
    activeTooltip = t;
    t.addEventListener('mouseleave', removeTooltip);
  }

  eq(other: ModuleBadgeWidget): boolean {
    return this.funcName === other.funcName && this.filePath === other.filePath;
  }

  ignoreEvent(): boolean { return false; }
}
