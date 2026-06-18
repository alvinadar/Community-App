import streamlit as st 
import mysql.connector
from google import genai
import os

#1.Set up the database management(MySQL)

# 1. Set up the database management (MySQL)

def init_db():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123"
        )
        cursor = mydb.cursor()

        # Create database if not exists 
        cursor.execute("CREATE DATABASE IF NOT EXISTS community_issues")
        cursor.execute("USE community_issues")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                action_plan TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        mydb.commit()

        # Safely add the status column to an existing table if it doesn't exist yet
        try:
            cursor.execute("ALTER TABLE issues ADD COLUMN status VARCHAR(50) DEFAULT 'Open'")
            mydb.commit()
        except mysql.connector.Error:
            # Column already exists, safe to ignore
            pass

        cursor.close()
        mydb.close()
    except mysql.connector.Error as err:
        st.error(f"Database error: {err}")

# Save all the user data alongside the AI response using MySQL syntax 
def save_issue(title, category, description, action_plan):
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123",
            database="community_issues"
        )
        cursor = mydb.cursor()
        query = '''
            INSERT INTO issues (title, category, description, action_plan, status)
            VALUES (%s, %s, %s, %s, 'Open')
            '''
        cursor.execute(query, (title, category, description, action_plan))
        mydb.commit()
        cursor.close()
        mydb.close()
    except mysql.connector.Error as err:
        st.error(f"Database error: {err}")

# Update the status of an issue (Open <-> Resolved)
def update_issue_status(issue_id, new_status):
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123",
            database="community_issues"
        )
        cursor = mydb.cursor()
        query = "UPDATE issues SET status = %s WHERE id = %s"
        cursor.execute(query, (new_status, issue_id))
        mydb.commit()
        cursor.close()
        mydb.close()
    except mysql.connector.Error as err:
        st.error(f"Database error while updating status: {err}")

# Retrieve all the community logs from the MYSQL database 
def fetch_issues():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123",
            database="community_issues"
        )
        cursor = mydb.cursor()
        # Explicitly fetching status along with other columns
        cursor.execute("SELECT id, title, category, description, action_plan, timestamp, status FROM issues ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        cursor.close()
        mydb.close()
        return rows
    except mysql.connector.Error as err:
        st.error(f"Database error: {err}")
        return []
    
#Initialize the database when the app starts
init_db()
    
#Create the AI Wrapper 
#We will integerate the prompt into the AI wrapper to generate the action plan based on the user input
#Promp we use the consept of RACE (Role, Action, Context, Expecation) to generate the action plan
def generate_action_plan(api_key,title,category,description):
    try:
        client = genai.Client(api_key = api_key)

        prompt = f"""
       You are an expert community organizer. A resident has reported a local problem.
       Issue Title: {title}
       Category: {category}
       Detailed Description: {description}
       
       Please provide a structured ,practical , and localized action plan to address this issue.
       Keep your response friendly but direct. Structure it with 3 distinct,sequential steps label 'Step 1','Step 2','Step 3' so residents can act immediately.
       The action plan should be based on the local context of Malaysia, considering common community resources and local government processes.
       """
        
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = prompt
        )
        return response.text
    except Exception as e:
        return f"API Error:Unable to generate response.Details :  {str(e)}"
    


#Streamlit UI

st.set_page_config(page_title ="Community Action Hub (MySQL Edition)",layout= "wide")
st.title("Community Action Hub")
st.caption("Empowering neighbours with ersistent, production-grade scaling infrastructure.")
st.markdown("---")

#Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    user_api_key = st.text_input("Google AI Studio API Key", type="password",help="Input your Germini API key here.")
    st.markdown("[Get a free Germini API key here](https://aistudio.google.com/api-keys?project=gen-lang-client-0779282876)")

#Layout Split 
col1,col2 = st.columns([2,3],gap="large")  
with col1:
    st.subheader("Log Community Issues")
    with st.form("Issue_submission_form",clear_on_submit = True):
        issue_title = st.text_input("Short Title /Headline ",placeholder = "Blocked ddrainage at Jalan Jun")
        issue_category = st.selectbox("Category", ["Infrastructure","Public Safety","Enviroment","Health & Sanitation","Others"])
        issue_desc = st.text_area("Detailed Context",placeholder = "Provide a detailed description of the issue...")

        submit_clicked = st.form_submit_button("Submit & Request AI Solution Blueprint")

        if submit_clicked:
            if not user_api_key:
                st.error("Please enter your Google AI Studio API key in the sidebar.")
            elif not issue_title or not issue_desc:
                st.warning("What your problem?")
            else:
                with st.spinner("Analyzing your porblem & structuring task list...."):
                    #1.Request the AI Generation 
                    ai_blueprint = generate_action_plan(user_api_key,issue_title,issue_category,issue_desc)

                    #2. Write our feedback to the database 
                    save_issue(issue_title,issue_category,issue_desc,ai_blueprint)

                    st.success("All your problems had been saved and we will be back to you.")

with col2:
    st.subheader("Love Neighbourhood Action Board")
    past_log = fetch_issues()

    if not past_log:
        st.info("There is no issue log yet. Be the first one to report a problem in your community.")
    else:
        for entry in past_log:
            issue_id = entry[0]
            title = entry[1]
            category = entry[2]
            description = entry[3]
            action_plan = entry[4]
            timestamp = entry[5]
            status = entry[6]

            # Format the timestamp to a more human-friendly format
            str_timestamp = timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(timestamp, "strftime") else str(timestamp)[:16]

            # Append emoji indicators based on open status
            status_emoji = "⏳" if status == "Open" else "✅"

            with st.expander(f"{status_emoji} [{category}] {title} -  {str_timestamp}"):
                st.markdown("**Status:** " + (f"🔴 `{status}`" if status == "Open" else f"🟢 `{status}`"))
                st.markdown("**Resident Complain**")
                st.write(description)
                st.markdown("---")
                st.markdown("AI_Generated Action Plan:")
                st.write(action_plan)
                st.markdown("---")

                #Render Resolve /Repoen button conditional actions 
                if status == "Open":
                    if st.button("Mark as Resolved",key = f"resolve_{issue_id}"):
                        update_issue_status(issue_id,'Resolved')
                        st.rerun()
                else:
                    if st.button("Re Open Issue", key = f"reopen_{issue_id}"):
                        update_issue_status(issue_id,"Open")
                        st.rerun()

