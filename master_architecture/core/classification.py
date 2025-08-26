"""
Data classification for security levels
"""

class DataClassification:
    """Classify database fields by security level"""
    
    PERSONAL_IDENTIFIERS = ['email', 'phoneNumber', 'fullName', 'username', 'birthdate']
    MEDICAL_DATA = ['caries_number', 'recession_number', 'teeth_count', 'caries_count', 'recession_count']
    SECURITY_DATA = ['password', 'token', 'resetToken', 'reset_code', 'resetTokenCreatedAt', 'reset_code_expiry']
    ANALYTICS_SAFE_DATA = ['gender', 'ageGroup', 'register_method', 'confirmed', 'client_id', 'createdAt', 'lastUpdatedAt', 'appointDate']
    
    def classify_user_table_fields(self):
        """Complete classification of all User table fields"""
        
        complete_classification = {
            'CONFIDENTIAL': {
                'userId': 'Primary key - unique identifier for individual users',
                'username': 'User-chosen identifier, may contain personal info',
                'email': 'Direct personal identifier, used for communication',
                'phoneNumber': 'Direct contact information, personally identifiable',
                'fullName': 'Direct personal identifier, real name of user',
                'birthdate': 'Exact birthdate can be used for identification'
            },
            
            'MEDICAL': {
                'teeth_count': 'Specific dental health diagnosis data',
                'caries_count': 'Specific dental health diagnosis data',
                'recession_count': 'Specific dental health diagnosis data', 
            },
            
            'SECURITY': {
                'password': 'Authentication credential - must be encrypted',
                'token': 'Session token for API access',
                'resetToken': 'Password reset token for security',
                'resetTokenCreatedAt': 'Security token timestamp',
                'reset_code': '6-digit password reset code',
                'reset_code_expiry': 'Security code expiration time',
                'confirmed': 'Email verification status (security measure)',
                'confirmed_at': 'Email confirmation timestamp'
            },
            
            'ANALYTICS_SAFE': {
                'gender': 'Demographics - no personal identification',
                'ageGroup': 'Already aggregated age data (safe)',
                'appointDate': 'Appointment patterns (dates only, anonymized)',
                'createdAt': 'Registration timestamp for growth analysis',
                'lastUpdatedAt': 'Activity patterns for engagement analysis',
                'register_method': 'Registration channel analysis (email/google)',
                'client_id': 'Clinic/location identifier for business analytics'
            }
        }
        
        return complete_classification
