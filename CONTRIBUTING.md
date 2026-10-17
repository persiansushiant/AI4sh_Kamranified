# Contributing

1. Read the architecture and complete activity example in `docs/`.
2. Create a branch for one feature; use responsibility-based names.
3. Keep Python activity behavior, HTML content, browser handlers, persistence and models separate.
4. Use the public controls with an active framework context. Do not create arbitrary threads for feature work.
5. Validate inputs on the server. Never trace credentials or secret-bearing exception text.
6. Add behavioral tests when changing persistence, permissions, lifecycle or transitions. Use temporary databases and keys.
7. Update the relevant documentation in the same change. Clearly label demo and unimplemented behavior.
8. Describe what changed, how it was verified, and what remains incomplete in the pull request.

Do not assign a new project license without the owner's decision. Preserve third-party notices. Do not assume that a public repository automatically grants a redistribution license.
