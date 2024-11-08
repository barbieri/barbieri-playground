import F from"child_process";import S from"fs";import O from"net";function v(...e){console.error("ERROR:",...e),process.exit(1)}var k=process.env.DEBUG==="1",c=k?console.log:()=>{},w={interval:1e3,maxRetries:10},y=(e,{interval:s=w.interval,maxRetries:t=w.maxRetries}={})=>new Promise((i,r)=>{let o=0,a=Date.now(),{host:n,port:f,...u}=e,l=`${[n,f].concat(Object.entries(u).map(([d,m])=>`${d}=${JSON.stringify(m)}`)).join(":")}:`;function b(){c(`${l} connecting to server!`);let d=O.createConnection(e,()=>{c(`${l} connected to server!`),d.end()});d.on("data",m=>{c(`${l} data=${m}`),d.end()}),d.on("end",()=>{c(`${l} disconnected from server`),i()}),d.on("error",m=>{if(o+=1,c(`${l} #${o} failed to connect:`,m),o===t){let x=(Date.now()-a)/1e3;r(new Error(`${l} could not connect. ${o} tries, elapsed ${x} seconds`))}setTimeout(b,s)})}b()}),g={exclusive:!0,failFileReadError:!0,trimFileContents:"both",required:!0};function P(e,{defaultValue:s,varFileName:t,exclusive:i=g.exclusive,failFileReadError:r=g.failFileReadError,trimFileContents:o=g.trimFileContents,required:a=g.required}={}){let{env:n}=process,f=t??`${e}_FILE`,u=n[e],p=n[f];if(c("fileEnv",{varName:e,varValue:u,varFileName:f,varFileNameValue:p}),i&&u&&p)throw new Error(`both ${e} and ${f} are set, but they are mutually exclusive!`);if(!u){if(p)try{let l=S.readFileSync(p,{encoding:"utf-8"});switch(o){case"both":l=l.trim();break;case"start":l=l.trimStart();break;case"end":l=l.trimEnd();break;case"none":default:break}c(`fileEnv: set ${e}=${JSON.stringify(l)}`),n[e]=l;return}catch(l){if(r)throw l}if(s!==void 0){n[e]=s;return}if(a)throw new Error(`missing environment variable ${e} (alternatively loaded from ${f})`)}}function h(e,s,t){let i=[],r=e;for(;i.length<t-1;){let o=r.indexOf(s);if(o<0)break;i.push(r.substring(0,o)),r=r.substring(o+1)}return i.push(r),i}function R(e){let[s,t]=h(e,":",2),i=t?JSON.parse(t):void 0;return P(s,i)}function N(e){let[s,t,i]=h(e,":",3),r=i?JSON.parse(i):void 0;if(!s)throw new Error("missing host, format: host:port[:options]");if(!t)throw new Error("missing port, format: host:port[:options]");let o=Number(t);return y({host:s,port:o},r)}var $=/[A-Za-z0-9_]/;function E(e){let s="",t=!1,i,r="";function o(a){let n=process.env[r];n===void 0&&a===void 0&&c(`missing env var ${r} (expanded to empty string)`),s+=n??a??"",r="",i=void 0}for(let a=0;a<e.length;a+=1){let n=e[a];if(i==="simple")$.test(n)?r+=n:n==="{"?i="braces":(a-=1,o());else if(i==="braces")if($.test(n))r+=n;else if(n===":"&&e[a+1]==="-"){let f=e.indexOf("}",a+2);if(f<0)throw new Error(`missing '}' (variable: ${r})`);let u=e.substring(a+2,f);a=f+1,o(u)}else{if(n!=="}")throw new Error(`position ${a} '${n}' while '}' was expected (variable: ${r})`);o()}else t?(t=!1,s+=n):n==="\\"?t=!0:n==="$"?i="simple":s+=n}if(i==="simple")o();else if(i==="braces")throw new Error(`unterminated env var ${r} (missing '}')`);return s}async function C(e=process.argv){c("docker-entrypoint:",e);let s=[],t=2;for(;t<e.length;t+=1){let o=E(e[t]);if(!o.startsWith("--"))break;let[a,n]=h(o.substring(2),"=",2);if(a===""){t+=1;break}switch(a){case"file-env":n||(t+=1,n=e[t],n||v("missing --file-env value")),R(n);break;case"wait-server":n||(t+=1,n=e[t],n||v("missing --wait-server value")),s.push(N(n));break;default:v(`unknown flag ${a} (${e[t]})`)}}s.length&&(c(`waiting ${s.length} servers...`),await Promise.all(s));let i=e[t];i||v("missing javascript file to run");let r=e.slice(t+1).map(E);c("fork:",i,r),F.fork(i,r)}function D(){return process.argv.length===1?!1:import.meta?.filename===process.argv[1]}D()&&C().catch(e=>v(e));export{v as die,P as fileEnv,R as handleFileEnvFlag,N as handleWaitServerFlag,C as main,y as waitServer};
//! Copyright (C) 2023-2024 Gustavo Sverzut Barbieri <barbieri@profusion.mobi>
//! License: MIT
//! Source: https://github.com/barbieri/barbieri-playground/tree/master/docker/distroless/nodejs/
