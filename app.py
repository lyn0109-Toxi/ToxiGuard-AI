import csv
import base64
import json
from pathlib import Path
from urllib.parse import quote, quote_plus
from urllib.request import urlopen

import streamlit as st

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


def assess_impurities(raw_text):
    origin_actions = {
        "degradation product": "Link to forced degradation pathway and stability-indicating method.",
        "raw material": "Check supplier qualification, raw material specification, and carryover control.",
        "unreacted starting material": "Confirm purge factor, process clearance, and residual starting material control.",
        "process impurity": "Assess process origin, purge strategy, and batch-to-batch trend.",
        "residual solvent": "Compare with ICH Q3C class limit and daily exposure.",
        "unknown impurity": "Identify structure, assess qualification threshold, and evaluate genotoxic alert.",
    }

    rows = []
    for line in raw_text.splitlines():
        if not line.strip() or line.lower().startswith("name,"):
            continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            continue

        code, trade_name, chemical_name, origin, observed_text, limit_text = parts[:6]
        concern = parts[6] if len(parts) > 6 else "Not specified"
        observed = to_float(observed_text)
        limit = to_float(limit_text)
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
                "Impurity Trade / Reference Name": trade_name,
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
            "Impurity Trade / Reference Name": "USP 4-Aminophenol RS",
            "Impurity Chemical Name": "4-Aminophenol",
            "Likely Origin": "Raw material or degradation product",
            "Why It Matters": "Potential carryover from synthesis and known degradation-related concern",
            "Control Strategy": "Raw material control, release/stability method, degradation pathway justification",
            "Reference Basis": "USP/EP/JP monograph preferred; verify with DMF or validated literature if compendial data are unavailable",
        },
        {
            "Reference Impurity": "4-Nitrophenol",
            "Impurity Trade / Reference Name": "4-Nitrophenol reference standard",
            "Impurity Chemical Name": "4-Nitrophenol",
            "Likely Origin": "Raw material or synthetic intermediate",
            "Why It Matters": "May indicate upstream material carryover or incomplete process clearance",
            "Control Strategy": "Supplier qualification, incoming raw material specification, purge assessment",
            "Reference Basis": "USP/EP monograph preferred; verify with literature only as supportive evidence",
        },
        {
            "Reference Impurity": "Acetanilide-related impurity",
            "Impurity Trade / Reference Name": "Acetaminophen related compound / route-specific reference",
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
            "Impurity Trade / Reference Name": "Telmisartan related compound / EP- or USP-listed reference",
            "Impurity Chemical Name": "Route-specific telmisartan related compound",
            "Likely Origin": "Process impurity",
            "Why It Matters": "May arise from coupling, cyclization, or side reaction depending on route",
            "Control Strategy": "Route-specific impurity map, purge factor, batch trend review",
            "Reference Basis": "USP/EP monograph preferred; verify exact identity with DMF or literature if needed",
        },
        {
            "Reference Impurity": "Residual starting material or intermediate",
            "Impurity Trade / Reference Name": "Route-specific intermediate reference standard",
            "Impurity Chemical Name": "Route-specific starting material or intermediate",
            "Likely Origin": "Unreacted starting material",
            "Why It Matters": "Indicates incomplete conversion or insufficient purge during manufacturing",
            "Control Strategy": "Starting material specification, process clearance, residual control",
            "Reference Basis": "USP/EP monograph preferred when available; replace with route-specific starting material name",
        },
        {
            "Reference Impurity": "Oxidative or stress degradation product",
            "Impurity Trade / Reference Name": "Stress degradation product reference",
            "Impurity Chemical Name": "Route-specific oxidative degradation product",
            "Likely Origin": "Degradation product",
            "Why It Matters": "May appear during forced degradation or long-term stability",
            "Control Strategy": "Forced degradation, stability-indicating method, shelf-life trend evaluation",
            "Reference Basis": "USP/EP monograph preferred when available; confirm under validated stability protocol",
        },
    ],
}


def load_reference_database():
    database_path = Path(__file__).with_name("impurity_reference_database.csv")
    references = {}
    if not database_path.exists():
        return references

    with database_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            api_name = row.get("api_name", "").strip().lower()
            if not api_name:
                continue
            references.setdefault(api_name, []).append(
                {
                    "Record Type": row.get("record_type", "Verification task").strip(),
                    "Verification Status": row.get(
                        "verification_status",
                        "USP/EP confirmation required",
                    ).strip(),
                    "Reference Impurity": row.get("reference_impurity", "").strip(),
                    "Impurity Trade / Reference Name": row.get(
                        "impurity_trade_name",
                        row.get("reference_impurity", ""),
                    ).strip(),
                    "Impurity Chemical Name": row.get("impurity_chemical_name", "").strip(),
                    "Likely Origin": row.get("likely_origin", "").strip(),
                    "Why It Matters": row.get("why_it_matters", "").strip(),
                    "Control Strategy": row.get("control_strategy", "").strip(),
                    "Reference Basis": row.get("reference_basis", "").strip(),
                }
            )
    return references


CSV_IMPURITY_REFERENCES = load_reference_database()


def get_impurity_references(compound_name):
    compound = compound_name.strip()
    key = compound.lower()
    if not compound:
        return []
    if key in CSV_IMPURITY_REFERENCES:
        return CSV_IMPURITY_REFERENCES[key]
    if key in KNOWN_IMPURITY_REFERENCES:
        return KNOWN_IMPURITY_REFERENCES[key]

    return [
        {
            "Record Type": "Verification task",
            "Verification Status": "No confirmed impurity name loaded",
            "Reference Impurity": "Compound-specific related-substance verification required",
            "Impurity Trade / Reference Name": "To be confirmed from USP/EP, EDQM/USP RS, or validated method",
            "Impurity Chemical Name": "To be confirmed from official monograph, reference standard, LC-MS, or validated method",
            "Likely Origin": "Potential process impurity, degradation product, raw material carryover, or unknown impurity; exact identity not confirmed",
            "Why It Matters": "This row is a verification task, not a confirmed impurity name. Compound-specific impurity profiles should be verified from authoritative references before regulatory use.",
            "Control Strategy": "Search USP/EP monograph first; confirm with official RS/CRS, DMF, validated method, forced degradation, and literature.",
            "Reference Basis": "No verified entry loaded in demo library for the searched compound.",
        }
    ]


def make_reference_search_links(compound_name):
    compound = compound_name.strip()
    if not compound:
        return []

    usp_query = quote_plus(
        f'site:doi.usp.org/USPNF "{compound}" "Related Compound" OR impurity'
    )
    usp_rs_query = quote_plus(
        f'site:usp.org/reference-standards "{compound}" "Related Compound"'
    )
    ep_query = quote_plus(
        f'site:edqm.eu OR site:crs.edqm.eu "{compound}" impurity CRS'
    )
    pubchem_query = quote_plus(f"{compound} impurity related compound")
    pubmed_query = quote_plus(f"{compound} impurity degradation product")
    google_patent_query = quote_plus(f"{compound} impurity process degradation product")

    return [
        {
            "Search Target": "USP-NF / USP monograph public search",
            "Purpose": "Check compendial related substances and official impurity references",
            "Link": f"https://www.google.com/search?q={usp_query}",
        },
        {
            "Search Target": "USP Reference Standards",
            "Purpose": "Find USP RS / related compound reference standards",
            "Link": f"https://www.google.com/search?q={usp_rs_query}",
        },
        {
            "Search Target": "EP / EDQM CRS",
            "Purpose": "Check European Pharmacopoeia CRS and impurity reference standards",
            "Link": f"https://www.google.com/search?q={ep_query}",
        },
        {
            "Search Target": "PubChem",
            "Purpose": "Check chemical identity, synonyms, and possible structures",
            "Link": f"https://pubchem.ncbi.nlm.nih.gov/#query={pubchem_query}",
        },
        {
            "Search Target": "PubMed / literature",
            "Purpose": "Search degradation, forced degradation, and impurity literature",
            "Link": f"https://pubmed.ncbi.nlm.nih.gov/?term={pubmed_query}",
        },
        {
            "Search Target": "General process impurity search",
            "Purpose": "Find public process/degradation impurity discussions",
            "Link": f"https://www.google.com/search?q={google_patent_query}",
        },
    ]


def fetch_pubchem_identity(compound_name):
    compound = compound_name.strip()
    if not compound:
        return "Not searched"

    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{quote(compound)}/property/MolecularFormula,MolecularWeight,CanonicalSMILES/JSON"
    )
    try:
        with urlopen(url, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
        props = data["PropertyTable"]["Properties"][0]
        formula = props.get("MolecularFormula", "N/A")
        mw = props.get("MolecularWeight", "N/A")
        smiles = props.get("CanonicalSMILES", "N/A")
        return f"Found: formula {formula}, MW {mw}, canonical SMILES {smiles}"
    except Exception:
        return "Not automatically confirmed; use PubChem link for manual verification"


def fetch_pubchem_compound_report(compound_name):
    compound = compound_name.strip()
    if not compound:
        return []

    try:
        cid_url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            f"{quote(compound)}/cids/JSON"
        )
        with urlopen(cid_url, timeout=4) as response:
            cid_data = json.loads(response.read().decode("utf-8"))
        cids = cid_data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            return []

        cid = cids[0]
        property_url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
            f"{cid}/property/IUPACName,MolecularFormula,MolecularWeight,CanonicalSMILES/JSON"
        )
        with urlopen(property_url, timeout=4) as response:
            property_data = json.loads(response.read().decode("utf-8"))
        props = property_data["PropertyTable"]["Properties"][0]

        synonyms_url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
            f"{cid}/synonyms/JSON"
        )
        synonyms = []
        try:
            with urlopen(synonyms_url, timeout=4) as response:
                synonyms_data = json.loads(response.read().decode("utf-8"))
            synonyms = synonyms_data["InformationList"]["Information"][0].get("Synonym", [])
        except Exception:
            synonyms = []

        return [
            {
                "Field": "Search term",
                "PubChem Result": compound,
            },
            {
                "Field": "CID",
                "PubChem Result": str(cid),
            },
            {
                "Field": "PubChem compound page",
                "PubChem Result": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
            },
            {
                "Field": "IUPAC name",
                "PubChem Result": props.get("IUPACName", "N/A"),
            },
            {
                "Field": "Molecular formula",
                "PubChem Result": props.get("MolecularFormula", "N/A"),
            },
            {
                "Field": "Molecular weight",
                "PubChem Result": str(props.get("MolecularWeight", "N/A")),
            },
            {
                "Field": "Canonical SMILES",
                "PubChem Result": props.get("CanonicalSMILES", "N/A"),
            },
            {
                "Field": "Synonyms",
                "PubChem Result": "; ".join(synonyms[:8]) if synonyms else "N/A",
            },
        ]
    except Exception:
        return [
            {
                "Field": "PubChem search status",
                "PubChem Result": "Not automatically confirmed; open PubChem link for manual review",
            }
        ]


def build_reference_search_report(compound_name):
    compound = compound_name.strip()
    if not compound:
        return []

    pubchem_status = fetch_pubchem_identity(compound)
    rows = []
    for item in make_reference_search_links(compound):
        status = "Manual verification required"
        expected_output = "Relevant reference documents or candidate impurity names"
        if item["Search Target"] == "PubChem":
            status = pubchem_status
            expected_output = "Chemical identity, synonyms, formula, molecular weight, structure"
        elif "USP" in item["Search Target"]:
            expected_output = "USP monograph, USP RS, related compound names, acceptance criteria if public"
        elif "EP" in item["Search Target"] or "EDQM" in item["Search Target"]:
            expected_output = "EP CRS / impurity reference standard candidates"
        elif "PubMed" in item["Search Target"]:
            expected_output = "Forced degradation, stability, degradation pathway, impurity literature"

        rows.append(
            {
                "Search Target": item["Search Target"],
                "Search Purpose": item["Purpose"],
                "Expected Output": expected_output,
                "Search Status": status,
                "Search Link": item["Link"],
            }
        )
    return rows


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
search_links = make_reference_search_links(compound)
search_report_rows = build_reference_search_report(compound)
pubchem_report_rows = fetch_pubchem_compound_report(compound)
if compound.strip():
    st.markdown(f"### PubChem Basic Search Result for {compound.strip()}")
    st.caption(
        "This section uses the public PubChem PUG REST service to retrieve the basic compound result."
    )
    st.table(pubchem_report_rows)

    st.markdown(f"### USP/EP Impurity Verification Workspace for {compound.strip()}")
    st.caption(
        "The searched compound is checked against the current demo reference library. "
        "Rows marked as verification tasks are not confirmed impurity names. "
        "USP/EP monographs and official reference standards should be used as the primary source."
    )
    st.info(
        "Important: A row such as 'USP/EP related-substance verification required' means "
        "the app is telling you what to verify. It is not naming an official impurity."
    )
    st.table(reference_rows)
    st.markdown("### External Reference Search Links")
    st.caption(
        "These links do not replace USP/EP verification. They are shortcuts to help find "
        "official monographs, reference standards, chemical identity, and literature."
    )
    for item in search_links:
        st.markdown(
            f"- [{item['Search Target']}]({item['Link']}) - {item['Purpose']}"
        )
    st.markdown("### Reference Search Report")
    st.caption(
        "The app prepares a structured search report for the entered compound. "
        "PubChem identity is checked automatically when network access is available; "
        "USP/EP sources still require manual verification."
    )
    st.table(search_report_rows)
else:
    st.info("Enter a compound name to check compound-specific impurity reference information.")

material_type = st.selectbox(
    "Material Type",
    ["API", "Excipient", "Impurity", "Degradation Product"],
    key="material_type",
)

purpose = st.selectbox(
    "Assessment Purpose",
    ["Early R&D", "IND", "NDA", "ANDA", "Investor Due Diligence"],
    key="purpose",
)

st.markdown("### Related Substance / Impurity Specification Comparison")
st.caption(
    "Example limits below are proposed internal specifications for demo purposes. "
    "Replace them with approved release/stability specifications, USP/EP monograph limits, "
    "or ICH qualification thresholds as appropriate."
)
st.caption(
    "Paste one impurity per line: impurity code, trade/reference name, chemical name, origin, observed %, specification %, concern. "
    "Origin examples: Degradation product, Raw material, Unreacted starting material, "
    "Process impurity, Residual solvent, Unknown impurity."
)

impurity_input = st.text_area(
    "Impurity Data",
    value=(
        "Impurity A, USP 4-Aminophenol RS, 4-Aminophenol, Degradation product, 0.08, 0.10, Genotoxic alert not identified\n"
        "Impurity B, Route-specific starting material RS, Route-specific starting material, Unreacted starting material, 0.16, 0.15, Requires qualification review\n"
        "Impurity C, Supplier raw material impurity, Supplier-related raw material impurity, Raw material, 0.04, 0.05, Supplier-related carryover\n"
        "Impurity D, Unknown related substance, Unknown related substance, Unknown impurity, 0.06, 0.05, Structure identification needed"
    ),
    height=150,
    key="impurity_input",
)

if st.button("Run Preliminary Assessment", key="run_assessment"):
    st.markdown('<div class="report">', unsafe_allow_html=True)
    st.markdown("### Preliminary Regulatory Toxicology Report")

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
    st.write(
        """
    The current signal should be interpreted through intended use, material classification,
    exposure level, impurity profile, and the credibility of the supporting model or NAMs evidence.
    """
    )

    st.markdown(f"#### PubChem Basic Search Result for {compound.strip() or 'Searched Compound'}")
    st.table(pubchem_report_rows)

    st.markdown(f"#### USP/EP Impurity Verification Workspace for {compound.strip() or 'Searched Compound'}")
    st.table(reference_rows)
    st.warning(
        "Rows marked as verification tasks are not confirmed impurity names. "
        "Reference information must be confirmed using USP/EP monographs first when available. "
        "DMF data, validated analytical methods, forced degradation studies, and peer-reviewed "
        "literature should support the compendial reference, not replace it."
    )
    if search_links:
        st.markdown("#### External Reference Search Links")
        for item in search_links:
            st.markdown(
                f"- [{item['Search Target']}]({item['Link']}) - {item['Purpose']}"
            )
    if search_report_rows:
        st.markdown("#### Automated Reference Search Report")
        st.caption(
            "This section records all reference searches prepared for the entered compound. "
            "USP/EP results must be verified from the official source before regulatory use."
        )
        st.table(search_report_rows)

    impurity_rows = assess_impurities(impurity_input)
    if impurity_rows:
        st.markdown("#### Related Substance / Impurity Specification Comparison")
        st.caption(
            "Specification basis in this demo: proposed internal limit (% area or w/w). "
            "For real use, align the basis with approved specifications, stability data, "
            "ICH Q3A/Q3B thresholds, ICH M7 acceptable intake logic, or product-specific justification."
        )
        st.table(impurity_rows)

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
    else:
        st.warning(
            "No valid impurity rows were detected. Use this format: "
            "Impurity A, USP 4-Aminophenol RS, 4-Aminophenol, Degradation product, 0.08, 0.10, Genotoxic alert not identified"
        )

    st.markdown("#### Recommended Next Steps")
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
