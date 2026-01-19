"""Database backup script."""

import shutil
from datetime import datetime
from pathlib import Path

from loguru import logger

# Database file path
DB_FILE = Path("threat_intel.db")
BACKUP_DIR = Path("backups")

def backup_database():
    """Create a backup of the database."""
    if not DB_FILE.exists():
        logger.error(f"Database file not found: {DB_FILE}")
        return None
    
    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"threat_intel_backup_{timestamp}.db"
    
    try:
        # Copy database file
        shutil.copy2(DB_FILE, backup_file)
        logger.info(f"Database backed up to: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return None

if __name__ == "__main__":
    backup_database()









