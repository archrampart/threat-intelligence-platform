"""IP Geolocation helper using ip-api.com free service."""
import requests
from typing import Optional, Dict
from loguru import logger


class IPGeolocation:
    """Simple IP geolocation using ip-api.com (free, no API key required)."""
    
    BASE_URL = "http://ip-api.com/json/"
    
    @staticmethod
    def get_location(ip: str) -> Optional[Dict[str, any]]:
        """
        Get geolocation data for an IP address.
        
        Args:
            ip: IP address to locate
            
        Returns:
            dict with keys: country, countryCode, city, lat, lon
            or None if lookup fails
        """
        try:
            response = requests.get(
                f"{IPGeolocation.BASE_URL}{ip}",
                params={"fields": "status,country,countryCode,city,lat,lon"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "country": data.get("countryCode"),
                        "country_name": data.get("country"),
                        "city": data.get("city"),
                        "latitude": data.get("lat"),
                        "longitude": data.get("lon"),
                    }
            
            logger.warning(f"IP geolocation failed for {ip}: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting geolocation for {ip}: {e}")
            return None
