import { useState } from "react"
import ChatContainer from "./components/ChatContainer"
import ChatInput from "./components/ChatInput"
import Header from "./components/Header"
import "./App.css"

function App(){

const [messages,setMessages] = useState([])

const clearChat = () => {
setMessages([])
}

const sendMessage = async(text)=>{

const userMsg = {role:"user",content:text}
setMessages(prev=>[...prev,userMsg])

const res = await fetch("http://localhost:8000/ask",{
method:"POST",
headers:{ "Content-Type":"application/json"},
body:JSON.stringify({question:text})
})

const data = await res.json()

const botMsg = {role:"assistant",content:data.answer}

setMessages(prev=>[...prev,botMsg])

}

return(

<div className="app">

<Header clearChat={clearChat}/>

<ChatContainer messages={messages}/>

<ChatInput sendMessage={sendMessage}/>

</div>

)

}

export default App