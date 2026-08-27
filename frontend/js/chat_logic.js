document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const loadingIndicator = document.getElementById('loading-indicator');
    const sendButton = document.getElementById('send-button');

    const API_URL = 'http://127.0.0.1:8000/api/chat';

    // In-memory conversation history state
    const conversationHistory = [];

    // Scroll chat window to bottom
    const scrollToBottom = () => {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    // Append User Message Bubble (Right-aligned)
    const appendUserMessage = (messageText) => {
        const userDiv = document.createElement('div');
        userDiv.className = 'flex items-start justify-end space-x-3 user-bubble';
        userDiv.innerHTML = `
            <div class="bg-blue-600 text-white p-4 rounded-2xl rounded-tr-none max-w-lg shadow-sm">
                ${escapeHtml(messageText)}
            </div>
            <div class="w-8 h-8 bg-gray-700 text-gray-200 rounded-full flex items-center justify-center font-bold text-sm shadow">You</div>
        `;
        chatHistory.appendChild(userDiv);
        scrollToBottom();
    };

    // Append AI Message Bubble (Left-aligned)
    const appendAIMessage = (messageText) => {
        const aiDiv = document.createElement('div');
        aiDiv.className = 'flex items-start space-x-3 ai-bubble';
        aiDiv.innerHTML = `
            <div class="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm shadow">AI</div>
            <div class="bg-gray-800 border border-gray-700 text-gray-200 p-4 rounded-2xl rounded-tl-none max-w-lg shadow-sm whitespace-pre-wrap">
                ${escapeHtml(messageText)}
            </div>
        `;
        chatHistory.appendChild(aiDiv);
        scrollToBottom();
    };

    // Utility: HTML Sanitizer to prevent XSS
    const escapeHtml = (str) => {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    };

    // Form submit handler
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const userText = messageInput.value.trim();
        if (!userText) return;

        // Render user message and clear input
        appendUserMessage(userText);
        messageInput.value = '';

        // Disable input controls & show loading state
        messageInput.disabled = true;
        sendButton.disabled = true;
        loadingIndicator.classList.remove('hidden');
        scrollToBottom();

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: userText,
                    history: conversationHistory 
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const botReply = data.response || 'No response content.';
            
            appendAIMessage(botReply);

            // Record turn in history for conversational context
            conversationHistory.push({ role: 'user', content: userText });
            conversationHistory.push({ role: 'assistant', content: botReply });

        } catch (error) {
            console.error('Chat API Error:', error);
            appendAIMessage(`⚠️ Connection Error: Unable to communicate with backend server at ${API_URL}. Make sure your FastAPI backend is running.`);
        } finally {
            // Re-enable controls & hide loading state
            loadingIndicator.classList.add('hidden');
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
            scrollToBottom();
        }
    });
});
