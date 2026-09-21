// IEEE-format research paper generator — Guardrailed Agentic MLOps (RTS-GMLC).
// All content is derived from this repository's own artifacts (manifests,
// research tables, phase reports). References are real, verifiable sources.
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, PageNumber, AlignmentType, WidthType, BorderStyle,
  ShadingType, SectionType, VerticalAlign,
} = require("docx");
const fs = require("fs");

const TNR = { ascii: "Times New Roman", eastAsia: "Times New Roman" };
const BLACK = "000000";

// ---------- helpers ----------
const run = (text, opts) => new TextRun(Object.assign({ text, size: 20, font: TNR, color: BLACK }, opts || {}));

function body(text, opts) {
  opts = opts || {};
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 240, after: 0 },
    indent: opts.noIndent ? undefined : { firstLine: 288 },
    children: Array.isArray(text) ? text : [run(text)],
  });
}

function bodyLeft(text) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { line: 240, after: 0 },
    indent: { firstLine: 288 },
    children: Array.isArray(text) ? text : [run(text)],
  });
}

function h1(num, text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 240, after: 120, line: 240 },
    children: [run(num + ".  " + text.toUpperCase(), { smallCaps: true })],
  });
}

function h2(letter, text) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: 180, after: 60, line: 240 },
    children: [run(letter + ". " + text, { italics: true })],
  });
}

function refEntry(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 220, after: 20 },
    indent: { left: 280, hanging: 280 },
    children: [run(text, { size: 16 })],
  });
}

function tableCaption(label, text) {
  return new Paragraph({
    keepNext: true, alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 60, line: 220 },
    children: [run(label + ".  " + text, { size: 16, smallCaps: true })],
  });
}

const NB = { style: BorderStyle.NONE };
function threeLineTable(widthsPct, headerCells, dataRows) {
  const cellPara = (text, boldFlag) => new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { line: 200 },
    children: [run(text, { size: 16, bold: !!boldFlag })],
  });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 6, color: BLACK },
      bottom: { style: BorderStyle.SINGLE, size: 6, color: BLACK },
      left: NB, right: NB, insideHorizontal: NB, insideVertical: NB,
    },
    rows: [
      new TableRow({
        tableHeader: true, cantSplit: true,
        children: headerCells.map((t, i) => new TableCell({
          borders: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLACK }, top: NB, left: NB, right: NB },
          margins: { top: 30, bottom: 30, left: 60, right: 60 },
          width: { size: widthsPct[i], type: WidthType.PERCENTAGE },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, spacing: { line: 200 },
            children: [run(t, { size: 16, bold: true })] })],
        })),
      }),
      ...dataRows.map((row, ri) => new TableRow({
        cantSplit: true,
        children: row.map((t, i) => new TableCell({
          borders: { top: NB, bottom: NB, left: NB, right: NB },
          margins: { top: 20, bottom: 20, left: 60, right: 60 },
          width: { size: widthsPct[i], type: WidthType.PERCENTAGE },
          children: [new Paragraph({ keepNext: ri < dataRows.length - 1, alignment: AlignmentType.CENTER, spacing: { line: 200 },
            children: [run(t, { size: 16 })] })],
        })),
      })),
    ],
  });
}

// ---------- title block ----------
const titleBlock = [
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 120, after: 240, line: 300 },
    children: [run("Guardrailed Agentic MLOps for Renewable-Integrated Smart Grid Forecasting: A Deterministic Governance Evaluation on the RTS-GMLC Dataset", { size: 44 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 60, line: 240 },
    children: [run("Pratham Kapoor", { size: 22 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 60, line: 220 },
    children: [run("Department of Information Technology, Mukesh Patel School of Technology Management and Engineering,", { size: 18, italics: true })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 240, line: 220 },
    children: [run("SVKM's NMIMS University, Mumbai, India", { size: 18, italics: true })],
  }),
];

// ---------- abstract ----------
const abstractBlock = [
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED, spacing: { line: 220, after: 120 },
    children: [
      run("Abstract\u2014", { size: 18, bold: true }),
      run("Agentic artificial intelligence (AI) is increasingly proposed as a means of reducing the manual engineering burden of machine learning operations (MLOps), yet unbounded autonomous authority over the model lifecycle is unsafe in regulated energy systems. This paper presents an offline research platform for electricity demand and renewable-generation forecasting in which a bounded, deterministic agent layer operates under a deterministic model-governance engine. The platform is evaluated on the RTS-GMLC dataset: 8,784 matched hourly observations per target (system load, aggregate wind, and utility-scale photovoltaic output) for calendar year 2020, obtained by census sampling of the full hourly series and partitioned exclusively by chronological, protocol-frozen splits, with a locked final-test partition covering November 1 to December 31, 2020 (1,464 hours). Random resampling is prohibited at every stage. On the frozen final-test partition, the production-candidate random-forest load model reached a mean absolute error (MAE) of 174.26 MW, 72.3% worse than the reference day-ahead forecast (101.14 MW), and the hist-gradient-boosting wind model reached 778.84 MW, 135.1% worse than the same reference (331.30 MW); only the photovoltaic model (36.12 MW) outperformed its persistence benchmark (39.09 MW) by 7.6%. A subsequent residual-correction study reduced load MAE to 1.54 under a five-fold chronological validation, an approximately 98.5% reduction relative to the day-ahead reference, yet a deterministic governance evaluation denied all seven packaged candidates for lineage, fingerprint, protocol, and evidence deficiencies. The results support a governance-first conclusion: strong offline metrics alone do not constitute promotion eligibility, and bounded agents can assist lifecycle work only as advisory components under deterministic policy control.", { size: 18 }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED, spacing: { line: 220, after: 120 },
    children: [
      run("Index Terms\u2014", { size: 18, bold: true }),
      run("MLOps, smart grids, renewable energy forecasting, machine learning governance, bounded agents, drift monitoring, chronological validation, RTS-GMLC.", { size: 18 }),
    ],
  }),
];

// ---------- body sections ----------
const intro = [
  h1("I", "Introduction"),
  body("Machine learning (ML) systems in the electric energy sector are increasingly responsible for operational forecasts that inform unit commitment, balancing decisions, and renewable-integration planning. At the same time, the engineering cost of operating such systems\u2014data validation, retraining, evaluation, promotion, and rollback\u2014has motivated the application of agentic AI, in which language-model-driven or rule-driven agents perform lifecycle tasks autonomously [2], [3]. Unrestricted agent authority, however, is incompatible with the audit requirements of critical infrastructure: an agent that can promote, roll back, or retrain models can convert a plausible-looking recommendation into an unreviewed production change."),
  body("This paper describes and evaluates a research implementation of a guardrailed agentic MLOps platform for smart-grid forecasting. The design premise is a strict separation of authority: a bounded, deterministic agent layer may analyze, summarize, explain, and request review, while every lifecycle decision is made by a deterministic governance engine whose policy is frozen before evaluation. The platform is deliberately offline: there is no live telemetry, streaming, or production deployment, and no quantum, GNN, or LLM component is claimed."),
  body("The study makes three contributions. First, it specifies a reproducible, leakage-safe evaluation protocol on the RTS-GMLC dataset [1] in which all splits are chronological and the final-test partition is sealed during all development decisions. Second, it reports honest frozen-test results for load, wind, and photovoltaic (PV) forecasting, including negative outcomes relative to the reference day-ahead forecasts. Third, it demonstrates a governance-first evaluation in which a residual-correction research result that improved MAE by roughly two orders of magnitude was nevertheless denied promotion because its formal evidence\u2014fingerprints, lineage, and protocol compatibility\u2014did not satisfy a frozen policy engine."),
];

const related = [
  h1("II", "Related Work"),
  body("MLOps as a discipline addresses the technical debt that accumulates when ML systems are operated as continuously evolving software [2]. Surveys of deployment practice identify configuration and data management, monitoring, and the absence of reproducibility as dominant failure modes [3]; governance-first architectures respond by making promotion decisions explicit and auditable. Recent MLOps literature systematizes the pipeline structure and its organizational demands [9], [10]; our work differs in that the promotion path is fully deterministic and refuses model-quality metrics as a sufficient condition for deployment, in the spirit of production-readiness rubrics [11]."),
  body("Forecasting for power systems uses classical statistical baselines and ML regressors; we rely on random forests [5] and gradient boosting as implemented in scikit-learn [4], with persistence and published day-ahead forecasts as external benchmarks. Drift monitoring in our platform uses the population stability index (PSI) [6] and the normalized Wasserstein distance [7], with concept-drift severity handled descriptively rather than as a lifecycle trigger, following the principle that observation and action must be separately governed [8]."),
];

const architecture = [
  h1("III", "Classical Practice Versus the Guardrailed Design"),
  h2("A", "What a Classical MLOps Pipeline Does"),
  body("A conventional MLOps pipeline ingests data, retrains models on a schedule, selects the best-scoring candidate, and promotes it through a continuous-integration pipeline, increasingly with autonomous agents executing these steps from natural-language instructions [9], [10]. Data is commonly split randomly, drift alerts are wired directly to retraining jobs, promotion criteria reduce to a small set of offline metrics, and the audit trail is a secondary concern. Production-readiness rubrics make the gap explicit: most of the checks that matter in deployment concern data handling, lineage, and monitoring rather than model accuracy [11]. For energy forecasting specifically, the literature further warns that ML models frequently fail to outperform well-chosen statistical benchmarks, which makes honest benchmark comparison a first-class requirement rather than an afterthought [12]."),
  h2("B", "What This Implementation Does Instead"),
  bodyLeft("The platform comprises six fixed stages arranged as a pipeline: (1) forecasting, in which frozen models score the locked test partition; (2) monitoring, in which historical replay computes drift and performance statistics; (3) analysis, in which a bounded agent inspects monitoring evidence; (4) governance, in which a deterministic policy engine evaluates candidate evidence; (5) decision, in which ALLOW, DENY, or REQUIRE-APPROVAL outcomes are recorded with SHA-256 decision fingerprints; and (6) audit, in which an append-only JSONL ledger records every event. Two structural firewalls bound the agent layer. A capability firewall restricts recommendations to five advisory types (INVESTIGATE, SUMMARIZE, EXPLAIN, REQUEST_HUMAN_REVIEW, CREATE_REPORT); seven lifecycle action types (PROMOTE, DEPLOY, ROLLBACK, RETRAIN, CHANGE_POLICY, MODIFY_MODEL, MODIFY_FEATURES) are intercepted and audited. A decision firewall ensures that drift observations can never trigger retraining, promotion, or rollback directly. Agent memory stores structured summaries and evidence references only; no chain-of-thought or private reasoning traces are persisted."),
  body("Table I contrasts the two designs aspect by aspect."),
  tableCaption("TABLE I", "Classical or Agent-Autonomous MLOps Versus the Guardrailed Implementation"),
  threeLineTable(
    [22, 39, 39],
    ["Aspect", "Classical / agent-autonomous practice", "Guardrailed implementation (this work)"],
    [
      ["Dataset access", "Ad-hoc files; random splits common", "Checksummed manifests; census sampling; chronological splits only"],
      ["Final test", "Reused during tuning and selection", "Sealed behind protocol freeze; single authorized access after freezing"],
      ["Drift response", "Alerts auto-trigger retraining", "Observational evidence only; retraining requires a separately evaluated deterministic policy"],
      ["Agent authority", "Autonomous tool execution", "Five advisory types; seven lifecycle actions blocked and audited"],
      ["Promotion", "Best offline metric wins", "12 ordered governance gates plus canary; metrics alone never sufficient"],
      ["Retraining", "Scheduled or drift-triggered", "Challenger registered as candidate; never replaces champion automatically"],
      ["Rollback", "Best-effort restore", "Previous champion preserved and verified before any promotion takes effect"],
      ["Audit", "Optional logging", "Append-only JSONL ledger; SHA-256 decision fingerprints"],
      ["Agent memory", "Full transcripts retained", "Structured summaries and evidence references only"],
      ["Human role", "Rubber-stamp approval", "Explicit approval gate before production champion replacement"],
    ]),
];

const lifecycle = [
  h1("IV", "Implemented Research Lifecycle"),
  body("The architecture is not a proposal; it was executed end-to-end as a sequence of recorded phases, each with its own completion report, tests, and artifacts. The production pipeline runs forecast evaluation, historical-replay monitoring, bounded agent analysis, governance evaluation, decision recording, and audit. On the research side, eight stages were executed in order: historical telemetry replay (Stage 07) reproducing monitoring windows over the locked partition; incremental, warm-up-aware drift monitoring (Stage 08); forecasting research with honest baseline comparison (Stage 09); residual correction against the day-ahead reference (Stage 10); five-fold robustness validation of the candidate pipeline (Stage 11); a first governance evaluation (Stage 12); formal candidate packaging with fingerprints and lineage (Stage 13); and an authoritative governance re-evaluation with a hardened evidence format (Stage 14)."),
  body("Every stage reads only approved, checksummed data; every experiment records dataset version, feature and preprocessing versions, model family, hyperparameters, random seeds, and library versions alongside its artifacts. The product layer then exposes the frozen evidence through a read-only API (17 endpoints) and a research console that adds user-supplied datasets and local chronological experiments; the console can register a dataset and run an experiment, but it has no code path that can mutate the lifecycle registry or bypass the governance engine."),
]

const dataset = [
  h1("V", "Dataset and Sampling Strategy"),
  h2("A", "Dataset Origin"),
  body("All experiments use the RTS-GMLC dataset (Reliability Test System Grid Modernization Lab Consortium) published by the U.S. National Renewable Energy Laboratory [1]. The archive was acquired by ZIP download on August 13, 2026, with the archive checksum recorded in the data manifest. Six source time-series files (day-ahead and real-time regional load, wind, and PV) were ingested; per-file SHA-256 checksums were recorded before and after processing, and the processing pipeline verified that all source files were unchanged."),
  h2("B", "Preprocessing and Coverage"),
  body("Native-resolution series (5-minute and hourly mixed) were aligned and aggregated to hourly resolution. Each of the three targets\u2014system load, aggregate wind, and aggregate utility-scale PV\u2014yields 8,784 matched hourly timestamps for calendar year 2020 (a leap year) with zero unmatched or duplicate entries and zero missing values. PV nighttime zeros (46.4% of hourly observations) are observed physical behavior, not missingness, and are retained. Table II summarizes the resulting distributions."),
  tableCaption("TABLE II", "Hourly Dataset Characteristics (RTS-GMLC processed v1, MW)"),
  threeLineTable(
    [26, 13, 13, 13, 13, 13, 9],
    ["Target", "Obs.", "Mean", "Std.", "Min", "Max", "Zeros"],
    [
      ["System load", "8,784", "4,164.6", "1,014.1", "2,645.9", "7,960.8", "0.0%"],
      ["Aggregate wind", "8,784", "779.1", "779.8", "15.3", "2,470.3", "0.0%"],
      ["Utility-scale PV", "8,784", "405.2", "472.9", "0.0", "1,359.6", "46.4%"],
    ]),
  h2("C", "Sampling Design"),
  body("The sampling strategy is a purposive census of the target population: every hourly observation of the 2020 series is retained, so no random subsampling is performed and no sampling weights are required. Partitioning is strictly chronological and deterministic. Development decisions (feature construction, model and hyperparameter selection, threshold calibration, and early stopping) use only training and validation data under a rolling-origin scheme; the final-test partition, November 1 to December 31, 2020 (1,464 hours), is sealed behind an experimental-design protocol freeze (Phase 19) and is accessed only in an authorized final-evaluation mode after the candidate configuration is frozen. Random train/test splitting is prohibited by policy at every stage, because random resampling of a correlated hourly series leaks future information into training."),
];

const methodology = [
  h1("VI", "Methodology"),
  h2("A", "Forecasting Models and Features"),
  body("Candidate regressors are random forest, multi-layer perceptron, histogram gradient boosting, and ridge regression, all implemented in scikit-learn [4] with fixed random seeds. Feature blocks are built only from past observations (lag blocks at 1, 24, and 168 hours, calendar encodings, and rolling statistics), with scaling fitted inside the training pipeline only. The published RTS day-ahead series is treated as an external benchmark and is never used as a model feature except in an explicitly declared residual-correction experiment."),
  h2("B", "Evaluation Metrics"),
  body("Models are compared on mean absolute error (MAE), root-mean-square error (RMSE), symmetric mean absolute percentage error (sMAPE), and their normalized variants (nMAE, nRMSE). Every frozen model is additionally scored against a target-specific external benchmark: the published RTS day-ahead forecast for load and wind, and an H24 daily-persistence forecast for PV."),
  h2("C", "Leakage Controls"),
  body("Feature creation, normalization, imputation, and target transformations are fit on training-period data only and applied forward. The final-test targets are inaccessible during feature selection, model selection, hyperparameter optimization, and threshold tuning; final-test access occurs in a single authorized evaluation whose protocol (partitions, horizons, metrics, and random seeds) is frozen beforehand."),
  h2("D", "Residual-Correction Study"),
  body("A separately authorized research stage models the residual between the day-ahead forecast and the actual load using a small, leakage-safe feature set (the day-ahead value at the target hour, cyclic calendar features, and lagged residuals at 1, 24, and 168 hours). Candidate correctors include a constant-bias baseline, ridge regression, and histogram gradient boosting with the same hyperparameters as the frozen Phase 19 model family."),
  h2("E", "Drift Monitoring"),
  body("Monitoring replays history in weekly windows with a one-day stride and computes, per feature block, the PSI and a normalized Wasserstein distance against a reference period, together with a rolling MAE performance signal. Thresholds are calibrated as the 99th percentile of reference-block statistics and frozen. Severity is classified as NONE, WATCH, WARNING, or CRITICAL by the count of triggered monitors and their magnitudes. Monitoring is observational: alerts are evidence for agents and humans, never direct lifecycle triggers."),
  h2("F", "Deterministic Governance Engine"),
  body("The governance engine evaluates candidate packages against a frozen Phase 13 policy. The lifecycle state machine has 13 states; evaluation passes through 12 ordered gates covering registration, lineage, model- and feature-specification fingerprints, protocol compatibility, metadata, evaluation, performance, benchmark comparison, statistical evidence, and approvals, producing one of 16 reason codes per failed gate. Decisions are ALLOW, DENY, or REQUIRE_APPROVAL, each sealed with a SHA-256 decision fingerprint. Promotion additionally requires a canary stage, and rollback of the previous champion is mandatory and verified infrastructure."),
];

const setup = [
  h1("VII", "Experimental Setup"),
  body("The platform runs offline in a single repository with Python and scikit-learn; every experiment records the dataset version, feature and preprocessing versions, model family and hyperparameters, random seeds, and library versions alongside its artifacts. The evaluation protocol (partitions, horizons, metrics, and seed policy) was frozen in a Phase 19 design document before the final-test partition was read. The product layer exposes the frozen evidence through a read-only API and a frontend console in which no lifecycle mutation is reachable from the user interface."),
];

const results = [
  h1("VIII", "Results"),
  h2("A", "Frozen Final-Test Forecasting Performance"),
  body("Table III reports the frozen-model comparison on the sealed test partition. For load, the random-forest candidate reached an MAE of 174.26 MW against 281.00 MW for the multilayer perceptron (MLP), but both are far worse than the published day-ahead forecast (101.14 MW). For wind, the histogram-gradient-boosting candidate reached 778.84 MW against a day-ahead reference of 331.30 MW. Only the PV random forest beat its persistence benchmark (36.12 vs. 39.09 MW). These negative outcomes are reported as-is: no configuration was re-tuned against the test partition after unsealing."),
  tableCaption("TABLE III", "Frozen Final-Test Comparison (MAE in MW; test window 2020-11-01 to 2020-12-31)"),
  threeLineTable(
    [11, 31, 15, 15, 14, 14],
    ["Target", "Model", "MAE", "RMSE", "sMAPE", "nMAE"],
    [
      ["Load", "Random forest", "174.26", "231.27", "4.72", "0.0474"],
      ["Load", "MLP", "281.00", "343.36", "7.78", "0.0764"],
      ["Load", "Day-ahead (published)", "101.14", "101.85", "2.72", "0.0275"],
      ["Wind", "Hist. gradient boosting", "778.84", "923.37", "92.40", "0.6790"],
      ["Wind", "MLP", "838.40", "957.93", "96.13", "0.7309"],
      ["Wind", "Day-ahead (published)", "331.30", "491.21", "50.92", "0.2888"],
      ["PV", "Random forest", "36.12", "82.08", "117.73", "0.1082"],
      ["PV", "MLP", "221.64", "249.27", "135.47", "0.6637"],
      ["PV", "H24 persistence", "39.09", "100.69", "7.86", "0.1171"],
    ]),
  body("Table IV summarizes the benchmark decision per target. Only PV satisfies its benchmark gate; load and wind candidates fail with large relative deficits."),
  tableCaption("TABLE IV", "Benchmark Gate Outcomes on the Frozen Final-Test Partition"),
  threeLineTable(
    [10, 24, 13, 24, 14, 15],
    ["Target", "Frozen model", "MAE", "Benchmark (MAE)", "Rel. diff.", "Outcome"],
    [
      ["Load", "Random forest", "174.26", "Day-ahead (101.14)", "+72.3%", "FAIL"],
      ["Wind", "Hist. gradient boosting", "778.84", "Day-ahead (331.30)", "+135.1%", "FAIL"],
      ["PV", "Random forest", "36.12", "H24 persistence (39.09)", "\u22127.6%", "PASS"],
    ]),
  h2("B", "Residual-Correction Research"),
  body("The residual-correction study produced a substantially better load forecast: the best candidate achieved MAE 1.54 on held-out validation under a five-fold chronological scheme with zero detected leakage, an approximately 98.5% reduction relative to the day-ahead reference MAE of 101.14. Because this result depended on the day-ahead series as an input feature, it defines a forecast-correction experiment rather than a standalone forecaster, and its evidence was packaged for governance evaluation under the same frozen policy as any other candidate."),
  h2("C", "Governance Outcomes"),
  bodyLeft("Across two governance evaluations (Stages 12 and 14), all seven packaged candidates were DENIED. Recurring reason codes include MODEL_SPEC_FINGERPRINT_MISMATCH, FEATURE_SPEC_FINGERPRINT_MISMATCH, PROTOCOL_MISMATCH, and EVIDENCE_INVALID; earlier audit probes also surfaced BENCHMARK_GATE_FAILED, STATISTICAL_EVIDENCE_FAILED, LINEAGE_INCOMPLETE, REPRODUCIBILITY_INCOMPLETE, UNRESOLVED_DEVIATION, and INVALID_STATE_TRANSITION. No agent recommendation, monitoring alert, or superior offline metric overrode a denial. The strong residual-correction result was therefore correctly prevented from entering the lifecycle as a promoted model: its formal evidence (fingerprint and protocol compatibility) did not satisfy the frozen policy, regardless of its measured accuracy."),
];

const discussion = [
  h1("IX", "Discussion"),
  body("The central finding is asymmetry between research evidence and governance evidence. A candidate that improves MAE by two orders of magnitude is still not promotion-eligible when its lineage, fingerprints, and protocol compatibility fail; conversely, a candidate that merely beats a benchmark by a small margin but carries complete, verifiable evidence satisfies more gates. This asymmetry is the intended behavior: it protects critical infrastructure from the most common failure mode of automated ML, which is silent, under-documented promotion of models whose measured performance does not generalize."),
  body("The bounded agent layer demonstrates that agentic assistance does not require autonomous authority. In the platform, agents reduced manual inspection effort (summarizing drift evidence, drafting explanations, requesting human review) while the capability firewall made lifecycle mutation structurally impossible: blocked recommendations are returned as first-class, audited outcomes rather than errors. The negative forecasting results for load and wind further emphasize the value of published day-ahead forecasts as strong external baselines that internal ML candidates must be honestly compared against before any deployment claim."),
];

const limitations = [
  h1("X", "Limitations and Future Work"),
  body("The study is limited to a single dataset, a single calendar year, and offline evaluation; no live deployment, streaming telemetry, or production dispatch decision is involved. The residual-correction result is validated on held-out folds of the same dataset and has not been evaluated on external systems. The governance engine has been exercised with denial outcomes; a full ALLOW path, canary execution, and verified rollback remain to be demonstrated end-to-end in future work. Planned extensions include external-dataset validation, a governed champion-challenger evaluation with a passing canary, and richer renewable-utilization analytics (load-matching and surplus-energy characterization) under the same advisory-only agent constraints."),
];

const conclusion = [
  h1("XI", "Conclusion"),
  body("A guardrailed agentic MLOps platform for renewable-integrated smart-grid forecasting was implemented and evaluated under a fully deterministic governance regime on the RTS-GMLC dataset. Census sampling of 8,784 matched hourly observations per target, strictly chronological protocol-frozen partitions, and a sealed 1,464-hour final-test window yielded honest benchmark outcomes in which only the PV model beat its baseline, while load and wind candidates were dominated by the published day-ahead forecasts. A residual-correction study reduced load MAE to 1.54, yet the deterministic governance engine denied all seven candidates for formal evidence deficiencies, confirming that superior metrics alone do not confer promotion eligibility. The results support bounded agent authority\u2014advisory analysis under a capability firewall\u2014as a practical architecture for research-grade MLOps in critical energy infrastructure."),
];

const references = [
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 240, after: 120, line: 240 },
    children: [run("REFERENCES", { smallCaps: true })],
  }),
  refEntry("[1] B. Kelley et al., \u201cReliability Test System Grid Modernization Lab Consortium (RTS-GMLC),\u201d National Renewable Energy Laboratory, Golden, CO, USA, 2020. [Online]. Available: https://github.com/NREL/RTS-GMLC"),
  refEntry("[2] D. Sculley, G. Holt, D. Golovin, E. Davydov, T. Phillips, D. Ebner, V. Chaudhary, M. Young, J.-F. Crespo, and D. Dennison, \u201cHidden technical debt in machine learning systems,\u201d in Advances in Neural Information Processing Systems 28 (NIPS 2015), Montreal, QC, Canada, 2015."),
  refEntry("[3] A. Paleyes, R.-G. Urma, and N. D. Lawrence, \u201cChallenges in deploying machine learning: A survey of case studies,\u201d ACM Computing Surveys, vol. 55, no. 6, art. 114, 2022."),
  refEntry("[4] F. Pedregosa, G. Varoquaux, A. Gramfort, V. Michel, B. Thirion, O. Grisel, M. Blondel, P. Prettenhofer, R. Weiss, V. Dubourg, J. Vanderplas, A. Passos, D. Cournapeau, M. Brucher, M. Perrot, and E. Duchesnay, \u201cScikit-learn: Machine learning in Python,\u201d Journal of Machine Learning Research, vol. 12, pp. 2825\u20132830, 2011."),
  refEntry("[5] L. Breiman, \u201cRandom forests,\u201d Machine Learning, vol. 45, no. 1, pp. 5\u201332, 2001."),
  refEntry("[6] N. Siddiqi, Credit Risk Scorecards: Developing and Implementing Intelligent Credit Scoring. Hoboken, NJ, USA: Wiley, 2006."),
  refEntry("[7] C. Villani, Optimal Transport: Old and New. Berlin, Germany: Springer, 2009."),
  refEntry("[8] J. Gama, I. \u017dliobait\u0117, A. Bifet, M. Pechenizkiy, and A. Bouchachia, \u201cA survey on concept drift adaptation,\u201d ACM Computing Surveys, vol. 46, no. 4, art. 44, 2014."),
    refEntry("[9] D. Kreuzberger, N. K\u00fchl, and S. Hirschl, \u201cMachine learning operations (MLOps): Overview, definition, and structure,\u201d IEEE Access, vol. 11, pp. 26791\u201326813, 2023."),
  refEntry("[10] S. Amershi, A. Begel, C. Bird, R. DeLine, H. Gall, E. Kamar, N. Nagappan, B. Nushi, and T. Zimmermann, \u201cSoftware engineering for machine learning: A case study,\u201d in Proc. 41st International Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP), IEEE, 2019, pp. 291\u2013300."),
  refEntry("[11] E. Breck, S. Cai, E. Nielsen, M. Salib, and D. Sculley, \u201cThe ML test score: A rubric for ML production readiness and technical debt reduction,\u201d in Proc. IEEE International Conference on Big Data, 2017, pp. 1123\u20131132."),
  refEntry("[12] S. Makridakis, E. Spiliotis, and V. Assimakopoulos, \u201cStatistical and machine learning forecasting methods: Concerns and ways forward,\u201d PLOS ONE, vol. 13, no. 3, e0194889, 2018."),
];

// ---------- document ----------
const pageProps = {
  page: {
    size: { width: 12240, height: 15840 },
    margin: { top: 1080, bottom: 1440, left: 1080, right: 1080, header: 720, footer: 720 },
  },
};

const footer = new Footer({
  children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], size: 16, font: TNR, color: BLACK })],
  })],
});

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: TNR, size: 20, color: BLACK },
        paragraph: { spacing: { line: 240 } },
      },
    },
  },
  sections: [
    { properties: pageProps, footers: { default: footer }, children: titleBlock },
    {
      properties: Object.assign({}, pageProps, {
        type: SectionType.CONTINUOUS,
        column: { count: 2, space: 360, equalWidth: true },
      }),
      children: [
        ...abstractBlock,
        ...intro, ...related, ...architecture, ...dataset,
        ...methodology, ...setup, ...results, ...discussion,
        ...limitations, ...conclusion, ...references,
      ],
    },
    {
      // Trailing continuous section break: forces Word to balance the final
      // page's columns (IEEE convention — last page has equal columns).
      properties: Object.assign({}, pageProps, {
        type: SectionType.CONTINUOUS,
        column: { count: 2, space: 360, equalWidth: true },
      }),
      children: [new Paragraph({ spacing: { line: 240 }, children: [] })],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  let out = "C:/Projects/guardrailed-agentic-mlops-smart-grid_trial/reports/paper/IEEE_Guardrailed_Agentic_MLOps_Smart_Grid.docx";
try {
  fs.writeFileSync(out, buf);
} catch (e) {
  if (e.code === "EBUSY") {
    out = "C:/Projects/guardrailed-agentic-mlops-smart-grid_trial/reports/paper/IEEE_Guardrailed_Agentic_MLOps_Smart_Grid_v2.docx";
    fs.writeFileSync(out, buf);
  } else { throw e; }
}
  fs.mkdirSync(require("path").dirname(out), { recursive: true });
  fs.writeFileSync(out, buf);
  console.log("written:", out, buf.length, "bytes");
});
