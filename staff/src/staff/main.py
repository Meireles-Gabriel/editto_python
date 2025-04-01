#!/usr/bin/env python
import os
import json
import types
import warnings
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask, request, jsonify
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

# Pub/Sub client configuration
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Pub/Sub topic and subscription
project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
topic_path = publisher.topic_path(project_id, 'news-processing-topic')
subscription_path = subscriber.subscription_path(project_id, 'news-processing-topic-sub')

def get_news_parameters(coins):
    """Determine the number of news articles and period based on coins value."""
    if coins == '1':
        return 6, 1
    elif coins == '3':
        return 10, 7
    elif coins == '7':
        return 14, 30
    else:
        raise ValueError(f"Invalid coins value: {coins}")

def fetch_news_articles(topic, n_news, period):
    """Fetch news articles from Exa API based on topic and parameters."""
    exa = exa_py.Exa(os.environ.get("EXA_API_KEY"))
    print("Exa client initialized.")

    results = exa.search_and_contents(
        topic,
        type="auto",
        category="news",
        num_results=n_news,
        use_autoprompt=True,
        text=True,
        start_published_date=(datetime.now() - timedelta(days=period)).strftime('%m/%d/%Y'),
        end_published_date=datetime.now().strftime('%m/%d/%Y'),
    )
    print(f"Search results obtained: {results}")

    articles = []
    for result in results.results:
        parsed_url = urlparse(result.url)
        source_site = parsed_url.netloc.replace('www.', '')
        
        articles.append({
            'title': result.title,
            'url': result.url,
            'text': result.text,
            'source': source_site
        })
    
    print(f"Extracted articles: {articles}")
    return articles

def rewrite_articles(articles, topic, n_news, language):
    """Rewrite articles using the content crew."""
    content_crew = Staff().content_crew()
    print("Content crew initialized.")
    
    full_articles_content = ''
    for article in articles:
        full_articles_content += 'INDEX:' + str(articles.index(article)) + '\nTITLE:' + article['title'] + '\nTEXT:' + article['text'] + '\nSOURCE:' + article['source'] + '\n---ARTICLE DIVIDER---\n'
    
    rewrite_inputs = {
        'topic': topic,
        'articles': full_articles_content,
        'n_news': str(n_news/2),
        'language': language
    }    
    rewrite_result = content_crew.kickoff(inputs=rewrite_inputs)
    print(f"New Articles: {rewrite_result.raw}")
    
    return process_rewritten_article(rewrite_result.raw)

def create_cover_content(rewritten_articles, topic, language):
    """Create cover content using the design crew."""
    design_crew = Staff().design_crew()
    print("Design crew initialized.")
    
    cover_inputs = {
        'topic': topic,
        'n_news': len(rewritten_articles),
        'articles': rewritten_articles,
        'language': language
    }
    
    cover_result = design_crew.kickoff(inputs=cover_inputs)
    print(f"Cover result: {cover_result}")
    
    return process_cover_content(cover_result.raw)

def generate_cover_image(topic):
    """Generate cover image using Imagen 3."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    base_prompt = f"An image of an object related to '{topic}' as a sculpture made of crystal, set against a solid navy blue background, without texts, standard lens, 50mm, crisp details, in 4k resolution, under dramatic and professional lighting"
    
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

        for generated_image in response.generated_images:
            if generated_image.image.image_bytes:
                image = Image.open(BytesIO(generated_image.image.image_bytes))                   
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                return b64encode(buffered.getvalue()).decode('utf-8')
        
        raise ValueError("No image found in the response")
            
    except Exception as e:
        print(f"Image generation error: {e}")
        print(response)
        raise RuntimeError(f"Failed to generate cover image: {str(e)}")

def create_magazine_data(language, topic, period, rewritten_articles, cover_content, cover_image):
    """Create the final magazine data structure."""
    return {
        'language': language,
        'topic': topic,
        'period': period,
        'articles': rewritten_articles,
        'cover_content': cover_content,
        'cover_image': cover_image,
    }

# Step 1: Initialize process and gather parameters
@app.route('/api/magazine/init/<userID>/<language>/<topic>/<coins>')
def init_magazine_process(userID, language, topic, coins):
    """Initialize the magazine creation process and fetch articles."""
    try:
        # Create process ID
        process_id = str(uuid.uuid4())
        
        # Initialize Firebase storage
        storage_bucket = initialize_firebase_storage(running_locally)
        if storage_bucket is None:
            raise Exception("Failed to initialize Firebase Storage bucket")
        
        # Get news parameters
        n_news, period = get_news_parameters(coins)
        print(f"Inputs prepared: n_news={n_news}, period={period}")
        
        # Create process data
        process_data = {
            'process_id': process_id,
            'userID': userID,
            'language': language,
            'topic': topic,
            'coins': coins,
            'n_news': n_news,
            'period': period,
            'status': 'initialized'
        }
        
        return jsonify({
            'process_data': process_data,
            'status': 'initialized',
            'next_step': f'/api/magazine/fetch-articles'
        })
        
    except Exception as e:
        print(f"Initialization error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 2: Fetch articles
@app.route('/api/magazine/fetch-articles', methods=['POST'])
def fetch_articles():
    """Fetch news articles for the magazine."""
    try:
        # Get process data from request
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        topic = process_data.get('topic')
        n_news = process_data.get('n_news')
        period = process_data.get('period')
        
        if not all([topic, n_news, period]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Fetch articles
        articles = fetch_news_articles(topic, n_news, period)
        
        # Update process data
        process_data['articles'] = articles
        process_data['status'] = 'articles_fetched'
        
        return jsonify({
            'process_data': process_data,
            'status': 'articles_fetched',
            'article_count': len(articles),
            'next_step': f'/api/magazine/rewrite-articles'
        })
        
    except Exception as e:
        print(f"Article fetching error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 3: Rewrite articles
@app.route('/api/magazine/rewrite-articles', methods=['POST'])
def rewrite_articles_endpoint():
    """Rewrite articles for the magazine."""
    try:
        # Get process data from request
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        articles = process_data.get('articles')
        topic = process_data.get('topic')
        n_news = process_data.get('n_news')
        language = process_data.get('language')
        
        if not all([articles, topic, n_news, language]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Rewrite articles
        rewritten_articles = rewrite_articles(articles, topic, n_news, language)
        
        # Update process data
        process_data['rewritten_articles'] = rewritten_articles
        process_data['status'] = 'articles_rewritten'
        
        return jsonify({
            'process_data': process_data,
            'status': 'articles_rewritten',
            'rewritten_count': len(rewritten_articles),
            'next_step': f'/api/magazine/create-cover'
        })
        
    except Exception as e:
        print(f"Article rewriting error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 4: Create cover content
@app.route('/api/magazine/create-cover', methods=['POST'])
def create_cover_endpoint():
    """Create cover content for the magazine."""
    try:
        # Get process data from request
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        rewritten_articles = process_data.get('rewritten_articles')
        topic = process_data.get('topic')
        language = process_data.get('language')
        
        if not all([rewritten_articles, topic, language]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Create cover content
        cover_content = create_cover_content(rewritten_articles, topic, language)
        
        # Update process data
        process_data['cover_content'] = cover_content
        process_data['status'] = 'cover_created'
        
        return jsonify({
            'process_data': process_data,
            'status': 'cover_created',
            'next_step': f'/api/magazine/generate-image'
        })
        
    except Exception as e:
        print(f"Cover creation error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 5: Generate cover image
@app.route('/api/magazine/generate-image', methods=['POST'])
def generate_image_endpoint():
    """Generate cover image for the magazine."""
    try:
        # Get process data from request
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        topic = process_data.get('topic')
        
        if not topic:
            return jsonify({'error': 'Missing required parameter: topic'}), 400
        
        # Generate cover image
        cover_image = generate_cover_image(topic)
        
        # Update process data
        process_data['cover_image'] = cover_image
        process_data['status'] = 'image_generated'
        
        return jsonify({
            'process_data': process_data,
            'status': 'image_generated',
            'next_step': f'/api/magazine/finalize'
        })
        
    except Exception as e:
        print(f"Image generation error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 6: Finalize and upload magazine
@app.route('/api/magazine/finalize', methods=['POST'])
def finalize_magazine():
    """Finalize and upload the magazine."""
    try:
        # Get process data from request
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        # Check for required components
        required_keys = ['language', 'topic', 'period', 'rewritten_articles', 'cover_content', 'cover_image', 'userID']
        missing_keys = [key for key in required_keys if key not in process_data]
        
        if missing_keys:
            return jsonify({'error': f'Missing required components: {", ".join(missing_keys)}'}), 400
        
        language = process_data['language']
        topic = process_data['topic']
        period = process_data['period']
        rewritten_articles = process_data['rewritten_articles']
        cover_content = process_data['cover_content']
        cover_image = process_data['cover_image']
        userID = process_data['userID']
        
        # Initialize Firebase storage
        storage_bucket = initialize_firebase_storage(running_locally)
        if storage_bucket is None:
            raise Exception("Failed to initialize Firebase Storage bucket")
        
        # Create magazine data
        magazine_data = create_magazine_data(language, topic, period, rewritten_articles, cover_content, cover_image)
        
        # Upload to Firebase
        upload_to_firebase(storage_bucket, json.dumps(magazine_data), userID)
        
        # Update status
        process_data['status'] = 'completed'
        
        return jsonify({
            'process_data': process_data,
            'status': 'completed',
            'message': 'Magazine created and uploaded successfully'
        })
        
    except Exception as e:
        print(f"Finalization error: {e}")
        return jsonify({'error': str(e)}), 500

# Legacy route for backward compatibility
@app.route('/run/<userID>/<language>/<topic>/<coins>')
def run(userID, language, topic, coins):
    """Legacy endpoint that orchestrates the entire magazine creation process."""
    print(f"Received request with userID: {userID}, language: {language}, topic: {topic}, coins: {coins}")
    
    try:
        # Initialize Firebase storage
        storage_bucket = initialize_firebase_storage(running_locally)
        if storage_bucket is None:
            raise Exception("Failed to initialize Firebase Storage bucket")
            
        # Get news parameters
        n_news, period = get_news_parameters(coins)
        print(f"Inputs prepared: n_news={n_news}, period={period}")
        
        # Fetch news articles
        articles = fetch_news_articles(topic, n_news, period)
        
        # Rewrite articles
        rewritten_articles = rewrite_articles(articles, topic, n_news, language)
        
        # Create cover content
        cover_content = create_cover_content(rewritten_articles, topic, language)
        
        # Generate cover image
        cover_image = generate_cover_image(topic)
        print("Cover image generated successfully.")
        
        # Create magazine data
        magazine_data = create_magazine_data(language, topic, period, rewritten_articles, cover_content, cover_image)
        print("Magazine data prepared for upload.")
        
        # Upload to Firebase
        upload_to_firebase(storage_bucket, json.dumps(magazine_data), userID)
        
        return "Magazine created and uploaded successfully"
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)