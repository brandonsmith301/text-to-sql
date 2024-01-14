TEXT-TO-SQL WITH CONTEXT GENERATION
===
Text-to-SQL translates natural language into SQL, making database interactions easier for those without SQL technical expertise. OpenAI's GPT-3.5 and GPT-4 have shown good results in this area - provided that it was given the right instructions. However, since they are no longer open-sourced and can be slow due to accessibility by a wide range of users, they may not be the best option for businesses, as well as being costly. In this project, we developed a framework which utilises a dual retrieval strategy: It initially searches through a historical database of past queries to find and utilise context from similar previous inputs. For new or distinct inputs, it performs a semantic search within the user database metadata to dynamically construct relevant context. The pre-trained model used for this project is CodeLlama-7b-Instruct which was fine-tune on a 78.6k SQL dataset. 

## Requirements
- accelerate==0.25.0
- peft==0.7.1
- bitsandbytes==0.41.3.post2
- trl==0.7.4
- peft==0.5.0
- sentence-transformers
- transformers

## Use
- for evaluation
  ```
  evaluation/text-to-sql-evaluation.ipynb
  ```

## Directory Hierarchy
```
|—— evaluation
|    |—— context.sql
|    |—— text-to-sql-evaluation.ipynb
|—— model
|    |—— ContextSQL-7b
|        |—— README.md
|        |—— adapter_config.json
|        |—— adapter_model.safetensors
|    |—— requirements.txt
|—— training
|    |—— fine-tuning-text-to-sql.ipynb
|    |—— training_data.json
|—— utils
|    |—— context_generation.py
|    |—— create_database.py
```

### Results

| Model          | Accuracy |
|----------------|----------|
| GPT-4          | 100%     |
| GPT-3.5        | 90%      |
| Gemini-Pro     | 60%      |
| CodeLlama-FT-7B| 50%      |

### WIP..

TODO: Implement a historical vector database to retrieve successful query inputs. This database will provide additional context for new queries if the retrieved similarity is greater than a predefined threshold.

