# NoteBook_MOD — Architecture

> Mermaid diagrams render natively on GitHub. Three views: data model → classification pipeline → library/function/variable dependency.

---

## 1. Data Model (ERD)

StateDB에 저장되는 엔티티와 노트북 개념 모델 간 관계.

```mermaid
erDiagram
    NOTEBOOK {
        string path
        string name
    }
    CELL {
        int    index
        string cell_type
        string source
    }
    FUNCTION {
        string name
        bool   isClass
        string sourceCode
    }
    MAPPING {
        string   funcName    PK
        string   filePath
        string   source      "llm | human | fallback | state"
        float    confidence  "0.0 – 1.0"
        datetime confirmed_at
    }
    CORRECTION {
        int      id          PK
        string   funcName    FK
        string   fromPath
        string   toPath
        datetime corrected_at
    }
    CATEGORY {
        string name         PK
        string description
    }

    NOTEBOOK    ||--o{  CELL        : "contains"
    CELL        ||--o{  FUNCTION    : "defines"
    FUNCTION    }o--o|  MAPPING     : "resolved to"
    MAPPING     }o--o{  CORRECTION  : "overridden by"
    CATEGORY    ||--o{  MAPPING     : "classifies"
```

---

## 2. Classification Pipeline (3-tier)

노트북 오픈 → 뱃지 렌더링 → 사용자 수정 → StateDB 플라이휠.

```mermaid
flowchart TD
    NB([📓 Notebook open]) --> COLLECT

    COLLECT["collectFunctions(panel)\nregex: /def|class \\w+/gm\n→ FuncInfo[]"]
    COLLECT --> LOAD

    LOAD["loadState()\nGET /notebook-mod/state\n→ StateStore {mappings, categories}"]
    LOAD --> MERGE

    MERGE{funcName\nin StateDB?}
    MERGE -- hit\nconfidence=1.0 --> BADGE
    MERGE -- miss --> LLM

    LLM["classify_functions()\nPOST openai gpt-4o-mini\nfew-shot: confirmed_mappings + corrections\n→ {funcName: {path, confidence, reason}}"]
    LLM -- success --> SAVE_LLM

    SAVE_LLM["StateDB.set_mapping()\nsource='llm'"] --> BADGE

    LLM -- fail / no API key --> RULE

    RULE["_rule_based_classify()\n① SentenceTransformer('all-MiniLM-L6-v2')\n   or TfidfVectorizer (char_wb 3-5gram)\n② cosine similarity greedy clustering\n③ _infer_dir() + _cluster_filename()\n→ {funcName: filePath}"]
    RULE --> BADGE

    BADGE["buildDecorations(doc)\nCodeMirror Decoration.replace block=true\n→ 📄 funcName · agents/analyzer_node.py"]

    BADGE --> HOVER["hover → tooltip\nsourceCode preview"]
    BADGE --> CLICK["click → CorrectionDropdown\nconfidence%, source label"]
    BADGE --> DBLCLICK["dblclick → expandFunction()\ninline restore"]

    CLICK --> CONFIRM["✓ 확정\nPOST /state\n{action:'confirm', funcName, path}"]
    CLICK --> CORRECT["✎ 수정\nPOST /state\n{action:'correct', funcName,\n path:newPath, fromPath}"]

    CONFIRM --> STATEDB[("StateDB\n.nbmod_state.db")]
    CORRECT --> STATEDB

    STATEDB -. "next open:\nfew-shot 주입" .-> LLM
```

---

## 3. Library → Function → Variable Dependency

외부 라이브러리가 어느 함수에서 쓰이고, 무슨 변수/타입을 만들어내는지.

```mermaid
flowchart LR
    subgraph PY_LIBS["Python Libraries"]
        sqlite3(["sqlite3"])
        numpy(["numpy"])
        sentence_t(["sentence-transformers\nSentenceTransformer"])
        sklearn_t(["sklearn\nTfidfVectorizer"])
        openai_lib(["openai\nOpenAI"])
        tornado_lib(["tornado\nAPIHandler"])
    end

    subgraph TS_LIBS["TypeScript Libraries"]
        jl_nb(["@jupyterlab/notebook\nNotebookPanel"])
        jl_cells(["@jupyterlab/cells\nCodeCell"])
        jl_doc(["@jupyterlab/docmanager\nIDocumentManager"])
        cm_view(["@codemirror/view\nEditorView, Decoration"])
        cm_state(["@codemirror/state\nStateField, StateEffect"])
    end

    subgraph STATE_DB["state_db.py — StateDB"]
        sqlite3 --> sd_conn["_connect()\n→ sqlite3.Connection"]
        sd_conn --> sd_get["get_mapping(name)\n→ str | None"]
        sd_conn --> sd_set["set_mapping(name, path, src, conf)\n→ void"]
        sd_conn --> sd_all["get_all_mappings()\n→ dict[str, MappingInfo]"]
        sd_conn --> sd_cor["add_correction(name, from, to)\n→ void"]
        sd_conn --> sd_cat["get_categories()\n→ list[CategoryRow]"]
    end

    subgraph LLM_CLS["llm_classifier.py"]
        openai_lib --> llm_call["classify_functions(\n  functions, categories,\n  confirmed_mappings,\n  corrections\n)\n→ dict[str,{path,confidence,reason}]"]
        llm_call --> llm_prompt["_build_user_prompt()\n→ str (few-shot context)"]
    end

    subgraph RULE_CLS["handlers.py — rule-based"]
        sentence_t --> get_emb["_get_embeddings(texts)\n→ np.ndarray"]
        sklearn_t  --> get_emb
        numpy      --> cosine["_cosine(a, b)\n→ float"]
        get_emb    --> cluster["_cluster(embeddings, threshold)\n→ list[list[int]]"]
        cosine     --> cluster
        cluster    --> rbc["_rule_based_classify(\n  names, sources, threshold\n)\n→ dict[str, str]"]
    end

    subgraph HANDLERS["handlers.py — Handlers"]
        tornado_lib --> ah["AnalyzeHandler.post()\nbody: {functions[], threshold}\n→ {funcName:{path,source,confidence}}"]
        tornado_lib --> sh["StateHandler.post()\nbody: {funcName,path,action}\n→ {status,funcName,path}"]
        tornado_lib --> ch["CategoryHandler.post()\nbody: {action,name,description}\n→ {status,categories[]}"]

        sd_get --> ah
        sd_all --> ah
        sd_cat --> ah
        sd_cor --> ah
        llm_call --> ah
        rbc --> ah

        sd_set --> sh
        sd_cor --> sh
        sd_set --> ch
    end

    subgraph TS_CORE["TypeScript Core"]
        jl_nb    --> collect["collectFunctions(panel)\n→ FuncInfo[]\n  {funcName, isClass, sourceCode}"]
        jl_cells --> collect

        collect  --> fetchMap["fetchModuleMapping(panel)\n→ Map‹string, ConfirmedMapping›\n  {path, source, confidence}"]
        ah       -. "POST /analyze" .-> fetchMap
        sh       -. "GET /state" .-> fetchMap

        fetchMap --> build["buildDecorations(doc, overrideMap)\n→ DecorationSet"]
        cm_view  --> build
        cm_state --> build

        build    --> badge["ModuleBadgeWidget\n.toDOM() → HTMLElement\n  icon + label + hint"]

        badge    --> correction["CorrectionDropdown\n{funcName, currentPath,\n source, confidence}\nonConfirm / onCorrect"]

        badge    --> expand["expandFunction(\n  funcName, sourceCode, view\n)\n→ void (doc edit)"]

        jl_doc   --> open_file["docManager.openOrReveal(path)\n→ split-right panel"]
        correction --> open_file

        correction --> ss_confirm["confirmMapping(baseUrl,funcName,path)\nPOST /state action:confirm"]
        correction --> ss_correct["correctMapping(baseUrl,funcName,from,to)\nPOST /state action:correct"]

        ss_confirm -. "HTTP" .-> sh
        ss_correct -. "HTTP" .-> sh
    end
```

---

## Route Map

| Method | Endpoint | Handler | Key variables |
|--------|----------|---------|---------------|
| `GET`  | `/notebook-mod/analyze` | `AnalyzeHandler.get` | `backend: "openai" \| "sentence-transformers" \| "tfidf-fallback"` |
| `POST` | `/notebook-mod/analyze` | `AnalyzeHandler.post` | `functions[], threshold` → `{funcName:{path,source,confidence}}` |
| `GET`  | `/notebook-mod/state` | `StateHandler.get` | → `{mappings{}, categories[], corrections[]}` |
| `POST` | `/notebook-mod/state` | `StateHandler.post` | `{funcName, path, action:"confirm"\|"correct", fromPath?}` |
| `GET`  | `/notebook-mod/categories` | `CategoryHandler.get` | → `{categories[]}` |
| `POST` | `/notebook-mod/categories` | `CategoryHandler.post` | `{action:"add"\|"delete", name, description?}` |
