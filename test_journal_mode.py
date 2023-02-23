"""Test the behavior of setting sqlite's "journal_mode" pragma."""
import sqlite3
import sys
import uuid


def new_db_path():
    return f"/tmp/test_journal_mode_sqlite.{uuid.uuid4()}"


def populate_dummy_schema(con):
    con.execute("create table dummy (message text)")
    con.execute("insert into dummy (message) values (?)", ("hello",))
    con.execute("insert into dummy (message) values (?)", ("world",))


def current_journal_mode(con):
    return con.execute("pragma journal_mode").fetchone()[0]


def error(message):
    print(f'\033[1m\033[91m!!! WARNING: {message}\033[0m', file=sys.stderr)


def journal_mode_off_reuse_connection_without_cursor_close(desired_mode):
    """Set journal_mode and check it without closing the cursor (should keep desired mode)."""
    print(journal_mode_off_reuse_connection_without_cursor_close.__doc__)
    with sqlite3.connect(new_db_path()) as con:
        print(f"journal_mode before: {current_journal_mode(con)}")
        con.execute(f"pragma journal_mode={desired_mode}")
        mode = current_journal_mode(con)
        print(f"journal_mode after: {mode}")
        if mode != desired_mode:
            error(f'"{mode}" is not "{desired_mode}"')
            print("sqlite's pragma compile_options are:")
            print(list(con.execute("pragma compile_options")))


def journal_mode_off_reuse_connection_after_cursor_close(desired_mode):
    """Set journal_mode and check after closing the cursor (should keep desired mode)."""
    print(journal_mode_off_reuse_connection_after_cursor_close.__doc__)
    with sqlite3.connect(new_db_path()) as con:
        print(f"journal_mode before: {current_journal_mode(con)}")
        con.execute(f"pragma journal_mode={desired_mode}").close()
        mode = current_journal_mode(con)
        print(f"journal_mode after: {mode}")
        if mode != desired_mode:
            error(f'"{mode}" is not "{desired_mode}"')
            print("sqlite's pragma compile_options are:")
            print(list(con.execute("pragma compile_options")))


def journal_mode_off_with_new_connection(desired_mode):
    """Set journal_mode, close connection, and check with a connection (should revert to default)."""
    print(journal_mode_off_with_new_connection.__doc__)
    db_path = new_db_path()
    with sqlite3.connect(db_path) as con:
        default_mode = current_journal_mode(con)
        print(f"journal_mode before: {default_mode}")
        con.execute(f"pragma journal_mode={desired_mode}")
    with sqlite3.connect(db_path) as con:
        mode = current_journal_mode(con)
        print(f"journal_mode after: {mode}")
        if mode != default_mode:
            error(f'"{mode}" is not "{default_mode}"')
            print("sqlite's pragma compile_options are:")
            print(list(con.execute("pragma compile_options")))



if __name__ == "__main__":
    desired_mode = sys.argv[1]

    print('#' * 10)
    print(sys.executable)
    print(f"Python {sys.version} on {sys.platform}")
    print(f"Sqlite {sqlite3.sqlite_version}")
    print('-' * 10)
    journal_mode_off_reuse_connection_without_cursor_close(desired_mode)
    print('-' * 10)
    journal_mode_off_reuse_connection_after_cursor_close(desired_mode)
    print('-' * 10)
    journal_mode_off_with_new_connection(desired_mode)
