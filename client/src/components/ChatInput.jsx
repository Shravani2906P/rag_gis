import {useState} from "react"

function ChatInput({sendMessage}){

const [text,setText] = useState("")

const handleSend=()=>{
if(!text.trim()) return
sendMessage(text)
setText("")
}

return(

<div className="chat-input">

<input
value={text}
onChange={(e)=>setText(e.target.value)}
placeholder="Ask about dams, lakes, reservoirs..."
onKeyDown={(e)=> e.key==="Enter" && handleSend()}
/>

<button onClick={handleSend}>
Send
</button>

</div>

)

}

export default ChatInput