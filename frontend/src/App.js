import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';


const STARTER_OPTIONS = [
  "How do I reset my password?",
  "Is multi-factor authentication mandatory for all employees?",
  "Can I install software without IT approval?",
  "Can I use my personal laptop for work?"
];



function App() {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    {
      user: null,
      bot: "Hello 👋 I’m the Company IT Helpdesk Bot. How can I help you today?",
      followups: STARTER_OPTIONS,
      confidence: null,
      explanations: []
    }
  ]);

  const [loading, setLoading] = useState(false);
  const typingTimerRef = React.useRef(null);


  // Auto-scroll to the bottom of the chat when a new message is added
  useEffect(() => {
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
  }, [chatHistory]);

  const typeText = (fullText, callback) => {
    let index = 0;
    const words = fullText.split(" ");

    const interval = setInterval(() => {
      index++;
      callback(words.slice(0, index).join(" "));
      if (index >= words.length) clearInterval(interval);
    }, 150); // speed control
  };


  // Handle form submission and call the backend
  const sendMessage = async (text) => {
    if (!text.trim()) return;

    typingTimerRef.current = setTimeout(() => {
      setLoading(true);
    }, 400);


    try {
      const response = await axios.post("http://localhost:8000/chat", {
        message: text,
      });
      const emptyBotMessage = {
        user: text,
        bot: "",
        followups: [],
        confidence: response.data.confidence,
        explanations: response.data.explanations || []
      };

      setChatHistory((prev) => [
        ...prev.map((item) => ({
          ...item,
          followups: []
        })),
        emptyBotMessage
      ]);

      typeText(response.data.response, (partialText) => {
        setChatHistory((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            bot: partialText,
            followups: response.data.followups || []
          };
          return updated;
        });
      });
    } catch (error) {
      setChatHistory((prev) => [
        ...prev,
        {
          user: text,
          bot: "Error processing your request.",
          followups: []
        }
      ]);
    } finally {
      clearTimeout(typingTimerRef.current);
      setLoading(false);
      setMessage("");
    }
  };


  const handleFollowupClick = (followup) => {
    sendMessage(followup);
  };

  const handleSubmit = (e) => {
      e.preventDefault();
      sendMessage(message);
    };


  return (
    <div className="App">
      <div className="chat-container">
        <h1 className="chat-header">Company HelpBot</h1>
        <div className="chat-box" id="chat-box">
          {chatHistory.map((chat, index) => (
            <div key={index} className="message-container">
              {chat.user && (
                <div className="message user-message">
                  <div className="message-avatar">
                    <img src="/user-avatar.jpg" alt="User Avatar" />
                  </div>
                  <div className="message-text">
                    <strong>You:</strong> {chat.user}
                  </div>
                </div>
              )}

              <div className="message bot-message">
              <div className="message-avatar">
                <img src="/bot-avatar.jpg" alt="Bot Avatar" />
              </div>

              <div className="bot-bubble">
                
                {/* Main answer */}
                <div className="bot-answer">
                  <strong>Bot:</strong> {chat.bot}
                </div>

                {/* Meta section */}
                {(chat.confidence || (chat.explanations && chat.explanations.length > 0)) && (
                  <div className="bot-meta">

                    {chat.confidence && (
                      <div className={`confidence-badge ${chat.confidence.toLowerCase()}`}>
                        Answer confidence: {chat.confidence}
                      </div>
                    )}

                    {chat.explanations && chat.explanations.length > 0 && (
                      <details className="explain-toggle">
                        <summary>Why am I seeing this?</summary>
                        <ul>
                          {chat.explanations.map((e, i) => (
                            <li key={i}>{e}</li>
                          ))}
                        </ul>
                      </details>
                    )}

                  </div>
                )}

              </div>
            </div>

              {chat.followups && chat.followups.length > 0 && (
                < div className="followup-container">
                  {chat.followups.map((f, i) => (
                    <button
                      key={i}
                      className="followup-chip"
                      onClick={() => handleFollowupClick(f)}
                      disabled={loading}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              )}
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
