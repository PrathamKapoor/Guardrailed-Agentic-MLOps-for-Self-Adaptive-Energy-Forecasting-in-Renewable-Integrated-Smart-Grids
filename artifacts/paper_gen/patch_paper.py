import io

p = "generate_paper.js"
s = io.open(p, encoding="utf-8").read()

# 1) Replace the architecture section with an expanded classical-vs-ours section
old_arch_start = s.index("const architecture = [")
old_arch_end = s.index("const dataset = [")
new_arch = '''const architecture = [
  h1("III", "Classical Practice Versus the Guardrailed Design"),
  h2("A", "What a Classical MLOps Pipeline Does"),
  body("A conventional MLOps pipeline ingests data, retrains models on a schedule, selects the best-scoring candidate, and promotes it through a continuous-integration pipeline, increasingly with autonomous agents executing these steps from natural-language instructions [9], [10]. Data is commonly split randomly, drift alerts are wired directly to retraining jobs, promotion criteria reduce to a small set of offline metrics, and the audit trail is a secondary concern. Production-readiness rubrics make the gap explicit: most of the checks that matter in deployment concern data handling, lineage, and monitoring rather than model accuracy [11]. For energy forecasting specifically, the literature further warns that ML models frequently fail to outperform well-chosen statistical benchmarks, which makes honest benchmark comparison a first-class requirement rather than an afterthought [12]."),
  h2("B", "What This Implementation Does Instead"),
  body("The platform comprises six fixed stages arranged as a pipeline: (1) forecasting, in which frozen models score the locked test partition; (2) monitoring, in which historical replay computes drift and performance statistics; (3) analysis, in which a bounded agent inspects monitoring evidence; (4) governance, in which a deterministic policy engine evaluates candidate evidence; (5) decision, in which ALLOW, DENY, or REQUIRE-APPROVAL outcomes are recorded with SHA-256 decision fingerprints; and (6) audit, in which an append-only JSONL ledger records every event. Two structural firewalls bound the agent layer. A capability firewall restricts recommendations to five advisory types (INVESTIGATE, SUMMARIZE, EXPLAIN, REQUEST_HUMAN_REVIEW, CREATE_REPORT); seven lifecycle action types (PROMOTE, DEPLOY, ROLLBACK, RETRAIN, CHANGE_POLICY, MODIFY_MODEL, MODIFY_FEATURES) are intercepted and audited. A decision firewall ensures that drift observations can never trigger retraining, promotion, or rollback directly. Agent memory stores structured summaries and evidence references only; no chain-of-thought or private reasoning traces are persisted."),
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

'''
s = s[:old_arch_start] + new_arch + s[old_arch_end:]

# 2) Renumber dataset section IV -> V and its table caption I -> II
s = s.replace('h1("IV", "Dataset and Sampling Strategy")', 'h1("V", "Dataset and Sampling Strategy")')
s = s.replace('tableCaption("TABLE I", "Hourly Dataset Characteristics (rts_gmlc_processed_v1, MW)")',
              'tableCaption("TABLE II", "Hourly Dataset Characteristics (rts_gmlc_processed_v1, MW)")')
s = s.replace("Table I summarizes the resulting distributions.", "Table II summarizes the resulting distributions.")

# 3) Results tables renumber II->III, III->IV and in-text mentions
s = s.replace('tableCaption("TABLE II", "Frozen Final-Test Comparison (MAE in MW; test window 2020-11-01 to 2020-12-31)")',
              'tableCaption("TABLE III", "Frozen Final-Test Comparison (MAE in MW; test window 2020-11-01 to 2020-12-31)")')
s = s.replace('tableCaption("TABLE III", "Benchmark Gate Outcomes on the Frozen Final-Test Partition")',
              'tableCaption("TABLE IV", "Benchmark Gate Outcomes on the Frozen Final-Test Partition")')
s = s.replace("Table II reports the frozen-model comparison", "Table III reports the frozen-model comparison")
s = s.replace("Table III summarizes the benchmark decision per target.", "Table IV summarizes the benchmark decision per target.")

# 4) Renumber remaining sections V..X -> VI..XI
s = s.replace('h1("V", "Methodology")', 'h1("VI", "Methodology")')
s = s.replace('h1("VI", "Experimental Setup")', 'h1("VII", "Experimental Setup")')
s = s.replace('h1("VII", "Results")', 'h1("VIII", "Results")')
s = s.replace('h1("VIII", "Discussion")', 'h1("IX", "Discussion")')
s = s.replace('h1("IX", "Limitations and Future Work")', 'h1("X", "Limitations and Future Work")')
s = s.replace('h1("X", "Conclusion")', 'h1("XI", "Conclusion")')

# 5) Weave new citations into Related Work
s = s.replace("Our work differs in that the promotion path is fully deterministic and refuses model-quality metrics as a sufficient condition for deployment.",
              "Recent MLOps literature systematizes the pipeline structure and its organizational demands [9], [10]; our work differs in that the promotion path is fully deterministic and refuses model-quality metrics as a sufficient condition for deployment, in the spirit of production-readiness rubrics [11].")

# 6) Add 4 more real references (total 12)
ref8 = 'refEntry("[8] J. Gama, I. \\u017dliobait\\u0117, A. Bifet, M. Pechenizkiy, and A. Bouchachia, \\u201cA survey on concept drift adaptation,\\u201d ACM Computing Surveys, vol. 46, no. 4, art. 44, 2014."),'
add = (
    '  refEntry("[9] D. Kreuzberger, N. K\\u00fchl, and S. Hirschl, \\u201cMachine learning operations (MLOps): '
    'Overview, definition, and structure,\\u201d IEEE Access, vol. 11, pp. 26791\\u201326813, 2023."),\n'
    '  refEntry("[10] S. Amershi, A. Begel, C. Bird, R. DeLine, H. Gall, E. Kamar, N. Nagappan, B. Nushi, and '
    'T. Zimmermann, \\u201cSoftware engineering for machine learning: A case study,\\u201d in Proc. 41st International '
    'Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP), IEEE, 2019, pp. 291\\u2013300."),\n'
    '  refEntry("[11] E. Breck, S. Cai, E. Nielsen, M. Salib, and D. Sculley, \\u201cThe ML test score: A rubric for ML '
    'production readiness and technical debt reduction,\\u201d in Proc. IEEE International Conference on Big Data, '
    '2017, pp. 1123\\u20131132."),\n'
    '  refEntry("[12] S. Makridakis, E. Spiliotis, and V. Assimakopoulos, \\u201cStatistical and machine learning '
    'forecasting methods: Concerns and ways forward,\\u201d PLOS ONE, vol. 13, no. 3, e0194889, 2018."),'
)
assert ref8 in s, "ref8 anchor not found"
s = s.replace(ref8, ref8 + "\n  " + add)

io.open(p, "w", encoding="utf-8").write(s)
print("patched ok")
