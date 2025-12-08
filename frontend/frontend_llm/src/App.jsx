import { useState } from 'react';
import LogoChatbot from './assets/logochatbot.png';
import TickButton from './assets/tickbutton.png';
import './App.css';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', text: input }]);

    try {
      // Call backend
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();

      // Add bot response
      setMessages((prev) => [...prev, { role: 'bot', text: data.response }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: 'Error: could not reach backend.' },
      ]);
    }

    setInput('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') sendMessage();
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      {/* Logo */}
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        <img src={LogoChatbot} alt="ChatBot Logo" style={{ height: '80px' }} />
      </div>

       {/* Assistant header */}
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        <div style={{ fontWeight: 'bold', fontSize: '16px' }}>
          Assistant - prescription d'imagerie
        </div>
        <div style={{ color: '#888', fontSize: '14px', marginTop: '4px' }}>
          Saisissez un cas clinique pour obtenir l'examen complémentaire adapté.
        </div>
      </div>


      {/* Chat messages */}
      <div>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
              margin: '5px 0',
            }}
          >
            {m.role === 'user' ? (
              <div
                style={{
                  background: '#d1e7ff',
                  padding: '8px 12px',
                  borderRadius: '15px',
                  maxWidth: '70%',
                  wordWrap: 'break-word',
                }}
              >
                {m.text}
              </div>
            ) : (
              <div
                style={{
                  maxWidth: '70%',
                  wordWrap: 'break-word',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {m.text}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input field + tick */}
      <div style={{ display: 'flex', alignItems: 'center', marginTop: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type a message..."
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: '12px',
            border: '1px solid #ccc',
            outline: 'none',
          }}
        />
        <img
          src={TickButton}
          alt="Send"
          onClick={sendMessage}
          style={{
            width: '28px',
            height: '28px',
            marginLeft: '8px',
            cursor: 'pointer',
            transition: 'filter 0.2s',
            filter: 'brightness(1)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.filter = 'brightness(0.7)')}
          onMouseLeave={(e) => (e.currentTarget.style.filter = 'brightness(1)')}
        />
      </div>
    </div>
  );
}
