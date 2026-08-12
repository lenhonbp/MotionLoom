# Multi-scene continuity fixture

This fixture contains two ordered scenes that share the same project context and runtime timing contract. `scene-01` and `scene-02` are the expected passing transition. A drift variant is created in the regression harness by changing only `scene-02`'s context hash; the expected result is a non-blocking `warn` with a selective transition scope.

The fixture is intentionally small and framework-neutral. It exercises scene identity, scene order, intent presence, context binding, FPS compatibility and positive duration without fabricating browser approval or perceptual acceptance.
