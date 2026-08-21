# External analyzer corpus

MotionLoom keeps external project evaluation **opt-in**. The default CI path never clones, installs, builds, tests or executes code from third-party repositories. A checkout is considered evidence only when the caller explicitly fetches it into a workspace and the evaluator records its source and commit.

## Reproduce the corpus evaluation

From the repository root, run:

```bash
rm -rf /tmp/motionloom-external-corpus
python3 scripts/fetch-project-corpus.py \
  --workspace /tmp/motionloom-external-corpus \
  --all \
  --depth 1
python3 scripts/eval-projects.py \
  --workspace /tmp/motionloom-external-corpus \
  --output /tmp/motionloom-external-corpus/evaluation.json
```

The fetch helper reads the allowlisted repository URLs and relative paths from `tests/evals/project-corpus.json`, records the resolved commit in `.motionloom-corpus-fetch.json`, and performs no package installation or external code execution. The evaluator runs MotionLoom's bounded analyzer only; it writes a separate report containing the available project count, expected signals, scan budgets and status.

The current manifest covers Motion One, GSAP and Rive React as external projects, in addition to the first-party repository. On 21 Aug 2026, a depth-one checkout of all three external projects produced `available_external_projects=3` and `status=pass`. This is analyzer compatibility evidence, not a guarantee of runtime correctness, design quality or product value in arbitrary host applications.

## Evidence policy

External evidence must remain labeled with its source URL, resolved commit and fetch timestamp. Missing or unavailable checkouts must produce `insufficient_evidence`; `--allow-insufficient` may make a local report non-blocking, but it must not turn missing evidence into a pass. No external checkout should be added to the npm package or committed into this repository.
