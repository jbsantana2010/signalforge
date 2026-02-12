'use client';

import { Language } from '@/types/funnel';

interface ThankYouScreenProps {
  language: Language;
}

const CONTENT = {
  en: {
    title: 'Thank You!',
    message: 'Your information has been submitted successfully. Our team will contact you shortly.',
    cta: 'Back to Home',
  },
  es: {
    title: 'Gracias!',
    message: 'Su informacion se ha enviado con exito. Nuestro equipo se pondra en contacto con usted pronto.',
    cta: 'Volver al Inicio',
  },
};

export default function ThankYouScreen({ language }: ThankYouScreenProps) {
  const content = CONTENT[language] || CONTENT.en;

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <div className="text-6xl mb-4">&#10003;</div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">{content.title}</h1>
        <p className="text-gray-600 mb-8">{content.message}</p>
        <a
          href="/"
          className="inline-block px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
        >
          {content.cta}
        </a>
      </div>
    </div>
  );
}
