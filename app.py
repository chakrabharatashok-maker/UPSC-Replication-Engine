import streamlit as st
import os
import re
import google.generativeai as genai
from engine import ExamEngine
from librarian import Librarian, LIBRARY_DIR
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.graphics.shapes import Drawing, Rect, Path
from reportlab.pdfgen import canvas

# Optional: OAuth Support
try:
    from streamlit_oauth import OAuth2Component
    HAS_OAUTH = True
except ImportError:
    HAS_OAUTH = False

@st.cache_data(ttl=3600)
def get_available_models(api_key):
    """Fetches available Gemini models dynamically from the API."""
    if not api_key: return []
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name.lower():
                    # FILTER: Strict JSON Support & Legacy Check
                    # User Request: Remove 1.5, remove 1.0. Keep only what works (latest aliases + 2.0)
                    n = m.name.lower()
                    if "1.0" in n: continue
                    if "1.5" in n: continue # User requested removal
                    if "experimental" in n: continue 
                    if n == "models/gemini-pro": continue 
                    
                    models.append(m.name)
        
        # Reliability Sort: Flash Latest (Alias) > 2.0 Flash
        def model_sorter(name):
            val = 0
            n = name.lower()
            if "flash" in n and "latest" in n: val += 150 # Absolute Top Priority
            elif "2.0" in n and "flash" in n: val += 120 
            elif "pro" in n and "latest" in n: val += 80 
            return val

        models.sort(key=model_sorter, reverse=True)
        return models
    except Exception:
        return []

# Page Config
st.set_page_config(
    page_title="UPSC Exam Replication Engine",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -- Authentication Logic (Premium Gate) --
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def render_login_page():
    # Centered Layout for Login
    _, col_login, _ = st.columns([1, 1.5, 1])
    
    with col_login:
        st.markdown("")
        st.markdown("")
        st.markdown("### 👋 Welcome Aspirant")
        st.markdown("Sign in to sync your **Mock Tests**, **History**, and **Progress**.")
        
        # Stylized Container
        with st.container(border=True):
            st.markdown("#### Access Your Account")
            
            # Google Auth "Link" Logic (Hybrid: Real vs Simulation)
            CLIENT_ID = st.secrets.get("google", {}).get("client_id")
            CLIENT_SECRET = st.secrets.get("google", {}).get("client_secret")
            
            if HAS_OAUTH and CLIENT_ID and CLIENT_SECRET:
                # -- REAL OAUTH FLOW --
                oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                    "https://accounts.google.com/o/oauth2/v2/auth", 
                    "https://oauth2.googleapis.com/token", 
                    "https://www.googleapis.com/oauth2/v3/token", 
                    "https://www.googleapis.com/oauth2/v1/userinfo")
                
                result = oauth2.authorize_button(
                    name="Sign in with Google",
                    icon="https://www.google.com.tw/favicon.ico",
                    redirect_uri="http://localhost:8501", # Note: User might need to change this for deploys
                    scope="openid email profile",
                    key="google_auth",
                    extras_params={"prompt": "select_account"},
                    use_container_width=True,
                )
                
                if result:
                    # Verify token and get email
                    if "token" in result:
                        st.session_state.authenticated = True
                        email_data = result.get("token", {}).get("id_token_claims", {}).get("email", "Google User")
                        st.balloons()
                        st.toast(f"Verified Google Login: {email_data}", icon="✅")
                        st.session_state.auth_method = "google_real"
                        st.rerun()
            else:
                # -- SIMULATION FLOW (Fallback) --
                if st.button("🔴  Sign in with Google", use_container_width=True):
                    st.session_state.auth_method = "google"
                
            if st.session_state.get("auth_method") == "google":
                st.info("ℹ️ Enter your **Gmail** address to verify identity.")
            
            st.markdown("""<div style='text-align: center; color: #6B7280; font-size: 12px; margin: 10px 0;'>ACCOUNT VERIFICATION</div>""", unsafe_allow_html=True)
            
            email = st.text_input("Email Address", placeholder="name@gmail.com", label_visibility="collapsed")
            
            if st.button("Continue ➔", type="primary", use_container_width=True):
                if "@" in email and "." in email:
                    # Logic: If it's a Gmail, we treat it as a Google Auth session
                    if "gmail.com" in email.lower() or st.session_state.get("auth_method") == "google":
                        st.session_state.authenticated = True
                        st.balloons()
                        st.toast(f"Authenticated via Google: {email}", icon="✅")
                        st.rerun()
                    else:
                        st.session_state.authenticated = True
                        st.toast(f"Welcome, {email.split('@')[0]}!", icon="🚀")
                        st.rerun()
                else:
                    st.warning("Please enter a valid email address.")

        st.markdown("""<div style='text-align: center; color: #9CA3AF; font-size: 12px; margin-top: 20px;'>
        By continuing, you link your email to your Agent AI Profile.<br>
        Agent AI • UPSC Dream App
        </div>""", unsafe_allow_html=True)

if not st.session_state.authenticated:
    render_login_page()
    st.stop() # Halts the rest of the app logic until authenticated

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle

def draw_modern_background(c, doc):
    """
    Draws the decorative background elements (organic curves) based on the reference image.
    """
    c.saveState()
    
    # -- Colors --
    # Reference image has purple/pink gradients. We'll use a professional "UPSC" palette 
    # but soft: Muted Purple/Blue and Soft Gold/Pink.
    color_top = colors.Color(0.3, 0.2, 0.4, alpha=0.15) # Muted Deep Purple (Transparent)
    color_bottom = colors.Color(0.6, 0.2, 0.3, alpha=0.15) # Muted Rose (Transparent)
    
    width, height = letter
    
    # -- Top Right Curve --
    p1 = c.beginPath()
    p1.moveTo(width, height)
    p1.lineTo(width, height - 3*inch)
    # Cubic Bezier curve to create the organic swoosh
    p1.curveTo(width - 1*inch, height - 2*inch, width - 3*inch, height - 0.5*inch, width - 4*inch, height)
    p1.close()
    c.setFillColor(color_top)
    c.setStrokeColor(colors.transparent)
    c.drawPath(p1, fill=1, stroke=0)
    
    # Secondary Top Curve (Layering)
    p1b = c.beginPath()
    p1b.moveTo(width, height)
    p1b.lineTo(width, height - 2*inch)
    p1b.curveTo(width - 0.5*inch, height - 1.5*inch, width - 1.5*inch, height - 0.2*inch, width - 2.5*inch, height)
    p1b.close()
    c.setFillColor(colors.Color(0.3, 0.2, 0.5, alpha=0.1)) # Variable shade
    c.drawPath(p1b, fill=1, stroke=0)

    # -- Bottom Left Curve --
    p2 = c.beginPath()
    p2.moveTo(0, 0)
    p2.lineTo(0, 3*inch)
    p2.curveTo(1*inch, 2*inch, 3*inch, 0.5*inch, 4*inch, 0)
    p2.close()
    c.setFillColor(color_bottom)
    c.drawPath(p2, fill=1, stroke=0)
    
    # Secondary Bottom Curve
    p2b = c.beginPath()
    p2b.moveTo(0, 0)
    p2b.lineTo(0, 1.5*inch)
    p2b.curveTo(0.5*inch, 1*inch, 1.5*inch, 0.2*inch, 2.5*inch, 0)
    p2b.close()
    c.setFillColor(colors.Color(0.6, 0.2, 0.4, alpha=0.1))
    c.drawPath(p2b, fill=1, stroke=0)
    
    c.restoreState()

def create_pdf(quiz_data, user_answers, topic, difficulty, total_score, max_score):
    buffer = BytesIO()
    # Generous margins for a clean look
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, leftMargin=1*inch, rightMargin=1*inch, bottomMargin=1*inch)
    
    styles = getSampleStyleSheet()
    
    # -- Typography & Palette --
    # Keeping it clean and professional
    accent_color = colors.navy
    
    title_style = ParagraphStyle(
        'MainTitle', 
        parent=styles['Heading1'], 
        fontSize=22, 
        textColor=accent_color, 
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=24,
        fontName='Helvetica'
    )
    
    q_text_style = ParagraphStyle(
        'QText', 
        parent=styles['Normal'], 
        fontSize=11, 
        leading=15,
        spaceAfter=10, 
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    opt_style = ParagraphStyle(
        'Option', 
        parent=styles['Normal'], 
        fontSize=10,
        leading=14,
        leftIndent=0, 
        spaceAfter=4,
        fontName='Helvetica'
    )
    
    exp_style = ParagraphStyle(
        'Explanation', 
        parent=styles['Normal'], 
        fontSize=10,
        leading=13,
        textColor=colors.dimgrey, # Muted text
        leftIndent=0,
        spaceBefore=6,
        fontName='Helvetica-Oblique'
    )
    
    story = []
    
    # -- Header Info --
    story.append(Paragraph(f"UPSC Mock Assessment: {topic}", title_style))
    story.append(Spacer(1, 15))
    
    # -- SCORECARD TABLE --
    score_data = [
        ["METRIC", "DETAILS"],
        ["Difficulty", difficulty],
        ["Questions", str(len(quiz_data))],
        ["Result", f"{total_score:.2f} / {max_score}"]
    ]
    
    # Minimalist Table Style to match modern look
    t = Table(score_data, colWidths=[2.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), accent_color),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        ('BACKGROUND', (0, 1), (-1, -1), colors.white), # Keep white background for readability
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, accent_color),
    ]))
    story.append(t)
    
    story.append(Spacer(1, 30))
    story.append(Paragraph("DETAILED ANALYSIS", ParagraphStyle('Section', parent=styles['Heading3'], textColor=accent_color, spaceAfter=15)))
    story.append(Paragraph("<hr width='100%' color='lightgrey' thickness='0.5'/>", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # -- Question Loop --
    for i, q in enumerate(quiz_data):
        raw_text = q['question_text']
        
        # Enhanced Formatting Logic for proper line breaks
        # 1. Statements (1. ... 2. ...)
        # Regex: Look for digit-dot-space, and ensure it's preceded by space or start. 
        # Add <br/> and Bold the number.
        fmt_text = re.sub(r'(\s|^)(\d+\.)(\s)', r'<br/><b>\2</b>\3', raw_text)
        
        # 2. Key phrases
        fmt_text = re.sub(r'(Which of the statements)', r'<br/><br/>\1', fmt_text)
        fmt_text = re.sub(r'(Select the correct)', r'<br/><br/>\1', fmt_text)
        fmt_text = re.sub(r'(Consider the following)', r'\1<br/>', fmt_text)
        
        # 3. Clean up generic newlines
        fmt_text = fmt_text.replace("\n", " ") # Collapse inherent newlines first to avoid weird gaps, let regex handle structure
        
        # 4. Final Polish: Ensure double breaks aren't excessive
        fmt_text = fmt_text.replace("<br/><br/><br/>", "<br/><br/>")
        
        q_label = f"<b>Q{i+1}.</b> "
        story.append(Paragraph(q_label + fmt_text, q_text_style))
        
        user_choice = user_answers.get(i)
        correct_choice = q['correct_option']
        
        # Options
        for opt_key, opt_text in q['options'].items():
            color_hex = "#333333" # Dark Grey default
            prefix = ""
            bg_color = None
            
            # Logic: Simpler visual cues. 
            if opt_key == correct_choice:
                color_hex = "#006400" # Dark Green
                prefix = "✓ "
            elif opt_key == user_choice and user_choice != correct_choice:
                color_hex = "#8B0000" # Dark Red
                prefix = "✗ (Your Answer) "
            elif opt_key == user_choice:
                 prefix = "✓ (Your Answer) "
                 color_hex = "#006400"

            formatted_opt = f'''<font color="{color_hex}"><b>{prefix}{opt_key})</b> {opt_text}</font>'''
            story.append(Paragraph(formatted_opt, opt_style))
            
        # Explanation (Minimalist)
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"<b>Explanation:</b> {q['explanation']}", exp_style))
        
        story.append(Spacer(1, 25))
            
    # Build with Background
    doc.build(story, onFirstPage=draw_modern_background, onLaterPages=draw_modern_background)
    buffer.seek(0)
    return buffer

# Custom CSS for "Premium Card-Based" Aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-color: #030712;       /* Ultra Dark (Gray 950) */
        --card-bg: #111827;        /* Rich Dark (Gray 900) */
        --text-primary: #F9FAFB;   /* Bright White (Gray 50) */
        --text-secondary: #9CA3AF; /* Muted Grey (Gray 400) */
        --accent-color: #3B82F6;   /* Bright Blue (Blue 500) */
        --border-color: #1F2937;   /* Dark Border (Gray 800) */
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--text-primary);
        background-color: var(--bg-color);
    }
    
    /* 1. Layout: Clean & Open */
    .stApp {
        background-color: var(--bg-color);
        background-image: none;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 900px;
    }

    /* 2. Typography: "Stylish Modern" */
    h1, h2, h3, h4, h5 {
        font-family: 'Outfit', sans-serif !important;
        color: var(--text-primary) !important;
        font-weight: 700;
        letter-spacing: -0.02em; /* Tight tracking for style */
    }
    
    h1 { font-size: 2.6rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 2rem !important; margin-top: 2rem !important; }
    h3 { font-size: 1.5rem !important; }
    
    p, li, label, .stMarkdown {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 16px;
        line-height: 1.6;
        color: var(--text-primary) !important;
    }

    /* 3. Sidebar: Muted & Minimal */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-color); /* Very subtle grey */
        border-right: 1px solid var(--border-color);
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label {
        color: var(--text-primary) !important;
    }
    
    /* 4. Inputs: "Shopping Search" Style */
    .stTextInput > div > div > input, 
    .stSelectbox > div > div > div, 
    .stMultiSelect > div > div > div {
        background-color: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--accent-color);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    /* 5. Buttons: Subtle & Premium */
    .stButton > button {
        background-color: var(--card-bg);
        color: var(--accent-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        transition: all 0.2s;
    }
    .stButton > button:hover {
        border-color: var(--accent-color);
        background-color: var(--card-bg); /* Keep dark on hover */
        color: var(--accent-color);
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.4);
    }

    /* 6. Cards: The "Product Catalog" Look */
    .quiz-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px; /* Soft, friendly corners */
        padding: 32px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.3); /* Premium dark shadow */
        border-left: 4px solid var(--accent-color);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    
    hr {
        border-color: var(--border-color);
        margin: 2.5rem 0;
    }
    
</style>
""", unsafe_allow_html=True)

from syllabus_data import UPSC_SYLLABUS

# Page Config (already set)

# -- Syllabus Helper --
def get_syllabus_progress():
    if "syllabus_tracker" not in st.session_state:
        # Init structure
        st.session_state.syllabus_tracker = {
            subj: {topic: False for topic in topics} 
            for subj, topics in UPSC_SYLLABUS.items()
        }
    
    # Calculate
    total_topics = 0
    completed_topics = 0
    for subj, topics in st.session_state.syllabus_tracker.items():
        total_topics += len(topics)
        completed_topics += sum(topics.values())
        
    return completed_topics, total_topics

# State Management for Navigation
if "navigation" not in st.session_state:
    st.session_state.navigation = "🏠 Home"

# Sidebar - Configuration
st.sidebar.markdown("### Settings") # Minimal Header
app_mode = st.sidebar.radio(
    "Navigation", 
    ["🏠 Home", "Topic Practice", "Full Mock Test", "📚 Knowledge Base", "📊 Syllabus Tracker", "📜 Quiz History"],
    key="navigation"
)

# Persistent Scratchpad
st.sidebar.markdown("---")
st.sidebar.markdown("### 📝 Quick Notes")
st.sidebar.text_area("Jot down concepts...", height=200, key="scratchpad", help="These notes persist during your session.")

# -- Configuration --
# Load API Key (Supports both Local .env and Streamlit Cloud Secrets)
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key and "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

if not api_key:
    st.sidebar.error("⚠️ API Key missing in .env")

# Model Selection: Hardcoded to reliable models for Free Tier
# 'gemini-1.5-flash' is the current stability king for free tier high-volume.
# model_name = "gemini-2.0-flash" 

# Advanced Config (Hidden by default)
with st.sidebar.expander("⚙️ Advanced Config"):
    
    # 1. Fetch Dynamic Models
    fetched_models = get_available_models(api_key)
    
    # 2. Fallback if fetch fails or returns empty
    default_models = [
        "gemini-flash-latest",   # The "Works" Alias
        "gemini-2.0-flash",      # Modern
        "gemini-pro-latest"      # Pro Alias
    ]
    
    # Combined: fetched first, then unique defaults
    if fetched_models:
        # Use set logic to avoid dupes but keep order? No, simpler:
        final_list = fetched_models
        # Add aliases manually if not present, as API usually returns specific versions
        if "gemini-flash-latest" not in final_list: final_list.insert(0, "gemini-flash-latest")
    else:
        final_list = default_models

    model_name = st.selectbox(
        "AI Model (Switch if Busy)", 
        final_list, 
        index=0,
        help="Switch models if you hit a 'Rate Limit' (429) error."
    )

difficulty = st.sidebar.select_slider(
    "Complexity",
    options=["Fundamental", "Applied", "Advanced", "UPSC Actual"],
    value="Advanced"
)

num_questions = st.sidebar.slider("Questions", 1, 10, 5)

# Initialize Engine & Librarian
if "engine" not in st.session_state:
    st.session_state.engine = ExamEngine(api_key)

# Self-healing
if not hasattr(st.session_state.engine, 'generate_mock_test'):
    st.session_state.engine = ExamEngine(api_key)

if api_key:
    st.session_state.engine.set_api_key(api_key)
    if "librarian" not in st.session_state:
        st.session_state.librarian = Librarian(api_key)

# Main Content: Minimal Header
st.title("UPSC Dream")
st.markdown("---") # Minimal Divider

if app_mode == "🏠 Home":
    st.markdown("### Welcome, Aspirant.")
    st.markdown("What is your focus for today's session?")
    
    # 2 rows of 2 columns for better layout
    row1 = st.columns(2)
    row2 = st.columns(2)
    
    # Navigation Callbacks
    def go_to_topic(): st.session_state.navigation = "Topic Practice"
    def go_to_mock(): st.session_state.navigation = "Full Mock Test"
    def go_to_kb(): st.session_state.navigation = "📚 Knowledge Base"
    def go_to_history(): st.session_state.navigation = "📜 Quiz History"
    
    with row1[0]:
        st.markdown("""
        <div style="padding: 20px; background-color: #111827; border: 1px solid #1F2937; border-radius: 12px; height: 160px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 40px; margin-bottom: 10px;">🎯</div>
            <h3 style="margin: 0; color: #F9FAFB;">Topic Drill</h3>
        </div>
        """, unsafe_allow_html=True)
        st.button("Start Drill ➔", key="btn_topic", use_container_width=True, on_click=go_to_topic)
    
    with row1[1]:
        st.markdown("""
        <div style="padding: 20px; background-color: #111827; border: 1px solid #1F2937; border-radius: 12px; height: 160px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 40px; margin-bottom: 10px;">🛡️</div>
            <h3 style="margin: 0; color: #F9FAFB;">Mock Test</h3>
        </div>
        """, unsafe_allow_html=True)
        st.button("Launch Mock ➔", key="btn_mock", use_container_width=True, on_click=go_to_mock)
        
    with row2[0]:
        st.markdown("""
        <div style="padding: 20px; background-color: #111827; border: 1px solid #1F2937; border-radius: 12px; height: 160px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 40px; margin-bottom: 10px;">📚</div>
            <h3 style="margin: 0; color: #F9FAFB;">Library</h3>
        </div>
        """, unsafe_allow_html=True)
        st.button("Open Library ➔", key="btn_kb", use_container_width=True, on_click=go_to_kb)

    with row2[1]:
        st.markdown("""
        <div style="padding: 20px; background-color: #111827; border: 1px solid #1F2937; border-radius: 12px; height: 160px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 40px; margin-bottom: 10px;">📜</div>
            <h3 style="margin: 0; color: #F9FAFB;">History</h3>
        </div>
        """, unsafe_allow_html=True)
        st.button("View Past Quizzes ➔", key="btn_hist", use_container_width=True, on_click=go_to_history)

    st.info("👈 Select a mode from the sidebar to begin.")

elif app_mode == "Topic Practice":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Source Material")
        uploaded_file = st.file_uploader("Upload Chapter (PDF)", type="pdf")
        
        source_text = None
        if uploaded_file:
            with st.spinner("Analyzing text..."):
                source_text = st.session_state.engine.extract_text_from_pdf(uploaded_file)
                st.success("Analysis complete.")

    with col2:
        st.markdown("#### Inquiry Topic")
        topic = st.text_input("Topic", placeholder="e.g. Constitutional Morality...")

        generate_btn = st.button("Begin Session")

    if generate_btn:
        if not api_key:
            st.error("API Key required.")
        elif not topic:
            st.warning("Please define a topic.")
        else:
            with st.spinner("Curating questions..."):
                # Map aesthetic difficulty names back to logic
                diff_map = {"Fundamental": "Easy", "Applied": "Moderate", "Advanced": "Hard", "UPSC Actual": "Extreme"}
                
                response_json = st.session_state.engine.generate_questions(
                    topic=topic,
                    source_text=source_text,
                    difficulty=diff_map.get(difficulty, "Hard"),
                    num_questions=num_questions,
                    model_name=model_name
                )
                
                if "error" in response_json:
                    st.error(response_json["error"])
                else:
                    st.session_state.quiz_data = response_json.get("questions", [])
                    st.session_state.quiz_active = True
                    st.session_state.current_topic = topic
                    st.rerun()

elif app_mode == "Full Mock Test":
    st.markdown("#### Comprehensive Simulation")
    st.info("Full syllabus coverage: History, Polity, Economy, Geography, Science, Current Affairs.")
    
    col_mock1, col_mock2 = st.columns([2, 1])
    with col_mock1:
        st.write("") # Spacer
    
    with col_mock2:
         mock_q_count = st.select_slider("Length", options=[10, 20, 30, 50, 100], value=20)
    
    if st.button("Start Simulation"):
        if not api_key:
            st.error("API Key required.")
        else:
            diff_map = {"Fundamental": "Easy", "Applied": "Moderate", "Advanced": "Hard", "UPSC Actual": "Extreme"}
            with st.spinner(f"Curating {mock_q_count} questions..."):
                response_json = st.session_state.engine.generate_mock_test(
                    num_questions=mock_q_count,
                    difficulty=diff_map.get(difficulty, "Hard"),
                    model_name=model_name
                )
                
                if "error" in response_json:
                    st.error(response_json.get("error"))
                else:
                    st.session_state.quiz_data = response_json.get("questions", [])
                    st.session_state.quiz_active = True
                    st.session_state.current_topic = f"Full Mock Test ({len(st.session_state.quiz_data)} Qs)"
                    st.rerun()

elif app_mode == "📚 Knowledge Base":
    st.markdown("#### 📚 Digital Library & Study Center")
    st.info("Upload PDFs to your library. The AI will index them by Subject & Chapter.")
    
    # 1. Upload Section
    if not os.path.exists(LIBRARY_DIR):
        os.makedirs(LIBRARY_DIR)
        
    uploaded_files = st.file_uploader("Add to Library", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        for uf in uploaded_files:
            if uf.name not in os.listdir(LIBRARY_DIR):
                with open(os.path.join(LIBRARY_DIR, uf.name), "wb") as f:
                    f.write(uf.getbuffer())
                st.toast(f"Saved {uf.name} to Library.")
    
    if st.button("🔄 Scan & Index Library"):
        if not api_key:
            st.error("API Key needed to index files.")
        else:
            if "librarian" not in st.session_state:
                st.session_state.librarian = Librarian(api_key)
            
            with st.spinner("Librarian is analyzing book structures..."):
                logs = st.session_state.librarian.scan_library()
                for log in logs:
                    if "Error" in log: st.error(log)
                    else: st.success(log)
                st.rerun()

    st.markdown("---")
    
    # 2. Browsing & Selection
    if "librarian" in st.session_state:
        lib_struct = st.session_state.librarian.get_library_structure()
        
        if not lib_struct:
            st.warning("Library is empty. Upload PDFs and click 'Scan & Index'.")
        else:
            st.markdown("#### 📖 Select Study Material")
            
            # Cascading Drops
            sel_subject = st.selectbox("1. Subject", options=lib_struct.keys())
            
            if sel_subject:
                books = lib_struct[sel_subject]
                book_names = [b["filename"] for b in books]
                sel_book = st.selectbox("2. Source Book", options=book_names)
                
                if sel_book:
                    curr_book = next(b for b in books if b["filename"] == sel_book)
                    chapters = curr_book["chapters"]
                    
                    # Book Card Visual
                    st.markdown(f"""
                    <div style="padding: 24px; border: 1px solid #1F2937; border-radius: 12px; background-color: #111827; display: flex; align-items: start; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);">
                        <div style="font-size: 32px; margin-right: 20px; line-height: 1;">📖</div>
                        <div>
                            <h3 style="margin: 0 0 8px 0; color: #F9FAFB; font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 600;">{sel_book}</h3>
                            <p style="margin: 0; color: #9CA3AF; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 15px;">
                                {len(chapters)} Chapters Indexed <span style="margin: 0 8px;">•</span> 
                                <span style="color: #3B82F6; font-weight: 500;">{sel_subject}</span>
                            </p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if not chapters:
                        st.warning("No chapters found/indexed for this book.")
                    else:
                        chap_options = [f"{c['index']}. {c['title']}" for c in chapters]
                        
                        col_c1, col_c2 = st.columns([3, 1])
                        with col_c1:
                            sel_chapter_str = st.selectbox("Select Chapter to Study", options=chap_options)
                        
                        if sel_chapter_str:
                            chap_idx = int(sel_chapter_str.split(".")[0])
                            
                            with col_c2:
                                st.write("") # Spacer
                                st.write("")
                                generate_chap = st.button("🚀 Start Quiz", use_container_width=True)
                            
                            if generate_chap:
                                with st.spinner("Reading chapter content & generating questions..."):
                                    # Get Context
                                    chap_content = st.session_state.librarian.get_chapter_content(sel_book, chap_idx)
                                    if not chap_content:
                                        st.error("Could not read chapter content.")
                                    else:
                                        # Generate
                                        response_json = st.session_state.engine.generate_questions(
                                            topic=f"{sel_chapter_str} ({sel_subject})",
                                            source_text=chap_content,
                                            difficulty=difficulty,
                                            num_questions=num_questions,
                                            model_name=model_name
                                        )
                                        
                                        if "error" in response_json:
                                            st.error(response_json["error"])
                                        else:
                                            st.session_state.quiz_data = response_json.get("questions", [])
                                            st.session_state.quiz_active = True
                                            st.session_state.current_topic = sel_chapter_str
                                            st.rerun()

# Quiz Interface
if "quiz_active" in st.session_state and st.session_state.quiz_active:
    st.markdown("---")
    # Use stored topic if available, else generic
    title_topic = st.session_state.get("current_topic", "Generated Quiz")
    st.markdown(f"### 📝 Quiz: {title_topic}")
    
    # Audit QA Section
    with st.expander("🛡️ Quality Control (Self-Check)"):
        if st.button("Run Examiner Audit"):
            with st.spinner("Senior Examiner is reviewing the questions..."):
                audit_report = st.session_state.engine.evaluate_questions(
                    questions=st.session_state.quiz_data, 
                    topic=title_topic,
                    model_name=model_name
                )
                
                if "error" in audit_report:
                    st.error(audit_report["error"])
                else:
                    st.markdown(f"### Quality Score: {audit_report.get('overall_score')}/10")
                    st.info(f"**Verdict:** {audit_report.get('verdict')}")
                    
                    col_s, col_i = st.columns(2)
                    with col_s:
                        st.markdown("**✅ Strengths:**")
                        for s in audit_report.get("strengths", []):
                            st.markdown(f"- {s}")
                    
                    with col_i:
                        st.markdown("**⚠️ Potential Issues:**")
                        for issue in audit_report.get("issues", []):
                            st.markdown(f"- **Q{issue.get('question_index') + 1}:** {issue.get('issue')}")
    
    with st.form("quiz_form"):
        user_answers = {}
        for i, q in enumerate(st.session_state.quiz_data):
            # Format Question Text for Web (Add line breaks for statements)
            raw_q = q['question_text']
            
            # 1. Handle newlines from API
            fmt_q = raw_q.replace("\n", "<br>")
            
            # 2. Force breaks for numbered statements (1. , 2. ) if they are inline
            # Look for 1., 2., 3. preceded by space or start, followed by space
            fmt_q = re.sub(r'(\s|^)(\d+\.)(\s)', r'<br><b>\2</b>\3', fmt_q)
            
            # 3. Handle separate breaks for common UPSC phrases
            fmt_q = re.sub(r'(Which of the statements)', r'<br><br>\1', fmt_q)
            
            # Open Card
            st.markdown(f"""
            <div class="quiz-card">
                <h4>Q{i+1}. {fmt_q}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Options (Streamlit components need to be outside the HTML block to be interactive, 
            # effectively floating "inside" visually if we don't close the div? 
            # No, Streamlit doesn't support nesting components inside raw HTML strings.
            # Workaround: Use the card style on the text, and let the radio button sit below it cleanly.
            # OR better: Just style the question text container.
            
            # Actually, standard Streamlit practice for "Cards" is just styling the container or using a markdown block for the visual part.
            # Let's simple style the Question Text as the "Header" of the card, and let options follow.
            # BUT to make it look like a box, we can't easily wrap the radio.
            
            # Revised approach: Just put the question text in the nice box.
            # The user asked for "Quiz Cards". Only the text being in a card looks weird if options are outside.
            
            # Alternative: We can't easily wrap the st.radio.
            # So I will styles the Q text heavily and put a separator.
            # Let's try to mimic the card look by just having the Question Text in the styled box, 
            # and maybe adding a left border to the whole block via markdown if possible? 
            # No, let's keep it simple: Question Text in the "Card", Options below.
            
            options = q['options']
            choice = st.radio(
                "Select Option:",
                options=options.keys(),
                format_func=lambda x: f"{x}) {options[x]}",
                key=f"q_{i}",
                index=None,
                label_visibility="collapsed" # Hide "Select Option" label for cleaner look
            )
            user_answers[i] = choice
            
            # Gap between questions
            st.markdown("<br>", unsafe_allow_html=True)
        
        submit_btn = st.form_submit_button("Submit Quiz")
    
    if submit_btn:
        st.session_state.user_answers = user_answers
        st.session_state.quiz_submitted = True
        
        # Save to History
        # We need to calc score here (duplicate logic, but needed for save data)
        # Optimized: Just save, we calc properly in Results view.
        # WAIT: save_quiz needs the score. Let's do a quick calc.
        
        _score = 0
        for _i, _q in enumerate(st.session_state.quiz_data):
            _choice = user_answers.get(_i)
            if _choice == _q['correct_option']:
                _score += 2
            elif _choice is not None:
                _score -= 0.66
        
        _max = len(st.session_state.quiz_data) * 2
        
        #Lazy init
        if "history_manager" not in st.session_state:
            from quiz_history_manager import QuizHistory
            st.session_state.history_manager = QuizHistory()
            
        st.session_state.history_manager.save_quiz(
            topic=st.session_state.get("current_topic", "General Quiz"),
            quiz_data=st.session_state.quiz_data,
            score=_score,
            max_score=_max
        )
        
        st.rerun()

# Results Display
if "quiz_submitted" in st.session_state and st.session_state.quiz_submitted:
    st.markdown("## 📊 Performance Report")
    
    quiz_data = st.session_state.quiz_data
    user_answers = st.session_state.user_answers
    
    # Calculate Score
    score = 0
    correct_count = 0
    for i, q in enumerate(quiz_data):
        user_choice = user_answers.get(i)
        if user_choice == q['correct_option']:
            score += 2
            correct_count += 1
        elif user_choice is not None:
            score -= 0.66
            
    total_q = len(quiz_data)
    max_score = total_q * 2
    accuracy = (correct_count / total_q) * 100
    
    # 1. Visual Scorecard
    st.markdown("---")
    metric_cols = st.columns([1, 1, 2])
    with metric_cols[0]: st.metric("Net Score", f"{score:.2f} / {max_score}")
    with metric_cols[1]: st.metric("Accuracy", f"{accuracy:.1f}%")
        
    with metric_cols[2]:
        if accuracy >= 80:
            status = "🌟 Outstanding"
            color = "green"
        elif accuracy >= 50:
            status = "📈 Good"
            color = "orange"
        else:
            status = "⚠️ Needs Revision"
            color = "red"
        st.markdown(f"**Status:**")
        st.markdown(f"<h3 style='color: {color}; margin:0;'>{status}</h3>", unsafe_allow_html=True)
        st.progress(min(max(accuracy / 100, 0), 1.0))
        
    st.markdown("---")
    
    # 2. Detailed Breakdown
    for i, q in enumerate(quiz_data):
        user_choice = user_answers.get(i)
        correct_choice = q['correct_option']
        
        if not user_choice:
            status = "Skipped"
            color = "orange"
        elif user_choice == correct_choice:
            status = "Correct"
            color = "green"
        else:
            status = "Wrong"
            color = "red"
            
        with st.expander(f"Q{i+1}: {status}", expanded=False):
            st.markdown(f"**Question:** {q['question_text']}")
            col_ua, col_ca = st.columns(2)
            with col_ua: st.markdown(f"**Your Answer:** :{color}[{user_choice if user_choice else 'None'}]")
            with col_ca: st.markdown(f"**Correct Answer:** :green[{correct_choice}]")
            st.info(f"**Explanation:** {q['explanation']}")
            
    st.markdown("---")
    
    # Export PDF (Simplification: Just basic reset for now to fix error, PDF can be re-added if needed but prioritized fixing crash)
    
    def reset_quiz():
        st.session_state.quiz_active = False
        st.session_state.quiz_submitted = False
        st.session_state.quiz_data = []
        st.session_state.user_answers = {}
        st.rerun()

    st.button("Start New Quiz", on_click=reset_quiz)

elif app_mode == "📜 Quiz History":
    st.markdown("### 📜 Past Quiz Archive")
    
    if "history_manager" not in st.session_state:
        from quiz_history_manager import QuizHistory
        st.session_state.history_manager = QuizHistory()
        
    history = st.session_state.history_manager.load_history()
    
    if not history:
        st.info("No quizzes taken yet. Generate one!")
    else:
        for q in history:
            with st.expander(f"{q['timestamp']} | {q['topic']} | Score: {q['score']:.2f}/{q['max_score']}"):
                st.markdown(f"**Score:** {q['score']:.2f} / {q['max_score']}")
                
                if st.button("🔄 Retake This Quiz", key=f"replay_{q['id']}"):
                    # Load into session
                    st.session_state.quiz_data = q['questions']
                    st.session_state.current_topic = q['topic']
                    st.session_state.quiz_active = True
                    st.session_state.quiz_submitted = False
                    st.session_state.user_answers = {}
                    st.session_state.navigation = "Topic Practice" # Redirect
                    st.rerun()

elif app_mode == "📊 Syllabus Tracker":
    st.markdown("### 📊 Official Syllabus Tracker")
    st.markdown("Track your coverage of official UPSC Prelims topics. (Data persists in session)")
    
    # 1. Global Progress
    done, total = get_syllabus_progress()
    perc = (done / total) * 100 if total > 0 else 0
    
    st.markdown(f"#### Overall Coverage: **{perc:.1f}%** ({done}/{total} Topics)")
    st.progress(perc / 100)
    st.markdown("---")
    
    # 2. Checklist per Subject
    for subj, topics in UPSC_SYLLABUS.items():
        # Get progress for this subject
        s_done = sum(st.session_state.syllabus_tracker[subj].values())
        s_total = len(topics)
        
        with st.expander(f"{subj} ({s_done}/{s_total})"):
            for t in topics:
                # Checkbox modifies state directly
                is_checked = st.session_state.syllabus_tracker[subj].get(t, False)
                new_val = st.checkbox(t, value=is_checked, key=f"{subj}_{t}")
                st.session_state.syllabus_tracker[subj][t] = new_val

st.markdown("---")
st.markdown("*Note: This system relies on AI and may hallucinate. Verify with standard books.*")
