"""
Data anonymization strategies for privacy protection
"""

import hashlib
from datetime import date

class DataAnonymizationStrategy:
    """Define how to convert personal data into anonymous analytics"""
    
    def design_user_id_anonymization(self, user_id: str, client_id: str, salt: str = "myoral_salt") -> str:
        """Convert userId to an anonymous, unique, non-reversible tracking ID for analytics"""
        to_hash = f"{user_id}:{client_id}:{salt}"
        anon_id = hashlib.sha256(to_hash.encode()).hexdigest()
        return anon_id

    def design_age_anonymization(self, birthdate: date) -> str:
        """Convert exact birthdate to an age group string for privacy"""
        today = date.today()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        if age < 18:
            return "under_18"
        elif 18 <= age <= 24:
            return "18_24"
        elif 25 <= age <= 34:
            return "25_34"
        elif 35 <= age <= 44:
            return "35_44"
        elif 45 <= age <= 54:
            return "45_54"
        elif 55 <= age <= 64:
            return "55_64"
        else:
            return "65_plus"

    def design_location_anonymization(self, client_id: str, client_lookup: dict = None) -> str:
        """Anonymize clinic location using client_id"""
        if client_lookup and client_id in client_lookup:
            return client_lookup[client_id]
        
        if client_id.startswith("north"):
            return "North Region"
        elif client_id.startswith("south"):
            return "South Region"
        elif client_id.startswith("east"):
            return "East Region"
        elif client_id.startswith("west"):
            return "West Region"
        elif client_id.startswith("dental"):
            return "dental_clinic"
        else:
            return "Unknown Region"
