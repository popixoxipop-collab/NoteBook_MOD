"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ModuleBadgeWidget = void 0;
const view_1 = require("@codemirror/view");
// 툴팁 싱글톤 — 화면에 하나만 존재
let activeTooltip = null;
function removeTooltip() {
    if (activeTooltip) {
        activeTooltip.remove();
        activeTooltip = null;
    }
}
/**
 * 모듈화된 함수/클래스를 대체하는 인라인 뱃지 위젯.
 * - hover  → 원본 코드 툴팁 표시
 * - click  → 연결된 .py 파일 열기
 * - dblclick → 뱃지 해제 (인라인 전개)
 */
class ModuleBadgeWidget extends view_1.WidgetType {
    constructor(funcName, filePath, sourceCode, onOpen, onExpand) {
        super();
        this.funcName = funcName;
        this.filePath = filePath;
        this.sourceCode = sourceCode;
        this.onOpen = onOpen;
        this.onExpand = onExpand;
    }
    toDOM() {
        const wrap = document.createElement('span');
        wrap.className = 'nbmod-badge';
        wrap.title = `클릭: ${this.filePath} 열기 / 더블클릭: 인라인 전개`;
        // 파일 아이콘
        const icon = document.createElement('span');
        icon.className = 'nbmod-badge__icon';
        icon.textContent = '📄';
        // 함수명
        const label = document.createElement('span');
        label.className = 'nbmod-badge__label';
        label.textContent = this.funcName;
        // 파일 경로 힌트
        const hint = document.createElement('span');
        hint.className = 'nbmod-badge__hint';
        hint.textContent = this.filePath;
        wrap.appendChild(icon);
        wrap.appendChild(label);
        wrap.appendChild(hint);
        // ── 이벤트 핸들러 ──────────────────────────────────
        wrap.addEventListener('mouseenter', (e) => {
            this._showTooltip(wrap, e);
        });
        wrap.addEventListener('mouseleave', () => {
            // 툴팁 위로 마우스가 이동하면 유지, 아니면 제거
            setTimeout(() => {
                if (activeTooltip && !activeTooltip.matches(':hover')) {
                    removeTooltip();
                }
            }, 100);
        });
        // 단일 클릭 → 파일 오픈
        wrap.addEventListener('click', (e) => {
            e.stopPropagation();
            removeTooltip();
            this.onOpen(this.filePath);
        });
        // 더블클릭 → 인라인 전개 (뱃지 해제)
        wrap.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            removeTooltip();
            this.onExpand();
        });
        return wrap;
    }
    _showTooltip(anchor, _e) {
        removeTooltip();
        const tooltip = document.createElement('div');
        tooltip.className = 'nbmod-tooltip';
        // 툴팁 헤더
        const header = document.createElement('div');
        header.className = 'nbmod-tooltip__header';
        header.innerHTML = `<span class="nbmod-tooltip__icon">📄</span>
                        <span class="nbmod-tooltip__path">${this.filePath}</span>`;
        // 소스 코드 블록
        const pre = document.createElement('pre');
        pre.className = 'nbmod-tooltip__code';
        const code = document.createElement('code');
        code.textContent = this.sourceCode;
        pre.appendChild(code);
        // 하단 힌트
        const footer = document.createElement('div');
        footer.className = 'nbmod-tooltip__footer';
        footer.textContent = 'click: 파일 열기  •  dblclick: 인라인 전개';
        tooltip.appendChild(header);
        tooltip.appendChild(pre);
        tooltip.appendChild(footer);
        // 위치 계산 — 뱃지 아래에 표시
        const rect = anchor.getBoundingClientRect();
        tooltip.style.top = `${rect.bottom + window.scrollY + 6}px`;
        tooltip.style.left = `${rect.left + window.scrollX}px`;
        document.body.appendChild(tooltip);
        activeTooltip = tooltip;
        // 툴팁 자체에 마우스가 있으면 유지
        tooltip.addEventListener('mouseleave', removeTooltip);
    }
    // CodeMirror 동등성 비교 — 같은 함수면 재렌더 안 함
    eq(other) {
        return (this.funcName === other.funcName &&
            this.filePath === other.filePath);
    }
    ignoreEvent() {
        return false; // 클릭/hover 이벤트를 CodeMirror가 가로채지 않도록
    }
}
exports.ModuleBadgeWidget = ModuleBadgeWidget;
//# sourceMappingURL=badge.js.map