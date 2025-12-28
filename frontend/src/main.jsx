import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import LiveCommentaryPage from './LiveCommentaryPage.jsx'

// Simple routing based on pathname
const renderApp = () => {
  const path = window.location.pathname;
  
  if (path === '/live-commentary') {
    return <LiveCommentaryPage />;
  }
  
  return <App />;
};

createRoot(document.getElementById('root')).render(
  renderApp()
)
