import os
from firebase_admin import storage, credentials, initialize_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_firebase_storage():
    """
    Initialize Firebase Storage connection using credentials from environment variables.
    Returns the storage bucket instance.
    """
    try:
        # Get the path to the Firebase credentials file
        cred_path = os.getenv('FIREBASE_APPLICATION_CREDENTIALS')
        
        if not cred_path:
            raise ValueError("FIREBASE_APPLICATION_CREDENTIALS not found in environment variables")
        
        # Convert relative path to absolute path
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        # Construct absolute path to credentials file
        abs_cred_path = os.path.join(current_dir, cred_path)
        
        # Initialize Firebase Admin SDK with credentials
        cred = credentials.Certificate(abs_cred_path)
        initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
        })
        
        # Get the storage bucket
        bucket = storage.bucket()
        return bucket
        
    except Exception as e:
        print(f"Error initializing Firebase Storage: {str(e)}")
        raise

# Create a singleton instance of the storage bucket
storage_bucket = initialize_firebase_storage() 