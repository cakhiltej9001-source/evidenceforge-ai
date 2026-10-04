"""Cooperative cancellation signal shared by graph and retrieval boundaries."""


class RunCancellation(Exception):
    """An owner requested termination at a safe workflow boundary."""
