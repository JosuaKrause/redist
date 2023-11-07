"""
This module contains various useful functions. The functions in this module are
not necessarily be considered part of the package API and might change or
disappear in the future. Use with caution outside of the package internals.
"""
import datetime
import hashlib
import inspect
import json
import os
import re
import string
import threading
import uuid
from collections.abc import Callable, Iterable
from typing import Any, IO, overload, TypeVar

import pytz


ET = TypeVar('ET')
CT = TypeVar('CT')
RT = TypeVar('RT')
VT = TypeVar('VT')


NL = "\n"


TEST_SALT_LOCK = threading.RLock()
TEST_SALT: dict[str, str] = {}


def is_test() -> bool:
    """
    Whether we are currently running a test with pytest.

    Returns:
        bool: Whether the current execution environment is within a pytest.
    """
    test_id = os.getenv("PYTEST_CURRENT_TEST")
    return test_id is not None


def get_test_salt() -> str | None:
    """
    Creates a unique salt to be used as redis key prefix for unit tests.

    Returns:
        str | None: A unique prefix for the current test. None if we are not
        running inside a pytest environment.
    """
    test_id = os.getenv("PYTEST_CURRENT_TEST")
    if test_id is None:
        return None
    res = TEST_SALT.get(test_id)
    if res is None:
        with TEST_SALT_LOCK:
            res = TEST_SALT.get(test_id)
            if res is None:
                res = f"salt:{uuid.uuid4().hex}"
                TEST_SALT[test_id] = res
    return res


def indent(text: str, amount: int = 0) -> list[str]:
    """
    Breaks a string into lines and indents each line by a set amount.

    Args:
        text (str): The text to break into lines.
        amount (int, optional): The indentation amount. Defaults to 0.

    Returns:
        list[str]: The indented lines.
    """
    istr = " " * amount
    return [
        f"{istr}{line}" for line in text.splitlines()
    ]


def deindent(text: str) -> str:
    """
    Removes a fixed amount of whitespace in front of each line. The amount is
    the maximum length of whitespace that is present on every line. The first
    line and empty lines are treated specially to result in a pleasing output.

    Args:
        text (str): The text to deindent.

    Returns:
        str: The deindented text.
    """
    min_indent = None
    lines = text.rstrip().splitlines()
    if lines and not lines[0]:
        lines.pop(0)
    for line in lines:
        if not line.strip():
            continue
        cur_indent = len(line) - len(line.lstrip())
        if min_indent is None or min_indent > cur_indent:
            min_indent = cur_indent
            if min_indent == 0:
                break
    return "".join((f"{line[min_indent:]}\n" for line in lines))


def lua_fmt(text: str) -> str:
    """
    Formats a multi-line string by deindenting and changing the indent size
    from 4 to 2.

    Args:
        text (str): The multi-line string.

    Returns:
        str: A deindented 2-space indented string.
    """
    return deindent(text).replace("    ", "  ")


def code_fmt(lines: list[str]) -> str:
    """
    Joins a list of lines.

    Args:
        lines (list[str]): The list of lines.

    Returns:
        str: The output as single string.
    """
    return "".join(f"{line.rstrip()}\n" for line in lines)


def get_text_hash(text: str) -> str:
    """
    Computes the blake2b hash of the given string.

    Args:
        text (str): The string.

    Returns:
        str: The hash of length text_hash_size.
    """
    blake = hashlib.blake2b(digest_size=32)
    blake.update(text.encode("utf-8"))
    return blake.hexdigest()


def text_hash_size() -> int:
    """
    The length of the hash produced by get_text_hash.

    Returns:
        int: The length of the hash.
    """
    return 64


def get_short_hash(text: str) -> str:
    """
    Computes a short blake2b hash of the given string.

    Args:
        text (str): The string.

    Returns:
        str: The hash of length short_hash_size.
    """
    blake = hashlib.blake2b(digest_size=4)
    blake.update(text.encode("utf-8"))
    return blake.hexdigest()


def short_hash_size() -> int:
    """
    The length of the hash produced by get_short_hash.

    Returns:
        int: The length of the hash.
    """
    return 8


BUFF_SIZE = 65536  # 64KiB
"""
The buffer size used to compute file hashes.
"""


def get_file_hash(fname: str) -> str:
    """
    Computes the blake2b hash of the given file's content.

    Args:
        fname (str): The filename.

    Returns:
        str: The hash of length file_hash_size.
    """
    blake = hashlib.blake2b(digest_size=32)
    with open(fname, "rb") as fin:
        while True:
            buff = fin.read(BUFF_SIZE)
            if not buff:
                break
            blake.update(buff)
    return blake.hexdigest()


def file_hash_size() -> int:
    """
    The length of the hash produced by get_file_hash.

    Returns:
        int: The length of the hash.
    """
    return 64


def is_hex(text: str) -> bool:
    """
    Whether the string represents a hexadecimal value.

    Args:
        text (str): The string to inspect.

    Returns:
        bool: Whether the string represents a hex value.
    """
    hex_digits = set(string.hexdigits)
    return all(char in hex_digits for char in text)


def only(arr: list[RT]) -> RT:
    """
    Extracts the only item of a single item list.

    Args:
        arr (list[RT]): The single item list.

    Raises:
        ValueError: If the length of the list is not 1.

    Returns:
        RT: The single item.
    """
    if len(arr) != 1:
        raise ValueError(f"array must have exactly one element: {arr}")
    return arr[0]


# time units for logging request durations
ELAPSED_UNITS: list[tuple[int, str]] = [
    (1, "s"),
    (60, "m"),
    (60*60, "h"),
    (60*60*24, "d"),
]
"""Unit conversions for time durations."""


def elapsed_time_string(elapsed: float) -> str:
    """Convert elapsed time into a readable string."""
    cur = ""
    for (conv, unit) in ELAPSED_UNITS:
        if elapsed / conv >= 1 or not cur:
            cur = f"{elapsed / conv:8.3f}{unit}"
        else:
            break
    return cur


def now() -> datetime.datetime:
    """
    Returns a timestamp representing now.

    Returns:
        datetime.datetime: The timestamp representing now.
    """
    return datetime.datetime.now(datetime.timezone.utc).astimezone()


def fmt_time(when: datetime.datetime) -> str:
    """
    Format a timestamp.

    Args:
        when (datetime.datetime): The timestamp.

    Returns:
        str: The formatted time.
    """
    return when.isoformat()


def get_time_str() -> str:
    """
    Formatted now.

    Returns:
        str: Formatted now.
    """
    return fmt_time(now())


def parse_time_str(time_str: str) -> datetime.datetime:
    """
    Parses a timestamp formatted via fmt_time.

    Args:
        time_str (str): The time as string.

    Returns:
        datetime.datetime: A timestamp.
    """
    return datetime.datetime.fromisoformat(time_str)


def time_diff(
        from_time: datetime.datetime, to_time: datetime.datetime) -> float:
    return (to_time - from_time).total_seconds()


def to_bool(value: bool | float | int | str) -> bool:
    value = f"{value}".lower()
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return bool(int(float(value)))
    except ValueError:
        pass
    raise ValueError(f"{value} cannot be interpreted as bool")


def to_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{value} is not a list")
    return value


def is_int(value: Any) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_float(value: Any) -> bool:
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_json(value: str) -> bool:
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True


def report_json_error(err: json.JSONDecodeError) -> None:
    raise ValueError(
        f"JSON parse error ({err.lineno}:{err.colno}): "
        f"{repr(err.doc)}") from err


def json_maybe_read(data: str) -> Any | None:
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def json_load(fin: IO[str]) -> Any:
    try:
        return json.load(fin)
    except json.JSONDecodeError as e:
        report_json_error(e)
        raise e


def json_dump(obj: Any, fout: IO[str]) -> None:
    print(json_pretty(obj), file=fout)


def json_pretty(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2)


def json_compact(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        indent=None,
        separators=(",", ":")).encode("utf-8")


def json_read(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        report_json_error(e)
        raise e


def read_jsonl(fin: IO[str]) -> Iterable[Any]:
    for line in fin:
        line = line.rstrip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as e:
            report_json_error(e)
            raise e


def from_timestamp(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, pytz.utc)


def to_timestamp(time: datetime.datetime) -> float:
    return time.timestamp()


def now_ts() -> datetime.datetime:
    return datetime.datetime.now(pytz.utc)


def get_function_info(*, clazz: type) -> tuple[str, int, str]:
    stack = inspect.stack()

    def get_method(cur_clazz: type) -> tuple[str, int, str] | None:
        class_filename = inspect.getfile(cur_clazz)
        for level in stack:
            if os.path.samefile(level.filename, class_filename):
                return level.filename, level.lineno, level.function
        return None

    queue = [clazz]
    while queue:
        cur = queue.pop(0)
        res = get_method(cur)
        if res is not None:
            return res
        queue.extend(cur.__bases__)
    frame = stack[1]
    return frame.filename, frame.lineno, frame.function


def get_relative_function_info(
        depth: int) -> tuple[str, int, str, dict[str, Any]]:
    depth += 1
    stack = inspect.stack()
    if depth >= len(stack):
        return "unknown", -1, "unknown", {}
    frame = stack[depth]
    return frame.filename, frame.lineno, frame.function, frame.frame.f_locals


def identity(obj: RT) -> RT:
    return obj


NUMBER_PATTERN = re.compile(r"\d+")


def extract_list(
        arr: Iterable[str],
        prefix: str | None = None,
        postfix: str | None = None) -> Iterable[tuple[str, str]]:
    if not arr:
        yield from []
        return

    for elem in arr:
        text = elem
        if prefix is not None:
            if not text.startswith(prefix):
                continue
            text = text[len(prefix):]
        if postfix is not None:
            if not text.endswith(postfix):
                continue
            text = text[:-len(postfix)]
        yield (elem, text)


def extract_number(
        arr: Iterable[str],
        prefix: str | None = None,
        postfix: str | None = None) -> Iterable[tuple[str, int]]:

    def get_num(text: str) -> int | None:
        match = re.search(NUMBER_PATTERN, text)
        if match is None:
            return None
        try:
            return int(match.group())
        except ValueError:
            return None

    for elem, text in extract_list(arr, prefix=prefix, postfix=postfix):
        num = get_num(text)
        if num is None:
            continue
        yield elem, num


def highest_number(
        arr: Iterable[str],
        prefix: str | None = None,
        postfix: str | None = None) -> tuple[str, int] | None:
    res = None
    res_num = 0
    for elem, num in extract_number(arr, prefix=prefix, postfix=postfix):
        if res is None or num > res_num:
            res = elem
            res_num = num
    return None if res is None else (res, res_num)


def retain_some(
        arr: Iterable[VT],
        count: int,
        *,
        key: Callable[[VT], Any],
        reverse: bool = False,
        keep_last: bool = True) -> tuple[list[VT], list[VT]]:
    res: list[VT] = []
    to_delete: list[VT] = []
    if keep_last:
        for elem in arr:
            if len(res) <= count:
                res.append(elem)
                continue
            res.sort(key=key, reverse=reverse)
            to_delete.extend(res[:-count])
            res = res[-count:]
            res.append(elem)
    else:
        for elem in arr:
            res.append(elem)
            if len(res) < count:
                continue
            res.sort(key=key, reverse=reverse)
            to_delete.extend(res[:-count])
            res = res[-count:]
    res.sort(key=key, reverse=reverse)
    return res, to_delete


def python_module() -> str:
    stack = inspect.stack()
    module = inspect.getmodule(stack[1][0])
    if module is None:
        raise ValueError("module not found")
    res = module.__name__
    if res != "__main__":
        return res
    package = module.__package__
    if package is None:
        package = ""
    mfname = module.__file__
    if mfname is None:
        return package
    fname = os.path.basename(mfname)
    fname = fname.removesuffix(".py")
    if fname in ("__init__", "__main__"):
        return package
    return f"{package}.{fname}"


def parent_python_module(p_module: str) -> str:
    dot_ix = p_module.rfind(".")
    if dot_ix < 0:
        return ""
    return p_module[:dot_ix]


def check_pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ideal_thread_count() -> int:
    res = os.cpu_count()
    if res is None:
        return 4
    return res


def escape(text: str, subs: dict[str, str]) -> str:
    text = text.replace("\\", "\\\\")
    for key, repl in subs.items():
        text = text.replace(key, f"\\{repl}")
    return text


def unescape(text: str, subs: dict[str, str]) -> str:
    res: list[str] = []
    in_escape = False
    for c in text:
        if in_escape:
            in_escape = False
            if c == "\\":
                res.append("\\")
                continue
            done = False
            for key, repl in subs.items():
                if c == key:
                    res.append(repl)
                    done = True
                    break
            if done:
                continue
        if c == "\\":
            in_escape = True
            continue
        res.append(c)
    return "".join(res)


@overload
def to_maybe_str(res: bytes) -> str:
    ...


@overload
def to_maybe_str(res: None) -> None:
    ...


def to_maybe_str(res: bytes | None) -> str | None:
    if res is None:
        return res
    return res.decode("utf-8")


@overload
def to_list_str(res: Iterable[bytes]) -> list[str]:
    ...


@overload
def to_list_str(res: None) -> None:
    ...


def to_list_str(res: Iterable[bytes] | None) -> list[str] | None:
    if res is None:
        return res
    return [val.decode("utf-8") for val in res]


def normalize_values(res: Any) -> Any:
    if res is None:
        return None
    if isinstance(res, bytes):
        return res.decode("utf-8")
    if isinstance(res, list):
        return [normalize_values(val) for val in res]
    if isinstance(res, tuple):
        return tuple(normalize_values(val) for val in res)
    if isinstance(res, dict):
        return {
            normalize_values(key): normalize_values(value)
            for key, value in res.items()
        }
    return res
