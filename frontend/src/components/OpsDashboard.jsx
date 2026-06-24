// frontend/src/components/PilotDashboard.jsx
// STRATEX PILOT COMMAND // FIELD OPERATIONS INTERFACE
// PURPOSE: LIVE TELEMETRY FEED & DRONE-IN-A-BOX CONTROL

import React from 'react';

const PilotDashboard = () => {
  return (
    <div className="pilot-command-container" style={{ 
      padding: '25px', 
      background: '#0a0f14',
      border: '2px solid #00f2fe',
      borderRadius: '12px'
    }}>
      <h2 style={{ color: '#00f2fe' }}>// PILOT COMMAND // STATUS: ACTIVE</h2>
      
      {/* Hardware Telemetry Display */}
      <div className="telemetry-grid" style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        <div className="card" style={{ flex: 1, padding: '15px', border: '1px solid #ff9d00' }}>
          <h4>DJI HARDWARE SYNC</h4>
          <p style={{ color: '#00f2fe' }}>SIGNAL: ENCRYPTED // ACTIVE</p>
        </div>
        <div className="card" style={{ flex: 1, padding: '15px', border: '1px solid #ff9d00' }}>
          <h4>MISSION LOG</h4>
          <p>READY FOR SCAN SEQUENCE // CLARITY: OPTIMIZED</p>
        </div>
      </div>

      {/* Action Button */}
      <button style={{ 
        marginTop: '30px',
        width: '100%',
        padding: '20px',
        background: 'transparent',
        border: '2px solid #ff9d00',
        color: '#ff9d00',
        fontSize: '1.2rem',
        cursor: 'pointer',
        textTransform: 'uppercase'
      }}>
        // EXECUTE AERIAL SCAN SEQUENCE
      </button>
    </div>
  );
};

export default PilotDashboard;
