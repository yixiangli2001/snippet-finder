import { useState } from 'react';
import './AdminPanel.css';
import { type User } from '../utils/auth';
import { useAdmin } from '../hooks/useAdmin';

interface Props {
  token: string;
  currentUserId: string;
  onBack: () => void;
}

export function AdminPanel({ token, currentUserId, onBack }: Props) {
  const { users, loading, error, updateUser, deleteUser } = useAdmin(token);

  // ── Delete state ───────────────────────────────────────────
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // ── Edit state ─────────────────────────────────────────────
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editUsername, setEditUsername] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState('');

  function startEdit(user: User) {
    setEditingId(user.id);
    setEditUsername(user.username);
    setEditEmail(user.email);
    setEditError('');
    setConfirmingId(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditError('');
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!editingId) return;
    setSaving(true);
    setEditError('');
    try {
      await updateUser(editingId, { username: editUsername.trim(), email: editEmail.trim() });
      setEditingId(null);
    } catch (err) {
      setEditError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(user: User) {
    setDeleteError('');
    setDeleting(true);
    try {
      await deleteUser(user.id);
      setConfirmingId(null);
    } catch (err) {
      setDeleteError((err as Error).message);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <button className="admin-back-btn" onClick={onBack}>← Back</button>
        <h1 className="admin-title">Admin Panel</h1>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Users</h2>

        {loading && <p className="admin-status">Loading…</p>}
        {error && <p className="admin-status admin-status--error">{error}</p>}

        {!loading && !error && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  editingId === user.id ? (
                    /* ── Inline edit row ── */
                    <tr key={user.id}>
                      <td colSpan={4}>
                        <form className="admin-edit-form" onSubmit={handleSave}>
                          <input
                            className="auth-input"
                            value={editUsername}
                            onChange={e => setEditUsername(e.target.value)}
                            placeholder="Username"
                            required
                          />
                          <input
                            className="auth-input"
                            type="email"
                            value={editEmail}
                            onChange={e => setEditEmail(e.target.value)}
                            placeholder="Email"
                            required
                          />
                          {editError && <span className="auth-error">{editError}</span>}
                          <div className="admin-confirm-row">
                            <button type="button" className="snippet-btn snippet-btn--ghost" onClick={cancelEdit}>
                              Cancel
                            </button>
                            <button type="submit" className="snippet-btn snippet-btn--primary" disabled={saving}>
                              {saving ? 'Saving…' : 'Save'}
                            </button>
                          </div>
                        </form>
                      </td>
                    </tr>
                  ) : (
                    /* ── Normal display row ── */
                    <tr key={user.id} className={user.id === currentUserId ? 'admin-row--self' : ''}>
                      <td className="admin-cell-username">{user.username}</td>
                      <td className="admin-cell-email">{user.email}</td>
                      <td>
                        <span className={`admin-role-badge${user.role === 'admin' ? ' admin-role-badge--admin' : ''}`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="admin-cell-actions">
                        {user.id === currentUserId ? (
                          <span className="admin-self-label">You</span>
                        ) : confirmingId === user.id ? (
                          <span className="admin-confirm-row">
                            <span className="admin-confirm-label">Delete {user.username}?</span>
                            <button
                              className="snippet-btn snippet-btn--danger"
                              onClick={() => handleDelete(user)}
                              disabled={deleting}
                            >
                              {deleting ? 'Deleting…' : 'Confirm'}
                            </button>
                            <button
                              className="snippet-btn snippet-btn--ghost"
                              onClick={() => { setConfirmingId(null); setDeleteError(''); }}
                              disabled={deleting}
                            >
                              Cancel
                            </button>
                          </span>
                        ) : (
                          <span className="admin-confirm-row">
                            <button className="admin-delete-btn" onClick={() => startEdit(user)}>
                              Edit
                            </button>
                            <button className="admin-delete-btn" onClick={() => setConfirmingId(user.id)}>
                              Delete
                            </button>
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                ))}
              </tbody>
            </table>
            {deleteError && <p className="auth-error" style={{ marginTop: '8px' }}>{deleteError}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
