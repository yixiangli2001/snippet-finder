import { useState } from 'react';
import { type User } from '../utils/auth';
import { AlertIcon, SaveIcon, ShieldIcon, UserIcon } from './Icons';

interface Props {
  user: User;
  onUpdateProfile: (updates: { email?: string; username?: string }) => Promise<void>;
  onUpdatePassword: (old: string, next: string) => Promise<void>;
  onDeleteAccount: () => Promise<void>;
  onClose: () => void;
}

export function SettingsModal({ user, onUpdateProfile, onUpdatePassword, onDeleteAccount, onClose }: Props) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
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

  async function handleUpdateProfile(e: React.FormEvent) {
    e.preventDefault();
    if (username === user.username && email === user.email) return;
    setProfileError('');
    setProfileSuccess(false);
    setProfileSaving(true);
    try {
      await onUpdateProfile({ username: username.trim(), email: email.trim() });
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
      await onUpdatePassword(oldPassword, newPassword);
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
      await onDeleteAccount();
      onClose();
    } catch (err) {
      setDeleteError((err as Error).message);
      setDeleting(false);
    }
  }

  const isProfileDirty = username !== user.username || email !== user.email;

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel settings-modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-head">
          <h2 className="overlay-title">Account Settings</h2>
          <button className="auth-modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>

        <div className="settings-sections">
          <section className="settings-section">
            <h3 className="settings-section-title">
              <UserIcon /> Profile
            </h3>
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
                <button 
                  className="snippet-btn snippet-btn--primary" 
                  disabled={profileSaving || !isProfileDirty}
                >
                  <SaveIcon /> {profileSaving ? 'Saving...' : 'Update Profile'}
                </button>
                {profileSuccess && <span className="settings-success">Saved!</span>}
              </div>
              {profileError && <span className="auth-error">{profileError}</span>}
            </form>
          </section>

          <div className="user-dropdown-divider" />

          <section className="settings-section">
            <h3 className="settings-section-title">
              <ShieldIcon /> Security
            </h3>
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
                  <SaveIcon /> {passwordSaving ? 'Updating...' : 'Change Password'}
                </button>
                {passwordSuccess && <span className="settings-success">Password updated!</span>}
              </div>
              {passwordError && <span className="auth-error">{passwordError}</span>}
            </form>
          </section>

          <div className="user-dropdown-divider" />

          <section className="settings-section">
            <h3 className="settings-section-title settings-section-title--danger">
              <AlertIcon /> Danger Zone
            </h3>
            <p className="settings-section-desc">Once you delete your account, there is no going back. Please be certain.</p>
            <div className="settings-action-row">
              <button 
                className="snippet-btn snippet-btn--danger" 
                disabled={deleting}
                onClick={handleDeleteAccount}
              >
                Delete Account
              </button>
            </div>
            {deleteError && <p className="auth-error">{deleteError}</p>}
          </section>
        </div>
      </div>
    </div>
  );
}
