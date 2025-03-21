from datetime import datetime
import os
from firebase_admin import storage, credentials, initialize_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_firebase_storage(running_locally):
    """
    Initialize Firebase Storage connection using credentials from environment variables.
    Returns the storage bucket instance.
    """
    try:
        if running_locally:
            cred_path = os.path.join(os.path.dirname(__file__), 'fac.json')
        else:
            cred_path = '/app/fac.json'
            
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
            
        # Initialize Firebase Admin SDK with credentials
        cred = credentials.Certificate(cred_path)
        initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
        })
        
        # Get the storage bucket
        bucket = storage.bucket()
        print(f"Firebase Storage bucket initialized")
        return bucket
        
    except Exception as e:
        print(f"Error initializing Firebase Storage: {str(e)}")
        raise  # Re-raise the exception to handle it in the calling code

def upload_to_firebase(storage_bucket, file_path, user_id):
    """Upload the generated report to Firebase Storage"""
    try:
        if storage_bucket is None:
            raise ValueError("Firebase Storage bucket is not initialized")
            
        if not os.path.exists(file_path):
            print(f"File not found at: {file_path}")
        
        # Generate a unique filename with timestamp
        firebase_path = f'{user_id}/base_files/report.md'
        
        # Upload the file
        blob = storage_bucket.blob(firebase_path)
        blob.upload_from_filename(file_path)
        print(f"Successfully uploaded report to Firebase Storage: {firebase_path}")
        
    except Exception as e:
        print(f"Error uploading to Firebase Storage: {str(e)}")
        raise  # Re-raise the exception to handle it in the calling code
        
