"""
Professional Enterprise Markdown-to-Word (.docx) Converter for HLD and LLD
Produces executive-ready, beautifully styled Word documents matching Infosys corporate standards.
"""
import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Color Palette (Corporate Infosys Navy & Modern Slate)
NAVY = RGBColor(0x00, 0x4B, 0x87)         # Infosys Blue
DARK_NAVY = RGBColor(0x00, 0x2D, 0x62)    # Deep Navy
SLATE = RGBColor(0x4A, 0x55, 0x68)        # Charcoal Slate
TEXT_BODY = RGBColor(0x1A, 0x20, 0x2C)    # Primary Text
MUTED = RGBColor(0x71, 0x80, 0x96)        # Muted
BORDER_COLOR = "D2D6DC"
HEADER_BG = "004B87"
ZEBRA_BG = "F7F9FC"
CALLOUT_BG = "F0F4F8"
CODE_BG = "F8F9FA"


def set_cell_background(cell, color_hex):
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    cell._tc.get_or_add_tcPr().append(tcMar)


def set_table_borders(table, border_color=BORDER_COLOR):
    tblBorders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{border_color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="{border_color}"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    table._tbl.tblPr.append(tblBorders)


def add_inline_formatted_text(paragraph, text, base_font="Calibri", base_size=Pt(10), base_color=TEXT_BODY):
    """Parses bold, italic, and inline code formatting."""
    # Pattern matching: `code`, **bold**, *italic*
    pattern = re.compile(r'(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)')
    tokens = pattern.split(text)

    for token in tokens:
        if not token:
            continue
        if token.startswith('`') and token.endswith('`'):
            code_text = token[1:-1]
            run = paragraph.add_run(code_text)
            run.font.name = "Consolas"
            run.font.size = Pt(base_size.pt * 0.92)
            run.font.color.rgb = RGBColor(0x80, 0x1F, 0x48)  # Subtle wine/magenta
        elif token.startswith('**') and token.endswith('**'):
            bold_text = token[2:-2]
            run = paragraph.add_run(bold_text)
            run.font.name = base_font
            run.font.size = base_size
            run.font.bold = True
            run.font.color.rgb = base_color
        elif token.startswith('*') and token.endswith('*'):
            italic_text = token[1:-1]
            run = paragraph.add_run(italic_text)
            run.font.name = base_font
            run.font.size = base_size
            run.font.italic = True
            run.font.color.rgb = base_color
        else:
            run = paragraph.add_run(token)
            run.font.name = base_font
            run.font.size = base_size
            run.font.color.rgb = base_color


def format_table(doc, table_lines):
    if len(table_lines) < 2:
        return

    # Extract rows and cells
    parsed_rows = []
    for line in table_lines:
        line_clean = line.strip().strip('|')
        cells = [c.strip() for c in line_clean.split('|')]
        # Skip divider row (e.g. | :--- | :--- |)
        if all(re.match(r'^:?-+:?$', c) for c in cells):
            continue
        parsed_rows.append(cells)

    if not parsed_rows:
        return

    col_count = max(len(r) for r in parsed_rows)
    # Pad shorter rows
    for r in parsed_rows:
        while len(r) < col_count:
            r.append("")

    table = doc.add_table(rows=len(parsed_rows), cols=col_count)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table)

    # Style Header Row
    header_row = table.rows[0]
    # repeat header across pages
    trPr = header_row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

    for c_idx, cell in enumerate(header_row.cells):
        set_cell_background(cell, HEADER_BG)
        set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        text = parsed_rows[0][c_idx]
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Style Data Rows
    for r_idx, row_cells in enumerate(parsed_rows[1:], start=1):
        row = table.rows[r_idx]
        # Prevent row split across pages
        row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        bg_color = ZEBRA_BG if r_idx % 2 == 1 else "FFFFFF"

        for c_idx, cell_text in enumerate(row_cells):
            cell = row.cells[c_idx]
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            add_inline_formatted_text(p, cell_text, base_font="Calibri", base_size=Pt(9), base_color=TEXT_BODY)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def format_callout(doc, text, alert_type="NOTE"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, CALLOUT_BG)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)

    # Left border only (accent)
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="32" w:space="0" w:color="{HEADER_BG}"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    cell._tc.get_or_add_tcPr().append(tcBorders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15

    add_inline_formatted_text(p, text, base_font="Calibri", base_size=Pt(9.5), base_color=SLATE)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def format_code_block(doc, code_lines, language=""):
    code_text = "\n".join(code_lines)
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, CODE_BG)
    set_cell_margins(cell, top=120, bottom=120, left=160, right=160)

    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        f'</w:tcBorders>'
    )
    cell._tc.get_or_add_tcPr().append(tcBorders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05

    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(8.0)
    run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def convert_markdown_to_docx(md_path, docx_path, doc_title, doc_id):
    print(f"[Converter] Reading: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    doc = docx.Document()

    # Configure Margins
    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

        # Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run(f"Infosys Enterprise Architecture | {doc_title} ({doc_id})")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = MUTED

        # Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun1 = fp.add_run("CONFIDENTIAL & PROPRIETARY — INFOSYS UK PUBLIC SECTOR PRACTICE")
        frun1.font.name = "Calibri"
        frun1.font.size = Pt(8)
        frun1.font.color.rgb = MUTED

    # Document Title Block
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run(doc_title)
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(24)
    r_title.font.bold = True
    r_title.font.color.rgb = NAVY

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run("Infosys Social Value RFP Response Engine — Production Design Specification")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = SLATE

    # State machine parsing lines
    in_code_block = False
    code_lines = []
    code_lang = ""

    in_table = False
    table_lines = []

    in_callout = False
    callout_lines = []

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")

        # 1. Code block handling
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line.strip()[3:].strip()
                code_lines = []
            else:
                in_code_block = False
                format_code_block(doc, code_lines, code_lang)
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # 2. Table handling
        if line.strip().startswith("|") and line.strip().endswith("|"):
            if not in_table:
                in_table = True
                table_lines = [line]
            else:
                table_lines.append(line)
            continue
        else:
            if in_table:
                in_table = False
                format_table(doc, table_lines)
                table_lines = []

        # 3. Blockquote / Callout handling
        if line.strip().startswith(">"):
            callout_text = line.strip()[1:].strip()
            # Remove [!NOTE] or [!IMPORTANT]
            callout_text = re.sub(r'^\[!(NOTE|IMPORTANT|TIP|WARNING|CAUTION)\]\s*', r'\1: ', callout_text)
            format_callout(doc, callout_text)
            continue

        # Empty lines
        if not line.strip():
            continue

        # 4. Horizontal Rule
        if re.match(r'^-{3,}$', line.strip()) or re.match(r'^\*{3,}$', line.strip()):
            p_hr = doc.add_paragraph()
            p_hr.paragraph_format.space_before = Pt(6)
            p_hr.paragraph_format.space_after = Pt(6)
            pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="{BORDER_COLOR}"/></w:pBdr>')
            p_hr._p.get_or_add_pPr().append(pBdr)
            continue

        # 5. Headings
        if line.startswith("# "):
            # Skip if duplicate of main title
            continue
        elif line.startswith("## "):
            h_text = line[3:].strip()
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(16)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(h_text)
            r.font.name = "Calibri"
            r.font.size = Pt(15)
            r.font.bold = True
            r.font.color.rgb = DARK_NAVY
            # Add bottom accent border
            pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="10" w:space="2" w:color="{HEADER_BG}"/></w:pBdr>')
            h._p.get_or_add_pPr().append(pBdr)
            continue
        elif line.startswith("### "):
            h_text = line[4:].strip()
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(3)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(h_text)
            r.font.name = "Calibri"
            r.font.size = Pt(12)
            r.font.bold = True
            r.font.color.rgb = NAVY
            continue
        elif line.startswith("#### "):
            h_text = line[5:].strip()
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(h_text)
            r.font.name = "Calibri"
            r.font.size = Pt(10.5)
            r.font.bold = True
            r.font.color.rgb = SLATE
            continue

        # 6. List Items
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            content = line.strip()[2:]
            add_inline_formatted_text(p, content, base_font="Calibri", base_size=Pt(10), base_color=TEXT_BODY)
            continue

        if re.match(r'^\d+\.\s+', line.strip()):
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            content = re.sub(r'^\d+\.\s+', '', line.strip())
            add_inline_formatted_text(p, content, base_font="Calibri", base_size=Pt(10), base_color=TEXT_BODY)
            continue

        # 7. Standard Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        add_inline_formatted_text(p, line.strip(), base_font="Calibri", base_size=Pt(10), base_color=TEXT_BODY)

    # Flush any trailing table
    if in_table and table_lines:
        format_table(doc, table_lines)

    os.makedirs(os.path.dirname(docx_path), exist_ok=True)
    doc.save(docx_path)
    print(f"[Converter] Successfully generated professional Word doc: {docx_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    docs_dir = os.path.join(base_dir, "docs")
    proj_docs_dir = os.path.join(base_dir, "social-value-infoproj", "docs")

    hld_md = os.path.join(docs_dir, "HIGH_LEVEL_DESIGN_DOCUMENT_HLD.md")
    hld_docx = os.path.join(docs_dir, "HIGH_LEVEL_DESIGN_DOCUMENT_HLD.docx")
    proj_hld_docx = os.path.join(proj_docs_dir, "HIGH_LEVEL_DESIGN_DOCUMENT_HLD.docx")

    lld_md = os.path.join(docs_dir, "LOW_LEVEL_DESIGN_DOCUMENT_LLD.md")
    lld_docx = os.path.join(docs_dir, "LOW_LEVEL_DESIGN_DOCUMENT_LLD.docx")
    proj_lld_docx = os.path.join(proj_docs_dir, "LOW_LEVEL_DESIGN_DOCUMENT_LLD.docx")

    convert_markdown_to_docx(
        hld_md,
        hld_docx,
        "High-Level Design (HLD) Document",
        "INFOSYS-SV-HLD-2026-V1"
    )

    convert_markdown_to_docx(
        lld_md,
        lld_docx,
        "Low-Level Design (LLD) Document",
        "INFOSYS-SV-LLD-2026-V1"
    )

    # Also mirror into project docs directory
    import shutil
    shutil.copyfile(hld_docx, proj_hld_docx)
    shutil.copyfile(lld_docx, proj_lld_docx)
    print(f"[Done] Copied to both {docs_dir} and {proj_docs_dir}")
