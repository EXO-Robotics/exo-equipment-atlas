# Platform contract

Each machine package supplies identity, evidence, mechanics, presentation, and
validation data. A future shared viewer will own rendering, input, cameras,
selection, accessibility, responsive controls, diagnostics, and receipt loading.

Machine-specific modules will own:

- exact configuration and asset identity;
- required hierarchy and interaction volumes;
- controls, stow state, motion limits, and solver behavior;
- component inspection definitions and camera poses;
- mechanical closure, invariant, collision, and envelope gates.

The shared runtime must never contain manufacturer names, configuration IDs,
machine-specific node names, motion ranges, or inspector prose. Generic node
presence cannot substitute for a machine-specific mechanical gate.
