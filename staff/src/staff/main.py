#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from dotenv import load_dotenv

from crew import Staff

load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():

    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year)
    }
    
    try:
        Staff().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


if __name__ == "__main__":
    run()

