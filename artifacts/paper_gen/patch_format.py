import io

p = "generate_paper.js"
s = io.open(p, encoding="utf-8").read()

# ---- 1) bodyLeft helper: left-aligned body paragraph (avoids justification
#        rivers around unbreakable ALL-CAPS tokens) ----
anchor = "function h1(num, text) {"
helper = """function bodyLeft(text) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { line: 240, after: 0 },
    indent: { firstLine: 288 },
    children: Array.isArray(text) ? text : [run(text)],
  });
}

function h1(num, text) {"""
s = s.replace(anchor, helper, 1)

# ---- 2) Architecture paragraph with the two ALL-CAPS lists -> left aligned ----
old = '  body("The platform comprises six fixed stages arranged as a pipeline:'
new = '  bodyLeft("The platform comprises six fixed stages arranged as a pipeline:'
assert old in s
s = s.replace(old, new, 1)

# ---- 3) Governance outcomes paragraph with reason codes -> left aligned ----
old = '  body("Across two governance evaluations (Stages 12 and 14), all seven packaged candidates were DENIED.'
new = '  bodyLeft("Across two governance evaluations (Stages 12 and 14), all seven packaged candidates were DENIED.'
assert old in s
s = s.replace(old, new, 1)

# ---- 4) Table II caption + column widths/headers ----
s = s.replace('tableCaption("TABLE II", "Hourly Dataset Characteristics (rts_gmlc_processed_v1, MW)")',
              'tableCaption("TABLE II", "Hourly Dataset Characteristics (RTS-GMLC processed v1, MW)")')
s = s.replace("""  threeLineTable(
    [24, 15, 13, 13, 13, 13, 9],
    ["Target", "Obs.", "Mean", "Std.", "Min", "Max", "Zero %"],
    [
      ["System load", "8,784", "4,164.55", "1,014.09", "2,645.90", "7,960.81", "0.0"],
      ["Aggregate wind", "8,784", "779.09", "779.77", "15.28", "2,470.29", "0.0"],
      ["Utility-scale PV", "8,784", "405.22", "472.92", "0.00", "1,359.61", "46.4"],
    ]),""",
"""  threeLineTable(
    [26, 13, 13, 13, 13, 13, 9],
    ["Target", "Obs.", "Mean", "Std.", "Min", "Max", "Zeros"],
    [
      ["System load", "8,784", "4,164.6", "1,014.1", "2,645.9", "7,960.8", "0.0%"],
      ["Aggregate wind", "8,784", "779.1", "779.8", "15.3", "2,470.3", "0.0%"],
      ["Utility-scale PV", "8,784", "405.2", "472.9", "0.0", "1,359.6", "46.4%"],
    ]),""")

# ---- 5) Table III: proper-case names, wider model column, no % headers ----
s = s.replace("""  threeLineTable(
    [13, 29, 15, 15, 14, 14],
    ["Target", "Model", "MAE", "RMSE", "sMAPE %", "nMAE"],
    [
      ["load", "random_forest", "174.26", "231.27", "4.72", "0.0474"],
      ["load", "mlp", "281.00", "343.36", "7.78", "0.0764"],
      ["load", "RTS_DAY_AHEAD", "101.14", "101.85", "2.72", "0.0275"],
      ["wind", "hist_grad_boost", "778.84", "923.37", "92.40", "0.6790"],
      ["wind", "mlp", "838.40", "957.93", "96.13", "0.7309"],
      ["wind", "RTS_DAY_AHEAD", "331.30", "491.21", "50.92", "0.2888"],
      ["pv", "random_forest", "36.12", "82.08", "117.73", "0.1082"],
      ["pv", "mlp", "221.64", "249.27", "135.47", "0.6637"],
      ["pv", "H24 persistence", "39.09", "100.69", "7.86", "0.1171"],
    ]),""",
"""  threeLineTable(
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
    ]),""")

# ---- 6) Table IV: proper-case names, shorter benchmark text, header fixes ----
s = s.replace("""  threeLineTable(
    [11, 24, 15, 20, 15, 15],
    ["Target", "Frozen model", "Model MAE", "Benchmark (MAE)", "Rel. diff.", "Outcome"],
    [
      ["load", "random_forest", "174.26", "RTS day-ahead (101.14)", "+72.3%", "FAIL"],
      ["wind", "hist_grad_boost", "778.84", "RTS day-ahead (331.30)", "+135.1%", "FAIL"],
      ["pv", "random_forest", "36.12", "H24 persistence (39.09)", "\\u22127.6%", "PASS"],
    ]),""",
"""  threeLineTable(
    [10, 24, 13, 24, 14, 15],
    ["Target", "Frozen model", "MAE", "Benchmark (MAE)", "Rel. diff.", "Outcome"],
    [
      ["Load", "Random forest", "174.26", "Day-ahead (101.14)", "+72.3%", "FAIL"],
      ["Wind", "Hist. gradient boosting", "778.84", "Day-ahead (331.30)", "+135.1%", "FAIL"],
      ["PV", "Random forest", "36.12", "H24 persistence (39.09)", "\\u22127.6%", "PASS"],
    ]),""")

# ---- 7) In-text naming consistency with the tables ----
s = s.replace("the random-forest candidate reached an MAE of 174.26 MW against 281.00 MW for the MLP",
              "the random-forest candidate reached an MAE of 174.26 MW against 281.00 MW for the multilayer perceptron (MLP)")
s = s.replace("For wind, histogram gradient boosting reached 778.84 MW",
              "For wind, the histogram-gradient-boosting candidate reached 778.84 MW")
s = s.replace("Only the PV random forest beat its persistence benchmark (36.12 vs. 39.09 MW).",
              "Only the PV random forest beat its persistence benchmark (36.12 vs. 39.09 MW).")
s = s.replace('["load", "random_forest", "174.26"', '["Load", "Random forest", "174.26"')  # safety no-op if already replaced

io.open(p, "w", encoding="utf-8").write(s)
print("patched ok")
