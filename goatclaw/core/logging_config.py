import logging
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for structured logs.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        
        # Add extra fields if they exist
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging(level: int = logging.INFO, use_json: bool = False):
    """
    Configure logging for the entire platform.
    """
    # Force JSON if env var set
    if os.getenv("GOATCLAW_LOG_JSON", "").lower() == "true":
        use_json = True
        
    handler = logging.StreamHandler(sys.stdout)
    
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        # Standard readable format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)
    
    # Disable propagation for some noisy libraries if needed
    # logging.getLogger("urllib3").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
