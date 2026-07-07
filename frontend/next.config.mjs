/** @type {import('next').NextConfig} */
// Static export: the app is fully client-side, so Cloudflare Pages serves
// plain files — no server runtime, no adapter. NEXT_PUBLIC_* values are baked
// in at build time; set them before `npm run build`.
export default { output: "export" };
