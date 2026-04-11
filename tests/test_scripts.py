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
# resolve_printify_sources.py helpers
# ===================================================================

class TestResolvePrintifySourcesHelpers:
    """Test pure helper functions in resolve_printify_sources.py."""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        self.mod = importlib.import_module('resolve_printify_sources')

    def test_normalize_asset_key_strips_staging_hash(self):
        value = 'joe-louis_army-mess-hall_1942__8c4d85f3.jpg'
        assert self.mod.normalize_asset_key(value) == 'joe-louis-army-mess-hall-1942'

    def test_rebase_library_path_maps_old_repo_path(self, tmp_path):
        raw = '/Users/jasonjenkins/Desktop/alpha/toxico/docs/design/reference-images/jazz/miles-davis_gottlieb.jpg'
        expected = tmp_path / 'docs' / 'design' / 'reference-images' / 'jazz' / 'miles-davis_gottlieb.jpg'
        assert self.mod.rebase_library_path(raw, tmp_path) == str(expected)

    def test_parse_staging_log_maps_staging_to_source(self, tmp_path):
        log_path = tmp_path / 'fetch_images.log'
        log_path.write_text(
            'STAGING: /Users/jasonjenkins/Desktop/alpha/toxico/docs/design/reference-images/jazz/miles-davis_gottlieb.jpg -> '
            '/Users/jasonjenkins/Desktop/alpha/toxico/docs/design/reference-images/_staging/miles-davis_gottlieb__2d8d1de1.jpg\n',
            encoding='utf-8',
        )

        mapping = self.mod.parse_staging_log(log_path, tmp_path)
        assert 'miles-davis-gottlieb' in mapping
        assert str(tmp_path / 'docs' / 'design' / 'reference-images' / 'jazz' / 'miles-davis_gottlieb.jpg') in mapping['miles-davis-gottlieb']

    def test_resolve_uploaded_image_candidates_uses_file_name(self):
        index = {
            'miles-davis-gottlieb': {
                '/repo/docs/design/reference-images/jazz/miles-davis_gottlieb.jpg'
            }
        }
        upload_record = {
            'file_name': 'miles-davis_gottlieb.jpg',
            'preview_url': 'https://example.com/uploads/miles-davis_gottlieb.jpg',
        }

        candidates = self.mod.resolve_uploaded_image_candidates(upload_record, index)
        assert candidates == ['/repo/docs/design/reference-images/jazz/miles-davis_gottlieb.jpg']


class TestExportRenameBriefHelpers:
    """Test pure helper functions in export_rename_brief.py."""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        self.mod = importlib.import_module('export_rename_brief')

    def test_extract_mockup_urls_limits_and_dedupes(self):
        product = {
            'images': [
                {'src': 'https://example.com/a.jpg'},
                {'src': 'https://example.com/a.jpg'},
                {'src': 'https://example.com/b.jpg'},
                {'src': 'https://example.com/c.jpg'},
                {'src': 'https://example.com/d.jpg'},
                {'src': 'https://example.com/e.jpg'},
            ]
        }
        assert self.mod.extract_mockup_urls(product) == [
            'https://example.com/a.jpg',
            'https://example.com/b.jpg',
            'https://example.com/c.jpg',
            'https://example.com/d.jpg',
        ]

    def test_build_rename_record_collects_source_candidates(self):
        product_detail = {
            'id': 'prod-1',
            'title': 'Copy Of Something',
            'external': {'id': '123', 'handle': 'copy-of-something'},
            'blueprint_id': 77,
            'print_provider_id': 99,
            'images': [{'src': 'https://example.com/mockup.jpg'}],
            'print_areas': [
                {
                    'variant_ids': [1],
                    'placeholders': [
                        {
                            'position': 'front',
                            'images': [{'id': 'upload-1'}],
                        }
                    ],
                }
            ],
        }
        uploaded_images = {
            'upload-1': {
                'file_name': 'miles-davis_gottlieb.jpg',
                'preview_url': 'https://example.com/uploads/miles-davis_gottlieb.jpg',
            }
        }
        asset_index = {
            'miles-davis-gottlieb': {
                '/repo/docs/design/reference-images/jazz/miles-davis_gottlieb.jpg'
            }
        }

        record = self.mod.build_rename_record(product_detail, uploaded_images, asset_index)
        assert record['product_id'] == 'prod-1'
        assert record['mockup_urls'] == ['https://example.com/mockup.jpg']
        assert record['candidate_source_paths'] == [
            '/repo/docs/design/reference-images/jazz/miles-davis_gottlieb.jpg'
        ]
        assert record['artwork'][0]['file_name'] == 'miles-davis_gottlieb.jpg'


class TestPublishApresTopsHelpers:
    """Test pure helper functions in publish_apres_tops.py."""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        self.mod = importlib.import_module('publish_apres_tops')

    def test_family_from_pant_title_strips_suffix(self):
        assert self.mod.family_from_pant_title('Cyan Glow Harem Pant') == 'Cyan Glow'

    def test_apres_title_from_family(self):
        assert self.mod.apres_title_from_family('Cyan Glow') == 'Cyan Glow Apres'

    def test_extract_upload_id_picks_most_common(self):
        product = {
            'print_areas': [
                {'placeholders': [{'images': [{'id': 'img-1'}, {'id': 'img-1'}]}]},
                {'placeholders': [{'images': [{'id': 'img-2'}, {'id': 'img-1'}]}]},
            ]
        }
        assert self.mod.extract_upload_id(product) == 'img-1'

    def test_build_image_payload_applies_scale_and_brick(self):
        payload = self.mod.build_image_payload(
            image={
                'x': 0.5,
                'y': 0.5,
                'scale': 0.2,
                'angle': 0,
                'pattern': {'spacing_x': 1, 'spacing_y': 1, 'angle': 0, 'offset': 0},
            },
            upload_id='img-1',
            scale_multiplier=1.25,
            brick_offset=0.5,
        )
        assert payload['id'] == 'img-1'
        assert payload['scale'] == pytest.approx(0.25)
        assert payload['pattern']['offset'] == pytest.approx(0.5)

    def test_build_catalog_entry_uses_external_handle(self):
        product = {
            'id': 'prod-1',
            'title': 'Cyan Glow Apres',
            'external': {'id': '123', 'handle': 'https://shop.example/products/cyan-glow-apres'},
            'images': [
                {'src': 'https://example.com/front.jpg', 'is_default': True}
            ],
        }
        entry = self.mod.build_catalog_entry(product, 120)
        assert entry['id'] == 'printify-prod-1'
        assert entry['url'] == 'https://shop.example/products/cyan-glow-apres'
        assert entry['price'] == 120

    def test_build_set_price_rule_sets_discount_gap(self):
        rule = self.mod.build_set_price_rule(
            title='Apres Set 200',
            pant_product_ids=[1, 2],
            top_product_ids=[3, 4],
            set_price_dollars=200,
            item_price_dollars=120,
        )
        assert rule['value'] == '-40.00'
        assert rule['prerequisite_product_ids'] == [1, 2]
        assert rule['entitled_product_ids'] == [3, 4]


class TestRefreshPreviewHelpers:
    """Test pure helper functions in refresh_preview.py."""

    @pytest.fixture(autouse=True)
    def import_module(self):
        import importlib
        self.mod = importlib.import_module('refresh_preview')

    def test_extract_product_id_from_mockup_url(self):
        url = 'https://images.printify.com/mockup/69dab8da70e65284fd01727d/74644/19527/toxico-apres.jpg?camera_label=front'
        assert self.mod.extract_product_id(url) == '69dab8da70e65284fd01727d'

    def test_parse_preview_entries_splits_live_and_staging(self):
        html = '''<script>
const P = [
  /* -- LIVE (alphabetical) -- */
  {t:"Toxico Apres", y:"apres", s:"live", f:"https://images.printify.com/mockup/live-1/front.jpg?camera_label=front", b:"https://images.printify.com/mockup/live-1/back.jpg?camera_label=back"},

  /* -- STAGING (alphabetical) -- */
  {t:"Cyan Glow", y:"harem", s:"staging", f:"https://images-api.printify.com/mockup/stage-1/front.jpg?camera_label=front", b:"https://images-api.printify.com/mockup/stage-1/back.jpg?camera_label=back"},
];
</script>'''
        live, staging = self.mod.parse_preview_entries(html)
        assert [entry.title for entry in live] == ['Toxico Apres']
        assert [entry.title for entry in staging] == ['Cyan Glow']

    def test_sync_entries_refreshes_urls_and_prunes_missing(self):
        entries = [
            self.mod.PreviewEntry(
                title='Toxico Apres',
                category='apres',
                shop='live',
                front='https://images.printify.com/mockup/live-1/old-front.jpg?camera_label=front',
                back='https://images.printify.com/mockup/live-1/old-back.jpg?camera_label=back',
            ),
            self.mod.PreviewEntry(
                title='Deleted Item',
                category='staging',
                shop='staging',
                front='https://images.printify.com/mockup/missing-1/old-front.jpg?camera_label=front',
                back='https://images.printify.com/mockup/missing-1/old-back.jpg?camera_label=back',
            ),
        ]
        products = {
            'live-1': {
                'images': [
                    {'src': 'https://images.printify.com/mockup/live-1/new-front.jpg?camera_label=front'},
                    {'src': 'https://images.printify.com/mockup/live-1/new-back.jpg?camera_label=back'},
                ]
            }
        }
        synced, removed = self.mod.sync_entries(entries, products)
        assert len(synced) == 1
        assert synced[0].front.endswith('new-front.jpg?camera_label=front')
        assert synced[0].back.endswith('new-back.jpg?camera_label=back')
        assert [entry.title for entry in removed] == ['Deleted Item']

    def test_replace_preview_entries_renders_sections(self):
        html = '''<script>
const P = [
  /* old */
  {t:"Old", y:"old", s:"live", f:"https://images.printify.com/mockup/old/front.jpg?camera_label=front", b:"https://images.printify.com/mockup/old/back.jpg?camera_label=back"},
];
</script>'''
        updated = self.mod.replace_preview_entries(
            html,
            [
                self.mod.PreviewEntry(
                    title='Toxico Apres',
                    category='apres',
                    shop='live',
                    front='https://images.printify.com/mockup/live-1/front.jpg?camera_label=front',
                    back='https://images.printify.com/mockup/live-1/back.jpg?camera_label=back',
                )
            ],
            [],
        )
        assert 'Toxico Apres' in updated
        assert 'STAGING' in updated


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
        'scripts/refresh_preview.py',
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
