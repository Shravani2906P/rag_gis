function Header({ clearChat }) {

return (

<header className="header">

<div className="logo">
<<<<<<< HEAD
RAG GIS Assistant
=======

<div className="logo-text">
<p className="logo-sub">Water Resource AI</p>
>>>>>>> 45538ef71bd0693dbb60f86d3a65d8beaa4c07e1
</div>

</div>

<button className="new-chat" onClick={clearChat}>
+ New Chat
</button>

</header>

)

}

export default Header