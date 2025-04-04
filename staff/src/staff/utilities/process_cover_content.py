from typing import Dict, Any
from globals import running_locally

def process_cover_content(result: str) -> Dict[str, Any]:
    """
    Process the raw output from the cover content creation task.
    Converts the text format into a structured dictionary with magazine cover elements.
    
    Parameters:
    - result: Raw string output from the AI cover content generation task
    
    Returns:
    - Dictionary containing structured cover content (headlines, summaries, and article indices)
    
    Processa a saída bruta da tarefa de criação de conteúdo da capa.
    Converte o formato de texto em um dicionário estruturado com elementos da capa da revista.
    
    Parâmetros:
    - result: String bruta de saída da tarefa de geração de conteúdo de capa pela IA
    
    Retorna:
    - Dicionário contendo conteúdo estruturado da capa (manchetes, resumos e índices de artigos)
    """
    if running_locally:
        print("Processing cover content...")  # Debug print
        
    # Split the result into lines for processing
    # Divide o resultado em linhas para processamento
    lines = result.strip().split('\n')
    cover_content = {}
    
    # Extract each cover element from the formatted text
    # Extrai cada elemento da capa do texto formatado
    for line in lines:
        if line.startswith('MAIN_HEADLINE:'):
            # Extract the main headline/title for the magazine cover
            # Extrai a manchete/título principal para a capa da revista
            cover_content['main_headline'] = line.replace('MAIN_HEADLINE:', '').strip()
            
        elif line.startswith('SUBHEADING:'):
            # Extract the subheading/subtitle for the magazine cover
            # Extrai o subtítulo para a capa da revista
            cover_content['subheading'] = line.replace('SUBHEADING:', '').strip()
            
        elif line.startswith('MAIN_ARTICLE_INDEX:'):
            # Extract the index of the main featured article
            # Extrai o índice do artigo principal em destaque
            cover_content['main_article_index'] = int(line.replace('MAIN_ARTICLE_INDEX:', '').strip())
            
        elif line.startswith('SUMMARY1_INDEX:'):
            # Extract the index of the first summary article
            # Extrai o índice do primeiro artigo resumido
            cover_content['summary1_index'] = int(line.replace('SUMMARY1_INDEX:', '').strip())
            
        elif line.startswith('SUMMARY1:'):
            # Extract the text summary of the first highlighted article
            # Extrai o resumo de texto do primeiro artigo destacado
            cover_content['summary1'] = line.replace('SUMMARY1:', '').strip()
            
        elif line.startswith('SUMMARY2_INDEX:'):
            # Extract the index of the second summary article
            # Extrai o índice do segundo artigo resumido
            cover_content['summary2_index'] = int(line.replace('SUMMARY2_INDEX:', '').strip())
            
        elif line.startswith('SUMMARY2:'):
            # Extract the text summary of the second highlighted article
            # Extrai o resumo de texto do segundo artigo destacado
            cover_content['summary2'] = line.replace('SUMMARY2:', '').strip()
    
    if running_locally:
        print("Cover content processed successfully.")  # Debug print
        
    # Return the structured cover content dictionary
    # Retorna o dicionário estruturado de conteúdo da capa
    return cover_content