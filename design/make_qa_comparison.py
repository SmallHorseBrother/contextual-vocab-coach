from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
TARGET = (1440, 1024)


def cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


reference = cover(Image.open(ROOT / "reference-codex-sidecar.png").convert("RGB"), TARGET)
raw = Image.open(ROOT / "implementation-codex-sidecar.jpg").convert("RGB")
# The in-app browser capture includes blank Codex panel space to the right and
# below the 1440x1024 CSS viewport. On this host the rendered browser surface
# occupies 1070x761 pixels inside the returned desktop image.
implementation = raw.crop((0, 0, min(1070, raw.width), min(761, raw.height)))
implementation = cover(implementation, TARGET)
implementation.save(ROOT / "workbench-preview.png", optimize=True)

header_height = 58
canvas = Image.new("RGB", (TARGET[0] * 2, TARGET[1] + header_height), "#f4f1ea")
canvas.paste(reference, (0, header_height))
canvas.paste(implementation, (TARGET[0], header_height))
draw = ImageDraw.Draw(canvas)
font_path = Path("C:/Windows/Fonts/arial.ttf")
font = ImageFont.truetype(str(font_path), 25) if font_path.exists() else ImageFont.load_default()
draw.text((24, 15), "SOURCE CONCEPT · 1440 × 1024", fill="#173044", font=font)
draw.text((TARGET[0] + 24, 15), "IMPLEMENTATION · 1440 × 1024", fill="#173044", font=font)
canvas.save(ROOT / "qa-side-by-side.png", optimize=True)
