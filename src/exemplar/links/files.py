"""Reading a file on disk as text, for every link that reads one."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


# `None` when nothing is at the path; `error` when something is, but it cannot
# be read as UTF-8 text.
def read_text(file: Path, error: type[Exception]) -> str | None:
    try:
        return file.read_text(encoding="utf-8", newline="")
    # A parent that is a file means the path does not exist either.
    except FileNotFoundError, NotADirectoryError:
        return None
    except OSError as cause:
        msg = f"{file}: {cause.strerror}"
        raise error(msg) from cause
    except UnicodeDecodeError as cause:
        msg = f"{file}: not UTF-8 text"
        raise error(msg) from cause
