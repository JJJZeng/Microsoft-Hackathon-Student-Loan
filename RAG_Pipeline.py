from openai import AzureOpenAI
from dotenv import dotenv_values
import json
from prompts import prompt_gpt
from uuid import uuid4
from utils import get_logger,clean_html_tags,trim_string,clean_answer_html_tags

from Azure_ContentSafety_jailbreak import jail_break_detect

# Create a logger to track events and help with debugging.
logger = get_logger(__name__)

class AzureBlobDataRAG:
    """
    Class to handle Retrieval Augmented Generation (RAG) functionality using hybrid search
    Inherits from DataRAGBase and implements:
    - Document retrieval,
    - Retrieval reordering,
    - Prompt construction,
    - Calling the LLM interface. 
    """
    # Class attributes declarations. They will be set later during initialization.
    
    endpoint: str = None
    deployment: str = None
    search_endpoint: str = None
    search_key: str = None
    subscription_key: str = None
    
    def __init__(self):
        config =dotenv_values("Configuration.env")

        self.endpoint=config['ENDPOINT_URL']
        self.deployment=config['DEPLOYMENT_NAME']
        self.search_endpoint=config['SEARCH_ENDPOINT']
        self.search_key=config['SEARCH_KEY']
        self.subscription_key=config['AZURE_OPENAI_API_KEY']
        self.index_name=config["INDEX_NAME"]
        
        logger.info("Load the azure API configuration")
        logger.debug(f"model={self.deployment}")
        
    def invoke_llm(self,
                   query:str,
                   k: int):
        """
        Searches the vector store for relevant documents based on the asking_question.
        
        Parameters:
            query: Input question string.
            k: Number of documents to retrieve.
            
        Returns:
            A dictionary with answer name and search results.
        """
        uuid = str(uuid4())
        
        #check for the jail break
        jail_break_filter=jail_break_detect(user_query=query,document_list=[""])
        flag_jailbreak=jail_break_filter['userPromptAnalysis']['attackDetected']
        if flag_jailbreak:
            ai_answer=""
            return {"uuid": uuid,
                    "jailbreak_violated": flag_jailbreak}
        
        client =AzureOpenAI(
        azure_endpoint=self.endpoint,
        api_key=self.subscription_key,
        api_version="2024-05-01-preview"
        )
        
        prompt=prompt_gpt.PROMPT
        messages = [
            {
                "role": "system",
                "content": f"{prompt}"
            },
            {
                "role":"user",
                "content":f"{query}"
            }        
        ]
        
        completion= client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            max_tokens=1000,
            temperature=0.1,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False,
            extra_body={
                "data_sources":[
                    {
                        "type":"azure_search",
                        "parameters":{
                            "filter":None,
                            "endpoint": f"{self.search_endpoint}",
                            "index_name": self.index_name,
                            "semantic_configuration":"azureml-default",
                            "authentication": {
                                "type":"api_key",
                                "key":f"{self.search_key}"
                            },
                            "embedding_dependency":{
                                "type":"endpoint",
                                "endpoint":f"{self.endpoint}/openai/deployments/text-embedding-ada-002/embeddings?api-version=2023-05-15",
                                "authentication":{
                                    "type": "api_key",
                                    "key":f"{self.subscription_key}"
                                }
                            },
                            "query_type":"vector_simple_hybrid",
                            "in_scope":True,
                            "role_information":f"{prompt}",
                            "strictness":3,
                            "top_n_documents":k
                        }
                    }
                ]
            }
            
        )
        
        res=json.loads(completion.to_json())
        
        ai_answer=res["choices"][0]["message"]['content']
        ai_answer = clean_answer_html_tags(trim_string(ai_answer))
        
        search_results=res["choices"][0]["message"]['context']['citations']
        document_sources = [({
            'raw_text': (clean_html_tags(doc['content'])[0:350] if "content" in doc else ""),
            'source_url': (doc['url'] if "url" in doc else "")
            })
        for doc in search_results[:k]]
        
        # Use a dictionary to filter out duplicate source_url entries
        unique_sources = {}
        for source in document_sources:
            unique_sources[source["source_url"]] = source

        # Convert back to list format
        document_sources = list(unique_sources.values())
        
        
        response_context = {
                "question": query,
                "answer": ai_answer,
                "llm_model_id": self.deployment,
                "sources": document_sources
            }

        return {
            "uuid": uuid,
            **response_context
        }
        
###############################################################################################
if __name__ == "__main__":
    import os
    import sys

    logger.info("====================================================\nStart to test the retrieval elasticsearch backend...")

    question = "I did not receive a welcome email. How do I register?"

    # Instantiate the AzureBlobDataRAG class for processing
    data_rag_hybridsearch=AzureBlobDataRAG()
    final_output=data_rag_hybridsearch.invoke_llm(query=question,k=10)

    logger.info("====================================================\nEnd testing with the answer: \n {}".format(final_output['answer']))        
        
        