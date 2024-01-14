import os
import re
import spacy
import torch
import torch.nn.functional as F
from typing import (
    Dict,
    List, 
    Tuple, 
    Optional, 
    Any,
    Set
)

import subprocess
import sys

try:
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError:   
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "sentence_transformers"]
    )
    from sentence_transformers import SentenceTransformer  

if os.getenv("TOKENIZERS_PARALLELISM") is None:
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    
def read_context(
    path: str
) -> Optional[Dict[str, Dict[str, List[Any]]]]:
    """
    Reads context.sql file and parses it to generate a structured format.
    """
    try:
        with open(path, 'r') as f:
            context = f.read()
            context = parse_context(context)
    except FileNotFoundError:
        print(f"File is not found: {path}")
        return None
        
    return context


def load_encoder(
    model_path: str
) -> SentenceTransformer:
    """
    Load SentenceTransformer to create word embeddings.
    """
    return SentenceTransformer(
        model_path, device="cpu"
    )


def encodes(
    text: str
) -> torch.Tensor:
    """
    Encodes the input text using a SentenceTransformer model.
    """
    encoder = load_encoder(
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    
    emb = encoder.encode(
        text, convert_to_tensor=True, show_progress_bar=False, 
        device="cpu"
    )
    return emb


def parse_context(
    context: str
) -> Dict[str, Dict[str, List[Any]]]:
    
    """
    Given context.sql - which should contain the SQL used for creating the tables in a user database, we generate a format
    which can be used for the similarity search, this means the user will not have to parse this on their end.

    STEPS:
        1. Split parts for each CREATE TABLE statement and initialize dictionary.
        2. Run loop to break the statement into parts, i.e., table, column, constraints, and comments.
        3. Parse into dictionary format.
    """
    
    # split tables
    tables = re.split(
        r';\s*(?=--.*?\nCREATE TABLE)', 
        context
    )
    
    tables_dictionary = {}

    for text in tables:
        # get table comment
        table_comment_search = re.search(
            r'--(.*?)\nCREATE TABLE (\w+)', 
            text, 
            re.DOTALL
        )
        
        # if no table comment continue..
        if not table_comment_search:
            continue
        table_comment, t_name = table_comment_search.groups()
        table_comment = table_comment.strip()

        tables_dictionary[t_name] = {
            "comment": table_comment,
            "columns": {}, 
            "constraints": []
        }

        lines = text.split('\n')
        column_comment = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('CREATE TABLE'):
                continue

            if line.startswith('--'):
                column_comment = line.strip('--').strip()
                continue

            if 'PRIMARY KEY' in line or 'FOREIGN KEY' in line:
                tables_dictionary[t_name]["constraints"].append(line.strip(','))
                continue

            column_details = re.match(r'(\w+)\s+(\w+)(.*)', line)
            if column_details:
                c_name, c_type, _ = column_details.groups()
                tables_dictionary[t_name]["columns"][c_name] = {
                    "type": c_type,
                    "comment": column_comment
                }
                column_comment = None  

    return tables_dictionary


def get_top_k(
    question: str, 
    tables_metadata: Dict[str, Dict[str, Any]], 
    k: int = 5
) -> Optional[Dict[str, List[str]]]:
    """
    Retrieves the top-k tables based on similarity to the question.
    
    k determines the top k returned default is 5
    """
    question_emb = encodes(question)
    
    # generate embeddings for all table comments
    table_embs = [
        encodes(table_info['comment']) 
        for table_info in tables_metadata.values()
    ]
    table_embs_tensor = torch.stack(table_embs)

    # utilise cosine in batch
    cos_similarities = torch.nn.functional.cosine_similarity(
        question_emb, table_embs_tensor
    )

    # retrieve the top k indices based on similarity
    _, top_k_indices = torch.topk(
        cos_similarities, k=min(k, len(cos_similarities))
    )

    results = {}
    table_names = list(
        tables_metadata.keys()
    )

    for i in top_k_indices:
        table_name = table_names[i]
        table_info = tables_metadata[table_name]
        column_names = list(
            table_info['columns'].keys()
        )
        
        results[table_name] = column_names

    return prune_top_k(question, results, tables_metadata) 


def extract_key_columns(
    constraints: List[str], 
    referenced_tables: Set[str]
) -> Dict[str, List[str]]:
    """
    Extracts key columns from foreign key constraints - this ensures whenever there are 2 or more tables the PK
    and FK are returned in the context input.
    """
    key_columns = {}
    for constraint in constraints:
        # extract the FK and referenced table
        fk_match = re.search(
            r'FOREIGN KEY\s*\(([^)]+)\)\s+REFERENCES\s+(\w+)', constraint
        )
        if fk_match:
            fk_column, referenced_table = fk_match.groups()
            if referenced_table in referenced_tables:
                fk_column = fk_column.strip()
                key_columns.setdefault(
                    referenced_table, []
                ).append(fk_column)
                
    return key_columns


def format_top_k(
    pruned_results: Dict[str, list]
) -> str:
    """
    Formats the top-k results which is fed as the context for the input.
    """
    output = [
        f"(TABLE: {table_name} COLUMNS: {', '.join(columns)})"
        for table_name, columns in pruned_results.items()
    ]
    return ' '.join(output)


def prune_top_k(
    question: str,
    results: Dict[str, Dict[str, dict]], 
    tables_metadata: Dict[str, Dict[str, dict]]
) -> str:
    """
    Prunes the top-k tables and columns based on similarity to the question.
    
    STEPS:
        1. Calculate cosine similarities for all table comments and column descriptions against the encoded question.
        2. Find the average similarity across all tables and columns, then slightly reduce it to broaden the selection criteria.
        3. Select tables and columns that exceed the mean similarity threshold.
        4. Adjust the final output to include necessary primary and foreign key columns.

    """
    question_emb = encodes(question)
    all_sim = []

    # Step 1: compute similarities
    for table_info in tables_metadata.values():
        table_comment = table_info['comment']
        table_emb = encodes(table_comment)
        table_sim = torch.nn.functional.cosine_similarity(
            question_emb, table_emb, dim=0
        )
        
        all_sim.append(table_sim.item())
        
        # move to columns in table
        for column_desc in table_info['columns'].values():
            column_desc = column_desc['comment']
            column_emb = encodes(column_desc)
            column_sim = torch.nn.functional.cosine_similarity(
                question_emb, column_emb, dim=0
            )
            all_sim.append(column_sim.item())

    # Step 2: determine mean similarity - minus by threshold
    mean_similarity = (sum(all_sim) / len(all_sim))
    mean_similarity = mean_similarity - (mean_similarity * 0.05)
    pruned_results = {}

    # Step 3: prune based on mean similarity
    for table_name, table_info in tables_metadata.items():
        table_comment = table_info['comment']
        table_emb = encodes(table_comment)
        table_sim = torch.nn.functional.cosine_similarity(
            question_emb, table_emb, dim=0
        )

        if table_sim.item() > mean_similarity:
            pruned_columns = []  # reset pruned columns for each table

            for column_name, column_desc in table_info['columns'].items():
                column_desc = column_desc['comment']
                column_emb = encodes(column_desc)
                column_sim = torch.nn.functional.cosine_similarity(
                    question_emb, column_emb, dim=0
                )
                
                if column_sim.item() > mean_similarity:
                    pruned_columns.append(column_name)
                    
            if pruned_columns:
                pruned_results[table_name] = pruned_columns

    # Step 4: ensure inclusion of primary and foreign keys
    referenced_tables = set(pruned_results.keys())

    for table_name, table_info in tables_metadata.items():
        if table_name in pruned_results:
            fk_columns_info = extract_key_columns(
                table_info.get('constraints', []), referenced_tables
            )

            for ref_table, columns in fk_columns_info.items():
                # ensure PK/FK at the start of column in context
                pruned_results[table_name] = columns + pruned_results[table_name]

                if ref_table != table_name and ref_table in pruned_results:
                    pruned_results[ref_table] = columns + pruned_results[ref_table]

    return format_top_k(pruned_results)


def generate_prompt(
    context_path: str, 
    question: str
) -> str:
    """
    Generates prompt for a text-to-SQL model.
    """
    context = get_top_k(
        question, read_context(context_path)
    )

    prompt = (
        "### Question: {user_question}\n"
        "### Context: {table_metadata_string}\n"
        "### Answer: {Answer}"
    ).format(
        user_question=question,
        table_metadata_string=context,
        Answer=""
    )

    return prompt