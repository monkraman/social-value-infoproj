"""
Synthetic Social Value Knowledge Generator
Generates realistic PDF, DOCX, and XLSX sample knowledge documents for testing the POC.
All documents are clearly marked as synthetic POC test data.
"""
import os
import sys
import docx
from docx.shared import Pt, Inches, RGBColor
import pymupdf
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "documents", "synthetic")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_docx():
    """Generates Infosys_Birmingham_Digital_Inclusion.docx."""
    path = os.path.join(OUTPUT_DIR, "Infosys_Birmingham_Digital_Inclusion.docx")
    doc = docx.Document()

    # Title
    title = doc.add_heading("Infosys Social Value Initiative: Birmingham Digital Inclusion Clinics", level=0)
    
    # Subtitle / Metadata
    p_meta = doc.add_paragraph()
    p_meta.add_run("Classification: ").bold = True
    p_meta.add_run("Synthetic POC Data Only — Demonstration Knowledge Base\n")
    p_meta.add_run("Target Geography: ").bold = True
    p_meta.add_run("Birmingham & Greater West Midlands\n")
    p_meta.add_run("Primary Theme: ").bold = True
    p_meta.add_run("Digital Inclusion & Skills\n")
    p_meta.add_run("Author: ").bold = True
    p_meta.add_run("Infosys UK Social Value Practice")

    doc.add_heading("1. Executive Summary & Context", level=1)
    doc.add_paragraph(
        "In collaboration with local community anchors across Birmingham wards (including Ladywood, Aston, and "
        "Nechells), Infosys proposes a structured Digital Inclusion Clinic programme. The initiative addresses "
        "digital poverty by providing accessible, face-to-face workshops on fundamental digital literacy, access to "
        "essential council online services, digital NHS portals, and online banking safety."
    )

    doc.add_heading("2. Initiative Specifications", level=1)
    doc.add_paragraph(
        "• Initiative Name: Digital Inclusion Workshop Series\n"
        "• Theme: Digital Inclusion\n"
        "• Target Beneficiaries: Elderly residents, long-term jobseekers, and economically inactive households.\n"
        "• Delivery Mechanism: 4 comprehensive multi-hour workshops per contract year.\n"
        "• Cohort Size: 12-15 participants per workshop session.\n"
        "• Annual Volume: 4 workshops per year (48-60 direct beneficiaries annually).\n"
        "• National TOMs Proxy Alignment: NT8 (No. of digital skills / inclusion workshops delivered to vulnerable groups).\n"
        "• Proxy Unit Value: £1,250.00 per workshop."
    )

    doc.add_heading("3. Local Delivery Partner & Venues", level=1)
    doc.add_paragraph(
        "Delivery is coordinated in partnership with Birmingham Community Matters (BCM) and local library learning hubs. "
        "BCM assists with grassroots participant outreach, safeguarding, and venue coordination, while Infosys STEM "
        "volunteers deliver curriculum and hands-on coaching. (Note: Synthetic partner example for POC purposes)."
    )

    doc.add_heading("4. Refurbished Hardware & Connectivity Donations", level=1)
    doc.add_paragraph(
        "To ensure sustainable digital access beyond the classroom, Infosys commits to donating 20 wiped and refurbished "
        "corporate enterprise laptops per contract year, paired with 12-month data SIMs. This aligns with proxy metric "
        "NT20 (Refurbished Digital Devices Donated) at a proxy value of £320.00 per device."
    )

    # Table of delivery plan
    doc.add_heading("5. 3-Year Delivery Milestone Plan", level=1)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Year"
    hdr_cells[1].text = "Workshops (NT8)"
    hdr_cells[2].text = "Devices Donated (NT20)"
    hdr_cells[3].text = "Annual Proxy Value"

    milestones = [
        ("Year 1", "4 workshops (48 learners)", "20 laptops", "£11,400.00"),
        ("Year 2", "4 workshops (48 learners)", "20 laptops", "£11,400.00"),
        ("Year 3", "4 workshops (48 learners)", "20 laptops", "£11,400.00"),
    ]

    for y, w, d, val in milestones:
        row_cells = table.add_row().cells
        row_cells[0].text = y
        row_cells[1].text = w
        row_cells[2].text = d
        row_cells[3].text = val

    doc.save(path)
    print(f"Generated DOCX: {path}")


def generate_pdf():
    """Generates Infosys_Youth_Employment_Pathways.pdf."""
    path = os.path.join(OUTPUT_DIR, "Infosys_Youth_Employment_Pathways.pdf")
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    text = """INFOSYS UK — SOCIAL VALUE KNOWLEDGE BRIEF
YOUTH EMPLOYMENT & SKILLS PATHWAYS (BIRMINGHAM)
[Classification: Synthetic Test Evidence — POC Use Only]

1. Overview & Objective
Youth unemployment in the West Midlands Combined Authority remains significantly above the national average. Infosys commits to delivering high-impact youth employment pathways targeted specifically at 16-24 year olds not in education, employment, or training (NEET).

2. Core Programme: Youth Tech Mentoring & Career Launch
• Initiative Name: Youth Employment & Mentoring Pathways
• Theme: Youth Employment
• Target Geography: Birmingham, Solihull, and Black Country
• Annual Volume: 3 young people supported into sustained employment/training per contract year
• Total 3-Year Volume: 9 young people
• National TOMs Proxy Metric: NT3 (Young People Supported into Employment: 16-24 NEET)
• Unit Proxy Value: £4,850.00 per individual
• 3-Year Social Value Impact: 9 × £4,850 = £43,650.00

3. Delivery Structure & Curriculum
Each participant undertakes:
- 4 weeks of structured digital work experience at Infosys Birmingham facilities
- 1-on-1 career mentoring with an Infosys Senior Consultant (12 sessions)
- Hands-on training in Python, Cloud Fundamentals, and Agile Delivery
- CV preparation, mock interviews, and guaranteed interview for Infosys entry-level roles

4. Delivery Partners
Partnering with St Basils (West Midlands youth charity supporting young people at risk of homelessness) and Birmingham Metropolitan College (BMet). (Synthetic partnership example for POC demonstration).

5. Apprenticeship Expansion Option (Enhanced Package)
Where the contract scale permits, Infosys can scale the engagement to include full-time apprenticeships:
• Metric: NT1 (Local Apprenticeship Weeks)
• Unit Value: £215.00 / week
• 52 weeks/year = £11,180.00 annual proxy value (£33,540.00 over 3 years)

6. Traceability and Audit
All evidence logs participant attendance, verified National Insurance onboarding numbers, and partner referral documentation to satisfy public sector audit requirements.
"""
    # Write text to PDF page
    rect = pymupdf.Rect(50, 50, 545, 792)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    doc.save(path)
    doc.close()
    print(f"Generated PDF: {path}")


def generate_xlsx_catalog():
    """Generates Infosys_Social_Value_Initiatives_Catalog.xlsx."""
    path = os.path.join(OUTPUT_DIR, "Infosys_Social_Value_Initiatives_Catalog.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Initiatives Catalog"

    headers = [
        "Initiative ID",
        "Initiative Name",
        "Theme",
        "Location",
        "Delivery Mechanism",
        "Annual Volume",
        "Volume Unit",
        "TOMs Code",
        "Proxy Unit Value (GBP)",
        "Delivery Partner",
        "Package Fit"
    ]
    ws.append(headers)

    data = [
        [
            "INF-SV-001",
            "Birmingham Digital Inclusion Workshops",
            "Digital Inclusion",
            "Birmingham",
            "4 community sessions per year with 12 participants per session",
            4,
            "workshops",
            "NT8",
            1250.00,
            "Birmingham Community Matters",
            "Core / Localised"
        ],
        [
            "INF-SV-002",
            "Youth Tech Mentoring & Work Experience",
            "Youth Employment",
            "Birmingham",
            "Dedicated work experience and mentoring for 3 young NEETs per year",
            3,
            "people",
            "NT3",
            4850.00,
            "St Basils Youth Charity",
            "Core / Enhanced"
        ],
        [
            "INF-SV-003",
            "Staff STEM Volunteering & School Outreach",
            "Community Engagement",
            "Birmingham",
            "Infosys tech staff delivering 100 hours coding clubs at local schools",
            100,
            "hours",
            "NT10",
            45.00,
            "Local Birmingham Secondary Schools",
            "Enhanced"
        ],
        [
            "INF-SV-004",
            "Hardware Reuse & Laptop Donation Scheme",
            "Digital Inclusion",
            "Birmingham",
            "20 refurbished laptops wiped and donated annually with data SIMs",
            20,
            "devices",
            "NT20",
            320.00,
            "West Midlands Digital Device Bank",
            "Enhanced"
        ],
        [
            "INF-SV-005",
            "Local SME & VCSE Supply Chain Procurement",
            "Economic Growth",
            "Birmingham",
            "Direct subcontracting and spend with local West Midlands suppliers",
            50000,
            "GBP spend",
            "NT14",
            0.22,
            "West Midlands Chamber of Commerce",
            "Localised"
        ],
        [
            "INF-SV-006",
            "Digital Skills Junior Apprenticeship Weeks",
            "Employment & Skills",
            "Birmingham",
            "52 weeks of certified cloud and software testing apprentice training",
            52,
            "weeks",
            "NT1",
            215.00,
            "BMet College",
            "Enhanced"
        ]
    ]

    for row in data:
        ws.append(row)

    # Style header row
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    wb.save(path)
    print(f"Generated XLSX Catalog: {path}")


def generate_xlsx_toms():
    """Generates Synthetic_National_TOMs_Proxy_Reference.xlsx."""
    path = os.path.join(OUTPUT_DIR, "Synthetic_National_TOMs_Proxy_Reference.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TOMs Proxy Reference"

    headers = [
        "TOMs Code",
        "Metric Title",
        "Theme",
        "Unit of Measure",
        "Proxy Unit Value (GBP)",
        "Description & Audit Guidance",
        "Status"
    ]
    ws.append(headers)

    toms = [
        ["NT1", "Local Apprenticeship Weeks", "Employment & Skills", "weeks", 215.00, "Apprenticeship training weeks on contract", "Synthetic POC Proxy"],
        ["NT3", "Young People Supported into Employment", "Youth Employment", "people", 4850.00, "16-24 NEETs supported into sustained jobs", "Synthetic POC Proxy"],
        ["NT8", "Digital Inclusion Workshops", "Digital Inclusion", "workshops", 1250.00, "Workshops for digitally excluded residents", "Synthetic POC Proxy"],
        ["NT10", "Staff Volunteering Hours", "Community Engagement", "hours", 45.00, "Volunteering hours supporting education/charity", "Synthetic POC Proxy"],
        ["NT14", "Local SME Supply Chain Spend", "Economic Growth", "GBP spend", 0.22, "Direct local supplier procurement spend proxy", "Synthetic POC Proxy"],
        ["NT20", "Refurbished Digital Devices Donated", "Digital Inclusion", "devices", 320.00, "Donated laptops/tablets with connectivity", "Synthetic POC Proxy"]
    ]

    for row in toms:
        ws.append(row)

    # Style
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    wb.save(path)
    print(f"Generated TOMs Reference XLSX: {path}")


def main():
    print("Generating synthetic Social Value knowledge documents...")
    generate_docx()
    generate_pdf()
    generate_xlsx_catalog()
    generate_xlsx_toms()
    print("All synthetic test documents generated successfully!")


if __name__ == "__main__":
    main()
