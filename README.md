# picture — 画像の高品質化（AI 超解像）ツール

Google ドライブのフォルダに入れた画像を一括で拡大し、
「横幅 2,000px 以上・300dpi」の JPEG に仕上げるための道具一式です。
Claude Code のセッションから使う前提で書かれています。

## 構成

| ファイル | 役割 |
|---|---|
| `tools/upscale.py` | 1 枚を Real-ESRGAN x4plus（CPU）で 4 倍に拡大し、dpi を書き込む本体。外部ライブラリは torch と Pillow だけ |
| `tools/batch.sh` | `in/*.jpg` を順番に処理して `out/<名前>_up.jpg` に出力。進み具合は `batch.log` |
| `tools/make_gallery.py` | 出力画像を埋め込んだ納品ページ（HTML）を作る。Artifact として発行すると 1 枚ずつ保存できる |
| `tools/requirements.txt` | 必要な Python パッケージ |
| `docs/gazo_UP_20260907.md` | 2026-09-07 の処理記録（12 枚の対応表と仕上がりサイズ） |

学習済みモデル（約 67MB）は同梱していません。初回に次から取得して `tools/` に置きます。
`https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth`

## 使い方（Claude Code 内）

```bash
pip install pillow numpy torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
cd tools && curl -L -O https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
# in/ に元画像を置いてから
bash batch.sh
python3 make_gallery.py gallery.html "ページ名" out/*.jpg   # 合計 11MB を超えるなら分割する
```

1 枚あたりの所要時間の目安（4 コア CPU）: 640×480 で約 1 分、1500×1000 で約 6 分。

## 仕上がりの規則

- 横幅 2,000px 未満の画像だけ拡大する（4 倍）。4 倍しても 2,000px に届かない場合は 2,000px まで補間で伸ばす。
- 横幅が 4,000px を超えたら 4,000px に縮小する（ファイル容量の抑制）。
- EXIF の回転情報は拡大前に反映する。出力は JPEG 品質 95・色情報の間引きなし・300dpi。
- 納品ファイル名は半角英数のみ。日本語名は対応表に記録する。

## 元画像の受け渡し

- ドライブのフォルダを「リンクを知っている全員（閲覧者）」にすると、`https://drive.google.com/uc?export=download&id=<ID>` で直接取得できる。作業後は「制限付き」に戻す。
- ドライブへの書き戻しは実用的でないため、結果は納品ページ（Artifact）で渡す。
