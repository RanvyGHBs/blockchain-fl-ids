"""
Captures genuine application screenshots of the running Streamlit dashboard
using native headless Chrome CLI.
"""

import os
import sys
import time
import subprocess
import urllib.request

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "submission_report", "figures"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False

def main():
    print("[*] Starting Streamlit dashboard on port 8501...")
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.serverAddress=localhost",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        url = "http://localhost:8501"
        print(f"[*] Waiting for {url} to become ready...")
        ready = wait_for_server(url, timeout=35)
        if not ready:
            print("[-] Streamlit server did not become ready in time.")
            return

        print("[+] Streamlit server is active!")
        time.sleep(5)  # Allow initial render to stabilize

        screenshots = [
            ("dashboard_overview.png", "http://localhost:8501"),
        ]

        for filename, target_url in screenshots:
            out_path = os.path.join(OUTPUT_DIR, filename)
            chrome_cmd = [
                CHROME_PATH,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size=1920,1080",
                f"--screenshot={out_path}",
                target_url
            ]
            print(f"[*] Capturing screenshot: {filename}...")
            res = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=30)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                print(f"[+] Successfully captured: {out_path} ({os.path.getsize(out_path)} bytes)")
            else:
                print(f"[-] Failed to capture {filename}: {res.stderr}")

    finally:
        print("[*] Stopping Streamlit server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[+] Streamlit process closed.")

if __name__ == "__main__":
    main()
