import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import io
import re

# --- 1. CENTRALIZED UI CONFIGURATION (Single Source of Truth) ---
APP_CONSTANTS = {
    "APP_TITLE": "Agile Anti-Pattern Scanner v3.0",
    "APP_CAPTION": "Powered by 'The Scrum Anti-Patterns Guide'",
    "LOGO_URL": "https://cdn-icons-png.flaticon.com/512/1087/1087815.png",
    "LOGO_LINK": "https://www.scrum.org",
    "BTN_RUN": "🚀 Run Analysis",
    "BTN_DOWNLOAD": "📥 Download Remediation Report",
    "HEADER_RESULTS": "🔍 Analysis Results",
    "MSG_SUCCESS": "✅ Amazing! No anti-patterns detected in this dataset.",
    "MSG_LOCKED": "🔒 Custom Rules Locked (Admin Only)",
    "MSG_DEMO": "🚀 Use Demo Data (No file needed)"
}

# --- 2. EMBEDDED DEMO DATA ---
DEMO_DATA_CSV = """Issue Key,Summary,Description,Status,Sprint,Story Points,Acceptance Criteria,Created,Updated
PROJ-101,Fix the login button,Fix the login button,To Do,Sprint 10,3,User can click login,2025-11-01,2025-11-10
PROJ-102,Stabilization Phase,Ensure the build is stable before release,To Do,Sprint 10 Hardening,8,No critical bugs,2025-11-01,2025-11-15
PROJ-103,Legacy Database Migration,Migrate SQL to NoSQL architecture,Backlog,,13,Data integrity verified,2022-05-20,2023-01-15
PROJ-104,User Profile Update,Allow users to change their avatar,To Do,Sprint 10,5,,2025-11-05,2025-11-18
PROJ-105,Rewrite Entire Frontend,Rewrite the entire application in React,To Do,Sprint 10,40,Pixel perfect match,2025-11-01,2025-11-15
PROJ-106,Urgent Marketing Color Change,Change the banner to red,To Do,Sprint 10,1,Banner is red,2025-11-21,2025-11-21
PROJ-107,Bug fix,Fixing the null pointer exception,To Do,Sprint 10,2,No crash,2025-11-01,2025-11-15
PROJ-108,Search Bar Logic,Implement fuzzy search algorithm,In Progress,Sprint 10,5,Returns relevant results,2025-11-01,2025-11-01
PROJ-109,Valid Feature,As a user I want to logout so that I am secure,Done,Sprint 10,3,Session is cleared,2025-11-01,2025-11-20
PROJ-110,Sprint 0 Setup,Set up servers and Jira project,To Do,Sprint 0,5,Servers running,2025-11-01,2025-11-10
PROJ-111,Server,Setup the server environments,To Do,Sprint 10,3,Env is live,2025-11-01,2025-11-01
PROJ-112,Investigate API Latency,Looking into why the API takes 2000ms,In Progress,Sprint 10,5,Root cause identified,2025-11-01,2025-11-05
PROJ-113,Refactor Entire Backend,Complete overhaul of microservices architecture,To Do,Sprint 10,21,,2025-11-01,2025-11-01
PROJ-114,New CEO Request,Add a flying animation to the logo,To Do,Sprint 10,2,Animation works,2025-11-20,2025-11-20
PROJ-115,Update Wiki,Documentation needs updating for v1.0,Backlog,,1,Wiki updated,2024-01-01,2024-01-01
PROJ-116,Technical Debt Cleanup,Remove unused libraries and comments,To Do,Sprint 11 Cleanup,5,Libs removed,2025-11-01,2025-11-01
PROJ-117,Check logs,Check logs,To Do,Sprint 10,1,Logs checked,2025-11-01,2025-11-01
PROJ-118,Big Data Migration,Move all petabytes to S3 buckets,In Progress,Sprint 10,100,All data moved,2025-11-01,2025-11-01
PROJ-119,Valid User Story,As admin I want to ban users so I can moderate,To Do,Sprint 10,3,Ban button functions,2025-11-01,2025-11-21
PROJ-120,Another Valid Story,As user I want to reset password,To Do,Sprint 10,5,Email sent,2025-11-01,2025-11-21"""

# --- 3. RULES CONFIGURATION ---
DEFAULT_KNOWLEDGE_BASE = {
    "meta_info": {"version": "3.0", "source": "The Scrum Anti-Patterns Guide"},
    "anti_patterns": [
        {
            "id": "PO-01",
            "name": "Copy & Paste Product Owner",
            "category": "Product Owner",
            "severity": "Medium",
            "description": "PO creates items by simply copying the title into the description, adding no value (Source: Ch 2).",
            "detection_logic": {"field": "Summary", "operator": "fields_are_identical", "threshold": "Description"},
            "remedy": "Refine items collaboratively to ensure shared understanding and avoid 'ticket monkey' behavior."
        },
        {
            "id": "SP-03",
            "name": "The 'Hardening' Sprint",
            "category": "Sprint Planning",
            "severity": "High",
            "description": "There is no such thing as a hardening Sprint in Scrum. Quality should be built in (Source: Ch 5).",
            "detection_logic": {"field": "Sprint", "operator": "text_contains_regex", "threshold": ["Hardening", "Stabilization", "Cleanup", "Sprint 0"]},
            "remedy": "Ensure the Definition of Done is met every Sprint. Do not defer quality work."
        },
        {
            "id": "BP-01",
            "name": "Outdated Items (Zombie Tickets)",
            "category": "Product Backlog",
            "severity": "Medium",
            "description": "Items that haven't been touched for months create noise (Source: Ch 10).",
            "detection_logic": {"field": "Updated", "operator": "older_than_days", "threshold": 90},
            "remedy": "Review in 'Anti-Product Backlog' and delete if no longer valuable."
        },
        {
            "id": "BP-02",
            "name": "Missing Acceptance Criteria",
            "category": "Product Backlog",
            "severity": "High",
            "description": "Stories without clear finish lines lead to scope creep (Source: Ch 10).",
            "detection_logic": {"field": "Acceptance Criteria", "operator": "is_empty", "threshold": 0},
            "remedy": "Define criteria during refinement. Use Gherkin syntax."
        },
        {
            "id": "SP-01",
            "name": "Oversized Item (INVEST)",
            "category": "Sprint Planning",
            "severity": "Medium",
            "description": "Item is too big to finish in one sprint (Source: Ch 11).",
            "detection_logic": {"field": "Story Points", "operator": "greater_than", "threshold": 13},
            "remedy": "Split the story using 'Hamburger' or 'Spider' method."
        },
        {
            "id": "ST-01",
            "name": "Scope Creep (Flow Disruption)",
            "category": "Stakeholders",
            "severity": "High",
            "description": "Work added after the sprint started disrupts flow (Source: Ch 1).",
            "detection_logic": {"field": "Created", "operator": "created_after_sprint_start", "threshold": 0},
            "remedy": "Stakeholders must respect the Sprint Goal. Urgent work replaces existing work, not adds to it."
        },
        {
            "id": "BP-03",
            "name": "Vague Summary (Too Short)",
            "category": "Quality",
            "severity": "High",
            "description": "One-liner stories often hide complexity.",
            "detection_logic": {"field": "Summary", "operator": "word_count_less_than", "threshold": 4},
            "remedy": "Rewrite summary to follow 'As a... I want... So that...' format."
        },
        {
            "id": "SP-02",
            "name": "Stagnant Work (Fake Progress)",
            "category": "Sprint Execution",
            "severity": "High",
            "description": "Item marked 'In Progress' but hasn't moved in days.",
            "detection_logic": {"field": "Updated", "operator": "days_since_last_update", "threshold": 5},
            "remedy": "Swarm the problem or move back to backlog if blocked."
        }
    ]
}

# --- 4. MOCK USER DATABASE ---
USERS = {
    "coach": "admin123",       # ADMIN: Can edit rules and run analysis
    "sm": "scrum123",          # USER: Can run analysis only
    "developer": "code4life",  # USER: Can run analysis only
    "po": "value99"            # USER: Can run analysis only
}

# --- 5. HELPER FUNCTIONS ---

def load_rules(uploaded_rules_file):
    """Loads rules from uploaded file or falls back to default."""
    if uploaded_rules_file is not None:
        try:
            return json.load(uploaded_rules_file)
        except Exception as e:
            st.error(f"Error reading JSON file: {e}")
            return DEFAULT_KNOWLEDGE_BASE
    return DEFAULT_KNOWLEDGE_BASE

def check_login(username, password):
    if username in USERS and USERS[username] == password:
        return True
    return False

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def render_brand_header():
    """Renders the consistent Logo and Title for all pages using APP_CONSTANTS."""
    # Sidebar Logo
    try:
        st.logo(APP_CONSTANTS["LOGO_URL"], link=APP_CONSTANTS["LOGO_LINK"])
    except AttributeError:
        pass

    # Main Page Logo
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        st.image(APP_CONSTANTS["LOGO_URL"], width=200)
    
    # Titles
    st.markdown(f"<h1 style='text-align: center;'>{APP_CONSTANTS['APP_TITLE']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: grey;'>{APP_CONSTANTS['APP_CAPTION']}</p>", unsafe_allow_html=True)

# --- 6. LOGIC ENGINE ---

def apply_rules(df, rules_json):
    """Applies rules to DataFrame and returns violations."""
    violations = []
    date_cols = ['Updated', 'Created', 'Resolved']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    for rule in rules_json["anti_patterns"]:
        logic = rule["detection_logic"]
        field = logic["field"]
        
        if field not in df.columns:
            # Exception for days_since_last_update which needs Status too
            if logic["operator"] != "days_since_last_update":
                continue
            elif logic["operator"] == "days_since_last_update" and "Status" not in df.columns:
                continue
            
        flagged_rows = pd.DataFrame()
        
        # Logic Blocks
        if logic["operator"] == "older_than_days":
            if field in df.columns:
                cutoff = datetime.now() - timedelta(days=logic["threshold"])
                flagged_rows = df[df[field] < cutoff]
        elif logic["operator"] == "is_empty":
            flagged_rows = df[df[field].isnull() | (df[field] == "") | (df[field].astype(str).str.strip() == "")]
        elif logic["operator"] == "greater_than":
            df[field] = pd.to_numeric(df[field], errors='coerce')
            flagged_rows = df[df[field] > logic["threshold"]]
        elif logic["operator"] == "created_after_sprint_start":
            sprint_start = datetime.now() - timedelta(days=5)
            flagged_rows = df[df[field] > sprint_start]
        elif logic["operator"] == "word_count_greater_than":
            flagged_rows = df[df[field].astype(str).apply(lambda x: len(x.split())) > logic["threshold"]]
        elif logic["operator"] == "word_count_less_than":
            non_empty = df[df[field].notna() & (df[field].astype(str).str.strip() != "")]
            flagged_rows = non_empty[non_empty[field].astype(str).apply(lambda x: len(x.split())) < logic["threshold"]]
        elif logic["operator"] == "days_since_last_update":
            if "Status" in df.columns and field in df.columns:
                in_progress = df[df["Status"] == "In Progress"]
                cutoff = datetime.now() - timedelta(days=logic["threshold"])
                flagged_rows = in_progress[in_progress[field] < cutoff]
        elif logic["operator"] == "contains_text":
            flagged_rows = df[df[field].astype(str).str.contains(str(logic["threshold"]), case=False, na=False)]
        elif logic["operator"] == "fields_are_identical":
            target_field = logic["threshold"] 
            if field in df.columns and target_field in df.columns:
                flagged_rows = df[
                    (df[field].notna()) & 
                    (df[target_field].notna()) & 
                    (df[field].astype(str).str.strip() == df[target_field].astype(str).str.strip())
                ]
        elif logic["operator"] == "text_contains_regex":
            bad_keywords = [x.lower() for x in logic["threshold"]]
            pattern = '|'.join(bad_keywords)
            flagged_rows = df[
                df[field].astype(str).str.lower().str.contains(pattern, na=False, regex=True)
            ]

        if not flagged_rows.empty:
            for idx, row in flagged_rows.iterrows():
                violations.append({
                    "Issue Key": row.get("Issue Key", "Unknown"),
                    "Summary": row.get("Summary", "Unknown"),
                    "Anti-Pattern": rule["name"],
                    "Category": rule["category"],
                    "Severity": rule["severity"],
                    "Violation Reason": rule["description"],
                    "Suggested Remedy": rule["remedy"]
                })
                
    return violations

# --- 7. PAGE FUNCTIONS ---

def login_page():
    render_brand_header()

    # Instructions
    with st.container():
        st.markdown("---")
        st.markdown("### 👋 Welcome!")
        st.info("""
        **How to use this tool:**
        1. **Login** with your team credentials (see below).
        2. **Upload** your backlog CSV file (or use our Demo Data).
        3. **Review** the automated report for process smells like 'Hardening Sprints' or 'Zombie Tickets'.
        """)
        
        with st.expander("ℹ️ Available Demo Accounts"):
            st.markdown("""
            * **Admin/Coach:** `coach` / `admin123` (Can edit Rules)
            * **Scrum Master:** `sm` / `scrum123` (Read-only Rules)
            * **Developer:** `developer` / `code4life` (Read-only Rules)
            * **Product Owner:** `po` / `value99` (Read-only Rules)
            """)

    st.markdown("### Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if check_login(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid credentials.")

def analysis_page():
    render_brand_header()
    
    # Identify User Role
    current_user = st.session_state.get("username", "unknown")
    is_admin = current_user == "coach"
    
    # Display Welcome Message
    if is_admin:
        st.success(f"Welcome, Coach! You have **Admin** access to configure rules.")
    else:
        st.info(f"Welcome, {current_user}. You are in **Viewer** mode (Default Rules Only).")

    st.markdown("Upload your Jira/ADO export (CSV) to detect anti-patterns defined in *The Scrum Anti-Patterns Guide*.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Configuration")
        
        if is_admin:
            st.info("Upload Custom Rules (Admin Only)")
            uploaded_rules = st.file_uploader("Upload Custom Rules (JSON)", type="json")
            current_rules = load_rules(uploaded_rules)
        else:
            st.warning(APP_CONSTANTS["MSG_LOCKED"])
            current_rules = DEFAULT_KNOWLEDGE_BASE
        
        with st.expander("View Active Rules"):
            st.json(current_rules)

    with col2:
        st.subheader("2. Backlog Data")
        
        # Demo Data Logic
        if "use_demo_data" not in st.session_state:
            st.session_state["use_demo_data"] = False

        uploaded_data = st.file_uploader("Upload Data (CSV)", type="csv")
        
        if st.button(APP_CONSTANTS["MSG_DEMO"]):
            st.session_state["use_demo_data"] = True
            st.rerun()

        if uploaded_data is not None:
            st.session_state["use_demo_data"] = False

        if st.session_state["use_demo_data"] and uploaded_data is None:
            st.success("Using Embedded Demo Dataset")

    st.divider()

    # Load Data
    df = None
    if uploaded_data is not None:
        try:
            df = pd.read_csv(uploaded_data)
        except Exception as e:
            st.error(f"Error reading uploaded CSV: {e}")
    elif st.session_state["use_demo_data"]:
        try:
            df = pd.read_csv(io.StringIO(DEMO_DATA_CSV))
        except Exception as e:
            st.error(f"Error reading demo data: {e}")

    # Analysis & Results
    if df is not None:
        st.write(f"**Data Preview:** {len(df)} items loaded.")
        st.dataframe(df.head(3))
        
        if st.button(APP_CONSTANTS["BTN_RUN"]):
            results = apply_rules(df, current_rules)
            
            if results:
                st.subheader(APP_CONSTANTS["HEADER_RESULTS"])
                st.write(f"**Found {len(results)} Violations**")
                
                result_df = pd.DataFrame(results)
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("High Severity", len(result_df[result_df['Severity'] == 'High']))
                m2.metric("Medium Severity", len(result_df[result_df['Severity'] == 'Medium']))
                m3.metric("Categories Affected", result_df['Category'].nunique())

                st.dataframe(result_df)
                
                csv_data = convert_df_to_csv(result_df)
                st.download_button(
                    label=APP_CONSTANTS["BTN_DOWNLOAD"],
                    data=csv_data,
                    file_name="agile_remediation_plan.csv",
                    mime="text/csv"
                )
            else:
                st.success(APP_CONSTANTS["MSG_SUCCESS"])

# --- 8. MAIN ---
def main():
    st.set_page_config(page_title="Agile Scanner", layout="wide")
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        st.sidebar.title("Menu")
        st.sidebar.write(f"User: {st.session_state.get('username')}")
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.rerun()
            
        analysis_page()

if __name__ == "__main__":
    main()
