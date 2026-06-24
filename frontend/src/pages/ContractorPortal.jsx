// frontend/src/pages/ContractorPortal.jsx
// STRATEX CONTRACTOR GATEWAY // RESIDENTIAL PROJECT TRACKING
// PURPOSE: UNIFIED ACCESS TO DIAGNOSTIC REPORTS & MATERIAL SCHEDULES

import React from 'react';

const ContractorPortal = () => {
  return (
    <div className="contractor-portal-container" style={{ 
      padding: '30px', 
      background: '#0a0f14',
      minHeight: '100vh',
      color: '#e0e0e0'
    }}>
      <h1 style={{ color: '#00f2fe' }}>// CONTRACTOR GATEWAY // PROJECT ACCESS</h1>
      
      {/* Project Status Panel */}
      <div className="project-feed" style={{ 
        marginTop: '30px', 
        border: '1px solid #00f2fe', 
        padding: '20px' 
      }}>
        <h3 style={{ color: '#ff9d00' }}>// ACTIVE RESIDENTIAL DIAGNOSTICS</h3>
        <p>AWAITING DRONE-IN-A-BOX TELEMETRY INTEGRATION...</p>
      </div>

      {/* Action Schedules */}
      <div className="schedule-panel" style={{ marginTop: '20px', display: 'grid', gap: '15px' }}>
        <button className="neon-button" style={{ padding: '15px', border: '1px solid #00f2fe' }}>
          VIEW WINDOW & DOOR SCHEDULE
        </button>
        <button className="neon-button" style={{ padding: '15px', border: '1px solid #00f2fe' }}>
          VIEW MOISTURE INTEGRITY REPORT
        </button>
      </div>
    </div>
  );
};

export default ContractorPortal;
