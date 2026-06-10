/**
 * src/main.jsx
 * -------------
 * React application entry point.
 * Mounts the App component into the #root DOM node.
 * Imports global CSS (Tailwind base + custom overrides).
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
