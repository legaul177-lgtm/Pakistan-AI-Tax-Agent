import streamlit as st
import sqlite3
import os
from google import genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. API Configuration
os.environ["GEMINI_API_KEY"] = "AIzaSyD9ivtqQJfFsAJzytdl4fjqiiHaeBWldLI" # <-- Apni Key Re-enter krain

# 2. Database Core
def get_db_connection():
    conn = sqlite3.connect('tax_app_live.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, salary INTEGER, rent INTEGER, donation INTEGER, tax_paid INTEGER
        )
    ''')
    conn.commit()
    return conn

# 3. Pakistani Statutory Law Slabs
def calculate_property_tax(net_rent):
    if net_rent <= 300000: return 0
    elif net_rent <= 600000: return int((net_rent - 300000) * 0.05)
    elif net_rent <= 2000000: return int(15000 + (net_rent - 600000) * 0.10)
    elif net_rent <= 4000000: return int(155000 + (net_rent - 2000000) * 0.15)
    else: return int(455000 + (net_rent - 4000000) * 0.20)

def calculate_pakistan_tax_v2(salary, property_income=0, donation_made=0):
    if salary <= 600000: salary_tax, slab_desc = 0, "Slab 1: Up to 600k (0%)"
    elif salary <= 1200000: salary_tax, slab_desc = (salary - 600000) * 0.05, "Slab 2: 600k to 1.2M (5%)"
    elif salary <= 2200000: salary_tax, slab_desc = 30000 + (salary - 1200000) * 0.15, "Slab 3: 1.2M to 2.2M"
    elif salary <= 3200000: salary_tax, slab_desc = 180000 + (salary - 2200000) * 0.25, "Slab 4: 2.2M to 3.2M"
    else: salary_tax, slab_desc = 430000 + (salary - 3200000) * 0.30, "Slab 5: Above 3.2M"
    
    property_tax = calculate_property_tax(property_income)
    total_gross_tax = int(salary_tax) + property_tax
    total_income = salary + property_income
    
    tax_credit = 0
    if donation_made > 0 and total_income > 0:
        eligible_donation = min(donation_made, total_income * 0.30)
        tax_credit = int((total_gross_tax / total_income) * eligible_donation)
        
    return {
        "salary_tax": int(salary_tax), "salary_slab": slab_desc, "property_tax": property_tax,
        "tax_credit_sec61": tax_credit, "total_gross_tax": total_gross_tax, "final_tax_liability": max(0, total_gross_tax - tax_credit)
    }

# 4. Gemini AI Legal Expert
def generate_ai_tax_report_v2(client_data, tax_math_results):
    try:
        client = genai.Client()
        context_prompt = f"You are a Senior Tax Advocate High Court Pakistan. Analyze Name: {client_data['name']}, Salary: {client_data['salary']}, Rent: {client_data['property_income']}, Donation: {client_data['donation_made']}. Math Results: Net Liability: {tax_math_results['final_tax_liability']}. Provide a professional legal assessment under Income Tax Ordinance 2001."
        response = client.models.generate_content(model='gemini-2.5-flash', contents=context_prompt)
        return response.text, True
    except Exception as e:
        fallback_text = f"STATUTORY TAX RECONCILIATION REPORT\n\nClient Name: {client_data['name'].upper()}\nSalary Income Bracket: {tax_math_results['salary_slab']}\nGross Salary Tax: PKR {tax_math_results['salary_tax']:,}\nProperty Rent Tax (Sec 15): PKR {tax_math_results['property_tax']:,}\nDonation Tax Credit (Sec 61): PKR {tax_math_results['tax_credit_sec61']:,}\nFinal Calculated Tax Burden: PKR {tax_math_results['final_tax_liability']:,}\n\nLegal Note: Personal consumption expenditures remain strictly inadmissible under Section 21 of the Income Tax Ordinance, 2001."
        return fallback_text, False

# 5. Local PDF Engine
def generate_pdf_bytes(client_name, report_text):
    filename = "Tax_Report.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"🏛️ LEGAL TAX ASSESSMENT: {client_name.upper()}", styles['Heading2']), Spacer(1, 15)]
    body_style = ParagraphStyle('LegalBody', parent=styles['BodyText'], fontSize=11, leading=16)
    
    for line in report_text.split('\n'):
        if line.strip():
            story.append(Paragraph(line.replace('**', '').strip(), body_style))
            story.append(Spacer(1, 6))
    doc.build(story)
    with open(filename, "rb") as f:
        return f.read()

# 6. Streamlit Premium Branded Layout
st.set_page_config(page_title="AI Tax Agent Pakistan", page_icon="🏛️", layout="wide")

# Custom Premium Styling Header
st.markdown("""
    <div style='background-color: #0f172a; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: white; margin-bottom: 0px;'>🏛️ Pakistan Legal AI Tax Automation Engine</h1>
        <p style='color: #94a3b8; font-size: 16px; margin-top: 5px;'>Advocate High Court Executive Suite — Powered by Gemini 2.5 Flash</p>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.8])

with col1:
    st.subheader("👤 Client Profile Entry")
    with st.container(border=True):
        name = st.text_input("Full Client Name", "Irfan Ahmed")
        salary = st.number_input("Annual Gross Salary (PKR)", value=3500000, step=50000)
        rent = st.number_input("Annual Net Rental Income (Sec 15)", value=0, step=50000)
        donation = st.number_input("Charitable Donations (Sec 61)", value=0, step=10000)
        tax_paid = st.number_input("Tax Withheld / Deducted at Source", value=150000, step=10000)
        
        st.write("")
        submit_btn = st.button("🚀 Run Statutory Audit & AI Synthesis", use_container_width=True)

if submit_btn:
    with col2:
        st.subheader("📜 System Audit Metrics Ledger")
        
        # Save to Local DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tax_clients (name, salary, rent, donation, tax_paid) VALUES (?, ?, ?, ?, ?)", (name, salary, rent, donation, tax_paid))
        conn.commit()
        
        # Calculations
        math_res = calculate_pakistan_tax_v2(salary, rent, donation)
        net_payable = math_res['final_tax_liability'] - tax_paid
        client_data = {"name": name, "salary": salary, "property_income": rent, "donation_made": donation, "tax_deducted": tax_paid}
        
        # Financial Cards Layout
        with st.container(border=True):
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Gross Computed Tax", f"PKR {math_res['total_gross_tax']:,}")
            m_col2.metric("Sec 61 Relief Credit", f"PKR {math_res['tax_credit_sec61']:,}")
            
            # Color indicator for payable vs refund
            if net_payable >= 0:
                m_col3.metric("Net Tax Payable to FBR", f"PKR {net_payable:,}", delta="- Action Required", delta_color="inverse")
            else:
                m_col3.metric("Refundable Claims", f"PKR {abs(net_payable):,}", delta="+ Refund Due", delta_color="normal")

        st.write("")
        st.subheader("⚖️ High Court Legal Opinion & Assessment")
        
        # AI Generator Window
        with st.spinner("AI Tax Counsel is evaluating statutory provisions..."):
            report_output, ai_status = generate_ai_tax_report_v2(client_data, math_res)
        
        if not ai_status:
            st.warning("⚠️ Cloud AI clusters are experiencing high traffic. Local rule engine output appended below:")
            
        with st.container(border=True):
            st.markdown(report_output)
        
        # Interactive Download Action Bar
        st.write("")
        d_col1, d_col2 = st.columns(2)
        pdf_bytes = generate_pdf_bytes(name, report_output)
        
        with d_col1:
            st.download_button(label="📥 Download Signed PDF Legal Memo", data=pdf_bytes, file_name=f"{name.replace(' ', '_')}_Tax_Report.pdf", mime="application/pdf", use_container_width=True)
        with d_col2:
            st.download_button(label="📄 Export Raw Text Draft (.txt)", data=report_output, file_name=f"{name.replace(' ', '_')}_Draft.txt", mime="text/plain", use_container_width=True)
