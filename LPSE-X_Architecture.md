# LPSE-X System Architecture — Complete Technical Diagrams

**Product:** LPSE-X (Explainable AI for Procurement Fraud Detection)
**Competition:** Find IT! 2026 — Universitas Gadjah Mada
**Track:** C — "The Explainable Oracle" (Predictive Analytics)
**Date:** February 27, 2026

---

## 1. System Overview — High-Level Architecture

The LPSE-X platform is a modular, high-performance system designed for local-only deployment on participant hardware. It integrates 1.1 million tenders through a multi-stage pipeline, leveraging a tri-method AI engine and a five-layer explainability sandwich.

```mermaid
flowchart TB
    subgraph DATA_SOURCES ["Data Sources"]
        DS1["opentender.net (ICW)"]
        DS2["pyproc (LPSE real-time)"]
        DS3["LKPP Open Data (SiRUP)"]
        DS4["Corruption Cases"]
    end

    subgraph INGESTION ["Ingestion Pipeline"]
        AF["Async Fetcher"]
        OV["OCDS Validator"]
        DC["Data Cleaner"]
        SL["SQLite Loader"]
    end

    subgraph STORAGE ["Storage Layer"]
        DB[("SQLite Database")]
    end

    subgraph FEATURE_ENG ["Feature Engineering"]
        CRD["Cardinal (73 Red Flags)"]
        CST["12 Custom ML Features"]
        FV["85-dim Feature Vector"]
    end

    subgraph GRAPH_ENGINE ["Graph Engine"]
        NX["NetworkX Bipartite Graph"]
        LA["Leiden (leidenalg)"]
        GM["Graph Metrics"]
    end

    subgraph TRI_METHOD ["Tri-Method AI Engine"]
        IF["Isolation Forest (Unsupervised)"]
        XG["XGBoost (Supervised)"]
        WL["ICW Weak Labels"]
        DP["Disagreement Protocol"]
        ORT["ONNX Runtime"]
    end

    subgraph ORACLE_XAI ["Oracle Sandwich XAI"]
        L1["SHAP (Global)"]
        L2["DiCE (Local)"]
        L3["Anchors (Rules)"]
        L4["Leiden (Graph)"]
        L5["Benford (Statistical)"]
    end

    subgraph REPORT_GEN ["Report Generation"]
        JN["Jinja2 NLG"]
        STD["IIA 2025 Standards"]
        BI["Bahasa Indonesia"]
    end

    subgraph API_LAYER ["API Layer (FastAPI)"]
        UV["Uvicorn ASGI"]
        INJ["PUT /api/config/inject"]
        ENDP["All Endpoints"]
    end

    subgraph FRONTEND ["Frontend Layer (React)"]
        SPA["React SPA"]
        PLT["Plotly Charts"]
        FOL["Folium Maps"]
        OUT["5 Output Components"]
    end

    subgraph CONFIG ["Configuration Manager"]
        CM["ConfigManager Singleton"]
        YAML["runtime_config.yaml"]
    end

    %% Data Flow
    DS1 & DS2 & DS3 & DS4 --> AF
    AF --> OV --> DC --> SL --> DB
    DB --> FEATURE_ENG & GRAPH_ENGINE
    FEATURE_ENG --> TRI_METHOD
    GRAPH_ENGINE --> ORACLE_XAI
    TRI_METHOD --> ORACLE_XAI
    ORACLE_XAI --> REPORT_GEN
    REPORT_GEN --> API_LAYER
    API_LAYER --> FRONTEND

    %% Config Flow
    CM -.-> FEATURE_ENG
    CM -.-> GRAPH_ENGINE
    CM -.-> TRI_METHOD
    CM -.-> ORACLE_XAI
    CM -.-> REPORT_GEN
    CM -.-> API_LAYER

    %% Styling
    classDef sources fill:#e1f5fe,stroke:#01579b
    classDef processing fill:#e8f5e9,stroke:#1b5e20
    classDef storage fill:#fff3e0,stroke:#e65100
    classDef ai fill:#f3e5f5,stroke:#4a148c
    classDef xai fill:#fce4ec,stroke:#880e4f
    classDef api fill:#e0f7fa,stroke:#006064
    classDef frontend fill:#e8eaf6,stroke:#1a237e
    classDef config fill:#fffde7,stroke:#f57f17

    class DS1,DS2,DS3,DS4 sources
    class AF,OV,DC,SL,CRD,CST,FV,NX,LA,GM processing
    class DB storage
    class IF,XG,WL,DP,ORT ai
    class L1,L2,L3,L4,L5 xai
    class API_LAYER,UV,INJ,ENDP api
    class FRONTEND,SPA,PLT,FOL,OUT frontend
    class CONFIG,CM,YAML config
```

---

## 2. Data Ingestion Pipeline — Detailed Flow

The ingestion pipeline handles 1.1 million tenders with OCDS validation and privacy-preserving NPWP hashing. All data is served from local SQLite after the initial ingestion phase.

```mermaid
flowchart LR
    subgraph SOURCES ["Data Sources"]
        OT["opentender.net (ICW)
        - 1,106,096 tenders
        - OCDS Format
        - /api/tender/export/"]
        PY["pyproc
        - Real-time LPSE
        - Rate 1 req/2s
        - Exp. Backoff"]
        SIR["LKPP SiRUP
        - CKAN API
        - 26 Datasets
        - 631+ K/L/PD"]
        COR["Corruption Cases
        - 200+ Curated
        - ground truth labels"]
    end

    subgraph PIPELINE ["Ingestion Pipeline"]
        direction TB
        S1["Async Fetcher
        (httpx + aiofiles)"]
        S2["OCDS Validator
        (Pydantic BaseModel)"]
        S3["Data Cleaner
        (Median Imputation)"]
        S4["Privacy Compliance
        (NPWP SHA-256 Hash)"]
        S5["SQLite Bulk Insert
        (aiosqlite)"]
    end

    subgraph TABLES ["SQLite Tables"]
        T1["tenders"]
        T2["vendors"]
        T3["awards"]
        T4["corruption_cases"]
        T5["vendor_network_edges"]
    end

    OT & PY & SIR & COR --> S1
    S1 --> S2 --> S3 --> S4 --> S5
    S5 --> T1 & T2 & T3 & T4 & T5
```

---

## 3. Feature Engineering — 85 Forensic Signals

LPSE-X calculates 85 dimensions of feature data per tender, combining international OCP red flags with 12 custom behavioral forensic signals.

```mermaid
flowchart TB
    subgraph CARDINAL_ENG ["Cardinal Library (OCP)"]
        CF["73 Red Flags"]
        CF1["Planning Phase Flags"]
        CF2["Tender Phase Flags"]
        CF3["Award Phase Flags"]
        CF4["Implementation Phase Flags"]
        CF --> CF1 & CF2 & CF3 & CF4
    end

    subgraph CUSTOM_ENG ["12 Custom ML Features"]
        direction TB
        M1["Bid Clustering Score"]
        M2["Vendor Win Concentration"]
        M3["HPS Deviation Ratio"]
        M4["Participant Count Anomaly"]
        M5["Geographic Concentration"]
        M6["Repeat Pairing Index"]
        M7["Temporal Submission Pattern"]
        M8["Historical Win Rate"]
        M9["Phantom Bidder Score"]
        M10["Benford's Law Anomaly"]
        M11["Interlocking Directorates"]
        M12["Bid Rotation Pattern"]
    end

    subgraph OUTPUT ["Feature Integration"]
        FV["85-Dimensional Feature Vector"]
    end

    CARDINAL_ENG --> OUTPUT
    CUSTOM_ENG --> OUTPUT
    OUTPUT --> AE["Tri-Method AI Engine"]
```

---

## 4. Graph-Based Cartel Detection

Using bipartite graph analysis and the Leiden community detection algorithm to identify suspicious vendor clusters.

```mermaid
flowchart LR
    DB[("SQLite Database")] --> NX["NetworkX Bipartite Graph
    (Vendor ↔ Tender)"]
    NX --> LA["Leiden Community Detection
    (leidenalg library)"]
    LA --> CI["Cartel Clusters Identified"]
    CI --> GM["Graph Metrics
    (Degree, Betweenness)"]
    GM --> OS["Oracle Sandwich Layer 4"]

    style CI fill:#fce4ec,stroke:#880e4f
    subgraph NOTE ["Validation"]
        V["Validated by Imhof et al. (2025):
        GAT 91% accuracy across 13 markets"]
    end
```

```mermaid
classDiagram
    class Vendor {
        +String npwp_hash
        +String name
        +String region
        +int win_count
    }
    class Tender {
        +String id
        +String ocid
        +String buyer
        +float hps
        +float contract_value
    }
    class Bid {
        +float amount
        +DateTime submission_time
    }
    class Community {
        +int id
        +int member_count
        +float risk_score
    }

    Vendor "1..*" -- "1..*" Tender : participates via Bid
    Community "1" -- "1..*" Vendor : contains
```

---

## 5. Tri-Method AI Engine

The engine combines three detection methods through a disagreement protocol to ensure high-precision risk scoring.

```mermaid
flowchart TB
    subgraph INPUT ["Input"]
        FV["85-dim Feature Vector"]
    end

    subgraph ENGINES ["Detection Engines"]
        IF["Isolation Forest
        (Unsupervised)"]
        XG["XGBoost Classifier
        (Supervised, 4-level)"]
        WL["ICW Weak Labels
        (Weakly Supervised)"]
    end

    subgraph ENSEMBLE ["Decision Layer"]
        DP["Disagreement Protocol
        (Weighted Ensemble)"]
    end

    subgraph OUTCOMES ["Final Scoring"]
        AG["Weighted Average Risk Score"]
        DG["Manual Review Priority Flag"]
    end

    INPUT --> IF & XG & WL
    IF & XG & WL --> DP
    DP --> AG & DG
    AG & DG --> ORT["ONNX Runtime
    (<200ms CPU Inference)"]

    subgraph EVAL ["Performance Target"]
        T["F1: 0.85-0.92 (Westerski et al. 2021)"]
    end
```

```mermaid
stateDiagram-v2
    [*] --> Aman: score < risk_threshold_low
    Aman --> Perlu_Pantauan: score >= risk_threshold_low
    Perlu_Pantauan --> Risiko_Tinggi: score >= risk_threshold_mid
    Risiko_Tinggi --> Risiko_Kritis: score >= risk_threshold_high
    Risiko_Kritis --> [*]: alert generated

    state Aman {
        label: "Aman"
    }
    state Perlu_Pantauan {
        label: "Perlu Pantauan"
    }
    state Risiko_Tinggi {
        label: "Risiko Tinggi"
    }
    state Risiko_Kritis {
        label: "Risiko Kritis"
    }

    note right of Aman: Labels: Aman, Perlu Pantauan, Risiko Tinggi, Risiko Kritis
    note right of Risiko_Kritis: Configurable via PUT /api/config/inject
```

---

## 6. Oracle Sandwich XAI — 5 Layers

The Oracle Sandwich architecture provides multi-layer explanations, meeting EU AI Act Pasal 86 transparency standards.

```mermaid
flowchart TB
    IN["ONNX Risk Score + Features + Graph Metrics"] --> L1
    
    subgraph SANDWICH ["Oracle Sandwich Layers"]
        direction TB
        L1["Layer 1 — GLOBAL: SHAP
        (shap summary plots)"]
        L2["Layer 2 — LOCAL: DiCE
        (Counterfactuals, CACHED/ASYNC)"]
        L3["Layer 3 — RULES: Anchors
        (alibi if-then rules)"]
        L4["Layer 4 — GRAPH: Leiden
        (leidenalg network viz)"]
        L5["Layer 5 — STATISTICAL: Benford
        (benford_py χ² distribution)"]
    end

    L1 --> L2 --> L3 --> L4 --> L5
    L5 --> OUT["Structured XAI Output"]

    style SANDWICH fill:#fce4ec,stroke:#880e4f
```

| Layer | Method | Library | Question Answered | SLA |
|-------|--------|---------|-------------------|-----|
| 1. Global | SHAP | `shap` | Which features matter most overall? | <2s |
| 2. Local | DiCE | `dice-ml` | What must change to NOT be flagged? | Async |
| 3. Rules | Anchors | `alibi` | What simple rule does the model follow? | <5s |
| 4. Graph | Leiden | `leidenalg` | Which companies form a cartel? | <3s |
| 5. Statistical | Benford | `benford_py` | Are bid prices statistically natural? | <1s (≥100 records pre-check required) |

---

## 7. Auto Report Generation

The report engine uses Jinja2 to generate IIA 2025 compliant reports in Bahasa Indonesia.

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant ReportEngine
    participant OracleSandwich
    participant SQLite
    participant Jinja2

    User->>FastAPI: GET /api/report/{tender_id}
    FastAPI->>ReportEngine: generate_report(tender_id, output_format)
    ReportEngine->>SQLite: query tender metadata + award data
    SQLite-->>ReportEngine: tender record
    ReportEngine->>OracleSandwich: get_all_explanations(tender_id)
    OracleSandwich-->>ReportEngine: {shap, dice, anchors, leiden, benford}
    ReportEngine->>Jinja2: render(template="iia_2025_bahasa.html", data=explanations)
    Note over Jinja2: Template-based NLG / Bahasa Indonesia / IIA 2025 standard
    Jinja2-->>ReportEngine: rendered HTML/PDF
    ReportEngine-->>FastAPI: report document
    FastAPI-->>User: 200 OK + report
```

---

## 8. FastAPI Backend Architecture with Dynamic Injection

The FastAPI backend provides a RESTful interface for analysis and configuration injection.

```mermaid
flowchart LR
    subgraph CLIENT ["Client"]
        RF["React Frontend"]
        JD["Judge"]
    end

    subgraph ROUTER ["FastAPI Router"]
        direction TB
        C_GRP["Config: PUT /api/config/inject"]
        D_GRP["Data: GET /api/tenders"]
        A_GRP["Analysis: GET /api/risk/{id}, /api/explain/{id}"]
        N_GRP["Network: GET /api/network"]
        R_GRP["Report: GET /api/report/{id}"]
        V_GRP["Viz: GET /api/heatmap"]
        H_GRP["Health: GET /api/health"]
    end

    subgraph MODULES ["Backend Modules"]
        CM["ConfigManager"]
        TR["TenderRepository"]
        RE["RiskEngine"]
        OS["OracleSandwich"]
        GE["GraphEngine"]
        RG["ReportEngine"]
        HB["HeatmapBuilder"]
    end

    RF & JD --> ROUTER
    C_GRP --> CM
    D_GRP --> TR
    A_GRP --> RE & OS
    N_GRP --> GE
    R_GRP --> RG
    V_GRP --> HB
```

```mermaid
sequenceDiagram
    participant Judge
    participant FastAPI
    participant Pydantic
    participant ConfigManager
    participant AuditLog
    participant AllModules

    Judge->>FastAPI: PUT /api/config/inject {procurement_scope, institution_filter, risk_threshold, year_range, anomaly_method, output_format, custom_params}
    FastAPI->>Pydantic: validate(payload)
    alt Invalid Parameters
        Pydantic-->>FastAPI: ValidationError (422)
        FastAPI-->>Judge: 422 Unprocessable Entity
    else Valid Parameters
        Pydantic-->>FastAPI: validated ConfigModel
        FastAPI->>ConfigManager: apply_config(validated_config)
        ConfigManager->>AuditLog: log_injection(timestamp, params)
        ConfigManager->>AllModules: notify_config_updated()
        Note over ConfigManager,AllModules: Applied instantly — no restart, no retraining required
        ConfigManager-->>FastAPI: config_applied
        FastAPI-->>Judge: 200 OK {applied_config, audit_id}
    end
```

---

## 9. React Frontend with 5 Outputs

The frontend is a React Single Page Application (SPA) visualizing forensic findings through 5 specialized output components.

```mermaid
flowchart TB
    SPA["React SPA (Vite build)"] --> API["FastAPI Backend REST API"]

    subgraph OUTPUT_1 ["Risk Score Dashboard"]
        D1["Plotly bar/pie charts"]
        D2["4-level color coding"]
        D3["Sortable Risk Tender list"]
    end

    subgraph OUTPUT_2 ["Oracle Sandwich Explanation Panel"]
        X1["SHAP waterfall chart"]
        X2["DiCE counterfactual table"]
        X3["Anchors if-then rules"]
        X4["Leiden graph snippet"]
        X5["Benford distribution chart"]
    end

    subgraph OUTPUT_3 ["Geographic Risk Heatmap"]
        H1["Folium/Leaflet map"]
        H2["Institution markers"]
        H3["Offline tile fallback"]
    end

    subgraph OUTPUT_4 ["Cartel Network Graph"]
        G1["Interactive force graph"]
        G2["Leiden community colors"]
        G3["Vendor sizing by win_count"]
    end

    subgraph OUTPUT_5 ["Pre-Investigation Report Viewer"]
        R1["Bahasa Indonesia report"]
        R2["IIA 2025 sections"]
        R3["Download PDF button"]
    end

    SPA --> OUTPUT_1 & OUTPUT_2 & OUTPUT_3 & OUTPUT_4 & OUTPUT_5
```

---

## 10. Runtime Config Flow

Configuration is managed as a thread-safe singleton, allowing for instant updates to all processing modules without service interruption.

```mermaid
sequenceDiagram
    participant YAML_File
    participant Pydantic
    participant ConfigManager
    participant FeatureEng
    participant GraphEngine
    participant TriMethodAI
    participant OracleSandwich
    participant ReportGen
    participant FastAPI

    Note over FastAPI,YAML_File: Part A: Startup Initialization
    FastAPI->>YAML_File: load runtime_config.yaml
    YAML_File-->>FastAPI: raw config dict
    FastAPI->>Pydantic: ConfigModel.parse(raw_config)
    Pydantic-->>FastAPI: validated ConfigModel
    FastAPI->>ConfigManager: initialize_singleton(config)
    ConfigManager->>FeatureEng: set_config(procurement_scope, institution_filter, year_range)
    ConfigManager->>GraphEngine: set_config(year_range, institution_filter)
    ConfigManager->>TriMethodAI: set_config(anomaly_method, risk_threshold)
    ConfigManager->>OracleSandwich: set_config(risk_threshold)
    ConfigManager->>ReportGen: set_config(output_format)

    Note over FastAPI,ConfigManager: Part B: Live Injection
    FastAPI->>FastAPI: Judge calls PUT /api/config/inject
    FastAPI->>Pydantic: re-validate(new_params)
    Pydantic-->>FastAPI: validated
    FastAPI->>ConfigManager: update_config(validated_params)
    Note over ConfigManager: Update in-place (thread-safe)
    ConfigManager-->>FastAPI: updated
    FastAPI-->>FastAPI: Applied instantly — no restart, no retraining
```

| Parameter | Controls | Module(s) Affected |
|-----------|----------|-------------------|
| `procurement_scope` | tender category filter | FeatureEng, GraphEngine, TenderRepository |
| `institution_filter` | K/L/Pemda filter | all data queries |
| `risk_threshold` | classification boundary | TriMethodAI, OracleSandwich |
| `year_range` | temporal filter | all data queries, temporal split |
| `anomaly_method` | Isolation Forest / XGBoost / ensemble | TriMethodAI |
| `output_format` | dashboard / API JSON / audit report | ReportGen, FastAPI responses |
| `custom_params` | wildcard dict for judge-injected unknown params | CustomParamsHandler |
