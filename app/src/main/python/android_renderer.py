"""Chaquopy entry point; desktop algorithms stay unchanged."""

import logging
import math
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PIL import Image, ImageFont
import img2ascii


def _text(value):
    if value is None:
        return '未提供'
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    return str(value).strip(' \t\r\n\x00')[:256] or '未提供'


def _measurement(value, kind):
    if value is None:
        return '未提供'
    try:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            return '数据无效'
        if kind == 'exposure':
            return f'1/{1 / number:.0f} 秒' if number < 1 else f'{number:g} 秒'
        if kind == 'aperture':
            return f'f/{number:g}'
        return f'{number:g} mm'
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return '数据无效'


def _gps_coordinate(values, reference, positive, negative, maximum):
    if not isinstance(values, (tuple, list)) or len(values) != 3:
        raise ValueError('Invalid GPS coordinate')
    degrees, minutes, seconds = map(float, values)
    if not all(math.isfinite(v) for v in (degrees, minutes, seconds)):
        raise ValueError('Invalid GPS coordinate')
    if degrees < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError('Invalid GPS coordinate')
    result = degrees + minutes / 60 + seconds / 3600
    ref = _text(reference).upper()
    if result > maximum or ref not in (positive, negative):
        raise ValueError('Invalid GPS coordinate')
    return -result if ref == negative else result


def image_info(source, display_name=''):
    """Read common metadata only; never load full pixels or modify the source."""
    with Image.open(source) as image:
        width, height = image.size
        exif, details, gps = {}, {}, {}
        damaged = False
        try:
            exif = image.getexif()
            details = exif.get_ifd(34665)  # Exif IFD: camera exposure and lens tags.
            gps = exif.get_ifd(34853)
        except (OSError, ValueError, TypeError, SyntaxError, KeyError, ZeroDivisionError):
            damaged = True
        orientation = exif.get(274, 1)
        displayed = (height, width) if orientation in (5, 6, 7, 8) else (width, height)
        orientation_label = {
            1: '正常', 2: '水平镜像', 3: '旋转 180°', 4: '垂直镜像',
            5: '转置', 6: '顺时针 90°', 7: '横向转置', 8: '逆时针 90°',
        }.get(orientation, '未知')
        latitude = longitude = '未提供'
        if gps:
            try:
                latitude = f'{_gps_coordinate(gps.get(2), gps.get(1), "N", "S", 90):.6f}°'
                longitude = f'{_gps_coordinate(gps.get(4), gps.get(3), "E", "W", 180):.6f}°'
            except (TypeError, ValueError, ZeroDivisionError, OverflowError):
                latitude = longitude = '数据无效或不完整'
        byte_count = Path(source).stat().st_size
        size_label = (f'{byte_count / 1024 ** 2:.2f} MiB' if byte_count >= 1024 ** 2
                      else f'{byte_count / 1024:.2f} KiB')
        taken = _text(details.get(36867, exif.get(306)))
        if details.get(36881):
            taken += ' ' + _text(details[36881])
        rows = [
            ('文件名', _text(display_name or Path(source).name)),
            ('格式', image.format or '未知'),
            ('文件大小', f'{size_label}（{byte_count} 字节）'),
            ('存储尺寸', f'{width}×{height}'),
            ('显示尺寸', f'{displayed[0]}×{displayed[1]}'),
            ('颜色模式', image.mode), ('方向', orientation_label),
            ('设备厂商', _text(exif.get(271))), ('设备型号', _text(exif.get(272))),
            ('镜头', _text(details.get(42036))), ('拍摄时间', taken),
            ('ISO', _text(details.get(34855))),
            ('光圈', _measurement(details.get(33437), 'aperture')),
            ('快门', _measurement(details.get(33434), 'exposure')),
            ('焦距', _measurement(details.get(37386), 'focal')),
            ('GPS 纬度', latitude), ('GPS 经度', longitude),
        ]
        text = '\n'.join(f'{name}：{value}' for name, value in rows)
        if damaged:
            text += '\n部分 EXIF 数据无法解析，以上为可读取的信息。'
        return text


def source_size(source):
    """Read displayed dimensions without decoding all pixels (honor EXIF rotation)."""
    with Image.open(source) as image:
        width, height = image.size
        if width * height > 40_000_000:
            raise ValueError('原图超过 4000 万像素，请先缩小后再导入。')
        if image.getexif().get(274) in (5, 6, 7, 8):
            width, height = height, width
        return width, height


def render(source, destination, font_path, width, height, font_size,
           mode, fit, background, dither, log_directory):
    logger = logging.getLogger('android-renderer')
    if not logger.handlers:
        Path(log_directory).mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            Path(log_directory) / 'renderer.log', maxBytes=1024 * 1024,
            backupCount=2, encoding='utf-8')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    try:
        if width < 1 or height < 1 or width * height > 16_000_000:
            raise ValueError('输出尺寸须为正数，且不超过 1600 万像素。')
        if not 6 <= font_size <= 64:
            raise ValueError('字体大小必须在 6–64 之间。')
        source_size(source)
        logger.info('render mode=%s fit=%s size=%sx%s font=%s',
                    mode, fit, width, height, font_size)
        bg = img2ascii.resolve_background(source, background)
        selected = img2ascii.recommend_mode(source, bg) if mode == 'auto' else mode
        font = ImageFont.truetype(font_path, font_size)
        image = img2ascii.ascii_image(
            source, font, (width, height), bg, selected,
            bool(dither) and selected not in ('braille', 'halfblock'), fit)
        try:
            image.save(destination, format='PNG')
        finally:
            image.close()
        return selected
    except Exception:
        logger.exception('render failed')
        raise
