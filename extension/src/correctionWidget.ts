/**
 * Dropdown shown when a module badge is clicked.
 * Provides confirm/correct actions for a path suggestion.
 */

export interface CorrectionOptions {
  funcName: string;
  currentPath: string;
  source: 'llm' | 'human';
  confidence: number;
  /** Called when user clicks confirm — argument is the current/confirmed path. */
  onConfirm: (path: string) => void;
  /** Called when user clicks correct with a (different) new path. */
  onCorrect: (newPath: string) => void;
}

let activeDropdown: CorrectionDropdown | null = null;

export class CorrectionDropdown {
  private readonly el: HTMLElement;
  private readonly input: HTMLInputElement;
  private readonly options: CorrectionOptions;
  private readonly outsideHandler: (ev: MouseEvent) => void;

  constructor(options: CorrectionOptions) {
    this.options = options;

    // Close any previously open dropdown first.
    activeDropdown?.close();
    activeDropdown = this;

    this.el = document.createElement('div');
    this.el.className = 'nbmod-correction-dropdown';

    // ── header: function name ───────────────────────────
    const title = document.createElement('div');
    title.className = 'nbmod-correction-title';
    title.textContent = options.funcName;
    title.style.fontWeight = '600';
    title.style.marginBottom = '4px';
    this.el.appendChild(title);

    // ── current path ────────────────────────────────────
    const pathRow = document.createElement('div');
    pathRow.className = 'nbmod-correction-path';
    pathRow.textContent = `📁 ${options.currentPath}`;
    pathRow.style.fontSize = '12px';
    pathRow.style.marginBottom = '4px';
    this.el.appendChild(pathRow);

    // ── meta: confidence + source ───────────────────────
    const meta = document.createElement('div');
    meta.className = 'nbmod-correction-meta';
    meta.style.fontSize = '11px';
    meta.style.marginBottom = '6px';
    const confPct = Math.round((options.confidence ?? 0) * 100);
    meta.textContent = `[신뢰도: ${confPct}%] [${options.source.toUpperCase()}]`;
    this.el.appendChild(meta);

    // ── separator ───────────────────────────────────────
    const hr = document.createElement('hr');
    hr.style.margin = '6px 0';
    hr.style.border = 'none';
    hr.style.borderTop = '1px solid var(--jp-border-color2, #ddd)';
    this.el.appendChild(hr);

    // ── label ───────────────────────────────────────────
    const label = document.createElement('div');
    label.textContent = '경로 수정:';
    label.style.fontSize = '12px';
    label.style.marginBottom = '2px';
    this.el.appendChild(label);

    // ── input ───────────────────────────────────────────
    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.value = options.currentPath;
    this.input.spellcheck = false;
    this.el.appendChild(this.input);

    // ── buttons ─────────────────────────────────────────
    const btnRow = document.createElement('div');
    btnRow.style.marginTop = '4px';

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'nbmod-btn-confirm';
    confirmBtn.textContent = '✓ 확정';
    confirmBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.options.onConfirm(this.options.currentPath);
      this.close();
    });

    const correctBtn = document.createElement('button');
    correctBtn.className = 'nbmod-btn-correct';
    correctBtn.textContent = '✎ 수정';
    correctBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const newPath = this.input.value.trim();
      if (!newPath || newPath === this.options.currentPath) {
        // no-op — same path => treat as confirm.
        this.options.onConfirm(this.options.currentPath);
      } else {
        this.options.onCorrect(newPath);
      }
      this.close();
    });

    btnRow.appendChild(confirmBtn);
    btnRow.appendChild(correctBtn);
    this.el.appendChild(btnRow);

    // ── inner clicks shouldn't close ────────────────────
    this.el.addEventListener('click', (e) => e.stopPropagation());

    // ── outside-click closes ────────────────────────────
    this.outsideHandler = (ev: MouseEvent) => {
      if (!this.el.contains(ev.target as Node)) {
        this.close();
      }
    };
    // Delay binding so the click that opened us doesn't immediately close us.
    setTimeout(() => {
      document.addEventListener('mousedown', this.outsideHandler);
    }, 0);
  }

  getElement(): HTMLElement {
    return this.el;
  }

  close(): void {
    document.removeEventListener('mousedown', this.outsideHandler);
    this.el.remove();
    if (activeDropdown === this) {
      activeDropdown = null;
    }
  }
}

/** Position the dropdown just below the given anchor element. */
export function positionDropdownBelow(
  dropdown: CorrectionDropdown,
  anchor: HTMLElement
): void {
  const el = dropdown.getElement();
  const rect = anchor.getBoundingClientRect();
  el.style.position = 'fixed';
  el.style.top = `${rect.bottom + 4}px`;
  el.style.left = `${rect.left}px`;
}
