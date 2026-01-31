import streamlit as st
import os
import re
from engine import ExamEngine
from librarian import Librarian, LIBRARY_DIR
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.graphics.shapes import Drawing, Rect, Path
from reportlab.pdfgen import canvas

# Page Config
st.set_page_config(
    page_title="UPSC Exam Replication Engine",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Custom CSS for "Premium" feel (Navy, Gold & Clean White)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    :root {
        --primary-color: #FAFAFA;
        --accent-color: #2D8CFF; /* Electric Blue */
        --bg-color: #0F1115; /* Matte Dark */
        --text-color: #FAFAFA;
        --card-bg: #181B21; /* Panel Dark */
        --sidebar-bg: #0F1115;
        --input-bg: #181B21;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-color);
    }

    /* Main App Background */
    .stApp {
        background-color: var(--bg-color);
        background-image: radial-gradient(circle at 50% 0%, #1a202c 0%, #0F1115 50%);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: 1px solid #1F2937;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: #94A3B8 !important; /* Muted Text */
    }
    
    /* Input Fields */
    .stTextInput > div > div > input, 
    .stSelectbox > div > div > div, 
    .stMultiSelect > div > div > div {
        background-color: var(--input-bg);
        color: #FAFAFA;
        border: 1px solid #2D3748;
        border-radius: 12px; /* Rounded inputs */
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--accent-color);
        box-shadow: 0 0 0 2px rgba(45, 140, 255, 0.2);
    }
    p, li, label, .stMarkdown {
        color: #E2E8F0 !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2D8CFF 0%, #2563EB 100%); /* Blue Gradient */
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 14px 0 rgba(45, 140, 255, 0.39);
        padding: 0.6rem 1.2rem;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px 0 rgba(45, 140, 255, 0.39);
        color: #FFF;
    }

    /* Headings */
    h1, h2, h3, h4, h5 {
        color: #FFF !important;
        font-weight: 800;
        letter-spacing: -0.025em;
    }

    /* Custom Card Class for Quiz */
    .quiz-card {
        background-color: var(--card-bg);
        border: 1px solid #2D3748;
        border-radius: 20px; /* Highly rounded cards */
        padding: 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        border-left: none; /* Removed the left accent for full card look */
        position: relative;
        overflow: hidden;
    }
    /* "Glass" accent on top of card */
    .quiz-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #2D8CFF, #60A5FA);
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: var(--card-bg);
        color: #FAFAFA !important;
        border-radius: 10px;
        border: 1px solid #2D3748;
    }
    
</style>
""", unsafe_allow_html=True)

# Sidebar - Configuration
st.sidebar.title("⚙️ Exam DNA Settings")
app_mode = st.sidebar.radio("Select Mode", ["Topic Practice", "Full Mock Test", "📚 Knowledge Base"], help="Topic Practice: Deep dive into one topic.\\nFull Mock: Mixed questions across all subjects.\\nKnowledge Base: Library & Chapter-wise tests.")

api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API Key here.")
if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

model_name = st.sidebar.selectbox(
    "AI Model",
    options=["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-flash-latest", "gemini-pro-latest"],
    index=0,
    help="Switch models if you encounter rate limits (429 errors)."
)

difficulty = st.sidebar.select_slider(
    "Difficulty Level",
    options=["Easy", "Moderate", "Hard", "Extreme (UPSC 2023 Level)"],
    value="Hard"
)

num_questions = st.sidebar.slider("Number of Questions", 1, 10, 5)

# Initialize Engine & Librarian
if "engine" not in st.session_state:
    st.session_state.engine = ExamEngine(api_key)

# Self-healing
if not hasattr(st.session_state.engine, 'generate_mock_test') or not hasattr(st.session_state.engine, 'analyze_structure'):
    st.session_state.engine = ExamEngine(api_key)

if api_key:
    st.session_state.engine.set_api_key(api_key)
    # Initialize Librarian
    if "librarian" not in st.session_state:
        st.session_state.librarian = Librarian(api_key)

# Main Content
st.title("🇮🇳 UPSC Exam Replication Engine")
st.markdown("### *Think like the Examiner.*")

col1, col2 = st.columns([1, 1])

if app_mode == "Topic Practice":
    with col1:
        st.markdown("#### 1. Context Source (Optional)")
        uploaded_file = st.file_uploader("Upload NCERT/Reference Chapter (PDF)", type="pdf")
        
        source_text = None
        if uploaded_file:
            with st.spinner("Extracting text from PDF..."):
                source_text = st.session_state.engine.extract_text_from_pdf(uploaded_file)
                st.success("PDF processed successfully!")
                with st.expander("View Extracted Text"):
                    st.text(source_text[:1000] + "...")

    with col2:
        st.markdown("#### 2. Target Topic")
        topic = st.text_input("Enter Topic (e.g., 'Revolt of 1857', 'Monetary Policy')", placeholder="Type a topic...")

        generate_btn = st.button("Generate Questions")

    if generate_btn:
        if not api_key:
            st.error("Please enter your Gemini API Key in the sidebar to proceed.")
        elif not topic:
            st.warning("Please enter a topic.")
        else:
            with st.spinner("Simulating Examiner Mindset... Generating Questions..."):
                response_json = st.session_state.engine.generate_questions(
                    topic=topic,
                    source_text=source_text,
                    difficulty=difficulty,
                    num_questions=num_questions,
                    model_name=model_name
                )
                
                if "error" in response_json:
                    st.error(response_json["error"])
                else:
                    st.session_state.quiz_data = response_json.get("questions", [])
                    st.session_state.quiz_active = True
                    # Store topic for results
                    st.session_state.current_topic = topic
                    st.rerun()

elif app_mode == "Full Mock Test":
    st.markdown("#### 🛡️ Full-Length Mock Simulation")
    st.info("This mode generates a balanced paper covering History, Polity, Economy, Geography, Science, and Current Affairs.")
    
    # Override num_questions for mock if needed, or use a separate slider?
    # Let's use a specific slider for mock length to allow larger sets
    col_mock1, col_mock2 = st.columns([2, 1])
    with col_mock1:
        st.markdown("The system will iterate through all major UPSC subjects to create a comprehensive test.")
    
    with col_mock2:
         mock_q_count = st.select_slider("Total Questions", options=[10, 20, 30, 50, 100], value=20)
    
    if st.button("Start Full Mock Test"):
        if not api_key:
            st.error("Please enter your Gemini API Key in the sidebar.")
        else:
            with st.spinner(f"Generating {mock_q_count} questions across all subjects... This may take a moment."):
                response_json = st.session_state.engine.generate_mock_test(
                    num_questions=mock_q_count,
                    difficulty=difficulty,
                    model_name=model_name
                )
                
                if "error" in response_json:
                    st.error(response_json.get("error"))
                else:
                    st.session_state.quiz_data = response_json.get("questions", [])
                    st.session_state.quiz_active = True
                    st.session_state.current_topic = f"Full Mock Test ({len(st.session_state.quiz_data)} Qs)"
                    st.rerun()

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
                    <div style="padding: 20px; border: 1px solid #2D3748; border-radius: 12px; background-color: #181B21; display: flex; align-items: center; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);">
                        <div style="font-size: 40px; margin-right: 20px;">📕</div>
                        <div>
                            <h3 style="margin: 0; color: #FAFAFA; font-weight: 700;">{sel_book}</h3>
                            <p style="margin: 5px 0 0 0; color: #94A3B8; font-size: 14px;">{len(chapters)} Chapters Indexed • Subject: <span style="color: #2D8CFF;">{sel_subject}</span></p>
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
        st.rerun()

# Results Display
if "quiz_submitted" in st.session_state and st.session_state.quiz_submitted:
    st.markdown("## 📊 Results")
    quiz_data = st.session_state.quiz_data
    user_answers = st.session_state.user_answers
    
    score = 0
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    
    for i, q in enumerate(quiz_data):
        user_choice = user_answers.get(i)
        correct_choice = q['correct_option']
        
        color = "black"
        status = "Skipped"
        
        if not user_choice:
            skipped_count += 1
            color = "orange"
        elif user_choice == correct_choice:
            score += 2
            correct_count += 1
            color = "green"
            status = "Correct (+2)"
        else:
            score -= 0.66
            wrong_count += 1
            color = "red"
            status = "Wrong (-0.66)"
            
        with st.expander(f"Q{i+1}: {status}", expanded=False):
            st.markdown(f"**Question:** {q['question_text']}")
            st.markdown(f"**Your Answer:** :{color}[{user_choice if user_choice else 'None'}]")
            st.markdown(f"**Correct Answer:** :green[{correct_choice}]")
            st.markdown(f"**Explanation:** {q['explanation']}")
    
    max_score = len(quiz_data) * 2
    st.markdown(f"### 🏆 Final Score: {score:.2f} / {max_score}")
    st.markdown(f"✅ Correct: **{correct_count}** | ❌ Wrong: **{wrong_count}** | ⏭️ Skipped: **{skipped_count}**")
    
    # Export PDF
    # Use stored topic
    pdf_topic = st.session_state.get("current_topic", topic if 'topic' in locals() else "UPSC Mock")
    pdf_file = create_pdf(quiz_data, user_answers, pdf_topic, difficulty, score, max_score)
    st.download_button(
        label="📄 Download Results & Explanations (PDF)",
        data=pdf_file,
        file_name=f"upsc_results_{pdf_topic.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

    def reset_quiz():
        st.session_state.quiz_active = False
        st.session_state.quiz_submitted = False
        st.session_state.quiz_data = []
        st.session_state.user_answers = {}

    st.button("Start New Quiz", on_click=reset_quiz)

st.markdown("---")
st.markdown("*Note: This system relies on AI and may hallucinate. Verify with standard books.*")
