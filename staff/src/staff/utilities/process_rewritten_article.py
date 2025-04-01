
def process_rewritten_article(result: str) -> list:
    """Process the result of the rewrite_articles_task.
    Now handles multiple articles from a single combined response."""
    print("Processing rewritten articles...")  # Debug print
    
    # Split the result by article divider
    articles_raw = result.strip().split('---ARTICLE DIVIDER---')
    processed_articles = []
    
    for article_text in articles_raw:
        if not article_text.strip():  # Skip empty entries
            continue
            
        lines = article_text.strip().split('\n')
        new_title = ''
        new_content = ''
        original_source = ''
        
        current_section = None
        
        for line in lines:
            if line.startswith('NEW_TITLE:'):
                current_section = 'title'
                new_title = line.replace('NEW_TITLE:', '').strip()
            elif line.startswith('NEW_CONTENT:'):
                current_section = 'content'
                new_content = line.replace('NEW_CONTENT:', '').strip()
            elif line.startswith('ORIGINAL_SOURCE:'):
                current_section = 'source'
                original_source = line.replace('ORIGINAL_SOURCE:', '').strip()
            elif current_section == 'content':
                new_content += '\n' + line
        
        if new_title:  # Only add valid articles
            processed_articles.append({
                'title': new_title,
                'content': new_content,
                'source': original_source
            })
    
    print(f"Processed {len(processed_articles)} rewritten articles successfully.")  # Debug print
    return processed_articles