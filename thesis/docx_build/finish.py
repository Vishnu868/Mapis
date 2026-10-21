import copy, re
import docx
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

D = docx.Document('body.docx')
FONT = 'Times New Roman'
MAROON = RGBColor(0xA4, 0x12, 0x3F)

# ---------------------------------------------------------------- styles
def set_font(style, size=None, bold=None, italic=None, color=None, name=FONT):
    f = style.font
    f.name = name
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.append(rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), name)
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:cstheme', 'w:eastAsiaTheme'):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    f.color.rgb = color or RGBColor(0, 0, 0)

body_styles = ['Normal', 'Body Text', 'First Paragraph', 'Compact', 'Bibliography', 'Definition', 'Definition Term']
for n in body_styles:
    try:
        st = D.styles[n]
    except KeyError:
        continue
    set_font(st, 12)
    pf = st.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(6)
    pf.space_before = Pt(0)
    if n in ('Body Text', 'First Paragraph', 'Normal'):
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
D.styles['Definition Term'].font.bold = True
D.styles['Bibliography'].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

for n, size, before, after in (('Heading 1', 20, 0, 18), ('Heading 2', 14, 14, 6), ('Heading 3', 12, 10, 4)):
    st = D.styles[n]
    set_font(st, size, bold=True, italic=False)
    pf = st.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.keep_with_next = True
    pf.line_spacing = 1.15
D.styles['Heading 1'].paragraph_format.page_break_before = True

for n in ('Table Caption', 'Image Caption'):
    st = D.styles[n]
    set_font(st, 11, italic=False)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    st.paragraph_format.space_before = Pt(4); st.paragraph_format.space_after = Pt(10)
for n in ('Captioned Figure',):
    try:
        D.styles[n].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    except KeyError:
        pass
try:
    set_font(D.styles['Source Code'], 9, name='Consolas')
    D.styles['Source Code'].paragraph_format.line_spacing = 1.0
except KeyError:
    pass
try:
    set_font(D.styles['Verbatim Char'], 10, name='Consolas')
except KeyError:
    pass

# ---------------------------------------------------------------- headings: "Chapter N" line, number captions per chapter
chap = 0
fig = tab = 0
appendix = False
for p in list(D.paragraphs):
    sn = p.style.name
    if sn == 'Heading 1':
        m = re.match(r'^(\d+)\t(.*)$', p.text)
        if m:
            chap = int(m.group(1)); fig = tab = 0
            title = m.group(2)
            label = 'Chapter %d' % chap
            if title.startswith('Reproduction Guide'):
                appendix = True; label = 'Appendix A'; chap = 'A'
            for r in p.runs[1:]:
                r._element.getparent().remove(r._element)
            p.runs[0].text = title
            br = p.runs[0]._element
            # put "Chapter N" + line break before the title inside the same heading
            lab = OxmlElement('w:r'); t = OxmlElement('w:t'); t.text = label; lab.append(t)
            brk = OxmlElement('w:r'); b = OxmlElement('w:br'); brk.append(b)
            br.addprevious(lab); br.addprevious(brk)
    elif sn == 'Heading 2':
        m = re.match(r'^(\d+)\.(\d+)\t', p.text)
        if m and appendix:
            p.runs[0].text = p.runs[0].text.replace(m.group(1) + '.', 'A.', 1)
    elif sn in ('Heading 3',) and appendix:
        pass
    elif sn == 'Table Caption' and p.text.strip():
        tab += 1
        p.runs[0].text = 'Table %s.%d: ' % (chap, tab) + p.runs[0].text if p.runs else p.text
    elif sn == 'Image Caption' and p.text.strip():
        fig += 1
        if p.runs:
            p.runs[0].text = 'Figure %s.%d: ' % (chap, fig) + p.runs[0].text

# ---------------------------------------------------------------- tables: booktabs-like lines, 10.5 pt, header bold, centred
def border(el, tag, sz=8, val='single'):
    b = OxmlElement('w:' + tag); b.set(qn('w:val'), val); b.set(qn('w:sz'), str(sz)); b.set(qn('w:space'), '0'); b.set(qn('w:color'), '000000')
    el.append(b)

for t in D.tables:
    tblPr = t._tbl.tblPr
    for old in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(old)
    bd = OxmlElement('w:tblBorders')
    border(bd, 'top', 12); border(bd, 'bottom', 12); border(bd, 'insideH', 4)
    border(bd, 'left', 0, 'nil'); border(bd, 'right', 0, 'nil'); border(bd, 'insideV', 0, 'nil')
    tblPr.append(bd)
    jc = tblPr.find(qn('w:jc'))
    if jc is None:
        jc = OxmlElement('w:jc'); tblPr.append(jc)
    jc.set(qn('w:val'), 'center')
    for ri, row in enumerate(t.rows):
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.1
                p.paragraph_format.space_after = Pt(2)
                for r in p.runs:
                    r.font.size = Pt(10.5); r.font.name = FONT
                    if ri == 0:
                        r.font.bold = True


# ---- fix-ups: acknowledgement signature, plain abbreviation/symbol lists, full-width data tables
for p in D.paragraphs:
    if 'DODLA' in p.text.upper() and 'NITHYA' in p.text.upper() and len(p.text) < 80:
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.line_spacing = 1.15
def plain_list_table(t, widths):
    tblPr = t._tbl.tblPr
    for old in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(old)
    bd = OxmlElement('w:tblBorders')
    for tag in ('top', 'bottom', 'left', 'right', 'insideH', 'insideV'):
        border(bd, tag, 0, 'nil')
    tblPr.append(bd)
    for row in t.rows:
        for i, c in enumerate(row.cells):
            c.width = Cm(widths[i])
            for p in c.paragraphs:
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.bold = False; r.font.size = Pt(12)
    for i, gc in enumerate(t._tbl.tblGrid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(widths[i] * 567)))
for t in D.tables[:2]:
    plain_list_table(t, [3.5, 1.0, 11.5])
for t in D.tables[2:]:
    tblPr = t._tbl.tblPr
    tw = tblPr.find(qn('w:tblW'))
    if tw is None:
        tw = OxmlElement('w:tblW'); tblPr.append(tw)
    tw.set(qn('w:type'), 'pct'); tw.set(qn('w:w'), '5000')

# ---------------------------------------------------------------- page setup
for s in D.sections:
    s.page_height = Cm(29.7); s.page_width = Cm(21.0)
    s.left_margin = Cm(3.0); s.right_margin = Cm(2.0); s.top_margin = Cm(2.5); s.bottom_margin = Cm(2.5)

# ---------------------------------------------------------------- front matter (inserted before the first paragraph)
first = D.paragraphs[0]
def para(text='', size=12, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, italic=False, color=None):
    p = first.insert_paragraph_before()
    p.style = D.styles['Normal']
    p.paragraph_format.alignment = align
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.15
    if text:
        r = p.add_run(text); r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic; r.font.name = FONT
        if color: r.font.color.rgb = color
    return p
def rich(parts, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=12, after=6, spacing=1.5):
    p = first.insert_paragraph_before(); p.style = D.styles['Normal']
    p.paragraph_format.alignment = align; p.paragraph_format.space_after = Pt(after); p.paragraph_format.line_spacing = spacing
    for txt, b in parts:
        r = p.add_run(txt); r.font.bold = b; r.font.size = Pt(size); r.font.name = FONT
    return p
def pagebreak():
    p = first.insert_paragraph_before(); p.add_run().add_break(WD_BREAK.PAGE)
def logo(width_cm=7):
    p = para(); p.add_run().add_picture('images/univA.png', width=Cm(width_cm))
def section_break(fmt=None, start=None):
    """End the current section here (paragraph-level sectPr)."""
    p = first.insert_paragraph_before()
    sp = copy.deepcopy(D.sections[-1]._sectPr)
    for x in sp.findall(qn('w:pgNumType')) + sp.findall(qn('w:footerReference')) + sp.findall(qn('w:headerReference')):
        sp.remove(x)
    if fmt:
        pg = OxmlElement('w:pgNumType'); pg.set(qn('w:fmt'), fmt)
        if start: pg.set(qn('w:start'), str(start))
        sp.append(pg)
    p._p.get_or_add_pPr().append(sp)
    return sp

students = [('Dodla Nithya Sai', 'CB.SC.U4AIE23021'), ('Vishnu Vardhan', 'CB.SC.U4AIE23043'),
            ('Sreekar Reddy', 'CB.SC.U4AIE23049'), ('Beena Reddy', 'CB.SC.U4AIE23065')]

# title page
para('MAPIS: MULTI-AGENT PROMPT INJECTION SHIELD', 16, True, before=24)
para('A Stateful Trust-Scoring Monitor for Indirect Prompt Injection in Multi-Agent LLM Pipelines', 13, True, before=6, after=30)
for t in ('A Thesis', 'Submitted in partial fulfilment for the Degree of', 'BACHELOR OF TECHNOLOGY', 'in',
          'COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE)'):
    para(t, 12, after=4)
para('by', 12, before=20, after=6)
for n, r in students:
    para('%s (%s)' % (n, r), 14, True, after=2)
para('', after=40)
logo(8)
para('', after=30)
para('DEPARTMENT OF ARTIFICIAL INTELLIGENCE', 12, after=2)
para('AMRITA VISHWA VIDYAPEETHAM', 14, True, after=2)
para('COIMBATORE CAMPUS (INDIA)', 12, after=10)
para('October 2026', 12)
pagebreak()

# bonafide
para('DEPARTMENT OF ARTIFICIAL INTELLIGENCE', 12, after=2)
para('AMRITA VISHWA VIDYAPEETHAM', 14, True, after=2)
para('COIMBATORE CAMPUS', 12, after=24)
logo(7)
para('BONAFIDE CERTIFICATE', 16, True, before=24, after=18)
rich([('This is to certify that the thesis entitled “', False), ('MAPIS: Multi-Agent Prompt Injection Shield', True),
      ('” submitted by ', False)] +
     sum([[('%s, Roll. No: %s' % s, True), (', ' if i < 2 else (' and ' if i == 2 else ''), False)] for i, s in enumerate(students)], []) +
     [(' for the award of the ', False), ('Degree of Bachelor of Technology', True), (' under the ', False), ('Faculty of Engineering', True),
      (' is a bonafide record of the work carried out by them under our guidance and supervision at “Department of Artificial Intelligence”, '
       'Amrita Vishwa Vidyapeetham, Coimbatore Campus.', False)])
para('Submitted for the examination held on 22 October 2026.', 12, align=WD_ALIGN_PARAGRAPH.LEFT, before=30, after=40)
ex = first.insert_paragraph_before(); ex.paragraph_format.tab_stops.add_tab_stop(Cm(11))
r = ex.add_run('INTERNAL EXAMINER\tEXTERNAL EXAMINER'); r.bold = True; r.font.name = FONT
para('', after=40)
gt = D.add_table(rows=1, cols=2)
for cell, lines in zip(gt.rows[0].cells, (['K. Sripriyan', 'Guide,', 'Assistant Professor,', 'Department of Artificial Intelligence,', 'Amrita Vishwa Vidyapeetham,', 'Coimbatore Campus, India.'],
                                          ['Anjana Sankar', 'Co-Guide,', 'Assistant Professor,', 'Department of Artificial Intelligence,', 'Amrita Vishwa Vidyapeetham,', 'Coimbatore Campus, India.'])):
    cell.paragraphs[0].text = ''
    for i, l in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(0)
        rr = p.add_run(l); rr.bold = (i == 0); rr.font.name = FONT; rr.font.size = Pt(12)
first._p.addprevious(gt._tbl)
pagebreak()

# declaration
para('DEPARTMENT OF ARTIFICIAL INTELLIGENCE', 12, after=2)
para('AMRITA VISHWA VIDYAPEETHAM', 14, True, after=2)
para('COIMBATORE CAMPUS', 12, after=50)
para('DECLARATION', 16, True, after=18)
rich([('We, ', False)] + sum([[(s[0], True), (', ', False), ('Reg. No: ' + s[1], True), (', ' if i < 2 else (' and ' if i == 2 else ''), False)] for i, s in enumerate(students)], []) +
     [(', hereby declare that this thesis entitled “', False), ('MAPIS: Multi-Agent Prompt Injection Shield', True),
      ('” is the record of the original work done by us under the guidance of ', False), ('K. Sripriyan', True),
      (', Assistant Professor (Guide), and ', False), ('Anjana Sankar', True),
      (', Assistant Professor (Co-Guide), Department of Artificial Intelligence, Amrita Vishwa Vidyapeetham, Coimbatore Campus. '
       'To the best of our knowledge, this work has not formed the basis for the award of any degree/diploma/associateship/fellowship '
       'or a similar award to any candidate in any University.', False)])
pl = first.insert_paragraph_before(); pl.paragraph_format.space_before = Pt(36)
pl.paragraph_format.tab_stops.add_tab_stop(Cm(16), alignment=2)
r = pl.add_run('Place: Coimbatore\tSignature of the Students'); r.bold = True; r.font.name = FONT
r = para('Date: 22 October 2026', 12, True, align=WD_ALIGN_PARAGRAPH.LEFT, after=60)
para('COUNTERSIGNED', 13, after=50)
for i, l in enumerate(['Dr. K.P Soman', 'Professor and Dean,', 'Department of Artificial Intelligence', 'Amrita Vishwa Vidyapeetham,', 'Coimbatore Campus,', 'India.']):
    para(l, 12, bold=(i == 0))
section_break()          # section 1: no page numbers

# contents + lists (Word fields; Word fills them on opening)
def heading_unnumbered(text):
    p = first.insert_paragraph_before(text); p.style = D.styles['Heading 1']
    p.paragraph_format.page_break_before = False
    return p
def field(instr, placeholder):
    p = first.insert_paragraph_before(); p.style = D.styles['Normal']
    r = p.add_run(); f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'begin'); f.set(qn('w:dirty'), 'true'); r._r.append(f)
    r = p.add_run(); it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = instr; r._r.append(it)
    r = p.add_run(); f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'separate'); r._r.append(f)
    p.add_run(placeholder).italic = True
    r = p.add_run(); f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'end'); r._r.append(f)
heading_unnumbered('Contents')
field('TOC \\o "1-2" \\h \\z \\u', 'Right-click here and choose "Update Field" to build the table of contents.')
pagebreak()
heading_unnumbered('List of Figures')
field('TOC \\h \\z \\t "Image Caption,1"', 'Right-click and choose "Update Field".')
pagebreak()
heading_unnumbered('List of Tables')
field('TOC \\h \\z \\t "Table Caption,1"', 'Right-click and choose "Update Field".')

# acknowledgement heading etc. start a new page via Heading 1 page_break_before.
# arabic numbering from Chapter 1: find the Heading 1 of chapter 1 and end the roman section just before it
intro = next(p for p in D.paragraphs if p.style.name == 'Heading 1' and p.text.endswith('Introduction'))
sp_intro = copy.deepcopy(D.sections[-1]._sectPr)
for x in sp_intro.findall(qn('w:pgNumType')) + sp_intro.findall(qn('w:footerReference')) + sp_intro.findall(qn('w:headerReference')):
    sp_intro.remove(x)
pg = OxmlElement('w:pgNumType'); pg.set(qn('w:fmt'), 'lowerRoman'); pg.set(qn('w:start'), '1'); sp_intro.append(pg)
brk_p = intro.insert_paragraph_before(); brk_p._p.get_or_add_pPr().append(sp_intro)
intro.paragraph_format.page_break_before = False
final = D.sections[-1]._sectPr
for x in final.findall(qn('w:pgNumType')):
    final.remove(x)
pg = OxmlElement('w:pgNumType'); pg.set(qn('w:fmt'), 'decimal'); pg.set(qn('w:start'), '1'); final.append(pg)

# list of publications at the end
p = D.add_paragraph('List of Publications', style='Heading 1')
p2 = D.add_paragraph('(Based on the Project Work)'); p2.runs[0].bold = True; p2.runs[0].font.size = Pt(14)
D.add_paragraph('No papers have been published or communicated from this work at the time of submission.', style='Body Text')

# ---------------------------------------------------------------- footers with page numbers (sections 2 and 3), none on section 1
D2 = docx.Document  # noqa
secs = D.sections
for i, s in enumerate(secs):
    s.footer.is_linked_to_previous = False
    fp = s.footer.paragraphs[0]; fp.text = ''
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if i == 0:
        continue
    r = fp.add_run(); f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'begin'); r._r.append(f)
    r = fp.add_run(); it = OxmlElement('w:instrText'); it.text = 'PAGE'; r._r.append(it)
    r = fp.add_run(); f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), 'end'); r._r.append(f)

# ask Word to refresh fields (TOC, lists) on open
st = D.settings.element
u = OxmlElement('w:updateFields'); u.set(qn('w:val'), 'true'); st.append(u)

D.core_properties.title = 'MAPIS: Multi-Agent Prompt Injection Shield'
D.core_properties.author = 'Team A1'
D.save('MAPIS_Thesis.docx')
print('sections', len(D.sections))
