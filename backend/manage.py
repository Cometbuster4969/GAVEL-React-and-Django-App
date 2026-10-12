import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calendar_backend.settings")
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.stderr.write(
            "Refusing to run tests against the application database.\n"
            "Use `bun test` from the repository root. That command creates a\n"
            "throwaway gavel_test_* database, runs the suite, and drops it.\n"
        )
        sys.exit(2)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
