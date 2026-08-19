# SRIS Project Rules

## Tooling

- The `gh` CLI lives inside the `sris` conda environment. Invoke it via `conda run -n sris gh ...`. It is NOT on the system PATH.
- Use the `sris` conda env for other project tooling as well when needed.

## Delivery workflow

- When making code changes, push a feature branch and create a pull request (PR) via `conda run -n sris gh pr create ...`.
- After creating the PR, watch CI: `conda run -n sris gh pr checks <n> --watch`.
- Merge the PR only if all required checks are green: `conda run -n sris gh pr merge <n> --merge --delete-branch`.
- After merging, clean up: delete the feature branch locally (`git branch -D <branch>`) and confirm the remote branch is gone.

## Verification

- Frontend tests: `npm run test:run` (in `frontend/`)
- Frontend build/typecheck: `npm run build` (in `frontend/`)
