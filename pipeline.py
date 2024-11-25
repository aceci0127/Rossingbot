import logging
import streamlit as st

# Configure logging to show info level messages with timestamp and log level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import required libraries
import openai 
from pinecone import Pinecone
import cohere
import os
from dotenv import load_dotenv 
import json

# Load environment variables from .env file
load_dotenv("search/.env")

class AthenaPipeline:
    def __init__(self, query, conversation_list, namespace):
        
        # Retrieve API keys from environment variables
        #openai_api_key = os.getenv('OPENAI_API_KEY')
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        cohere_api_key = os.getenv('COHERE_API_KEY')
        # Initialize query and memory variables
        self.query = query
        self.conversation_list = conversation_list
        self.memory = ""
        self.namespace = ""

        # Initialize OpenAI client with API key
        self.client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        # Initialize Pinecone client with API key
        self.pc = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])

        # Initialize Cohere client with API key
        self.co = cohere.Client(api_key=st.secrets["COHERE_API_KEY"])

    def perform_embedding(self, text, model="text-embedding-3-large"):
        logging.info("Performing embedding for the provided text...")
        # Ensure the input text is a string
        if not isinstance(text, str):
            text = str(text)
        try:
            # Create an embedding vector using OpenAI's embedding model
            response = self.client.embeddings.create(input=text, model=model)
            vector = response.data[0].embedding
            logging.info("Embedding performed successfully!")
            return vector
        except Exception as e:
            logging.error(f"Failed to perform embedding: {e}")
            return None

    def memory_generation(self, conversation_list):
        logging.info("Generating memory summary from conversation list...")
        # Generate a summary of the conversation using a detailed prompt
        prompt = """
        You are provided with a list of questions and answers from a conversation between a user and a chatbot. 
        The questions are arranged from the oldest to the most recent. 
        Your task is to generate a detailed and accurate summary of the conversation, with particular emphasis on the latest question and answer. 

        Guidelines:
            •	Clearly indicate what the user asked in each question.
            •	Clearly highlight the chatbot’s response to each question.
            •	Focus more attention on the latest question and answer, providing additional details or context revealed in that interaction.
            •	Do not include any subjective comments or conclusions.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "user", "content": f"Conversazione: {conversation_list}."}
            ],
            temperature=0.1
        )
        answer = response.choices[0].message.content
        logging.info(f"Memory summary generated successfully:{answer}")
        return answer

    def refined_query(self, query, memory):
        logging.info("Refining user query based on provided memory...")
        # Refine the user query to make it more precise for vector searches
        prompt = """
        If the user’s question does not provide clear context, use the conversation history to fill in the missing information.
        If the context is already present, keep the user’s query as close to the original as possible, making only slight refinements to improve its accuracy.
        Avoid adding unnecessary details or expanding the context beyond what is required.
        The reformulated question should be clear, concise, and natural, as if it were directly asked by the user.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "user", "content": f"Memoria:{memory}. Query:{query}."}
            ],
            temperature=0.2
        )
        answer = response.choices[0].message.content
        logging.info(f"User query refined successfully: {answer}")
        return answer

    def HyDE(self, query):
        logging.info("Generating response using HyDE method...")
        # Generate a response to the given question
        prompt = """
        Answer the question concisely and briefly.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "user", "content": f"Domanda::{query}."}
            ],
            temperature=0.1
        )
        answer = response.choices[0].message.content
        logging.info(f"HyDE response generated successfully: {answer}")
        return answer

    def sub_queries(self, query):
        logging.info("Segmenting user query into sub-queries...")
        # Split the query into multiple parts if necessary to improve vector search
        prompt = """
        - Segment the question into as many parts as necessary to improve vector search.
	    - For example, if the question involves comparing two or more concepts, identify and separate each concept.
	    - Format the output following this example:
        1# Concept 1
        2# Concept 2
        3# Concept 3
        4# Concept 4
        You can use as many concepts as needed.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "user", "content": f"Domanda:{query}."}
            ],
            temperature=0.1
        )
        answer = response.choices[0].message.content
        # Split the answer into individual sub-queries by parsing the response
        sub_queries_list = [line.split('# ', 1)[-1] for line in answer.splitlines() if line.strip()]
        logging.info(f"Generated sub-queries: {sub_queries_list}")
        return sub_queries_list

    def perform_search(self, input_text, index, namespace):
        logging.info(f"Performing search in Pinecone index '{index}' with input text: {input_text}")
        # Perform a search in the specified Pinecone index using the provided input text
        try:
            indice = self.pc.Index(index)
            vec = self.perform_embedding(input_text)  # Get the embedding vector for the input text
            if vec is None:
                raise ValueError("Embedding vector is None. Skipping search.")
            query_results = indice.query(
                namespace=namespace,  # Define the namespace for the query
                vector=vec,  # Use the embedding vector for the search
                top_k=4,  # Return the top 2 matches
                include_values=True,
                include_metadata=True)
            # Extract metadata text and scores from the query results
            metadata_list = [match['metadata']['text'] for match in query_results['matches']]
            score_list = [match['score'] for match in query_results['matches']]
            logging.info(f"Search results Scores: {score_list}")
            # Return results only if the score of the top match is above the threshold
            if score_list[0] < 0.25:
                logging.warning("No relevant results found with a sufficient score.")
                return []
            else:
                logging.info("Search results retrieved successfully.")
                return metadata_list
        except Exception as e:
            logging.error(f"Failed to perform search: {e}")
            return ""

    def rerank_documents(self, documents, query):
        logging.info("Reranking documents using Cohere...")
        # Use Cohere to rerank the retrieved documents
        try:
            rerank_docs = self.co.rerank(
                query=query, documents=documents, top_n=25, model="rerank-english-v2.0"
            )
            # Get the indices of the reranked documents
            reranked_indices = [doc.index for doc in rerank_docs.results]
            logging.info(f"Reranked document indices: {reranked_indices}")
            # Filter the list of documents to include only the reranked documents
            reranked_docs = [documents[i] for i in reranked_indices]
            #logging.info(f"Reranked documents: {reranked_docs}")
            return reranked_docs
        except Exception as e:
            logging.error(f"Failed to rerank documents: {e}")
            return []
    

    def perform_response(self, query, reranked_docs):
        logging.info("Generating final response based on retrieved results and user query...\n\n\n")
        # Generate a final response using the retrieved texts and user query
        prompt = """Your name is Athena.
        To generate a response based on the retrieved text and the user’s question, follow these steps:

        1. Understand the Question:
	        •	Identify and clarify the main question being asked.
	        •	Determine whether the question requires a brief or detailed response.

        2. Gather Information:
            •	Review the retrieved text and the conversation memory.
            •	Extract only the relevant information that directly answers the question.

        3. Formulate the Response:
            •	If relevant text is available, use it to construct your answer.
            •	If no relevant text is found, rely on your knowledge base.

        4. Draft the Response:
            •	Provide a clear and concise explanation if the question is straightforward.
            •	Offer an in-depth explanation if the question requires more detail.

        5. Format and Review:
            •	Ensure the response is well-structured and easy to read.
            •	Review for clarity and consistency.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"{prompt}"},
                    {"role": "user", "content": f"-Domanda:{query} \n\n-Testo:{reranked_docs}."}
                ],
                temperature=0.2
            )
            answer = response.choices[0].message.content
            logging.info(f"Query: {query}\n\n\n")
            logging.info(f"Document used: {reranked_docs}\n\n\n")
            logging.info("Final response generated successfully.\n\n\n")
            logging.info(f"Generated answer: {answer}\n\n\n")
            return answer
        except Exception as e:
            logging.error(f"Failed to generate response: {e}")
            return "Failed to generate response: {e}"


    def run_pipeline(self, query, conversation_list, namespace):
        # Generate refined queries and possible answers
        memory = self.memory_generation(conversation_list)  # Generate a summary of the conversation
        logging.info("Generating refined query, HyDE response, and sub-queries...")
        rq = self.refined_query(query, memory)  # Refined version of the query
        hyde = self.HyDE(rq)  # Generate a response using the HyDE method
        sq = self.sub_queries(rq)  # Generate sub-queries if the query is complex
        index_name = "eli-demo"

        # Perform searches using the refined query, HyDE answer, and sub-queries
        logging.info(f"Performing searches with refined query, HyDE, and sub-queries in namespace: {namespace}\n")
        res1 = self.perform_search(rq, index_name, namespace)  # Search using refined query
        res2 = self.perform_search(hyde, index_name, namespace)  # Search using HyDE response

        # Perform multiple searches based on the split sub-queries
        res3 = []
        for sub_query in sq:
            res3.extend(self.perform_search(sub_query, index_name, namespace))  # Search using each sub-query

        # Combine results from all searches
        if res1 == []:
            res = res2 + res3
        elif res2 == []:
            res = res1 + res3
        elif res3 == []:
            res = res1 + res2
        elif res1 == [] and res2 == []:
            res = res3
        elif res1 == [] and res3 == []:
            res = res2
        elif res2 == [] and res3 == []:
            res = res1
        elif res1 == [] and res2 == [] and res3 == []:
            res = []
        else:
            res = res1 + res2 + res3
        res = list(set(res))
        #logging.info(f"Combined search results: {res}")

        # Rerank documents
        reranked_docs = self.rerank_documents(res, rq)

        #Utility Detector
        logging.info(f"The redifined query is: {rq}\n\n")
        # Generate final response
        logging.info("Generating final answer based on search results.")
        answer = self.perform_response(rq, reranked_docs)
        return answer