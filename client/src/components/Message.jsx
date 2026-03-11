import ReactMarkdown from "react-markdown"

function Message({message}){

const isUser = message.role === "user"

return(

<div className={`message-row ${isUser ? "user" : "bot"}`}>

{!isUser && (
<div className="avatar">AI</div>
)}

<div className="message-bubble">

<ReactMarkdown>
{message.content}
</ReactMarkdown>

</div>

{isUser && (
<div className="avatar">U</div>
)}

</div>

)

}

export default Message