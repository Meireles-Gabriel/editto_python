#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from crew import Staff
from utilities.firebase_storage import initialize_firebase_storage, upload_to_firebase
import os
from google.cloud import pubsub_v1
from globals import running_locally

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Set up Google Cloud credentials

if running_locally:
    gac_path = os.path.join(os.path.dirname(__file__), 'utilities', 'gac.json')
else:
    gac_path = '/app/gac.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gac_path

# Create a singleton instance of the storage bucket
try:
    storage_bucket = initialize_firebase_storage(running_locally)
    if storage_bucket is None:
        raise Exception("Failed to initialize Firebase Storage bucket")
except Exception as e:
    print(f"Failed to initialize Firebase Storage: {e}")
    storage_bucket = None

app = Flask(__name__)

# Configuração do cliente Pub/Sub
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Tópico e assinatura do Pub/Sub
project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
topic_path = publisher.topic_path(project_id, 'news-processing-topic')
subscription_path = subscriber.subscription_path(project_id, 'news-processing-topic-sub')

@app.route('/run')
def run():
    if storage_bucket is None:
        return "Firebase Storage not initialized. Please check your credentials and try again.", 500
        
    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year)
    }
    
    # Define results_dir outside try block so it's available in finally
    if running_locally:
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
    else:
        results_dir = os.path.join('/tmp', 'results')
    report_path = os.path.join(results_dir, 'report.md')
    
    try:
        # Run the crew to generate the report
        Staff().crew().kickoff(inputs=inputs)
        
    except Exception as e:
        return f"An error occurred while running the crew: {e}", 500 
    
    try:
        if not os.path.exists(report_path):
            print(f"Second attempt failed to save report to: {report_path}")

        # After the crew finishes, upload the report to Firebase
        print("\nUploading report to Firebase Storage...")
        print('Trying to upload report from:', report_path)
        upload_to_firebase(storage_bucket, report_path, 'test_user')
        
    except Exception as e:
        return f"An error occurred while uploading the report to Firebase: {e}", 500
    
    finally:    
        # Delete the results folder after uploading
        print("\nCleaning up results directory...")
        try:
            import shutil
            if os.path.exists(results_dir):
                shutil.rmtree(results_dir)
                print("Results directory cleaned up successfully")
            else:
                print("Results directory does not exist, no cleanup needed")
        except OSError as e:
            return f"Error cleaning up results directory: {e}", 500

    return "Report uploaded successfully"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)