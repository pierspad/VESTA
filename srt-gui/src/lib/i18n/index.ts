/**
 * Sistema di internazionalizzazione (i18n)
 * 
 * Struttura semplice e manutenibile:
 * - Un file JSON per ogni lingua in /locales/
 * - Riferimenti generici nel codice tramite chiavi
 * - Facile aggiungere nuove lingue
 */

import { derived, get, writable } from 'svelte/store';
import de from './locales/de.json';
import en from './locales/en.json';
import es from './locales/es.json';
import fr from './locales/fr.json';
import it from './locales/it.json';
import ja from './locales/ja.json';
import pt from './locales/pt.json';
import ru from './locales/ru.json';
import zh from './locales/zh.json';

// Definizione lingue disponibili per l'interfaccia
export interface UILanguage {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
}

export const availableUILanguages: UILanguage[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇬🇧' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵' },
];

// Mappa delle traduzioni
const translations: Record<string, Record<string, string>> = {
  en,
  it,
  de,
  es,
  fr,
  ru,
  pt,
  zh,
  ja,
};

// Store per la lingua corrente
const STORAGE_KEY = 'srt-tools-ui-language';

function getSystemLanguage(): string {
  if (typeof navigator !== 'undefined') {
    // Prova prima navigator.language (es: "it-IT", "en-US")
    const fullLang = navigator.language;
    const shortLang = fullLang.split('-')[0].toLowerCase();
    
    if (translations[shortLang]) {
      return shortLang;
    }
    
    // Prova navigator.languages per lingue alternative
    if (navigator.languages) {
      for (const lang of navigator.languages) {
        const short = lang.split('-')[0].toLowerCase();
        if (translations[short]) {
          return short;
        }
      }
    }
  }
  return 'en';
}

function getInitialLanguage(): string {
  if (typeof localStorage !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && translations[saved]) {
      return saved;
    }
  }
  // Usa la lingua del sistema operativo come default
  return getSystemLanguage();
}

export const currentLanguage = writable<string>(getInitialLanguage());

// Salva la lingua quando cambia
currentLanguage.subscribe((lang) => {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, lang);
  }
});

// Funzione di traduzione
export function t(key: string, params?: Record<string, string | number>): string {
  const lang = get(currentLanguage);
  const translation = translations[lang]?.[key] || translations['en']?.[key] || key;
  
  if (params) {
    return Object.entries(params).reduce(
      (str, [k, v]) => str.replace(new RegExp(`{{${k}}}`, 'g'), String(v)),
      translation
    );
  }
  
  return translation;
}

// Store derivato per le traduzioni reattive
export const locale = derived(currentLanguage, ($lang) => {
  return (key: string, params?: Record<string, string | number>): string => {
    const translation = translations[$lang]?.[key] || translations['en']?.[key] || key;
    
    if (params) {
      return Object.entries(params).reduce(
        (str, [k, v]) => str.replace(new RegExp(`{{${k}}}`, 'g'), String(v)),
        translation
      );
    }
    
    return translation;
  };
});

// Funzione per cambiare lingua
export function setLanguage(lang: string): void {
  if (translations[lang]) {
    currentLanguage.set(lang);
  }
}

// Funzione per ottenere la lingua corrente
export function getLanguage(): string {
  return get(currentLanguage);
}
