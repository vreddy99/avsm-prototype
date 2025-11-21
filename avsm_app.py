import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import io

# --- CONFIGURATION & STATE MANAGEMENT ---
# In a real app, this would be a database. Here we use Session State for the prototype.

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
    "coach": "admin123",  # The Agile Expert (Can edit rules)
    "sm": "scrum123"      # The Scrum Master (Can run analysis)
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
    # Creates a fake Jira export CSV
    data = {
        "Issue Key": ["EQS-101", "EQS-102", "EQS-103", "EQS-104", "EQS-105"],
        "Summary": ["Setup Cloud Env", "Login Page", "Fix Typos", "Huge Migration", "Urgent Fix"],
        "Status": ["To Do", "In Progress", "Done", "To Do", "In Progress"],
        "Updated": [
            (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d"), # Outdated
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
            datetime.now().strftime("%Y-%m-%d") # Created today (Sprint Stuffing risk)
        ],
        "Story Points": [5, 8, 1, 20, 3], # 20 is Oversized
        "Acceptance Criteria": ["Defined", "", "Fixed", "Defined", "Defined"] # Missing AC
    }
    return pd.DataFrame(data)

# --- PAGE: LOGIN ---
def login_page():
    st.title("🔐 EQS Agile Intelligence Platform")
    st.markdown("### AI Virtual Scrum Master (AVSM)")
    
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
                st.error("Invalid credentials. Try coach/admin123 or sm/scrum123")

# --- PAGE: ADMIN (CONFIGURE RULES) ---
def admin_page():
    st.header("⚙️ Configure AVSM Logic (No-Code Interface)")
    st.info("This interface allows Agile Coaches to update anti-pattern rules without writing Python code.")
    
    kb = load_knowledge_base()
    
    # View Current Rules
    st.subheader("Current Knowledge Base")
    df_rules = pd.DataFrame(kb["anti_patterns"])
    st.dataframe(df_rules[["name", "category", "severity", "remedy"]])
    
    # Add New Rule
    st.subheader("➕ Add New Anti-Pattern Rule")
    with st.form("add_rule"):
        c1, c2 = st.columns(2)
        new_name = c1.text_input("Anti-Pattern Name")
        new_cat = c2.selectbox("Category", ["Product Backlog", "Sprint Planning", "Sprint Execution", "Review"])
        new_sev = c1.selectbox("Severity", ["Low", "Medium", "High"])
        new_desc = c2.text_area("Description")
        
        st.markdown("**Detection Logic**")
        l1, l2, l3 = st.columns(3)
        target_field = l1.text_input("Jira Field to Check", value="Story Points")
        operator = l2.selectbox("Operator", ["greater_than", "less_than", "is_empty", "older_than_days"])
        threshold = l3.number_input("Threshold Value", value=0)
        
        new_remedy = st.text_area("Recommended Remedy (The advice AVSM will give)")
        
        saved = st.form_submit_button("Save Rule to Knowledge Base")
        
        if saved:
            new_entry = {
                "id": f"CUST-{len(kb['anti_patterns'])+1}",
                "name": new_name,
                "category": new_cat,
                "severity": new_sev,
                "description": new_desc,
                "detection_logic": {"field": target_field, "operator": operator, "threshold": threshold},
                "remedy": new_remedy
            }
            kb["anti_patterns"].append(new_entry)
            save_knowledge_base(kb)
            st.rerun()

# --- PAGE: ANALYZE (THE ENGINE) ---
def analysis_page():
    st.header("🔍 AVSM Analysis Engine")
    st.markdown("Upload your **Jira/ADO Export (CSV)** to detect Agile Anti-Patterns.")
    
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
        # Show Raw Data
        with st.expander("View Raw Backlog Data"):
            st.dataframe(df)
            
        if st.button("🚀 Run AVSM Analysis"):
            run_analysis_engine(df)

def run_analysis_engine(df):
    kb = load_knowledge_base()
    violations = []
    
    st.divider()
    st.subheader("📋 Analysis Report")
    
    # --- THE LOGIC ENGINE ---
    for rule in kb["anti_patterns"]:
        logic = rule["detection_logic"]
        field = logic["field"]
        
        # Check if field exists in DF (Fuzzy match or exact)
        if field not in df.columns:
            continue # Skip rules where field is missing
            
        # Apply Logic
        flagged_items = []
        
        if logic["operator"] == "older_than_days":
            # Date logic
            df["temp_date"] = pd.to_datetime(df[field])
            cutoff = datetime.now() - timedelta(days=logic["threshold"])
            flagged_items = df[df["temp_date"] < cutoff]
            
        elif logic["operator"] == "is_empty":
            # Empty field logic
            flagged_items = df[df[field].isnull() | (df[field] == "")]
            
        elif logic["operator"] == "greater_than":
            # Numeric logic
            flagged_items = df[df[field] > logic["threshold"]]
            
        elif logic["operator"] == "created_after_sprint_start":
            # Scope creep logic - simplified for demo (assumes sprint started 5 days ago)
            df["temp_created"] = pd.to_datetime(df[field])
            sprint_start = datetime.now() - timedelta(days=5)
            flagged_items = df[df["temp_created"] > sprint_start]

        # Record Violations
        if len(flagged_items) > 0:
            violations.append({
                "rule": rule["name"],
                "severity": rule["severity"],
                "count": len(flagged_items),
                "items": flagged_items["Issue Key"].tolist(),
                "remedy": rule["remedy"]
            })

    # --- DISPLAY RESULTS ---
    if not violations:
        st.success("🎉 Amazing! No anti-patterns detected. Keep up the great work!")
    else:
        # 1. Scorecard
        score = max(0, 100 - (len(violations) * 15))
        col1, col2, col3 = st.columns(3)
        col1.metric("Agile Health Score", f"{score}/100", delta=-len(violations), delta_color="inverse")
        col2.metric("Issues Detected", len(violations))
        col3.metric("Critical Issues", len([v for v in violations if v["severity"] == "High"]))
        
        # 2. Detailed Findings
        for v in violations:
            color = "red" if v["severity"] == "High" else "orange"
            with st.container():
                st.markdown(f"### :{color}[{v['rule']}]")
                st.markdown(f"**Severity:** {v['severity']} | **Affected Items:** {', '.join(v['items'])}")
                st.warning(f"💡 **AVSM Suggestion:** {v['remedy']}")
                st.divider()

# --- MAIN APP STRUCTURE ---
def main():
    st.set_page_config(page_title="AVSM Prototype", layout="wide")
    
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        # Sidebar Navigation
        st.sidebar.title("🤖 AVSM")
        st.sidebar.write(f"Logged in as: **{st.session_state['username']}**")
        
        menu = ["Analyze Backlog"]
        if st.session_state["role"] == "Admin":
            menu.append("Configure Rules (Admin)")
            
        choice = st.sidebar.radio("Navigation", menu)
        
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.rerun()
            
        # Routing
        if choice == "Analyze Backlog":
            analysis_page()
        elif choice == "Configure Rules (Admin)":
            admin_page()

if __name__ == "__main__":
    main()


### How to turn this code into a Live Public URL (in 5 minutes)

You can do this right now. You do not need to pay anything.

1.  **Create a GitHub Repository:**
    * Go to GitHub.com and create a new public repository (e.g., `avsm-prototype`).
    * Create a file named `app.py` and paste the code above into it.
    * Create a file named `requirements.txt` and paste this inside:
        ```
        streamlit
        pandas
