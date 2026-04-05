import { useState } from "react"
import ChatContainer from "./components/ChatContainer"
import ChatInput from "./components/ChatInput"
import Header from "./components/Header"
import "./App.css"

function App() {
  const [messages, setMessages] = useState([])
  //added mute state
  const [isMuted, setIsMuted] = useState(false)

  const clearChat = () => {
    setMessages([])
  }

  
  const toggleMute = () => {
    setIsMuted(!isMuted)
    //if i hit mute while the bot is currently talking, shut it up instantly!
    if (!isMuted) {
      window.speechSynthesis.cancel()
    }
  }

  const sendMessage = async (text) => {
    const userMsg = { role: "user", content: text }
    setMessages((prev) => [...prev, userMsg])

    try {
      const res = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      })

      const data = await res.json()
      const botMsg = { role: "assistant", content: data.answer }
      setMessages((prev) => [...prev, botMsg])

      // only speak if the app is NOT muted
      if (!isMuted) {
        const cleanText = data.answer.replace(/[*#_]/g, "")
        const utterance = new SpeechSynthesisUtterance(cleanText)
        utterance.rate = 0.85; 
        utterance.pitch = 0.8;
        window.speechSynthesis.speak(utterance)
      }

    } catch (error) {
      console.error("Error communicating with backend:", error)
    }
  }

  return (
    <div className="app">
      <Header clearChat={clearChat} isMuted={isMuted} toggleMute={toggleMute} />
      <ChatContainer messages={messages} />
      <ChatInput sendMessage={sendMessage} />
    </div>
  )
}

export default App