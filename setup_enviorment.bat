@echo off
echo Setting up virtual enviorments, please wait...
echo Creating venv for gui-p
cd gui-p
python -m venv .venv
.venv\Scripts\pip.exe install requests customtkinter
echo Creating venv for daemon
cd ..
cd daemon
python -m venv .venv
.venv\Scripts\pip.exe install dotenv-python transformers fastapi pydantic uvicorn
.venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu121
echo HF_TOKEN=YOUR_HUGGING_FACE_TOKEN > .env
echo HF_HUB=./model/ >> .env