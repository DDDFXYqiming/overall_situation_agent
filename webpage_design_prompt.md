# Interface design reference

The reference combines a light neutral surface with blue accents, clear section boundaries and restrained animation. It is a presentation guide for the existing report interface.

## Palette

| Role | Colour |
|---|---|
| Background | `#FAFAFA` |
| Main text | `#0F172A` |
| Muted surface | `#F1F5F9` |
| Secondary text | `#64748B` |
| Primary accent | `#0052FF` |
| Gradient endpoint | `#4D7CFF` |
| Border | `#E2E8F0` |
| Card surface | `#FFFFFF` |

## Typography and components

Calistoga is the reference heading typeface; Inter and system sans-serif fonts handle body text and controls. Headings, data tables and supporting descriptions should have distinct sizes and spacing.

Primary buttons use the blue accent, while secondary actions use neutral surfaces and borders. Cards use moderate corner radii and subtle shadows. Forms need visible labels, focus states and useful validation messages.

## Layout and motion

Keep related controls together and reserve space around report sections. Narrow layouts should preserve access to filters, uploads and generated results. Animation should explain state changes without delaying work, and reduced-motion preferences should be respected.

Colour, spacing and component rules should be shared through the existing styling system. Decorative effects must not reduce text contrast or obscure report data.
