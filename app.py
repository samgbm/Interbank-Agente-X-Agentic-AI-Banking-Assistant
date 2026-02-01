import streamlit as st
import os
import re
import requests
from typing import Annotated, Literal
# from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver  # <--- NEW: Import Memory
from langgraph.prebuilt import ToolNode  # <--- NEW IMPORTS
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# =============================================================================
# 1. SETUP & CONFIGURATION
# =============================================================================

# Set page configuration for Streamlit (Tab title and icon)
st.set_page_config(
    page_title="Interbank Agent",
    page_icon="💚",
    layout="centered",  # Better for mobile look
    initial_sidebar_state="collapsed",
)

# API Key handling (Replace with your actual key or set in environment)
# If you don't have a key yet, we will use a "Mock" response mode below.
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-proj-...")
# tools = []

llm = ChatOpenAI(model="gpt-4o", temperature=0)
# llm_with_tools = llm.bind_tools(tools)


# --- CSS: INTERBANK VISUAL SYSTEM ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    /* GLOBAL RESET & FONT */
    html, body, [class*="css"] {
        font-family: 'Roboto', 'Geometria', sans-serif;
        color: #0f193c; /* Interbank Dark Blue */
    }

    /* BACKGROUND */
    .stApp {
        background-color: #f3f4f6; /* Soft Gray Background */
    }

    /* HEADER CUSTOMIZATION */
    .header-container {
        background-color: #059c5b; /* Interbank Green */
        padding: 20px;
        border-radius: 0 0 20px 20px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header-logo {
        color: white;
        font-weight: 700;
        font-size: 24px;
        letter-spacing: 1px;
    }
    .header-subtitle {
        color: #e6f7ef;
        font-size: 14px;
        margin-top: 5px;
    }

    /* CHAT BUBBLES - MOBILE OPTIMIZED */
    .chat-row {
        display: flex;
        margin-bottom: 15px;
        width: 100%;
    }
    
    .user-row {
        justify-content: flex-end;
    }
    
    .bot-row {
        justify-content: flex-start;
    }

    .user-bubble {
        background-color: #059c5b; /* Primary Green */
        color: white;
        padding: 12px 16px;
        border-radius: 16px 16px 0 16px; /* Rounded corners with visual cue */
        max-width: 85%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        font-size: 15px;
        line-height: 1.4;
    }

    .bot-bubble {
        background-color: #ffffff;
        color: #0f193c;
        padding: 12px 16px;
        border-radius: 16px 16px 16px 0;
        max-width: 85%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        font-size: 15px;
        line-height: 1.4;
    }

    /* ADMIN NOTIFICATION BADGE */
    .admin-badge {
        background-color: #003057; /* Deep Blue */
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 12px;
        margin-bottom: 10px;
        display: inline-block;
        border-left: 4px solid #00d1c1; /* Cyan accent */
    }

    /* INPUT FIELD STYLING */
    .stChatInput textarea {
        border-radius: 25px !important;
        border: 1px solid #d1d5db !important;
    }
    
    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# 2. DEFINE TOOLS (The Agent's Hands)
# =============================================================================


@tool
def verify_identity(user_id: str):
    """
    Queries the Core Banking System to verify a user ID and fetch their profile.
    Use this immediately after a user provides their ID.
    """
    try:
        # We assume the banking_api is running locally on port 8000
        response = requests.get(f"http://127.0.0.1:8000/customer/{user_id}")
        if response.status_code == 200:
            data = response.json()
            return f"SUCCESS: User found. Name: {data['name']}, Status: {data['employment_status']}, Income: ${data['income']}."
        else:
            return "ERROR: User ID not found in the database."
    except Exception as e:
        return f"SYSTEM ERROR: Could not connect to Banking API. Details: {e}"


@tool
def check_credit_score(user_id: str):
    """
    Checks the external Credit Bureau for the user's credit score (FICO).
    Use this ONLY after verifying identity.
    """
    try:
        response = requests.get(f"http://127.0.0.1:8000/credit-score/{user_id}")
        if response.status_code == 200:
            data = response.json()
            return f"CREDIT REPORT: User: {user_id}, Score: {data['credit_score']}."
        else:
            return "ERROR: Score not found."
    except Exception as e:
        return f"API ERROR: {e}"


@tool
def assess_loan_risk(income: float, credit_score: int, loan_amount: float):
    """
    Step 3: THE PREDICTIVE MODEL RISK ENGINE.
    Calculates risk based on financial data. Returns APPROVED, REJECTED, or MANUAL_REVIEW with a reason.
    """
    # 1. Calculate Debt-to-Income (DTI) Logic (Simplified)
    # We assume monthly repayment is roughly 5% of the loan amount for this heuristic
    estimated_payment = loan_amount * 0.05
    dti_ratio = estimated_payment / income

    # 2. Risk Rules (The "Model")
    risk_decision = "UNKNOWN"
    reason = ""

    if credit_score < 600:
        risk_decision = "REJECTED"
        reason = "Credit score is below the minimum threshold of 600."
    elif dti_ratio > 0.40:
        risk_decision = "REJECTED"
        reason = f"Debt-to-Income ratio is too high ({dti_ratio:.2f}). Loan is too large for income."
    elif credit_score < 700:
        # NEW LOGIC: The "Gray Area"
        risk_decision = "MANUAL_REVIEW"
        reason = f"Score 600-700 requires Manager Approval."
    elif credit_score >= 700:
        risk_decision = "APPROVED"
        reason = "Excellent credit score and healthy income ratio."
    else:
        # Score is between 600 and 700
        risk_decision = "MANUAL_REVIEW"
        reason = "Moderate risk. Requires human underwriter approval."

    return f"RISK ASSESSMENT: Decision: {risk_decision}. Reason: {reason}"


@tool
def disburse_funds(user_id: str, amount: float):
    """
    Step 4: TRANSACTION EXECUTION.
    Only call this if assess_loan_risk returned 'APPROVED'.
    This sends a secure command to the Mainframe to deposit funds.
    """
    try:
        # Note: We use query params for this simple mock. In real life, this is a JSON body.
        url = f"http://127.0.0.1:8000/loan/disburse?user_id={user_id}&amount={amount}"
        response = requests.post(url)

        if response.status_code == 200:
            data = response.json()
            return f"TRANSACTION SUCCESS: {data['message']} (Txn ID: {data['transaction_id']})"
        else:
            return f"TRANSACTION FAILED: {response.text}"
    except Exception as e:
        return f"SYSTEM ERROR: {e}"


# Register ALL 4 tools
tools = [verify_identity, check_credit_score, assess_loan_risk, disburse_funds]
llm_with_tools = llm.bind_tools(tools)


# =============================================================================
# 2. LANGGRAPH BACKEND (The Brain)
# =============================================================================


# Define the State: This holds the conversation history
# class AgentState(TypedDict):
#     messages: Annotated[list, add_messages]


# Expanded State: Now we track 'user_id' specifically
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str | None  # Can be a string (e.g., "user_123") or None


# NODE 1: The ID Collector
# Its only job is to extract the User ID if the user provides it.
def collect_info_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    content = last_message.content.lower()

    # Improved Logic: Look for "user_" anywhere
    # This regex looks for 'user_' followed by digits (e.g., user_123)
    match = re.search(r"(user_\d+)", content)

    if match:
        found_id = match.group(1)
        return {
            "user_id": found_id,
            "messages": [
                AIMessage(
                    content=f"✅ Identity Verified. Accessing secure profile for **{found_id}**. \n\nHow can I help you with your finances today?"
                )
            ],
        }

    # If we are here, we failed to find the ID.
    return {
        "messages": [
            AIMessage(
                content="⚠️ **Access Denied**: I need your User ID to proceed.\n\nPlease type it exactly like this: **user_123**"
            )
        ]
    }


# Define the Chat Node
# NODE 2: The Chatbot (Now with Tool Capability)
def chatbot_node(state: AgentState):
    current_user = state.get("user_id")

    # System Prompt: We instruct it to ALWAYS verify the ID if it hasn't successfully done so yet.
    system_msg = SystemMessage(
        content=f"""
            You are an Agentic Banking Assistant for Interbank Peru. 
            Current User ID in context: {current_user}
            
            If you have a User ID but haven't verified it yet:
                Current User: {current_user}
                Protocol:
                1. If you have a User ID but haven't verified it yet, call the 'verify_identity' tool immediately.
                2. Once verified, address the user by their real name (from the tool output).
                3. Be professional and concise.
            
            If the user asks for a LOAN APPLICATION: 
                
                Current User: {current_user}
                
                STRICT PROTOCOL WORKFLOW FOR LOANS APPLICATIONS:
                1. **Identify**: You need the User ID (already have it).
                2. **Amount**: You need the requested Loan Amount from the user.
                3. **Gather Data**: Call 'verify_identity' AND 'check_credit_score'.
                4. **Analyze**: Call 'assess_loan_risk' passing the data you found.
                5. **Act**: 
                    - **APPROVED**: If risk tool says APPROVED -> Tell user they are approved.  
                        - Ask the user if it want to proceed with disbursement
                            - if YES: Call 'disburse_funds' immediately to send the money. Confirm to the user that the transaction is complete.
                            - if NO: Assert user decision politely.
                    - **REJECTED**: If risk tool says REJECTED -> Tell user politely why, referencing the specific reason (e.g., "Score too low").DO NOT disburse funds.
                    - **MANUAL_REVIEW**: STOP IMMEDIATELY. Say "This requires Manager Approval." Do NOT disburse.
                Do not skip the Risk Assessment step. It is mandatory for compliance.
                EXCEPTION - ADMIN OVERRIDE: If you receive a message starting with "ADMIN_OVERRIDE: APPROVED", you are authorized to proceed with 'disburse_funds' immediately, ignoring previous risk warnings.
                You have permission to execute transactions autonomously if the Risk Engine approves.          
        """
    )

    messages = [system_msg] + state["messages"]

    # We use the LLM *with tools* bound to it
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# MANUAL DEFINITION of tools_condition
# This function checks the last message from the LLM.
# If the LLM decided to call a tool (it has 'tool_calls'), we route to the "tools" node.
# Otherwise, we end the turn.
def tools_condition(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    # Check if the LLM message has tool calls attached
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tools"
    # If no tool call, the agent is done (stops generating)
    return END

# ROUTER: The Traffic Cop
# Decides which node to go to next
# def route_step(state: AgentState) -> Literal["collect_info", "chatbot"]:
#     # Check if we have the user_id in state
#     if not state.get("user_id"):
#         return "collect_info"
#     return "chatbot"
# ROUTER 1: Initial check for User ID
def route_step(state: AgentState) -> Literal["collect_info", "chatbot"]:
    if state.get("user_id"):
        return "chatbot"
    return "collect_info"

# =============================================================================
# 4. BUILD GRAPH
# =============================================================================

if "agent_app" not in st.session_state:
    # We build the graph ONLY once and store it in session state
    # This ensures the 'memory' object is the same instance across re-runs.

    workflow = StateGraph(AgentState)

    workflow.add_node("collect_info", collect_info_node)
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_conditional_edges(START, route_step, {"collect_info": "collect_info", "chatbot": "chatbot"}    )
    # Chatbot -> Tools (Conditional)
    # If LLM says "Call Tool", go to 'tools'. If LLM says "Hello", go to END.
    workflow.add_conditional_edges("chatbot", tools_condition)

    # Tools -> Chatbot
    # After the tool runs, always go back to chatbot so it can read the result and answer the user.
    workflow.add_edge("tools", "chatbot")
    workflow.add_edge("collect_info", END)
    # workflow.add_edge("chatbot", END)

    # Initialize Memory
    memory = MemorySaver()

    # Store the compiled app in session state
    st.session_state.agent_app = workflow.compile(checkpointer=memory)

# =============================================================================
# 3. STREAMLIT FRONTEND (The WhatsApp UI)
# =============================================================================

# --- HEADER (Interbank Brand) ---
st.markdown(
    """
<div style="transform: translateY(-60px);" class="header-container">
    <div class="header-logo">Interbank 💚</div>
    <div class="header-subtitle">Banca Digital · Agente AI</div>
</div>
""",
    unsafe_allow_html=True,
)


# --- SIDEBAR ADMIN PANEL ---
# --- SIDEBAR (Admin Panel) ---
with st.sidebar:
    st.markdown("### 🔐 Zona Segura")
    st.info("Panel de Control para Gestores")

    if st.button("✅ Aprobar Crédito (Manager)"):
        override_msg = HumanMessage(
            content="ADMIN_OVERRIDE: APPROVED. Proceed with disbursement."
        )
        st.session_state.messages.append(override_msg)

        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {"messages": st.session_state.messages}

        with st.status("🔄 Procesando autorización...", expanded=True) as status:
            result = st.session_state.agent_app.invoke(inputs, config=config)
            status.update(
                label="✅ Autorización Completada", state="complete", expanded=False
            )

            final_response = result["messages"][-1]
            st.session_state.messages.append(final_response)
        st.rerun()


# st.markdown(
#     "<style>.stApp {background-color: #E5DDD5;}</style>", unsafe_allow_html=True
# )
# st.markdown(
#     "<h2 style='text-align: center; color: #075E54;'>🏦 INTERSECZ BANK APP</h2>",
#     unsafe_allow_html=True,
# )

# Initialize Messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="Welcome to the Bank. Please enter your User ID to start.")
    ]

# We need a thread_id to track THIS specific user's conversation in LangGraph
if "thread_id" not in st.session_state:
    import uuid
    st.session_state.thread_id = str(uuid.uuid4())


# Display Loop with Custom CSS Classes
for msg in st.session_state.messages:
    if isinstance(msg, (HumanMessage, AIMessage)):
        content = msg.content
        if "ADMIN_OVERRIDE" in content:
            st.markdown(
                f'<div class="admin-badge">🔔 Autorización de Gerencia Recibida</div>',
                unsafe_allow_html=True,
            )
        else:
            if isinstance(msg, HumanMessage):
                st.markdown(
                    f"""
                <div class="chat-row user-row">
                    <div class="user-bubble">{content}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                <div class="chat-row bot-row">
                    <div class="bot-bubble">{content}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

# --- INPUT AREA ---
user_input = st.chat_input("Escribe aquí tu consulta...")

if user_input:
    # 1. Append User Message
    st.session_state.messages.append(HumanMessage(content=user_input))

    # Force UI update to show user message immediately
    st.rerun()

# --- PROCESSING LOGIC (AFTER RERUN) ---
# We check if the last message is from Human to trigger the bot
if st.session_state.messages and isinstance(
    st.session_state.messages[-1], HumanMessage
):
    last_msg = st.session_state.messages[-1]
    if "ADMIN_OVERRIDE" not in last_msg.content:  # Avoid double trigger on admin button

        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {"messages": st.session_state.messages}

        # VISUAL POLISH: The "Thinking" Status
        with st.status("🤖 Interbank AI está procesando...", expanded=True) as status:

            # We invoke the graph
            result = st.session_state.agent_app.invoke(inputs, config=config)

            # Optional: Show tool outputs in the expander for "Explainability"
            # This extracts intermediate tool messages
            tool_msgs = [
                m
                for m in result["messages"]
                if hasattr(m, "tool_calls") or m.type == "tool"
            ]
            if tool_msgs:
                st.write("🔍 **Detalles Técnicos:**")
                for m in tool_msgs:
                    if m.type == "tool":
                        st.code(f"Tool Output: {m.content}", language="json")

            status.update(label="✅ Respuesta Lista", state="complete", expanded=False)

        # Append Bot Response
        final_response = result["messages"][-1]
        st.session_state.messages.append(final_response)
        st.rerun()
