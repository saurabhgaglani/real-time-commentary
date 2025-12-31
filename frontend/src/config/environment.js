/**
 * Environment configuration for chess commentary system
 * Automatically detects local vs cloud deployment
 */

// Detect if we're running in production (Google Cloud Run)
const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';

// For production, construct backend URL from current hostname
// Cloud Run services in same project can communicate via internal URLs
const getBackendUrl = () => {
  if (isProduction) {
    // Extract the project and region from current URL
    // Format: https://chess-commentary-frontend-HASH-uc.a.run.app
    const currentHost = window.location.hostname;
    const backendHost = currentHost.replace('chess-commentary-frontend', 'chess-commentary-backend');
    return `https://${backendHost}`;
  }
  return 'http://127.0.0.1:8000';
};

// Local development URLs
const LOCAL_BACKEND_URL = 'http://127.0.0.1:8000';
const LOCAL_WS_URL = 'ws://127.0.0.1:8000';

// Export configuration based on environment
export const API_CONFIG = {
  // Backend API base URL
  BACKEND_URL: getBackendUrl(),
  
  // WebSocket URL for live commentary
  WS_URL: isProduction 
    ? getBackendUrl().replace('https://', 'wss://') 
    : LOCAL_WS_URL,
  
  // Environment info
  IS_PRODUCTION: isProduction,
  
  // API endpoints
  ENDPOINTS: {
    ANALYZE: '/analyze',
    GAME_STATUS: '/game/status',
    WS_COMMENTARY: '/ws/commentary'
  }
};

// Log current configuration (only in development)
if (!isProduction) {
  console.log('🔧 Environment Configuration:', API_CONFIG);
}

export default API_CONFIG;