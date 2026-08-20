#!/usr/bin/env python3
"""Проверка русского текста на форменные признаки AI-текста. Только предупреждает, не правит."""

from __future__ import annotations

import argparse
import collections
import re
import sys
from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_DASHES = {
    "—": "длинное тире (—)",
    "–": "среднее тире (–)",
}

# Минус (−, U+2212) в такие цифрах как «−30» не тире, не трогаем его.

_IC = re.IGNORECASE

REVERSAL_PATTERNS = (
    re.compile(r"\bне\s+[^.!?\n,]{1,60},\s*а\s+", _IC),
    re.compile(r"\bне\s+про\s+[^.!?\n]{1,40}(?:,\s*)?(?:это|а)\s+про\s+", _IC),
    re.compile(r"\bдело\s+не\s+в\s+[^.!?\n]{1,40},\s*а\s+в\s+", _IC),
    # Точка (.) внутри намеренно ловится обычным «.» (без re.DOTALL): по умолчанию
    # «.» не матчит перенос строки, значит паттерн пересекает конец предложения
    # внутри абзаца (разбитый на два предложения вариант того же хода), но не
    # перескакивает через границу абзаца на несвязанный текст.
    re.compile(r"\bказалось\s+бы\b.{1,90}?(?:на\s+деле|на\s+самом\s+деле)", _IC),
    re.compile(r"\bс\s+виду\b.{1,80}?по\s+факту", _IC),
    re.compile(r"\b(?:ты\s+дума(?:ешь|л)|думаешь)\b.{1,80}?на\s+самом\s+деле", _IC),
    re.compile(r"\bоказывается,", _IC),
    re.compile(r"\bесли\s+приглядеться\b", _IC),
    re.compile(r"\bответ\s+прост[а-я]*\s*:?\s*не\s+", _IC),
    re.compile(r"[^.!?\n]{1,30}не\s+так\s+важ[а-я]*,\s*как\s+", _IC),
)

ROAD_SIGNS = (
    "стоит отметить",
    "важно отметить",
    "важно понимать",
    "необходимо учитывать",
    "нельзя не отметить",
    "следует подчеркнуть",
    "на самом деле",
    "по сути",
    "в принципе",
    "как известно",
    "не секрет что",
    "в свою очередь",
    "таким образом",
)

CONNECTORS = (
    "но",
    "однако",
    "при этом",
    "вместе с тем",
    "кроме того",
    "более того",
    "тем не менее",
    "в то же время",
    "таким образом",
    "в результате",
    "следовательно",
    "соответственно",
    "поэтому",
    "вследствие",
    "в связи с этим",
)

REPEATED_OPENERS = (
    "кстати",
    "итак",
    "однако",
    "впрочем",
    "конечно",
    "наконец",
    "в общем",
    "по сути",
    "на самом деле",
    "стоит сказать",
)


# Значения ниже это основы слов, не словарные формы: русский язык склоняет и
# спрягает, поэтому «полка» не находит «полке», а «передовая» не находит
# «передовую». Основа подобрана так, чтобы захватывать падежи и число, но
# оставаться достаточно длинной и избегать частых случайных совпадений
# (например «полк» вместо «полка» ловил бы «полковника» — вместо этого ниже
# перечислены конкретные падежные формы).
METAPHOR_FIELDS = {
    "температура": ("накал", "остыва", "остыл", "разогре", "греет", "горячая тем"),
    "война": ("передов", "поле боя", "битв", "атаку", "атакует", "фронт", "штурм", "сражени", "на баррикадах"),
    "стройка/разрушение": ("фундамент", "руш", "рухну", "трещи", "обвал", "пошатну"),
    "склад": ("полка", "полке", "полки", "полку", "полок", "хранилищ", "склад", "запас", "залежи", "загашник"),
    "гонка": ("обгоня", "финиш", "стартов", "гонк"),
    "механизм/организм": ("шестерён", "шестерен", "мотор", "пульс", "двигател", "кровь проекта"),
    "море": ("волн", "прилив", "маяк", "гаван", "шторм", "штил", "якор"),
}


@dataclass
class Paragraph:
    position: int
    text: str
    words: int
    sentences: int


def word_count(text: str) -> int:
    return len(re.findall(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?", text))


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def excerpt(value: str, width: int = 80) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= width else value[: width - 1] + "…"


def mask_non_prose(text: str) -> str:
    """Прячет код, ссылки и служебные блоки, сохраняя позиции символов и переносы строк."""

    def mask(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group())

    patterns = (
        re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.DOTALL),
        re.compile(r"```.*?```", re.DOTALL),
        re.compile(r"`[^`\n]*`"),
        re.compile(r"\]\([^\n)]*\)"),
        re.compile(r"https?://[^\s)>]+"),
        re.compile(r"<[^>\n]+>"),
    )
    masked = text
    for pattern in patterns:
        masked = pattern.sub(mask, masked)
    return masked


def non_overlapping_terms(text: str, terms: tuple[str, ...]):
    lowered = text.lower()
    matches = []
    occupied = []
    for term in sorted(terms, key=len, reverse=True):
        for match in re.finditer(re.escape(term.lower()), lowered):
            start, end = match.span()
            if any(start < old_end and end > old_start for old_start, old_end in occupied):
                continue
            matches.append((start, term))
            occupied.append((start, end))
    return sorted(matches)


def all_matches(text: str, patterns: tuple[re.Pattern[str], ...]):
    matches = []
    for pattern in patterns:
        matches.extend(pattern.finditer(text))
    return sorted(matches, key=lambda match: match.start())


def sentence_length_cv(text: str):
    """Коэффициент вариации длины предложений в словах. У человека разброс больше."""

    lengths = [
        word_count(match.group())
        for match in re.finditer(r"[^.!?\n]+[.!?]", text)
        if word_count(match.group()) >= 2
    ]
    if len(lengths) < 8:
        return None
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return None
    variance = sum((value - mean) ** 2 for value in lengths) / len(lengths)
    return (variance ** 0.5) / mean, len(lengths)


def prose_paragraphs(text: str) -> list[Paragraph]:
    paragraphs = []
    cursor = 0
    for block in re.split(r"\n\s*\n", text):
        position = text.find(block, cursor)
        cursor = max(position + len(block), cursor)
        clean = re.sub(r"[>*_`#]", "", block).strip()
        if not clean or clean.startswith(("http", "![")):
            continue
        if re.match(r"^(?:[-+*]|\d+[.)])\s", clean):
            continue
        count = word_count(clean)
        if count < 2:
            continue
        sentences = max(1, len(re.findall(r"[.!?]", clean)))
        paragraphs.append(Paragraph(position, clean, count, sentences))
    return paragraphs


def metaphor_cluster(text: str, distance: int = 600):
    hits = []
    lowered = text.lower()
    for field, words in METAPHOR_FIELDS.items():
        for word in words:
            for match in re.finditer(re.escape(word), lowered):
                hits.append((match.start(), field, word))
    hits.sort()
    for index, (start, _, _) in enumerate(hits):
        window = [hit for hit in hits[index:] if hit[0] - start <= distance]
        fields = {hit[1] for hit in window}
        if len(fields) >= 3:
            return window, fields
    return None


def short_streak(paragraphs: list[Paragraph], limit: int = 4):
    streak = []
    for paragraph in paragraphs:
        if paragraph.words <= 18 and paragraph.sentences <= 1:
            streak.append(paragraph)
            if len(streak) >= limit:
                return streak
        else:
            streak = []
    return None


def opener_counts(paragraphs: list[Paragraph]):
    counts = collections.Counter()
    examples = {}
    for paragraph in paragraphs:
        value = paragraph.text.lower().lstrip("“‘\"(")
        for opener in REPEATED_OPENERS:
            if value.startswith(opener):
                counts[opener] += 1
                examples.setdefault(opener, paragraph.position)
                break
    return counts, examples


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка русского текста на форменные признаки AI-текста")
    parser.add_argument("path", help="Путь к Markdown/текстовому файлу. Используй - для стдин")
    args = parser.parse_args()

    try:
        text = read_text(args.path)
    except (OSError, UnicodeError) as error:
        print(f"Не удалось прочитать файл. {error}", file=sys.stderr)
        return 2

    prose = mask_non_prose(text)
    total_words = word_count(prose)
    if total_words == 0:
        print("Русских слов не найдено.", file=sys.stderr)
        return 2

    failures = []
    warnings = []

    for symbol, label in FORBIDDEN_DASHES.items():
        matches = list(re.finditer(re.escape(symbol), prose))
        if matches:
            lines = ", ".join(str(line_number(text, match.start())) for match in matches[:8])
            failures.append(f"{label}: {len(matches)} шт., строки {lines}.")

    reversals = all_matches(prose, REVERSAL_PATTERNS)
    for match in reversals[:8]:
        failures.append(
            f"переворотная риторика, строка {line_number(text, match.start())}: "
            f"«{excerpt(match.group())}»"
        )

    road_hits = non_overlapping_terms(prose, ROAD_SIGNS)
    if road_hits:
        lines = ", ".join(dict.fromkeys(str(line_number(text, pos)) for pos, _ in road_hits[:8]))
        samples = ", ".join(dict.fromkeys(term for _, term in road_hits))
        warnings.append(f"словесная вода/путевые знаки, {len(road_hits)} шт., строки {lines}: {samples}.")

    connector_hits = non_overlapping_terms(prose, CONNECTORS)
    if total_words >= 300:
        density = len(connector_hits) * 1000 / total_words
        if density > 12:
            top = ", ".join(
                f"«{term}» {count} раз" for term, count in collections.Counter(t for _, t in connector_hits).most_common(4)
            )
            warnings.append(
                f"высокая плотность союзов-связок: {density:.0f} на 1000 слов. {top}. "
                "Русская речь чаще связывает предложения порядком слов и смыслом, а не союзом на каждом стыке."
            )

    cv_result = sentence_length_cv(prose)
    if cv_result and cv_result[0] < 0.40:
        warnings.append(
            f"{cv_result[1]} предложений, коэффициент вариации длины {cv_result[0]:.2f} (ниже 0.40). "
            "Предложения слишком одинаковы по длине, это ровный машинный ритм. Добавь коротких и длинных вперемешку."
        )

    paragraphs = prose_paragraphs(prose)
    streak = short_streak(paragraphs)
    if streak:
        first = streak[0]
        warnings.append(
            f"с строки {line_number(text, first.position)} подряд идут {len(streak)} коротких однострочных абзаца. "
            "Проверь, не строится ли текст как барабанная дробь коротких выводов."
        )

    if len(paragraphs) >= 8:
        one_sentence = sum(paragraph.sentences <= 1 for paragraph in paragraphs)
        ratio = one_sentence / len(paragraphs)
        if ratio >= 0.7:
            warnings.append(f"{ratio:.0%} абзацев состоят из одного предложения. Слишком единообразная структура.")

    counts, examples = opener_counts(paragraphs)
    repeated = [(opener, count) for opener, count in counts.items() if count >= 4]
    if repeated:
        details = ", ".join(f"«{opener}» {count} раз" for opener, count in repeated)
        first_position = min(examples[opener] for opener, _ in repeated)
        warnings.append(f"повторяющиеся зачины абзацев примерно от строки {line_number(text, first_position)}: {details}.")

    metaphors = metaphor_cluster(prose)
    if metaphors:
        window, fields = metaphors
        samples = ", ".join(dict.fromkeys(hit[2] for hit in window))
        warnings.append(
            f"в пределах ~600 символов встретились {len(fields)} метафорических поля: {', '.join(sorted(fields))}. "
            f"Слова: {samples}. Похоже на подбор готовых образов вместо прямого описания."
        )

    print(f"Слов: {total_words}")
    print(
        f"Переворотная риторика: {len(reversals)}. Тире: "
        f"{sum(len(list(re.finditer(re.escape(s), prose))) for s in FORBIDDEN_DASHES)}. "
        f"Путевые знаки: {len(road_hits)}. Метафорических кластеров: {1 if metaphors else 0}."
    )

    if failures:
        print("\nНужно исправить:")
        for item in failures:
            print(f"- {item}")

    if warnings:
        print("\nНа ручную проверку:")
        for item in warnings:
            print(f"- {item}")

    if not failures and not warnings:
        print("\nПроблем из этого чек-листа не найдено.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
