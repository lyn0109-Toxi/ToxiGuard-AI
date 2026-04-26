import base64
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ToxiGuard AI", page_icon="TG", layout="wide")


def image_to_data_uri(path):
    if not path.exists():
        return ""
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(path.suffix.lower(), "image/png")
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


app_dir = Path(__file__).parent
genotoxicity_image = next(
    (
        app_dir / filename
        for filename in [
            "genotoxicity.png",
            "genotoxicity.jpg",
            "genotoxicity.jpeg",
            "genotoxicity.webp",
        ]
        if (app_dir / filename).exists()
    ),
    app_dir / "genotoxicity.png",
)
genotoxicity_uri = image_to_data_uri(genotoxicity_image)
genotoxicity_style = (
    f"background-image:url('{genotoxicity_uri}');"
    if genotoxicity_uri
    else ""
)

st.markdown("""
<style>
.stApp { background:#ffffff; color:#111827; }
.block-container { max-width:1180px; padding-top:2rem; }
.topbar {
    border-bottom:1px solid #d9e2ef;
    padding-bottom:16px;
    margin-bottom:40px;
    display:flex;
    justify-content:space-between;
}
.brand { font-size:42px; font-weight:950; color:#002060; letter-spacing:0; }
.nav { color:#5b6575; font-weight:650; }
.hero {
    display:grid;
    grid-template-columns:1.15fr .85fr;
    gap:42px;
    align-items:center;
    margin-bottom:50px;
}
.kicker {
    color:#0070c0;
    font-size:13px;
    font-weight:900;
    text-transform:uppercase;
    letter-spacing:.08em;
}
.hero h1 {
    font-size:58px;
    line-height:1.05;
    margin:14px 0 18px 0;
    color:#111827;
}
.hero-brand {
    font-size:86px;
    line-height:.92;
    font-weight:950;
    color:#002060;
    margin:10px 0 18px 0;
}
.hero-brand span {
    color:#bb3e33;
}
.red { color:#bb3e33; }
.hero p {
    font-size:21px;
    line-height:1.55;
    color:#374151;
}
.panel {
    background:#002060;
    color:white;
    padding:32px;
    border-radius:6px;
}
.panel h3 {
    color:white;
    font-size:30px;
    line-height:1.15;
    margin-top:0;
}
.panel-row {
    border-top:1px solid rgba(255,255,255,.25);
    padding:16px 0;
}
.panel-row b { color:#fff2cc; }
.genotox-screen {
    position:relative;
    min-height:430px;
    overflow:hidden;
    border-radius:8px;
    background:#06101f;
    box-shadow:0 24px 50px rgba(0,32,96,.28);
}
.genotox-photo {
    position:absolute;
    inset:-20px;
    background:
        radial-gradient(circle at 30% 20%, rgba(255,255,255,.16), transparent 24%),
        radial-gradient(circle at 76% 66%, rgba(187,62,51,.42), transparent 30%),
        linear-gradient(145deg, #001538 0%, #002060 46%, #07111f 100%);
    background-size:cover;
    background-position:center;
    transform:scale(1.04);
    animation:imageBreath 10s ease-in-out infinite;
    filter:saturate(1.08) contrast(1.05);
}
.genotox-screen:after {
    content:"";
    position:absolute;
    inset:0;
    background:
        linear-gradient(90deg, rgba(0,32,96,.62) 0%, rgba(0,32,96,.08) 46%, rgba(0,0,0,.35) 100%),
        radial-gradient(circle at 42% 42%, transparent 0%, rgba(0,0,0,.16) 55%, rgba(0,0,0,.62) 100%);
    z-index:2;
}
.genotox-title {
    position:absolute;
    top:24px;
    left:26px;
    right:26px;
    z-index:4;
    color:white;
}
.genotox-title h3 {
    color:white;
    font-size:30px;
    line-height:1.12;
    margin:0 0 8px 0;
}
.genotox-title p {
    color:#cfe4ff;
    font-size:15px;
    line-height:1.4;
    margin:0;
}
.dna-wrap {
    position:absolute;
    left:50%;
    top:55%;
    width:210px;
    height:310px;
    transform:translate(-50%,-50%) rotate(-18deg);
    animation:floatDna 5.5s ease-in-out infinite;
}
.dna-strand {
    position:absolute;
    top:0;
    width:18px;
    height:100%;
    border-radius:50%;
    border-left:4px solid rgba(255,255,255,.88);
}
.dna-strand.left { left:44px; }
.dna-strand.right {
    right:44px;
    border-left:0;
    border-right:4px solid rgba(255,255,255,.88);
}
.rung {
    position:absolute;
    left:56px;
    width:98px;
    height:4px;
    background:#9edbff;
    border-radius:99px;
    box-shadow:0 0 12px rgba(158,219,255,.85);
    animation:pulseRung 2.2s ease-in-out infinite;
}
.rung:nth-child(3){ top:38px; transform:rotate(18deg); }
.rung:nth-child(4){ top:78px; transform:rotate(-14deg); animation-delay:.2s; background:#fff2cc; }
.rung:nth-child(5){ top:118px; transform:rotate(16deg); animation-delay:.4s; }
.rung:nth-child(6){ top:158px; transform:rotate(-16deg); animation-delay:.6s; background:#ffb4a8; }
.rung:nth-child(7){ top:198px; transform:rotate(15deg); animation-delay:.8s; }
.rung:nth-child(8){ top:238px; transform:rotate(-14deg); animation-delay:1s; background:#fff2cc; }
.damage {
    position:absolute;
    width:16px;
    height:16px;
    border-radius:50%;
    background:#ff3b30;
    box-shadow:0 0 0 8px rgba(255,59,48,.14), 0 0 26px rgba(255,59,48,.95);
    animation:damageBlink 1.2s ease-in-out infinite;
}
.damage.one { left:147px; top:175px; }
.damage.two { left:62px; top:92px; animation-delay:.45s; }
.scanline {
    position:absolute;
    left:0;
    right:0;
    height:3px;
    top:0;
    background:linear-gradient(90deg, transparent, #fff2cc, transparent);
    box-shadow:0 0 18px rgba(255,242,204,.95);
    animation:scan 3.8s linear infinite;
    z-index:3;
}
.particle {
    position:absolute;
    width:7px;
    height:7px;
    border-radius:50%;
    background:#9edbff;
    opacity:.75;
    animation:particleDrift 7s linear infinite;
}
.particle.p1 { left:12%; top:68%; animation-delay:0s; }
.particle.p2 { left:78%; top:30%; animation-delay:1.1s; background:#fff2cc; }
.particle.p3 { left:68%; top:82%; animation-delay:2.1s; }
.particle.p4 { left:22%; top:38%; animation-delay:3.1s; background:#ffb4a8; }
.genotox-caption {
    position:absolute;
    left:24px;
    right:24px;
    bottom:22px;
    z-index:4;
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
}
.mini-signal {
    background:rgba(255,255,255,.1);
    border:1px solid rgba(255,255,255,.24);
    color:white;
    padding:12px;
    font-size:13px;
    line-height:1.3;
}
.mini-signal b { color:#fff2cc; }
@keyframes floatDna {
    0%,100% { transform:translate(-50%,-50%) rotate(-18deg) scale(1); }
    50% { transform:translate(-50%,-54%) rotate(-12deg) scale(1.04); }
}
@keyframes pulseRung {
    0%,100% { opacity:.58; }
    50% { opacity:1; }
}
@keyframes damageBlink {
    0%,100% { transform:scale(.86); opacity:.65; }
    50% { transform:scale(1.22); opacity:1; }
}
@keyframes scan {
    0% { transform:translateY(0); opacity:0; }
    10% { opacity:1; }
    90% { opacity:1; }
    100% { transform:translateY(430px); opacity:0; }
}
@keyframes particleDrift {
    0% { transform:translateY(28px) translateX(0); opacity:0; }
    20% { opacity:.85; }
    100% { transform:translateY(-140px) translateX(34px); opacity:0; }
}
@keyframes imageBreath {
    0%,100% { transform:scale(1.04) translate3d(0,0,0); }
    45% { transform:scale(1.13) translate3d(-18px, -10px, 0); }
    70% { transform:scale(1.09) translate3d(14px, 8px, 0); }
}
.big-question {
    font-size:42px;
    font-weight:950;
    line-height:1.12;
    margin:8px 0 16px 0;
}
.body-large {
    font-size:18px;
    line-height:1.65;
    color:#374151;
    max-width:930px;
}
.service-grid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:18px;
    margin:26px 0 44px 0;
}
.service {
    border-top:6px solid #0070c0;
    padding:22px 20px;
    box-shadow:0 14px 30px rgba(17,24,39,.08);
    min-height:200px;
}
.service:nth-child(2) { border-top-color:#bb3e33; }
.service h3 { color:#002060; font-size:23px; }
.service p { color:#5b6575; line-height:1.5; }
.pathway {
    display:grid;
    grid-template-columns:repeat(4,1fr);
    border:1px solid #d9e2ef;
    margin:22px 0 44px 0;
}
.step {
    padding:22px;
    border-right:1px solid #d9e2ef;
}
.step:last-child {
    border-right:0;
    background:#fff2cc;
}
.step b {
    color:#bb3e33;
    display:block;
    font-size:13px;
    margin-bottom:10px;
}
.step span {
    font-size:18px;
    font-weight:850;
    color:#111827;
}
.assessment {
    border:2px solid #002060;
    padding:28px;
    background:#f8fbff;
    margin-bottom:42px;
}
.report {
    border-left:7px solid #bb3e33;
    background:white;
    padding:24px;
    margin-top:24px;
    box-shadow:0 14px 28px rgba(17,24,39,.08);
}
div.stButton > button {
    background:#bb3e33;
    color:white;
    border:0;
    border-radius:4px;
    font-weight:850;
}
@media(max-width:900px){
    .hero,.service-grid,.pathway{grid-template-columns:1fr;}
    .hero h1{font-size:42px;}
    .hero-brand{font-size:58px;}
    .brand{font-size:32px;}
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="topbar">
    <div class="brand">ToxiGuard AI</div>
    <div class="nav">In silico toxicology | NAMs | ICH/FDA strategy</div>
</div>

<section class="hero">
    <div>
        <div class="kicker">Regulatory trust, not just prediction</div>
        <div class="hero-brand">ToxiGuard <span>AI</span></div>
        <h1>Can your toxicity signal become a <span class="red">regulatory decision</span>?</h1>
        <p>
        ToxiGuard AI translates AI/QSAR toxicity signals, NAMs evidence,
        and read-across outputs into regulatory-ready interpretation for
        pharmaceutical development teams.
        </p>
    </div>
    <div class="genotox-screen">
        <div class="genotox-photo" style="{genotoxicity_style}"></div>
        <div class="scanline"></div>
        <div class="particle p1"></div>
        <div class="particle p2"></div>
        <div class="particle p3"></div>
        <div class="particle p4"></div>
        <div class="genotox-title">
            <h3>Genotoxicity signal monitor</h3>
            <p>DNA damage alerts, QSAR signals, and explainability evidence move together toward regulatory interpretation.</p>
        </div>
        <div class="genotox-caption">
            <div class="mini-signal"><b>Question 1</b><br>What does the toxicity signal mean?</div>
            <div class="mini-signal"><b>Outcome</b><br>From early signal to submission strategy.</div>
        </div>
    </div>
</section>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kicker">What We Do</div>
<div class="big-question">Prediction alone is not enough.</div>
<p class="body-large">
AI toxicity prediction is becoming more important in pharmaceutical development,
but the business value comes from interpretation. We help teams understand whether
a signal is scientifically credible, whether it creates regulatory risk, and what
evidence should come next.
</p>
""", unsafe_allow_html=True)

st.markdown("""
<div class="service-grid">
    <div class="service">
        <h3>In Silico Toxicity Assessment</h3>
        <p>Preliminary toxicity review for APIs, excipients, impurities, and degradation products.</p>
    </div>
    <div class="service">
        <h3>ICH M7 Impurity Review</h3>
        <p>Mutagenic impurity risk interpretation focused on classification, exposure, and justification.</p>
    </div>
    <div class="service">
        <h3>Regulatory Data Gap Analysis</h3>
        <p>Convert scientific uncertainty into practical IND, NDA, ANDA, or due diligence next steps.</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kicker">How It Works</div>
<div class="big-question">From compound input to regulatory pathway.</div>
<div class="pathway">
    <div class="step"><b>01 INPUT</b><span>Compound, SMILES, material type</span></div>
    <div class="step"><b>02 SCREEN</b><span>QSAR, NAMs, read-across review</span></div>
    <div class="step"><b>03 INTERPRET</b><span>Toxicity concern and regulatory relevance</span></div>
    <div class="step"><b>04 DECIDE</b><span>Data gap, next study, submission strategy</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="assessment">', unsafe_allow_html=True)
st.markdown("## Start Preliminary Toxicity Assessment")
st.caption("Demo only. Final regulatory decisions require qualified expert review.")

compound = st.text_input("Compound Name", key="compound_name")
smiles = st.text_input("SMILES", key="smiles")

material_type = st.selectbox(
    "Material Type",
    ["API", "Excipient", "Impurity", "Degradation Product"],
    key="material_type"
)

purpose = st.selectbox(
    "Assessment Purpose",
    ["Early R&D", "IND", "NDA", "ANDA", "Investor Due Diligence"],
    key="purpose"
)

if st.button("Run Preliminary Assessment", key="run_assessment"):
    st.markdown('<div class="report">', unsafe_allow_html=True)
    st.markdown("### Preliminary Regulatory Toxicology Report")
    st.write(f"**Compound:** {compound if compound else 'Not provided'}")
    st.write(f"**SMILES:** {smiles if smiles else 'Not provided'}")
    st.write(f"**Material Type:** {material_type}")
    st.write(f"**Assessment Purpose:** {purpose}")

    st.markdown("#### Predicted Toxicity Concerns")
    st.write("""
    - Mutagenicity: Low preliminary concern unless structural alerts are identified
    - Genotoxicity: Low preliminary concern; confirm with QSAR evidence package
    - Carcinogenicity: Exposure-dependent concern requiring longer-term context
    - Hepatotoxicity: Further review recommended based on class and exposure
    - Reproductive toxicity: Data gap remains unless supported by analog evidence
    """)

    st.markdown("#### Regulatory Interpretation")
    st.write("""
    The current signal should be interpreted through intended use, material classification,
    exposure level, impurity profile, and the credibility of the supporting model or NAMs evidence.
    """)

    st.markdown("#### Recommended Next Steps")
    st.write("""
    1. Review QSAR outputs from VEGA, OECD QSAR Toolbox, or equivalent tools
    2. Document model applicability domain and explainability
    3. Conduct impurity profiling and degradation product assessment
    4. Prepare ICH M7-based justification if relevant
    5. Consider confirmatory Ames testing if structural alerts remain unresolved
    """)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("## Request a Consultation")

name = st.text_input("Name", key="contact_name")
company = st.text_input("Company", key="contact_company")
email = st.text_input("Email", key="contact_email")
project = st.text_area("Compound / Project Description", key="contact_project")

if st.button("Submit Request", key="submit_request"):
    st.success("Thank you. Your request has been received.")
    st.write(f"Name: {name}")
    st.write(f"Company: {company}")
    st.write(f"Email: {email}")
    st.write(f"Project: {project}")

st.markdown("---")
st.caption(
    "ToxiGuard AI is an early-stage decision-support concept for in silico toxicology, "
    "NAMs interpretation, and regulatory strategy."
)
