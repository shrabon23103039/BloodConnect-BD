# Architecture diagrams and project artwork

This folder contains editable Mermaid sources (`.mmd`) and their rendered SVGs. The diagrams document the current local Django implementation and distinguish proposed hosting from verified deployment.

| Diagram | Source | Render |
|---|---|---|
| System architecture | [`system-architecture.mmd`](system-architecture.mmd) | [`system-architecture.svg`](system-architecture.svg) |
| Data model | [`database-er.mmd`](database-er.mmd) | [`database-er.svg`](database-er.svg) |
| Application user flow | [`user-flow.mmd`](user-flow.mmd) | [`user-flow.svg`](user-flow.svg) |
| Technology stack | [`technology-stack.mmd`](technology-stack.mmd) | [`technology-stack.svg`](technology-stack.svg) |

The Mermaid sources are editable diagram definitions. SVG exports are included for browsers and Markdown viewers; use Mermaid CLI with [`mermaid-config.json`](mermaid-config.json) to regenerate or validate them. For example, with `@mermaid-js/mermaid-cli` 12.2.0 installed:

```sh
npx --yes @mermaid-js/mermaid-cli@12.0.1 -c docs/architecture/mermaid-config.json -i docs/architecture/system-architecture.mmd -o docs/architecture/system-architecture.svg
npx --yes @mermaid-js/mermaid-cli@12.0.1 -c docs/architecture/mermaid-config.json -i docs/architecture/database-er.mmd -o docs/architecture/database-er.svg
npx --yes @mermaid-js/mermaid-cli@12.0.1 -c docs/architecture/mermaid-config.json -i docs/architecture/user-flow.mmd -o docs/architecture/user-flow.svg
npx --yes @mermaid-js/mermaid-cli@12.0.1 -c docs/architecture/mermaid-config.json -i docs/architecture/technology-stack.mmd -o docs/architecture/technology-stack.svg
```

[`social-preview.svg`](social-preview.svg) is the editable GitHub social-preview banner source. [`social-preview.png`](social-preview.png) is the 1280×640 rendered image used in the repository README and suitable for GitHub's social preview setting. It is project artwork, not an application screenshot.

The app screenshots live in [`../screenshots/`](../screenshots/). They are captured from real Django routes using only synthetic test records.
