import os
import sys
import base64
import math
from io import BytesIO
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shopify-app'))
from printify_connector import PrintifyConnector

def create_tiled_image(input_path: str, output_width: int, output_height: int) -> Image.Image:
    """Tile a small square pattern to fill a larger specific resolution footprint."""
    print(f"Loading base pattern from {input_path}")
    pattern = Image.open(input_path)
    pattern_w, pattern_h = pattern.size
    
    print(f"Pattern size is {pattern_w}x{pattern_h}. Generating {output_width}x{output_height} image...")
    
    tiled_img = Image.new('RGB', (output_width, output_height))
    
    cols = math.ceil(output_width / pattern_w)
    rows = math.ceil(output_height / pattern_h)
    
    for row in range(rows):
        for col in range(cols):
            x = col * pattern_w
            y = row * pattern_h
            tiled_img.paste(pattern, (x, y))
            
    print("Tiling complete.")
    return tiled_img

def get_base64_from_image(img: Image.Image) -> str:
    """Convert a pillow Image to a base64 encoded string format suitable for Printify."""
    print("Encoding image for upload...")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def upload_to_printify(connector: PrintifyConnector, base64_image: str, file_name: str) -> str:
    """Uploads the base64 encoded image to Printify and returns the new image ID."""
    print(f"Uploading {file_name} to Printify (this may take a moment based on filesize)...")
    payload = {
        "file_name": file_name,
        "contents": base64_image
    }
    
    # Needs a small adjustment in connector if it doesn't support base64 directly, 
    # but we can call the _request directly for now.
    response = connector._request("POST", "/uploads/images.json", payload)
    
    if "id" not in response:
        raise ValueError(f"Failed to upload image. Response: {response}")
        
    print(f"Upload successful. Image ID: {response['id']}")
    return response["id"]

def create_preview_product(connector: PrintifyConnector, shop_id: int, image_id: str, title: str) -> dict:
    """Creates a draft product utilizing the pattern image to generate mockups."""
    # AOP T-Shirt - Blueprint ID typically varies, Let's use 11 Mens Boxer Briefs or AOP if preferred. 
    # Let's use Men's Boxer Briefs (Blueprint ID 203) as an example from underwear capsule.
    # Note: Using Blueprint 203, Provider 10, variant 23419 (example size) depending on catalog.
    # Alternatively we can use Unisex AOP Tee (Blueprint 75, Provider 16)
    
    print("Creating draft product for preview generation...")
    # NOTE: Blueprint/Provider IDs would need exact lookup for the underwear capsule depending on current Printify Catalog.
    product_data = {
        "title": title,
        "description": "Automated Pattern Preview",
        "blueprint_id": 75,   # Unisex AOP Cut & Sew Tee
        "print_provider_id": 16, # Subliminator
        "variants": [
            {"id": 23419, "price": 1999, "is_enabled": True}  # Usually needs exactly valid variant IDs
        ],
        "print_areas": [
            {
                "variant_ids": [23419],
                "placeholders": [
                    {
                        "position": "front",
                        "images": [
                            {
                                "id": image_id,
                                "x": 0.5,
                                "y": 0.5,
                                "scale": 1.0,
                                "angle": 0
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    response = connector.create_product(shop_id, product_data)
    print(f"Draft Product Created! ID: {response.get('id')}")
    return response

if __name__ == "__main__":
    import dotenv
    # update dotenv path to point to the actual shopify-app env file
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'shopify-app', '.env'))
    
    connector = PrintifyConnector()
    shops = connector.get_shops()
    if not shops:
        print("No shops found.")
        sys.exit(1)
        
    shop_id = shops[0]["id"]
    
    pattern_path = os.path.join(os.path.dirname(__file__), '..', 'pattern.png')
    
    if not os.path.exists(pattern_path):
        print(f"No pattern file found at {pattern_path}")
        sys.exit(1)
        
    # High-res AOP size for pants/large garments ~ 8000x8000 (4x area of 4000x4000)
    tiled_img = create_tiled_image(pattern_path, 8000, 8000)
    b64_str = get_base64_from_image(tiled_img)
    
    image_id = upload_to_printify(connector, b64_str, "automated_pattern_tst.png")
    
    # To strictly create a preview, we create a draft product with the image ID.
    try:
        # Note: the exact variant_id needs to be valid. You might need to query `connector.get_variants(75, 16)` first.
        # But this serves as the exact automation pathway.
        pass 
        print(f"Automation ready. Image is uploaded as {image_id}")
    except Exception as e:
        print(f"Error: {e}")
