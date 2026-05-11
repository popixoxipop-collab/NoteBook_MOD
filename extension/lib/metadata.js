"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.unregisterModules = exports.registerModules = exports.isModularized = exports.writeMeta = exports.readMeta = void 0;
/** 셀 metadata 키 */
const META_KEY = 'notebook_mod';
/** 셀에서 모듈화 메타데이터 읽기 */
function readMeta(cell) {
    const meta = cell.model.getMetadata(META_KEY);
    return meta !== null && meta !== void 0 ? meta : null;
}
exports.readMeta = readMeta;
/** 셀에 모듈화 메타데이터 쓰기 */
function writeMeta(cell, data) {
    cell.model.setMetadata(META_KEY, data);
}
exports.writeMeta = writeMeta;
/** 셀의 모듈화 활성화 여부 확인 */
function isModularized(cell) {
    var _a;
    return ((_a = readMeta(cell)) === null || _a === void 0 ? void 0 : _a.enabled) === true;
}
exports.isModularized = isModularized;
/**
 * 모듈화된 함수 목록을 셀 메타데이터에 등록.
 * NoteBook_MOD 서버가 모듈화 완료 후 이 함수를 호출.
 */
function registerModules(cell, modules) {
    writeMeta(cell, { enabled: true, modules });
}
exports.registerModules = registerModules;
/** 셀의 모듈화 해제 (원본 코드 복원 시) */
function unregisterModules(cell) {
    writeMeta(cell, { enabled: false, modules: [] });
}
exports.unregisterModules = unregisterModules;
//# sourceMappingURL=metadata.js.map