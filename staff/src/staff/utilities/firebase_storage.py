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
    print("Initializing Firebase Storage...")  # Debug print
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
        print("Firebase Storage bucket initialized.")  # Debug print
        return bucket
        
    except Exception as e:
        print(f"Error initializing Firebase Storage: {str(e)}")
        raise  # Re-raise the exception to handle it in the calling code

def upload_to_firebase(storage_bucket, content, user_id):
    """Upload the generated report to Firebase Storage"""
    print("Uploading content to Firebase Storage...")  # Debug print
    try:
        if storage_bucket is None:
            raise ValueError("Firebase Storage bucket is not initialized")
            
        # Generate a unique filename with timestamp
        firebase_path = f'{user_id}/base_files/report.json'
        
        # Upload the content directly
        blob = storage_bucket.blob(firebase_path)
        blob.upload_from_string(content, content_type='application/json')
        print(f"Successfully uploaded report to Firebase Storage: {firebase_path}")
        
        # Make the blob publicly accessible
        blob.make_public()
        print(f"Report download URL: {blob.public_url}")
        
    except Exception as e:
        print(f"Error uploading to Firebase Storage: {str(e)}")
        raise  # Re-raise the exception to handle it in the calling code
        
