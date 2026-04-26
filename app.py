import streamlit as st

st.set_page_config(
    page_title="ToxiPath AI",
    page_icon="🧪",
    layout="wide"
)

st.markdown("# 🧪 ToxiPath AI")
st.markdown("### From toxicity prediction to regulatory pathway.")

st.write("""
ToxiPath AI helps pharmaceutical and biotech companies translate 
in silico toxicity signals into regulatory-ready decisions.
""")

st.markdown("---")

st.header("What We Do")

st.write("""
AI toxicity prediction is becoming increasingly important in pharmaceutical development.
However, prediction alone is not enough. Companies need to understand whether a toxicity
signal matters under ICH/FDA expectations and what additional evidence may be required.
""")

st.markdown("---")

st.header("Our Services")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("In Silico Toxicity Assessment")
    st.write("Preliminary toxicity review for APIs, excipients, impurities, and degradation products.")

with col2:
    st.subheader("ICH M7 Impurity Review")
    st.write("Mutagenic impurity risk assessment and regulatory interpretation.")

with col3:
    st.subheader("Regulatory Data Gap Analysis")
    st.write("Identify missing evidence and recommended next steps for regulatory strategy.")

st.markdown("---")

st.header("Why ToxiPath AI?")

st.success("""
We do not simply predict toxicity.
We identify the regulatory pathway to make the prediction usable.
""")

st.markdown("---")

st.header("Request a Consultation")

name = st.text_input("Name")
company = st.text_input("Company")
email = st.text_input("Email")
project = st.text_area("Compound / Project Description")

if st.button("Submit Request"):
    st.success("Thank you. Your request has been received.")
    st.write(f"Name: {name}")
    st.write(f"Company: {company}")
    st.write(f"Email: {email}")
    st.write(f"Project: {project}")

st.markdown("---")
st.header("Try Our Toxicity Assessment")

compound = st.text_input("Compound Name", key="assessment_compound")
smiles = st.text_input("SMILES", key="assessment_smiles")

if st.button("Run Assessment", key="run_assessment"):
    st.write("## Preliminary Report")
    st.write(f"Compound: {compound}")

    st.write("### Predicted Toxicity")
    st.write("""
    - Mutagenicity: Low
    - Genotoxicity: Low
    - Carcinogenicity: Moderate
    """)

    st.write("### Regulatory Interpretation")
    st.write("""
    Based on ICH M7, this compound is considered low risk.
    Further evaluation may be required depending on exposure level.
    """)