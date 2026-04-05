import { useState, useRef, useEffect } from "react"

function ChatInput({ sendMessage }) {
  const [text, setText] = useState("")
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)
  
  //we used a ref to track the latest text so the browser API doesn't use outdated state
  const textRef = useRef(text)
  useEffect(() => {
    textRef.current = text
  }, [text])

  const handleSend = () => {
    if (!text.trim()) return
    sendMessage(text)
    setText("")
  }

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop()
      setIsListening(false)
      return
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert("Your browser does not support voice input.")
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false // tells it to stop automatically when you pause
    recognition.interimResults = false
    recognition.lang = 'en-US' 

    recognition.onstart = () => setIsListening(true)

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      
      //for combinin anything already typed with the newly spoken words
      const finalMessage = (textRef.current + " " + transcript).trim()

      //auto send
      sendMessage(finalMessage)
      
      //clear the input box
      setText("")
    }

    recognition.onerror = (e) => {
      console.error("Speech error:", e.error)
      setIsListening(false)
    }

    //when the browser detects you stopped talking,turn off the red mic animation
    recognition.onend = () => setIsListening(false)

    recognitionRef.current = recognition
    recognition.start()
  }

  return (
    <div className="chat-input">
      <button 
        className={`mic-btn ${isListening ? "listening" : ""}`} 
        onClick={toggleListen}
        title={isListening ? "Stop listening" : "Click to speak"}
      >
        {isListening ? (
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <rect x="6" y="6" width="12" height="12" rx="2" ry="2" fill="currentColor"></rect>
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="22"></line>
          </svg>
        )}
      </button>

      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Ask about dams, lakes, reservoirs..."
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
          }
        }}
      />

      <button className="send-btn" onClick={handleSend}>
        Send
      </button>
    </div>
  )
}

export default ChatInput