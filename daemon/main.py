import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Conversation, pipeline
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

app = FastAPI()
conversation = None
conversation_history = None

class ChatMessage(BaseModel):
    message: str

# Load Hugging Face token from environment variable
load_dotenv()
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise ValueError("Hugging Face token (HF_TOKEN) not found in environment variables.")

# Load tokenizer and model
model_name = "google/gemma-2b-it"  # Start with a smaller model
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=hf_token)
model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=hf_token)

# Use GPU if available, otherwise fallback to CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
print(f"Using device: {device}")

# Initialize conversation pipeline
conversational_pipeline = pipeline("conversational", model=model, tokenizer=tokenizer, device=0 if torch.cuda.is_available() else -1)

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/chat")
def chat(chat_message: ChatMessage):
    global conversation

    # Initialize conversation if it doesn't exist
    if conversation is None:
        conversation = Conversation()

    try:
        # Add user message to the conversation
        conversation.add_user_input(chat_message.message)

        # Generation parameters for Gemma
        generation_params = {
            "max_new_tokens": 128,  
            "temperature": 0.7,     
            "top_p": 0.95,         
        }

        # Use the conversational_pipeline with generation parameters
        conversation = conversational_pipeline(
            [conversation], 
            model=model, 
            tokenizer=tokenizer,
            generation_params=generation_params
        )[0]

        # Extract and return the bot's response
        response_text = conversation.generated_responses[-1]
        return {"message": response_text}

    except torch.cuda.OutOfMemoryError:
        return {"error": "Out of GPU memory. Try reducing the max_new_tokens or use CPU."}


# Initialize conversation history outside endpoints
conversation_history = None 

@app.post("/reset")
def reset():
    global conversation_history, conversation
    conversation_history = []
    conversation = None
    return {"status": "Conversation reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5609)  # Use a fixed port for now