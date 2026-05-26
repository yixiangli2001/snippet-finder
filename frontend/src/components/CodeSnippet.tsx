import { useState } from "react";
import "./CodeSnippet.css";
import { FormField } from "./FormField";
import { LanguageSelect } from "./LanguageSelect";
import { DeleteDialog } from "./DeleteDialog";
import { CopyIcon, CheckIcon, EditIcon, EyeIcon, EyeOffIcon, PlusIcon, TrashIcon, XIcon } from "./Icons";
import AddToCollectionModal from "./AddToCollectionModal";
import { Link } from "react-router-dom";
import { displayOwner } from "../utils/author";

export interface Snippet {
  id: string;
  owner_id: string | null;
  owner_username: string | null;
  title: string;
  language: string;
  code: string;
  description: string;
  tags: string[];
  is_public: boolean;
  times_copied: number;
  created_at: string;
  updated_at: string;
}

interface Props {
  snippet: Snippet;
  canEdit?: boolean;
  token?: string;
  currentUserId?: string | null;
  onCopy?: (id: string) => void;
  onDelete?: (id: string) => void;
  onEdit?: (id: string, updated: Partial<Snippet>) => void;
  onToggleVisibility?: (id: string) => void;
  onRemove?: (id: string) => void;
  onCollectionChanged?: () => void;
}

export default function CodeSnippet({
  snippet,
  canEdit = false,
  token,
  currentUserId,
  onCopy,
  onDelete,
  onEdit,
  onToggleVisibility,
  onRemove,
  onCollectionChanged
}: Props) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [showAddToCollection, setShowAddToCollection] = useState(false);
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});
  const [editForm, setEditForm] = useState({
    title: snippet.title,
    language: snippet.language,
    code: snippet.code,
    description: snippet.description,
    tags: snippet.tags.join(", "),
  });

  async function handleCopy() {
    await navigator.clipboard.writeText(snippet.code);
    setCopied(true);
    onCopy?.(snippet.id);
    setTimeout(() => setCopied(false), 2000);
  }

  function validateEditForm() {
    const errors: Record<string, string> = {};
    if (!editForm.title.trim()) errors.title = "Title is required";
    if (!editForm.language.trim()) errors.language = "Language is required";
    if (!editForm.code.trim()) errors.code = "Code is required";
    return errors;
  }

  function clearError(field: string) {
    setEditErrors((err) => ({ ...err, [field]: "" }));
  }

  function handleSave() {
    const errors = validateEditForm();
    setEditErrors(errors);
    if (Object.keys(errors).length > 0) return;

    onEdit?.(snippet.id, {
      title: editForm.title.trim(),
      language: editForm.language.toUpperCase().trim(),
      code: editForm.code,
      description: editForm.description.trim(),
      tags: editForm.tags.split(",").map((t) => t.trim()).filter(Boolean),
    });
    setIsEditing(false);
  }

  function handleCancelEdit() {
    setEditForm({
      title: snippet.title,
      language: snippet.language,
      code: snippet.code,
      description: snippet.description,
      tags: snippet.tags.join(", "),
    });
    setIsEditing(false);
  }

  if (isEditing) {
    return (
      <article className="snippet-card snippet-card--editing">
        <div className="snippet-edit-form">
          <div className="snippet-edit-row">
            <FormField error={editErrors.title}>
              <input
                className={`snippet-edit-input${editErrors.title ? " snippet-edit-input--error" : ""}`}
                placeholder="Title *"
                value={editForm.title}
                onChange={(e) => {
                  setEditForm((f) => ({ ...f, title: e.target.value }));
                  clearError("title");
                }}
              />
            </FormField>
            <FormField error={editErrors.language} className="snippet-field--lang">
              <LanguageSelect
                value={editForm.language}
                onChange={(lang) => setEditForm((f) => ({ ...f, language: lang }))}
                error={editErrors.language}
                onClearError={() => clearError("language")}
              />
            </FormField>
          </div>
          <FormField error={editErrors.code}>
            <textarea
              className={`snippet-edit-textarea snippet-edit-code${editErrors.code ? " snippet-edit-input--error" : ""}`}
              placeholder="Code *"
              value={editForm.code}
              onChange={(e) => {
                setEditForm((f) => ({ ...f, code: e.target.value }));
                clearError("code");
              }}
              rows={8}
              spellCheck={false}
            />
          </FormField>
          <textarea
            className="snippet-edit-textarea"
            placeholder="Description (optional)"
            value={editForm.description}
            onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
            rows={2}
          />
          <input
            className="snippet-edit-input"
            placeholder="Tags (comma separated)"
            value={editForm.tags}
            onChange={(e) => setEditForm((f) => ({ ...f, tags: e.target.value }))}
          />
          <div className="snippet-edit-actions">
            <button className="snippet-btn snippet-btn--ghost" onClick={handleCancelEdit}>
              Cancel
            </button>
            <button className="snippet-btn snippet-btn--primary" onClick={handleSave}>
              Save
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="snippet-card">
      <header className="snippet-header">
        <div className="snippet-header-top">
          <div className="snippet-meta">
            <span className="snippet-lang">{snippet.language}</span>
            <span className={snippet.is_public ? "snippet-visibility snippet-visibility--public" : "snippet-visibility"}>
              {snippet.is_public ? "Public" : "Private"}
            </span>
          </div>
          <div className="snippet-actions">
            {token && currentUserId && !onRemove && (
              <button
                className="snippet-action-btn"
                onClick={() => setShowAddToCollection(true)}
                title="Add to collection"
                aria-label="Add to collection"
              >
                <PlusIcon />
              </button>
            )}
            {onRemove && (
              <button
                className="snippet-action-btn snippet-action-btn--delete"
                onClick={() => onRemove(snippet.id)}
                title="Remove from collection"
                aria-label="Remove from collection"
              >
                <XIcon />
              </button>
            )}
            {canEdit && !onRemove && (
              <>
                <button
                  className="snippet-action-btn"
                  onClick={() => onToggleVisibility?.(snippet.id)}
                  title={snippet.is_public ? "Make private" : "Make public"}
                  aria-label={snippet.is_public ? "Make private" : "Make public"}
                >
                  {snippet.is_public ? <EyeOffIcon /> : <EyeIcon />}
                </button>
                <button
                  className="snippet-action-btn"
                  onClick={() => setIsEditing(true)}
                  title="Edit snippet"
                  aria-label="Edit snippet"
                >
                  <EditIcon />
                </button>
                <button
                  className="snippet-action-btn snippet-action-btn--delete"
                  onClick={() => setConfirmingDelete(true)}
                  title="Delete snippet"
                  aria-label="Delete snippet"
                >
                  <TrashIcon />
                </button>
              </>
            )}
          </div>
        </div>
        <h2 className="snippet-title">{snippet.title}</h2>
        {snippet.description && (
          <p className="snippet-description">{snippet.description}</p>
        )}
      </header>

      <div
        className={`snippet-code-wrapper${copied ? " copied" : ""}`}
        onClick={handleCopy}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && handleCopy()}
        aria-label="Copy code"
      >
        <span className="snippet-copy-btn" aria-hidden="true" title={copied ? "Copied!" : "Copy code"}>
          {copied ? <CheckIcon /> : <CopyIcon />}
        </span>
        <pre className="snippet-pre">
          <code>{snippet.code}</code>
        </pre>
      </div>

      <footer className="snippet-footer">
        <div className="snippet-footer-row">
          {snippet.tags.length > 0 && (
            <ul className="snippet-tags">
              {snippet.tags.map((tag) => (
                <li key={tag} className="snippet-tag">
                  {tag}
                </li>
              ))}
            </ul>
          )}
          <span className="snippet-copies">
            {snippet.times_copied} {snippet.times_copied === 1 ? "copy" : "copies"}
          </span>
        </div>
        {snippet.owner_username ? (
          <Link to={`/users/${snippet.owner_username}`} className="snippet-owner snippet-owner--link">
            {snippet.owner_username}
          </Link>
        ) : (
          <span className="snippet-owner">Anonymous</span>
        )}
      </footer>

      {confirmingDelete && (
        <DeleteDialog
          title={snippet.title}
          onConfirm={() => {
            onDelete?.(snippet.id);
            setConfirmingDelete(false);
          }}
          onCancel={() => setConfirmingDelete(false)}
        />
      )}

      {showAddToCollection && token && (
        <AddToCollectionModal
          snippetId={snippet.id}
          token={token}
          currentUserId={currentUserId ?? ""}
          onClose={() => setShowAddToCollection(false)}
          onSuccess={() => {
            setShowAddToCollection(false);
            onCollectionChanged?.();
          }}
        />
      )}
    </article>
  );
}
