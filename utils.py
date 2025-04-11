import json
import logging
import numbers
import os
import re
import time
from random import randint
from typing import Any, List, Iterator

import numpy as np
import requests
from dotenv import load_dotenv
import pandas as pd

def is_array(x: Any):
    """
    Checks if the input is an array-like structure.
    
    Args:
        x (Any): The input to check.
    
    Returns:
        bool: True if the input is an array; False if it's a scalar.
    """
    if issubclass(type(np.asarray(x)[()]), numbers.Number):
        return False
    return np.ndim(x) > 0

def clean_answer_html_tags(answer: str) ->str:
    """
    Remove HTML tags while preserving basic text structure.
    Converts list items to use "- " as a prefix and keeps line breaks.
    
    Args:
        answer (str): The input text containing HTML formatting.
    
    Returns:
        str: Cleaned text with HTML tags removed.
    """
    # Convert list items to dash points
    answer = re.sub(r'<li[^>]*>', '\n- ', answer)  # Changed to '- '
    answer = re.sub(r'</li>', '', answer)
    
    # Preserve line breaks and paragraphs
    answer = re.sub(r'<br\s*/?>', '\n', answer, flags=re.IGNORECASE)
    answer = re.sub(r'</p>', '\n\n', answer, flags=re.IGNORECASE)
    
    # Remove remaining HTML tags
    answer = re.sub(r'<[^>]+>', '', answer)
    
    # Clean whitespace
    answer = re.sub(r'\n\s*\n', '\n\n', answer)
    answer = re.sub(r'[ \t]+', ' ', answer)
    answer = re.sub(r'\n ', '\n', answer)
    
    return answer.strip()  

def clean_html_tags(content: str) -> str:
    """
    Replaces HTML tags with spaces and cleans up whitespace.
    
    Args:
        content (str): Input text that may contain HTML
        
    Returns:
        str: Cleaned text with HTML tags replaced by spaces
        
    Example:
        Input: "<div>Hello<br>World</div>"
        Output: "Hello World"
    """
    # Regex pattern explanation: <!?/?[a-zA-Z][^>]*> - Matches HTML tags (including comments and doctype)
    html_pattern = re.compile(r'<!?/?[a-zA-Z][^>]*>')
    
    # Replace HTML tags with space
    cleaned = html_pattern.sub(' ', content)
    
    # trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def get_logger(logger_name: str) -> logging.Logger:
    """
    Configures and returns a logger instance with a specified name.
    Loads environment variables from a .env file if available.
    
    Args:
        logger_name (str): The name for the logger instance.
    
    Returns:
        logging.Logger: Configured logger object.
    """
    # Load environment vars
    if os.path.exists(".env"):
        load_dotenv(dotenv_path=".env")

    # Setup logging
    api_logger = logging.getLogger(logger_name)
    api_logger.propagate = False
    # Make a logging handler
    if api_logger.hasHandlers():
        api_logger.handlers.clear()
    # Make a handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(lineno)d - %(funcName)s: %(message)s')
    handler.setFormatter(formatter)
    # Set logger level
    api_logger.setLevel(os.getenv("LOGGING_LEVEL", logging.INFO))
    # Add it to the root logger
    api_logger.addHandler(handler)
    # logging.basicConfig(level=logging.DEBUG if "DEBUG" == os.getenv("LOGGING_LEVEL") else logging.INFO,
    #                     handlers=[handler])

    return api_logger


logger = get_logger(__name__)



def remove_html_tags(content: str, abbreviate_max_length: int = None) -> str:
    """
    Removes HTML tags from the given content.
    If abbreviate_max_length is provided, the result is truncated with ellipsis.
    
    Args:
        content (str): The string to be processed.
        abbreviate_max_length (int, optional): Maximum length of the abbreviated output.
        
    Returns:
        str: Content with HTML tags removed (abbreviated if required).
    """   
    if content is None or len(content.strip()) == 0:
        return content
    if abbreviate_max_length is None:
        if is_content_html(content):
            return re.sub(r' +', ' ',
                          re.sub(r'\n+', '\n',
                                 re.sub(r'<.*?>', '\n',
                                        content).strip()))
        return content
    else:
        if is_content_html(content):
            return re.sub(r' +', ' ',
                          re.sub(r'\n+', '\n',
                                 re.sub(r'<.*?>', '\n',
                                        content).strip()))[:abbreviate_max_length] + "..."
        return content[:abbreviate_max_length] + "..."
    

def trim_string(content: str) -> str:
    if content is None or len(content.strip()) == 0:
        return content
    return content.strip()