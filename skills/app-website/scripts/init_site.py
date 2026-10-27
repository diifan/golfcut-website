#!/usr/bin/env python3
"""Create a dependency-free Bun website without overwriting an existing project."""
import argparse, json, pathlib, re, shutil
p=argparse.ArgumentParser()
p.add_argument('destination',type=pathlib.Path)
p.add_argument('--slug',required=True)
a=p.parse_args()
if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',a.slug):p.error('slug must be lowercase letters, digits and hyphens')
if a.destination.exists() and any(a.destination.iterdir()):p.error('destination must be empty')
source=pathlib.Path(__file__).resolve().parents[1]/'assets/starter'
shutil.copytree(source,a.destination,dirs_exist_ok=True)
(a.destination/'public').mkdir(exist_ok=True)
(a.destination/'package.json').write_text(json.dumps({'name':a.slug+'-website','version':'0.1.0','private':True,'type':'module','scripts':{'dev':'bun --watch scripts/serve.mjs','build':'bun scripts/build.mjs','preview':'bun scripts/serve.mjs --dist'},'engines':{'bun':'>=1.2.0'},'packageManager':'bun@1.4.3'},indent=2)+'\n')
(a.destination/'.gitignore').write_text('node_modules/\ndist/\n.vercel/\nvalidation/\n.env*\n.DS_Store\n')
print('Created',a.destination,'— put website source in public/, then bun run build')
