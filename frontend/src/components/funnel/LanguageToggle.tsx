'use client';

import { Language } from '@/types/funnel';

interface LanguageToggleProps {
  current: Language;
  available: string[];
  onChange: (lang: Language) => void;
}

const LANG_LABELS: Record<string, string> = {
  en: 'English',
  es: 'Español',
};

export default function LanguageToggle({ current, available, onChange }: LanguageToggleProps) {
  if (available.length <= 1) return null;

  return (
    <div className="flex items-center gap-2">
      {available.map((lang) => (
        <button
          key={lang}
          onClick={() => onChange(lang as Language)}
          className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
            current === lang
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {LANG_LABELS[lang] || lang}
        </button>
      ))}
    </div>
  );
}
