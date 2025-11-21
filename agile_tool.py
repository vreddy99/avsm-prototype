import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import io

# --- CONFIGURATION (FALLBACK) ---
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

# --- LOGIC ENGINE ---

def apply_rules(df, rules_json):
    """
    Applies the rules from the JSON to the Dataframe.
    Returns a list of violation dictionaries.
    """
    violations = []
    
    # Pre-processing: Ensure dates are datetime objects
    # We try to convert common date columns if they exist
    date_cols = ['Updated', 'Created', 'Resolved']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    for rule in rules_json["anti_patterns"]:
        logic = rule["detection_logic"]
        field = logic["field"]
        
        # Skip if the CSV doesn't have the required column
        if field not in df.columns:
            continue
            
        flagged_rows = pd.DataFrame()
        
        # 1. Logic: older_than_days (Date comparison)
        if logic["operator"] == "older_than_days":
            if field in df.columns:
                cutoff = datetime.now() - timedelta(days=logic["threshold"])
                # Filter rows where date is older than cutoff
                flagged_rows = df[df[field] < cutoff]
        
        # 2. Logic: is_empty (Null/Empty checks)
        elif logic["operator"] == "is_empty":
            # Check for NaN or empty strings
            flagged_rows = df[df[field].isnull() | (df[field] == "") | (df[field].astype(str).str.strip() == "")]

        # 3. Logic: greater_than (Numeric comparison)
        elif logic["operator"] == "greater_than":
            # Force numeric conversion, coerce errors to NaN
            df[field] = pd.to_numeric(df[field], errors='coerce')
            flagged_rows = df[df[field] > logic["threshold"]]

        # 4. Logic: created_after_sprint_start (Specific date logic)
        elif logic["operator"] == "created_after_sprint_start":
            # Simulating a sprint start date of 5 days ago for this demo
            sprint_start = datetime.now() - timedelta(days=5)
            flagged_rows = df[df[field] > sprint_start]

        # If violations found, append them
        if not flagged_rows.empty:
            for idx, row in flagged_rows.iterrows():
                violations.append({
                    "Issue Key": row.get("Issue Key", "Unknown"),
                    "Summary": row.get("Summary", "Unknown"),
                    "Anti-Pattern Detected": rule["name"],
                    "Severity": rule["severity"],
                    "Reason": rule["description"],
                    "Remedy Recommendation": rule["remedy"]
                })
                
    return violations

# --- PAGES ---

def login_page():
    st.title("🔐 Agile Anti-Pattern Scanner")
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
                st.error("Invalid credentials. Try 'coach' / 'admin123'")

def analysis_page():
    st.header("🔍 Backlog Analysis Engine")
    st.markdown("Upload your Rules and Data files below to generate an audit report.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Configuration")
        st.info("Upload a JSON file with anti-pattern rules.")
        uploaded_rules = st.file_uploader("Upload Rules (JSON)", type="json")
        
        # Load rules (either uploaded or default)
        current_rules = load_rules(uploaded_rules)
        
        with st.expander("View Active Rules"):
            st.json(current_rules)

    with col2:
        st.subheader("2. Backlog Data")
        st.info("Upload your Jira/ADO export (CSV).")
        uploaded_data = st.file_uploader("Upload Data (CSV)", type="csv")

    st.divider()

    if uploaded_data is not None:
        try:
            df = pd.read_csv(uploaded_data)
            st.write(f"**Data Preview:** {len(df)} items loaded.")
            st.dataframe(df.head(3))
            
            if st.button("🚀 Run Analysis"):
                results = apply_rules(df, current_rules)
                
                if results:
                    st.subheader(f"🚨 Found {len(results)} Violations")
                    
                    # Convert results to DataFrame
                    result_df = pd.DataFrame(results)
                    
                    # Show on screen
                    st.dataframe(result_df)
                    
                    # Download Logic
                    csv_data = convert_df_to_csv(result_df)
                    st.download_button(
                        label="📥 Download Remediation Report",
                        data=csv_data,
                        file_name="agile_remediation_plan.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("🎉 Amazing! No anti-patterns detected in this dataset.")
                    
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# --- MAIN ---
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
