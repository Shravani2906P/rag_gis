function Header({ clearChat }) {

return (

<header className="header">

<div className="logo">

<div className="logo-icon">🛰️</div>

<div className="logo-text">
<h2>RAG GIS Assistant</h2>
<p className="logo-sub">Water Resource AI</p>
</div>

</div>

<button className="new-chat" onClick={clearChat}>
+ New Chat
</button>

</header>

)

}

export default Header