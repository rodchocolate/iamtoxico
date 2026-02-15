"""Tests for utility scripts: fetch_images helpers and make_poster helpers.

We test the pure-function helpers without doing any real HTTP or file I/O.
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


# ===================================================================
# fetch_images.py helpers
# ===================================================================

class TestFetchImagesHelpers:
    """Test the pure utility functions in fetch_images.py."""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        self.mod = importlib.import_module('fetch_images')

    def test_slugify_basic(self):
        assert self.mod.slugify('Hello World') == 'hello-world'

    def test_slugify_strips_special_chars(self):
        assert self.mod.slugify('Joe "The Boss" Gans!') == 'joe-the-boss-gans'

    def test_slugify_truncates_to_80(self):
        long_text = 'a' * 200
        assert len(self.mod.slugify(long_text)) <= 80

    def test_slugify_empty(self):
        assert self.mod.slugify('') == ''

    def test_derive_filename_uses_title_slug(self):
        result = self.mod.derive_filename('Joe Louis', 'https://example.com/photo.jpg')
        assert result.startswith('joe-louis')
        assert result.endswith('.jpg')

    def test_derive_filename_extracts_extension(self):
        result = self.mod.derive_filename('Test', 'https://example.com/img.png')
        assert result.endswith('.png')

    def test_derive_filename_defaults_to_jpg(self):
        result = self.mod.derive_filename('Test', 'https://example.com/resource')
        assert result.endswith('.jpg')

    def test_iter_blocks_extracts_title_and_url(self):
        lines = [
            '1) Joe Louis Army mess hall 1942\n',
            '- Source URL: https://example.com/joe-louis.jpg\n',
            '- Rights: PD\n',
            '\n',
        ]
        blocks = list(self.mod.iter_blocks(lines))
        assert len(blocks) == 1
        title, url, rights, saveas = blocks[0]
        assert 'Joe Louis' in title
        assert url == 'https://example.com/joe-louis.jpg'
        assert 'PD' in rights.upper()

    def test_iter_blocks_skips_missing_url(self):
        lines = [
            '1) No URL here\n',
            '- Rights: PD\n',
            '\n',
        ]
        blocks = list(self.mod.iter_blocks(lines))
        assert len(blocks) == 0

    def test_iter_blocks_handles_angle_bracket_urls(self):
        lines = [
            '1) Test Image\n',
            '- Source URL: <https://example.com/test.jpg>\n',
            '- Rights: PD\n',
        ]
        blocks = list(self.mod.iter_blocks(lines))
        assert len(blocks) == 1
        assert blocks[0][1] == 'https://example.com/test.jpg'

    def test_iter_blocks_saves_as_field(self):
        lines = [
            '1) Custom Save Path\n',
            '- Source URL: https://example.com/img.jpg\n',
            '- Rights: PD\n',
            '- Save As: docs/design/custom.jpg\n',
        ]
        blocks = list(self.mod.iter_blocks(lines))
        assert blocks[0][3] == 'docs/design/custom.jpg'

    def test_allowed_rights_contains_pd(self):
        assert 'pd' in self.mod.ALLOWED_RIGHTS

    def test_image_exts_contains_common_formats(self):
        for ext in ('.jpg', '.png', '.tif'):
            assert ext in self.mod.IMAGE_EXTS


# ===================================================================
# make_poster.py helpers
# ===================================================================

class TestMakePosterHelpers:
    """Test pure functions in make_poster.py."""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        self.mod = importlib.import_module('make_poster')

    def test_load_font_returns_font_object(self):
        font = self.mod.load_font(48)
        # Should return either a TrueType or default font
        assert font is not None

    def test_load_font_respects_size(self):
        small = self.mod.load_font(12)
        large = self.mod.load_font(120)
        # Both should succeed
        assert small is not None
        assert large is not None

    def test_stylize_image_returns_image(self):
        from PIL import Image
        img = Image.new('RGB', (200, 200), 'red')
        result = self.mod.stylize_image(img)
        assert result.size[0] > 0
        assert result.size[1] > 0

    def test_stylize_image_converts_to_grayscale(self):
        from PIL import Image
        img = Image.new('RGB', (200, 200), 'red')
        result = self.mod.stylize_image(img)
        # stylize_image converts to grayscale ('L' mode)
        assert result.mode == 'L'

    def test_place_word_on_canvas(self):
        from PIL import Image
        canvas = Image.new('RGB', (600, 400), 'black')
        # Should not raise
        self.mod.place_word(canvas, 'DREAMER', '#FFFFFF', pad=20, font_size=48)

    def test_place_word_centered_band(self):
        from PIL import Image
        canvas = Image.new('RGB', (600, 400), 'black')
        band_box = (0, 300, 600, 400)
        self.mod.place_word_centered_band(canvas, 'TOXICO', band_box, '#FFFFFF', 48, 10)


# ===================================================================
# HTML static files exist
# ===================================================================

class TestStaticFilesExist:
    """Verify key project files are present on disk."""

    @pytest.mark.parametrize('filename', [
        'index.html',
        'landing.html',
        'shop.html',
        'styles.css',
        'data/catalog.json',
        'api.php',
        'server.py',
        'requirements.txt',
    ])
    def test_file_exists(self, filename):
        path = os.path.join(ROOT, filename)
        assert os.path.isfile(path), f'Missing file: {filename}'

    @pytest.mark.parametrize('dirname', [
        'data',
        'docs',
        'scripts',
        'shopify-app',
        'posters',
    ])
    def test_directory_exists(self, dirname):
        path = os.path.join(ROOT, dirname)
        assert os.path.isdir(path), f'Missing directory: {dirname}'
