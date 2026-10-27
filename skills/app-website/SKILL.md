---
name: app-website
description: Build or migrate an app marketing website from a supplied prototype using Bun, following the AceCut static website convention, and prepare or complete Vercel hosting and an app subdomain. Use for app official websites; not native app development.
---

# App website

Deliver the user's supplied design as a standalone static site, with reproducible Bun development/build commands and explicit deployment status. Preserve the requested hosting provider. This workflow comes from AceCut (`/data/swi-algo/Swi-App-Factory/Acecut/website`) and GolfCut; those projects are examples, not required dependencies.

## Establish inputs

Read applicable AGENTS.md and inspect the prototype, existing website and deployment documentation. Identify the app name, destination directory, canonical domain, real App Store URL and requested visual changes. Reuse existing branding and content. Check filesystem write access and hosting/DNS authentication early; continue local preparation if deployment access is unavailable. Do not treat unavailable authentication as deployment success.

## Prepare a Bun project

For a new static website, initialize an empty directory:

```sh
python3 <skill-directory>/scripts/init_site.py <app-directory>/website --slug <app-slug>
cd <app-directory>/website
bun install
```

The bundled starter contains the verified build/preview scripts and Vercel configuration. Keep an existing project's tooling when appropriate. `public/` contains source; `scripts/build.mjs` copies it to `dist/`; production requires no Bun server. No dependency is needed for plain HTML/CSS/JS. If Bun is absent from PATH, check `~/.bun/bin/bun` before installing anything. Do not copy `.git`, `.vercel`, credentials or identity from another app.

## Transfer the prototype

Prefer an authorized source export or repository. If only a public static prototype is available, retrieve HTML and recursively inspect same-origin HTML `src`/`href` and CSS `url()` dependencies, including feature pages, icons, SVGs and scripts. Fetch with curl if the host rejects the Python HTTP client. Fail visibly on missing resources; do not save error bodies as images. Map directory routes to `public/<route>/index.html`.

Keep assets local. Remove hosting-injected Cloudflare challenge scripts and preview-only metadata from fetched HTML, preserving application JS. Do not copy service credentials or add analytics without a requirement. Review external dependencies such as Google Fonts. Preserve the prototype's app links; never invent an App Store ID or silently substitute another app's legal terms.

Replace prototype origins in canonical URLs, Open Graph, JSON-LD, robots and sitemap with the intended production origin. Preserve page paths consistently. For button color requests, inspect the rendered asset as well as CSS: a filled SVG can conceal a CSS background. Change only the intended SVG background paths and preserve logo/text paths, accessible names and link targets.

## Build and verify

```sh
bun run build
bun run preview
```

The local server supports directory index routes and `.html` clean URLs, GET and HEAD, and returns 404 for missing files. Validate every page and local asset over HTTP; confirm sitemap and canonical URLs. Check desktop and narrow mobile widths (for example 1440, 768, 390 and 320), overflow, loaded images, browser errors, menus, tabs/keyboard controls, FAQ, filters and download targets as applicable. Capture review screenshots outside `public/`. When color is represented by an SVG, inspect its paths or screenshot pixels as well as computed CSS.

## GitHub publication and machine access

On the SWI machine, AceCut was pushed using the existing GitHub CLI login under Linux user `ubuntu` (GitHub identity `CC-AIMI`). Confirm the current identity and repository write permission with `gh repo view <owner>/<repo> --json viewerPermission,defaultBranchRef,isEmpty` before relying on this precedent. A network/proxy error is not proof of an invalid login. If Git asks for a username despite a working `gh` login, use a per-command credential helper in that same authenticated Linux account: `git -c credential.helper='!gh auth git-credential' push origin <branch>`. This reuses the existing login without exposing its token or changing global Git configuration. Do not copy credentials between accounts or put passwords/tokens in this skill, shell arguments, source files or logs.

When a user authorizes an administrator account to resolve a Unix permission issue, inspect `id` and `getfacl`, and grant only the needed project access (for example `setfacl -m u:<executor>:rwx,d:u:<executor>:rwx <project>`). Preserve owner/group and unrelated permissions. An administrator login does not authenticate Vercel or GoDaddy.

If an explicitly requested repository already exists, clone it first and preserve its history; do not force-push an unrelated initial commit. Place the website files at repository root, not in another `website/` layer. Exclude `.git`, `.vercel`, `dist`, `node_modules`, validation screenshots and secrets when transferring prepared source. If publishing through another authorized Linux account, use a temporary checkout owned by that account and grant only required read access to source. Configure the repository's intended author locally, inspect staged files, commit, push to the intended branch, and verify the remote SHA. Keep the main working checkout synchronized afterward.

For a standalone repo such as `diifan/golfcut-website`, Vercel must import that repo with Root Directory `./`. A GitHub push alone does not create a Vercel project.

## Vercel and DNS

The starter uses framework `null` (dashboard: Other), `bun install`, `bun run build`, output `dist`, `cleanUrls: true`, `trailingSlash: false`. In a standalone website repository, set Vercel Root Directory to `./`; in an app monorepo, use `website/`. GitHub integration is optional if an authenticated Vercel CLI/API can deploy directly. Follow the user's authorized publication scope without adding another approval gate.

Inspect the authenticated account/team and existing project before creating or linking. If CLI login is needed, run `bun x vercel login` and send the current device authorization URL to the user; keep the process alive while completing independent work. `bun x` works even when the `bunx` shim is missing. Never claim login until the CLI confirms it. After login, inspect available teams and AceCut's project, select the same intended scope, create/link the new app project, connect its exact GitHub repository, then deploy. Prefer a connected Vercel plugin if it supplies these capabilities. Do not reuse expired device codes or assume a suggested plugin is connected. Never reuse another app's project ID. Deploy the built website and verify its returned deployment URL. For a requested `app.goswie.com`, add that exact domain to its Vercel project, then obtain the project's current DNS recommendation. On the authoritative DNS provider (AceCut documents GoDaddy), create/update only the requested app record, usually CNAME host `app`. Use the target returned by Vercel, not a guessed or copied AceCut target. Preserve unrelated records, especially `@`, `www`, MX and nameservers. Resolve an ownership/conflict before replacing an existing unrelated record. Add only a requested verification TXT record when Vercel requires it.

Verify public DNS, Vercel domain status, HTTPS and the deployed pages. If credentials are missing, finish the build and document the exact remaining account action; distinguish prepared configuration, completed deployment and verified domain. Never label a planned domain as live.

Current official references (consult when doing deployment work):
- [Vercel project configuration](https://vercel.com/docs/project-configuration)
- [Vercel custom domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [GoDaddy CNAME records](https://www.godaddy.com/help/add-a-cname-record-19236)

## Handoff

Record source origin, commands, build output, validation evidence and remaining limitations in the website README. Keep generated output, local validation artifacts, environment files and provider credentials out of Git. Report the actual live URL only after successful deployment; otherwise provide the ready project and precise blocker.
