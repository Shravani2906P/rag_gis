import ReactMarkdown from "react-markdown"

function Message({message}){

const isUser = message.role === "user"

return(

<div className={`message-row ${isUser?"user":"bot"}`}>

<div className="message-bubble">

<ReactMarkdown>
{message.content}
</ReactMarkdown>

</div>

</div>

)

}

export default Message