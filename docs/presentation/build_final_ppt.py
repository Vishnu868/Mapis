from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
SHOT = "/home/user/Mapis/docs/screenshots/trained_3_decomposed_email_held.png"
MAROON = RGBColor(0xA4, 0x12, 0x3F)
INK = RGBColor(0x1F, 0x29, 0x33)
GREY = RGBColor(0x5B, 0x67, 0x70)
LIGHT = RGBColor(0xF3, 0xF4, 0xF6)
LINE = RGBColor(0xD0, 0xD5, 0xDA)
GREEN = RGBColor(0x2B, 0x7A, 0x4B)
FONT = "Calibri"

prs = Presentation(SRC)
slides = list(prs.slides)
W = prs.slide_width


def clear(slide, keep_pictures=False, keep_placeholders=False):
    for sh in list(slide.shapes):
        if keep_pictures and sh.shape_type == 13:
            continue
        if keep_placeholders and sh.is_placeholder:
            continue
        sh._element.getparent().remove(sh._element)


def tb(slide, x, y, w, h, text="", size=16, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        s.name = name
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    lines = text if isinstance(text, list) else [text]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = FONT
        r.font.color.rgb = color
    return s


def bullets(slide, x, y, w, h, items, size=16, gap=6, color=INK, plain=False):
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        head, _, rest = it.partition("||")
        if rest:
            r = p.add_run(); r.text = head; r.font.bold = True; r.font.size = Pt(size); r.font.name = FONT; r.font.color.rgb = MAROON
            r = p.add_run(); r.text = rest; r.font.size = Pt(size); r.font.name = FONT; r.font.color.rgb = color
        else:
            r = p.add_run(); r.text = "•  " + it; r.font.size = Pt(size); r.font.name = FONT; r.font.color.rgb = color
    return s


def title(slide, n, text, no):
    tb(slide, 0.5, 0.3, 9.0, 0.7, f"{n:02d} | {text}" if n else text, size=26, bold=True, color=INK, name="Title")
    tb(slide, 0.5, 7.0, 9.0, 0.3, f"FINAL REVIEW • B.TECH PROJECT • MAPIS • Team A1 • Slide {no}", size=9, color=GREY, name="Footer")


def card(slide, x, y, w, h, fill=LIGHT):
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.adjustments[0] = 0.06
    r.fill.solid(); r.fill.fore_color.rgb = fill
    r.line.fill.background()
    r.shadow.inherit = False
    return r


def stat(slide, x, y, w, big, label, color=MAROON):
    card(slide, x, y, w, 1.35)
    tb(slide, x, y + 0.1, w, 0.75, big, size=34, bold=True, color=color, align=PP_ALIGN.CENTER)
    tb(slide, x + 0.1, y + 0.82, w - 0.2, 0.5, label, size=12, color=GREY, align=PP_ALIGN.CENTER)


def table(slide, x, y, w, rows, col_w, size=12, row_h=0.36, header=True):
    nr, nc = len(rows), len(rows[0])
    gs = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    t = gs.table
    for j, cw in enumerate(col_w):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        t.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.06)
            c.margin_top = c.margin_bottom = Inches(0.02)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = ""
            r = p.add_run(); r.text = str(val)
            r.font.size = Pt(size); r.font.name = FONT
            c.fill.solid()
            if header and i == 0:
                c.fill.fore_color.rgb = MAROON
                r.font.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                c.fill.fore_color.rgb = LIGHT if i % 2 == 0 else RGBColor(255, 255, 255)
                r.font.color.rgb = INK
    return t


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def style_chart(chart, size=11):
    chart.font.size = Pt(size)
    chart.font.name = FONT
    chart.font.color.rgb = INK


# ---------------------------------------------------------------- slide 1 (title)
s = slides[0]
for sh in list(s.shapes):
    if sh.shape_type == 17:
        sh._element.getparent().remove(sh._element)
ph = {p.placeholder_format.type: p for p in s.placeholders}
for p in list(s.placeholders):
    p._element.getparent().remove(p._element)
tb(s, 0.5, 1.45, 9.0, 0.5, "FINAL REVIEW – B.TECH PROJECT", size=20, bold=True, align=PP_ALIGN.CENTER)
tb(s, 0.5, 2.05, 9.0, 1.5, "MAPIS — Multi-Agent Prompt Injection Shield", size=38, bold=True, color=MAROON, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
tb(s, 0.5, 3.55, 9.0, 0.7, "A stateful trust-scoring monitor for indirect prompt injection in multi-agent LLM pipelines", size=16, color=GREY, align=PP_ALIGN.CENTER)
tb(s, 0.5, 4.45, 9.0, 0.4, "Team Number: A1", size=16, bold=True, align=PP_ALIGN.CENTER)
tb(s, 1.2, 4.9, 7.6, 1.4, ["Dodla Nithya Sai – CB.SC.U4AIE23021", "Vishnu Vardhan – CB.SC.U4AIE23043",
                             "Sreekar Reddy – CB.SC.U4AIE23049", "Beena Reddy – CB.SC.U4AIE23065"], size=15, align=PP_ALIGN.CENTER)
tb(s, 0.5, 6.4, 9.0, 0.4, "Supervisor: Professor Sripriyan", size=16, bold=True, align=PP_ALIGN.CENTER)
tb(s, 0.5, 7.0, 9.0, 0.3, "FINAL REVIEW • B.TECH PROJECT • MAPIS • Team A1 • Slide 1", size=9, color=GREY, name="Footer")
notes(s, "Introduce the team and the project in one sentence: MAPIS is a security guard for teams of AI agents that remembers where every piece of information came from.")

# ---------------------------------------------------------------- slide 2 progress
s = slides[1]; clear(s); title(s, 1, "Progress Since First Review", 2)
rows = [["Area", "At First Review", "At Final Review"],
        ["Detector", "DeBERTa on single events", "Stateful: session signals in the classifier text, plus rules"],
        ["Runtime", "FastAPI /scan, heuristic baseline", "Tap, Redis session store, 4 response tiers, forensic trace"],
        ["Frameworks", "5-node LangGraph prototype", "LangGraph and AutoGen through one tap"],
        ["Data", "MAPIS-Bench v1, 1,693 sessions", "+ BIPIA, MultiHop, Decomposed, RealHarm, Adaptive; 2,304 test sessions"],
        ["Baselines", "Heuristic only", "Llama Guard, Prompt Guard 2, ProtectAI, NeMo, LLM judge"],
        ["Evaluation", "One held-out split", "5 training seeds, matched-FPR comparison, live LLM agents, team-written test set"],
        ["Interface", "Dashboard foundation", "Operator console: live monitor, session inspector, results"]]
table(s, 0.5, 1.2, 9.0, rows, [1.4, 2.9, 4.7], size=13, row_h=0.62)
tb(s, 0.5, 6.35, 9.0, 0.5, "All four project targets are now measured and met (slide 14).", size=16, bold=True, color=MAROON)
notes(s, "Contrast First Review and Final Review. At first review we had a trained classifier and a prototype. Now it is a complete shield evaluated against five baselines and on live LLM agents.")

# ---------------------------------------------------------------- slide 3 motivation
s = slides[2]; clear(s); title(s, 2, "Motivation & Problem Statement", 3)
bullets(s, 0.5, 1.15, 9.0, 2.0, [
    "Problem:||  An attacker hides text in a document, web page, tool output or memory. The agent trusts it and may act on it. Spread over several agents, no single message looks malicious.",
    "Gap:||  A guard that judges one message cannot tell a planted action from one the user asked for. The evidence is in the session history.",
    "Scope:||  In scope: indirect injection, multi-agent testbeds, stateful detection, tiered response, forensic trace, benchmarking. Out of scope: direct jailbreaks, training-time defences, multimodal injection, attacks on the classifier itself."], size=14, gap=8)
rows = [["Objective", "Target", "Status"],
        ["O1  Testbed with FastAPI tap (LangGraph + AutoGen)", "Every message, tool call, memory access", "Done"],
        ["O2  Labelled multi-hop benchmark", ">= 1,000 sessions, 5 attack classes", "Done: 8,000+ sessions"],
        ["O3  Stateful trust-scoring classifier", ">= 90 % accuracy, <= 5 % FPR", "98.5 % / 0.9 %"],
        ["O4  Tiered response + trace, latency", "<= 200 ms per message", "63 ms"],
        ["O5  Benchmark against existing guardrails", ">= 20 pts multi-hop recall gain", "+93 pts at matched FPR"]]
table(s, 0.5, 4.2, 9.0, rows, [4.0, 3.0, 2.0], size=12, row_h=0.45)
notes(s, "State the problem with the planted-address example. Then show each objective from the abstract with its measured status. The 8,000+ session count is the sum of the benchmark sets: v1 1,693, BIPIA 1,800, MultiHop about 2,100, RealHarm 2,330, Adaptive 1,692, Decomposed 288.")

# ---------------------------------------------------------------- slide 4 literature
s = slides[3]; clear(s); title(s, 3, "Literature Review & Research Gap", 4)
rows = [["Work", "What it does", "Limit that MAPIS addresses"],
        ["Greshake et al. 2023", "First showed indirect injection through retrieved content", "Attack discovery, no detector"],
        ["InjecAgent 2024, AgentDojo 2024", "Benchmarks for tool-using agents", "Explicit injection text; no fragment attacks with benign twins"],
        ["Task Shield 2024", "Checks each action against the user's task", "Per-action, relies on an LLM's judgement"],
        ["AgentWatcher 2026", "Attributes actions to causal context, rule-based monitor", "Adds LLM inference latency to every check"],
        ["LlamaFirewall AlignmentCheck 2025", "LLM audits the whole trajectory", "Heavy and post-hoc; our AlignmentCheck-style 7B judge flagged 80 % of benign multi-hop twins"],
        ["Prompt Infection 2024, G-Safeguard 2025", "Injection spreading across agents", "Study propagation or use graph models; not a lightweight inline stateful tap"]]
table(s, 0.5, 1.2, 9.0, rows, [2.3, 3.2, 3.5], size=12, row_h=0.62)
card(s, 0.5, 5.75, 9.0, 1.05, fill=RGBColor(0xF7, 0xE6, 0xEB))
tb(s, 0.65, 5.8, 8.7, 0.95, ["Research gap: a lightweight real-time monitor that carries session state across hops, tested on fragment attacks with matched benign twins.",
                             "MAPIS contribution: this combination, at a framework-neutral tap for AutoGen and LangGraph."], size=14, bold=True, color=INK, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "MAPIS is not the first work on multi-agent injection. The contribution is the combination: a small fine-tuned classifier fed with session signals, at a tap that works with both frameworks, evaluated with matched benign twins.")

# ---------------------------------------------------------------- slide 5 architecture
s = slides[4]; clear(s); title(s, 4, "System Architecture & Methodology", 5)
boxes = [("Agents", "planner, web, file,\nmemory, code/email\nLangGraph or AutoGen"),
         ("MAPIS tap", "FastAPI /inspect on every\nmessage, tool call,\nmemory read/write"),
         ("Session record", "Redis: goal, item sources,\nauthority claims,\nagent baselines"),
         ("Trust score", "DeBERTa-v3-small +\n4 signals, 0 = malicious\n1 = safe")]
x0, bw, gap = 0.5, 2.0, 0.33
for i, (h, t) in enumerate(boxes):
    x = x0 + i * (bw + gap)
    card(s, x, 1.25, bw, 1.75, fill=LIGHT if i not in (1, 2, 3) else RGBColor(0xF7, 0xE6, 0xEB))
    tb(s, x, 1.3, bw, 0.4, h, size=15, bold=True, color=MAROON, align=PP_ALIGN.CENTER)
    tb(s, x + 0.05, 1.75, bw - 0.1, 1.2, t.split("\n"), size=11, color=INK, align=PP_ALIGN.CENTER)
    if i < 3:
        tb(s, x + bw - 0.02, 1.9, gap + 0.04, 0.5, "→", size=22, bold=True, color=MAROON, align=PP_ALIGN.CENTER)
tiers = [("PASS", ">= 0.75", RGBColor(0x2B, 0x7A, 0x4B)), ("FLAG", "0.50 - 0.75", RGBColor(0xB7, 0x91, 0x0B)),
         ("QUARANTINE", "0.25 - 0.50", RGBColor(0xC2, 0x5E, 0x0E)), ("BLOCK", "< 0.25", RGBColor(0xB3, 0x26, 0x1E))]
tb(s, 0.5, 3.2, 9.0, 0.35, "Tiered response", size=15, bold=True)
for i, (n, r, col) in enumerate(tiers):
    x = 0.5 + i * 2.28
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(3.6), Inches(2.1), Inches(0.75))
    b.fill.solid(); b.fill.fore_color.rgb = col; b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    rr = p.add_run(); rr.text = n; rr.font.bold = True; rr.font.size = Pt(14); rr.font.name = FONT; rr.font.color.rgb = RGBColor(255, 255, 255)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
    rr = p2.add_run(); rr.text = r; rr.font.size = Pt(11); rr.font.name = FONT; rr.font.color.rgb = RGBColor(255, 255, 255)
bullets(s, 0.5, 4.55, 9.0, 2.4, [
    "The four signals:||  instruction in data, drift from the user goal, cross-hop provenance and escalation, behaviour anomaly.",
    "Same code in training and at run time:||  session.py builds the classifier text for both, so the model sees identical input.",
    "Response:||  QUARANTINE holds for operator Release or Reject. BLOCK drops the message and suspends the channel. Forensic trace: origin, relay, action.",
    "Stack:||  Python, PyTorch, HuggingFace, FastAPI, Redis, SQLite, React, LangGraph, AutoGen."], size=13, gap=5)
notes(s, "Walk the path of one message left to right. Emphasise the session record: it is what lets MAPIS tell a planted address from one the user named.")

# ---------------------------------------------------------------- slide 6 implementation status
s = slides[5]; clear(s); title(s, 5, "Implementation Status", 6)
rows = [["Component", "Status", "Evidence"],
        ["Testbed: LangGraph and AutoGen", "DONE", "backend/agents/graph.py, autogen_testbed.py"],
        ["FastAPI tap, Redis store, SQLite log", "DONE", "backend/api, backend/core/store.py, db.py"],
        ["Stateful shield: session record + 4 signals", "DONE", "backend/core/shield.py, session.py, features.py"],
        ["Classifier and training pipeline", "DONE", "backend/ml/, 3 training seeds"],
        ["Four tiers, channel suspension, quarantine review", "DONE", "Operator console, /inspect API"],
        ["Forensic trace and operator dashboard", "DONE", "frontend/ (live monitor, inspector, results)"],
        ["Benchmark sets and generators", "DONE", "scripts/generate_*.py, data/mapis_bench"],
        ["Baselines: 5 systems on identical sessions", "DONE", "backend/baselines.py, scripts/benchmark.py"],
        ["Live LLM agent evaluation (AgentDojo)", "DONE", "scripts/live_agentdojo.py"],
        ["Automated tests", "29 PASS", "tests/ (shield, API, train/serve parity, AutoGen tap)"]]
table(s, 0.5, 1.15, 9.0, rows, [3.9, 0.9, 4.2], size=12, row_h=0.5)
notes(s, "Everything planned in the abstract is implemented. Code is in the repository; the 29 tests include a train/serve parity test that checks the training text and the run-time text are identical.")

# ---------------------------------------------------------------- slide 7 setup
s = slides[6]; clear(s); title(s, 6, "Experimental Setup & Test Cases", 7)
rows = [["Set", "Content"],
        ["MAPIS-Bench v1", "1,693 sessions from AgentDojo and InjecAgent"],
        ["BIPIA", "1,800 sessions; test part never trained on"],
        ["MAPIS-MultiHop", "Fragment attacks across hops, the 5 mechanisms of the abstract, with benign twins"],
        ["MAPIS-Decomposed", "Exfiltration where no single message looks bad"],
        ["MAPIS-RealHarm", "InjecAgent direct harm and ASB, unseen attacker tools"],
        ["MAPIS-Adaptive", "Obfuscated, split, Unicode, paraphrased, delayed attacks"]]
table(s, 0.5, 1.15, 5.7, rows, [1.8, 3.9], size=11, row_h=0.62)
card(s, 6.4, 1.15, 3.1, 4.35)
tb(s, 6.5, 1.2, 2.9, 0.4, "Setup", size=15, bold=True, color=MAROON)
bullets(s, 6.5, 1.6, 2.9, 3.9, ["2,304 held-out test sessions (576 Adaptive)", "Test families, wordings and tools held out",
                                 "DeBERTa-v3-small, RTX 3050, 5 seeds", "Same events replayed through every system",
                                 "95 % Wilson intervals"], size=12, gap=5)
card(s, 0.5, 5.6, 9.0, 1.25, fill=RGBColor(0xF7, 0xE6, 0xEB))
tb(s, 0.65, 5.65, 8.7, 1.15, ["Benign twins for every attack: authorized (the user named the destination), resisted (planted text present, agent acts correctly), designated (the user named the file).",
                              "Without twins, a detector can score well just by flagging anything suspicious."], size=13, color=INK, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Explain twins with the example: the same email to the same address is an attack in one session and perfectly fine in the twin where the user asked for it.")

# ---------------------------------------------------------------- slide 8 results
s = slides[7]; clear(s); title(s, 7, "Results – Quantitative Performance", 8)
stat(s, 0.5, 1.1, 2.8, "98.0 %", "MAPIS recall (5-seed mean)")
stat(s, 3.6, 1.1, 2.8, "0.9 %", "False-positive rate")
stat(s, 6.7, 1.1, 2.8, "98.5 %", "Accuracy")
cd = CategoryChartData()
cd.categories = ["MAPIS", "Stateless DeBERTa", "Llama Guard 3", "ProtectAI", "Prompt Guard 2"]
cd.add_series("Recall (%)", (98.0, 94.1, 86.1, 53.3, 7.5))
cd.add_series("False-positive rate (%)", (0.9, 33.2, 90.3, 49.5, 0.1))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(2.65), Inches(9.0), Inches(3.55), cd)
ch = gf.chart; style_chart(ch)
ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
ch.value_axis.maximum_scale = 100; ch.value_axis.has_major_gridlines = True
ch.value_axis.major_gridlines.format.line.color.rgb = LINE
pl = ch.plots[0]; pl.gap_width = 60; pl.has_data_labels = True
pl.data_labels.font.size = Pt(10); pl.data_labels.number_format = '0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.series[0].format.fill.solid(); pl.series[0].format.fill.fore_color.rgb = MAROON
pl.series[1].format.fill.solid(); pl.series[1].format.fill.fore_color.rgb = RGBColor(0x8A, 0x94, 0x9C)
tb(s, 0.5, 6.3, 9.0, 0.6, "2,304 held-out sessions, same events for every system. MAPIS and the stateless model are means over 5 training seeds; the other systems do not depend on the seed.", size=11, color=GREY)
notes(s, "Read the chart as: maroon bars are attacks caught, grey bars are harmless sessions wrongly stopped. MAPIS is the only system that is high on the first and near zero on the second.")

# ---------------------------------------------------------------- slide 9 multihop analysis
s = slides[8]; clear(s); title(s, 8, "Analysis: Why Memory Matters", 9)
stat(s, 0.5, 1.1, 2.8, "100 %", "MAPIS multi-hop recall (FPR 3.0 %)")
stat(s, 3.6, 1.1, 2.8, "6.7 %", "Stateless recall at <= 5 % FPR", color=GREY)
stat(s, 6.7, 1.1, 2.8, "+93 pts", "Recall gain at matched FPR")
cd = CategoryChartData()
cd.categories = ["Multi-hop", "Adaptive (evasive)"]
cd.add_series("MAPIS", (100, 100))
cd.add_series("Stateless DeBERTa at <= 5 % FPR", (6.7, 8.7))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(2.65), Inches(4.6), Inches(3.4), cd)
ch = gf.chart; style_chart(ch, 10)
ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
ch.value_axis.maximum_scale = 100; ch.value_axis.major_gridlines.format.line.color.rgb = LINE
pl = ch.plots[0]; pl.gap_width = 70; pl.has_data_labels = True; pl.data_labels.number_format = '0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.font.size = Pt(10); pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.series[0].format.fill.solid(); pl.series[0].format.fill.fore_color.rgb = MAROON
pl.series[1].format.fill.solid(); pl.series[1].format.fill.fore_color.rgb = RGBColor(0x8A, 0x94, 0x9C)
bullets(s, 5.3, 2.7, 4.2, 4.2, [
    "Same words, different history:||  at the default threshold the stateless model reaches 92 % multi-hop recall but stops 55 % of harmless sessions, because it flags the twin where the user asked for the action.",
    "Evasive attacker:||  recall rose from 64.6 % to 100 % with normalisation, fragment matching and adversarial training, with 0 % false positives on all six techniques.",
    "Per mechanism:||  100 % on tool-output, cross-agent and goal-hijack; memory injection 99.2 % on all sets."], size=12, gap=7)
tb(s, 0.5, 6.2, 9.0, 0.6, "Thresholds for the stateless model were chosen on validation and applied to test; on test they gave 0.6 to 8.8 % FPR, so these recalls are generous to the baseline.", size=11, color=GREY)
notes(s, "This is the core result. The stateless model needs a very high false-alarm rate to catch these attacks. Held to 5 percent false alarms it catches under 10 percent. MAPIS catches all with 3.0 percent, and at most 5 percent on every checked seed with the validation-calibrated cut-off.")

# ---------------------------------------------------------------- slide 10 (duplicate) baselines + live agents
s = slides[9]; clear(s); title(s, 9, "Baselines and Live LLM Agents", 10)
tb(s, 0.5, 1.1, 4.4, 0.4, "Same 153 sessions", size=15, bold=True, color=MAROON)
rows = [["System", "Recall", "FPR"],
        ["MAPIS", "100 %", "0.0 %"],
        ["Stateless DeBERTa", "91.2 %", "32.9 %"],
        ["LLM judge (qwen2.5 7B)", "67.5 %", "23.3 %"],
        ["NeMo Guardrails (7B)", "48.7 %", "17.8 %"]]
table(s, 0.5, 1.55, 4.4, rows, [2.4, 1.0, 1.0], size=12, row_h=0.45)
bullets(s, 0.5, 3.95, 4.4, 2.9, [
    "The history-aware judge finds the multi-hop attacks but flags 80 % of the benign twins.",
    "NeMo misses most multi-hop and adaptive attacks.",
    "Neither separates an attack from the identical user-authorized action.",
    "Judge and NeMo used a small local 7B model; 20 sessions per dataset, so a 0 % FPR has a 5 % upper bound."], size=12, gap=5)
tb(s, 5.2, 1.1, 4.3, 0.4, "AgentDojo, real tool-calling agent", size=15, bold=True, color=MAROON)
cd = CategoryChartData()
cd.categories = ["No defence", "MAPIS", "Stateless"]
cd.add_series("Attack success rate (%)", (15.3, 0.0, 0.0))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(5.2), Inches(1.55), Inches(4.3), Inches(2.6), cd)
ch = gf.chart; style_chart(ch, 10); ch.has_legend = False
ch.value_axis.maximum_scale = 20; ch.value_axis.major_gridlines.format.line.color.rgb = LINE
pl = ch.plots[0]; pl.gap_width = 80; pl.has_data_labels = True; pl.data_labels.number_format = '0.0'; pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.series[0].format.fill.solid(); pl.series[0].format.fill.fore_color.rgb = MAROON
bullets(s, 5.2, 4.25, 4.3, 2.7, [
    "qwen2.5 7B agent, 4 suites, 39 benign and 144 attacked runs per defence.",
    "Attacks succeeded in 22 of 144 runs without defence; 0 of 144 with MAPIS (95 % upper bound 2.6 %).",
    "Benign utility 28.2 % without defence, 25.6 % with MAPIS.",
    "AgentDojo injections are explicit, so the stateless model also stops them; this shows integration and low cost."], size=12, gap=5)
notes(s, "Two separate checks. Left: all systems on the same 153 sessions, including the LLM judge and NeMo. Right: a live agent where MAPIS gates every tool call and tool output. Be clear that the live run shows MAPIS works inside a real agent pipeline with low cost; it does not by itself separate MAPIS from a stateless detector.")

# ---------------------------------------------------------------- slide 11 demo
s = slides[10]; clear(s); title(s, 10, "Prototype / Demonstration", 11)
s.shapes.add_picture(SHOT, Inches(0.5), Inches(1.15), height=Inches(4.6))
tb(s, 0.5, 5.8, 3.7, 0.9, "Operator console with the trained model: the decomposed attack is held at the email action.", size=10, color=GREY)
tb(s, 4.5, 1.1, 5.0, 0.4, "Live demo flow", size=15, bold=True, color=MAROON)
steps = ["Clean task: every hop passes, email sent", "Decomposed attack: no message has a command; the email to the planted address is held, trace file \u2192 memory \u2192 email",
         "Same verdict through AutoGen", "Session inspector: attack held, authorized twin passes", "Results tab: all comparisons"]
bullets(s, 4.5, 1.55, 5.0, 3.3, [f"{i+1}.||  {t}" for i, t in enumerate(steps)], size=13, gap=7)
card(s, 4.5, 5.0, 5.0, 1.6, fill=RGBColor(0xF7, 0xE6, 0xEB))
tb(s, 4.6, 5.05, 4.8, 1.5, ["Run it:", "python -m uvicorn backend.main:app --port 8000", "cd frontend ; npm start", "http://localhost:3000"], size=12, color=INK, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Run the five steps from the demo script. If the laptop is unavailable, use the screenshots and the in-browser explainer page.")

# ---------------------------------------------------------------- slide 12 limitations
s = slides[11]; clear(s); title(s, 11, "Limitations & Technical Challenges", 12)
rows = [["Limitation", "Detail"],
        ["Team-written test set", "20 hand-written attacks + 20 twins: MAPIS 35 % recall at 5 % FPR. Catches attacks carrying an email or URL; misses changed parameter values and short ids. Baselines do no better (they flag benign and attack equally)."],
        ["Attacks on the session record", "Test-only StateAttack: 58.9 % recall, 8.6 % FPR. Weak on items introduced by an agent (33 %) and items the agent must decode (29 %)."],
        ["Generated benchmarks", "MultiHop and Adaptive are template-generated, with held-out families, wordings and tools and real carrier text."],
        ["Seed variation", "Multi-hop FPR 3.0 +/- 3.0 % over 5 seeds; a cut-off chosen on validation keeps every checked seed <= 5 %."],
        ["Training overlap", "MAPIS was trained on AgentDojo-style injections; the live-agent run also uses them."],
        ["Small models in baselines", "Live agent, LLM judge and NeMo used a 7B local model."],
        ["Single-hop attacks", "On BIPIA there is no cross-hop evidence; stateless recall is within seed variance (MAPIS 95.8 %)."]]
table(s, 0.5, 1.15, 9.0, rows, [2.3, 6.7], size=11, row_h=0.66)
notes(s, "State these factually and once. The most important is the team-written set: MAPIS generalises to hand-written attacks that carry an email or URL, not to attacks that only change a parameter value.")

# ---------------------------------------------------------------- slide 13 remaining / completion
s = slides[12]; clear(s); title(s, 12, "Completion Status & Future Work", 13)
rows = [["Phase", "Status", "Outcome"],
        ["1  Literature and problem", "DONE", "Gap defined"],
        ["2  Testbed and FastAPI hooks", "DONE", "LangGraph and AutoGen via one tap"],
        ["3  Attack dataset and MAPIS-Bench", "DONE", "Six benchmark sets, twins"],
        ["4  Trust model and fine-tuning", "DONE", "5 seeds, adversarial training"],
        ["5  Tiered response and forensic logging", "DONE", "4 tiers, trace, quarantine review"],
        ["6  Dashboard and integration", "DONE", "Operator console"],
        ["7  Benchmarking against guardrails", "DONE", "5 baselines, live agents"],
        ["8  Report and demonstration", "DONE", "Thesis, report, live demo"]]
table(s, 0.5, 1.15, 9.0, rows, [3.9, 1.0, 4.1], size=12, row_h=0.43)
tb(s, 0.5, 5.15, 9.0, 0.4, "Future work", size=15, bold=True, color=MAROON)
bullets(s, 0.5, 5.55, 9.0, 1.4, ["Provenance for every argument value of an action, not only emails and URLs.", "Tap agent-internal reads; evaluate on real agent traffic.",
                                 "Larger live agents and stronger LLM judges; production hardening."], size=13, gap=4)
notes(s, "All eight phases from the timeline in the zeroth review are complete. Future work lists what would strengthen the evidence.")

# ---------------------------------------------------------------- slide 14 contribution
s = slides[13]; clear(s); title(s, 13, "Project Contribution & Achievement", 14)
rows = [["Target (from the abstract)", "Result", "Met"],
        ["Accuracy >= 90 %", "98.5 % (5 seeds)", "Yes"],
        ["False-positive rate <= 5 %", "0.9 +/- 0.8 % overall; multi-hop 3.0 +/- 3.0 % (<= 5 % calibrated)", "Yes"],
        ["Latency < 200 ms per message", "63 ms single, 51 ms batched (RTX 3050)", "Yes"],
        ["Multi-hop recall gain >= 20 points", "+93 points at matched FPR (+13.5 at default threshold)", "Yes"]]
table(s, 0.5, 1.15, 9.0, rows, [3.3, 4.9, 0.8], size=13, row_h=0.6)
tb(s, 0.5, 4.3, 9.0, 0.4, "Contributions", size=15, bold=True, color=MAROON)
bullets(s, 0.5, 4.7, 9.0, 2.2, [
    "A stateful, provenance-aware monitor at a framework-neutral tap, running in 63 ms per event.",
    "MAPIS-Bench: multi-hop fragment attacks with matched benign twins, and an evasive-attacker set.",
    "A fair matched-false-positive comparison against stateless and LLM-based detectors.",
    "Evaluation inside a live LLM-agent pipeline: attack success 15.3 % to 0 %."], size=14, gap=6)
notes(s, "Every target from the abstract is met. The multi-hop gain is +93 points at a matched false-positive budget and +13.5 points at the default threshold; both are stated.")

# ---------------------------------------------------------------- slide 15 team
s = slides[14]; clear(s); title(s, 14, "Team Contribution & Responsibility", 15)
people = [("Vishnu Vardhan", "Testbed & Orchestration Lead", "LangGraph and AutoGen testbed, agent orchestration, FastAPI tap and runtime integration."),
          ("Nithya Sai", "Attack Dataset & Red-Team Lead", "MAPIS-Bench construction, attack taxonomy, multi-hop and adaptive attack scenarios, labelling."),
          ("Sreekar Reddy", "Detection Model Lead", "Session-context design, trust-scoring classifier, training, features, threshold calibration."),
          ("Beena Reddy", "Response, Dashboard & Evaluation Lead", "Tiered response, forensic logging, dashboard, benchmark harness and evaluation.")]
for i, (n, r, d) in enumerate(people):
    x = 0.5 + (i % 2) * 4.6; y = 1.2 + (i // 2) * 2.35
    card(s, x, y, 4.4, 2.15)
    tb(s, x + 0.1, y + 0.1, 4.2, 0.4, n, size=16, bold=True, color=MAROON)
    tb(s, x + 0.1, y + 0.5, 4.2, 0.35, r, size=12, bold=True, color=INK)
    tb(s, x + 0.1, y + 0.9, 4.2, 1.2, d, size=12, color=GREY)
tb(s, 0.5, 5.95, 9.0, 0.8, "Shared: weekly integration testing, code review, experiment tracking, documentation and report writing.", size=13, color=INK)
notes(s, "Roles as stated in the zeroth and first review.")

# ---------------------------------------------------------------- slide 16 references
s = slides[15]; clear(s); title(s, 15, "References", 16)
refs = ["[1] Greshake et al., “Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,” AISec '23, 2023.",
        "[2] Liu et al., “Prompt injection attack against LLM-integrated applications,” arXiv:2306.05499, 2023.",
        "[3] Zhan et al., “InjecAgent: Benchmarking indirect prompt injections in tool-integrated LLM agents,” ACL Findings, 2024.",
        "[4] Debenedetti et al., “AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents,” NeurIPS 2024.",
        "[5] Jia et al., “The Task Shield: Enforcing task alignment to defend against indirect prompt injection in LLM agents,” arXiv:2412.16682, 2024.",
        "[6] Wang et al., “AgentWatcher: A rule-based prompt injection monitor,” arXiv:2604.01194, 2026.",
        "[7] Li and Zhao, “The autonomy tax: Defense training breaks LLM agents,” arXiv:2603.19423, 2026.",
        "[8] Geng et al., “Prompt injection attacks on large language models: A survey,” Computers, Materials & Continua, 2026.",
        "[9] Lee and Tiwari, “Prompt Infection: LLM-to-LLM prompt injection within multi-agent systems,” 2024.",
        "[10] G-Safeguard: topology-guided security lens for multi-agent systems, ACL 2025; Meta, LlamaFirewall (AlignmentCheck), 2025."]
bullets(s, 0.5, 1.1, 9.0, 5.8, ["•  " + r if False else r for r in refs], size=11, gap=5)
notes(s, "References 1 to 8 are from the zeroth and first review. References 9 and 10 are the related work added during the project.")

prs.save(OUT)
print("saved", OUT)
