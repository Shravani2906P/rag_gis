function Header({ clearChat, isMuted, toggleMute }) {
  return (
    <header className="header">
      <div className="logo">
        <div className="logo-text">
          <p className="logo-sub">Water Resource AI</p>
        </div>
      </div>

      <div className="header-actions">
        {/*mute toggle button */}
        <button 
          className={`mute-btn ${isMuted ? "muted" : ""}`} 
          onClick={toggleMute}
        >
          {isMuted ? "🔇 Muted" : "🔊 Sound On"}
        </button>

        <button className="new-chat" onClick={clearChat}>
          + New Chat
        </button>
      </div>
    </header>
  )
}

export default Header