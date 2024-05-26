import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Conversation, ConversationalPipeline
from fastapi import FastAPI
from pydantic import BaseModel
import os, sys
from dotenv import load_dotenv
import argparse

parser = argparse.ArgumentParser(description='Run the server with specified options.')
parser.add_argument('--force-cpu', action='store_true', help='Force the use of CPU even if GPU is available.')
args = parser.parse_args()

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
    def __init__(self, model_name="google/gemma-2b-it", force_cpu=False):  # You can switch back to 2b-it if your GPU can handle it
        torch_name = torch.cuda.get_device_name(0)
        zluda = False

        if "[ZLUDA]" in torch_name:
            zluda = True
            print("Warning: ZLUDA detected. Instability may occur. Find more information at https://todo.wojtmic.dev/zluda.")
            print("Due to ZLUDA, applying multiple workarounds.")
            print("If You encounter any issues, add --force-cpu flag to the command line or use $startcpu in the GUI.\n")
            if torch.backends.cudnn.enabled:
                print("Disabling cuDNN.")
                torch.backends.cudnn.enabled = False
            print("Enabling CUDA flash SDP.")
            torch.backends.cuda.enable_flash_sdp(True)
            print("Disabling CUDA math SDP.")
            torch.backends.cuda.enable_math_sdp(False)
            print("Disabling CUDA memory efficient SDP.")
            torch.backends.cuda.enable_mem_efficient_sdp(False)

            print("Most ZLUDA workarounds applied sucessfully.")
            print("Continuing standard daemon operation. One more workaround ready to apply.\n")

        if force_cpu:
            self.device = 'cpu'
        else:
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
        if zluda:
            print("Applying pending ZLUDA workaround.")
            print("Disabling PyTorch cross-attention.")
            for module in self.model.modules():
                if isinstance(module, torch.nn.MultiheadAttention):
                    module.register_forward_hook(self.disable_cross_attention)
            print("ZLUDA workaround applied successfully.\n")
    
    def zero_out_cross_attention(self, module, input, output):
        output[0] = torch.zeros_like(output[0])  # Zero out the cross-attention output

    def disable_cross_attention(self, module, input, output):
        try:
            output[0] = torch.zeros_like(output[0])  # Zero out the cross-attention output
        except RuntimeError as e:
            if "CUDA error: operation not supported" in str(e):
                print("Warning: Cross-attention operation not supported on this GPU. Using CPU fallback.")
                self.device = 'cpu'  # Switch to CPU if the operation is not supported
                # Re-initialize the pipeline on CPU
                device_int = -1
                self.pipeline = ConversationalPipeline(model=self.model.to('cpu'), tokenizer=self.tokenizer, device=device_int)
                # Now, retry generating the output on CPU
                output[0] = torch.zeros_like(output[0].to('cpu'))  # Zero out on CPU
            else:
                raise e  # Raise other RuntimeError

    def generate_text(self, conversation):
        print("Generating text...")
        return self.pipeline(conversation)

if args.force_cpu:
    print("Forcing CPU usage.")
    generator = TextGenerator(force_cpu=True) # Create the generator instance outside of the endpoints
else:
    generator = TextGenerator()

conversation = Conversation()  # Global conversation object

@app.post("/chat")
def chat(chat_message: ChatMessage):
    try:
        global conversation
        if isinstance(chat_message, ChatMessage):
            print("Received chat message:", chat_message.message)
            conversation.add_message({"role": "user", "content": chat_message.message})
            conversation = generator.generate_text(conversation)
            assistant_message = [msg['content'] for msg in conversation.messages if msg['role'] == 'assistant'][-1]
            print("Generated assistant message:", assistant_message)
            return {"response": assistant_message}
        else:
            print("Invalid chat message:", chat_message)
            return {"error": "Invalid chat message."}
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            print("Out of GPU memory.")
            return {"error": "Out of GPU memory. Try a smaller model or use CPU."}
        else:
            print("An error occurred:", str(e))
            return {"error": f"An error occurred: {str(e)}"}

@app.post("/reset")
def reset():
    global conversation
    conversation = Conversation()
    return {"status": "ok"}

@app.post("/stop")
def stop():
    print("Stopping daemon, goodbye!")
    sys.exit()
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5609)