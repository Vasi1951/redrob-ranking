import sys
import subprocess
import os

if __name__ == "__main__":
    # Get directory of current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rank_script = os.path.join(current_dir, "rank.py")
    
    # Forward all command line arguments to rank.py
    cmd = [sys.executable, rank_script] + sys.argv[1:]
    
    # Run and exit with the same code
    res = subprocess.run(cmd)
    sys.exit(res.returncode)
