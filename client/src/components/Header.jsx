function Header(){

const refreshChat = () => {
window.location.reload()
}

return(

<div className="header">

<div className="logo">
🛰️ RAG GIS Assistant
</div>

<button className="new-chat" onClick={refreshChat}>
+ New Chat
</button>

</div>

)

}

export default Header