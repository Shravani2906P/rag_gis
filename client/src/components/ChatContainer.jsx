import Message from "./Message"

function ChatContainer({messages}){

if(messages.length === 0){
return(

<div className="chat-container welcome">

<h1>RAG GIS Assistant</h1>

<p>
Ask questions about dams, lakes, reservoirs, and GIS datasets.
</p>

<div className="suggestions">

<button>Dams in India</button>
<button>Largest reservoirs</button>
<button>Major lakes in Gujarat</button>
<button>Water storage statistics</button>

</div>

</div>

)
}

return(

<div className="chat-container">

{messages.map((msg,i)=>(
<Message key={i} message={msg}/>
))}

</div>

)

}

export default ChatContainer