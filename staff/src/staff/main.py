#!/usr/bin/env python
import os
import types
import warnings
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from crew import Staff
from utilities.process_rewritten_article import process_rewritten_article
from utilities.process_cover_content import process_cover_content
from google import genai
from google.genai import types
from PIL import Image
from google.cloud import pubsub_v1
from io import BytesIO
from base64 import b64encode
import exa_py
from globals import running_locally

# Load environment variables
# Carrega variáveis de ambiente
load_dotenv()

# Suppress pysbd syntax warnings
# Suprime avisos de sintaxe do pysbd
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Set up Google Cloud credentials based on environment
# Configura as credenciais do Google Cloud com base no ambiente
if running_locally:
    gac_path = os.path.join(os.path.dirname(__file__), 'utilities', 'gac.json')
else:
    gac_path = '/app/gac.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gac_path

# Initialize Flask application
# Inicializa a aplicação Flask
app = Flask(__name__)

# Configure CORS with proper headers
# Configura CORS com os headers apropriados
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "max_age": 3600
    }
})

# Configure maximum content length
# Configura o tamanho máximo do conteúdo
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['JSON_AS_ASCII'] = False  # Allow non-ASCII characters in JSON

# Initialize Pub/Sub clients
# Inicializa os clientes Pub/Sub
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Configure Pub/Sub topic and subscription paths
# Configura os caminhos do tópico e assinatura do Pub/Sub
project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
topic_path = publisher.topic_path(project_id, 'news-processing-topic')
subscription_path = subscriber.subscription_path(project_id, 'news-processing-topic-sub')

def get_news_parameters(coins):
    """
    Determine number of news articles and time period based on coins value.
    Determina o número de artigos de notícias e o período de tempo com base no valor das moedas.
    """
    if coins == '1':
        return 6, 1  # 6 articles from the last day / 6 artigos do último dia
    elif coins == '3':
        return 10, 7  # 10 articles from the last week / 10 artigos da última semana
    elif coins == '7':
        return 20, 30  # 20 articles from the last month / 20 artigos do último mês
    else:
        raise ValueError(f"Invalid coins value: {coins}")

def fetch_articles(topic, n_news, period):
    """
    Fetch news articles from Exa API based on topic and parameters.
    Busca artigos de notícias da API Exa com base no tópico e parâmetros.
    """
    # Initialize Exa client with API key
    # Inicializa o cliente Exa com a chave de API
    exa = exa_py.Exa(os.environ.get("EXA_API_KEY"))
    if running_locally:
        print("Exa client initialized.")

    # Search for news articles with given parameters
    # Pesquisa artigos de notícias com os parâmetros fornecidos
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
    if running_locally:
        print(f"Search results obtained: {results}")

    # Process and format articles from search results
    # Processa e formata os artigos dos resultados da pesquisa
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
    
    if running_locally:
        print(f"Extracted articles: {articles}")
    return articles

def rewrite_articles(articles, topic, n_news, language):
    """
    Rewrite articles using AI to create magazine-style content.
    Reescreve artigos usando IA para criar conteúdo no estilo de revista.
    """
    # Initialize content crew from AI Staff
    # Inicializa a equipe de conteúdo da IA Staff
    content_crew = Staff().content_crew()
    if running_locally:
        print("Content crew initialized.")
    
    # Format articles for the AI input
    # Formata os artigos para a entrada da IA
    full_articles_content = ''
    for article in articles:
        full_articles_content += 'INDEX:' + str(articles.index(article)) + '\nTITLE:' + article['title'] + '\nTEXT:' + article['text'] + '\nSOURCE:' + article['source'] + '\n---ARTICLE DIVIDER---\n'
    
    # Prepare input parameters for the AI
    # Prepara os parâmetros de entrada para a IA
    rewrite_inputs = {
        'topic': topic,
        'articles': full_articles_content,
        'n_news': str(n_news/2),  # Request half the number of articles / Solicita metade do número de artigos
        'language': language
    }    
    
    # Start the rewriting process
    # Inicia o processo de reescrita
    rewrite_result = content_crew.kickoff(inputs=rewrite_inputs)
    if running_locally:
        print(f"New Articles: {rewrite_result.raw}")
    
    # Process the raw output from AI
    # Processa a saída bruta da IA
    return process_rewritten_article(rewrite_result.raw)

def generate_cover_text(rewritten_articles, topic, language):
    """
    Create magazine cover content (titles, headlines) using AI.
    Cria conteúdo de capa de revista (títulos, manchetes) usando IA.
    """
    # Initialize design crew from AI Staff
    # Inicializa a equipe de design da IA Staff
    design_crew = Staff().design_crew()
    if running_locally:
        print("Design crew initialized.")
    
    # Prepare input parameters for the AI
    # Prepara os parâmetros de entrada para a IA
    cover_inputs = {
        'topic': topic,
        'n_news': len(rewritten_articles),
        'articles': rewritten_articles,
        'language': language
    }
    
    # Start the cover content creation process
    # Inicia o processo de criação de conteúdo da capa
    cover_result = design_crew.kickoff(inputs=cover_inputs)
    if running_locally:
        print(f"Cover result: {cover_result}")
    
    # Process the raw output from AI
    # Processa a saída bruta da IA
    return process_cover_content(cover_result.raw)

def generate_cover_image(topic):
    """
    Generate magazine cover image using Google's Imagen AI.
    Gera imagem de capa de revista usando a IA Imagen do Google.
    """
    # Initialize Gemini client with API key
    # Inicializa o cliente Gemini com a chave de API
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Create prompt for image generation
    # Cria o prompt para geração de imagem
    base_prompt = f"An image of an object related to '{topic}' as a sculpture made of crystal, set against a solid navy blue background, without texts, standard lens, 50mm, crisp details, in 4k resolution, under dramatic and professional lighting"
    
    try:
        # Generate image with Imagen model
        # Gera imagem com o modelo Imagen
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=base_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio='3:4'
            )
        )
        if running_locally:
            print("Image generation response received.")

        # Process the generated image
        # Processa a imagem gerada
        for generated_image in response.generated_images:
            if generated_image.image.image_bytes:
                image = Image.open(BytesIO(generated_image.image.image_bytes))                   
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                return b64encode(buffered.getvalue()).decode('utf-8')
        
        raise ValueError("No image found in the response")
            
    except Exception as e:
        if running_locally:
            print(f"Image generation error: {e}")
            print(response)
        raise RuntimeError(f"Failed to generate cover image: {str(e)}")

def create_magazine_raw_data(language, topic, period, rewritten_articles, cover_content, cover_image):
    """
    Create the final magazine data structure with all components.
    Cria a estrutura de dados final da revista com todos os componentes.
    """
    return {
        'language': language,
        'topic': topic,
        'period': period,
        'articles': rewritten_articles,
        'cover_content': cover_content,
        'cover_image': cover_image,
    }

# API ROUTES / ROTAS DA API

# Step 1: Initialize magazine creation process
# Passo 1: Inicializa o processo de criação da revista
@app.route('/init-magazine-process-endpoint/<language>/<topic>/<coins>')
def init_magazine_process_endpoint(language, topic, coins):
    """
    Initialize the magazine creation process with basic parameters.
    Inicializa o processo de criação da revista com parâmetros básicos.
    """
    try:
        # Get article parameters based on coins
        # Obtém os parâmetros de artigos com base nas moedas
        n_news, period = get_news_parameters(coins)
        if running_locally:
            print(f"Inputs prepared: n_news={n_news}, period={period}")
        
        # Create initial process data
        # Cria dados iniciais do processo
        process_data = {
            'language': language,
            'topic': topic,
            'coins': coins,
            'n_news': n_news,
            'period': period,
            'status': 'initialized'
        }
        
        # Return process data and next step info
        # Retorna dados do processo e informações do próximo passo
        return jsonify({
            'process_data': process_data,
            'status': 'initialized',
            'next_step': f'/api/magazine/fetch-articles'
        })
        
    except Exception as e:
        if running_locally:
            print(f"Initialization error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 2: Fetch news articles
# Passo 2: Busca artigos de notícias
@app.route('/fetch-articles-endpoint', methods=['POST'])
def fetch_articles_endpoint():
    """
    Fetch relevant news articles based on the topic and parameters.
    Busca artigos de notícias relevantes com base no tópico e parâmetros.
    """
    try:
        # Get process data from request
        # Obtém dados do processo da requisição
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        # Extract required parameters
        # Extrai parâmetros necessários
        topic = process_data.get('topic')
        n_news = process_data.get('n_news')
        period = process_data.get('period')
        
        # Validate required parameters
        # Valida parâmetros necessários
        if not all([topic, n_news, period]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Fetch articles from news sources
        # Busca artigos de fontes de notícias
        articles = fetch_articles(topic, n_news, period)
        
        # Update process data with articles
        # Atualiza dados do processo com os artigos
        process_data['articles'] = articles
        process_data['status'] = 'articles_fetched'
        
        # Return updated process data and next step
        # Retorna dados do processo atualizados e próximo passo
        return jsonify({
            'process_data': process_data,
            'status': 'articles_fetched',
            'article_count': len(articles),
            'next_step': f'/api/magazine/rewrite-articles'
        })
        
    except Exception as e:
        if running_locally:
            print(f"Article fetching error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 3: Rewrite articles for magazine style
# Passo 3: Reescreve artigos no estilo de revista
@app.route('/rewrite-articles-endpoint', methods=['POST'])
def rewrite_articles_endpoint():
    """
    Rewrite news articles in magazine style using AI.
    Reescreve artigos de notícias no estilo de revista usando IA.
    """
    try:
        # Get process data from request
        # Obtém dados do processo da requisição
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        # Extract required parameters
        # Extrai parâmetros necessários
        articles = process_data.get('articles')
        topic = process_data.get('topic')
        n_news = process_data.get('n_news')
        language = process_data.get('language')
        
        # Validate required parameters
        # Valida parâmetros necessários
        if not all([articles, topic, n_news, language]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Rewrite articles using AI
        # Reescreve artigos usando IA
        rewritten_articles = rewrite_articles(articles, topic, n_news, language)
        
        # Update process data with rewritten articles
        # Atualiza dados do processo com os artigos reescritos
        process_data['rewritten_articles'] = rewritten_articles
        process_data['status'] = 'articles_rewritten'
        
        # Return updated process data and next step
        # Retorna dados do processo atualizados e próximo passo
        return jsonify({
            'process_data': process_data,
            'status': 'articles_rewritten',
            'rewritten_count': len(rewritten_articles),
            'next_step': f'/api/magazine/create-cover'
        })
        
    except Exception as e:
        if running_locally:
            print(f"Article rewriting error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 4: Create magazine cover content
# Passo 4: Cria conteúdo da capa da revista
@app.route('/generate-cover-text-endpoint', methods=['POST'])
def generate_cover_text_endpoint():
    """
    Create magazine cover content (title, subtitle, highlights) using AI.
    Cria conteúdo da capa da revista (título, subtítulo, destaques) usando IA.
    """
    try:
        # Get process data from request
        # Obtém dados do processo da requisição
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        # Extract required parameters
        # Extrai parâmetros necessários
        rewritten_articles = process_data.get('rewritten_articles')
        topic = process_data.get('topic')
        language = process_data.get('language')
        
        # Validate required parameters
        # Valida parâmetros necessários
        if not all([rewritten_articles, topic, language]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Create cover content using AI
        # Cria conteúdo da capa usando IA
        cover_content = generate_cover_text(rewritten_articles, topic, language)
        
        # Update process data with cover content
        # Atualiza dados do processo com o conteúdo da capa
        process_data['cover_content'] = cover_content
        process_data['status'] = 'cover_created'
        
        # Return updated process data and next step
        # Retorna dados do processo atualizados e próximo passo
        return jsonify({
            'process_data': process_data,
            'status': 'cover_created',
            'next_step': f'/api/magazine/generate-image'
        })
        
    except Exception as e:
        if running_locally:
            print(f"Cover creation error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 5: Generate magazine cover image
# Passo 5: Gera imagem da capa da revista
@app.route('/generate-image-endpoint', methods=['POST'])
def generate_image_endpoint():
    """
    Generate magazine cover image using AI image generation.
    Gera imagem da capa da revista usando geração de imagem por IA.
    """
    try:
        # Get process data from request
        # Obtém dados do processo da requisição
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        # Extract topic parameter
        # Extrai parâmetro de tópico
        topic = process_data.get('topic')
        
        # Validate topic parameter
        # Valida parâmetro de tópico
        if not topic:
            return jsonify({'error': 'Missing required parameter: topic'}), 400
        
        # Generate cover image with AI
        # Gera imagem da capa com IA
        cover_image = generate_cover_image(topic)
        
        # Update process data with cover image
        # Atualiza dados do processo com a imagem da capa
        process_data['cover_image'] = cover_image
        process_data['status'] = 'image_generated'
        
        # Return updated process data and next step
        # Retorna dados do processo atualizados e próximo passo
        return jsonify({
            'process_data': process_data,
            'status': 'image_generated',
            'next_step': f'/api/magazine/finalize'
        })
        
    except Exception as e:
        if running_locally:
            print(f"Image generation error: {e}")
        return jsonify({'error': str(e)}), 500

# Step 6: Finalize and return the magazine
# Passo 6: Finaliza e retorna a revista
@app.route('/finalize-magazine-raw-data-endpoint', methods=['POST'])
def finalize_magazine_raw_data_endpoint():
    """
    Finalize the magazine creation and return the complete magazine data.
    Finaliza a criação da revista e retorna os dados completos da revista.
    """
    try:
        # Get process data from request
        # Obtém dados do processo da requisição
        process_data = request.json.get('process_data', {})
        if not process_data:
            return jsonify({'error': 'Missing process data'}), 400
        
        # Validate all required components
        # Valida todos os componentes necessários
        required_keys = ['language', 'topic', 'period', 'rewritten_articles', 'cover_content', 'cover_image']
        missing_keys = [key for key in required_keys if key not in process_data]
        
        if missing_keys:
            return jsonify({'error': f'Missing required components: {", ".join(missing_keys)}'}), 400
        
        # Extract all magazine components
        # Extrai todos os componentes da revista
        language = process_data['language']
        topic = process_data['topic']
        period = process_data['period']
        rewritten_articles = process_data['rewritten_articles']
        cover_content = process_data['cover_content']
        cover_image = process_data['cover_image']
        
        # Create complete magazine data structure
        # Cria estrutura de dados completa da revista
        magazine_data = create_magazine_raw_data(language, topic, period, rewritten_articles, cover_content, cover_image)
        
        # Return only the magazine data and success status
        # Retorna apenas os dados da revista e status de sucesso
        return jsonify({
            'magazine_data': magazine_data,
            'status': 'success'
        })
        
    except Exception as e:
        if running_locally:
            print(f"Finalization error: {e}")
        return jsonify({'error': str(e)}), 500

# Run the Flask application
# Executa a aplicação Flask
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)