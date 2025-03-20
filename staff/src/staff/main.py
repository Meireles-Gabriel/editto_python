#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from crew import Staff
from utilities.firebase_storage import upload_to_firebase
import os
from google.cloud import pubsub_v1
load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Set up Google Cloud credentials
current_dir = os.path.dirname(os.path.abspath(__file__))
gac_path = os.path.join(current_dir, 'utilities', 'gac.json')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gac_path

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
    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year)
    }
    
    try:
        # Run the crew to generate the report
        Staff().crew().kickoff(inputs=inputs)
        
        # After the crew finishes, upload the report to Firebase
        print("\nUploading report to Firebase Storage...")
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        report_path = os.path.join(results_dir, 'report.md')
        upload_to_firebase(report_path, 'test_user')
        # Delete the results folder after uploading
        print("\nCleaning up results directory...")
        try:
            import shutil
            shutil.rmtree(results_dir)
            print("Results directory cleaned up successfully")
        except OSError as e:
            print(f"Error cleaning up results directory: {e}")
        
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")
    return "Report uploaded successfully"
app.run(port=5000, host='localhost', debug=False)