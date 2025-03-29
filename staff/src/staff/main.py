#!/usr/bin/env python
import os
import json
import random
import types
import warnings
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask
import requests
from crew import Staff
from utilities.process_rewritten_article import process_rewritten_article
from utilities.process_cover_content import process_cover_content
from utilities.firebase_storage import initialize_firebase_storage, upload_to_firebase
from google import genai
from google.genai import types
from PIL import Image
from google.cloud import pubsub_v1
from io import BytesIO
from base64 import b64encode
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
    # Create a singleton instance of the storage bucket
    try:
        storage_bucket = initialize_firebase_storage(running_locally)
        if storage_bucket is None:
            raise Exception("Failed to initialize Firebase Storage bucket")
    except Exception as e:
        print(f"Failed to initialize Firebase Storage: {e}")
        storage_bucket = None
        
    if storage_bucket is None:
        print("Firebase Storage is not initialized.")  # Debug print
        return "Firebase Storage not initialized. Please check your credentials and try again.", 300
            
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
            use_autoprompt=True,
            text=True,  # Get the full text content
            start_published_date=(datetime.now() - timedelta(days=period)).strftime('%m/%d/%Y'),
            end_published_date=datetime.now().strftime('%m/%d/%Y'),
            extras = {
                "imageLinks": 3  # Request 3 image per result
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
        
        # Initialize the magazine crews
        content_crew = Staff().content_crew()
        design_crew = Staff().design_crew()
        print("Magazine crews initialized.")  # Debug print
        
        rewritten_articles = []
        for article in articles:
            rewrite_inputs = {
                'topic': topic,
                'title': article['title'],
                'content': article['text'],
                'source': f"{article['source']} - {article['title']}",
                'language': language
            }
            
            rewrite_result = content_crew.kickoff(
                inputs=rewrite_inputs,
            )
            print(f"Rewrite result: {rewrite_result}")  # Debug print
            
            processed_result = process_rewritten_article(rewrite_result.raw)
            rewritten_articles.append({
                'original': article,
                'rewritten': processed_result
            })
        
        # Step 4: Create cover content
        cover_inputs = {
            'topic': topic,
            'n_news': len(rewritten_articles),
            'articles': rewritten_articles,  # Provide context about the articles
            'language': language
        }
        
        cover_result = design_crew.kickoff(
            inputs=cover_inputs,
        )
        print(f"Cover result: {cover_result}")  # Debug print
        
        cover_content = process_cover_content(cover_result.raw)
        
        # Step 5: Generate cover image using Imagen 3
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        subheading = cover_content['subheading']
        print(f"Image subject: {subheading}")
        
        # layout_type = random.choice([1, 2, 3])
        
        # Base do prompt que será igual para todos os layouts
        base_prompt = f"""
        Ignore any previous generated images from previous iterations.
        Create the described image from scratch:
        
        Create an image about this topic: "{subheading}".
        
        STYLE SPECIFICATIONS:
        - high fashion photography aesthetic, crisp details, main image subject in the right
        - high-definition, professional lighting, vibrant colors, sharp focus
        """
        
        
        try:
            response = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=base_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio='3:4'
                )
            )
            print("Image generation response received.")

            # Extract image from response
            for generated_image in response.generated_images:
                if generated_image.image.image_bytes:
                    image = Image.open(BytesIO(generated_image.image.image_bytes))                   
                    # Convert image data to Base64
                    buffered = BytesIO()
                    image.save(buffered, format="PNG")
                    base64_image = b64encode(buffered.getvalue()).decode('utf-8')
                    break
            

        except Exception as e:
            print(f"Image generation error: {e}")
            print(response)
            raise RuntimeError(f"Failed to generate cover image: {str(e)}")
        
        print(f"Cover image generated: Trust me. It worked.")  # Debug print
        
        # Package all the results
        magazine_data = {
            'language': language,
            'topic': topic,
            'period': period,
            'articles': rewritten_articles,
            'cover_content': cover_content,
            'cover_image': base64_image,
        }
        
        print(f"Magazine data prepared for upload.")  # Debug print
        
        # Upload to Firebase
        upload_to_firebase(storage_bucket, json.dumps(magazine_data), userID)
        
        return "Magazine created and uploaded successfully"
    except Exception as e:
        print(f"An error occurred: {e}")  # Debug print
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)