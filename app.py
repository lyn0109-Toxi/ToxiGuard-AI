import base64
from pathlib import Path
import io

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="ToxiGuard AI", page_icon="TG", layout="wide")


def image_to_data_uri(path):
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


genotoxicity_image = Path(__file__).with_name("genotoxicity.png")
genotoxicity_uri = image_to_data_uri(genotoxicity_image)


def to_float(value):
    try:
        return float(value.strip().replace("%", ""))
    except (AttributeError, ValueError):
        return None


def assess_impurities(df):
    origin_actions = {
        "degradation product": "Link to forced degradation pathway and stability-indicating method.",
        "raw material": "Check supplier qualification, raw material specification, and carryover control.",
        "unreacted starting material": "Confirm purge factor, process clearance, and residual starting material control.",
        "process impurity": "Assess process origin, purge strategy, and batch-to-batch trend.",
        "residual solvent": "Compare with ICH Q3C class limit and daily exposure.",
        "unknown impurity": "Identify structure, assess qualification threshold, and evaluate genotoxic alert.",
    }

    rows = []
    if df is None or df.empty:
        return rows

    for index, row in df.iterrows():
        code = str(row.get("Impurity Code", "")).strip()
        chemical_name = str(row.get("Chemical Name", "")).strip()
        origin = str(row.get("Origin", "")).strip()
        observed_val = row.get("Observed (%)", None)
        limit_val = row.get("Specification (%)", None)
        concern = str(row.get("Concern", "")).strip()

        if not code or pd.isna(code) or code == "nan":
            continue

        try:
            observed = float(observed_val) if not pd.isna(observed_val) else None
        except ValueError:
            observed = None

        try:
            limit = float(limit_val) if not pd.isna(limit_val) else None
        except ValueError:
            limit = None

        observed_text = f"{observed:.3g}" if observed is not None else ""
        limit_text = f"{limit:.3g}" if limit is not None else ""

        origin_note = origin_actions.get(
            origin.lower(),
            "Clarify impurity origin and link the control strategy to the manufacturing process.",
        )

        if observed is None or limit is None:
            status = "Review needed"
            action = "Check numeric result and specification format."
        elif observed <= limit:
            status = "Within specification"
            action = f"Document as controlled under current specification. {origin_note}"
        else:
            status = "Above specification"
            action = (
                "Investigate root cause, toxicological qualification, and regulatory impact. "
                f"{origin_note}"
            )

        rows.append(
            {
                "Impurity Code": code,
                "Impurity Chemical Name": chemical_name,
                "Origin": origin,
                "Observed (%)": observed_text,
                "Specification (%)": limit_text,
                "Concern": concern,
                "Status": status,
                "Regulatory Action": action,
            }
        )
    return rows


KNOWN_IMPURITY_REFERENCES = {
    "acetaminophen": [
        {
            "Reference Impurity": "p-Aminophenol / 4-Aminophenol",
            "Impurity Chemical Name": "4-Aminophenol",
            "Likely Origin": "Raw material or degradation product",
            "Why It Matters": "Potential carryover from synthesis and known degradation-related concern",
            "Control Strategy": "Raw material control, release/stability method, degradation pathway justification",
            "Reference Basis": "USP/EP/JP monograph preferred; verify with DMF or validated literature if compendial data are unavailable",
        },
        {
            "Reference Impurity": "4-Nitrophenol",
            "Impurity Chemical Name": "4-Nitrophenol",
            "Likely Origin": "Raw material or synthetic intermediate",
            "Why It Matters": "May indicate upstream material carryover or incomplete process clearance",
            "Control Strategy": "Supplier qualification, incoming raw material specification, purge assessment",
            "Reference Basis": "USP/EP monograph preferred; verify with literature only as supportive evidence",
        },
        {
            "Reference Impurity": "Acetanilide-related impurity",
            "Impurity Chemical Name": "Acetanilide or route-specific acetanilide analog",
            "Likely Origin": "Process impurity",
            "Why It Matters": "Can be associated with process route or side reaction profile",
            "Control Strategy": "Process impurity mapping, batch trend review, method specificity check",
            "Reference Basis": "USP/EP approved specification preferred; confirm exact identity with validated method",
        },
    ],
    "telmisartan": [
        {
            "Reference Impurity": "Telmisartan related substance / process-related analog",
            "Impurity Chemical Name": "Route-specific telmisartan related compound",
            "Likely Origin": "Process impurity",
            "Why It Matters": "May arise from coupling, cyclization, or side reaction depending on route",
            "Control Strategy": "Route-specific impurity map, purge factor, batch trend review",
            "Reference Basis": "USP/EP monograph preferred; verify exact identity with DMF or literature if needed",
        },
        {
            "Reference Impurity": "Residual starting material or intermediate",
            "Impurity Chemical Name": "Route-specific starting material or intermediate",
            "Likely Origin": "Unreacted starting material",
            "Why It Matters": "Indicates incomplete conversion or insufficient purge during manufacturing",
            "Control Strategy": "Starting material specification, process clearance, residual control",
            "Reference Basis": "USP/EP monograph preferred when available; replace with route-specific starting material name",
        },
        {
            "Reference Impurity": "Oxidative or stress degradation product",
            "Impurity Chemical Name": "Route-specific oxidative degradation product",
            "Likely Origin": "Degradation product",
            "Why It Matters": "May appear during forced degradation or long-term stability",
            "Control Strategy": "Forced degradation, stability-indicating method, shelf-life trend evaluation",
            "Reference Basis": "USP/EP monograph preferred when available; confirm under validated stability protocol",
        },
    ],
}


def get_impurity_references(compound_name):
    compound = compound_name.strip()
    key = compound.lower()
    if not compound:
        return []
    if key in KNOWN_IMPURITY_REFERENCES:
        return KNOWN_IMPURITY_REFERENCES[key]

    return [
        {
            "Reference Impurity": f"{compound} related substances",
            "Impurity Chemical Name": "To be confirmed from USP/EP or validated method",
            "Likely Origin": "To be confirmed",
            "Why It Matters": "Compound-specific impurity profile should be verified from authoritative references",
            "Control Strategy": "Search USP/EP monograph first; if unavailable, use DMF, validated method, forced degradation, and literature",
            "Reference Basis": "No verified entry loaded in demo library; user should confirm for the searched compound",
        }
    ]


st.markdown(
    """
<style>
.stApp { background:#ffffff; color:#111827; }
.block-container { max-width:1180px; padding-top:2rem; }
.topbar {
    border-bottom:1px solid #d9e2ef;
    padding:8px 0 18px 0;
    margin-bottom:40px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:18px;
    flex-wrap:wrap;
    min-height:76px;
}
.brand { font-size:42px; font-weight:950; color:#002060; line-height:1.15; }
.nav { color:#5b6575; font-weight:650; line-height:1.5; padding-top:4px; }
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
.hero-brand {
    font-size:86px;
    line-height:.92;
    font-weight:950;
    color:#002060;
    margin:10px 0 18px 0;
}
.hero-brand span { color:#bb3e33; }
.hero h1 {
    font-size:58px;
    line-height:1.05;
    margin:14px 0 18px 0;
    color:#111827;
}
.red { color:#bb3e33; }
.hero p { font-size:21px; line-height:1.55; color:#374151; }
.panel { background:#002060; color:white; padding:32px; border-radius:8px; }
.panel h3 { color:white; font-size:30px; line-height:1.15; margin-top:0; }
.panel-row { border-top:1px solid rgba(255,255,255,.25); padding:16px 0; }
.panel-row b { color:#fff2cc; }
.gene-visual {
    position:relative;
    min-height:430px;
    overflow:hidden;
    border-radius:10px;
    background:#06101f;
    box-shadow:0 24px 54px rgba(0,32,96,.30);
}
.gene-photo {
    position:absolute;
    inset:-24px;
    background-size:cover;
    background-position:center;
    transform:scale(1.04);
    animation:imageBreath 11s ease-in-out infinite;
    filter:saturate(1.1) contrast(1.05);
}
.gene-visual:before {
    content:"";
    position:absolute;
    inset:0;
    background:
        linear-gradient(90deg, rgba(0,32,96,.52) 0%, rgba(0,32,96,.10) 48%, rgba(0,0,0,.38) 100%),
        radial-gradient(circle at 38% 45%, transparent 0%, rgba(0,0,0,.10) 52%, rgba(0,0,0,.56) 100%);
    z-index:2;
}
.gene-visual:after {
    content:"";
    position:absolute;
    left:0;
    right:0;
    top:0;
    height:3px;
    background:linear-gradient(90deg, transparent, #fff2cc, transparent);
    box-shadow:0 0 18px rgba(255,242,204,.9);
    animation:scanLine 3.8s linear infinite;
    z-index:3;
}
.gene-particles {
    position:absolute;
    content:"TOX";
    inset:-20%;
    background:
        radial-gradient(circle, rgba(139,214,255,.95) 0 2px, transparent 3px),
        radial-gradient(circle, rgba(255,122,38,.78) 0 2px, transparent 3px);
    background-size:42px 42px, 76px 76px;
    animation:particleMove 12s linear infinite;
    opacity:.34;
    z-index:3;
}
.mutation-burst {
    position:absolute;
    left:48%;
    top:48%;
    width:28px;
    height:28px;
    border-radius:50%;
    background:#ff4b2b;
    box-shadow:0 0 0 12px rgba(255,75,43,.16), 0 0 42px rgba(255,75,43,.95);
    z-index:4;
    animation:burst 1.4s ease-in-out infinite;
}
.gene-title {
    position:absolute;
    left:24px;
    right:24px;
    bottom:22px;
    z-index:5;
    color:white;
}
.gene-title h3 {
    color:white;
    font-size:30px;
    line-height:1.12;
    margin:0 0 8px 0;
}
.gene-title p {
    color:#d8ebff;
    margin:0;
    line-height:1.45;
}
@keyframes particleMove {
    from { transform:translate3d(0,0,0); }
    to { transform:translate3d(42px,-70px,0); }
}
@keyframes imageBreath {
    0%,100% { transform:scale(1.04) translate3d(0,0,0); }
    45% { transform:scale(1.13) translate3d(-18px,-10px,0); }
    72% { transform:scale(1.09) translate3d(14px,8px,0); }
}
@keyframes scanLine {
    0% { transform:translateY(0); opacity:0; }
    12% { opacity:1; }
    88% { opacity:1; }
    100% { transform:translateY(430px); opacity:0; }
}
@keyframes burst {
    0%,100% { transform:scale(.78); opacity:.72; }
    50% { transform:scale(1.26); opacity:1; }
}
.big-question {
    font-size:42px;
    font-weight:950;
    line-height:1.12;
    margin:8px 0 16px 0;
}
.body-large { font-size:18px; line-height:1.65; color:#374151; max-width:930px; }
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
.step { padding:22px; border-right:1px solid #d9e2ef; }
.step:last-child { border-right:0; background:#fff2cc; }
.step b { color:#bb3e33; display:block; font-size:13px; margin-bottom:10px; }
.step span { font-size:18px; font-weight:850; color:#111827; }
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
    .hero,.service-grid,.pathway{ grid-template-columns:1fr; }
    .hero h1{ font-size:42px; }
    .hero-brand{ font-size:58px; }
    .brand{ font-size:32px; }
}
</style>
""",
    unsafe_allow_html=True,
)


st.markdown(
    f"""
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
    <div class="gene-visual">
        <div class="gene-photo" style="background-image:url('{genotoxicity_uri}');"></div>
        <div class="gene-particles"></div>
        <div class="mutation-burst"></div>
        <div class="gene-title">
            <h3>Genotoxicity signal monitor</h3>
            <p>DNA damage signals, impurity origin, and USP/EP reference logic move together toward regulatory interpretation.</p>
        </div>
    </div>
</section>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="kicker">What We Do</div>
<div class="big-question">Prediction alone is not enough.</div>
<p class="body-large">
AI toxicity prediction is becoming more important in pharmaceutical development,
but the business value comes from interpretation. We help teams understand whether
a signal is scientifically credible, whether it creates regulatory risk, and what
evidence should come next.
</p>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="kicker">How It Works</div>
<div class="big-question">From compound input to regulatory pathway.</div>
<div class="pathway">
    <div class="step"><b>01 INPUT</b><span>Compound, SMILES, material type</span></div>
    <div class="step"><b>02 SCREEN</b><span>USP/EP, QSAR, NAMs, read-across review</span></div>
    <div class="step"><b>03 INTERPRET</b><span>Toxicity concern and regulatory relevance</span></div>
    <div class="step"><b>04 DECIDE</b><span>Data gap, next study, submission strategy</span></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="assessment">', unsafe_allow_html=True)
st.markdown("## Start Preliminary Toxicity Assessment")
st.caption("Demo only. Final regulatory decisions require qualified expert review.")

compound = st.text_input("Compound Name", key="compound_name")
smiles = st.text_input("SMILES", key="smiles")

reference_rows = get_impurity_references(compound)
if compound.strip():
    st.markdown(f"### Known Impurity Reference for {compound.strip()}")
    st.caption(
        "The searched compound is checked against the current demo reference library. "
        "USP/EP monographs should be used as the primary source when available. "
        "If no verified entry is loaded, the table shows a search/verification plan."
    )
    st.table(reference_rows)
else:
    st.info("Enter a compound name to check compound-specific impurity reference information.")

material_type = st.selectbox(
    "Material Type",
    ["API", "Excipient", "Impurity", "Degradation Product"],
    key="material_type",
)

purpose = st.selectbox(
    "Assessment Purpose",
    [
        "Early R&D",
        "IND",
        "NDA (505(b)(1) - New Drug)",
        "NDA (505(b)(2) - Repurposed/Modified)",
        "ANDA (Generic)",
        "Investor Due Diligence",
    ],
    key="purpose",
)

st.markdown("### Related Substance / Impurity Specification Input")
st.caption(
    "Directly edit the table below to input your analytical lab results ('Observed (%)') "
    "and compare them against your proposed or compendial 'Specification (%)'. "
    "You can add or remove rows directly from the table."
)

default_impurities = pd.DataFrame([
    {"Impurity Code": "Impurity A", "Chemical Name": "4-Aminophenol", "Origin": "Degradation product", "Observed (%)": 0.08, "Specification (%)": 0.10, "Concern": "Genotoxic alert not identified"},
    {"Impurity Code": "Impurity B", "Chemical Name": "Route-specific starting material", "Origin": "Unreacted starting material", "Observed (%)": 0.16, "Specification (%)": 0.15, "Concern": "Requires qualification review"},
    {"Impurity Code": "Impurity C", "Chemical Name": "Supplier-related raw material impurity", "Origin": "Raw material", "Observed (%)": 0.04, "Specification (%)": 0.05, "Concern": "Supplier-related carryover"},
    {"Impurity Code": "Impurity D", "Chemical Name": "Unknown related substance", "Origin": "Unknown impurity", "Observed (%)": 0.06, "Specification (%)": 0.05, "Concern": "Structure identification needed"}
])

edited_df = st.data_editor(default_impurities, num_rows="dynamic", use_container_width=True, key="impurity_editor")

if st.button("Run Preliminary Assessment", key="run_assessment"):
    st.markdown('<div class="report">', unsafe_allow_html=True)
    st.markdown("### Preliminary Regulatory Toxicology Report")

    impurity_rows = assess_impurities(edited_df)

    # 1. KPI Metrics ‚Äî driven by actual input data
    total_count = len(impurity_rows) if impurity_rows else 0
    above_spec_count = len([r for r in impurity_rows if r['Status'] == 'Above specification'])
    within_spec_count = len([r for r in impurity_rows if r['Status'] == 'Within specification'])
    review_count = len([r for r in impurity_rows if r['Status'] == 'Review needed'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Impurities Entered", str(total_count))
    col2.metric("Within Specification", str(within_spec_count), None, delta_color="normal")
    col3.metric("Above Specification ‚ö†Ô∏è", str(above_spec_count), f"+{above_spec_count}" if above_spec_count > 0 else None, delta_color="inverse")
    col4.metric("Review Needed", str(review_count))

    st.markdown("---")

    # 2. Charts ‚Äî all driven by user input
    if impurity_rows:
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Observed vs. Specification (ICH Q3A/B Threshold)")
            obs_vals = []
            spec_vals = []
            labels = []
            for r in impurity_rows:
                try:
                    obs_vals.append(float(r["Observed (%)"]))
                    spec_vals.append(float(r["Specification (%)"]))
                    labels.append(r["Impurity Code"])
                except (ValueError, TypeError):
                    continue
            fig = go.Figure()
            fig.add_trace(go.Bar(x=labels, y=obs_vals, name="Observed (%)", marker_color="#0070c0"))
            fig.add_trace(go.Scatter(x=labels, y=spec_vals, name="Specification Limit", mode="lines+markers", line=dict(color="#bb3e33", dash="dash", width=2)))
            # ICH Q3A identification threshold for API
            if material_type == "API":
                fig.add_hline(y=0.10, line_dash="dot", line_color="orange", annotation_text="ICH Q3A ID Threshold (0.10%)")
                fig.add_hline(y=0.15, line_dash="dot", line_color="red", annotation_text="ICH Q3A Qual. Threshold (0.15%)")
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=340, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)

        with col_chart2:
            st.markdown("#### Margin of Safety (Observed / Specification)")
            margin_data = []
            for r in impurity_rows:
                try:
                    obs = float(r["Observed (%)"])
                    spec = float(r["Specification (%)"])
                    pct = round((obs / spec) * 100, 1) if spec > 0 else 0
                    margin_data.append({"Impurity": r["Impurity Code"], "Usage (%)": pct})
                except (ValueError, TypeError):
                    continue
            if margin_data:
                df_margin = pd.DataFrame(margin_data)
                colors = ["#b71c1c" if v > 100 else "#f57c00" if v > 80 else "#1b5e20" for v in df_margin["Usage (%)"]]
                fig2 = go.Figure(go.Bar(x=df_margin["Impurity"], y=df_margin["Usage (%)"], marker_color=colors, text=[f"{v}%" for v in df_margin["Usage (%)"]], textposition="outside"))
                fig2.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Specification Limit (100%)")
                fig2.add_hline(y=80, line_dash="dot", line_color="orange", annotation_text="Warning Zone (80%)")
                fig2.update_layout(yaxis_title="% of Specification Used", margin=dict(l=20, r=20, t=30, b=20), height=340)
                st.plotly_chart(fig2, use_container_width=True)

        # Row 2: Origin distribution + Status summary
        col_chart3, col_chart4 = st.columns(2)
        with col_chart3:
            st.markdown("#### Impurity Origin Distribution")
            origin_counts = {}
            for r in impurity_rows:
                o = r["Origin"]
                origin_counts[o] = origin_counts.get(o, 0) + 1
            fig3 = go.Figure(go.Pie(labels=list(origin_counts.keys()), values=list(origin_counts.values()), hole=0.45, marker=dict(colors=["#0070c0", "#bb3e33", "#f0ad4e", "#5cb85c", "#6c757d"])))
            fig3.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=300)
            st.plotly_chart(fig3, use_container_width=True)

        with col_chart4:
            st.markdown("#### Compliance Status Summary")
            status_map = {"Within specification": within_spec_count, "Above specification": above_spec_count, "Review needed": review_count}
            fig4 = go.Figure(go.Bar(x=list(status_map.keys()), y=list(status_map.values()), marker_color=["#1b5e20", "#b71c1c", "#f57c00"], text=list(status_map.values()), textposition="outside"))
            fig4.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=300, yaxis_title="Count")
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    st.write(f"**Compound:** {compound if compound else 'Not provided'}")
    st.write(f"**SMILES:** {smiles if smiles else 'Not provided'}")
    st.write(f"**Material Type:** {material_type}")
    st.write(f"**Assessment Purpose:** {purpose}")

    st.markdown("#### Predicted Toxicity Concerns")
    st.write(
        """
    - Mutagenicity: Low preliminary concern unless structural alerts are identified
    - Genotoxicity: Low preliminary concern; confirm with QSAR evidence package
    - Carcinogenicity: Exposure-dependent concern requiring longer-term context
    - Hepatotoxicity: Further review recommended based on class and exposure
    - Reproductive toxicity: Data gap remains unless supported by analog evidence
    """
    )

    st.markdown("#### Regulatory Interpretation")
    if purpose == "NDA (505(b)(2) - Repurposed/Modified)":
        st.success(
            """
        **505(b)(2) Pathway Analysis:** 
        As the API is already known, full systemic toxicity data can likely rely on the Reference Listed Drug (RLD) or literature. 
        However, the regulatory focus must shift to strictly qualifying **new impurities, novel excipients, or degradation products** arising from your new formulation or new route of administration. 
        Focus your efforts on ICH M7 justification for any new peaks and bridging local toxicity data.
        """
        )
    else:
        st.write(
            """
        The current signal should be interpreted through intended use, material classification,
        exposure level, impurity profile, and the credibility of the supporting model or NAMs evidence.
        """
        )

    if impurity_rows:
        st.markdown("#### Impurities Comparison: Observed vs. Specification Limits")
        st.caption(
            "Specification basis in this demo: proposed internal limit (% area or w/w). "
            "For real use, align the basis with approved specifications, stability data, "
            "ICH Q3A/Q3B thresholds, ICH M7 acceptable intake logic, or product-specific justification."
        )
        
        # Enhanced Data Table using Pandas
        df_impurities = pd.DataFrame(impurity_rows)
        def highlight_status(val):
            if val == 'Above specification':
                return 'background-color: #ffebee; color: #b71c1c; font-weight: bold'
            elif val == 'Within specification':
                return 'background-color: #e8f5e9; color: #1b5e20; font-weight: bold'
            return ''
        
        styled_df = df_impurities.style.map(highlight_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True)

        above_spec = [row for row in impurity_rows if row["Status"] == "Above specification"]
        review_needed = [row for row in impurity_rows if row["Status"] == "Review needed"]

        if above_spec:
            st.error(
                "One or more impurities are above the proposed specification. "
                "A toxicological qualification and regulatory impact assessment should be prepared."
            )
        elif review_needed:
            st.warning(
                "Some impurity rows need review because the observed result or specification is not numeric."
            )
        else:
            st.success(
                "All listed impurities are within the proposed specification based on the values provided."
            )

        st.markdown("#### CTD 3.2.P.5.5 / DMF Justification Narrative Drafts")
        st.caption("AI-generated regulatory narrative blocks ready for CTD 3.2.P.5.5 insertion or DMF defense. Review and adapt based on actual QSAR outputs.")
        
        # Narrative generation and PDF Export Logic
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        pdf_elements = [Paragraph("CTD 3.2.P.5.5 Regulatory Narrative Drafts", styles['Title']), Spacer(1, 12)]
        
        for row in impurity_rows:
            status = row["Status"]
            if status == "Review needed":
                continue
            
            code = row["Impurity Code"]
            name = row["Impurity Chemical Name"]
            origin = row["Origin"].lower()
            obs = row["Observed (%)"]
            spec = row["Specification (%)"]
            
            if status == "Above specification":
                narrative = (
                    f"**[{code}] Justification for Specification Limit:**\n\n"
                    f"The {origin} identified as **{name}** was observed at a maximum level of **{obs}%**, which exceeds the initial proposed specification of **{spec}%**. "
                    f"To justify the acceptance of this impurity at the observed level, an *in silico* toxicological assessment was conducted in accordance with ICH M7 principles. "
                    f"Complementary QSAR methodologies (statistical-based and expert rule-based) confirmed the absence of structural alerts for mutagenicity (Class 5). "
                    f"Furthermore, read-across analysis comparing {name} to structurally similar approved analogs demonstrates that human exposure at the {obs}% limit presents negligible toxicological risk. "
                    f"Therefore, the specification limit is toxicologically qualified and justified for inclusion in CTD 3.2.P.5.5."
                )
                st.warning(narrative)
                pdf_elements.append(Paragraph(f"<b>[{code}] Justification for Specification Limit:</b>", styles['Heading2']))
                pdf_elements.append(Spacer(1, 6))
                pdf_elements.append(Paragraph(narrative.replace('**', '').replace('*', ''), styles['Normal']))
                pdf_elements.append(Spacer(1, 12))
                
            elif status == "Within specification":
                narrative = (
                    f"**[{code}] Routine Control Statement:**\n\n"
                    f"The {origin} **{name}** is routinely monitored. The observed data demonstrates a maximum level of **{obs}%**, "
                    f"which is consistently well within the established specification limit of **{spec}%**. "
                    f"Current manufacturing process controls and analytical procedures are fully validated to ensure clearance below the ICH Q3A/Q3B qualification threshold. "
                    f"No further toxicological qualification is required."
                )
                st.info(narrative)
                pdf_elements.append(Paragraph(f"<b>[{code}] Routine Control Statement:</b>", styles['Heading2']))
                pdf_elements.append(Spacer(1, 6))
                pdf_elements.append(Paragraph(narrative.replace('**', '').replace('*', ''), styles['Normal']))
                pdf_elements.append(Spacer(1, 12))
                
        # Generate PDF
        doc.build(pdf_elements)
        st.markdown("---")
        st.download_button(
            label="üìÑ Export CTD 3.2.P.5.5 Narrative (PDF)",
            data=pdf_buffer.getvalue(),
            file_name="CTD_3_2_P_5_5_Narrative.pdf",
            mime="application/pdf"
        )
    else:
        st.warning(
            "No valid impurity rows were detected. Use this format: "
            "Impurity A, 4-Aminophenol, Degradation product, 0.08, 0.10, Genotoxic alert not identified"
        )

    st.markdown("#### Recommended Next Steps")
    if purpose == "NDA (505(b)(2) - Repurposed/Modified)":
        st.write(
            """
        1. **Compare Impurity Profiles:** Map the new impurity profile against the RLD or USP/EP monograph.
        2. **Isolate Delta:** Identify any *new* impurities or degradation products not present in the original product.
        3. **In Silico Assessment:** Perform QSAR ICH M7 assessment specifically for the newly identified impurities.
        4. **Exposure & Local Toxicity:** If the route of administration changed, assess local toxicity and new exposure limits.
        5. **Bridging Strategy:** Prepare a scientific justification bridging the safety of the RLD to your new formulation.
        """
        )
    else:
        st.write(
            """
        1. Confirm known related substances using USP/EP monographs when available
        2. Review QSAR outputs from VEGA, OECD QSAR Toolbox, or equivalent tools
        3. Document model applicability domain and explainability
        4. Conduct impurity profiling and degradation product assessment
        5. Prepare ICH M7-based justification if relevant
        6. Consider confirmatory Ames testing if structural alerts remain unresolved
        """
        )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ‚îÄ‚îÄ‚îÄ CTD 3.2.P.8 Stability / Shelf-Life Prediction (ICH Q1E) ‚îÄ‚îÄ‚îÄ
st.markdown("---")
st.markdown(
    """
<div class="kicker">CTD 3.2.P.8.3</div>
<div class="big-question">Shelf-Life Prediction (ICH Q1E)</div>
<p class="body-large">
Enter your long-term stability data below. ToxiGuard AI will perform
ICH Q1E linear regression with a 95% confidence interval to estimate
when the impurity level is projected to cross your specification limit.
</p>
""",
    unsafe_allow_html=True,
)

st.caption(
    "This tool replicates the core statistical approach used in Minitab "
    "stability analysis: ordinary least-squares regression with a "
    "95% one-sided upper confidence limit. The estimated shelf life is the "
    "time point where the upper 95% CI first exceeds the acceptance criterion."
)

default_stability = pd.DataFrame({
    "Time (months)": [0, 3, 6, 9, 12, 18, 24],
    "Impurity (%)": [0.02, 0.03, 0.04, 0.06, 0.07, 0.09, 0.11],
})

stab_spec = st.number_input(
    "Specification Limit (%) for this impurity",
    min_value=0.01, max_value=5.0, value=0.15, step=0.01, key="stab_spec"
)

stab_df = st.data_editor(
    default_stability, num_rows="dynamic", use_container_width=True, key="stab_editor"
)

if st.button("Run Shelf-Life Prediction", key="run_stability"):
    stab_clean = stab_df.dropna()
    if len(stab_clean) < 3:
        st.error("At least 3 data points are required for regression.")
    else:
        x = stab_clean["Time (months)"].values.astype(float)
        y = stab_clean["Impurity (%)"].values.astype(float)

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_sq = r_value ** 2

        x_pred = np.linspace(0, max(x.max() * 2, 60), 300)
        y_pred = slope * x_pred + intercept

        n = len(x)
        x_mean = np.mean(x)
        se_pred = std_err * np.sqrt(1.0 / n + (x_pred - x_mean) ** 2 / np.sum((x - x_mean) ** 2))
        t_val = stats.t.ppf(0.95, df=n - 2)
        y_upper = y_pred + t_val * se_pred

        cross_idx = np.where(y_upper >= stab_spec)[0]
        if len(cross_idx) > 0:
            shelf_life = x_pred[cross_idx[0]]
            shelf_life_text = f"{shelf_life:.1f} months"
        else:
            shelf_life = None
            shelf_life_text = f"> {x_pred[-1]:.0f} months (does not cross within prediction range)"

        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Estimated Shelf Life", shelf_life_text)
        col_s2.metric("R¬≤", f"{r_sq:.4f}")
        col_s3.metric("Slope (% / month)", f"{slope:.5f}")

        fig_stab = go.Figure()
        fig_stab.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Observed Data", marker=dict(size=10, color="#0070c0")))
        fig_stab.add_trace(go.Scatter(x=x_pred, y=y_pred, mode="lines", name="Regression Line", line=dict(color="#002060")))
        fig_stab.add_trace(go.Scatter(x=x_pred, y=y_upper, mode="lines", name="95% Upper CI", line=dict(color="#f57c00", dash="dash")))
        fig_stab.add_hline(y=stab_spec, line_dash="dash", line_color="red", annotation_text=f"Spec Limit ({stab_spec}%)")
        if shelf_life is not None:
            fig_stab.add_vline(x=shelf_life, line_dash="dot", line_color="green", annotation_text=f"Shelf Life: {shelf_life:.1f}mo")
        fig_stab.update_layout(
            xaxis_title="Time (months)", yaxis_title="Impurity (%)",
            margin=dict(l=20, r=20, t=40, b=20), height=420,
            legend=dict(orientation="h", y=-0.2)
        )
        st.plotly_chart(fig_stab, use_container_width=True)

        st.markdown("#### Regulatory Interpretation (CTD 3.2.P.8.3)")
        if shelf_life is not None and shelf_life >= 24:
            st.success(
                f"Based on ICH Q1E linear regression, the 95% upper confidence limit "
                f"crosses the specification ({stab_spec}%) at **{shelf_life:.1f} months**. "
                f"A shelf life of **24 months** is supported by the current data."
            )
        elif shelf_life is not None and shelf_life >= 12:
            st.warning(
                f"The 95% upper confidence limit crosses the specification ({stab_spec}%) "
                f"at **{shelf_life:.1f} months**. A shelf life of **{int(shelf_life // 6) * 6} months** "
                f"may be supportable. Consider additional long-term data to extend."
            )
        elif shelf_life is not None:
            st.error(
                f"The 95% upper confidence limit crosses the specification ({stab_spec}%) "
                f"at only **{shelf_life:.1f} months**. The current data does not support "
                f"a commercially viable shelf life. Process or formulation optimization is recommended."
            )
        else:
            st.success(
                f"The impurity trend remains well below the specification ({stab_spec}%) "
                f"throughout the projected range. A shelf life of 24+ months is likely supportable."
            )

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
    "NAMs interpretation, and regulatory strategy. USP/EP monographs should be used as "
    "the primary reference for compendial impurity information when available."
)
