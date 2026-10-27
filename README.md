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
- 功能页：`public/{ai-golf-video-editor,automatic-swing-cut,golf-shot-tracer,golf-video-effects}/index.html`
- App Store：https://apps.apple.com/us/app/golfcut-shot-tracer-ai-edit/id6808229443
- canonical、Open Graph、JSON-LD、robots、sitemap 目标：https://golfcut.goswie.com

页面内容保留原型，移除了原托管平台注入的 Cloudflare challenge 脚本。字体仍使用原型的 Google Fonts，在无法联网时使用系统回退字体。

## 部署及子域名

**状态：本地构建完成；GitHub 目标仓库为 https://github.com/diifan/golfcut-website；Vercel 部署和自定义域名尚未验证完成。** 2026-10-27 查询公共 DNS 返回 NXDOMAIN。目录写权限已通过 ubuntu 管理员修复，项目已落地 GolfCut/website；Vercel、GoDaddy 账户接入仍待完成。

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

部署后打开 Vercel Dashboard → golfcut-website → Settings → Domains，添加 golfcut.goswie.com；随后按上面的 GoDaddy CNAME 步骤操作。后续要求已更新为：推送到 diifan/golfcut-website 并创建 Vercel 项目；GoDaddy DNS 由用户操作。

## 可复用技能

本项目 `skills/app-website/SKILL.md` 保存完整流程及 Bun starter，副本安装在 `/var/lib/swi-codex/.codex/skills/app-website/`。后续可使用 `$app-website` 并提供 App 名称、原型和目标域名。初始化脚本拒绝覆盖非空目录。

## 验证

已通过 1440、768、390、320 像素宽度的渲染、无横向溢出、图片加载，以及故事切换/键盘、滤镜、FAQ、移动菜单检查；5 个页面无脚本或资源响应错误。98 处本地资源/锚点、SVG 颜色和 sitemap 校验通过。详见 `validation/results.json` 和对应宽度截图（不进入发布目录）。当前环境对本地回环端口的访问超时，因此浏览器验证通过 Playwright 将构建产物作为 HTTP 响应提供；这验证页面渲染和交互，不代表真实部署或服务器网络已验证。Bun build 和预览服务启动均成功。正式发布后仍需真实 HTTP/HTTPS 验证。
