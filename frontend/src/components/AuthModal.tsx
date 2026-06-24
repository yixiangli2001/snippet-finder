import { useState } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';
import { HttpError } from '../utils/auth';
import TurnstileWidget from './TurnstileWidget';

type View = 'log in' | 'sign up' | 'forgot password' | 'check email' | 'reset sent';

interface Props {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, username: string, password: string, turnstileToken: string) => Promise<void>;
  onForgotPassword: (email: string, turnstileToken: string) => Promise<void>;
  onResendVerification: (email: string) => Promise<void>;
  onClose: () => void;
  initialMode?: 'log in' | 'sign up';
}

export function AuthModal({
  onLogin, onRegister, onForgotPassword, onResendVerification, onClose, initialMode = 'log in',
}: Props) {
  const [view, setView] = useState<View>(initialMode);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [turnstileToken, setTurnstileToken] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  // 403 on login means the account exists but isn't verified yet — offer to resend the link.
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendStatus, setResendStatus] = useState<'idle' | 'sending' | 'sent'>('idle');
  const panelRef = useFocusTrap(onClose);

  function switchView(next: View) {
    setView(next);
    setError('');
    setNeedsVerification(false);
    setResendStatus('idle');
    setTurnstileToken('');
  }

  async function handleResend() {
    setResendStatus('sending');
    try {
      await onResendVerification(email.trim());
      setResendStatus('sent');
    } catch {
      setResendStatus('idle');
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNeedsVerification(false);
    setSaving(true);
    try {
      if (view === 'sign up') {
        await onRegister(email.trim(), username.trim(), password, turnstileToken);
        setView('check email');
      } else if (view === 'forgot password') {
        await onForgotPassword(email.trim(), turnstileToken);
        setView('reset sent');
      } else {
        await onLogin(email.trim(), password);
        onClose();
      }
    } catch (err) {
      if (err instanceof HttpError && err.status === 403) {
        setNeedsVerification(true);
      }
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const title =
    view === 'sign up' ? 'Create Account' :
    view === 'forgot password' ? 'Reset Password' :
    view === 'check email' || view === 'reset sent' ? 'Check Your Email' :
    'Welcome Back';

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel auth-modal-panel" ref={panelRef} onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-head">
          <h2 className="overlay-title">{title}</h2>
          <button className="auth-modal-close" type="button" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        {view === 'check email' && (
          <div className="overlay-form">
            <p className="auth-message">
              We&apos;ve sent a verification link to <strong>{email}</strong>. Click it to activate your
              account, then log in.
            </p>
            <button className="snippet-btn snippet-btn--primary" onClick={() => switchView('log in')}>
              Back to log in
            </button>
          </div>
        )}

        {view === 'reset sent' && (
          <div className="overlay-form">
            <p className="auth-message">
              If an account exists for <strong>{email}</strong>, we&apos;ve sent a password reset link.
            </p>
            <button className="snippet-btn snippet-btn--primary" onClick={() => switchView('log in')}>
              Back to log in
            </button>
          </div>
        )}

        {(view === 'log in' || view === 'sign up' || view === 'forgot password') && (
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
              {view === 'sign up' && (
                <input
                  className="auth-input auth-input--full"
                  placeholder="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              )}
              {view !== 'forgot password' && (
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
                  {view === 'sign up' && <span className="auth-hint">Min. 8 characters</span>}
                </div>
              )}
              {(view === 'sign up' || view === 'forgot password') && (
                <TurnstileWidget onVerify={setTurnstileToken} onExpire={() => setTurnstileToken('')} />
              )}
            </div>

            <button className="snippet-btn snippet-btn--primary" disabled={saving}>
              {saving ? 'Processing…' :
                view === 'sign up' ? 'Create account' :
                view === 'forgot password' ? 'Send reset link' :
                'Log in'}
            </button>

            {view === 'log in' && (
              <div className="auth-switch">
                <button type="button" className="auth-switch-btn" onClick={() => switchView('forgot password')}>
                  Forgot password?
                </button>
              </div>
            )}

            <div className="auth-switch">
              {view === 'log in' ? (
                <>
                  Don&apos;t have an account?{' '}
                  <button type="button" className="auth-switch-btn" onClick={() => switchView('sign up')}>
                    Sign up
                  </button>
                </>
              ) : view === 'sign up' ? (
                <>
                  Already have an account?{' '}
                  <button type="button" className="auth-switch-btn" onClick={() => switchView('log in')}>
                    Log in
                  </button>
                </>
              ) : (
                <button type="button" className="auth-switch-btn" onClick={() => switchView('log in')}>
                  Back to log in
                </button>
              )}
            </div>

            {error && (
              <span className="auth-error">
                {error}
                {needsVerification && (
                  resendStatus === 'sent' ? (
                    <> Verification email resent.</>
                  ) : (
                    <>
                      {' '}
                      <button
                        type="button"
                        className="auth-switch-btn"
                        onClick={handleResend}
                        disabled={resendStatus === 'sending'}
                      >
                        {resendStatus === 'sending' ? 'Sending…' : 'Resend email'}
                      </button>
                    </>
                  )
                )}
              </span>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
