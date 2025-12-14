import logging
import json
import subprocess
from logging.handlers import RotatingFileHandler
from datetime import datetime
from datetime import datetime
from typing import Optional, Any
import os
import glob
import time

def cleanup_old_logs(log_dir: str, retention_days: int = 14):
    """
    Removes log files in the specified directory that are older than the retention period.
    Assumes log files start with 'dcv_process.log'.
    """
    try:
        # Construct the pattern to match log files
        # Adjust pattern if your log files have a different naming convention
        log_pattern = os.path.join(log_dir, "dcv_process.log*")
        
        # Calculate the cutoff time
        cutoff_time = time.time() - (retention_days * 86400)
        
        for log_file in glob.glob(log_pattern):
            if os.path.isfile(log_file):
                file_mtime = os.path.getmtime(log_file)
                if file_mtime < cutoff_time:
                    try:
                        os.remove(log_file)
                        print(f"Removed old log file: {log_file}")
                    except OSError as e:
                        print(f"Error removing {log_file}: {e}")
    except Exception as e:
        print(f"Error during log cleanup: {e}")

# Configure the logger
def setup_logger(log_file: str = '../log/dcv_process.log', max_bytes: int = 10_000_000, backup_count: int = 5, retention_days: int = 14):
    logger = logging.getLogger("dcv_logger")
    
    # Ensure log directory exists
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Failed to create log directory {log_dir}: {e}")

    # Perform cleanup of old logs
    if not log_dir: # Handle case where log_file is just a filename
        log_dir = os.getcwd()
    
    cleanup_old_logs(log_dir, retention_days)

    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()

def log_execution(func):
    """Decorator to log execution of functions."""
    def wrapper(*args, **kwargs):
        logger.info(f"Started function '{func.__name__}'")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Finished function '{func.__name__}' successfully")
            return result
        except Exception as e:
            logger.error(f"Error in function '{func.__name__}': {str(e)}", exc_info=True)
            raise
    return wrapper

def log_json_response(response: Any, context: Optional[str] = None):
    """Log JSON API responses."""
    try:
        if isinstance(response, str):
            response_obj = json.loads(response)
        else:
            response_obj = response
        msg = f"API Response{f' ({context})' if context else ''}: {json.dumps(response_obj, indent=2)}"
        logger.info(msg)
    except Exception as e:
        logger.error(f"Failed to log JSON response: {str(e)}")

def run_and_log_command(command: list, context: Optional[str] = None):
    """
    Run a shell command (e.g., dig) and log output/error.
    Usage: run_and_log_command(['dig', 'github.com'])
    """
    cmd_str = ' '.join(command)
    logger.info(f"Running command{f' ({context})' if context else ''}: {cmd_str}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Command Output [{cmd_str}]:\n{result.stdout.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{cmd_str}' failed with error code {e.returncode}")
        logger.error(f"Stderr: {e.stderr.strip()}")
        return None

# Example usage in a script:
if __name__ == "__main__":
    @log_execution
    def sample_api_call():
        # Simulate API response
        api_response = {"status": "ok", "data": {"key": "value"}}
        log_json_response(api_response, context="Sample API Call")
        return api_response

    @log_execution
    def test_dig():
        output = run_and_log_command(['dig', 'github.com'], context="Test dig command")
        if output:
            print("dig output captured")
        else:
            print("dig command failed")

    # Test functions
    sample_api_call()
    test_dig()
