from typing import Dict

def process_rewritten_article(result: str) -> Dict[str, str]:
    """Process the result of the rewrite_articles_task."""
    print("Processing rewritten article...")  # Debug print
    lines = result.strip().split('\n')
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
    
    print("Rewritten article processed successfully.")  # Debug print
    return {
        'title': new_title,
        'content': new_content,
        'source': original_source
    }