from typing import Dict, Any

def process_cover_content(result: str) -> Dict[str, Any]:
    """Process the result of the create_cover_content_task."""
    print("Processing cover content...")  # Debug print
    lines = result.strip().split('\n')
    cover_content = {}
    
    for line in lines:
        if line.startswith('MAIN_HEADLINE:'):
            cover_content['main_headline'] = line.replace('MAIN_HEADLINE:', '').strip()
        elif line.startswith('SUBHEADING:'):
            cover_content['subheading'] = line.replace('SUBHEADING:', '').strip()
        elif line.startswith('MAIN_ARTICLE_INDEX:'):
            cover_content['main_article_index'] = int(line.replace('MAIN_ARTICLE_INDEX:', '').strip())
        elif line.startswith('SUMMARY1_INDEX:'):
            cover_content['summary1_index'] = int(line.replace('SUMMARY1_INDEX:', '').strip())
        elif line.startswith('SUMMARY1:'):
            cover_content['summary1'] = line.replace('SUMMARY1:', '').strip()
        elif line.startswith('SUMMARY2_INDEX:'):
            cover_content['summary2_index'] = int(line.replace('SUMMARY2_INDEX:', '').strip())
        elif line.startswith('SUMMARY2:'):
            cover_content['summary2'] = line.replace('SUMMARY2:', '').strip()
    
    print("Cover content processed successfully.")  # Debug print
    return cover_content