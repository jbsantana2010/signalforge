'use client';

import { FunnelStep, FunnelField, Language } from '@/types/funnel';

interface StepRendererProps {
  step: FunnelStep;
  language: Language;
  answers: Record<string, string>;
  errors: Record<string, string>;
  onAnswer: (key: string, value: string) => void;
}

function FieldRenderer({
  field,
  language,
  value,
  error,
  onChange,
}: {
  field: FunnelField;
  language: Language;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const label = field.label[language] || field.label.en;

  const baseInputClass = `w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
    error ? 'border-red-500 bg-red-50' : 'border-gray-300'
  }`;

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>

      {field.type === 'select' && field.options ? (
        <div className="grid gap-2">
          {field.options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                value === option.value
                  ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                  : 'border-gray-200 hover:border-blue-200 hover:bg-gray-50'
              }`}
            >
              {option.label[language] || option.label.en}
            </button>
          ))}
        </div>
      ) : field.type === 'textarea' ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={baseInputClass}
          rows={4}
        />
      ) : (
        <input
          type={field.type === 'tel' ? 'tel' : 'text'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={baseInputClass}
          placeholder={label}
        />
      )}

      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}

export default function StepRenderer({ step, language, answers, errors, onAnswer }: StepRendererProps) {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {step.title[language] || step.title.en}
      </h2>
      <div className="space-y-4">
        {step.fields.map((field) => (
          <FieldRenderer
            key={field.key}
            field={field}
            language={language}
            value={answers[field.key] || ''}
            error={errors[field.key]}
            onChange={(value) => onAnswer(field.key, value)}
          />
        ))}
      </div>
    </div>
  );
}
