FROM python:latest

ENV desired_mode off
COPY test_journal_mode.py .
CMD python3 test_journal_mode.py ${desired_mode}
