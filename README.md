# GolfCut 官网

基于 https://golfcut-web.pastelcake18.chatgpt.site/ 原型迁移，沿用 AceCut 的静态网站 + Bun + Vercel 方案。首页、4 个功能页、18 个源文件及素材均已落地；保留原型的 AI Stories、滤镜、FAQ、移动导航及真实 App Store 链接。

## 开发与构建

```sh
bun install
bun run dev
bun run build
bun run preview
```

验证使用 Bun 1.4.3。无需第三方运行依赖。若 bun 不在 PATH，可先执行 `export PATH="$HOME/.bun/bin:$PATH"`。`public/` 为源码，`dist/` 为静态发布产物，默认预览地址 http://127.0.0.1:4173，可使用 `PORT`、`HOST` 覆盖。

- 首页：`public/index.html`
- 样式：`public/style.css`
- 交互：`public/app.js`
- 两个下载按钮共用 SVG：`public/assets/app-store-badge.svg`；其两个背景路径及按钮 CSS 均设为 `#123E32`，白色文字和 Apple 图形保持。
- 法律页面：`public/terms.html`、`public/privacy.html`，阅读样式 `public/legal.css`
- 全站页脚：`© 2026 SWINK AI INC.`、`hello@goswie.com`、Terms / Privacy，与 AceCut 公司信息对齐。法律内容按 GolfCut 的 AI Stories、Swing Cut 和 Shot Tracer 改写，未复制 AceCut 专属统计及处理方式声明。
- 功能页：`public/{ai-golf-video-editor,automatic-swing-cut,golf-shot-tracer,golf-video-effects}/index.html`
- App Store：https://apps.apple.com/us/app/golfcut-shot-tracer-ai-edit/id6808229443
- canonical、Open Graph、JSON-LD、robots、sitemap 目标：https://golfcut.goswie.com

页面内容保留原型，移除了原托管平台注入的 Cloudflare challenge 脚本。字体仍使用原型的 Google Fonts，在无法联网时使用系统回退字体。

## 部署及子域名

**状态：代码已推送，Vercel 项目已创建并完成生产部署；自定义域名 DNS 已通过 Vercel 验证。**

- GitHub：https://github.com/diifan/golfcut-website （main，已关联 Vercel）
- 公开预览：https://golfcut-website.vercel.app
- 项目：https://vercel.com/diifans-projects/golfcut-website
- 团队：`diifans-projects`，与 AceCut 相同
- 2026-10-27 首次部署：`dpl_CUCRPkLAhhAbJtQK2WXm19CSCRTZ`，READY
- 已配置：Other / `bun install` / `bun run build` / `dist`
- 已添加域名：`golfcut.goswie.com`；Vercel DNS 检查已通过
- GoDaddy 已配置：CNAME，Name `golfcut`，Value `75135cd2d0614f92.vercel-dns-017.com`，TTL 默认。此值是该项目当前实际返回值，其他 App 必须重新读取自己的值。

官网首页、4 个功能页及 CSS、JS、徽章、robots、sitemap 已通过公网 HTTP 检查。下面保留新项目的通用操作步骤。

1. 将本目录放入独立官网仓库（例如 `golfcut-website`），或在有登录状态的 Vercel CLI 中直接部署本目录。
2. Vercel 导入时 Framework 选择 Other；独立仓库 Root Directory 为 `./`，若使用 GolfCut 应用仓库则为 `website/`。
3. `vercel.json` 已设置 `bun install`、`bun run build`、输出 `dist`、clean URLs 和无尾斜杠规范。部署后先验证 Vercel 返回的部署地址。
4. 在 GolfCut 的 Vercel 项目添加 `golfcut.goswie.com`，读取该项目返回的 CNAME 值。
5. GoDaddy → goswie.com → DNS，添加 CNAME，Name 为 `golfcut`，Value 使用上一步真实返回值。不得照抄 AceCut 的 CNAME，也不要改动 `@`、`www`、MX、Nameservers。若有冲突，先核实记录用途；如需 TXT 验证，添加 Vercel 指定值。
6. 等待域名配置有效、HTTPS 证书生效，验证首页、四个功能页、下载链接和移动布局。

参考：[Vercel 域名配置](https://vercel.com/docs/domains/working-with-domains/add-a-domain)、[GoDaddy CNAME](https://www.godaddy.com/help/add-a-cname-record-19236)。

## 直接通过 CLI 发布（无需先建 GitHub 仓库）

在服务器以有权读取本目录且已安装 Bun 的用户运行：

```sh
cd /data/swi-algo/Swi-App-Factory/GolfCut/website
export PATH="$HOME/.bun/bin:$PATH"
bun x vercel login
bun x vercel --prod
```

在浏览器中完成 Vercel 登录授权。部署提示中选择 AceCut 所在的账号/团队；首次不关联旧项目，创建 `golfcut-website`，代码目录选择 `./`。仓库内 `vercel.json` 已提供 Bun 构建及 dist 输出设置。后续更新在同目录运行 `bun x vercel --prod`。

如当前用户没有安装 Bun，先安装 Bun，或使用已安装 Bun 的 swi-codex 用户执行。不要把账号 token 写入仓库。

部署后打开 Vercel Dashboard → golfcut-website → Settings → Domains，添加 golfcut.goswie.com；随后按上面的 GoDaddy CNAME 步骤操作。GitHub 推送、Vercel 创建和部署已完成；GoDaddy DNS 由用户操作。

## 可复用技能

本项目 `skills/app-website/SKILL.md` 保存完整流程及 Bun starter，副本安装在 `/var/lib/swi-codex/.codex/skills/app-website/`。后续可使用 `$app-website` 并提供 App 名称、原型和目标域名。初始化脚本拒绝覆盖非空目录。

## 验证

### Google Search Console

- 所有权验证文件：`public/google828db80516d18f39.html`，构建时原样复制到 `dist/`。验证成功后也必须保留此文件。
- 验证地址：`https://golfcut.goswie.com/google828db80516d18f39.html`。Vercel 的 `cleanUrls` 会重定向到同域名的无扩展名地址；Google 支持同域名验证文件重定向。上线后须确认最终响应为 200，内容与原文件完全一致。
- 在 GSC 的 `https://golfcut.goswie.com/` 资源中点击 Verify，成功后提交 `https://golfcut.goswie.com/sitemap.xml`。
- 参考：https://support.google.com/webmasters/answer/9008080

已通过 1440、768、390、320 像素宽度的渲染、无横向溢出、图片加载，以及故事切换/键盘、滤镜、FAQ、移动菜单检查；5 个页面无脚本或资源响应错误。98 处本地资源/锚点、SVG 颜色和 sitemap 校验通过。详见 `validation/results.json` 和对应宽度截图（不进入发布目录）。当前环境对本地回环端口的访问超时，因此浏览器验证通过 Playwright 将构建产物作为 HTTP 响应提供；这验证页面渲染和交互，不代表真实部署或服务器网络已验证。Bun build 和预览服务启动均成功。正式发布后仍需真实 HTTP/HTTPS 验证。
