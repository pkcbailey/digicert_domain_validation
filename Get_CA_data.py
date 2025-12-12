#!/usr/bin/env python3

import subprocess
import sys
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def remove_old_data_files():
    files_to_remove = [
        "data/combined_domains.csv",
        "data/digicert_domains.csv",
        "data/sectigo_domains.csv"
    ]
    for filepath in files_to_remove:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Removed old file: {filepath}")
            except Exception as e:
                logger.error(f"Error removing {filepath}: {e}")
        else:
            logger.info(f"File not found (skipped): {filepath}")

def run_script(script_name):
    try:
        logger.info(f"Starting {script_name}...")
        result = subprocess.run([sys.executable, script_name], check=True)
        logger.info(f"{script_name} finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{script_name} failed with exit code {e.returncode}.")
        return False

def main():
    # Remove old data files before running jobs
    remove_old_data_files()

    jobs = ["sectigo_get_domains.py", "digicert_get_domains.py"]

    # Run Sectigo and DigiCert jobs in parallel
    procs = []
    for job in jobs:
        logger.info(f"Launching {job} in background...")
        p = subprocess.Popen([sys.executable, job])
        procs.append((job, p))

    # Wait for both processes to finish
    for job, proc in procs:
        ret = proc.wait()
        if ret == 0:
            logger.info(f"{job} completed successfully.")
        else:
            logger.error(f"{job} failed with exit code {ret}.")

    # Run normalize job only if both succeeded
    if all(proc.returncode == 0 for _, proc in procs):
        normalize_script = "normalize_domain_data.py"
        logger.info(f"Running {normalize_script}...")
        run_script(normalize_script)
    else:
        logger.error("One or both CA jobs failed. Skipping normalization.")

if __name__ == "__main__":
    main()
