"""
RPP Internationalization Module

Provides translations for CLI output in multiple languages.
Zero dependencies - uses simple dictionary-based approach.

Supported languages:
  - en: English (default)
  - ar-gulf: Gulf Arabic (UAE, Qatar, Kuwait, Bahrain)
  - ar-hejaz: Hejazi Arabic (Western Saudi Arabia)
  - es: Spanish
  - ru: Russian
"""

from typing import Dict

# Default language
DEFAULT_LANG = "en"

# Supported languages
SUPPORTED_LANGS = ["en", "ar-gulf", "ar-hejaz", "es", "ru"]

# Translation dictionaries
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Status messages
        "ok": "OK",
        "fail": "FAIL",
        "encode": "ENCODE",
        "decode": "DECODE",
        "resolve": "RESOLVE",

        # Field labels
        "shell": "shell",
        "theta": "theta",
        "phi": "phi",
        "harmonic": "harmonic",
        "allowed": "allowed",
        "route": "route",
        "reason": "reason",

        # Shell names
        "shell_hot": "Hot",
        "shell_warm": "Warm",
        "shell_cold": "Cold",
        "shell_frozen": "Frozen",

        # Sector names
        "sector_gene": "Gene",
        "sector_memory": "Memory",
        "sector_witness": "Witness",
        "sector_dream": "Dream",
        "sector_bridge": "Bridge",
        "sector_guardian": "Guardian",
        "sector_emergence": "Emergence",
        "sector_meta": "Meta",

        # Grounding levels
        "grounding_grounded": "Grounded",
        "grounding_transitional": "Transitional",
        "grounding_abstract": "Abstract",
        "grounding_ethereal": "Ethereal",

        # Demo/Tutorial
        "demo_title": "Rotational Packet Protocol",
        "demo_subtitle": "28-bit Semantic Addressing",
        "demo_tagline": "Consent-Aware Routing",
        "routing_decision": "ROUTING DECISION",
        "demonstration_complete": "Demonstration Complete",
        "consent_level": "Consent Level",

        # Scenarios
        "scenario_1_title": "SCENARIO 1: Allowed Read (Grounded Consent)",
        "scenario_2_title": "SCENARIO 2: Denied Write (Ethereal - Consent Required)",
        "scenario_3_title": "SCENARIO 3: Cold Storage Routing",

        # Key takeaways
        "takeaway_grounded": "Low phi (Grounded) = immediate access allowed",
        "takeaway_ethereal": "High phi (Ethereal) = explicit consent required",
        "takeaway_cold": "Cold shell = routed to archive storage",

        # Reasons
        "reason_read_memory": "read permitted via memory",
        "reason_read_archive": "read permitted via archive",
        "reason_write_ethereal": "Write to ethereal zone requires explicit consent",

        # Tutorial
        "tutorial_welcome": "Welcome to the RPP Tutorial",
        "tutorial_what_is": "What is RPP?",
        "tutorial_address": "The 28-bit Address",
        "tutorial_resolver": "The Resolver",
        "tutorial_try_it": "Try it yourself",

        # Version
        "version": "version",
    },

    "ar-gulf": {
        # Status messages - Gulf Arabic
        "ok": "تمام",
        "fail": "فشل",
        "encode": "ترميز",
        "decode": "فك الترميز",
        "resolve": "حل",

        # Field labels
        "shell": "الطبقة",
        "theta": "ثيتا",
        "phi": "فاي",
        "harmonic": "التوافقي",
        "allowed": "مسموح",
        "route": "المسار",
        "reason": "السبب",

        # Shell names
        "shell_hot": "ساخن",
        "shell_warm": "دافئ",
        "shell_cold": "بارد",
        "shell_frozen": "مجمد",

        # Sector names
        "sector_gene": "الجين",
        "sector_memory": "الذاكرة",
        "sector_witness": "الشاهد",
        "sector_dream": "الحلم",
        "sector_bridge": "الجسر",
        "sector_guardian": "الحارس",
        "sector_emergence": "الظهور",
        "sector_meta": "ميتا",

        # Grounding levels
        "grounding_grounded": "مؤرض",
        "grounding_transitional": "انتقالي",
        "grounding_abstract": "مجرد",
        "grounding_ethereal": "أثيري",

        # Demo/Tutorial
        "demo_title": "بروتوكول الحزمة الدورانية",
        "demo_subtitle": "عنونة دلالية 28-بت",
        "demo_tagline": "توجيه واعي بالموافقة",
        "routing_decision": "قرار التوجيه",
        "demonstration_complete": "اكتمل العرض",
        "consent_level": "مستوى الموافقة",

        # Scenarios
        "scenario_1_title": "السيناريو 1: قراءة مسموحة (موافقة مؤرضة)",
        "scenario_2_title": "السيناريو 2: كتابة مرفوضة (أثيري - موافقة مطلوبة)",
        "scenario_3_title": "السيناريو 3: توجيه التخزين البارد",

        # Key takeaways
        "takeaway_grounded": "فاي منخفض (مؤرض) = وصول فوري مسموح",
        "takeaway_ethereal": "فاي عالي (أثيري) = موافقة صريحة مطلوبة",
        "takeaway_cold": "طبقة باردة = توجيه إلى الأرشيف",

        # Reasons
        "reason_read_memory": "القراءة مسموحة عبر الذاكرة",
        "reason_read_archive": "القراءة مسموحة عبر الأرشيف",
        "reason_write_ethereal": "الكتابة للمنطقة الأثيرية تتطلب موافقة صريحة",

        # Tutorial
        "tutorial_welcome": "مرحباً بك في درس RPP",
        "tutorial_what_is": "ما هو RPP؟",
        "tutorial_address": "العنوان 28-بت",
        "tutorial_resolver": "المحلل",
        "tutorial_try_it": "جربها بنفسك",

        # Version
        "version": "الإصدار",
    },

    "ar-hejaz": {
        # Status messages - Hejazi Arabic
        "ok": "تمام",
        "fail": "ما زبط",
        "encode": "ترميز",
        "decode": "فك الترميز",
        "resolve": "حل",

        # Field labels
        "shell": "الطبقة",
        "theta": "ثيتا",
        "phi": "فاي",
        "harmonic": "التوافقي",
        "allowed": "مسموح",
        "route": "المسار",
        "reason": "السبب",

        # Shell names
        "shell_hot": "حار",
        "shell_warm": "دافي",
        "shell_cold": "بارد",
        "shell_frozen": "مجمد",

        # Sector names
        "sector_gene": "الجين",
        "sector_memory": "الذاكرة",
        "sector_witness": "الشاهد",
        "sector_dream": "الحلم",
        "sector_bridge": "الجسر",
        "sector_guardian": "الحارس",
        "sector_emergence": "الظهور",
        "sector_meta": "ميتا",

        # Grounding levels
        "grounding_grounded": "متأصل",
        "grounding_transitional": "انتقالي",
        "grounding_abstract": "مجرد",
        "grounding_ethereal": "أثيري",

        # Demo/Tutorial
        "demo_title": "بروتوكول الحزمة الدورانية",
        "demo_subtitle": "عنونة دلالية 28-بت",
        "demo_tagline": "توجيه بموافقة",
        "routing_decision": "قرار التوجيه",
        "demonstration_complete": "خلص العرض",
        "consent_level": "مستوى الموافقة",

        # Scenarios
        "scenario_1_title": "السيناريو 1: قراءة مسموحة (موافقة متأصلة)",
        "scenario_2_title": "السيناريو 2: كتابة مرفوضة (أثيري - تبي موافقة)",
        "scenario_3_title": "السيناريو 3: توجيه للتخزين البارد",

        # Key takeaways
        "takeaway_grounded": "فاي واطي (متأصل) = دخول فوري مسموح",
        "takeaway_ethereal": "فاي عالي (أثيري) = لازم موافقة صريحة",
        "takeaway_cold": "طبقة باردة = يروح للأرشيف",

        # Reasons
        "reason_read_memory": "القراءة مسموحة من الذاكرة",
        "reason_read_archive": "القراءة مسموحة من الأرشيف",
        "reason_write_ethereal": "الكتابة للمنطقة الأثيرية تبي موافقة صريحة",

        # Tutorial
        "tutorial_welcome": "أهلاً فيك في درس RPP",
        "tutorial_what_is": "ايش هو RPP؟",
        "tutorial_address": "العنوان 28-بت",
        "tutorial_resolver": "المحلل",
        "tutorial_try_it": "جربها بنفسك",

        # Version
        "version": "الإصدار",
    },

    "es": {
        # Status messages - Spanish
        "ok": "OK",
        "fail": "ERROR",
        "encode": "CODIFICAR",
        "decode": "DECODIFICAR",
        "resolve": "RESOLVER",

        # Field labels
        "shell": "capa",
        "theta": "theta",
        "phi": "phi",
        "harmonic": "armónico",
        "allowed": "permitido",
        "route": "ruta",
        "reason": "razón",

        # Shell names
        "shell_hot": "Caliente",
        "shell_warm": "Tibio",
        "shell_cold": "Frío",
        "shell_frozen": "Congelado",

        # Sector names
        "sector_gene": "Gen",
        "sector_memory": "Memoria",
        "sector_witness": "Testigo",
        "sector_dream": "Sueño",
        "sector_bridge": "Puente",
        "sector_guardian": "Guardián",
        "sector_emergence": "Emergencia",
        "sector_meta": "Meta",

        # Grounding levels
        "grounding_grounded": "Arraigado",
        "grounding_transitional": "Transicional",
        "grounding_abstract": "Abstracto",
        "grounding_ethereal": "Etéreo",

        # Demo/Tutorial
        "demo_title": "Protocolo de Paquete Rotacional",
        "demo_subtitle": "Direccionamiento Semántico de 28 bits",
        "demo_tagline": "Enrutamiento Consciente del Consentimiento",
        "routing_decision": "DECISIÓN DE ENRUTAMIENTO",
        "demonstration_complete": "Demostración Completa",
        "consent_level": "Nivel de Consentimiento",

        # Scenarios
        "scenario_1_title": "ESCENARIO 1: Lectura Permitida (Consentimiento Arraigado)",
        "scenario_2_title": "ESCENARIO 2: Escritura Denegada (Etéreo - Requiere Consentimiento)",
        "scenario_3_title": "ESCENARIO 3: Enrutamiento a Almacenamiento Frío",

        # Key takeaways
        "takeaway_grounded": "Phi bajo (Arraigado) = acceso inmediato permitido",
        "takeaway_ethereal": "Phi alto (Etéreo) = se requiere consentimiento explícito",
        "takeaway_cold": "Capa fría = enrutado al archivo",

        # Reasons
        "reason_read_memory": "lectura permitida vía memoria",
        "reason_read_archive": "lectura permitida vía archivo",
        "reason_write_ethereal": "Escritura a zona etérea requiere consentimiento explícito",

        # Tutorial
        "tutorial_welcome": "Bienvenido al Tutorial de RPP",
        "tutorial_what_is": "¿Qué es RPP?",
        "tutorial_address": "La Dirección de 28 bits",
        "tutorial_resolver": "El Resolutor",
        "tutorial_try_it": "Pruébalo tú mismo",

        # Version
        "version": "versión",
    },

    "ru": {
        # Status messages - Russian
        "ok": "ОК",
        "fail": "ОШИБКА",
        "encode": "КОДИРОВАТЬ",
        "decode": "ДЕКОДИРОВАТЬ",
        "resolve": "РАЗРЕШИТЬ",

        # Field labels
        "shell": "оболочка",
        "theta": "тета",
        "phi": "фи",
        "harmonic": "гармоника",
        "allowed": "разрешено",
        "route": "маршрут",
        "reason": "причина",

        # Shell names
        "shell_hot": "Горячий",
        "shell_warm": "Тёплый",
        "shell_cold": "Холодный",
        "shell_frozen": "Замороженный",

        # Sector names
        "sector_gene": "Ген",
        "sector_memory": "Память",
        "sector_witness": "Свидетель",
        "sector_dream": "Сон",
        "sector_bridge": "Мост",
        "sector_guardian": "Страж",
        "sector_emergence": "Возникновение",
        "sector_meta": "Мета",

        # Grounding levels
        "grounding_grounded": "Заземлённый",
        "grounding_transitional": "Переходный",
        "grounding_abstract": "Абстрактный",
        "grounding_ethereal": "Эфирный",

        # Demo/Tutorial
        "demo_title": "Протокол Ротационных Пакетов",
        "demo_subtitle": "28-битная Семантическая Адресация",
        "demo_tagline": "Маршрутизация с Учётом Согласия",
        "routing_decision": "РЕШЕНИЕ О МАРШРУТИЗАЦИИ",
        "demonstration_complete": "Демонстрация Завершена",
        "consent_level": "Уровень Согласия",

        # Scenarios
        "scenario_1_title": "СЦЕНАРИЙ 1: Разрешённое Чтение (Заземлённое Согласие)",
        "scenario_2_title": "СЦЕНАРИЙ 2: Запрещённая Запись (Эфирный - Требуется Согласие)",
        "scenario_3_title": "СЦЕНАРИЙ 3: Маршрутизация в Холодное Хранилище",

        # Key takeaways
        "takeaway_grounded": "Низкий phi (Заземлённый) = немедленный доступ разрешён",
        "takeaway_ethereal": "Высокий phi (Эфирный) = требуется явное согласие",
        "takeaway_cold": "Холодная оболочка = маршрут в архив",

        # Reasons
        "reason_read_memory": "чтение разрешено через память",
        "reason_read_archive": "чтение разрешено через архив",
        "reason_write_ethereal": "Запись в эфирную зону требует явного согласия",

        # Tutorial
        "tutorial_welcome": "Добро пожаловать в Учебник RPP",
        "tutorial_what_is": "Что такое RPP?",
        "tutorial_address": "28-битный Адрес",
        "tutorial_resolver": "Резолвер",
        "tutorial_try_it": "Попробуйте сами",

        # Version
        "version": "версия",
    },
}


def get_text(key: str, lang: str = DEFAULT_LANG) -> str:
    """
    Get translated text for a key.

    Falls back to English if key not found in requested language.
    Falls back to key itself if not found in English either.
    """
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANG

    translations = TRANSLATIONS[lang]
    if key in translations:
        return translations[key]

    # Fallback to English
    if lang != DEFAULT_LANG and key in TRANSLATIONS[DEFAULT_LANG]:
        return TRANSLATIONS[DEFAULT_LANG][key]

    # Fallback to key itself
    return key


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Alias for get_text - shorter for convenience."""
    return get_text(key, lang)


def get_supported_languages() -> list:
    """Return list of supported language codes."""
    return SUPPORTED_LANGS.copy()


def is_rtl(lang: str) -> bool:
    """Check if language is right-to-left."""
    return lang.startswith("ar")
