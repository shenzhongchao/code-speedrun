# Runtime Selection

Use only the section that matches the codebase you are speedrunning. Do not drag unrelated runtime instructions into the output.

## Node.js / TypeScript

- Detect package manager from lockfiles: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`.
- Prefer the project's existing executor: `npm`, `pnpm`, `yarn`, `bun`, `tsx`, `ts-node`, `vite`, `next`, `node`.
- Put one dependency manifest at the speedrun root.
- Make unit commands copy-pasteable, for example:
  - `pnpm install`
  - `pnpm tsx unit-2-router/index.ts`
  - `node dist/unit-1-overall/index.js`
- For debugging, point `.vscode/launch.json` at unit entry files under the speedrun root.
- If the original project uses a framework dev server, build the unit around the narrowest runnable path instead of the full framework boot flow when possible.

## Python

- Detect toolchain from `pyproject.toml`, `requirements.txt`, `poetry.lock`, `uv.lock`, `Pipfile`.
- Keep a single environment/dependency definition at the speedrun root.
- Prefer `python`, `uv run`, `pytest`, or the project's existing task runner.
- Make each unit runnable as a module or script:
  - `uv run python unit-2-routing/main.py`
  - `python -m unit_3_state.main`
- Use `debugpy`, `pdb`, or `breakpoint()` in examples and debug configs.
- If the original project is notebook-heavy, convert the learning unit into a script with deterministic inputs unless the notebook itself is the concept being taught.

## Go

- Detect module roots from `go.mod` and package layout.
- Keep one `go.mod` at the speedrun root unless the source project clearly needs multiple modules.
- Make unit commands explicit:
  - `go run ./unit-1-overall`
  - `go test ./...`
- Keep packages small and importable by Unit 1.
- Prefer `dlv` or VS Code Go debug entries when the learner benefits from stepping through state transitions.

## Rust

- Detect crate layout from `Cargo.toml` and `src/`.
- Keep one `Cargo.toml` workspace or crate definition at the speedrun root.
- Use small binaries under unit directories or `src/bin/` if that matches the clearest structure.
- Make commands explicit:
  - `cargo run --bin unit-1-overall`
  - `cargo test`
- Keep ownership/lifetime complexity only when it is the concept being taught. Otherwise simplify aggressively and document the simplification.

## JVM Languages

- Detect `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle`, or wrapper scripts.
- Reuse the source project's build tool where possible.
- Prefer small runnable entry points over full application bootstraps when teaching architecture slices.
- Keep the unit commands explicit:
  - `./gradlew run`
  - `./gradlew test`
  - `mvn test`

## Frontend-Heavy Repos

- If the codebase is mostly UI, choose units around render flow, state flow, data fetching, routing, and build tooling.
- Favor narrow runnable examples over the entire app shell when that preserves the concept.
- Keep mocks realistic: component props, API responses, route params, and state snapshots should match the real app shape.

## Monorepos

- Pick the package, app, or service to speedrun before decomposing units.
- Reuse root tooling only if it does not force the learner to understand the whole monorepo.
- If a package depends on shared libraries, either extract the minimum shared code into the unit or document it as a simplification with a reference to the original path.
