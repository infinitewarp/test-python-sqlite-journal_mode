#!/usr/bin/bash

function test_setting_journal_mode() {
    printf "\n##########\n# Default /usr/bin/python3\n"
    /usr/bin/python3 ./test_journal_mode.py "$1"

    printf "\n##########\n# homebrew-installed python@3.9\n"
    "$(brew --prefix)"/bin/python3.9 ./test_journal_mode.py "$1"

    printf "\n##########\n# homebrew-installed python@3.10\n"
    "$(brew --prefix)"/bin/python3.10 ./test_journal_mode.py "$1"

    printf "\n##########\n# homebrew-installed python@3.11\n"
    "$(brew --prefix)"/bin/python3.11 ./test_journal_mode.py "$1"

    printf "\n##########\n# pyenv-installed 3.9.16\n"
    "$(pyenv prefix 3.9.16)"/bin/python3 ./test_journal_mode.py "$1"

    printf "\n##########\n# pyenv-installed 3.10.5\n"
    "$(pyenv prefix 3.10.5)"/bin/python3 ./test_journal_mode.py "$1"

    printf "\n##########\n# pyenv-installed 3.11.2\n"
    "$(pyenv prefix 3.11.2)"/bin/python3 ./test_journal_mode.py "$1"

    printf "\n##########\n# Docker python:latest\n"
    docker run --rm -it -e desired_mode="$1" "$(docker build -f Dockerfile -q .)"

    printf "\n##########\n# Docker python:3.9\n"
    docker run --rm -it -e desired_mode="$1" "$(docker build -f Dockerfile_39 -q .)"

    printf "\n##########\n# Docker python:3.9-alpine\n"
    docker run --rm -it -e desired_mode="$1" "$(docker build -f Dockerfile_alpine39 -q .)"

    printf "\n##########\n# Docker pypy:3.9\n"
    docker run --rm -it -e desired_mode="$1" "$(docker build -f Dockerfile_pypy39 -q .)"

    printf "\n##########\n# Docker ubi8/ubi-minimal (python39)\n"
    docker run --rm -it -e desired_mode="$1" "$(docker build -f Dockerfile_ubi8_python39 -q .)"

}

printf "\n####################\n# Attempting to set journal_mode=off\n"
test_setting_journal_mode "off"

printf "\n####################\n# Attempting to set journal_mode=memory\n"
test_setting_journal_mode "memory"
