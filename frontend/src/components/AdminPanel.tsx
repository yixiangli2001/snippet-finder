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
  const { users, loading, error, deleteUser } = useAdmin(token);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

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
                        <button
                          className="admin-delete-btn"
                          onClick={() => setConfirmingId(user.id)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
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
