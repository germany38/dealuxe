import type { Config, Context } from "@netlify/edge-functions";

// Clickio consent (TCF stub + Google Consent Mode defaults + CMP main tag), injected into every HTML page's <head>.
const HEAD_TAGS = `<!-- TCF stub -->
<script type="text/javascript">
!function(){"use strict";var t,e,o=(t=function(t){function e(t){return(e="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(t){return typeof t}:function(t){return t&&"function"==typeof Symbol&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t})(t)}t.exports=function(){for(var t,o,n=[],r=window,a=r;a;){try{if(a.frames.__tcfapiLocator){t=a;break}}catch(t){}if(a===r.top)break;a=a.parent}t||(function t(){var e=r.document,o=!!r.frames.__tcfapiLocator;if(!o)if(e.body){var n=e.createElement("iframe");n.style.cssText="display:none",n.name="__tcfapiLocator",e.body.appendChild(n)}else setTimeout(t,5);return!o}(),r.__tcfapi=function(){for(var t=arguments.length,e=new Array(t),r=0;r<t;r++)e[r]=arguments[r];if(!e.length)return n;"setGdprApplies"===e[0]?e.length>3&&2===parseInt(e[1],10)&&"boolean"==typeof e[3]&&(o=e[3],"function"==typeof e[2]&&e[2]("set",!0)):"ping"===e[0]?"function"==typeof e[2]&&e[2]({gdprApplies:o,cmpLoaded:!1,cmpStatus:"stub"}):n.push(e)},r.addEventListener("message",(function(t){var o="string"==typeof t.data,n={};if(o)try{n=JSON.parse(t.data)}catch(t){}else n=t.data;var r="object"===e(n)&&null!==n?n.__tcfapiCall:null;r&&window.__tcfapi(r.command,r.version,(function(e,n){var a={__tcfapiReturn:{returnValue:e,success:n,callId:r.callId}};t&&t.source&&t.source.postMessage&&t.source.postMessage(o?JSON.stringify(a):a,"*")}),r.parameter)}),!1))}},t(e={exports:{}}),e.exports);o()}();
</script>
<!-- Default Consent Mode config -->
<script>
    //<![CDATA[
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('consent', 'default', {
        'ad_storage': 'denied',
        'analytics_storage': 'denied',
        'functionality_storage': 'denied',
        'personalization_storage': 'denied',
        'security_storage': 'denied',
        'ad_user_data': 'denied',
        'ad_personalization': 'denied',
        'wait_for_update': 1500
    });
    gtag('set', 'ads_data_redaction', true);
    gtag('set', 'url_passthrough', false);
    (function(){
        const s={adStorage:{storageName:"ad_storage",serialNumber:0},analyticsStorage:{storageName:"analytics_storage",serialNumber:1},functionalityStorage:{storageName:"functionality_storage",serialNumber:2},personalizationStorage:{storageName:"personalization_storage",serialNumber:3},securityStorage:{storageName:"security_storage",serialNumber:4},adUserData:{storageName:"ad_user_data",serialNumber:5},adPersonalization:{storageName:"ad_personalization",serialNumber:6}};let c=localStorage.getItem("__lxG__consent__v2");if(c){c=JSON.parse(c);if(c&&c.cls_val)c=c.cls_val;if(c)c=c.split("|");if(c&&c.length&&typeof c[14]!==undefined){c=c[14].split("").map(e=>e-0);if(c.length){let t={};Object.values(s).sort((e,t)=>e.serialNumber-t.serialNumber).forEach(e=>{t[e.storageName]=c[e.serialNumber]?"granted":"denied"});gtag("consent","update",t)}}}
    })();
    //]]>
</script>
<!-- Clickio Consent Main tag -->
<script async type="text/javascript" src="//clickiocmp.com/t/consent_251122.js"></script>
<!-- Clickio main tag -->
<script defer data-cfasync='false' src='https://s.clickiocdn.com/t/251122_wv.js'></script>`;

// Slim, dismissible side tab promoting Clickio to visitors who run their own websites.
const SIDEBAR = `<aside id="ckio-side" aria-label="For website owners">
<style>
#ckio-side{position:fixed;right:0;top:50%;transform:translateY(-50%);z-index:9998;font:14px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
#ckio-side .ck-card{width:220px;background:#0f172a;color:#f8fafc;border-radius:12px 0 0 12px;padding:16px 16px 14px;box-shadow:0 8px 28px rgba(0,0,0,.25);position:relative}
#ckio-side .ck-tag{display:inline-block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#fbbf24;margin-bottom:6px}
#ckio-side h3{margin:0 0 6px;font-size:16px;line-height:1.25;color:#fff}
#ckio-side p{margin:0 0 12px;color:#cbd5e1;font-size:13px}
#ckio-side a.ck-cta{display:block;text-align:center;background:#fbbf24;color:#0f172a;font-weight:700;text-decoration:none;padding:9px 10px;border-radius:8px}
#ckio-side a.ck-cta:hover{background:#f59e0b}
#ckio-side .ck-x{position:absolute;top:6px;right:8px;background:none;border:0;color:#94a3b8;font-size:18px;cursor:pointer;line-height:1}
#ckio-side .ck-tab{display:none;writing-mode:vertical-rl;background:#0f172a;color:#fbbf24;border:0;border-radius:8px 0 0 8px;padding:12px 7px;font-weight:700;font-size:12px;cursor:pointer;letter-spacing:.05em}
#ckio-side.ck-min .ck-card{display:none}#ckio-side.ck-min .ck-tab{display:block}
@media (max-width:900px){#ckio-side .ck-card{display:none}#ckio-side .ck-tab{display:block}#ckio-side.ck-open .ck-card{display:block}#ckio-side.ck-open .ck-tab{display:none}}
</style>
<div class="ck-card">
<button class="ck-x" type="button" aria-label="Minimize">&times;</button>
<span class="ck-tag">Own a website?</span>
<h3>Earn more from your traffic</h3>
<p>Clickio helps publishers grow ad revenue with smart optimisation and built-in GDPR consent tools.</p>
<a class="ck-cta" href="http://account.clickio.com/r/fiATaVdVVWR4QlVp/" target="_blank" rel="sponsored noopener">Join Clickio free &rarr;</a>
</div>
<button class="ck-tab" type="button">FOR PUBLISHERS</button>
<script>(function(){var s=document.getElementById("ckio-side");if(!s)return;var m=window.matchMedia("(max-width:900px)");try{if(localStorage.getItem("ckioSideMin")==="1")s.classList.add("ck-min")}catch(e){}
s.querySelector(".ck-x").onclick=function(){s.classList.remove("ck-open");s.classList.add("ck-min");try{localStorage.setItem("ckioSideMin","1")}catch(e){}};
s.querySelector(".ck-tab").onclick=function(){s.classList.remove("ck-min");if(m.matches)s.classList.add("ck-open");try{localStorage.removeItem("ckioSideMin")}catch(e){}};})();</script>
</aside>`;

export default async (_req: Request, context: Context) => {
  const res = await context.next();
  const type = res.headers.get("content-type") || "";
  if (!type.includes("text/html")) return res;

  let html = await res.text();
  if (html.includes("clickiocmp.com/t/consent_251122.js")) return new Response(html, res);

  html = /<head[^>]*>/i.test(html)
    ? html.replace(/<head[^>]*>/i, (m) => `${m}\n${HEAD_TAGS}`)
    : HEAD_TAGS + html;
  html = /<\/body>/i.test(html) ? html.replace(/<\/body>/i, `${SIDEBAR}\n</body>`) : html + SIDEBAR;

  const headers = new Headers(res.headers);
  headers.delete("content-length");
  return new Response(html, { status: res.status, statusText: res.statusText, headers });
};

export const config: Config = {
  path: "/*",
  excludedPath: [
    "/assets/*",
    "/.netlify/*",
    "/*.css",
    "/*.js",
    "/*.json",
    "/*.xml",
    "/*.txt",
    "/*.png",
    "/*.jpg",
    "/*.jpeg",
    "/*.webp",
    "/*.svg",
    "/*.ico",
    "/*.pdf",
    "/*.csv",
  ],
};
