import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const auth = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await auth.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-page-card">
          <h1 className="overlay-title">Invalid link</h1>
          <p className="auth-error">This password reset link is missing its token.</p>
          <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
            Back to home
          </button>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-page-card">
          <h1 className="overlay-title">Password updated</h1>
          <p className="auth-message">You can log in with your new password now.</p>
          <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
            Go to Snippet Finder
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-page-card">
        <h1 className="overlay-title">Reset your password</h1>
        <form className="overlay-form" onSubmit={handleSubmit}>
          <div className="auth-fields">
            <div className="auth-password-wrap">
              <input
                className="auth-input auth-input--full"
                placeholder="New password"
                type="password"
                minLength={8}
                maxLength={72}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <span className="auth-hint">Min. 8 characters</span>
            </div>
          </div>
          <button className="snippet-btn snippet-btn--primary" disabled={saving}>
            {saving ? 'Updating…' : 'Update password'}
          </button>
          {error && <span className="auth-error">{error}</span>}
        </form>
      </div>
    </div>
  );
}
