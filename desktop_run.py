import os
import sys
import streamlit.web.cli as stcli

def resolve_path(path):
    if getattr(sys, "frozen", False):
        # If running as compiled exe, look in temporary _MEIPASS folder
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    # Point to the internal app.py
    app_path = resolve_path("app.py")
    
    # Set arguments for streamlit run
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.headless=true",  # Don't show generic server info
    ]
    
    # Run Streamlit
    print(f"🚀 Launching UPSC Exam Engine from: {app_path}")
    sys.exit(stcli.main())
