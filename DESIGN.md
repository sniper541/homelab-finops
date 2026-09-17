---
name: FinOps
description: Blue light and smoked glass for entry, with a stable financial workspace.
colors:
  entry-canvas: "#080d14"
  entry-glass: "#101c286b"
  auth-primary: "#9ed8ff"
  auth-primary-hover: "#b7e3ff"
  auth-primary-text: "#0b2435"
  auth-text: "#edf4fb"
  auth-muted: "#b1c4d3"
  workspace-primary: "#83c9ff"
  workspace-panel: "#101d2a"
  workspace-border: "#26394a"
  income: "#91d5b6"
  opaque-glass: "#142333"
typography:
  display:
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "clamp(40px,4.5vw,64px)"
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "-.04em"
  auth-title:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "30px"
    fontWeight: 500
    lineHeight: 1.16
    letterSpacing: "-.035em"
  auth-label:
    fontSize: "13px"
    fontWeight: 500
rounded:
  control: "12px"
  entry-panel: "32px 12px 32px 12px"
  registration-panel: "12px 32px 12px 32px"
  workspace-panel: "20px"
spacing:
  field-gap: "20px"
  embedded-form: "24px 28px"
  embedded-form-mobile: "20px"
components:
  auth-button-primary:
    backgroundColor: "{colors.auth-primary}"
    textColor: "{colors.auth-primary-text}"
    rounded: "{rounded.control}"
    padding: "14px 18px"
  auth-button-primary-hover:
    backgroundColor: "{colors.auth-primary-hover}"
  workspace-panel:
    backgroundColor: "{colors.workspace-panel}"
    rounded: "{rounded.workspace-panel}"
    padding: "26px"
---

# Design System: FinOps

## Overview

The September 2026 direction follows the user's blue brand and supplied login video: dark smoked glass, diagonal light, rounded controls, and visible but finite movement. The reference inspires the visual treatment rather than prescribing a pixel-for-pixel copy.

Entry uses one continuous glass surface around native authentication. The workspace preserves a quieter, stable hierarchy: balance first, then income, expenses, charts, and transactions. Existing Sniper541 identity remains shared with the standalone authentication surface used by Vault.

## Colors

### Primary

Pale blue identifies authentication actions and focus. The workspace uses its existing stronger blue for primary actions and expense chart marks. These are separate observed surface tokens.

### Neutral

The entry canvas is almost black with a blue cast. Translucent glass exposes diagonal light; light text and muted blue-gray text establish hierarchy. Workspace panels use opaque blue surfaces and restrained borders. Reduced transparency substitutes the opaque-glass token.

### Semantic

Green indicates income. Preserve text labels alongside chart colors. Native errors use rose text and borders; successful authentication feedback uses green.

## Typography

The app uses its existing Inter/system sans stack; native identity forms use the system sans stack. Headings use medium weights and slightly tight tracking. Native text fields use 16px text, with restrained labels. Amounts use tabular numerals and do not animate numerically.

The entry display becomes 40px below 960px and 32px below 760px. Native form titles become 28px below 480px. Balance remains the largest financial value in the workspace.

## Layout

Entry is centered in two columns, capped at 1180px, with a 490px form column. Below 960px the form column becomes 440px. Below 760px, the form precedes introductory copy in a single column capped at 490px; the decorative ledger disappears. Embedded form padding follows the frontmatter, switching below 480px.

The native document determines iframe height. Registration places first and last names side by side when the iframe viewport is at least 420px wide; other field groups span the form. Do not force a fixed height that clips validation or recovery content.

The workspace retains its sidebar and responsive navigation. Overview and supporting panels collapse to one column below 840px; income and expense summaries retain their paired layout. Check entry and registration at 320px, 390px, and 1440px, including longer translated labels and validation messages.

## Elevation & Depth

The parent entry page owns the glass: a faint diagonal highlight, translucent fill, fine border, 14px backdrop blur, and a soft shadow. Embedded forms remain transparent because blur cannot cross document boundaries. The standalone identity panel retains its own glass and 16px blur. Workspace panels use tonal separation and borders instead of moving or glowing on hover.

Reduced transparency removes backdrop blur and supplies an opaque panel. Shadow and motion values live in `.impeccable/design.json`; frontmatter owns color, type, spacing, and shape primitives.

## Shapes

The persistent entry panel alternates opposing large and small corners between login and registration. Small decorative corner pieces move inward during pointer-initiated native form navigation, then return when the next document is ready. They are decorative, never controls. Fields and buttons share rounded corners; workspace panels keep their existing quieter rounded rectangles.

## Components

### Native authentication

Native Keycloak fields appear immediately inside a cross-origin iframe while the top-level address remains app.sniper541.com. The parent owns presentation; native forms own credentials, validation, password visibility, language selection, recovery, and registration. Telegram stays visibly disabled. If embedding fails, expose the explicit standard-login fallback.

Preserve existing authentication boundaries: the adapter validates state and uses PKCE S256, tokens remain in memory, and React does not collect passwords. The realm permits framing only from itself and the app; the app's own frame-ancestors policy stays self-only. Vault retains its canonical issuer and callback.

### Fields and actions

Native inputs and primary actions have a minimum height of 52px. Tabs provide 44px minimum targets. Focus shifts the field border, background, and subtle ring over 160ms; keyboard-focus outlines remain visible. Invalid fields include native error text as well as a changed border. Disabled actions retain their disabled semantics.

### Motion

Panel height and corner radii transition over 300ms using the shared ease-out curve. Fields enter over 400ms with at most 70ms staggering. The parent frame fades during a native form switch over 160ms. Decorative entry light settles within 2 seconds; standalone identity light may take 2.2 seconds. Navigation has no artificial delay or perpetual loop.

Reduced motion disables spatial animation and panel transitions. The switching iframe remains fully opaque under reduced motion. Keyboard navigation suppresses native document view transitions. Retain native fallback behavior when view transitions are unavailable.

### Financial workspace

Balance leads the overview; income and expense summaries support it. Chart and transaction panels stay stable. Preserve chart colors, tabular amounts, responsive transaction wrapping, and readable empty/error states. Product copy avoids backend implementation names.

## Do's and Don'ts

- **Do** preserve the user's blue identity and existing workspace hierarchy.
- **Do** render authentication fields immediately and let native validation change panel height.
- **Do** verify login, registration, recovery, callbacks, authenticated API requests, logout, language selection, password visibility, disabled Telegram, and reduced motion.
- **Do** retain reduced-transparency and keyboard-focus treatments.
- **Don't** collect credentials in React or introduce client secrets or password grants.
- **Don't** add perpetual motion, artificial navigation delays, or animated financial values.
- **Don't** duplicate the parent's glass treatment inside the embedded native form.
