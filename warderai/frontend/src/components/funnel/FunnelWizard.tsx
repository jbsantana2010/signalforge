'use client';

import { useState } from 'react';
import { FunnelResponse, Language, FunnelStep } from '@/types/funnel';
import { submitLead } from '@/lib/api';
import LanguageToggle from './LanguageToggle';
import StepRenderer from './StepRenderer';
import ProgressBar from './ProgressBar';
import ThankYouScreen from './ThankYouScreen';

interface FunnelWizardProps {
  funnel: FunnelResponse;
}

const VALIDATION_MESSAGES: Record<string, Record<Language, string>> = {
  required: {
    en: 'This field is required',
    es: 'Este campo es obligatorio',
  },
  phone: {
    en: 'Please enter a valid phone number (at least 10 digits)',
    es: 'Ingrese un numero de telefono valido (al menos 10 digitos)',
  },
};

export default function FunnelWizard({ funnel }: FunnelWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [language, setLanguage] = useState<Language>(
    (funnel.languages?.[0] as Language) || 'en'
  );
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [honeypot, setHoneypot] = useState('');

  const steps = funnel.schema_json.steps;
  const step = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;

  const getSourceData = () => {
    if (typeof window === 'undefined') return {};
    const params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get('utm_source') || undefined,
      utm_medium: params.get('utm_medium') || undefined,
      utm_campaign: params.get('utm_campaign') || undefined,
      referrer: document.referrer || undefined,
      landing_url: window.location.href,
    };
  };

  const validateStep = (step: FunnelStep): boolean => {
    const newErrors: Record<string, string> = {};
    let isValid = true;

    for (const field of step.fields) {
      const value = answers[field.key] || '';

      if (field.required && !value.trim()) {
        newErrors[field.key] = VALIDATION_MESSAGES.required[language];
        isValid = false;
        continue;
      }

      if (field.type === 'tel' && value.trim()) {
        const digitsOnly = value.replace(/\D/g, '');
        if (digitsOnly.length < 10) {
          newErrors[field.key] = VALIDATION_MESSAGES.phone[language];
          isValid = false;
        }
      }
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleNext = async () => {
    if (!validateStep(step)) return;

    if (isLastStep) {
      setIsSubmitting(true);
      setSubmitError(null);
      try {
        const result = await submitLead({
          funnel_slug: funnel.slug,
          answers,
          language,
          source: getSourceData(),
          honeypot: honeypot || undefined,
        });
        if (result.success) {
          setIsComplete(true);
        } else {
          setSubmitError(result.message || 'Submission failed');
        }
      } catch {
        setSubmitError(
          language === 'es'
            ? 'Error al enviar. Intente de nuevo.'
            : 'Failed to submit. Please try again.'
        );
      } finally {
        setIsSubmitting(false);
      }
    } else {
      setCurrentStep((prev) => prev + 1);
      setErrors({});
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
      setErrors({});
    }
  };

  const handleAnswer = (key: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  if (isComplete) {
    return <ThankYouScreen language={language} />;
  }

  const buttonLabels = {
    next: { en: 'Next', es: 'Siguiente' },
    back: { en: 'Back', es: 'Atras' },
    submit: { en: 'Submit', es: 'Enviar' },
    submitting: { en: 'Submitting...', es: 'Enviando...' },
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-lg font-semibold text-gray-600">{funnel.name}</h1>
          <LanguageToggle
            current={language}
            available={funnel.languages}
            onChange={setLanguage}
          />
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          <ProgressBar current={currentStep} total={steps.length} />

          <StepRenderer
            step={step}
            language={language}
            answers={answers}
            errors={errors}
            onAnswer={handleAnswer}
          />

          {/* Honeypot - hidden from users */}
          <div style={{ position: 'absolute', left: '-9999px', opacity: 0 }} aria-hidden="true">
            <input
              type="text"
              name="website"
              tabIndex={-1}
              autoComplete="off"
              value={honeypot}
              onChange={(e) => setHoneypot(e.target.value)}
            />
          </div>

          {submitError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {submitError}
            </div>
          )}

          <div className="flex justify-between mt-8">
            <button
              type="button"
              onClick={handleBack}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                currentStep === 0
                  ? 'invisible'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {buttonLabels.back[language]}
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={isSubmitting}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting
                ? buttonLabels.submitting[language]
                : isLastStep
                ? buttonLabels.submit[language]
                : buttonLabels.next[language]}
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          {language === 'es'
            ? 'Protegido de forma segura'
            : 'Securely protected'}
        </p>
      </div>
    </div>
  );
}
