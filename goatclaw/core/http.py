"""
GOATCLAW HTTP helpers.

Central place for creating aiohttp client sessions.

Sessions are created with ``trust_env=True`` so that standard proxy
environment variables (HTTP_PROXY / HTTPS_PROXY / ALL_PROXY and their
lowercase variants) are honored. Newer aiohttp versions default
``trust_env`` to False, which makes plain ``ClientSession()`` ignore the
proxy env entirely and attempt direct connections -- that fails in
sandboxed / egress-proxy environments. Passing ``trust_env=True`` is
portable: where no proxy env vars are set, behavior is unchanged.
"""

import aiohttp


def create_session(**kwargs) -> aiohttp.ClientSession:
    """
    Create an aiohttp ClientSession that honors proxy environment variables.

    Any extra kwargs are forwarded to ``aiohttp.ClientSession``.
    """
    kwargs.setdefault("trust_env", True)
    return aiohttp.ClientSession(**kwargs)
