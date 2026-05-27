// All auth state lives in AuthContext so every component shares one source of truth.
// Calling useAuth() in multiple components used to give each component its own
// independent state copy — meaning logout() in App only cleared App's copy.
export { useAuthContext as useAuth } from '../context/AuthContext';
