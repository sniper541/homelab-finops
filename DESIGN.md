# FinOps interface

The September 2026 direction is based on the user's blue brand and supplied login video: dark smoked glass, diagonal light, clear rounded controls, and visible but finite movement. The reference is inspiration, not a pixel-for-pixel target.

## Entry and authentication

The app opens its own welcome screen without an authentication redirect. Only an explicit login or registration action navigates to Keycloak, which can reuse an existing SSO session. OIDC callbacks still initialize the authenticated workspace. The realm blocks embedded authentication pages, so the welcome screen does not depend on an iframe. Password fields remain native Keycloak fields. Telegram remains visible as a disabled future option on both entry surfaces.

Use #080f17 for the entry canvas, translucent #121e2b for glass, #9ed8ff for primary controls, #edf4fb for text, and #b1c4d3 for supporting text. The same light treatment links the welcome screen to the neutral Sniper541 identity form, which is also used by Vault.

## Workspace

The balance leads the financial overview; income and expenses support it. Stable chart and transaction panels use #101d2a with #26394a borders. Green indicates income; blue indicates expenses in the chart. Amounts use tabular numerals. Product copy avoids backend implementation names.

## Interaction

Entry panels arrive over 500 ms; decorative light settles within 2.2 seconds. Login/registration copy transitions over 200–240 ms with a sliding selection indicator. Buttons respond over 140–200 ms. There are no perpetual decorative loops or animated financial values. Keyboard focus is visible; reduced-motion disables spatial motion, and reduced-transparency uses solid surfaces.

Verify welcome, identity form and workspace at 320, 390, 768 and 1440 px. Test empty/error/logout states, native password visibility, disabled Telegram, and explicit OIDC navigation.
