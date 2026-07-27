import uvicorn
import os
import sys

# Add the current directory to python path to ensure import pathing works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("===================================================")
    echo_msg = "Starting AI Resume Analyzer Dev Server..."
    print(echo_msg)
    print("Navigate to http://127.0.0.1:8000 in your browser.")
    print("===================================================\n")
    
    # Auto-open browser automatically in a background thread
    import threading
    import time
    import webbrowser

    def open_browser():
        time.sleep(1.5) # Wait for uvicorn to bind and start listening
        webbrowser.open("http://127.0.0.1:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(
        "backend.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )
