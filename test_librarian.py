import os
import sys
from librarian import Librarian

def test_librarian():
    print("🔍 Testing Librarian Logic...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No API Key found.")
        return

    lib = Librarian(api_key)
    
    # Check if sample file exists
    sample_path = "library/sample_polity_ncert.pdf"
    if not os.path.exists(sample_path):
        print("⚠️ Sample file not found. Creating it...")
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_path)
        c.drawString(100, 800, "Table of Contents")
        c.save()
        
    print(f"📂 Scanning library (Files: {os.listdir('library')})...")
    logs = lib.scan_library()
    
    print("\n📝 Operation Logs:")
    for log in logs:
        print(f" - {log}")
        
    print("\n📚 Validating Index...")
    struct = lib.get_library_structure()
    print(struct)

if __name__ == "__main__":
    test_librarian()
