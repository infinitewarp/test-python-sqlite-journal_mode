# Summary

Some versions of Python+SQLite ignore `PRAGMA journal_mode=off`. This means that SQLite may continue to operate in its default `journal_mode=delete` mode which can result in a `-journal` file _temporarily_ being written alongside a SQLite database file. The existence of these additional short-lived `-journal` files can cause problems for `coverage`.

This repo documents my investigation into problems that arise with `coverage` when SQLite ignores `PRAGMA journal_mode=off`.

## Why would SQLite ignore `journal_mode=off`?

This one is a mystery to me. SQLite [documentation suggests the `SQLITE_DBCONFIG_DEFENSIVE` compile-time option](https://sqlite.org/c3ref/c_dbconfig_defensive.html#sqlitedbconfigdefensive) may be to blame because it disables the `PRAGMA journal_mode=OFF` statement, but I could find no direct evidence of that option being set. Supposedly you can see all relevant options with `PRAGMA compile_options`, but I've yet to see `SQLITE_DBCONFIG_DEFENSIVE` in its output. :shrug:

## How does this hurt coverage?

`coverage` internally uses SQLite to record its coverage data. Typically this results in one `.coverage` SQLite database file in the working directory, but when running tests in parallel, many smaller `.coverage.*` SQLite database files also exist, effectively collecing data separately for each process.  Near the end of processing, `coverage` naively globs for all `.coverage.*` files (see [`combinable_files`](https://github.com/nedbat/coverage/blob/b059a67fd1fe5d514f7c283f5ab99052e1cea15f/coverage/data.py#L66)) in the working directory and attempts to combine them into one file (see [`combine_parallel_data`](https://github.com/nedbat/coverage/blob/b059a67fd1fe5d514f7c283f5ab99052e1cea15f/coverage/data.py#L89)), optionally deleting those smaller files once they've been read and combined into the larger file.

`coverage` _attempts_ to disable the SQLite journal files at startup by executing `PRAGMA journal_mode=off`. If SQLite ignores that command, though, SQLite may write `-journal` files and they _may_ still be present when `coverage` combines parallel data, and it may _**crash**_ `combine_parallel_data`.

SQLite's `-journal` files are deleted by default, but it's unclear how often changes are actually syned to disk. [3.5. Creating A Rollback Journal File](https://www.sqlite.org/atomiccommit.html#section_3_5) suggests it's unpredictable due to outside factors like the operating system and its various caches and buffers. Regardless, my real-world observations have repeatedly shown that _sometimes_ `-journal` files still exist when `coverage` calls `combinable_files` and `combine_parallel_data`.

If a `-journal` file was present at both `combinable_files` and `combine_parallel_data`, `coverage` may report an error like:

```
CoverageWarning: Data file '/path/to/cwd/.coverage.localhost.92493.872556' doesn't seem to be a coverage data file
...
CoverageWarning: Data file '/path/to/cwd/.coverage.localhost.92515.710572' doesn't seem to be a coverage data file
...
CoverageWarning: Couldn't use data file '/path/to/cwd/.coverage.localhost.63019.998061-journal': file is not a database
```

If a `-journal` file was identified by `combinable_files` but no longer exists when `combine_parallel_data` runs, `coverage` may _**crash**_ due to an unhandled exception like:

```
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/cwd/.coverage.localhost.92515.710572-journal'
```

## Two ways to fix coverage

I propose two different changes to `coverage` to prevent the aforementioned errors and crashes:

1. Exclude `-journal` files from `combinable_files`. This is a somewhat crude fix and relies on SQLite always naming its journal files with the `-journal` suffix, but so far in all my testing, that appears to be a safe assumption. However, if the `-journal` file still contains data that has not yet been synced to its SQLite database file, then reading the SQLite database file may give incomplete and inaccurate results. I suspect this is what happened in the "doesn't seem to be a coverage data file" examples in the logs quoted above.
2. Retrieve the current `journal_mode` value _after_ attempting to set it to `off`, and if it's _not_ `off`, attempt to set it to `memory`. In my testing, the `memory` setting always appears to work. This could introduce a _slight_ performance penalty or increased memory footprint to `coverage` since SQLite will needlessly be operating with an in-memory WAL, but I think this should be negligible since `coverage` isn't using transactions (AFAICT).


# Which Python+SQLite versions are affected?

I wrote the scripts in this repository to try to identify a pattern around this problematic behavior. I have only found that macOS not-homebrew versions of Python+SQLite are affected.

Requesting `PRAGMA journal_mode=off` for various Python versions and distributions:

| python version             | sqlite | default | desired | after execute | after cur.close | with new con | okay?              |
| -------------------------- | ------ | ------- | ------- | ------------- | --------------- | ------------ | ------------------ |
| 3.9.6 (macOS 13.2.1)       | 3.39.5 | delete  | off     | delete        | delete          | delete       | :x:                |
| 3.9.16 (homebrew)          | 3.40.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.10.10 (homebrew)         | 3.40.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.11.2 (homebrew)          | 3.40.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.9.16 (pyenv on macOS)    | 3.39.5 | delete  | off     | delete        | delete          | delete       | :x:                |
| 3.10.5 (pyenv on macOS)    | 3.39.5 | delete  | off     | delete        | delete          | delete       | :x:                |
| 3.11.2 (pyenv on macOS)    | 3.39.5 | delete  | off     | delete        | delete          | delete       | :x:                |
| 3.11.2 (python:latest)     | 3.34.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.9.16 (python:3.9)        | 3.34.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.9.16 (python:3.9-alpine) | 3.40.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.9.16 (pypy:3.9)          | 3.34.1 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |
| 3.9.13 (ubi8/ubi-minimal)  | 3.26.0 | delete  | off     | off           | off             | delete       | :heavy_check_mark: |

In all versions I tested, however, requesting `PRAGMA journal_mode=memory` appears to work fine:

| python version             | sqlite | default | desired | after execute | after cur.close | with new con | okay?              |
| -------------------------- | ------ | ------- | ------- | ------------- | --------------- | ------------ | ------------------ |
| 3.9.6 (macOS 13.2.1)       | 3.39.5 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.9.16 (homebrew)          | 3.40.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.10.10 (homebrew)         | 3.40.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.11.2 (homebrew)          | 3.40.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.9.16 (pyenv on macOS)    | 3.39.5 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.10.5 (pyenv on macOS)    | 3.39.5 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.11.2 (pyenv on macOS)    | 3.39.5 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.11.2 (python:latest)     | 3.34.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.9.16 (python:3.9)        | 3.34.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.9.16 (python:3.9-alpine) | 3.40.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.9.16 (pypy:3.9)          | 3.34.1 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
| 3.9.13 (ubi8/ubi-minimal)  | 3.26.0 | delete  | memory  | memory        | memory          | delete       | :heavy_check_mark: |
