import os
from engine import ExamEngine
import json

def test_ncert_logic():
    print("🚀 Starting Logic Verification with NCERT Sample...")
    
    # 1. Initialize Engine
    engine = ExamEngine()
    if not engine.api_key:
        print("❌ Error: API Key not found.")
        return

    # 2. Simulate NCERT Content (Source: NCERT Class 10 Polity - Federalism)
    ncert_text = """
    Federalism is a system of government in which the power is divided between a central authority and various constituent units of the country. 
    Usually, a federation has two levels of government. One is the government for the entire country that is usually responsible for a few subjects of common national interest. 
    The others are governments at the level of provinces or states that look after much of the day-to-day administering of their state. 
    Both these levels of governments enjoy their power independent of the other.
    
    Key features of federalism:
    1. There are two or more levels (or tiers) of government.
    2. Different tiers of government govern the same citizens, but each tier has its own JURISDICTION in specific matters of legislation, taxation and administration.
    3. The jurisdictions of the respective levels or tiers of government are specified in the constitution.
    4. The fundamental provisions of the constitution cannot be unilaterally changed by one level of government.
    """
    
    print("\n📚 Context provided: NCERT Class 10 (Federalism)")
    
    # 3. Generate Questions
    print("🧠 Generating questions based on context...")
    response = engine.generate_questions(
        topic="Federalism",
        source_text=ncert_text,
        difficulty="Moderate",
        num_questions=2,
        model_name="gemini-flash-latest"
    )

    if "error" in response:
        print(f"❌ Error during generation: {response['error']}")
        return

    # 4. Verify Output
    questions = response.get("questions", [])
    if not questions:
        print("❌ Assessment Failed: No questions returned.")
        return

    print(f"\n✅ Successfully generated {len(questions)} questions.\n")
    
    for i, q in enumerate(questions):
        print(f"🔹 Question {i+1}:")
        print(f"   {q['question_text']}")
        print(f"   Options: {q['options']}")
        print(f"   Correct: {q['correct_option']}")
        print(f"   Explanation: {q['explanation']}")
        print("-" * 50)
        
        # Validation Checks
        if "federal" not in q['question_text'].lower() and "government" not in q['question_text'].lower():
            print("   ⚠️  Warning: Question might not be strictly relevant to context.")
        
        if len(q['explanation']) < 20:
             print("   ⚠️  Warning: Explanation is too short.")
        else:
            print("   ✅ Explanation length looks good.")

    print("\n🚀 logic_verification_complete.")

if __name__ == "__main__":
    test_ncert_logic()
