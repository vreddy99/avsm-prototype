import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import io
import re

# --- CONFIGURATION (Based on 'The Scrum Anti-Patterns Guide') ---
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

# --- MOCK USER DATABASE (Updated with Roles) ---
USERS = {
    "coach": "admin123",       # ADMIN: Can edit rules and run analysis
    "sm": "scrum123",          # USER: Can run analysis only
    "developer": "code4life",  # USER: Can run analysis only
    "po": "value99"            # USER: Can run analysis only
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
    date_cols = ['Updated', 'Created', 'Resolved']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    for rule in rules_json["anti_patterns"]:
        logic = rule["detection_logic"]
        field = logic["field"]
        
        # Skip if the CSV doesn't have the required column
        # Exception: 'days_since_last_update' requires Status + Date
        if field not in df.columns:
            if logic["operator"] != "days_since_last_update":
                continue
            elif logic["operator"] == "days_since_last_update" and "Status" not in df.columns:
                continue
            
        flagged_rows = pd.DataFrame()
        
        # 1. Logic: older_than_days (Date comparison)
        if logic["operator"] == "older_than_days":
            if field in df.columns:
                cutoff = datetime.now() - timedelta(days=logic["threshold"])
                flagged_rows = df[df[field] < cutoff]
        
        # 2. Logic: is_empty (Null/Empty checks)
        elif logic["operator"] == "is_empty":
            flagged_rows = df[df[field].isnull() | (df[field] == "") | (df[field].astype(str).str.strip() == "")]

        # 3. Logic: greater_than (Numeric comparison)
        elif logic["operator"] == "greater_than":
            df[field] = pd.to_numeric(df[field], errors='coerce')
            flagged_rows = df[df[field] > logic["threshold"]]

        # 4. Logic: created_after_sprint_start (Scope Creep)
        elif logic["operator"] == "created_after_sprint_start":
            # Simulating a sprint start date of 5 days ago for this demo
            sprint_start = datetime.now() - timedelta(days=5)
            flagged_rows = df[df[field] > sprint_start]

        # 5. Logic: word_count_greater_than (Verbosity)
        elif logic["operator"] == "word_count_greater_than":
            flagged_rows = df[df[field].astype(str).apply(lambda x: len(x.split())) > logic["threshold"]]

        # 6. Logic: word_count_less_than (Vagueness)
        elif logic["operator"] == "word_count_less_than":
            non_empty = df[df[field].notna() & (df[field].astype(str).str.strip() != "")]
            flagged_rows = non_empty[non_empty[field].astype(str).apply(lambda x: len(x.split())) < logic["threshold"]]

        # 7. Logic: days_since_last_update (Stagnation)
        elif logic["operator"] == "days_since_last_update":
            if "Status" in df.columns and field in df.columns:
                in_progress = df[df["Status"] == "In Progress"]
                cutoff = datetime.now() - timedelta(days=logic["threshold"])
                flagged_rows = in_progress[in_progress[field] < cutoff]

        # 8. Logic: contains_text (Keyword Search)
        elif logic["operator"] == "contains_text":
            flagged_rows = df[df[field].astype(str).str.contains(str(logic["threshold"]), case=False, na=False)]

        # 9. Logic: fields_are_identical (Copy & Paste PO)
        elif logic["operator"] == "fields_are_identical":
            target_field = logic["threshold"] 
            if field in df.columns and target_field in df.columns:
                flagged_rows = df[
                    (df[field].notna()) & 
                    (df[target_field].notna()) & 
                    (df[field].astype(str).str.strip() == df[target_field].astype(str).str.strip())
                ]
