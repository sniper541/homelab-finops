<#macro content>
  <footer class="finops-footer">
    <div class="access-divider"><span>${msg("finopsOtherWays")}</span></div>
    <button class="finops-telegram" type="button" disabled aria-describedby="telegram-soon">
      <i class="fa fa-paper-plane" aria-hidden="true"></i>
      ${msg("finopsTelegram")}<span>${msg("finopsSoon")}</span>
    </button>
    <p id="telegram-soon">${msg("finopsTelegramSoon")}</p>
    <p>${msg("finopsTagline")}</p>
  </footer>
</#macro>
