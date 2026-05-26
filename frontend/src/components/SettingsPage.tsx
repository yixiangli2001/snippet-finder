import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { AlertIcon, SaveIcon, ShieldIcon, UserIcon } from './Icons';
import './CollectionPage.css'; /* for .collection-page-header and .collection-page-back */

export default function SettingsPage() {
  const { user, token, updateProfile, updatePassword, deleteAccount } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState(user?.username ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const [profileSaving, setProfileSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [profileError, setProfileError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [deleteError, setDeleteError] = useState('');

  const [profileSuccess, setProfileSuccess] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  // Redirect unauthenticated visitors
  if (!user) return <Navigate to="/snippets" replace />;

  const isProfileDirty = username !== user.username || email !== user.email;

  async function handleUpdateProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!isProfileDirty) return;
    setProfileError('');
    setProfileSuccess(false);
    setProfileSaving(true);
    try {
      await updateProfile({ username: username.trim(), email: email.trim() });
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3000);
    } catch (err) {
      setProfileError((err as Error).message);
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleUpdatePassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess(false);
    setPasswordSaving(true);
    try {
      await updatePassword(oldPassword, newPassword);
      setOldPassword('');
      setNewPassword('');
      setPasswordSuccess(true);
      setTimeout(() => setPasswordSuccess(false), 3000);
    } catch (err) {
      setPasswordError((err as Error).message);
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleDeleteAccount() {
    if (!window.confirm('Are you absolutely sure? This will delete all your snippets and cannot be undone.')) return;
    setDeleteError('');
    setDeleting(true);
    try {
      await deleteAccount();
    } catch (err) {
      setDeleteError((err as Error).message);
      setDeleting(false);
    }
  }

  return (
    <div className="settings-page">
      {/* Inner wrapper centres both header and body to 900px — same as admin panel */}
      <div className="settings-page-inner">
        <div className="collection-page-header">
          <button className="collection-page-back" onClick={() => navigate(-1)}>← Back</button>
          <h1 className="settings-page-title">Account Settings</h1>
        </div>

      <div className="settings-page-body">
        {/* ── Profile ──────────────────────────────── */}
        <section className="settings-section">
          <h2 className="settings-section-title">
            <UserIcon /> Profile
          </h2>
          <form className="overlay-form" onSubmit={handleUpdateProfile}>
            <div className="auth-fields">
              <div className="settings-input-group">
                <label className="settings-label">Username</label>
                <input
                  className="auth-input auth-input--full"
                  placeholder="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
              <div className="settings-input-group">
                <label className="settings-label">Email address</label>
                <input
                  className="auth-input auth-input--full"
                  placeholder="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="settings-action-row">
              <button className="snippet-btn snippet-btn--primary" disabled={profileSaving || !isProfileDirty}>
                <SaveIcon /> {profileSaving ? 'Saving…' : 'Update Profile'}
              </button>
              {profileSuccess && <span className="settings-success">Saved!</span>}
            </div>
            {profileError && <span className="auth-error">{profileError}</span>}
          </form>
        </section>

        <div className="settings-divider" />

        {/* ── Security ─────────────────────────────── */}
        <section className="settings-section">
          <h2 className="settings-section-title">
            <ShieldIcon /> Security
          </h2>
          <form className="overlay-form" onSubmit={handleUpdatePassword}>
            <div className="auth-fields">
              <div className="settings-input-group">
                <label className="settings-label">Current password</label>
                <input
                  className="auth-input auth-input--full"
                  placeholder="Current password"
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                />
              </div>
              <div className="settings-input-group">
                <label className="settings-label">New password</label>
                <div className="auth-password-wrap">
                  <input
                    className="auth-input auth-input--full"
                    placeholder="New password"
                    type="password"
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                  />
                  <span className="auth-hint">Min. 8 characters</span>
                </div>
              </div>
            </div>
            <div className="settings-action-row">
              <button className="snippet-btn snippet-btn--primary" disabled={passwordSaving}>
                <SaveIcon /> {passwordSaving ? 'Updating…' : 'Change Password'}
              </button>
              {passwordSuccess && <span className="settings-success">Password updated!</span>}
            </div>
            {passwordError && <span className="auth-error">{passwordError}</span>}
          </form>
        </section>

        <div className="settings-divider" />

        {/* ── Danger Zone ──────────────────────────── */}
        <section className="settings-section">
          <h2 className="settings-section-title settings-section-title--danger">
            <AlertIcon /> Danger Zone
          </h2>
          <p className="settings-section-desc">
            Once you delete your account, there is no going back. All private snippets and collections will be permanently deleted.
          </p>
          <div className="settings-action-row">
            <button className="snippet-btn snippet-btn--danger" disabled={deleting} onClick={handleDeleteAccount}>
              {deleting ? 'Deleting…' : 'Delete Account'}
            </button>
          </div>
          {deleteError && <p className="auth-error">{deleteError}</p>}
        </section>
      </div>
      </div>{/* end settings-page-inner */}
    </div>
  );
}
