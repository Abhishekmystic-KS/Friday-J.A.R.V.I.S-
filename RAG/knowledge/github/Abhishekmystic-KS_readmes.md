## Abhishekmystic-KS/Friday-J.A.R.V.I.S-

# J.A.R.V.I.S 

This is a voice assistant project in progress.


## Main files

- [scripts/run_assistant.py](scripts/run_assistant.py) — run assistant
- [scripts/run_orb.py](scripts/run_orb.py) — run orb only
- [src/jarvis/assistant.py](src/jarvis/assistant.py) — assistant logic
- [src/jarvis/ui/orb_popup.py](src/jarvis/ui/orb_popup.py) — UI
- [config/app.json](config/app.json) — settings
- [env/.env](env/.env) — API key

## Demo Video
[![Demo](./readmeui/preview.gif)](./readmeui/demovideo.mp4)
<video src="https://raw.githubusercontent.com/Abhishekmystic-KS/Friday-J.A.R.V.I.S-/db326c0586b9412a7d377337528fd355cc3d538f/readmeui/demovideo.mp4" controls="controls" muted="muted" style="max-width: 100%;"></video>

## Quick setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install "setuptools<81"
```

Add key to [env/.env](env/.env):

```env
GROQ_API_KEY=your_groq_key_here
```

## Run

```bash
python scripts/run_assistant.py
```

## Basic voice commands

- Wake: `friday`, `hey friday`, `wake up`
- Sleep: `go to sleep friday`

## Notes

- Project is still being improved.
- Logs: [data/logs](data/logs)

Current goal:
- listen from mic
- wake/sleep by voice
- transcribe with Groq
- reply with LLM + TTS
- show orb popup UI

## Main files

- [scripts/run_assistant.py](scripts/run_assistant.py) — run assistant
- [scripts/run_orb.py](scripts/run_orb.py) — run orb only
- [src/jarvis/assistant.py](src/jarvis/assistant.py) — assistant logic
- [src/jarvis/ui/orb_popup.py](src/jarvis/ui/orb_popup.py) — UI
- [config/app.json](config/app.json) — settings
- [env/.env](env/.env) — API key

## Quick setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install "setuptools<81"
```

Add key to [env/.env](env/.env):

```env
GROQ_API_KEY=your_groq_key_here
```

## Run

```bash
python scripts/run_assistant.py
```

## Basic voice commands

- Wake: `friday`, `hey friday`, `wake up`
- Sleep: `go to sleep friday`

## Notes

- Project is still being improved.
- Logs: [data/logs](data/logs)


---

## Abhishekmystic-KS/Enhanced_Facial_Expression_and_Hand_Gesture_recognition_System

# Enhanced Facial Expression and Hand Gesture Recognition System

A real-time Python application for recognizing facial expressions and hand gestures using a webcam. The system features advanced hand landmark detection, finger counting capabilities, and an enhanced UI.

## How it works?
https://github.com/user-attachments/assets/7e8b4e7e-483a-4980-830c-d86b58c324cf


## 🌟 Features

- **Real-time Face Detection**
  - Multiple facial expression recognition
  - Support for 13 different expressions
  - Confidence score display

- **Advanced Hand Detection**
  - Real-time hand gesture recognition
  - Precise finger counting (0-5 fingers)
  - Hand landmark tracking
  - Support for 14 different gestures

- **Enhanced UI**
  - Multiple display modes (default, debug, minimal)
  - Real-time performance metrics
  - Confidence visualization
  - History tracking

- **Performance Optimizations**
  - Multi-threading support
  - Motion detection
  - Frame downscaling
  - Optimized detection parameters

## 🛠️ Technology Stack

- OpenCV - Image processing and webcam handling
- MediaPipe - Hand landmark detection
- Scikit-learn - Machine learning models
- NumPy - Numerical processing
- Scikit-image - Feature extraction

## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/expression-gesture-recognition.git
   cd expression-gesture-recognition
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

### Basic Application
```bash
python main.py
```

Options:
- `--use_advanced_features`: Enable advanced feature extraction
- `--use_threading`: Enable multi-threaded processing
- `--use_motion_detection`: Enable motion detection
- `--downscale_factor`: Frame downscale factor (percentage)
- `--ui_mode`: UI mode (default, debug, minimal)

### Finger Counting Application
```bash
python finger_counting_app.py [--threshold 60] [--blur 41]
```

### Advanced Gesture Recognition
```bash
python advanced_gesture_recognition.py [options]
```

## 🎯 Supported Recognition

### Facial Expressions(still working on facial expressions)
- Happy
- Sad
- Angry
- Surprised
- Neutral
- Fearful
- Disgusted
- Contempt
- Confused
- Calm
- Shocked
- Wink
- Depressed

### Hand Gestures
- Thumbs up
- Thumbs down
- Peace sign
- Open palm
- Closed fist
- Pointing
- OK sign
- Wave
- Grab
- Pinch
- Swipe left
- Swipe right
- Super (shaka sign)
- I love you

## 📊 Data Collection & Training

### Collect Training Data
```bash
python collect_training_data.py --data_type [expression|gesture] --output_dir data --num_samples [count]
```

### Train Models
```bash
python train_model.py --model_type [expression|gesture] --data_path [path] --output_path [path]
```

### Authours
- Abhishek(https://github.com/Abhishekmystic-KS/)
- Akshatha(https://github.com/AkshathaaRk/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout

---

## Abhishekmystic-KS/n8n_Ai_Agents

# GalaxyEye Multi-Agent n8n (Simple Setup)

# Preview
![img alt](https://github.com/Abhishekmystic-KS/n8n_Ai_Agents/blob/3feb084f539d9799c4ab3eb2ccbcde36e3920d4f/n8nimg.png)

## Project overview

This project is an n8n workflow that routes user messages to specialized AI agents:

- Chat specialist
- Coding specialist
- Task specialist
- File specialist
- LLM reasoning specialist

We host n8n on a Linux laptop using Docker, then expose localhost with Cloudflare Tunnel so other devices can access it.

Workflow to import:
- `GalaxyEye Multi-Agent System-public.json`

---

## Quick setup (minimal)

### 1) Install Docker (one-time)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

### 2) Start n8n container

```bash
docker volume create n8n_data
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=change_this_password \
  -v n8n_data:/home/node/.n8n \
  --restart unless-stopped \
  n8nio/n8n:latest
```

### 3) Start Cloudflare tunnel to localhost (no install needed)

```bash
docker run --rm -it --network host cloudflare/cloudflared:latest tunnel --url http://localhost:5678
```

Cloudflare will print a public URL like:
- `https://xxxx.trycloudflare.com`

Open that URL on your other laptop/phone to access n8n.

---

## Import this project workflow

1. Open n8n UI
2. Go to **Workflows** → **Import from File**
3. Choose `GalaxyEye Multi-Agent System-public.json`
4. Add your Gemini/API credentials in n8n
5. Save and activate

---

## Daily use commands

```bash
# Start n8n
docker start n8n

# Stop n8n
docker stop n8n

# Logs
docker logs -f n8n
```

To expose again, run Cloudflare command again:

```bash
docker run --rm -it --network host cloudflare/cloudflared:latest tunnel --url http://localhost:5678
```

# Author 
  Abhishek : https://github.com/Abhishekmystic-KS
  Akshatha :  https://github.com/AkshathaaRk

---

## Abhishekmystic-KS/PRODIGY_GA_02


Untitled1.ipynb_

!pip install diffusers transformers accelerate torch

# Create .gitignore to keep your repo clean
gitignore_content = """
# Python artifacts
__pycache__/
*.py[cod]
.ipynb_checkpoints/

# Stable Diffusion / AI specific
*.ckpt
*.pth
*.safetensors
diffusers-cache/
outputs/
*.png
*.jpg

# Large model folders
stable-diffusion-v1-5/
"""

with open(".gitignore", "w") as f:
    f.write(gitignore_content)

print("✅ .gitignore created!")

✅ .gitignore created!

Gemini

# Stable Diffusion Image Generation in Google Colab

This notebook demonstrates how to generate images using the Stable Diffusion v1.5 model directly within Google Colab.

## How it works

1.  **Installation**: Installs necessary libraries (`diffusers`, `transformers`, `accelerate`, `torch`).
2.  **Model Loading**: Loads the `runwayml/stable-diffusion-v1-5` model onto the GPU for efficient image generation.
3.  **Image Generation**: Uses a user-defined text prompt to generate an image and saves it as `ai_lab_result.png`.
4.  **`.gitignore`**: Creates a `.gitignore` file to help keep your repository clean of generated artifacts and large model files.

## Getting Started

### Running in Google Colab

1.  Open this notebook in Google Colab.
2.  Ensure you have a GPU runtime selected (Runtime > Change runtime type > GPU).
3.  Run all cells sequentially (Runtime > Run all).
4.  After execution, the generated image will be saved as `ai_lab_result.png` in your Colab environment. You can view it by clicking the 'Files' icon on the left panel.

### Customization

*   **Prompt**: Modify the `prompt` variable in the image generation cell to describe what you want the AI to create.
*   **Negative Prompt**: Adjust the `n_prompt` variable to specify elements you want to avoid in the generated image.
*   **Guidance Scale**: Experiment with `guidance_scale` for more or less adherence to your prompt.

## Example Output

Below is the image generated by the notebook with the default prompt:

![Generated Image](ai_lab_result.png)

Colab paid products - Cancel contracts here


---

## Abhishekmystic-KS/PRODIGY_GA_01

%%writefile README.md
# Text Generation with Fine-Tuned GPT-2

## 📌 Project Overview
This project focuses on the **fine-tuning of the GPT-2 transformer model** to perform stylistic text generation. Using a custom dataset of 40,000+ lines of Shakespearean text, the model was adapted from a general-purpose language model into a specialized generator capable of mimicking 16th-century linguistic patterns.

## 🛠️ Technical Stack
* **Base Model:** GPT-2 (117M parameters)
* **Frameworks:** Hugging Face `transformers`, `datasets`
* **Hardware:** NVIDIA T4 GPU (via Google Colab)
* **Language:** Python 3.12
* **Deployment:** Gradio (Web Interface)

## 🚀 Key Features
* **Custom Fine-Tuning:** Leveraged the `Trainer` API to update model weights based on specialized stylistic corpora.
* **Optimization:** Achieved a **17.9% reduction in training loss** (from 4.46 to 3.66).
* **Interactive UI:** Integrated a Gradio frontend for real-time text generation.
* **Contextual Awareness:** The model maintains character-based dialogue structures (e.g., `ROMEO:`).

## 📊 Performance Metrics
* **Initial Loss:** 4.46
* **Final Loss:** 3.66
* **Inference Speed:** ~3.73 iterations per second on T4 GPU

## 💻 How to Run
1. **Install Dependencies:**
   ```bash
   pip install transformers datasets torch gradio
   ```
2. **Run Inference:**
   Execute the notebook `PRODIGY_AI_01.ipynb` to launch the Gradio interface.

## 🎓 Internship Credits
This project was completed as part of the **AI Engineering Internship at Prodigy Infotech (Task-01)**.


---

## Abhishekmystic-KS/Abhishekmystic-KS

[![MasterHead](https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQCsg19T-zPtYhFzt_d3_KuUxhfa5IEjKmz-A&s)](https://abhishekmystic-KS.io)
<h1 align="center">Hi 👋, I'm Abhishek KS</h1>
<h3 align="center">A passionate Generative AI Developer & LLM Researcher </h3>
<img align="right" alt="Coding" width="400" src="https://i.pinimg.com/originals/13/dc/1f/13dc1f9bd046a5c7825397eaebe1f852.gif">

<p align="left"> <img src="https://komarev.com/ghpvc/?username=abhishekmystic-ks&label=Profile%20views&color=0e75b6&style=flat" alt="abhishekmystic-ks" /> </p>

- 🔭 I’m currently working on **Fine-tuning LLMs and RAG (Retrieval-Augmented Generation) Pipelines**

- 🌱 I’m currently learning **LangChain, Vector DB and Prompt Engineering**

- 💬 Ask me about **Generative AI, Large Language Models, and AI Security**

- ⚡ Fun fact **I love exploring the intersection of deep learning and cybersecurity to build robust AI systems.**

<h3 align="left">Connect with me:</h3>
<p align="left">
<a href="https://linkedin.com/in/abhishekks5" target="blank"><img align="center" src="https://raw.githubusercontent.com/rahuldkjain/github-profile-readme-generator/master/src/images/icons/Social/linked-in-alt.svg" alt="abhishekks5" height="30" width="40" /></a>
</p>

<h3 align="left">Languages and Tools:</h3>
<p align="left"> <a href="https://aws.amazon.com" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/amazonwebservices/amazonwebservices-original-wordmark.svg" alt="aws" width="40" height="40"/> </a> <a href="https://www.gnu.org/software/bash/" target="_blank" rel="noreferrer"> <img src="https://www.vectorlogo.zone/logos/gnu_bash/gnu_bash-icon.svg" alt="bash" width="40" height="40"/> </a> <a href="https://www.w3schools.com/cpp/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/cplusplus/cplusplus-original.svg" alt="cplusplus" width="40" height="40"/> </a> <a href="https://www.docker.com/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/docker/docker-original-wordmark.svg" alt="docker" width="40" height="40"/> </a> <a href="https://flask.palletsprojects.com/" target="_blank" rel="noreferrer"> <img src="https://www.vectorlogo.zone/logos/pocoo_flask/pocoo_flask-icon.svg" alt="flask" width="40" height="40"/> </a> <a href="https://www.java.com" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/java/java-original.svg" alt="java" width="40" height="40"/> </a> <a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/javascript/javascript-original.svg" alt="javascript" width="40" height="40"/> </a> <br> <a href="https://www.linux.org/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/lin

---

## Abhishekmystic-KS/keylogger-telegram

# Keylogger-Telegram

A Python-based keystroke logger that monitors keyboard input and sends captured keystrokes to Telegram via bot API. Captures keyboard input in real-time and sends notifications to your Telegram bot.

## Features

- **Real-time Keystroke Monitoring**: Captures all keyboard input using the pynput library
- **Telegram Integration**: Sends captured keystrokes directly to Telegram via bot API
- **Global Logging Control**: Enable/disable logging on demand
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Error Handling**: Robust exception handling with fallback mechanisms
- **Threading Support**: Non-blocking keystroke monitoring
- **Rate Limiting**: Built-in delays to prevent API rate limiting

## Prerequisites

- Python 3.6 or higher
- pip (Python package manager)
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather) on Telegram)
- Your Telegram Chat ID

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/keylogger-telegram.git
   cd keylogger-telegram
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create a Telegram Bot:**
   - Open Telegram and search for [@BotFather](https://t.me/botfather)
   - Send `/newbot` command and follow the prompts
   - Save your bot token

2. **Find your Chat ID:**
   - Message your bot and visit: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
   - Look for the `chat` → `id` field in the JSON response

3. **Set up environment variables:**
   
   Create a `.env` file in the project root:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

4. **Update the code** to use environment variables:
   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()
   TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
   TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
   ```

## Usage

1. **Run the program:**
   ```bash
   python key.py
   ```

2. **Control logging:**
   - The program starts with logging disabled by default
   - Modify the `is_logging` variable to enable/disable keystroke capture

3. **Check Telegram:**
   - Messages will appear in your Telegram chat as keys are pressed

## Security & Legal Considerations

⚠️ **IMPORTANT:**

- **Ethical Use Only**: Only use this tool on systems you own or have explicit permission to monitor
- **Sensitive Data**: Never commit bot tokens or chat IDs to version control
- **Legal Compliance**: Keystroke logging may be illegal in your jurisdiction. Ensure compliance with local laws
- **Privacy**: Use only for personal security monitoring, research, or authorized testing
- **Disclosure**: Inform users if monitoring their systems

## Environment Security

- Always use a `.env` file for sensitive credentials
- Add `.env` to your `.gitignore` (already configured)

## Dependencies

- `pynput` - Keyboard input monitoring
- `requests` - HTTP requests for Tel

---

## Abhishekmystic-KS/Medical-Image-Retrieval

# 🩺 Medical X-Ray Search Engine

AI-powered search engine for medical X-ray images using deep learning embeddings and similarity search.

## Features
- 🖼️ **Image-based search**: Upload an X-ray to find similar cases
- 📝 **Text-based search**: Search using medical terms (e.g., "chest pneumonia", "spine scoliosis")
- 🎯 **Auto-category detection**: Automatically identifies anatomy type (chest, spine, skull, fracture, dental)
- 🔍 **Smart filtering**: Returns only relevant anatomical matches
- 📊 **Similarity scores**: Shows relevance percentage for each result

## Dataset
- **Chest X-rays**: 500+ images (Normal/Abnormal)
- **Spine X-rays**: 150+ images (Normal/Scoliosis/Spondylolisthesis)
- **Skull X-rays**: 50+ images
- **Fracture X-rays**: 50+ images
- **Dental X-rays**: 22+ images (Panoramic/Periapical)
- **Total**: 772 images with pre-computed embeddings

## Installation

### Prerequisites
- Python 3.8+
- 4GB RAM
- 2GB disk space

## Demo video 
https://drive.google.com/drive/folders/1DwdGtDxvrh4Rqag2SLmeW7plessScsuR

### Setup
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/xray-similarity-search.git
cd xray-similarity-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate embeddings (first time only)
python src/embeddings.py
```

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run the app
streamlit run app.py
```

Open browser to: **http://localhost:8501**

## How It Works

1. **Image-Based Search**:
   - Upload an X-ray image
   - ResNet50 extracts 2048-dimensional embeddings
   - System auto-detects anatomy category
   - Finds top 5 similar images using cosine similarity
   - Displays results with similarity scores

2. **Text-Based Search**:
   - Enter medical keywords (e.g., "spine", "chest pneumonia")
   - TF-IDF vectorization matches against image metadata
   - Returns relevant results with relevance scores

## Project Structure
```
xray-similarity-search/
├── app.py                  # Streamlit web interface
├── src/
│   ├── __init__.py
│   ├── embeddings.py       # Generate image embeddings
│   └── search_engine.py    # Search logic
├── dataset/
│   ├── images/             # X-ray images by category
│   │   ├── chest/
│   │   ├── spine/
│   │   ├── skull/
│   │   ├── fracture/
│   │   └── dental/
│   └── metadata.csv        # Image metadata
├── models/
│   └── embeddings.pkl      # Pre-computed embeddings (generated)
├── requirements.txt
├── README.md
└── .gitignore
```

## Technical Details
- **Model**: ResNet50 (pre-trained ImageNet)
- **Embeddings**: 2048-dimensional vectors
- **Similarity Metric**: Cosine similarity
- **Text Search**: TF-IDF + cosine similarity
- **Framework**: Streamlit (web UI)
- **Backend**: PyTorch, scikit-learn

## Dataset Sources
- [Kaggle Chest X-Ray Pneumonia](https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia

---

## Abhishekmystic-KS/ai-image-restoration

# AI Image Restoration with ESRGAN

This repository contains a Google Colab notebook demonstrating AI-powered image restoration using the ESRGAN (Enhanced Super-Resolution Generative Adversarial Network) model from TensorFlow Hub. The provided code focuses on restoring low-resolution or degraded images, with optimizations for memory usage.

## Table of Contents

- Project Overview
- Features
- Setup
- Usage
- Model Details
- Example Output

## Project Overview

This project leverages a pre-trained ESRGAN model to enhance the quality of images. It's particularly useful for upscaling and improving the visual fidelity of older or lower-quality images. The notebook is designed to be run in Google Colab, making it accessible without requiring local GPU setup.

## Features

- **ESRGAN Model Integration**: Utilizes the captain-pool/esrgan-tf2/1 model from TensorFlow Hub.
- **RAM Optimization**: Automatically resizes large input images (e.g., above 600px) to prevent out-of-memory errors, especially when running on Colab or systems with limited RAM/GPU.
- **Color Correction**: Correctly handles pixel value scaling (0-255 range) to avoid common color issues like purple/magenta tints in the output.
- **Simple Python Interface**: A straightforward restore_image function to process images.

## Setup

To run this project, you will need a Google Colab environment.

1. **Open the Notebook**: Upload or open the .ipynb file in Google Colab.

2. **Install Dependencies**: Run the first code cell to install the necessary Python libraries:

```bash
pip install tensorflow tensorflow-hub numpy Pillow
```

3. **Import Libraries**: Ensure all required libraries are imported:

```python
import tensorflow_hub as hub
import tensorflow as tf
import numpy as np
from PIL import Image
import os
```

## Usage

1. **Upload Your Image**: Upload the image you wish to restore to your Colab environment. For example, if your image is named my_image.jpg, upload it to the /content/ directory.

2. **Load the Model and Define Function**: The notebook contains a cell that loads the ESRGAN model and defines the restore_image function. This function handles loading, resizing, processing, and saving the image.

```python
# 1. Load the model once
print("Loading ESRGAN model...")
model = hub.load('https://tfhub.dev/captain-pool/esrgan-tf2/1')

def restore_image(image_path, output_path):
    # Load Image
    img = Image.open(image_path).convert('RGB')

    # --- RAM OPTIMIZATION: Resize if the image is too big ---
    # ESRGAN 4x will crash if the input is > 1000px.
    # We downsize the input so the output stays under control.
    max_size = 600
    if max(img.size) > max_size:
        print(f"Resizing input from {img.size} to save RAM...")
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    # Convert to Tensor (Removed / 255.0 normalization as model expects 0-255 range)
    img_tensor = tf.expand_dims(np.array(img).astype(np.float32), axis=0)

    print("Processing... (This uses hig

---

## Abhishekmystic-KS/UnifiedChain-ID

## UnifiedChain ID Wallet with Blockchain Integration

A blockchain-based wallet system that allows users to create and manage digital identities across multiple blockchain networks with enhanced security and privacy. This platform gives you a foreground in blockchain of all the other wallets where we authenticate the other wallets on behalf of them as well it gives you a holdings of multiple wallet's Seed-phrase and private key.It gives you one seed phrase and UID where by remembering your UID and password you access all wallets very safely and securedly. It is better to remember one UID tahn storing and losing of multiple wallets.    


## Features

- Create wallets with unique seed phrases and UIDs stored securely on the blockchain
- Import existing wallets by verifying seed phrases and UIDs
- Face authentication for enhanced security
- Added external Security while revealing the seed phrase as only owner of the account whould know hoew to use it.
- Cross-chain identity management
- Military-grade encryption for wallet data
- Plays as a foreground for all the other wallets and gives authentication for them on behalf of the user.

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Framer Motion
- **Blockchain**: Web3.js, Ethers.js, Ganache (local blockchain)
- **Authentication**: BIP39 for seed phrases, Face authentication
- **3D Visualization**: Three.js with React Three Fiber
- **Build Tools**: Vite, ESLint

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/unifiedchain-id-wallet.git
   cd unifiedchain-id-wallet
   ```

2. Install dependencies
   ```bash
   npm install
   ```

## Running the Application

### Start the Local Blockchain

```bash
npm run ganache
```

This will:
- Start a Ganache instance on port 7545
- Deploy the WalletStorage smart contract
- Display available accounts and their balances

### Start the Development Server

```bash
npm run dev
```

The application will be available at http://localhost:5173

## How It Works
https://youtu.be/quuwZu3rK_w
![Image](https://github.com/user-attachments/assets/ec5bec9c-2661-4538-a137-8ebd8dce8843)

### Creating a Wallet

1. Navigate to the Dashboard
2. Click "Create New Wallet"
3. Enter your name and other required information
4. A unique seed phrase and UID will be generated
5. The wallet data is registered on the blockchain
6. Save your seed phrase securely

### Importing a Wallet

1. Navigate to the Dashboard
2. Click "Import Existing Wallet"
3. Enter your seed phrase and UID
4. The wallet data is verified against the blockchain
5. If verification is successful, your wallet is imported

## Security Features

- Seed phrases are hashed before being stored on the blockchain
- Optional face authentication for accessing wallet details
- Password protection for sensitive operations
- Code protected for Revealing Seed-phrase.

## Contact

For questions or support, ple

---

## Abhishekmystic-KS/Packet_sniffer

# Network Packet Sniffer & Injector

## Overview
This Python script captures network packets, logs them, and detects suspicious IPs. It also injects ARP spoofing packets and provides real-time network statistics.

## Features
- Captures IP packets and logs details.
- Monitors traffic for suspicious IPs.
- Injects ARP spoofing packets.
- Displays real-time network statistics.

## Requirements
- Python 3.x
- Required libraries:
  - `scapy`
  - `threading`
  - `collections`
  - `datetime`
  - `time`
- Enter the Target ip in the code 
Install dependencies using:
```bash
pip install scapy
```

## Usage
Run the script with:
```bash
python script.py
```

## Configuration
- **SUSPICIOUS_IPS**: Modify this list to add IPs to monitor.
- **PACKET_FILE**: Change the filename to store captured packets.

## Functions
- `process_packet(packet)`: Captures and logs packet details.
- `inject_packets()`: Sends ARP spoofing packets every 20 seconds.
- `display_statistics()`: Displays protocol statistics every 5 seconds.
- `start_sniffing()`: Begins sniffing network packets.

## Notes
- Run with administrative/root privileges for full functionality.
- Modify the ARP injection target as needed.

## Disclaimer
Use this script responsibly and only on networks you have permission to monitor and modify.


---

## Abhishekmystic-KS/Network_Scanner

# Network Scanner

## Overview
This script is a comprehensive network scanning tool that performs various reconnaissance tasks, including:

- **Ping Sweep**: Identifies live hosts in a given network range.
- **Port Scanning**: Detects open ports on live hosts.
- **MAC Address Retrieval**: Attempts to retrieve MAC addresses of discovered devices.
- **Service Detection**: Identifies services running on open ports using basic banner grabbing.
- **OS Fingerprinting**: Uses Nmap to estimate the operating system running on a host.
- **Network Mapping**: Provides a summary of discovered hosts and their MAC addresses.

## Features
- Cross-platform compatibility (Windows, Linux, MacOS)
- Multi-threaded for efficiency
- Logs results in `network_scanner.log`
- Simple command-line interface

## Prerequisites
Ensure you have the following dependencies installed:

- Python 3.x
- `nmap` (for OS fingerprinting)

## Installation
Clone the repository and navigate into the project directory:

```sh
git clone https://github.com/yourusername/network-scanner.git
cd network-scanner
```

Install required dependencies:

```sh
pip install socket threading subproces ipaddress platform  # If any external libraries are needed
```

## Usage
Run the script using:

```sh
python network_scanner.py
```

It will prompt you to enter:
- Network range (e.g., `192.168.1.0/24`)
- Start and end ports for scanning

## Ethical Considerations & Legal Awareness
This tool is intended for **authorized security assessments** and educational purposes only. Unauthorized scanning of networks without explicit permission is illegal in many jurisdictions and may lead to legal consequences. Always ensure you have **explicit permission** before scanning any network.

### **Responsible Use Guidelines:**
- **Only scan networks you own or have permission to scan.**
- **Obtain written consent** before scanning third-party networks.
- **Do not use this tool for malicious purposes.**
- Be aware of laws like the **Computer Fraud and Abuse Act (CFAA)** and **GDPR** regulations regarding network reconnaissance.

## Logging
The script logs all activities to `network_scanner.log`, including discovered hosts, open ports, and detected services.


## License
This project is licensed under the MIT License. See `LICENSE` for details.

## Contribution
Contributions are welcome! Feel free to submit a pull request or open an issue.


---
*Disclaimer: This tool is for educational and authorized security testing purposes only.*


---

## Abhishekmystic-KS/amazon-clone

# amazon-clone
This project is a simplified Amazon clone featuring a responsive front page built with HTML and CSS.
It include a clean design and navigation bar for easy access to product categories.
Explore the code to see how I implemented the layout and styling
Technologies Used :HTML,CSS.
Responsive Layout for optimal viewing on various devices.
Clean and modern deign that mimics the look and feel of e-commerce platform.
Navigation bar for easy access to different product categories.
Explore the code to see how i implemented the design and Structure!


---

## Abhishekmystic-KS/SysAura

# SysAura - Real-Time System And Server Monitoring Application

SysAura is a real-time system and server(still working on server) monitoring application that provides detailed insights into CPU, memory, disk, and network usage. It features a modern React frontend and a robust Node.js backend with WebSocket support for real-time updates.

##How it Works
https://drive.google.com/drive/folders/1QqdzelWDzui8TduurK6YV7NphFt5Wn7U

## Features

- Real-time monitoring of system metrics (CPU, memory, disk, network)
- User authentication and authorization with role-based access (admin and user)
- System management and monitoring
- Server managementand monitoring
- Alerts and notifications for system events
- Responsive UI with dark mode support
- WebSocket support for live data updates

## Tech Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Node.js, Express, WebSocket, SQLite
- Authentication: JWT
- Real-time communication: WebSocket

## Project Structure

- `/src` - React frontend source code
- `/backend` - Node.js backend server
- Root contains configuration files for frontend and backend

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sysauraft.git
   cd sysauraft
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Install backend dependencies:
   ```bash
   cd backend
   npm install
   ```

4. Create a `.env` file in the `backend` directory with the following variables:
   ```
   PORT=5000
   JWT_SECRET=your_jwt_secret
   NODE_ENV=development
   ```

## Running the Application

1. Start the backend server:
   ```bash
   cd backend
   npm run dev
   ```

2. Start the frontend development server:
   ```bash
   # In the project root
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173`

## Backend API Overview

The backend provides RESTful API endpoints for authentication, system metrics, system management, alerts, and user management.

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Metrics
- `GET /api/metrics/current` - Get current system metrics
- `GET /api/metrics/history/:systemId` - Get metrics history for a system
- `POST /api/metrics/:systemId` - Save system metrics

### Systems
- `GET /api/systems` - Get all systems (admin only)
- `GET /api/systems/user` - Get systems for current user
- `GET /api/systems/:id` - Get a single system
- `POST /api/systems` - Create a new system
- `PUT /api/systems/:id` - Update a system
- `DELETE /api/systems/:id` - Delete a system

### Alerts
- `GET /api/alerts` - Get all alerts
- `GET /api/alerts/system/:systemId` - Get alerts for a specific system
- `POST /api/alerts` - Create a new alert
- `PATCH /api/alerts/:id` - Update alert status

### Users
- `GET /api/users` - Get all users (admin only)
- `GET /api/users/profile` - 

---

## Abhishekmystic-KS/Password_Strength_Checker


# Password Strength Meter

This project is a **Password Strength Meter** built using **HTML, CSS, and JavaScript**. It allows users to enter a password and visually see its strength categorized as Weak, Medium, or Strong.

## Features
- Real-time password strength checking
- Strength levels: Weak, Medium, Strong
- Show/Hide password toggle
- Background color changes based on strength
- Suggests strong passwords

## Technologies Used
- **HTML** for structure
- **CSS** for styling and UI enhancements
- **JavaScript** for dynamic behavior

## File Structure
```
|-- index.html      # Main HTML file
|-- style.css       # Stylesheet for design and layout
|-- script.js       # JavaScript for password strength logic
```

## Usage
1. Open `index.html` in a web browser.
2. Type a password in the input field.
3. See the strength indicator change color:
   - **Red** for Weak
   - **Orange** for Medium
   - **Green** for Strong
4. Click the **eye icon** to show/hide the password.
5. If the input is empty, suggested strong passwords will appear.

## Installation
No installation is required. Simply open `index.html` in V/S Code.

## How It Works
- Uses **regular expressions** to check for:
  - Lowercase letters
  - Uppercase letters
  - Numbers
  - Special characters
- The more complexity, the stronger the password
- Strength levels are visually indicated

 
 ## Password Strength Checker
  ![Image](https://github.com/user-attachments/assets/724750fa-b55c-4b28-800a-ddeebcb1b15a) 
