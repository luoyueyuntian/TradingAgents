import{B as k,C as $,j as r,c as i,E as t,P as c,e as d,f as u,G as S,R as j,I as T,N as I,S as O,b,w as C,y as E,z as B,q as A,aG as D,d as N,t as h}from"./app.js";var G=`
    .p-card {
        background: dt('card.background');
        color: dt('card.color');
        box-shadow: dt('card.shadow');
        border-radius: dt('card.border.radius');
        display: flex;
        flex-direction: column;
    }

    .p-card-caption {
        display: flex;
        flex-direction: column;
        gap: dt('card.caption.gap');
    }

    .p-card-body {
        padding: dt('card.body.padding');
        display: flex;
        flex-direction: column;
        gap: dt('card.body.gap');
    }

    .p-card-title {
        font-size: dt('card.title.font.size');
        font-weight: dt('card.title.font.weight');
    }

    .p-card-subtitle {
        color: dt('card.subtitle.color');
    }
`,L={root:"p-card p-component",header:"p-card-header",body:"p-card-body",caption:"p-card-caption",title:"p-card-title",subtitle:"p-card-subtitle",content:"p-card-content",footer:"p-card-footer"},R=k.extend({name:"card",style:G,classes:L}),M={name:"BaseCard",extends:$,style:R,provide:function(){return{$pcCard:this,$parentInstance:this}}},q={name:"Card",extends:M,inheritAttrs:!1};function H(e,n,s,o,l,a){return r(),i("div",t({class:e.cx("root")},e.ptmi("root")),[e.$slots.header?(r(),i("div",t({key:0,class:e.cx("header")},e.ptm("header")),[c(e.$slots,"header")],16)):d("",!0),u("div",t({class:e.cx("body")},e.ptm("body")),[e.$slots.title||e.$slots.subtitle?(r(),i("div",t({key:0,class:e.cx("caption")},e.ptm("caption")),[e.$slots.title?(r(),i("div",t({key:0,class:e.cx("title")},e.ptm("title")),[c(e.$slots,"title")],16)):d("",!0),e.$slots.subtitle?(r(),i("div",t({key:1,class:e.cx("subtitle")},e.ptm("subtitle")),[c(e.$slots,"subtitle")],16)):d("",!0)],16)):d("",!0),u("div",t({class:e.cx("content")},e.ptm("content")),[c(e.$slots,"content")],16),e.$slots.footer?(r(),i("div",t({key:1,class:e.cx("footer")},e.ptm("footer")),[c(e.$slots,"footer")],16)):d("",!0)],16)],16)}q.render=H;var K=`
    .p-message {
        display: grid;
        grid-template-rows: 1fr;
        border-radius: dt('message.border.radius');
        outline-width: dt('message.border.width');
        outline-style: solid;
    }

    .p-message-content-wrapper {
        min-height: 0;
    }

    .p-message-content {
        display: flex;
        align-items: center;
        padding: dt('message.content.padding');
        gap: dt('message.content.gap');
    }

    .p-message-icon {
        flex-shrink: 0;
    }

    .p-message-close-button {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        margin-inline-start: auto;
        overflow: hidden;
        position: relative;
        width: dt('message.close.button.width');
        height: dt('message.close.button.height');
        border-radius: dt('message.close.button.border.radius');
        background: transparent;
        transition:
            background dt('message.transition.duration'),
            color dt('message.transition.duration'),
            outline-color dt('message.transition.duration'),
            box-shadow dt('message.transition.duration'),
            opacity 0.3s;
        outline-color: transparent;
        color: inherit;
        padding: 0;
        border: none;
        cursor: pointer;
        user-select: none;
    }

    .p-message-close-icon {
        font-size: dt('message.close.icon.size');
        width: dt('message.close.icon.size');
        height: dt('message.close.icon.size');
    }

    .p-message-close-button:focus-visible {
        outline-width: dt('message.close.button.focus.ring.width');
        outline-style: dt('message.close.button.focus.ring.style');
        outline-offset: dt('message.close.button.focus.ring.offset');
    }

    .p-message-info {
        background: dt('message.info.background');
        outline-color: dt('message.info.border.color');
        color: dt('message.info.color');
        box-shadow: dt('message.info.shadow');
    }

    .p-message-info .p-message-close-button:focus-visible {
        outline-color: dt('message.info.close.button.focus.ring.color');
        box-shadow: dt('message.info.close.button.focus.ring.shadow');
    }

    .p-message-info .p-message-close-button:hover {
        background: dt('message.info.close.button.hover.background');
    }

    .p-message-info.p-message-outlined {
        color: dt('message.info.outlined.color');
        outline-color: dt('message.info.outlined.border.color');
    }

    .p-message-info.p-message-simple {
        color: dt('message.info.simple.color');
    }

    .p-message-success {
        background: dt('message.success.background');
        outline-color: dt('message.success.border.color');
        color: dt('message.success.color');
        box-shadow: dt('message.success.shadow');
    }

    .p-message-success .p-message-close-button:focus-visible {
        outline-color: dt('message.success.close.button.focus.ring.color');
        box-shadow: dt('message.success.close.button.focus.ring.shadow');
    }

    .p-message-success .p-message-close-button:hover {
        background: dt('message.success.close.button.hover.background');
    }

    .p-message-success.p-message-outlined {
        color: dt('message.success.outlined.color');
        outline-color: dt('message.success.outlined.border.color');
    }

    .p-message-success.p-message-simple {
        color: dt('message.success.simple.color');
    }

    .p-message-warn {
        background: dt('message.warn.background');
        outline-color: dt('message.warn.border.color');
        color: dt('message.warn.color');
        box-shadow: dt('message.warn.shadow');
    }

    .p-message-warn .p-message-close-button:focus-visible {
        outline-color: dt('message.warn.close.button.focus.ring.color');
        box-shadow: dt('message.warn.close.button.focus.ring.shadow');
    }

    .p-message-warn .p-message-close-button:hover {
        background: dt('message.warn.close.button.hover.background');
    }

    .p-message-warn.p-message-outlined {
        color: dt('message.warn.outlined.color');
        outline-color: dt('message.warn.outlined.border.color');
    }

    .p-message-warn.p-message-simple {
        color: dt('message.warn.simple.color');
    }

    .p-message-error {
        background: dt('message.error.background');
        outline-color: dt('message.error.border.color');
        color: dt('message.error.color');
        box-shadow: dt('message.error.shadow');
    }

    .p-message-error .p-message-close-button:focus-visible {
        outline-color: dt('message.error.close.button.focus.ring.color');
        box-shadow: dt('message.error.close.button.focus.ring.shadow');
    }

    .p-message-error .p-message-close-button:hover {
        background: dt('message.error.close.button.hover.background');
    }

    .p-message-error.p-message-outlined {
        color: dt('message.error.outlined.color');
        outline-color: dt('message.error.outlined.border.color');
    }

    .p-message-error.p-message-simple {
        color: dt('message.error.simple.color');
    }

    .p-message-secondary {
        background: dt('message.secondary.background');
        outline-color: dt('message.secondary.border.color');
        color: dt('message.secondary.color');
        box-shadow: dt('message.secondary.shadow');
    }

    .p-message-secondary .p-message-close-button:focus-visible {
        outline-color: dt('message.secondary.close.button.focus.ring.color');
        box-shadow: dt('message.secondary.close.button.focus.ring.shadow');
    }

    .p-message-secondary .p-message-close-button:hover {
        background: dt('message.secondary.close.button.hover.background');
    }

    .p-message-secondary.p-message-outlined {
        color: dt('message.secondary.outlined.color');
        outline-color: dt('message.secondary.outlined.border.color');
    }

    .p-message-secondary.p-message-simple {
        color: dt('message.secondary.simple.color');
    }

    .p-message-contrast {
        background: dt('message.contrast.background');
        outline-color: dt('message.contrast.border.color');
        color: dt('message.contrast.color');
        box-shadow: dt('message.contrast.shadow');
    }

    .p-message-contrast .p-message-close-button:focus-visible {
        outline-color: dt('message.contrast.close.button.focus.ring.color');
        box-shadow: dt('message.contrast.close.button.focus.ring.shadow');
    }

    .p-message-contrast .p-message-close-button:hover {
        background: dt('message.contrast.close.button.hover.background');
    }

    .p-message-contrast.p-message-outlined {
        color: dt('message.contrast.outlined.color');
        outline-color: dt('message.contrast.outlined.border.color');
    }

    .p-message-contrast.p-message-simple {
        color: dt('message.contrast.simple.color');
    }

    .p-message-text {
        font-size: dt('message.text.font.size');
        font-weight: dt('message.text.font.weight');
    }

    .p-message-icon {
        font-size: dt('message.icon.size');
        width: dt('message.icon.size');
        height: dt('message.icon.size');
    }

    .p-message-sm .p-message-content {
        padding: dt('message.content.sm.padding');
    }

    .p-message-sm .p-message-text {
        font-size: dt('message.text.sm.font.size');
    }

    .p-message-sm .p-message-icon {
        font-size: dt('message.icon.sm.size');
        width: dt('message.icon.sm.size');
        height: dt('message.icon.sm.size');
    }

    .p-message-sm .p-message-close-icon {
        font-size: dt('message.close.icon.sm.size');
        width: dt('message.close.icon.sm.size');
        height: dt('message.close.icon.sm.size');
    }

    .p-message-lg .p-message-content {
        padding: dt('message.content.lg.padding');
    }

    .p-message-lg .p-message-text {
        font-size: dt('message.text.lg.font.size');
    }

    .p-message-lg .p-message-icon {
        font-size: dt('message.icon.lg.size');
        width: dt('message.icon.lg.size');
        height: dt('message.icon.lg.size');
    }

    .p-message-lg .p-message-close-icon {
        font-size: dt('message.close.icon.lg.size');
        width: dt('message.close.icon.lg.size');
        height: dt('message.close.icon.lg.size');
    }

    .p-message-outlined {
        background: transparent;
        outline-width: dt('message.outlined.border.width');
    }

    .p-message-simple {
        background: transparent;
        outline-color: transparent;
        box-shadow: none;
    }

    .p-message-simple .p-message-content {
        padding: dt('message.simple.content.padding');
    }

    .p-message-outlined .p-message-close-button:hover,
    .p-message-simple .p-message-close-button:hover {
        background: transparent;
    }

    .p-message-enter-active {
        animation: p-animate-message-enter 0.3s ease-out forwards;
        overflow: hidden;
    }

    .p-message-leave-active {
        animation: p-animate-message-leave 0.15s ease-in forwards;
        overflow: hidden;
    }

    @keyframes p-animate-message-enter {
        from {
            opacity: 0;
            grid-template-rows: 0fr;
        }
        to {
            opacity: 1;
            grid-template-rows: 1fr;
        }
    }

    @keyframes p-animate-message-leave {
        from {
            opacity: 1;
            grid-template-rows: 1fr;
        }
        to {
            opacity: 0;
            margin: 0;
            grid-template-rows: 0fr;
        }
    }
`,U={root:function(n){var s=n.props;return["p-message p-component p-message-"+s.severity,{"p-message-outlined":s.variant==="outlined","p-message-simple":s.variant==="simple","p-message-sm":s.size==="small","p-message-lg":s.size==="large"}]},contentWrapper:"p-message-content-wrapper",content:"p-message-content",icon:"p-message-icon",text:"p-message-text",closeButton:"p-message-close-button",closeIcon:"p-message-close-icon"},W=k.extend({name:"message",style:K,classes:U}),x={name:"BaseMessage",extends:$,props:{severity:{type:String,default:"info"},closable:{type:Boolean,default:!1},life:{type:Number,default:null},icon:{type:String,default:void 0},closeIcon:{type:String,default:void 0},closeButtonProps:{type:null,default:null},size:{type:String,default:null},variant:{type:String,default:null}},style:W,provide:function(){return{$pcMessage:this,$parentInstance:this}}};function p(e){"@babel/helpers - typeof";return p=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(n){return typeof n}:function(n){return n&&typeof Symbol=="function"&&n.constructor===Symbol&&n!==Symbol.prototype?"symbol":typeof n},p(e)}function y(e,n,s){return(n=V(n))in e?Object.defineProperty(e,n,{value:s,enumerable:!0,configurable:!0,writable:!0}):e[n]=s,e}function V(e){var n=X(e,"string");return p(n)=="symbol"?n:n+""}function X(e,n){if(p(e)!="object"||!e)return e;var s=e[Symbol.toPrimitive];if(s!==void 0){var o=s.call(e,n);if(p(o)!="object")return o;throw new TypeError("@@toPrimitive must return a primitive value.")}return(n==="string"?String:Number)(e)}var J={name:"Message",extends:x,inheritAttrs:!1,emits:["close","life-end"],timeout:null,data:function(){return{visible:!0}},mounted:function(){var n=this;this.life&&setTimeout(function(){n.visible=!1,n.$emit("life-end")},this.life)},methods:{close:function(n){this.visible=!1,this.$emit("close",n)}},computed:{closeAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria.close:void 0},dataP:function(){return T(y(y({outlined:this.variant==="outlined",simple:this.variant==="simple"},this.severity,this.severity),this.size,this.size))}},directives:{ripple:j},components:{TimesIcon:S}};function g(e){"@babel/helpers - typeof";return g=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(n){return typeof n}:function(n){return n&&typeof Symbol=="function"&&n.constructor===Symbol&&n!==Symbol.prototype?"symbol":typeof n},g(e)}function v(e,n){var s=Object.keys(e);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);n&&(o=o.filter(function(l){return Object.getOwnPropertyDescriptor(e,l).enumerable})),s.push.apply(s,o)}return s}function w(e){for(var n=1;n<arguments.length;n++){var s=arguments[n]!=null?arguments[n]:{};n%2?v(Object(s),!0).forEach(function(o){F(e,o,s[o])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(s)):v(Object(s)).forEach(function(o){Object.defineProperty(e,o,Object.getOwnPropertyDescriptor(s,o))})}return e}function F(e,n,s){return(n=Q(n))in e?Object.defineProperty(e,n,{value:s,enumerable:!0,configurable:!0,writable:!0}):e[n]=s,e}function Q(e){var n=Y(e,"string");return g(n)=="symbol"?n:n+""}function Y(e,n){if(g(e)!="object"||!e)return e;var s=e[Symbol.toPrimitive];if(s!==void 0){var o=s.call(e,n);if(g(o)!="object")return o;throw new TypeError("@@toPrimitive must return a primitive value.")}return(n==="string"?String:Number)(e)}var Z=["data-p"],_=["data-p"],ee=["data-p"],ne=["aria-label","data-p"],se=["data-p"];function oe(e,n,s,o,l,a){var m=I("TimesIcon"),P=O("ripple");return r(),b(D,t({name:"p-message",appear:""},e.ptmi("transition")),{default:C(function(){return[l.visible?(r(),i("div",t({key:0,class:e.cx("root"),role:"alert","aria-live":"assertive","aria-atomic":"true","data-p":a.dataP},e.ptm("root")),[u("div",t({class:e.cx("contentWrapper")},e.ptm("contentWrapper")),[e.$slots.container?c(e.$slots,"container",{key:0,closeCallback:a.close}):(r(),i("div",t({key:1,class:e.cx("content"),"data-p":a.dataP},e.ptm("content")),[c(e.$slots,"icon",{class:E(e.cx("icon"))},function(){return[(r(),b(B(e.icon?"span":null),t({class:[e.cx("icon"),e.icon],"data-p":a.dataP},e.ptm("icon")),null,16,["class","data-p"]))]}),e.$slots.default?(r(),i("div",t({key:0,class:e.cx("text"),"data-p":a.dataP},e.ptm("text")),[c(e.$slots,"default")],16,ee)):d("",!0),e.closable?A((r(),i("button",t({key:1,class:e.cx("closeButton"),"aria-label":a.closeAriaLabel,type:"button",onClick:n[0]||(n[0]=function(z){return a.close(z)}),"data-p":a.dataP},w(w({},e.closeButtonProps),e.ptm("closeButton"))),[c(e.$slots,"closeicon",{},function(){return[e.closeIcon?(r(),i("i",t({key:0,class:[e.cx("closeIcon"),e.closeIcon],"data-p":a.dataP},e.ptm("closeIcon")),null,16,se)):(r(),b(m,t({key:1,class:[e.cx("closeIcon"),e.closeIcon],"data-p":a.dataP},e.ptm("closeIcon")),null,16,["class","data-p"]))]})],16,ne)),[[P]]):d("",!0)],16,_))],16)],16,Z)):d("",!0)]}),_:3},16)}J.render=oe;const te={class:"page-header"},ae={class:"eyebrow"},re={class:"page-description"},ie={class:"page-header-actions"},me=N({__name:"PageHeader",props:{eyebrow:{},title:{},description:{}},setup(e){return(n,s)=>(r(),i("div",te,[u("div",null,[u("p",ae,h(e.eyebrow),1),u("h1",null,h(e.title),1),u("p",re,h(e.description),1)]),u("div",ie,[c(n.$slots,"actions")])]))}});function ce(e,n={}){const s=new URL(e,window.location.origin),o=n.tenantId?.trim(),l=n.apiToken?.trim();return o&&s.searchParams.set("tenant_id",o),l&&s.searchParams.set("api_token",l),`${s.pathname}${s.search}`}async function le(e){try{const n=await e.json();if(n&&typeof n.detail=="string")return new Error(n.detail);if(n&&Array.isArray(n.detail))return new Error(n.detail.map(s=>typeof s=="string"?s:s.msg||String(s)).join("; "))}catch{}return new Error(e.statusText||`Request failed with ${e.status}`)}function de(e){const n={"Content-Type":"application/json"},s=e.tenantId?.trim(),o=e.apiToken?.trim();return s&&(n["X-TradingAgents-Tenant"]=s),o&&(n["X-TradingAgents-Token"]=o),n}async function f(e,n,s={},o){const l=s.fetchImpl||fetch,a={headers:de(s)};e!=="GET"&&(a.method=e),o!==void 0&&(a.body=typeof o=="string"?o:JSON.stringify(o));const m=await l(ce(n,s),a);if(!m.ok)throw await le(m);if(m.status!==204)return m.json()}function pe(e,n={}){return f("GET",e,n)}function ge(e,n,s={}){return f("POST",e,s,n)}function fe(e,n,s={}){return f("PUT",e,s,n)}function be(e,n,s={}){return f("PATCH",e,s,n)}function he(e,n={}){return f("DELETE",e,n)}export{me as _,q as a,pe as b,ge as c,ce as d,he as e,be as f,fe as g,J as s};
