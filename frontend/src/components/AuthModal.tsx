import { useState } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';

interface Props {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, username: string, password: string) => Promise<void>;
  onClose: () => void;
  initialMode?: 'log in' | 'sign up';
}

export function AuthModal({ onLogin, onRegister, onClose, initialMode = 'log in' }: Props) {
  const [mode, setMode] = useState<'log in' | 'sign up'>(initialMode);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const panelRef = useFocusTrap(onClose);

  function switchMode(next: 'log in' | 'sign up') {
    setMode(next);
    setError('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      if (mode === 'sign up') {
        await onRegister(email.trim(), username.trim(), password);
      } else {
        await onLogin(email.trim(), password);
      }
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel auth-modal-panel" ref={panelRef} onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-head">
          <h2 className="overlay-title">{mode === 'log in' ? 'Welcome Back' : 'Create Account'}</h2>
          <button className="auth-modal-close" type="button" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        <form className="overlay-form" onSubmit={handleSubmit}>
          <div className="auth-fields">
            <input
              className="auth-input auth-input--full"
              placeholder="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required

            />
            {mode === 'sign up' && (
              <input
                className="auth-input auth-input--full"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            )}
            <div className="auth-password-wrap">
              <input
                className="auth-input auth-input--full"
                placeholder="Password"
                type="password"
                minLength={8}
                maxLength={72}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              {mode === 'sign up' && (
                <span className="auth-hint">Min. 8 characters</span>
              )}
            </div>
          </div>
          
          <button className="snippet-btn snippet-btn--primary" disabled={saving}>
            {saving ? 'Processing…' : mode === 'sign up' ? 'Create account' : 'Log in'}
          </button>

          <div className="auth-switch">
            {mode === 'log in' ? (
              <>
                Don&apos;t have an account?{' '}
                <button type="button" className="auth-switch-btn" onClick={() => switchMode('sign up')}>
                  Sign up
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button type="button" className="auth-switch-btn" onClick={() => switchMode('log in')}>
                  Log in
                </button>
              </>
            )}
          </div>

          {error && <span className="auth-error">{error}</span>}
        </form>
      </div>
    </div>
  );
}
