import Message from "./Message"

function ChatContainer({messages}){

return(

<div className="chat-container">

{messages.map((msg,i)=>(
<Message key={i} message={msg}/>
))}

</div>

)

}

export default ChatContainer