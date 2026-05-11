/**
 * 함수/클래스 이름과 컨텍스트를 분석해 모듈 파일 경로를 추론하는 규칙 기반 엔진.
 * 외부 API나 메타데이터 없이 클라이언트 사이드에서만 동작.
 */

export interface InferredModule {
  funcName: string;
  filePath: string;
  isClass: boolean;
}

/**
 * 함수/클래스 이름으로 모듈 경로 추론.
 * 우선순위: 명시적 규칙 → 접두사 패턴 → 기본값
 */
export function inferFilePath(funcName: string, isClass: boolean): string {
  const lower = funcName.toLowerCase();

  if (isClass) {
    if (/state$/i.test(funcName))   return 'state.py';
    if (/config$/i.test(funcName))  return 'config.py';
    if (/schema$/i.test(funcName))  return 'schema.py';
    return `models/${funcName}.py`;
  }

  // 에이전트 노드
  if (/_node$/.test(lower))  return `agents/${funcName}.py`;
  if (/_agent$/.test(lower)) return `agents/${funcName}.py`;

  // 그래프 / 라우팅
  if (/^build_/.test(lower))   return `graph/${funcName}.py`;
  if (/^route_/.test(lower))   return `graph/${funcName}.py`;
  if (/^compile_/.test(lower)) return `graph/${funcName}.py`;
  if (/^create_graph/.test(lower)) return `graph/${funcName}.py`;

  // 데이터베이스
  if (/^init_db/.test(lower))  return `db/${funcName}.py`;
  if (/^save_/.test(lower))    return `db/${funcName}.py`;
  if (/^(get|fetch)_.*db/.test(lower)) return `db/${funcName}.py`;

  // 유틸리티 / 로더
  if (/^(_?load|get|read|fetch)_/.test(lower)) return `utils/${funcName}.py`;
  if (/^(setup|configure)_/.test(lower))       return `utils/${funcName}.py`;

  return `${funcName}.py`;
}

const FUNC_PATTERN      = /^(\s*)(def|class)\s+(\w+)/;
const WRITEFILE_PATTERN = /^%%writefile\s+(\S+)/;

/**
 * 셀 소스 전체를 파싱해서 포함된 함수/클래스 목록과 추론된 경로를 반환.
 * %%writefile 매직은 해당 파일의 경로를 컨텍스트로 활용.
 */
export function analyzeCell(source: string): InferredModule[] {
  const lines = source.split('\n');
  const modules: InferredModule[] = [];

  const writefileMatch = WRITEFILE_PATTERN.exec(lines[0] ?? '');
  // %%writefile 셀이라도 함수별 경로는 이름 규칙으로 독립 추론

  for (const line of lines) {
    const m = FUNC_PATTERN.exec(line);
    if (!m) continue;
    const isClass = m[2] === 'class';
    const funcName = m[3];
    if (funcName === '_') continue;          // 익명 패턴 스킵
    if (funcName.startsWith('__')) continue; // dunder 스킵

    const filePath = inferFilePath(funcName, isClass);
    modules.push({ funcName, filePath, isClass });
  }

  return modules;
}
