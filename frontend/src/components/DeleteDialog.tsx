import { useEffect } from 'react';
import { TrashIcon } from './Icons';

interface Props {
  title: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteDialog({ title, onConfirm, onCancel }: Props) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [onCancel]);

  return (
    <div className="delete-overlay" onClick={onCancel}>
      <div className="delete-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="delete-dialog-icon">
          <TrashIcon />
        </div>
        <h3 className="delete-dialog-title">Delete snippet</h3>
        <p className="delete-dialog-desc">
          Are you sure you want to delete <strong>"{title}"</strong>? This action cannot be undone.
        </p>
        <div className="delete-dialog-actions">
          <button className="snippet-btn snippet-btn--ghost" onClick={onCancel}>
            Cancel
          </button>
          <button className="snippet-btn snippet-btn--danger" onClick={onConfirm}>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
