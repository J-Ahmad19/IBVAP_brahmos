# Mars Design System

Mars is a dark mission-control design system. It creates interfaces with a near-black continuous surface, mars-red glow, orange and slate accents, Space Grotesk typography, flat panels, and tactile pill buttons.

The system is built to evoke spacecraft dashboards and telemetry consoles. It gives generated UI a focused, high-stakes atmosphere without relying on gradients, heavy shadows, or decorative sci-fi clutter.

## Design Tokens

### Color Palette
Mars uses a restrained mission palette centered on black, red, orange, and warm slate.

| Token | Value | Purpose |
|-------|-------|---------|
| Surface | `#050505` | Continuous page and section background |
| Panel | `#0D0B08` | Cards and elevated surface steps |
| Brand | `#BD5347` | Mars-red headings, actions, accents, and telemetry emphasis |
| Brand Strong | `#A23E33` | Stronger red controls and active states |
| Warning | `#F59E2B` | Orange signals, alerts, and secondary emphasis |
| Body | `#B7A98E` | Warm readable body copy on black |

The whole interface should share one dark surface. Cards sit one step lighter, and section backgrounds should not alternate or tint away from the mission-control base.

### Typography
Mars uses **Space Grotesk** throughout the interface. The type should feel technical and compact, with confident heading treatment and readable labels. Button text uses medium weight with tight letter spacing as part of the tactile control design.

### Spacing and Shape
Mars uses an **8px rhythm**, 96px symmetric section spacing, 1152px containers, and **12px cards**. The page should read as one continuous mission panel, often reinforced by vertical rails and consistent borders.

### Component Language
Cards are **flat, shadow-free panels with 1px borders**. Depth comes from surface steps, not elevation. 

The signature button is a layered pill control with inset highlights, dark surface contours, clipped inner layers, and press feedback. Gradients belong inside the button surface treatment, not on page or card backgrounds.
