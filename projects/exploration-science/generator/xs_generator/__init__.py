"""Explorateur de systèmes: the node generator (Phase 1).

The generator is code that calls a model API. Which API, which model and with which
parameters is a *profile* (generator/profiles.toml); each API is wrapped by a *provider*
(providers.py) that brings it to the level of the reference, Anthropic's. Every model call
goes through a runner and is recorded (request, fingerprint, response, usage, cost), so a
run can be replayed byte for byte and its cost measured:

- ``api``: the real API call of the profile's provider (production);
- ``manual``: a person (or Claude Code during development) writes the response
  for a request saved on disk; such runs are marked as not reproducible;
- ``replay``: answers from a recorded run, and refuses if the request changed.
"""
