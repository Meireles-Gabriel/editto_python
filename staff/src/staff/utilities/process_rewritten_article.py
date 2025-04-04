from globals import running_locally

def process_rewritten_article(result: str) -> list:
    """
    Process the raw output from the article rewriting task.
    Converts the text format into a structured list of article dictionaries.
    Now handles multiple articles from a single combined response.
    
    Parameters:
    - result: Raw string output from the AI article rewriting task
    
    Returns:
    - List of dictionaries, each containing a rewritten article with title, content, and source
    
    Processa a saída bruta da tarefa de reescrita de artigos.
    Converte o formato de texto em uma lista estruturada de dicionários de artigos.
    Agora processa múltiplos artigos de uma única resposta combinada.
    
    Parâmetros:
    - result: String bruta de saída da tarefa de reescrita de artigos pela IA
    
    Retorna:
    - Lista de dicionários, cada um contendo um artigo reescrito com título, conteúdo e fonte
    """
    if running_locally:
        print("Processing rewritten articles...")  # Debug print
    
    # Split the result by article divider to separate multiple articles
    # Divide o resultado pelo separador de artigos para separar múltiplos artigos
    articles_raw = result.strip().split('---ARTICLE DIVIDER---')
    processed_articles = []
    
    # Process each article segment individually
    # Processa cada segmento de artigo individualmente
    for article_text in articles_raw:
        if not article_text.strip():  # Skip empty entries / Pula entradas vazias
            continue
            
        # Split article text into lines for processing
        # Divide o texto do artigo em linhas para processamento
        lines = article_text.strip().split('\n')
        new_title = ''
        new_content = ''
        original_source = ''
        
        # Track which section of the article we're currently processing
        # Acompanha qual seção do artigo estamos processando atualmente
        current_section = None
        
        # Extract article components from the formatted text
        # Extrai componentes do artigo do texto formatado
        for line in lines:
            if line.startswith('NEW_TITLE:'):
                # Extract the rewritten article title
                # Extrai o título reescrito do artigo
                current_section = 'title'
                new_title = line.replace('NEW_TITLE:', '').strip()
                
            elif line.startswith('NEW_CONTENT:'):
                # Extract the beginning of the rewritten article content
                # Extrai o início do conteúdo reescrito do artigo
                current_section = 'content'
                new_content = line.replace('NEW_CONTENT:', '').strip()
                
            elif line.startswith('ORIGINAL_SOURCE:'):
                # Extract the original source attribution
                # Extrai a atribuição da fonte original
                current_section = 'source'
                original_source = line.replace('ORIGINAL_SOURCE:', '').strip()
                
            elif current_section == 'content':
                # Append additional content lines to the article body
                # Adiciona linhas adicionais de conteúdo ao corpo do artigo
                new_content += '\n' + line
        
        # Only add articles that have a valid title
        # Adiciona apenas artigos que têm um título válido
        if new_title:
            processed_articles.append({
                'title': new_title,
                'content': new_content,
                'source': original_source
            })
            
    if running_locally:
        print(f"Processed {len(processed_articles)} rewritten articles successfully.")  # Debug print
        
    # Return the list of processed articles
    # Retorna a lista de artigos processados
    return processed_articles