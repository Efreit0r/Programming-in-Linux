#!/usr/bin/env python3
"""attestation.py — промежуточная аттестация по лекциям 1–4.

Один файл, без интернета и без установки чего-либо:

    python3 attestation.py

Что происходит:
  • спрашивает фамилию, имя и группу;
  • задаёт 12 вопросов по одной минуте на вопрос;
  • на всё — 30 минут, после этого тест закрывается сам;
  • ответ принимается один раз: вернуться и исправить нельзя;
  • результат сохраняется в папку «vk workspace» рядом с запуском.

Выйти из теста нельзя: Ctrl+C, Ctrl+D и закрытие окна означают,
что попытка прервана. Об этом сказано в правилах на первом экране.
"""

import os
import re
import select
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

MINUTES = int(os.environ.get("ATTESTATION_MINUTES", "30"))
PASS_PERCENT = 60
OUT_DIR_NAME = os.environ.get("ATTESTATION_OUT", "vk workspace")

QUESTIONS = [
    # --- Лекция 1. История Linux ---
    {
        "lecture": 1,
        "text": "Что такое ядро операционной системы?",
        "options": [
            "Программа для работы с файлами",
            "Центральная часть ОС, управляющая ресурсами компьютера",
            "Графическая оболочка",
            "Текстовый редактор",
        ],
        "correct": 2,
    },
    {
        "lecture": 1,
        "text": "В каком году вышло первое сообщение Линуса Торвальдса о его системе?",
        "options": ["1985", "1991", "1998", "2004"],
        "correct": 2,
    },
    {
        "lecture": 1,
        "text": "Под какой лицензией распространяется ядро Linux?",
        "options": [
            "Проприетарная лицензия",
            "BSD",
            "GNU General Public License (GPL)",
            "MIT",
        ],
        "correct": 3,
    },
    {
        "lecture": 1,
        "text": "Какой из дистрибутивов основан на Debian?",
        "options": ["Fedora", "Arch Linux", "Ubuntu", "openSUSE"],
        "correct": 3,
    },
    # --- Лекция 2. Командная строка ---
    {
        "lecture": 2,
        "text": "Что делает команда pwd?",
        "options": [
            "Показывает текущий каталог",
            "Создаёт каталог",
            "Удаляет файл",
            "Меняет права доступа",
        ],
        "correct": 1,
    },
    {
        "lecture": 2,
        "text": "Какая команда выводит содержимое каталога?",
        "options": ["cd", "ls", "cat", "mv"],
        "correct": 2,
    },
    {
        "lecture": 2,
        "text": "Что означает «..» в пути к файлу?",
        "options": [
            "Домашний каталог",
            "Текущий каталог",
            "Родительский каталог",
            "Корень файловой системы",
        ],
        "correct": 3,
    },
    {
        "lecture": 2,
        "text": "Какая команда покажет первые строки файла?",
        "options": ["tail", "head", "less", "wc"],
        "correct": 2,
    },
    # --- Лекция 3. Bash ---
    {
        "lecture": 3,
        "text": "Переменная name содержит «Linux User». Что выведет printf '%s\\n' \"$name\"?",
        "options": [
            "Две строки: Linux и User",
            "Одну строку: Linux User",
            "Ошибку",
            "Ничего",
        ],
        "correct": 2,
    },
    {
        "lecture": 3,
        "text": "Что делает команда chmod +x script.sh?",
        "options": [
            "Делает файл исполняемым",
            "Удаляет файл",
            "Копирует файл",
            "Открывает файл в редакторе",
        ],
        "correct": 1,
    },
    {
        "lecture": 3,
        "text": "Какой код возврата означает, что команда выполнилась успешно?",
        "options": ["0", "1", "2", "255"],
        "correct": 1,
    },
    {
        "lecture": 3,
        "text": "Какой поток обозначается номером 2?",
        "options": [
            "Стандартный ввод",
            "Стандартный вывод",
            "Поток ошибок",
            "Файл на диске",
        ],
        "correct": 3,
    },
    # --- Лекция 4. Сборка ---
    {
        "lecture": 4,
        "text": "Что делает команда gcc -c hello.c?",
        "options": [
            "Собирает исполняемый файл",
            "Создаёт объектный файл hello.o",
            "Запускает программу",
            "Проверяет права доступа",
        ],
        "correct": 2,
    },
    {
        "lecture": 4,
        "text": "Что означает ошибка линковщика «undefined reference»?",
        "options": [
            "В коде синтаксическая ошибка",
            "Линковщик не нашёл определение функции",
            "Не хватает прав на файл",
            "Компилятор не установлен",
        ],
        "correct": 2,
    },
    {
        "lecture": 4,
        "text": "Что сделает make, если запустить его второй раз без изменений в коде?",
        "options": [
            "Соберёт всё заново",
            "Удалит старые файлы",
            "Ничего не будет делать",
            "Выдаст ошибку",
        ],
        "correct": 3,
    },
    {
        "lecture": 4,
        "text": "Какой этап сборки подставляет содержимое #include?",
        "options": ["Препроцессор", "Компилятор", "Ассемблер", "Линковщик"],
        "correct": 1,
    },
]

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def have_colors():
    """Цвета только если вывод идёт в терминал."""
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def color(text, code):
    return f"{code}{text}{RESET}" if have_colors() else text


def clear():
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def rule():
    cols = 68
    print("─" * cols)


def safe_name(text, limit=40):
    """Привести строку к виду, пригодному для имени файла."""
    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^\w\-]", "", text, flags=re.UNICODE)
    return (text or "student")[:limit]


class Aborted(Exception):
    """Пользователь прервал тест (Ctrl+C, Ctrl+D, сигнал)."""


class TimeUp(Exception):
    """Время вышло, пока студент думал над вопросом."""


def _on_sigint(signum, frame):
    raise Aborted("прерывание с клавиатуры (Ctrl+C)")


def _on_sigterm(signum, frame):
    raise Aborted("закрытие терминала или сигнал завершения")


def _on_sigtstp(signum, frame):
    """Ctrl+Z не должен останавливать тест на полпути."""
    print(color("\nОстановить тест нельзя: продолжаем.", YELLOW))


def ask(prompt, deadline=None):
    """Прочитать строку. Если задан deadline — не ждать дольше него."""
    sys.stdout.write(prompt)
    sys.stdout.flush()

    if deadline is None:
        try:
            return input()
        except EOFError:
            raise Aborted("закрыт ввод (Ctrl+D)")

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeUp()

    # select ждёт ввода не дольше, чем осталось времени.
    ready, _, _ = select.select([sys.stdin], [], [], remaining)
    if not ready:
        print()
        raise TimeUp()

    line = sys.stdin.readline()
    if line == "":
        raise Aborted("закрыт ввод (Ctrl+D)")
    return line.rstrip("\n")


# ---------------------------------------------------------------------------
# Тест
# ---------------------------------------------------------------------------

def intro():
    clear()
    rule()
    print(color("  ПРОМЕЖУТОЧНАЯ АТТЕСТАЦИЯ · ПРОГРАММИРОВАНИЕ В LINUX", BOLD))
    print("  Лекции 1–4: история Linux, командная строка, Bash, сборка")
    rule()
    print()
    print(f"  Вопросов: {len(QUESTIONS)}")
    print(f"  Время:    {MINUTES} минут на всё")
    print(f"  Порог:    {PASS_PERCENT}% правильных ответов")
    print()
    print("  Правила:")
    print("   • ответ принимается один раз — вернуться нельзя;")
    print("   • подсказок и повторного показа вопроса нет;")
    print("   • выход из теста означает, что попытка прервана;")
    print("   • после последнего вопроса тест закроется сам.")
    print()
    rule()
    print()


def ask_student():
    print("Представьтесь, чтобы результат попал в ведомость.\n")
    while True:
        full_name = ask("Фамилия и имя: ").strip()
        if len(full_name) >= 3:
            break
        print(color("  Нужно хотя бы 3 символа. Попробуйте ещё раз.", YELLOW))
    while True:
        group = ask("Группа: ").strip()
        if group:
            break
        print(color("  Укажите группу.", YELLOW))
    return full_name, group


def show_question(number, total, question, remaining):
    clear()
    rule()
    mins, secs = divmod(max(0, int(remaining)), 60)
    print(f"  Вопрос {number} из {total}"
          f"   {DIM if have_colors() else ''}осталось {mins:02d}:{secs:02d}{RESET if have_colors() else ''}"
          f"   {color('лекция ' + str(question['lecture']), DIM)}")
    rule()
    print()
    print(f"  {question['text']}")
    print()
    for i, option in enumerate(question["options"], start=1):
        print(f"   {i}) {option}")
    print()


def ask_answer(count, deadline):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeUp()
        mins, secs = divmod(int(remaining), 60)
        raw = ask(f"  Ответ (1–{count})  [{mins:02d}:{secs:02d}]: ", deadline).strip()
        if raw.isdigit() and 1 <= int(raw) <= count:
            return int(raw)
        print(color(f"  Нужно число от 1 до {count}.", YELLOW))


def run_test(full_name, group, deadline):
    answers = []
    locked = set()

    for number, question in enumerate(QUESTIONS, start=1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return answers, "время вышло"

        if 0 < remaining <= 60 and number > 1:
            show_question(number, len(QUESTIONS), question, remaining)
            print(color("  Осталась последняя минута.", YELLOW))
            print()
        else:
            show_question(number, len(QUESTIONS), question, remaining)

        choice = ask_answer(len(question["options"]), deadline)

        # Ответ фиксируется сразу: правок после этого нет.
        answers.append(choice)
        locked.add(number)

        if remaining < 15 and number < len(QUESTIONS):
            print(color("\n  До конца теста меньше 15 секунд.", YELLOW))

    return answers, "тест завершён"


def score(answers):
    points = 0
    for answer, question in zip(answers, QUESTIONS):
        if answer == question["correct"]:
            points += 1
    percent = round(points * 100 / len(QUESTIONS))
    return points, percent


def save_result(full_name, group, answers, reason, points, percent, started):
    out_dir = Path(OUT_DIR_NAME).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = started.strftime("%Y-%m-%d_%H-%M")
    filename = f"{safe_name(full_name)}_{safe_name(group)}_{stamp}.txt"
    path = out_dir / filename

    verdict = "зачтено" if percent >= PASS_PERCENT else "не зачтено"

    lines = [
        "Промежуточная аттестация · Программирование в Linux",
        "Лекции 1–4: история Linux, командная строка, Bash, сборка",
        "",
        f"Студент:      {full_name}",
        f"Группа:       {group}",
        f"Начало:       {started.strftime('%d.%m.%Y %H:%M:%S')}",
        f"Завершение:   {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        f"Итог теста:   {reason}",
        "",
        f"Правильных:   {points} из {len(QUESTIONS)}",
        f"Процент:      {percent}%",
        f"Оценка:       {verdict}",
        "",
        "Ответы:",
    ]

    for number, question in enumerate(QUESTIONS, start=1):
        if number <= len(answers):
            given = answers[number - 1]
            mark = "верно" if given == question["correct"] else "неверно"
            text = question["options"][given - 1]
            lines.append(f"  {number:2d}. {text} — {mark}")
        else:
            lines.append(f"  {number:2d}. — нет ответа (тест прерван)")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path, verdict


def finish(full_name, group, answers, reason, started):
    points, percent = score(answers)
    path, verdict = save_result(
        full_name, group, answers, reason, points, percent, started
    )

    clear()
    rule()
    print(color("  ТЕСТ ЗАКРЫТ", BOLD))
    rule()
    print()
    print(f"  {full_name}, группа {group}")
    print()
    print(f"  Правильных ответов: {points} из {len(QUESTIONS)}  ({percent}%)")
    mark = color("зачтено", GREEN) if verdict == "зачтено" else color("не зачтено", RED)
    print(f"  Оценка: {mark}")
    print()
    print(f"  Результат сохранён: {path}")
    print(f"  Передайте этот файл преподавателю (папка «{OUT_DIR_NAME}»).")
    print()
    print(color("  Изменить ответы уже нельзя.", DIM))
    print()


def main():
    signal.signal(signal.SIGINT, _on_sigint)
    signal.signal(signal.SIGTERM, _on_sigterm)
    if hasattr(signal, "SIGTSTP"):
        signal.signal(signal.SIGTSTP, _on_sigtstp)

    started = datetime.now()

    intro()

    # Пока студент вводит имя, время ещё не идёт.
    try:
        full_name, group = ask_student()
    except (Aborted, KeyboardInterrupt) as exc:
        clear()
        print(f"\nТест прерван до начала: {exc}")
        print("Результат не сохранён. Запустите тест заново.")
        return 2

    # Отсчёт начинается после того, как студент представился.
    deadline = time.monotonic() + MINUTES * 60

    answers = []
    reason = "тест завершён"
    try:
        answers, reason = run_test(full_name, group, deadline)
    except Aborted as exc:
        reason = f"прервано: {exc}"
    except TimeUp:
        reason = "время вышло"
    except KeyboardInterrupt:
        reason = "прервано: Ctrl+C"
    finally:
        finish(full_name, group, answers, reason, started)


if __name__ == "__main__":
    main()
