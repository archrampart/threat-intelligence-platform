"""Remove ThreatMiner API source from database."""

from app.db.base import SessionLocal
from app.models.api_source import APISource, APIKey


def remove_threatminer():
    """Remove ThreatMiner API source and all associated API keys."""
    db = SessionLocal()
    
    try:
        # Find ThreatMiner API source
        threatminer = db.query(APISource).filter(APISource.name == "threatminer").first()
        
        if not threatminer:
            print("ThreatMiner API source not found in database.")
            return
        
        print(f"Found ThreatMiner API source: {threatminer.id} - {threatminer.display_name}")
        
        # Find and delete all API keys associated with ThreatMiner
        api_keys = db.query(APIKey).filter(APIKey.api_source_id == threatminer.id).all()
        print(f"Found {len(api_keys)} API key(s) associated with ThreatMiner")
        
        for api_key in api_keys:
            print(f"  - Deleting API key: {api_key.id}")
            db.delete(api_key)
        
        # Delete ThreatMiner API source
        print(f"Deleting ThreatMiner API source: {threatminer.id}")
        db.delete(threatminer)
        
        db.commit()
        print("Successfully removed ThreatMiner from database.")
    except Exception as e:
        db.rollback()
        print(f"Error removing ThreatMiner: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    remove_threatminer()







