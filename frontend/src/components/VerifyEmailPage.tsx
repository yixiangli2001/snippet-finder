import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const auth = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [error, setError] = useState('');
  // The verify token is single-use, so the request must fire exactly once.
  // StrictMode runs effects twice in dev; without this guard the second run
  // would consume an already-spent token and report a false "failed".
  const verifiedToken = useRef<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setError('This verification link is missing its token.');
      return;
    }
    if (verifiedToken.current === token) return;
    verifiedToken.current = token;
    auth.verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err: Error) => {
        setStatus('error');
        setError(err.message);
      });
    // Only re-run if the token in the URL changes — auth.verifyEmail is stable
    // for the lifetime of this page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <div className="auth-page">
      <div className="auth-page-card">
        {status === 'verifying' && <p className="auth-message">Verifying your email…</p>}

        {status === 'success' && (
          <>
            <h1 className="overlay-title">Email verified</h1>
            <p className="auth-message">Your account is ready. You can log in now.</p>
            <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
              Go to Snippet Finder
            </button>
          </>
        )}

        {status === 'error' && (
          <>
            <h1 className="overlay-title">Verification failed</h1>
            <p className="auth-error">{error}</p>
            <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
              Back to home
            </button>
          </>
        )}
      </div>
    </div>
  );
}
