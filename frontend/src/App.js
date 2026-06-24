// frontend/src/App.js
// STRATEX-QUANT MASTER PORTAL ENTRY
// BRANDING: DARK-MODE LUXURY-CORPORATE
// AESTHETIC: ELECTRIC CYBER TEAL, HYPER-VOLT ORANGE, METALLIC GOLD FILIGREE

import React from 'react';
import StratexPortal from './components/StratexPortal';

function App() {
  return (
    <div className="stratex-app-wrapper" style={{ 
      backgroundColor: '#0a0f14', 
      minHeight: '100vh', 
      color: '#e0e0e0',
      fontFamily: 'Orbitron, sans-serif',
      margin: 0,
      padding: 0
    }}>
      <header style={{ 
        borderBottom: '2px solid #00f2fe', 
        padding: '20px', 
        textAlign: 'center',
        background: 'linear-gradient(180deg, #101a22 0%, #0a0f14 100%)'
      }}>
        <h1 style={{ 
          color: '#00f2fe', 
          textShadow: '0 0 10px #00f2fe, 0 0 20px #00f2fe',
          margin: 0,
          letterSpacing: '2px'
        }}>
          STRATEX // COMPREHENSIVE RESIDENTIAL ANALYSIS
        </h1>
      </header>
      
      <main>
        <StratexPortal />
      </main>

      <footer style={{ 
        marginTop: '50px', 
        padding: '20px', 
        fontSize: '0.8rem', 
        opacity: '0.6',
        textAlign: 'center',
        borderTop: '1px solid #ff9d00'
      }}>
        <p>STRATEX RESIDENTIAL DETECT NETWORK // COMMAND CENTER OVERSIGHT</p>
      </footer>
    </div>
  );
}

export default App;
