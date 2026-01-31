import os
import google.generativeai as genai
import PyPDF2
from dotenv import load_dotenv
import json
import time
import random

load_dotenv()

# 🔴 1️⃣ MASTER SYSTEM PROMPT
MASTER_SYSTEM_PROMPT = """
You are an Exam Replication Intelligence Engine built exclusively for
UPSC and State Public Service Commission (PCS) examinations.

You are NOT a teacher, coach, mentor, or explainer.
You are a paper-setter simulation system.

Your sole purpose is to replicate:
- the mindset of UPSC and State PCS examiners
- the conceptual depth of questions
- the ambiguity and elimination logic
- the evolving pattern of competitive examinations

Your outputs must feel indistinguishable from actual UPSC / PCS exam material.

Ultimate Objective:
Train aspirants to THINK like the examiner, not to memorize content.

A student who practices exclusively using this system should develop
the conceptual sharpness, elimination ability, and exam temperament
required to clear Prelims and later Mains.

📚 AUTHORITATIVE KNOWLEDGE BOUNDARY
You are strictly constrained to:
- NCERT textbooks (Class 6–12)
- Standard reference books used by serious aspirants
- Official UPSC & State PCS question papers (last 30 years)
- Government publications (PIB, Economic Survey, Budget, official reports)
- International institutional reports only where UPSC-relevant

You must NOT use:
- coaching shortcuts
- guess tricks
- speculative facts
- motivational language
- unverified internet knowledge

Hallucination is unacceptable.
If unsure, avoid the claim.

🧠 CORE BEHAVIOR RULES
Always think like an examiner, never like a student.

Prefer:
- conceptual testing over factual recall
- elimination-based logic
- multi-concept linkage
- plausible distractors

Avoid:
- oversimplification
- beginner-friendly tone
- textbook-style explanations
- absolute statements unless constitutionally/factually exact

🏁 GOLDEN RULE
Before finalizing any output, internally ask:

“Would this confuse a well-prepared aspirant?”

If yes → proceed.
If no → regenerate.

🔵 2️⃣ DEVELOPER PROMPT
(controls HOW the system behaves)
This system is in its initial build phase.

Priorities (in order):
1. Question quality
2. Exam authenticity
3. Conceptual depth
4. Elimination logic

Deprioritize:
- UI concerns
- speed
- volume
- engagement features

Content Ingestion Rules:
- Accept NCERTs, standard books, and PYQs as structured or unstructured text
- Treat PYQs as the highest-priority signal
- Extract patterns, not templates

Question Generation Rules (Prelims):
- Questions must be original (non-derivative)
- Use authentic UPSC language:
    • “Consider the following statements”
    • “Which of the above is/are correct”
    • “With reference to”
- Every option must appear plausible
- Avoid memory-based one-liners unless historically UPSC-relevant

Explanation Rules:
- Explicitly explain:
    • why the correct option is correct
    • why each incorrect option is incorrect
- Explanations must aid elimination thinking
- Map explanations to a source (book + chapter OR official document)

Difficulty Calibration:
- Label every question:
    Easy / Moderate / Difficult / Extreme
- Benchmark against UPSC 2020–2024 standards
"""

class ExamEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def set_api_key(self, api_key):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

    def _call_with_retry(self, func, *args, **kwargs):
        """Exponential backoff retry wrapper for API calls."""
        max_retries = 5
        base_delay = 5
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "resource exhausted" in error_str:
                    if attempt < max_retries:
                        sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                        # Cap at 60s wait
                        sleep_time = min(sleep_time, 60)
                        print(f"⚠️ Rate limit hit. Retrying in {sleep_time:.2f}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise Exception("Rate limit exceeded. The model is too busy. Please wait 2 minutes.")
                else:
                    # Non-retryable error
                    raise e

    def extract_text_from_pdf(self, pdf_file, start_page=1, end_page=None):
        """
        Extracts text from a PDF. Can specify a page range (1-indexed).
        If end_page is None, reads until the end.
        """
        try:
            reader = None
            if isinstance(pdf_file, str):
                # File path
                f = open(pdf_file, 'rb')
                reader = PyPDF2.PdfReader(f)
                # Note: We are not closing f here immediately if we return text, so relying on GC or context manager is better.
                # But for simple extraction, we read all and close.
                # Actually, PyPDF2 is lazy. Let's read into memory.
            else:
                # File-like object
                reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            total_pages = len(reader.pages)
            
            # Adjust 1-based index to 0-based
            start_idx = max(0, start_page - 1)
            end_idx = total_pages if end_page is None else min(total_pages, end_page)
            
            for i in range(start_idx, end_idx):
                text += reader.pages[i].extract_text() + "\n"
            
            if isinstance(pdf_file, str):
                f.close()
                
            return text
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    def generate_questions(self, topic, source_text=None, difficulty="Hard", num_questions=5, model_name="gemini-2.0-flash"):
        if not self.api_key:
            return "Error: API Key not configured."
        
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            return f"Error initializing model: {str(e)}"

        prompt = f"""
        {MASTER_SYSTEM_PROMPT}

        Generate {num_questions} UPSC Prelims-level questions on the topic: '{topic}'.
        Difficulty Level: {difficulty}

        Constraints:
        - Use the provided source text as context if available.
        - Follow the 'Question Generation Rules' strictly.
        - Ensure 'elimination logic' is required to solve.
        
        Output Format:
        Return a valid JSON object with the following structure:
        {{
            "questions": [
                {{
                    "question_text": "The full question stem, INCLUDING the numbered statements (1., 2., 3.) and the question asking which are correct.",
                    "options": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
                    "correct_option": "A",
                    "explanation": "..."
                }}
            ]
        }}
        
        Source Context (if any):
        {source_text if source_text else "N/A (Use internal knowledge base constrained to authoritative sources)"}
        """

        try:
            # Wrapped Call
            response = self._call_with_retry(
                model.generate_content, 
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            text = response.text
            # Clean up markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text)
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                 return {"error": "⚠️ **Error: Rate limit exceeded (429).**\n\nThe AI model is currently busy. Please try:\n1. Switching to a different model in the sidebar.\n2. Waiting for a minute."}
            return {"error": f"Error generating content: {str(e)}"}

    def generate_mock_test(self, num_questions=30, difficulty="Hard", model_name="gemini-2.0-flash"):
        """
        Generates a balanced mock test across key UPSC subjects.
        """
        subjects = [
            "Ancient & Medieval History",
            "Modern Indian History", 
            "Indian Polity & Governance",
            "Indian Economy",
            "Geography (Physical & Indian)",
            "Environment & Ecology",
            "Science & Technology",
            "Current Events (Last 12 Months)"
        ]
        
        # Distribute questions
        q_per_subject = max(1, num_questions // len(subjects))
        remaining = num_questions % len(subjects)
        
        all_questions = []
        errors = []
        
        for i, subject in enumerate(subjects):
            count = q_per_subject + (1 if i < remaining else 0)
            if count == 0: continue
            
            # Generate for this subject
            # We use a slightly modified prompt concept by calling generate_questions with the subject as topic
            response = self.generate_questions(
                topic=f"{subject} (UPSC Prelims focus)", 
                difficulty=difficulty, 
                num_questions=count, 
                model_name=model_name
            )
            
            if "questions" in response:
                all_questions.extend(response["questions"])
            elif "error" in response:
                errors.append(f"{subject}: {response['error']}")
                # If rate limit, we strictly stop
                if "Rate limit" in response["error"]:
                     return response
            
            # Rate Limit Safety Valve: Sleep 5s between subjects to stay under 15 RPM
            # 8 subjects * 5s = 40s total gen time, but safe.
            time.sleep(5)
        
        if not all_questions:
            return {"error": "Failed to generate any questions.\nDetails:\n" + "\n".join(errors)}
            
        return {"questions": all_questions}

    def evaluate_questions(self, questions, topic, model_name="gemini-2.0-flash"):
        """
        Audits the generated questions using a 'Critic' persona to ensure high quality.
        """
        if not self.api_key:
            return {"error": "API Key not configured."}
            
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            return {"error": f"Error initializing model: {str(e)}"}

        questions_str = json.dumps(questions, indent=2)
        
        prompt = f"""
        You are a Senior Reviewer for UPSC Prelims Examination questions.
        
        Analyze the following set of {len(questions)} questions on '{topic}' produced by a junior setter.
        
        Your Job:
        1. Score the set out of 10 based on:
           - Conceptual Depth (Does it test understanding or just facts?)
           - Ambiguity (Are statements clear? Is elimination logic possible?)
           - Adherence to Recent Trend (2023-24 Pattern: 'Only one', 'Only two' types, Match pairs)
           
        2. Identify specific flaws in Question Number X (if any).
        
        3. Providing a Verdict: "Approved", "Needs Polish", or "Rejected".
        
        INPUT QUESTIONS JSON:
        {questions_str}
        
        OUTPUT FORMAT (JSON):
        {{
            "overall_score": 8,
            "verdict": "Approved",
            "strengths": ["...", "..."],
            "issues": [
                {{ "question_index": 0, "issue": "Too factual, options are too easy." }}
            ]
        }}
        """
        
        try:
            response = self._call_with_retry(
                model.generate_content, 
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}

        prompt = f"""
        You are a Senior Chief Examiner for UPSC (Union Public Service Commission).
        Your task is to AUDIT the quality of the following mock questions generated for the topic: '{topic}'.

        Questions Data:
        {questions_str}

        CRITERIA FOR AUDIT:
        1. Relevance: Are they strictly relevant to UPSC Prelims? (No generic GK)
        2. Difficulty: Are they challenging enough? (Avoid direct fact retrieval)
        3. Elimination Logic: Do options allow smart elimination?
        4. Ambiguity: Are statements precise and non-ambiguous?

        OUTPUT FORMAT:
        Return a valid JSON object:
        {{
            "overall_score": <int 1-10>,
            "verdict": "<Short summary text>",
            "issues": [
                {{"question_index": <int>, "issue": "..."}}
            ],
            "strengths": ["...", "..."]
        }}
        """

        try:
            response = model.generate_content(prompt)
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text)
        except Exception as e:
             return {"error": f"Error evaluating content: {str(e)}"}

    def analyze_structure(self, text, filename, model_name="gemini-2.0-flash"):
        """
        Analyzes the Table of Contents text to extract Subject, Chapters, and Page Ranges.
        Used by the Librarian. Includes retry logic for 429 errors.
        """
        import time 
        
        if not self.api_key:
            return {"error": "API Key not configured."}
            
        # Try a sequence of models if primary fails
        models_to_try = [model_name, "gemini-flash-latest", "gemini-2.0-flash-lite"]
        
        prompt = f"""
        You are an expert Librarian and Archiver.
        Your task is to analyze the following text, which is the beginning (Table of Contents) of a PDF file named '{filename}'.
        
        Extract the structured hierarchy of the content.
        
        Text Content:
        {text[:15000]}  # Limit context window just in case
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "subject": "Inferred Genric Subject (e.g., Indian Polity, Modern History)",
            "chapters": [
                {{
                    "index": 1,
                    "title": "Chapter Title",
                    "topics": ["Sub-topic 1", "Sub-topic 2"], 
                    "page_start": <int (inferred)>,
                    "page_end": <int (inferred_next_start - 1)>
                }}
            ]
        }}
        
        Rules:
        - If page numbers are not explicitly mentioned, estimate or leave 0.
        - 'topics' is optional, extract if available.
        - Return ONLY valid JSON.
        """
        
        for model_try in models_to_try:
            try:
                genai_model = genai.GenerativeModel(model_try)
                
                # Retry loop for 429 within the same model
                for attempt in range(3):
                    try:
                        response = genai_model.generate_content(prompt)
                        clean_text = response.text
                        if "```json" in clean_text:
                            clean_text = clean_text.split("```json")[1].split("```")[0]
                        elif "```" in clean_text:
                            clean_text = clean_text.split("```")[1].split("```")[0]
                        
                        return json.loads(clean_text)
                    except Exception as inner_e:
                        if "429" in str(inner_e):
                            time.sleep(2 * (attempt + 1)) # Backoff: 2s, 4s, 6s
                            continue
                        else:
                            raise inner_e # Break to next model if not 429
                            
            except Exception as e:
                # If all retries failed or other error, try next model
                continue
                
        return {"error": "Failed to analyze structure after multiple retries (Rate Limit 429). Try again later."}
