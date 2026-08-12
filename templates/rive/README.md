# Rive Templates

Rive scenes are editor-authored, so this template set covers the runtime side: the React component with state-machine inputs bound to project tokens, and the rules for naming inputs so the analyzer can drive them.

## Runtime component pattern

```tsx
import { useRive, StateMachineInput, InputType } from "@rive-app/react-canvas";

export default function RiveScene({ src, theme }: { src: string; theme?: Record<string, unknown> }) {
  const { RiveComponent, rive } = useRive({
    src,
    stateMachines: "Main",
    autoplay: true,
  });

  useEffect(() => {
    if (!rive) return;
    // Inputs follow the canonical naming: <token>_<slot> (e.g. primary_color)
    for (const [name, value] of Object.entries(theme ?? {})) {
      const input = rive.stateMachineInputs("Main")?.find((i) => i.name === name);
      if (input?.type === InputType.Number) input.value = Number(value);
    }
  }, [rive, theme]);

  return <RiveComponent style={{ width: "100%", height: "100%" }} />;
}
```

## Rules for editor authors

Name every color-controlling input `<token>_<slot>` so the analyzer's brand tokens map automatically. Keep the state machine flat (≤6 states) for UI assets. Export at 60 fps from the Rive editor; keep the .riv under 300 KB for UI scenes.

## License note

Rive runtimes are Apache-2.0 and free to bundle. The Rive editor is subject to Rive's own terms — record this in the scene manifest `license_note`.
