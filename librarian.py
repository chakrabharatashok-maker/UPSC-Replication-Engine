import os
import json
import hashlib
from engine import ExamEngine

LIBRARY_DIR = "library"
INDEX_FILE = "library_index.json"

class Librarian:
    def __init__(self, api_key):
        self.engine = ExamEngine(api_key)
        self.index = self._load_index()

    def _load_index(self):
        if os.path.exists(INDEX_FILE):
             try:
                 with open(INDEX_FILE, 'r') as f:
                     return json.load(f)
             except:
                 return {"files": {}}
        return {"files": {}}

    def _save_index(self):
        with open(INDEX_FILE, 'w') as f:
            json.dump(self.index, f, indent=2)

    def _calculate_file_hash(self, filepath):
        """Simple hash to detect file changes."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    def scan_library(self):
        """
        Scans the LIBRARY_DIR for new or modified files.
        Returns a list of logs/status updates.
        """
        if not os.path.exists(LIBRARY_DIR):
            os.makedirs(LIBRARY_DIR)
            return ["Created library directory."]

        logs = []
        files = [f for f in os.listdir(LIBRARY_DIR) if f.lower().endswith('.pdf')]
        
        current_files = set(files)
        indexed_files = set(self.index["files"].keys())
        
        # Detect Removed Files
        removed = indexed_files - current_files
        for f in removed:
            del self.index["files"][f]
            logs.append(f"🗑️ Removed missing file from index: {f}")

        # Detect New/Modified Files
        for filename in files:
            filepath = os.path.join(LIBRARY_DIR, filename)
            file_hash = self._calculate_file_hash(filepath)
            
            # Check if needs indexing
            if filename not in self.index["files"] or self.index["files"][filename].get("hash") != file_hash:
                logs.append(f"🔍 Indexing new file: {filename}...")
                
                # 1. Extract first 15 pages (TOC usually here)
                toc_text = self.engine.extract_text_from_pdf(filepath, start_page=1, end_page=15)
                
                # 2. Analyze Structure
                structure = self.engine.analyze_structure(toc_text, filename)
                
                if "error" in structure:
                    logs.append(f"❌ Error indexing {filename}: {structure['error']}")
                else:
                    self.index["files"][filename] = {
                        "hash": file_hash,
                        "subject": structure.get("subject", "Unknown"),
                        "chapters": structure.get("chapters", []),
                        "path": filepath
                    }
                    logs.append(f"✅ Successfully indexed {filename} ({len(structure.get('chapters', []))} chapters found).")
                    self._save_index()
            else:
                # logs.append(f"Skipping {filename} (already indexed).")
                pass

        self._save_index()
        return logs

    def get_library_structure(self):
        """
        Returns a hierarchical structure: Subject -> File -> Chapters
        """
        structure = {}
        for filename, data in self.index["files"].items():
            subj = data.get("subject", "Uncategorized")
            if subj not in structure:
                structure[subj] = []
            
            structure[subj].append({
                "filename": filename,
                "filepath": data.get("path"),
                "chapters": data.get("chapters", [])
            })
        return structure

    def get_chapter_content(self, filename, chapter_index):
        """
        Retrieves the text content for a specific chapter.
        """
        if filename not in self.index["files"]:
            return None
        
        file_data = self.index["files"][filename]
        chapters = file_data.get("chapters", [])
        
        target_chapter = next((c for c in chapters if c["index"] == chapter_index), None)
        
        if not target_chapter:
            return None
            
        start = target_chapter.get("page_start", 1)
        end = target_chapter.get("page_end", None)
        
        # Safety: If end is 0 or less than start, default to start + 10 or None
        if end and end < start:
            end = start + 10
            
        filepath = os.path.join(LIBRARY_DIR, filename)
        return self.engine.extract_text_from_pdf(filepath, start_page=start, end_page=end)
