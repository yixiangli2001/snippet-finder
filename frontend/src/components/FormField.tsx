interface FormFieldProps {
  error?: string;
  className?: string;
  children: React.ReactNode;
}

export function FormField({ error, className, children }: FormFieldProps) {
  return (
    <div className={`snippet-field${className ? ` ${className}` : ''}`}>
      {children}
      {error && <span className="snippet-field-error">{error}</span>}
    </div>
  );
}
