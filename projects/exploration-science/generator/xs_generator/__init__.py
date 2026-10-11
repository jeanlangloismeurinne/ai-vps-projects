"""Explorateur de systèmes: the node generator (Phase 1).

The generator is code that calls the Claude API. Every model call goes through a
runner and is recorded (request, fingerprint, response, usage, cost), so a run can
be replayed byte for byte and its cost measured:

- ``anthropic``: the real API call (production);
- ``manual``: a person (or Claude Code during development) writes the response
  for a request saved on disk; such runs are marked as not reproducible;
- ``replay``: answers from a recorded run, and refuses if the request changed.
"""
