####ChatStudio####

The locally deployed open-source LLM model operates purely locally without requiring internet connection, offering low cost. It is capable of knowledge inquiry, code writing, and various custom settings. Additionally, users can freely switch between multiple AI large models, ensuring ultra-secure privacy during local operation.

✨ Features
💬 Full chat history – persistent conversations saved locally

🧠 Thinking process display – view the model’s internal reasoning (when supported)

🌗 Dark / Light theme – toggle with Ctrl+T

⚡ Streaming responses – real-time token-by-token output

🔁 Regenerate answers – re‑run the last assistant response

📤 Export conversations – save as Markdown or plain text

🔍 Search history – filter conversations by title

⚙️ Customizable settings – system prompt, temperature, model selection

⌨️ Keyboard shortcuts – Ctrl+N for new chat, Enter to send

🚀 Installation
Prerequisites
Python 3.8 or higher

Ollama installed and running with at least one model pulled

Steps
Clone the repository

bash
git clone https://github.com/HAhahe12/Chat-Studio.git
cd chatstudio
Install dependencies

bash
pip install requests
No other external libraries are required – the GUI is built with Tkinter (included with Python).

Configure the API URL

Open chatstudio.py and replace the placeholders in the Constants section:

python
OLLAMA_API = "http://your-ollama-server:11434/api/chat"
OLLAMA_TAGS = "http://your-ollama-server:11434/api/tags"
If Ollama is running locally with default settings, use:
http://localhost:11434/api/chat

Run the application

bash
python chatstudio.py
🎮 Usage
Main Window
Left sidebar – conversation history, search, connection status, settings toggle

Chat area – message bubbles, streaming assistant responses

Bottom input – type your message, press Enter to send, Shift+Enter for new line

Settings
Click the ⚙ Settings button in the sidebar to:

Edit the system prompt (default: “You are a professional AI assistant…”)

Adjust Temperature (0.0 – 2.0) – higher = more creative

Change the active Ollama model (list is hardcoded; edit MODELS in the code if needed)

Conversation Management
New chat – Ctrl+N or click the green button

Clear current chat – toolbar button

Delete a conversation – hover over it in the history and click the ✕ button

Export – toolbar button saves the current conversation as Markdown (including thinking sections)

Theme Switching
Press Ctrl+T or click the theme button in the sidebar to switch between dark and light mode.

⚙️ Configuration Files
All data is stored in the same directory as the script:

File	Purpose
chat_conversations.json	All chat history (system, user, assistant messages)
chat_settings.json	UI theme, system prompt, temperature, last selected model
You can manually edit these files while the application is closed.

🧠 Thinking Process Support
Some Ollama models (like qwen3:30b-a3b-thinking-*) output a thinking field in the streaming response. ChatStudio automatically:

Displays the thinking content in a collapsible blue box

Separates it from the final answer

Exports it as an HTML <details> block

If your model does not support this field, the thinking area simply stays hidden.

🛠 Customization
Adding More Models
Edit the MODELS list at the top of the script:

python
MODELS = [
    "llama3",
    "mistral",
    "your-custom-model:latest",
]
Changing the Default API URL
Replace the constants at the top of the file. For remote servers, ensure the address is reachable from your machine.

🤝 Contributing
Pull requests are welcome! Please open an issue first to discuss major changes.

📄 License
This project is licensed under the MIT License – see the LICENSE file for details.

❓ Troubleshooting
Problem	Solution
“Cannot connect to Ollama service”	Make sure Ollama is running (ollama serve) and the API URL is correct. Test with curl http://localhost:11434/api/tags.
Model not showing in dropdown	Edit the MODELS list to include your pulled model.
Chinese characters appear in exported Markdown	The export uses UTF‑8 encoding – ensure your text editor supports it.
Window doesn’t scroll smoothly	Use the mouse wheel inside the chat area; the canvas widget handles scrolling.
🙏 Acknowledgements
Built with Ollama – run LLMs locally

Icons and emojis for visual clarity

Tkinter for the cross‑platform GUI

Enjoy chatting with your local LLMs! 🚀

