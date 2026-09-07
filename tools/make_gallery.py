#!/usr/bin/env python3
"""Build a private artifact page that embeds upscaled images and lets the viewer save each one.
usage: python3 make_gallery.py out.html "Page Title" img1.jpg [img2.jpg ...]
Each image is embedded as a data URI (never passes through the chat); the page offers
`downloads.save()` per image. Keep total under ~11 MB of JPEG per page (16 MB page limit).
"""
import sys, base64, json, os
from PIL import Image

out, title, files = sys.argv[1], sys.argv[2], sys.argv[3:]
items = []
for f in files:
    im = Image.open(f)
    with open(f, 'rb') as fh:
        b64 = base64.b64encode(fh.read()).decode()
    ext = os.path.splitext(f)[1].lower().lstrip('.')
    mime = 'image/png' if ext == 'png' else 'image/jpeg'
    items.append(dict(name=os.path.basename(f), w=im.size[0], h=im.size[1],
                      dpi=int((im.info.get('dpi') or (0, 0))[0]), kb=os.path.getsize(f) // 1024,
                      src=f'data:{mime};base64,{b64}'))

cards = ''.join(f'''
<figure class="card">
  <img src="{it['src']}" alt="{it['name']}" loading="lazy">
  <figcaption>
    <span class="name">{it['name']}</span>
    <span class="meta">{it['w']} × {it['h']} px · {it['dpi']} dpi · {it['kb']} KB</span>
    <button type="button" data-i="{i}">この画像を保存</button>
    <span class="status" id="st{i}"></span>
  </figcaption>
</figure>''' for i, it in enumerate(items))

html = f'''<title>{title}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700&family=IBM+Plex+Sans+JP:wght@400;500&display=swap">
<style>
:root{{--bg:#f3f1ec;--ink:#1f2422;--mute:#6b7370;--line:#d9d4c9;--accent:#2f5e6b;--accent-ink:#ffffff;--card:#fbfaf7}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#171a19;--ink:#ece8df;--mute:#9aa39f;--line:#33393a;--accent:#7fb4c1;--accent-ink:#0f1a1d;--card:#20242399}}}}
:root[data-theme="dark"]{{--bg:#171a19;--ink:#ece8df;--mute:#9aa39f;--line:#33393a;--accent:#7fb4c1;--accent-ink:#0f1a1d;--card:#20242399}}
body{{background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans JP",system-ui,sans-serif;padding:32px 24px 64px;max-width:1100px;margin:0 auto}}
h1{{font-family:"Shippori Mincho","Hiragino Mincho ProN",serif;font-weight:700;font-size:1.6rem;margin:0 0 6px;text-wrap:balance}}
p.lead{{color:var(--mute);margin:0 0 28px;max-width:60ch;line-height:1.6}}
.grid{{display:grid;gap:28px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}}
.card{{margin:0;background:var(--card);border:1px solid var(--line);display:flex;flex-direction:column}}
.card img{{width:100%;height:auto;display:block;border-bottom:1px solid var(--line)}}
figcaption{{padding:12px 14px 14px;display:grid;gap:6px}}
.name{{font-weight:500;word-break:break-all}}
.meta{{color:var(--mute);font-size:.85rem;font-variant-numeric:tabular-nums}}
button{{justify-self:start;margin-top:4px;background:var(--accent);color:var(--accent-ink);border:0;padding:8px 14px;font:inherit;font-size:.9rem;cursor:pointer}}
button:focus-visible{{outline:2px solid var(--ink);outline-offset:2px}}
button[disabled]{{opacity:.5;cursor:default}}
.status{{font-size:.85rem;color:var(--mute);min-height:1.2em}}
</style>
<h1>{title}</h1>
<p class="lead">各画像の下の「この画像を保存」を押すと、ブラウザの保存確認が出ます。画像を右クリックして保存することもできます。</p>
<div class="grid">{cards}</div>
<script>
const ITEMS = {json.dumps([dict(name=it['name']) for it in items], ensure_ascii=False)};
let dl = null;
(async () => {{ try {{ dl = await claude.use("downloads"); }} catch (e) {{ dl = null; }}
  if (!dl) document.querySelectorAll('button[data-i]').forEach(b => {{ b.disabled = true; b.textContent = '保存ボタンは使えません（右クリックで保存してください）'; }});
}})();
document.querySelectorAll('button[data-i]').forEach(b => b.addEventListener('click', async () => {{
  const i = +b.dataset.i, st = document.getElementById('st' + i);
  const img = document.querySelectorAll('.card img')[i];
  st.textContent = '準備中…';
  try {{
    // decode the data URI ourselves: fetch() on data: URLs is blocked by the page's security policy
    const src = img.getAttribute('src');
    const comma = src.indexOf(',');
    const mime = src.slice(5, src.indexOf(';'));
    const bin = atob(src.slice(comma + 1));
    const bytes = new Uint8Array(bin.length);
    for (let k = 0; k < bin.length; k++) bytes[k] = bin.charCodeAt(k);
    const blob = new Blob([bytes], {{ type: mime }});
    const r = await dl.save({{ filename: ITEMS[i].name, data: blob }});
    st.textContent = r && r.status === 'saved' ? '保存しました' : '保存しました';
  }} catch (e) {{
    st.textContent = e && e.code === 'declined' ? '保存をキャンセルしました' : '保存できませんでした: ' + (e && e.message || e);
  }}
}}));
</script>
'''
with open(out, 'w', encoding='utf-8') as fh:
    fh.write(html)
print(f'{out}: {len(items)} images, {os.path.getsize(out) / 1e6:.1f} MB')
