import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Conversation, ConversationalPipeline
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

app = FastAPI()

class ChatMessage(BaseModel):
    message: str

# Load Hugging Face token from environment variable
load_dotenv()
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise ValueError("Hugging Face token (HF_TOKEN) not found in environment variables.")

@app.post("/ping")
def ping():
    return {"status": "ok"}

class TextGenerator:
    def __init__(self, model_name="google/gemma-2b-it"):  # You can switch back to 2b-it if your GPU can handle it
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=hf_token)
            self.model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=hf_token).to(self.device)
            device_int = 0 if self.device == "cuda" else -1  # Correct device mapping
            self.pipeline = ConversationalPipeline(model=self.model, tokenizer=self.tokenizer, device=device_int)
        except Exception as e:  # Catch more specific exceptions if needed
            print(f"Failed to load model on {self.device}. Error: {e}")
            if self.device == 'cuda':
                print("Switching to CPU.")
                self.device = 'cpu'
                device_int = -1  # Correct device mapping
                self.pipeline = ConversationalPipeline(model=self.model, tokenizer=self.tokenizer, device=device_int)

    def generate_text(self, conversation):
        return self.pipeline(conversation)


generator = TextGenerator() # Create the generator instance outside of the endpoints

conversation = Conversation()  # Global conversation object

@app.post("/chat")
def chat(chat_message: ChatMessage):
    try:
        global conversation
        if isinstance(chat_message, ChatMessage):
            conversation.add_message(chat_message.message, "user")
            generated_responses = generator.generate_text([conversation])
            assistant_message = generated_responses[-1]['generated_text']
            conversation.add_message(assistant_message, "assistant")
            return {"response": assistant_message}
        else:
            return {"error": "Invalid chat message."}
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            return {"error": "Out of GPU memory. Try a smaller model or use CPU."}
        else:
            return {"error": f"An error occurred: {str(e)}"}

@app.post("/reset")
def reset():
    global conversation
    conversation = Conversation()
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5609)