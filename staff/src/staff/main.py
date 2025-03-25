#!/usr/bin/env python
from urllib.parse import urlparse
import warnings
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask
import requests
from crew import Staff
from utilities import process_rewritten_article
from utilities import process_cover_content
from utilities.firebase_storage import initialize_firebase_storage, upload_to_firebase
import os
import google.generativeai as genai
from PIL import Image
from io import BytesIO
from base64 import b64encode
from google.cloud import pubsub_v1
import json
import exa_py
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

@app.route('/run/<userID>/<language>/<topic>/<coins>')
def run(userID, language, topic, coins):
    print(f"Received request with userID: {userID}, language: {language}, topic: {topic}, coins: {coins}")  # Debug print

    if storage_bucket is None:
        print("Firebase Storage is not initialized.")  # Debug print
        return "Firebase Storage not initialized. Please check your credentials and try again.", 500
            
    if coins == '1':
        n_news = 3
        period = 1
    elif coins == '3':
        n_news = 5
        period = 7
    elif coins == '7':
        n_news = 10
        period = 30
    else:
        print(f"Invalid coins value: {coins}")  # Debug print
        return "Invalid coins value.", 400

    print(f"Inputs prepared: n_news={n_news}, period={period}")  # Debug print

    try:
        
        # Initialize the client
        exa = exa_py.Exa(os.environ.get("EXA_API_KEY"))
        print("Exa client initialized.")  # Debug print

        # Search for news articles on your theme
        results = exa.search_and_contents(
            topic,  # Replace with your actual theme
            type="auto",
            category="news",
            num_results=n_news,
            text=True,  # Get the full text content
            start_published_date=(datetime.now() - timedelta(days=period)).strftime('%m/%d/%Y'),
            end_published_date=datetime.now().strftime('%m/%d/%Y'),
            extras = {
                "imageLinks": 3  # Request 1 image per result
            }
        )
        print(f"Search results obtained: {results}")  # Debug print

        def is_likely_logo(image_url, min_width=300, min_height=300):
            """Check if image is likely a logo based on dimensions"""
            try:
                response = requests.get(image_url, timeout=5)
                img = Image.open(BytesIO(response.content))
                width, height = img.size
                # Small square-ish images are often logos
                return width < min_width or height < min_height
            except:
                return True  # If we can't check, assume it might be a logo

        articles = []
        for result in results.results:
             
            parsed_url = urlparse(result.url)
            source_site = parsed_url.netloc.replace('www.', '')
            
            # Find the best image (not a logo)
            best_image = None
            if hasattr(result, 'image_links') and result.image_links:
                for img_url in result.image_links:
                    if not is_likely_logo(img_url):
                        best_image = img_url
                        break
            
            # Fallback to the main image if available
            if not best_image and result.image:
                best_image = result.image
            
            if best_image:
                print(f"Best Image URL: {best_image}")
                image = best_image
            else:
                print("No suitable image found")
                image = ''
            
            articles.append({
                'title': result.title,
                'url': result.url,
                'text': result.text,
                'image': image,
                'source': source_site
            })
        
        print(f"Extracted articles: {articles}")  # Debug print

        # Step 3: Rewrite the articles
        
        # Initialize the magazine crew
        magazine_crew = Staff().crew()
        print("Magazine crew initialized.")  # Debug print
        
        rewritten_articles = []
        for article in articles:
            rewrite_inputs = {
                'title': article['title'],
                'content': article['text'],
                'source': f"{article['source']} - {article['title']}",
                'language': language
            }
            print(f"Rewriting article with inputs: {rewrite_inputs}")  # Debug print
            
            rewrite_result = magazine_crew.kickoff(
                inputs=rewrite_inputs,
                task=Staff().rewrite_articles_task()
            )
            print(f"Rewrite result: {rewrite_result}")  # Debug print
            
            processed_result = process_rewritten_article(rewrite_result)
            rewritten_articles.append({
                'original': article,
                'rewritten': processed_result
            })
        
        print(f"Rewritten articles: {rewritten_articles}")  # Debug print
        
        # Step 4: Create cover content
        cover_inputs = {
            'topic': topic,
            'n_news': len(rewritten_articles),
            'articles': rewritten_articles,  # Provide context about the articles
            'language': language
        }
        
        cover_result = magazine_crew.kickoff(
            inputs=cover_inputs,
            task=Staff().create_cover_content_task()
        )
        print(f"Cover result: {cover_result}")  # Debug print
        
        cover_content = process_cover_content(cover_result)
        
        # Step 5: Generate cover image using Gemini 2.0 Flash
        # Configure the Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Error: GOOGLE_API_KEY environment variable not set.")
        
        genai.configure(api_key=api_key)
        
        try:
            # Create a client instance
            client = genai.Client()
            print("Client instance created.")  # Debug print
            
            
            content = rewritten_articles[cover_content['main_article_index']]['original']['text']
            # Generate content using the specified model
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp-image-generation",
                contents=f"Generate a cover image for a magazine about {topic} based on this news article:{content}",
                config=genai.types.GenerateContentConfig(
                    response_modalities=['Text', 'Image']
                )
            )
            print("Image generation response received.")  # Debug print
            
            # Assuming the response contains the image data
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(part.text)
                elif part.inline_data is not None:
                    image_data = part.inline_data.data  # Ensure this is the correct type
                    image = Image.open(BytesIO(image_data))
            
            # Convert image data to Base64
            base64_image = b64encode(image.tobytes()).decode('utf-8')  # Convert bytes to Base64 string
            
            
        except Exception as e:
            raise RuntimeError(f"Error generating image: {str(e)}")

        print(f"Cover image generated: {base64_image}")  # Debug print
        
        # Package all the results
        magazine_data = {
            'language': language,
            'topic': topic,
            'period': period,
            'articles': rewritten_articles,
            'cover_content': cover_content,
            'cover_image': base64_image
        }
        
        print(f"Magazine data prepared for upload: {magazine_data}")  # Debug print
        
        # Upload to Firebase
        upload_to_firebase(storage_bucket, json.dumps(magazine_data), userID)
        
        return "Magazine created and uploaded successfully"
    except Exception as e:
        print(f"An error occurred: {e}")  # Debug print
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)