import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import io

# --- CONFIGURATION (FALLBACK) ---
# These load only if no external file is uploaded
DEFAULT_KNOWLEDGE_BASE = {
    "meta_info": {"version": "1.0", "last_updated": "2025-11-20"},
    "anti_patterns": [
        {
            "id": "BP-01",
            "name": "Outdated Items (Zombie Tickets)",
            "category": "Product Backlog",
            "severity": "Medium",
            "description": "Items that haven't been touched for months create noise.",
            "detection_logic": {"field": "Updated", "operator": "older_than_days", "threshold": 90},
            "remedy": "Review in 'Anti-Product Backlog' and delete if no longer valuable."
        },
        {
            "id": "BP-02",
            "name": "Missing Acceptance Criteria",
            "category": "Product Backlog",
            "severity": "High",
            "description": "Stories without clear finish lines lead to scope creep.",
            "detection_logic": {"field": "Acceptance Criteria", "operator": "is_empty", "threshold": 0},
            "remedy": "Define criteria during refinement. Use Gherkin syntax."
        },
        {
            "id": "SE-01",
            "name": "Sprint Stuffing",
            "category": "Sprint Execution",
            "severity": "High",
            "description": "Adding too much scope after Sprint start.",
            "detection_logic": {"field": "Created", "operator": "created_after_sprint_start", "threshold": 0},
            "remedy": "Monitor scope change. Only swap items of equal size."
        },
        {
            "id": "SP-01",
            "name": "Oversized Item (INVEST)",
            "category": "Sprint Planning",
            "severity": "Medium",
            "description": "Item is too big to finish in one sprint.",
            "detection_logic": {"field": "Story Points", "operator": "greater_than", "threshold": 13},
            "remedy": "Split the story using 'Hamburger' or 'Spider' method."
        }
    ]
}

# Mock User Database
USERS = {
    "coach": "admin123",
    "sm": "scrum123"
}

# --- HELPER FUNCTIONS ---

def load_knowledge_base():
    if "knowledge_base" not in st.session_state:
        st.session_state["knowledge_base"] = DEFAULT_KNOWLEDGE_BASE
    return st.session_state["knowledge_base"]

def save_knowledge_base(new_kb):
    st.session_state["knowledge_base"] = new_kb
    st.success("Knowledge Base Updated Successfully!")

def check_login(username, password):
    if username in USERS and USERS[username] == password:
        return True
    return False

def generate_sample_data():
    data = {
        "Issue Key": ["EQS-101", "EQS-102", "EQS-103", "EQS-104", "EQS-105"],
        "Summary": ["Setup Cloud Env", "Login Page", "Fix Typos", "Huge Migration", "Urgent Fix"],
        "Status": ["To Do", "In Progress", "Done", "To Do", "In Progress"],
        "Updated": [
            (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        ],
        "Created": [
            (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        ],
        "Story Points": [5, 8, 1, 20, 3],
        "Acceptance Criteria": ["Defined", "", "Fixed", "Defined", "Defined"]
    }
    return pd.DataFrame(data)

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- PAGES ---

def login_page():
    st.title("🔐 EQS Agile Intelligence Platform")
    st.markdown("### AI Virtual Scrum Master (AVSM v2.0)")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if check_login(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = "Admin" if username == "coach" else "User"
                st.rerun()
            else:
                st.error("Invalid credentials.")

def admin_page():
    st.header("⚙️ Knowledge Base Management")
    st.info("Agile Coaches can update logic here without changing code.")
    
    kb = load_knowledge_base()
    
    # 1. Download Current Logic (JSON)
    st.subheader("1. Export Current Logic")
    st.download_button(
        label="📥 Download Rules (JSON)",
        data=json.dumps(kb, indent=2),
        file_name="avsm_rules.json",
        mime="application/json"
    )

    # 2. Upload New Logic (JSON)
    st.subheader("2. Upload New Logic")
    uploaded_rules = st.file_uploader("Upload updated JSON file", type="json")
    if uploaded_rules is not None:
        if st.button("Update System Logic"):
            try:
                new_kb = json.load(uploaded_rules)
                save_knowledge_base(new_kb)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.subheader("Current Active Rules")
    st.dataframe(pd.DataFrame(kb["anti_patterns"])[["name", "category", "severity"]])

def analysis_page():
    st.header("🔍 AVSM Analysis Engine")
    
    # Data Loader
    data_source = st.radio("Select Data Source:", ["Use Sample Data (Demo)", "Upload CSV"])
    
    df = None
    if data_source == "Use Sample Data (Demo)":
        df = generate_sample_data()
        st.info("Loaded sample dataset with 5 simulated items.")
    else:
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
    
    if df is not None:
        with st.expander("View Raw Data"):
            st.dataframe(df)
            
        if st.button("🚀 Run AVSM Analysis"):
            run_analysis_engine(df)

def run_analysis_engine(df):
    kb = load_knowledge_base()
    violations = []
    
    st.divider()
    st.subheader("📋 Analysis Report")
    
    # Logic Engine
    for rule in kb["anti_patterns"]:
        logic = rule["detection_logic"]
        field = logic["field"]
        
        if field not in df.columns:
            continue
            
        flagged_items = []
        
        if logic["operator"] == "older_than_days":
            df["temp_date"] = pd.to_datetime(df[field], errors='coerce')
            cutoff = datetime.now() - timedelta(days=logic["threshold"])
            flagged_items = df[df["temp_date"] < cutoff]
            
        elif logic["operator"] == "is_empty":
            flagged_items = df[df[field].isnull() | (df[field] == "")]
            
        elif logic["operator"] == "greater_than":
            flagged_items = df[df[field] > logic["threshold"]]
            
        elif logic["operator"] == "created_after_sprint_start":
            df["temp_created"] = pd.to_datetime(df[field], errors='coerce')
            sprint_start = datetime.now() - timedelta(days=5)
            flagged_items = df[df["temp_created"] > sprint_start]

        if len(flagged_items) > 0:
            for idx, row in flagged_items.iterrows():
                violations.append({
                    "Issue": row.get("Issue Key", "Unknown"),
                    "Summary": row.get("Summary", "Unknown"),
                    "Anti-Pattern": rule["name"],
                    "Severity": rule["severity"],
                    "Recommendation": rule["remedy"]
                })

    if not violations:
        st.success("No issues found!")
    else:
        # Scorecard
        score = max(0, 100 - (len(violations) * 10))
        c1, c2 = st.columns(2)
        c1.metric("Agile Health Score", f"{score}/100")
        c2.metric("Issues Found", len(violations))
        
        # Visual Report
        for v in violations:
            st.error(f"**{v['Anti-Pattern']}** ({v['Severity']})")
            st.write(f"📌 {v['Issue']}: {v['Summary']}")
            st.caption(f"💡 Remedy: {v['Recommendation']}")
            st.divider()
            
        # DOWNLOAD BUTTON (The New Feature)
        st.subheader("📥 Export Report")
        df_violations = pd.DataFrame(violations)
        csv = convert_df_to_csv(df_violations)
        
        st.download_button(
            label="Download Report as CSV",
            data=csv,
            file_name="avsm_report.csv",
            mime="text/csv",
        )

# --- MAIN ---
def main():
    st.set_page_config(page_title="AVSM v2", layout="wide")
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        st.sidebar.title("🤖 AVSM v2.0")
        
        # Check if username exists in session_state before accessing it
        username = st.session_state.get('username', 'Unknown User')
        st.sidebar.write(f"User: {username}")
        
        menu = ["Analyze Backlog"]
        if st.session_state.get("role") == "Admin":
            menu.append("Configure Rules (Admin)")
        
        choice = st.sidebar.radio("Menu", menu)
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.rerun()
            
        if choice == "Analyze Backlog": analysis_page()
        elif choice == "Configure Rules (Admin)": admin_page()

if __name__ == "__main__":
    main()
