import { en } from "./locales/en";
import { it } from "./locales/it";

type TranslationKey = keyof typeof en;
type Dictionary = Record<TranslationKey, string>;
const dictionaries: Record<string, Dictionary> = { en, it };

export function translate(
  key: TranslationKey,
  language = "en",
  values?: Record<string, string | number>,
): string {
  const locale = language.toLowerCase().split(/[-_]/)[0] ?? "en";
  let message: string = (dictionaries[locale] ?? en)[key];
  for (const [name, value] of Object.entries(values ?? {})) {
    message = message.replaceAll(`{${name}}`, String(value));
  }
  return message;
}

export function languageOf(
  language?: string,
  locale?: { language?: string },
): string {
  return locale?.language ?? language ?? "en";
}
