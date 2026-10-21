"""Final-review deck, 21 slides, on the team's First Review template (Amrita logo, "NN | Title" headings).

    python docs/presentation/build_final_ppt_21.py <first-review template .pptx (17 slides)> docs/presentation/MAPIS_Final_Review.pptx
"""
import sys

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
REPO = "/home/user/Mapis"
FIG = f"{REPO}/slides_latex/figures"
MAROON = RGBColor(0xA4, 0x12, 0x3F)
PINK = RGBColor(0xF7, 0xE6, 0xEB)
INK = RGBColor(0x1F, 0x29, 0x33)
GREY = RGBColor(0x5B, 0x67, 0x70)
BAR_GREY = RGBColor(0x8A, 0x94, 0x9C)
LIGHT = RGBColor(0xF3, 0xF4, 0xF6)
LINE = RGBColor(0xD0, 0xD5, 0xDA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT, MONO = "Calibri", "Consolas"
L, CW = 0.55, 9.57          # left margin and content width (slide is 10.67 x 8.0 in)
TOTAL = 21

prs = Presentation(SRC)
blank = prs.slides[1].slide_layout
for _ in range(4):                                   # 17 template slides -> 21
    prs.slides.add_slide(blank)
ids = prs.slides._sldIdLst
thank = list(ids)[16]                                # keep "Thank You" last
ids.remove(thank)
ids.append(thank)
S = list(prs.slides)


def clear(slide, keep=()):
    for sh in list(slide.shapes):
        if sh.name not in keep:
            sh._element.getparent().remove(sh._element)


def tb(slide, x, y, w, h, text="", size=16, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT, italic=False):
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, ln in enumerate(text if isinstance(text, list) else [text]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(size), bold, italic, font
        r.font.color.rgb = color
    return s


def bullets(slide, x, y, w, h, items, size=15, gap=6, color=INK):
    """items: 'Head:||  rest' renders a maroon bold lead-in, otherwise a bullet."""
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        head, _, rest = it.partition("||")
        runs = [(head, True, MAROON), (rest, False, color)] if rest else [("•  " + it, False, color)]
        for text, bold, col in runs:
            r = p.add_run()
            r.text = text
            r.font.size, r.font.bold, r.font.name = Pt(size), bold, FONT
            r.font.color.rgb = col
    return s


def footer(slide, no):
    tb(slide, L, 7.55, CW, 0.3, f"FINAL REVIEW • B.TECH PROJECT • MAPIS • Team A1 • Slide {no} of {TOTAL}", size=9, color=GREY)


def title(slide, n, text, no):
    tb(slide, L, 0.32, CW, 0.7, f"{n:02d} | {text}", size=26, bold=True)
    footer(slide, no)


def card(slide, x, y, w, h, fill=LIGHT):
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.adjustments[0] = 0.06
    r.fill.solid()
    r.fill.fore_color.rgb = fill
    r.line.fill.background()
    r.shadow.inherit = False
    return r


def stat(slide, x, y, w, big, label, color=MAROON):
    card(slide, x, y, w, 1.35)
    tb(slide, x, y + 0.1, w, 0.75, big, size=34, bold=True, color=color, align=PP_ALIGN.CENTER)
    tb(slide, x + 0.1, y + 0.82, w - 0.2, 0.5, label, size=12, color=GREY, align=PP_ALIGN.CENTER)


def table(slide, x, y, w, rows, col_w, size=12, row_h=0.4, bold_rows=(), bold_first_col=False):
    t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows))).table
    for j, cw in enumerate(col_w):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        t.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.06)
            c.margin_top = c.margin_bottom = Inches(0.02)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = c.text_frame.paragraphs[0]
            c.text_frame.word_wrap = True
            r = p.add_run()
            r.text = str(val)
            r.font.size, r.font.name = Pt(size), FONT
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = MAROON
                r.font.bold, r.font.color.rgb = True, WHITE
            else:
                c.fill.fore_color.rgb = LIGHT if i % 2 == 0 else WHITE
                r.font.color.rgb = INK
                r.font.bold = i in bold_rows or (bold_first_col and j == 0)
    return t


def column_chart(slide, x, y, w, h, cats, series, maximum=100, legend=True, size=11, gap=60):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    ch = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.font.size, ch.font.name = Pt(size), FONT
    ch.font.color.rgb = INK
    ch.has_legend = legend
    if legend:
        ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.BOTTOM, False
    ch.value_axis.maximum_scale = maximum
    ch.value_axis.major_gridlines.format.line.color.rgb = LINE
    pl = ch.plots[0]
    pl.gap_width, pl.has_data_labels = gap, True
    pl.data_labels.font.size = Pt(size - 1)
    pl.data_labels.number_format, pl.data_labels.number_format_is_linked = "0.0", False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    for k, colr in enumerate((MAROON, BAR_GREY)[:len(series)]):
        pl.series[k].format.fill.solid()
        pl.series[k].format.fill.fore_color.rgb = colr
    return ch


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ======================================================================= 1 title
s = S[0]
clear(s, keep={"Group 8"})                           # keep only the Amrita logo group
tb(s, L, 1.75, CW, 0.5, "FINAL REVIEW – B.TECH PROJECT", size=20, bold=True, align=PP_ALIGN.CENTER)
tb(s, L, 2.3, CW, 1.3, "MAPIS — Multi-Agent Prompt Injection Shield", size=36, bold=True, color=MAROON, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
tb(s, L, 3.6, CW, 0.6, "A stateful trust-scoring monitor for indirect prompt injection in multi-agent LLM pipelines", size=16, color=GREY, align=PP_ALIGN.CENTER)
tb(s, L, 4.35, CW, 0.4, "Team Number: A1", size=16, bold=True, align=PP_ALIGN.CENTER)
tb(s, L, 4.8, CW, 1.4, ["Dodla Nithya Sai – CB.SC.U4AIE23021", "Vishnu Vardhan – CB.SC.U4AIE23043",
                        "Sreekar Reddy – CB.SC.U4AIE23049", "Beena Reddy – CB.SC.U4AIE23065"], size=15, align=PP_ALIGN.CENTER)
tb(s, L, 6.2, CW, 0.65, ["Guide: K. Sripriyan, Assistant Professor", "Co-Guide: Anjana Sankar, Assistant Professor"], size=14, bold=True, align=PP_ALIGN.CENTER)
tb(s, L, 6.95, CW, 0.4, "Amrita School of Artificial Intelligence, Coimbatore  •  22 October 2026", size=13, color=GREY, align=PP_ALIGN.CENTER)
footer(s, 1)
notes(s, "MAPIS is a monitor that sits between the agents of a multi-agent AI system, remembers each session, and stops attacks that are hidden in documents and spread over several steps.")

# ======================================================================= 2 progress
s = S[1]; clear(s); title(s, 1, "Progress Since First Review", 2)
table(s, L, 1.2, CW, [
    ["Area", "At First Review", "At Final Review"],
    ["Detector", "DeBERTa-v3-small on chunked history; gained only 2.3 points from session state", "Session signals written into the classifier input; +96 points over the stateless model on multi-hop attacks at matched FPR"],
    ["Runtime", "4-tier shield, session store, provenance, trace on LangGraph", "Same on LangGraph and AutoGen, plus escalation, evasion defences, tampering checks and a calibrated hold cut-off"],
    ["Data", "MAPIS-Bench v1 (1,693), BIPIA (1,800), Decomposed", "+ MultiHop, RealHarm, Adaptive; StateAttack and a team-written test set"],
    ["Baselines", "Llama Guard / NeMo comparison planned", "Llama Guard, Prompt Guard 2, ProtectAI, NeMo Guardrails, LLM judge on identical sessions"],
    ["Evaluation", "One training run, held-out BIPIA", "5 training seeds, 2,304-session test, matched-FPR comparison, live LLM agents (AgentDojo)"],
    ["Interface", "Dashboard integration in progress, demo pending", "Operator console: live monitor, session inspector, results"],
    ["Tests", "26 passing", "33 passing"]], [1.35, 3.4, 4.82], size=12, row_h=0.68, bold_first_col=True)
tb(s, L, 6.85, CW, 0.5, "All four project targets are measured and met (slide 18).", size=16, bold=True, color=MAROON)
notes(s, "At the First Review we had a trained classifier and a prototype shield. Since then the classifier really uses the session, we added AutoGen, five more test sets, five baselines, five training seeds and a live LLM-agent test.")

# ======================================================================= 3 motivation
s = S[2]; clear(s); title(s, 2, "Motivation & Problem Statement", 3)
bullets(s, L, 1.15, CW, 2.9, [
    "Problem:||  Teams of AI agents read web pages, files, tool outputs and memory that nobody checked. An attacker hides text there, and an agent acts on it (indirect prompt injection, OWASP LLM01).",
    "Hard case:||  A file says “Finance contact: audit-desk@fin-review.net”. One agent saves it to memory, another reads it back, the email agent sends the report there. No message contains a command.",
    "Gap:||  A guard that checks one message at a time cannot tell this email from the same email the user asked for. The evidence is in the session history.",
    "Scope:||  In: indirect injection, multi-agent testbeds, stateful detection, tiered response, forensic trace, benchmarking. Out: direct jailbreaks, training-time defences, images/audio, attacks on the classifier itself."], size=14, gap=7)
table(s, L, 4.25, CW, [
    ["Objective", "Target", "Status"],
    ["O1  Testbed with FastAPI tap (LangGraph + AutoGen)", "Every message, tool call, memory access", "Done"],
    ["O2  Labelled multi-hop benchmark", "≥ 1,000 sessions, 5 attack classes", "Done: ≈ 9,900 sessions"],
    ["O3  Stateful trust-scoring classifier", "≥ 90 % accuracy, ≤ 5 % FPR", "98.5 % / 0.9 %"],
    ["O4  Tiered response + trace, latency", "< 200 ms per message", "63 ms"],
    ["O5  Benchmark against existing guardrails", "≥ 20 pts multi-hop recall gain", "+96 pts at matched FPR"]], [4.3, 3.1, 2.17], size=12, row_h=0.5)
notes(s, "Tell the hard case as a story: no single message is bad, only the history shows the address came from a file. Then the five objectives from the abstract with what we measured.")

# ======================================================================= 4 literature
s = S[3]; clear(s); title(s, 3, "Literature Review & Research Gap", 4)
table(s, L, 1.2, CW, [
    ["Work", "What it does", "Limit that MAPIS addresses"],
    ["Greshake et al. 2023", "First showed indirect injection through retrieved content", "Attack discovery, no detector"],
    ["InjecAgent 2024, AgentDojo 2024", "Benchmarks for tool-using agents", "Explicit injection text; no fragment attacks with benign twins"],
    ["Task Shield 2024", "Checks each action against the user's task", "Per action; relies on an LLM's judgement"],
    ["AgentWatcher 2026", "Attributes actions to their context, rule-based monitor LLM", "Adds LLM inference to every check"],
    ["LlamaFirewall AlignmentCheck 2025", "An LLM audits the whole trajectory", "Heavy and after the fact; our 7B judge of this kind flagged 80 % of benign multi-hop twins"],
    ["Llama Guard, Prompt Guard 2, ProtectAI", "Single-message safety / injection classifiers", "No session memory"],
    ["Prompt Infection 2024, G-Safeguard 2025", "Injection spreading across agents", "Study spreading or use graph models; no light inline stateful tap"]], [2.6, 3.4, 3.57], size=12, row_h=0.58)
card(s, L, 6.05, CW, 1.15, fill=PINK)
tb(s, L + 0.15, 6.1, CW - 0.3, 1.05, ["Research gap: a lightweight real-time monitor that carries session state across hops, tested on fragment attacks with matched benign twins.",
                                      "MAPIS contribution: this combination, at one tap that works for both AutoGen and LangGraph."], size=14, bold=True, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "MAPIS is not the first work on multi-agent injection. The new part is the combination: a small, fast classifier that reads the session, at a framework-neutral tap, tested with matched benign twins.")

# ======================================================================= 5 architecture
s = S[4]; clear(s); title(s, 4, "System Architecture & Methodology", 5)
boxes = [("Agents", ["planner, web, file,", "memory, code/email", "LangGraph or AutoGen"]),
         ("MAPIS tap", ["FastAPI /inspect on every", "message, tool call,", "memory read / write"]),
         ("Session record", ["Redis or in-memory: user goal,", "where each item came from,", "authority claims, baselines"]),
         ("Trust score", ["DeBERTa-v3-small + signals", "+ tampering checks", "0 = malicious, 1 = safe"])]
bw, gap = 2.15, 0.323
for i, (h, t) in enumerate(boxes):
    x = L + i * (bw + gap)
    card(s, x, 1.25, bw, 1.8, fill=LIGHT if i == 0 else PINK)
    tb(s, x, 1.32, bw, 0.4, h, size=15, bold=True, color=MAROON, align=PP_ALIGN.CENTER)
    tb(s, x + 0.05, 1.78, bw - 0.1, 1.2, t, size=11, align=PP_ALIGN.CENTER)
    if i < 3:
        tb(s, x + bw - 0.03, 1.9, gap + 0.06, 0.5, "→", size=22, bold=True, color=MAROON, align=PP_ALIGN.CENTER)
tb(s, L, 3.25, CW, 0.35, "Tiered response", size=15, bold=True)
tiers = [("PASS", "≥ 0.75  deliver", RGBColor(0x2B, 0x7A, 0x4B)), ("FLAG", "0.50–0.75  deliver + alert", RGBColor(0xB7, 0x91, 0x0B)),
         ("QUARANTINE", "0.25–0.50  hold for operator", RGBColor(0xC2, 0x5E, 0x0E)), ("BLOCK", "< 0.25  drop + suspend", RGBColor(0xB3, 0x26, 0x1E))]
tw = (CW - 3 * 0.17) / 4
for i, (n, r, col) in enumerate(tiers):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(L + i * (tw + 0.17)), Inches(3.65), Inches(tw), Inches(0.8))
    b.fill.solid(); b.fill.fore_color.rgb = col; b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for k, (txt, sz, bd) in enumerate(((n, 14, True), (r, 11, False))):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        rr = p.add_run(); rr.text = txt; rr.font.size = Pt(sz); rr.font.bold = bd; rr.font.name = FONT; rr.font.color.rgb = WHITE
bullets(s, L, 4.7, CW, 2.7, [
    "Four signals:||  instruction in data, drift from the user goal, cross-hop provenance and escalation, behaviour anomaly.",
    "Tampering checks:||  an action argument the user never gave — a changed value, an extra privilege flag, a destination relayed by another agent.",
    "Same code in training and live:||  session.py builds the classifier text for both; a unit test checks they are identical.",
    "Response:||  QUARANTINE waits for operator Release / Reject; BLOCK drops the message and suspends the channel; every alert has a trace origin → relay → action.",
    "Stack:||  Python, PyTorch, HuggingFace, FastAPI, Redis, SQLite, React, LangGraph, AutoGen."], size=13, gap=4)
notes(s, "Follow one message from left to right. The session record is what lets MAPIS tell a planted address from one the user named.")

# ======================================================================= 6 how a message is scored (new)
s = S[5]; clear(s); title(s, 5, "How One Message Is Scored", 6)
card(s, L, 1.2, 4.75, 4.15)
tb(s, L + 0.15, 1.25, 4.5, 0.4, "What the classifier reads", size=15, bold=True, color=MAROON)
tb(s, L + 0.15, 1.7, 4.5, 2.75, ["MAPIS CURRENT EVENT",
                                  "  tool=send_email",
                                  "  to=audit-desk@fin-review.net",
                                  "MAPIS SESSION SIGNALS",
                                  "  claims=1  reuse=audit-desk@…<-hop2 file",
                                  "  user_items=lena@corp.example",
                                  "MAPIS SESSION HISTORY",
                                  "  goal: email the summary to lena@corp…",
                                  "  hop2 file: “Finance contact: audit-desk@…”"], size=11, font=MONO)
tb(s, L + 0.15, 4.45, 4.5, 0.85, "Current event first, so a long text only loses old history. Long events: 900-character chunks, trust = lowest chunk.", size=11, color=GREY)
table(s, 5.5, 1.2, 4.62, [
    ["Signal", "Weight", "Example"],
    ["Instruction in data", "0.5", "“ignore previous…” inside a page"],
    ["Drift from goal", "0.15", "goal: list contracts → grant admin"],
    ["Provenance / escalation / tampering", "0.8", "planted address used; WL-5508 instead of PS-7731"],
    ["Behaviour anomaly", "0.15", "file agent suddenly sends email"]], [1.6, 0.85, 2.17], size=11, row_h=0.6)
card(s, 5.5, 4.35, 4.62, 1.0, fill=PINK)
tb(s, 5.6, 4.38, 4.42, 0.95, ["survive = model × Π(1 − w × r)", "risk = (1 − survive) × (1 + sensitivity)", "trust = 1 − risk  →  tier"], size=11, bold=True, font=MONO, anchor=MSO_ANCHOR.MIDDLE)
table(s, L, 5.6, CW, [
    ["Worked example", "Inputs", "Trust", "Tier"],
    ["Address from a file, model unsure", "model 1.0, provenance 0.45", "0.64", "FLAG"],
    ["Same message, session already suspicious", "+ sensitivity 0.6", "0.42", "QUARANTINE"],
    ["Planted address used, model suspicious", "model 0.5, provenance 0.9", "0.14", "BLOCK"]], [3.6, 3.17, 1.2, 1.6], size=12, row_h=0.4)
notes(s, "The model gives its opinion, the rules add risk, and a noisy-OR combines them: one strong warning is enough, weak ones add up. A session that has already raised alarms is judged up to 1.6 times more strictly.")

# ======================================================================= 7 implementation
s = S[6]; clear(s); title(s, 6, "Implementation Status", 7)
table(s, L, 1.2, CW, [
    ["Component", "Status", "Where in the code"],
    ["Testbed: LangGraph and AutoGen (5 agents, 3 scenarios)", "DONE", "backend/agents/graph.py, autogen_testbed.py, testbed.py"],
    ["FastAPI tap, Redis session store, SQLite forensic log", "DONE", "backend/api/, core/store.py, db.py"],
    ["Stateful shield: session record + 4 signals", "DONE", "core/shield.py, session.py, features.py"],
    ["Evasion defences and tampering checks", "DONE", "features.py: canonical(), fragments, tamper_risk"],
    ["Classifier and training pipeline", "DONE", "backend/ml/, 5 training seeds"],
    ["Four tiers, channel suspension, quarantine review", "DONE", "/inspect API, operator console"],
    ["Forensic trace and operator dashboard", "DONE", "frontend/ (live monitor, inspector, results)"],
    ["Benchmark sets and generators", "DONE", "scripts/generate_*.py, data/mapis_bench/"],
    ["Baselines: 5 systems on identical sessions", "DONE", "backend/baselines.py, scripts/benchmark.py"],
    ["Live LLM agent evaluation (AgentDojo)", "DONE", "scripts/live_agentdojo.py"],
    ["Automated tests", "33 PASS", "tests/ (shield, API, train/serve parity, AutoGen tap, tampering)"]], [4.3, 1.0, 4.27], size=12, row_h=0.5)
notes(s, "Everything planned in the abstract is built and in the repository. The tests include a train/serve parity test.")

# ======================================================================= 8 datasets (new)
s = S[7]; clear(s); title(s, 7, "Datasets & Experimental Setup", 8)
table(s, L, 1.2, 6.25, [
    ["Set (sessions)", "Source", "Train", "Val", "Test"],
    ["v1 (1,693)", "AgentDojo + InjecAgent, public", "1,169", "242", "282"],
    ["BIPIA (1,800)", "Public benchmark", "872", "128", "800"],
    ["MultiHop (2,118)", "Generated, real carrier text", "1,512", "372", "234"],
    ["RealHarm (2,330)", "InjecAgent-DH + ASB, public", "1,733", "233", "364"],
    ["Adaptive (1,692)", "Generated, evasive attacker", "900", "216", "576"],
    ["Decomposed (288)", "Generated, test only", "–", "–", "48"],
    ["Total", "", "6,186", "1,191", "2,304"]], [1.65, 2.3, 0.8, 0.7, 0.8], size=12, row_h=0.47, bold_rows=(7,))
card(s, 7.0, 1.2, 3.12, 3.76)
tb(s, 7.1, 1.25, 2.9, 0.4, "Setup", size=15, bold=True, color=MAROON)
bullets(s, 7.1, 1.65, 2.95, 3.3, ["Test: 1,285 attacks, 1,019 harmless", "MultiHop, Adaptive, RealHarm: split by family, wording and tool — their test uses tools and phrasings never seen in training",
                                   "Test only: StateAttack (168), team-written set (40)", "Every system sees the same events", "5 seeds; 95 % Wilson intervals"], size=12, gap=4)
card(s, L, 5.15, CW, 1.6, fill=PINK)
bullets(s, L + 0.15, 5.22, CW - 0.3, 2.1, [
    "Benign twins for every attack:||  authorized (the user named the destination), resisted (planted text present, the agent acts correctly), designated (the user named the file). Without twins a detector can score well by flagging anything suspicious.",
    "Reported both ways:||  5 attack classes (exfiltration, financial, code/tool, instruction override, physical safety) and 5 mechanisms (document poisoning, memory injection, tool output, cross-agent, goal hijack)."], size=13, gap=6)
notes(s, "Public benchmarks are split into a trained part and a held-out part; we always report the held-out part. Decomposed, StateAttack and the team-written set were never trained on.")

# ======================================================================= 9 model and training (new)
s = S[8]; clear(s); title(s, 8, "Model & Training", 9)
table(s, L, 1.2, 4.6, [
    ["Setting", "Value"],
    ["Model", "DeBERTa-v3-small (6 layers, hidden 768, 44 M backbone)"],
    ["Method", "Fine-tuned from the pretrained model; 2-class head"],
    ["Loss", "Class-weighted cross-entropy"],
    ["Optimiser", "AdamW, lr 2e-5, weight decay 0.01, warm-up 10 %"],
    ["Batch / epochs", "4 × 4 accumulation / 2 (best val F1 at FPR ≤ 5 %)"],
    ["Precision", "fp16 with fp32 master weights"],
    ["Calibration", "Temperature fitted on validation"],
    ["Seeds", "42, 2, 3, 4, 5"],
    ["Hardware / time", "RTX 3050 laptop; 4.3 h stateful, 1.3 h stateless"]], [1.35, 3.25], size=11, row_h=0.47, bold_first_col=True)
s.shapes.add_picture(f"{FIG}/train_curves.png", Inches(5.35), Inches(1.25), width=Inches(4.77))
tb(s, 5.35, 3.1, 4.77, 0.6, "Training loss and validation F1 (seed 42, 9,064 validation events). MAPIS reaches F1 0.991; the stateless model levels off at 0.861.", size=11, color=GREY)
card(s, 5.35, 3.85, 4.77, 1.85, fill=PINK)
bullets(s, 5.45, 3.92, 4.6, 1.75, [
    "Two models, one difference:||  MAPIS reads event + signals + history; the stateless baseline reads the event only (--no-context).",
    "Same:||  data, split, seeds and settings — so any difference comes from session memory."], size=12, gap=5)
notes(s, "We did not train from scratch: we fine-tuned Microsoft's pretrained DeBERTa-v3-small on our labelled events, five times. The stateless twin model is the fair same-model-without-memory baseline.")

# ======================================================================= 10 results
s = S[9]; clear(s); title(s, 9, "Results – Quantitative Performance", 10)
sw = (CW - 2 * 0.36) / 3
for k, (big, lab) in enumerate((("98.0 %", "MAPIS recall (5-seed mean ± 0.6)"), ("0.9 %", "False-positive rate (± 0.8)"), ("98.5 %", "Accuracy  •  63 ms per message"))):
    stat(s, L + k * (sw + 0.36), 1.15, sw, big, lab)
column_chart(s, L, 2.7, CW, 3.95, ["MAPIS", "Stateless DeBERTa", "Llama Guard 3-1B", "ProtectAI v2", "Prompt Guard 2"],
             [("Recall (%)", (98.0, 94.1, 86.1, 53.3, 7.5)), ("False-positive rate (%)", (0.9, 33.2, 90.3, 49.5, 0.1))])
tb(s, L, 6.75, CW, 0.65, "2,304 held-out sessions, same events for every system. MAPIS and the stateless model are means over 5 training seeds. Llama Guard flags almost everything, Prompt Guard 2 almost nothing; only MAPIS is high on recall and near zero on false alarms.", size=11, color=GREY)
notes(s, "Maroon = attacks caught, grey = harmless sessions wrongly stopped. MAPIS is the only system high on the first and near zero on the second.")

# ======================================================================= 11 results by set (new)
s = S[10]; clear(s); title(s, 10, "Results by Benchmark Set", 11)
table(s, L, 1.2, 4.9, [
    ["Set (5-seed mean)", "Recall", "FPR"],
    ["MultiHop", "100 %", "3.0 ± 3.0 %"],
    ["Adaptive (6 techniques)", "100 %", "0.4 %"],
    ["RealHarm: InjecAgent-DH", "99.4 %", "0.0 %"],
    ["RealHarm: ASB", "100 %", "0.0 %"],
    ["Decomposed", "100 %", "0.0 %"],
    ["MAPIS-Bench v1", "100 %", "0.0 %"],
    ["BIPIA (held-out part)", "95.8 %", "1.4 %"]], [2.6, 1.0, 1.3], size=12, row_h=0.47, bold_first_col=True)
s.shapes.add_picture(f"{FIG}/confusion.png", Inches(5.65), Inches(1.25), width=Inches(4.47))
tb(s, 5.65, 3.3, 4.47, 0.5, "Confusion matrices, seed 42, all 2,304 sessions: stateless baseline vs MAPIS.", size=11, color=GREY)
bullets(s, L, 5.1, CW, 2.3, [
    "Calibrated cut-off:||  a hold threshold picked on validation brings multi-hop false alarms from 3.0 % to 0.6 % — every seed ≤ 1.8 %, recall still 100 %.",
    "By mechanism (seed 42):||  100 % for tool output, cross-agent, goal hijack and document poisoning; memory injection 99.2 %.",
    "Weakest class:||  instruction override (92.3 % in seed 42) — mostly harmless-looking single-hop BIPIA injections."], size=13, gap=6)
notes(s, "MAPIS is near 100 percent on every set except BIPIA, where the attack is in a single message and there is no history to use.")

# ======================================================================= 12 why memory matters
s = S[11]; clear(s); title(s, 11, "Analysis: Why Memory Matters", 12)
for k, (big, lab, col) in enumerate((("100 %", "MAPIS multi-hop recall (FPR 3.0 %)", MAROON), ("4.3 %", "Stateless recall at ≤ 5 % FPR", GREY), ("+96 pts", "Recall gain at matched FPR", MAROON))):
    stat(s, L + k * (sw + 0.36), 1.15, sw, big, lab, color=col)
column_chart(s, L, 2.7, 4.9, 3.7, ["Multi-hop", "Adaptive (evasive)"], [("MAPIS", (100, 100)), ("Stateless at ≤ 5 % FPR", (4.3, 6.1))], size=10, gap=70)
bullets(s, 5.65, 2.75, 4.47, 4.0, [
    "Same words, different history:||  at the default threshold the stateless model gets 86.5 % multi-hop recall but stops 51.1 % of harmless sessions — it flags the twin where the user asked for the action.",
    "Fair comparison:||  held to the same 5 % false-alarm budget it catches 4.3 % (multi-hop) and 6.1 % (adaptive); MAPIS catches 100 %.",
    "Evasive attacker:||  64.6 % → 100 % recall at 0.4 % FPR, with normalisation, fragment matching and adversarial training."], size=13, gap=7)
tb(s, L, 6.55, CW, 0.8, "Stateless thresholds were picked on validation and applied to test (5 seeds); on test they gave up to 8.8 % FPR, so these recalls are generous to the baseline. Explicit single-message attacks (RealHarm, AgentDojo) are caught by both — the gap there is at most 11 points.", size=11, color=GREY)
notes(s, "This is the core result: without memory a detector either misses the spread-out attacks or blocks the user's own requests.")

# ======================================================================= 13 harder tests (new)
s = S[12]; clear(s); title(s, 12, "Harder Tests: A Gap Found and Fixed", 13)
tb(s, L, 1.12, 4.85, 0.4, "Team-written set (seed 42)", size=14, bold=True, color=MAROON)
table(s, L, 1.55, 4.85, [
    ["System", "Recall", "FPR", "Acc."],
    ["MAPIS + tampering checks", "95.0", "5.0", "95.0"],
    ["MAPIS before the checks", "35.0", "5.0", "65.0"],
    ["Stateless DeBERTa", "40.0", "40.0", "50.0"],
    ["ProtectAI v2", "50.0", "50.0", "50.0"],
    ["Llama Guard 3-1B", "100", "100", "50.0"]], [2.35, 0.8, 0.8, 0.9], size=12, row_h=0.45, bold_rows=(1,))
tb(s, 5.65, 1.12, 4.47, 0.4, "Attacks on the session record (5 seeds)", size=14, bold=True, color=MAROON)
table(s, 5.65, 1.55, 4.47, [
    ["StateAttack technique", "Before", "After"],
    ["Evidence buried under filler", "76.7", "90.0"],
    ["Claim split over 3 documents", "78.3", "91.7"],
    ["Item laundered via memory", "63.3", "86.7"],
    ["Item introduced by an agent", "25.0", "90.0"],
    ["Item the agent must decode", "25.0", "25.0"],
    ["All (FPR 10.2 % both)", "55.7", "80.4"]], [2.67, 0.9, 0.9], size=12, row_h=0.42, bold_rows=(6,))
card(s, L, 4.75, CW, 2.2, fill=PINK)
bullets(s, L + 0.15, 4.85, CW - 0.3, 2.5, [
    "What the first run missed:||  changed values (wallet WL-5508 instead of PS-7731, alarm delay 360 instead of 10 min), extra privilege flags (bypass_checks=true), destinations relayed by another agent.",
    "Fix — three tampering checks on action arguments, no retraining:||  team-written set 35–45 % → 95 % in all 5 seeds; no new false positive on any of 2,512 test sessions.",
    "Honest note:||  the checks were designed after reading these misses, so a fresh hand-written set must confirm the 95 %. Decoded items stay the weak spot."], size=14, gap=8)
notes(s, "These sets were built to break MAPIS. The low first score showed exactly what was missing; plain rules fixed most of it without retraining the model.")

# ======================================================================= 14 baselines + live agents
s = S[13]; clear(s); title(s, 13, "Baselines & Live LLM Agents", 14)
tb(s, L, 1.12, 4.6, 0.4, "LLM detectors, same 153 sessions", size=14, bold=True, color=MAROON)
table(s, L, 1.55, 4.6, [
    ["System", "Recall", "FPR"],
    ["MAPIS", "100 %", "0.0 %"],
    ["Stateless DeBERTa", "91.2 %", "32.9 %"],
    ["LLM judge (qwen2.5 7B, full transcript)", "67.5 %", "23.3 %"],
    ["NeMo Guardrails (qwen2.5 7B)", "48.7 %", "17.8 %"]], [2.6, 1.0, 1.0], size=12, row_h=0.45, bold_rows=(1,))
bullets(s, L, 3.95, 4.6, 3.4, [
    "The judge finds the multi-hop attacks but flags 80 % of the benign twins.",
    "NeMo misses most multi-hop and adaptive attacks.",
    "Neither can separate an attack from the same action the user asked for.",
    "Both used a small local 7B model; 20 sessions per set, so 0 % FPR has a 5 % upper bound."], size=12, gap=5)
tb(s, 5.5, 1.12, 4.62, 0.4, "AgentDojo with a real tool-calling agent", size=14, bold=True, color=MAROON)
column_chart(s, 5.5, 1.55, 4.62, 2.7, ["No defence", "MAPIS", "Stateless"], [("Attack success rate (%)", (15.3, 0.0, 0.0))], maximum=20, legend=False, size=10, gap=80)
bullets(s, 5.5, 4.35, 4.62, 3.0, [
    "qwen2.5 7B agent, 4 suites, 39 benign + 144 attacked runs per defence.",
    "Attacks succeeded 22 / 144 times without defence, 0 / 144 with MAPIS (95 % upper bound 2.6 %).",
    "Benign tasks solved: 28.2 % without, 25.6 % with MAPIS (1 of 39 lost).",
    "AgentDojo injections are explicit, so the stateless model also stops them: this shows MAPIS works inside a live agent at low cost."], size=12, gap=5)
notes(s, "Left: all systems on the same 153 sessions. Right: a real LLM agent where MAPIS gates every tool call and tool output.")

# ======================================================================= 15 demo
s = S[14]; clear(s); title(s, 14, "Prototype / Demonstration", 15)
s.shapes.add_picture(f"{REPO}/docs/screenshots/trained_3_decomposed_email_held.png", Inches(L), Inches(1.15), height=Inches(5.3))
tb(s, L, 6.5, 5.45, 0.8, "Operator console with the trained model: the decomposed attack is held at the email action, with the trace file → memory write → memory read → email.", size=11, color=GREY)
tb(s, 6.2, 1.12, 3.92, 0.4, "Live demo flow", size=15, bold=True, color=MAROON)
steps = ["Clean task (LangGraph): every hop passes, the email is sent.",
         "Decomposed attack: no message has a command; the email to the planted address is held. Operator clicks Reject.",
         "Same attack through AutoGen: same verdict.",
         "Session inspector: multi-hop attack held; its authorized twin passes.",
         "Results tab: all comparisons."]
bullets(s, 6.2, 1.55, 3.92, 3.9, [f"{i + 1}.||  {t}" for i, t in enumerate(steps)], size=13, gap=6)
card(s, 6.2, 5.55, 3.92, 1.8, fill=PINK)
tb(s, 6.3, 5.6, 3.72, 1.7, ["Run it", "python -m uvicorn backend.main:app --port 8000", "cd frontend ; npm start", "→ http://localhost:3000"], size=11, font=MONO, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Run the five demo steps. If the laptop has a problem, use this screenshot and the fusion calculator page.")

# ======================================================================= 16 limitations
s = S[15]; clear(s); title(s, 15, "Limitations & Technical Challenges", 16)
table(s, L, 1.2, CW, [
    ["Limitation", "Detail"],
    ["Tampering checks are post-hoc", "Designed after reading the team-set misses; the 95 % there is not an independent estimate. A fresh hand-written set is needed."],
    ["Attacks on the session record", "StateAttack: 80.4 % recall but 10.2 % FPR (above target, mostly memory-laundering twins); items the agent must decode: 25 %."],
    ["Generated benchmarks", "MultiHop and Adaptive come from templates (held-out families, wordings and tools; real carrier text), so they are easier than real traffic."],
    ["Seed variation", "At the default cut-off 2 of 5 seeds exceed 5 % multi-hop FPR; the validation-calibrated cut-off keeps every seed ≤ 1.8 %."],
    ["Training overlap", "MAPIS was trained on AgentDojo-style injections, which the live-agent run also uses."],
    ["Small models in baselines", "The live agent, the LLM judge and NeMo used a local 7B model."],
    ["Single-hop attacks", "On BIPIA there is no cross-hop evidence; stateless recall is within seed variance (94.5 vs 95.8 %)."],
    ["Scripted testbed", "The 5-agent testbed is scripted; real LLM behaviour was tested on AgentDojo only."]], [2.5, 7.07], size=12, row_h=0.66, bold_first_col=True)
notes(s, "Stated once, factually. The most important: the tampering-check result needs a fresh set, and decoded items are still missed.")

# ======================================================================= 17 completion + future
s = S[16]; clear(s); title(s, 16, "Completion Status & Future Work", 17)
table(s, L, 1.2, CW, [
    ["Phase", "Status", "Outcome"],
    ["1  Literature and problem", "DONE", "Gap defined"],
    ["2  Testbed and FastAPI hooks", "DONE", "LangGraph and AutoGen through one tap"],
    ["3  Attack dataset and MAPIS-Bench", "DONE", "Six benchmark sets with twins, two test-only sets"],
    ["4  Trust model and fine-tuning", "DONE", "5 seeds, adversarial training, calibration"],
    ["5  Tiered response and forensic logging", "DONE", "4 tiers, trace, quarantine review, tampering checks"],
    ["6  Dashboard and integration", "DONE", "Operator console"],
    ["7  Benchmarking against guardrails", "DONE", "5 baselines, live LLM agents"],
    ["8  Report and demonstration", "DONE", "Thesis, report, live demo"]], [4.0, 1.1, 4.47], size=12, row_h=0.45)
tb(s, L, 5.4, CW, 0.4, "Future work", size=15, bold=True, color=MAROON)
bullets(s, L, 5.8, CW, 1.6, ["A fresh hand-written test set to confirm the tampering checks; checks for items the agent must decode.",
                             "Tap agent-internal reads; evaluate on real agent traffic with larger live agents and stronger LLM judges.",
                             "Multimodal content, more frameworks, production hardening."], size=13, gap=4)
notes(s, "All eight phases from the zeroth-review timeline are complete.")

# ======================================================================= 18 contribution + targets
s = S[17]; clear(s); title(s, 17, "Project Contribution & Achievement", 18)
table(s, L, 1.2, CW, [
    ["Target (from the abstract)", "Result", "Met"],
    ["Accuracy ≥ 90 %", "98.5 % (5 seeds)", "Yes"],
    ["False-positive rate ≤ 5 %", "0.9 ± 0.8 % overall; multi-hop 3.0 % (every seed ≤ 1.8 % with the calibrated cut-off)", "Yes"],
    ["Latency < 200 ms per message", "63 ms single, 51 ms batched (RTX 3050 laptop)", "Yes"],
    ["Multi-hop recall gain ≥ 20 points", "+96 points at matched FPR (+13.5 at the default threshold)", "Yes"]], [3.0, 5.67, 0.9], size=13, row_h=0.6)
tb(s, L, 4.35, CW, 0.4, "Contributions", size=15, bold=True, color=MAROON)
bullets(s, L, 4.75, CW, 2.7, [
    "A stateful, provenance-aware monitor at a framework-neutral tap, 63 ms per message.",
    "MAPIS-Bench: multi-hop fragment attacks with matched benign twins, an evasive-attacker set and attacks on the session record.",
    "A fair matched-false-positive comparison against stateless and LLM-based detectors.",
    "Action-argument tampering checks: team-written attacks 35–45 % → 95 % without retraining.",
    "Evaluation inside a live LLM-agent pipeline: attack success 15.3 % → 0 %."], size=14, gap=5)
notes(s, "Every target from the abstract is met.")

# ======================================================================= 19 team
s = S[18]; clear(s); title(s, 18, "Team Contribution & Responsibility", 19)
people = [("Vishnu Vardhan", "Testbed & Orchestration Lead", "The LangGraph multi-agent testbed, agent-to-agent orchestration, and FastAPI interception middleware."),
          ("Nithya Sai", "Attack Dataset & Red-Team Lead", "MAPIS-Bench construction, attack taxonomy, multi-hop attack scenarios, and dataset labelling."),
          ("Sreekar Reddy", "Detection Model Lead", "The session-context design and trust-scoring classifier, including model training, feature design, and threshold calibration."),
          ("Beena Reddy", "Response, Dashboard & Evaluation Lead", "The tiered response layer, forensic logging, dashboard integration, and benchmark evaluation.")]
cw2 = (CW - 0.3) / 2
for i, (n, r, d) in enumerate(people):
    x, y = L + (i % 2) * (cw2 + 0.3), 1.2 + (i // 2) * 2.45
    card(s, x, y, cw2, 2.25)
    tb(s, x + 0.12, y + 0.1, cw2 - 0.24, 0.4, n, size=17, bold=True, color=MAROON)
    tb(s, x + 0.12, y + 0.52, cw2 - 0.24, 0.35, r, size=13, bold=True)
    tb(s, x + 0.12, y + 0.95, cw2 - 0.24, 1.25, d, size=14, color=GREY)
tb(s, L, 6.25, CW, 0.9, size=14, text="Shared: the hand-written independent test set (each member wrote 5 attacks with their twins), weekly integration testing, code review, experiment tracking, documentation, and thesis preparation across all four members.")
notes(s, "Roles and wording as in the First Review; everyone took part in the whole project.")

# ======================================================================= 20 references
s = S[19]; clear(s); title(s, 19, "References", 20)
refs = ["[1] K. Greshake et al., “Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,” AISec '23, 2023.",
        "[2] Y. Liu et al., “Prompt injection attack against LLM-integrated applications,” arXiv:2306.05499, 2023.",
        "[3] Q. Zhan et al., “InjecAgent: Benchmarking indirect prompt injections in tool-integrated LLM agents,” Findings of ACL, 2024.",
        "[4] E. Debenedetti et al., “AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents,” NeurIPS 2024.",
        "[5] J. Yi et al., “Benchmarking and defending against indirect prompt injection attacks on large language models,” arXiv:2312.14197, 2023.",
        "[6] H. Zhang et al., “Agent Security Bench (ASB): Formalizing and benchmarking attacks and defenses in LLM-based agents,” arXiv:2410.02644, 2024.",
        "[7] F. Jia et al., “The Task Shield: Enforcing task alignment to defend against indirect prompt injection in LLM agents,” arXiv:2412.16682, 2024.",
        "[8] Y. Wang et al., “AgentWatcher: A rule-based prompt injection monitor,” arXiv:2604.01194, 2026.",
        "[9] S. Chennabasappa et al., “LlamaFirewall: An open source guardrail system for building secure AI agents,” arXiv:2505.03574, 2025.",
        "[10] D. Lee and M. Tiwari, “Prompt Infection: LLM-to-LLM prompt injection within multi-agent systems,” arXiv:2410.07283, 2024.",
        "[11] S. Wang et al., “G-Safeguard: A topology-guided security lens and treatment on LLM-based multi-agent systems,” ACL 2025.",
        "[12] P. He et al., “DeBERTa: Decoding-enhanced BERT with disentangled attention,” ICLR 2021.",
        "[13] H. Inan et al., “Llama Guard: LLM-based input-output safeguard for human-AI conversations,” arXiv:2312.06674, 2023.",
        "[14] T. Rebedea et al., “NeMo Guardrails: A toolkit for controllable and safe LLM applications with programmable rails,” EMNLP 2023 Demos.",
        "[15] S. Li and Y. Zhao, “The autonomy tax: Defense training breaks LLM agents,” arXiv:2603.19423, 2026.",
        "[16] T. Geng et al., “Prompt injection attacks on large language models: A survey of attack methods, root causes, and defense strategies,” Computers, Materials & Continua, 2026."]
bullets(s, L, 1.1, CW, 6.3, refs, size=12, gap=4)
for p in s.shapes[-1].text_frame.paragraphs:                      # numbered references, no bullet symbol
    p.runs[0].text = p.runs[0].text.replace("•  ", "")
notes(s, "References 1-5, 7, 8, 15 and 16 were in the First Review; the rest were added during the project.")

# ======================================================================= 21 thank you
s = S[20]; clear(s)
tb(s, L, 2.55, CW, 1.2, "Thank You", size=60, bold=True, color=MAROON, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
tb(s, L, 3.8, CW, 0.6, "Questions?", size=26, color=INK, align=PP_ALIGN.CENTER)
tb(s, L, 4.75, CW, 0.9, ["MAPIS — Multi-Agent Prompt Injection Shield  •  Team A1", "github.com/Vishnu868/Mapis"], size=14, color=GREY, align=PP_ALIGN.CENTER)
footer(s, 21)

assert len(prs.slides) == TOTAL
prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
