import os
import sys

def main():
    """Запуск команды Django из командной строки."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедись, что оно установлено в виртуальном окружении."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()