
import subprocess, sys, os

# Pracuj z folderu projektu
os.chdir(os.path.dirname(os.path.abspath(__file__)))

data_path = os.path.join("data", "items_kfc.csv")
if not os.path.exists(data_path):
    print("[!] Brak data/items_kfc.csv — wgraj najpierw swój plik z danymi (CSV).")
    sys.exit(1)

cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=false"]
print(">>> Running:", " ".join(cmd))
subprocess.run(cmd, check=False)
