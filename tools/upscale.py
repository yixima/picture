#!/usr/bin/env python3
"""Real-ESRGAN x4plus upscaler, CPU, standalone (no basicsr dependency).
usage: python3 upscale.py in.jpg out.png [--min-width 2000] [--dpi 300]
"""
import time, argparse, math
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
from PIL import Image, ImageOps


class RDB(nn.Module):
    def __init__(s, nf=64, gc=32):
        super().__init__()
        s.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        s.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        s.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        s.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        s.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        s.lrelu = nn.LeakyReLU(0.2, True)

    def forward(s, x):
        x1 = s.lrelu(s.conv1(x))
        x2 = s.lrelu(s.conv2(torch.cat((x, x1), 1)))
        x3 = s.lrelu(s.conv3(torch.cat((x, x1, x2), 1)))
        x4 = s.lrelu(s.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = s.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(s, nf=64, gc=32):
        super().__init__()
        s.rdb1, s.rdb2, s.rdb3 = RDB(nf, gc), RDB(nf, gc), RDB(nf, gc)

    def forward(s, x):
        return s.rdb3(s.rdb2(s.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(s, nf=64, nb=23, gc=32):
        super().__init__()
        s.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        s.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        s.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        s.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        s.lrelu = nn.LeakyReLU(0.2, True)

    def forward(s, x):
        feat = s.conv_first(x)
        feat = s.conv_body(s.body(feat)) + feat
        feat = s.lrelu(s.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        feat = s.lrelu(s.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        return s.conv_last(s.lrelu(s.conv_hr(feat)))


def run(model, img, tile=256, pad=16):
    """Tiled inference to bound memory. img: 1x3xHxW float tensor in [0,1]."""
    _, _, h, w = img.shape
    out = torch.zeros(1, 3, h * 4, w * 4)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, y1 = max(0, y - pad), min(h, y + tile + pad)
            x0, x1 = max(0, x - pad), min(w, x + tile + pad)
            with torch.no_grad():
                o = model(img[:, :, y0:y1, x0:x1])
            oy, ox = (y - y0) * 4, (x - x0) * 4
            th, tw = min(tile, h - y) * 4, min(tile, w - x) * 4
            out[:, :, y * 4:y * 4 + th, x * 4:x * 4 + tw] = o[:, :, oy:oy + th, ox:ox + tw]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--weights', default='RealESRGAN_x4plus.pth')
    ap.add_argument('--min-width', type=int, default=2000)
    ap.add_argument('--max-width', type=int, default=4000)
    ap.add_argument('--dpi', type=int, default=300)
    a = ap.parse_args()
    t0 = time.time()
    model = RRDBNet()
    sd = torch.load(a.weights, map_location='cpu')
    sd = sd.get('params_ema', sd.get('params', sd))
    model.load_state_dict(sd, strict=True)
    model.eval()
    im = ImageOps.exif_transpose(Image.open(a.inp)).convert('RGB')
    w0, h0 = im.size
    print(f'input {w0}x{h0}')
    x = torch.from_numpy(np.asarray(im).astype(np.float32) / 255.).permute(2, 0, 1).unsqueeze(0)
    # one x4 pass normally; a second pass only if x4 still falls far short (< 80%) of min_width
    passes = 0 if w0 >= a.min_width else (1 if w0 * 4 >= a.min_width * 0.8 else 2)
    for p in range(passes):
        x = run(model, x).clamp_(0, 1)
        print(f'pass {p + 1}: {x.shape[3]}x{x.shape[2]}  ({time.time() - t0:.0f}s)')
    arr = (x[0].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)
    res = Image.fromarray(arr)
    w, h = res.size
    target = None
    if w < a.min_width:
        target = a.min_width          # small shortfall: gentle resample up to the minimum
    elif w > a.max_width:
        target = a.max_width          # keep files manageable
    if target:
        res = res.resize((target, round(h * target / w)), Image.LANCZOS)
        print(f'resample {w}x{h} -> {res.size[0]}x{res.size[1]}')
    res.save(a.out, dpi=(a.dpi, a.dpi), quality=95, subsampling=0)
    o = Image.open(a.out)
    print(f'output {o.size[0]}x{o.size[1]} dpi={o.info.get("dpi")}  total {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
