# core/base.py
class Language:
    """Базовый класс для всех языков."""
    name = ""            # id: 'python', 'bf'
    title = ""           # Отображаемое имя: 'Python', 'Brainfuck'
    category = "О"       # 'О' или 'И'
    ext = ".txt"         # расширение
    keywords = []        # для подсветки
    types = []           # для подсветки
    comment_regex = None # regex для комментариев
    templates = {}       # {"[1] ...": "код"}

    def execute(self, src: str):
        """Выполнить код, вернуть вывод или None."""
        return None

    def generate_code(self, output: str):
        """Сгенерировать код на этом языке, печатающий output."""
        return None