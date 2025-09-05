"""
Streamlit To-Do List App with Perplexity API (Sonar Pro model) support, updated for latest Streamlit
File: streamlit_todo_app.py
"""

import streamlit as st
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import requests

# ---------- Session state setup ----------
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "refresh" not in st.session_state:
    st.session_state.refresh = False

# ---------- Persistence helpers ----------
DATA_FILE = Path("tasks.json")

def load_tasks():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

# ---------- Perplexity API helpers ----------
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
USE_PERPLEXITY = PERPLEXITY_API_KEY is not None

def perplexity_chat(prompt: str, max_tokens: int = 100, temperature: float = 0.3) -> str:
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"AI request failed: {e}")
        return ""

def ai_suggest_title(description: str) -> str:
    if not USE_PERPLEXITY:
        return ""
    prompt = f"You are a helpful assistant that suggests short, clear, actionable todo titles.\nTask description: {description}\nReturn a 3-6 word title."
    return perplexity_chat(prompt, max_tokens=30, temperature=0.3)

def ai_categorize(title: str, description: str) -> str:
    if not USE_PERPLEXITY:
        return ""
    prompt = f"You are an assistant that assigns a concise category to a todo item (work, personal, shopping, errands, learning, other).\nTitle: {title}\nDescription: {description}\nOnly return one of the categories: work, personal, shopping, errands, learning, other."
    cat = perplexity_chat(prompt, max_tokens=10, temperature=0.0).lower()
    for c in ["work","personal","shopping","errands","learning","other"]:
        if c in cat:
            return c
    return "other"

# ---------- App UI ----------
st.set_page_config(page_title="AI To-Do List", layout="centered")
st.title("🗒️ Smart To-Do List")

# Load tasks from file on start
if not st.session_state.tasks:
    st.session_state.tasks = load_tasks()

# Add new task form
with st.form("add_task_form", clear_on_submit=False):
    st.subheader("Add a task")
    col1, col2 = st.columns([3,1])
    with col1:
        title_input = st.text_input("Title", key="title_input")
        desc_input = st.text_area("Description", height=80, key="desc_input")
    with col2:
        due = st.date_input("Due date", value=None)
        priority = st.selectbox("Priority", ["Medium","High","Low"]) 
        category = st.selectbox("Category", ["uncategorized","work","personal","shopping","errands","learning","other"]) 
    submitted = st.form_submit_button("Add task")

    # AI buttons
    if USE_PERPLEXITY:
        ai_col1, ai_col2 = st.columns(2)
        with ai_col1:
            if st.button("Suggest title from description"):
                if desc_input.strip():
                    suggested = ai_suggest_title(desc_input.strip())
                    if suggested:
                        st.session_state.title_input = suggested
                        st.session_state.refresh = not st.session_state.refresh
                    else:
                        st.info("Couldn't get suggestion.")
        with ai_col2:
            if st.button("Auto-categorize"):
                if title_input.strip() or desc_input.strip():
                    cat = ai_categorize(title_input.strip(), desc_input.strip())
                    if cat:
                        st.info(f"AI suggests category: {cat}")

if submitted:
    if not title_input.strip() and not desc_input.strip():
        st.error("Please provide at least a title or description.")
    else:
        task = {
            "id": int(datetime.now(timezone.utc).timestamp()*1000),
            "title": title_input.strip() or (desc_input.strip()[:60] + "..."),
            "description": desc_input.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "due": str(due) if due else "",
            "priority": priority,
            "category": category,
            "done": False,
        }
        st.session_state.tasks.append(task)
        save_tasks(st.session_state.tasks)
        st.success("Task added!")
        st.session_state.refresh = not st.session_state.refresh

# Filters and view
st.markdown("---")
filter_col1, filter_col2, filter_col3 = st.columns([2,2,2])
with filter_col1:
    show_done = st.checkbox("Show done", value=True)
with filter_col2:
    filter_cat = st.selectbox("Filter by category", ["all","uncategorized","work","personal","shopping","errands","learning","other"]) 
with filter_col3:
    sort_by = st.selectbox("Sort by", ["created","due","priority"])

# Display tasks
filtered = []
for t in st.session_state.tasks:
    if not show_done and t.get("done"):
        continue
    if filter_cat != "all" and t.get("category","uncategorized") != filter_cat:
        continue
    filtered.append(t)

# Sorting
if sort_by == "due":
    filtered.sort(key=lambda x: x.get("due") or "9999-99-99")
elif sort_by == "priority":
    order = {"High":0, "Medium":1, "Low":2}
    filtered.sort(key=lambda x: order.get(x.get("priority","Medium"), 1))
else:
    filtered.sort(key=lambda x: x.get("created_at"), reverse=True)

st.subheader(f"Tasks ({len(filtered)})")
if not filtered:
    st.info("No tasks found.")

for t in filtered:
    cols = st.columns([0.06, 0.94])
    with cols[0]:
        done = st.checkbox("Task done", value=t.get("done", False), key=f"done_{t['id']}", label_visibility="collapsed")
    with cols[1]:
        title_display = t.get("title")
        meta = f"[{t.get('category','uncategorized')}] • {t.get('priority','Medium')}"
        if t.get("due"):
            meta += f" • due {t.get('due')}"
        st.markdown(f"""**{title_display}**  
{meta}""")
        if t.get("description"):
            st.write(t.get("description"))
        a1, a2, a3 = st.columns([1,1,1])
        if a1.button("Edit", key=f"edit_{t['id']}"):
            st.session_state.edit_id = t['id']
            st.session_state.edit_title = t.get('title')
            st.session_state.edit_description = t.get('description')
            st.session_state.edit_due = t.get('due')
            st.session_state.edit_priority = t.get('priority')
            st.session_state.edit_category = t.get('category')
            st.session_state.refresh = not st.session_state.refresh
        if a2.button("Delete", key=f"del_{t['id']}"):
            st.session_state.tasks = [x for x in st.session_state.tasks if x['id'] != t['id']]
            save_tasks(st.session_state.tasks)
            st.success("Deleted")
            st.session_state.refresh = not st.session_state.refresh
        if a3.button("Move to top", key=f"top_{t['id']}"):
            st.session_state.tasks = [x for x in st.session_state.tasks if x['id'] != t['id']]
            st.session_state.tasks.insert(0, t)
            save_tasks(st.session_state.tasks)
            st.session_state.refresh = not st.session_state.refresh
    if done != t.get("done", False):
        for task in st.session_state.tasks:
            if task['id'] == t['id']:
                task['done'] = done
        save_tasks(st.session_state.tasks)
        st.session_state.refresh = not st.session_state.refresh

# Edit task section (if needed)
if st.session_state.get('edit_id'):
    st.markdown("---")
    st.subheader("Edit task")
    eid = st.session_state.edit_id
    etitle = st.text_input("Title", value=st.session_state.get('edit_title',''), key='etitle')
    edesc = st.text_area("Description", value=st.session_state.get('edit_description',''), key='edesc')
    edue = st.text_input("Due (YYYY-MM-DD)", value=st.session_state.get('edit_due',''), key='edue')
    epriority = st.selectbox("Priority", ["Medium","High","Low"], index=["Medium","High","Low"].index(st.session_state.get('edit_priority','Medium')))
    ecat = st.selectbox("Category", ["uncategorized","work","personal","shopping","errands","learning","other"], index=["uncategorized","work","personal","shopping","errands","learning","other"].index(st.session_state.get('edit_category','uncategorized')))
    if st.button("Save changes"):
        for task in st.session_state.tasks:
            if task['id'] == eid:
                task['title'] = etitle.strip()
                task['description'] = edesc.strip()
                task['due'] = edue.strip()
                task['priority'] = epriority
                task['category'] = ecat
        save_tasks(st.session_state.tasks)
        st.success("Saved")
        for k in ['edit_id','edit_title','edit_description','edit_due','edit_priority','edit_category']:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.refresh = not st.session_state.refresh
    if st.button("Cancel"):
        for k in ['edit_id','edit_title','edit_description','edit_due','edit_priority','edit_category']:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.refresh = not st.session_state.refresh

st.markdown("---")
col_info1, col_info2 = st.columns(2)
with col_info1:
    st.caption("Data stored locally in tasks.json")
with col_info2:
    if USE_PERPLEXITY:
        st.caption("AI features enabled via Perplexity (Sonar Pro)")
    else:
        st.caption("AI features disabled — set PERPLEXITY_API_KEY to enable optional smart features")

# End of file
