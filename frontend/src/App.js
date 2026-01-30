import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  // Auto-scroll to the bottom of the chat when a new message is added
  useEffect(() => {
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
  }, [chatHistory]);

  // Handle form submission and call the backend
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/chat', {
        message,
      });

      setChatHistory([...chatHistory, { user: message, bot: response.data.response }]);
      setMessage('');
    } catch (error) {
      console.error('Error:', error);
      setChatHistory([...chatHistory, { user: message, bot: 'Error processing your request' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="chat-container">
        <h1 className="chat-header">Company HelpBot</h1>
        <div className="chat-box" id="chat-box">
          {chatHistory.map((chat, index) => (
            <div key={index} className="message-container">
              <div className="message user-message">
                <div className="message-avatar">
                  <img src="/user-avatar.jpg" alt="User Avatar" />
                </div>
                <div className="message-text">
                  <strong>You:</strong> {chat.user}
                </div>
              </div>
              <div className="message bot-message">
                <div className="message-avatar">
                  <img src="/bot-avatar.jpg" alt="Bot Avatar" />
                </div>
                <div className="message-text">
                  <strong>Bot:</strong> {chat.bot}
                </div>
              </div>
            </div>
          ))}
          {loading && <div className="loading-spinner"></div>}
        </div>

        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask something..."
            className="message-input"
            disabled={loading}
          />
          <button type="submit" className="send-button" disabled={loading}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
