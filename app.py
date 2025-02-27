from flask import Flask, render_template, request, send_file
import os
import requests
from io import BytesIO
from rembg import remove
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
TEMPLATE_PATH = 'static/template.jpg'  # Your design template
FINAL_IMAGE_PATH = 'static/final_image.jpg'

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def download_image(url):
    """Download image from a given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(BytesIO(response.content)).convert("RGBA")
    return None

def get_bounding_box(image):
    """Detects the product's bounding box after background removal."""
    bbox = image.getbbox()  # Detect non-transparent area
    if bbox:
        return image.crop(bbox)  # Crop tightly around the product
    return image

def process_image(image):
    """Removes background, detects the product, and resizes it while maintaining aspect ratio."""
    output_image = remove(image).convert("RGBA")  # Remove background

    # **Step 1: Detect the bounding box**
    cropped_image = get_bounding_box(output_image)

    # **Step 2: Maintain the aspect ratio while fitting into a slightly bigger frame**
    max_width = 500  # Increased from 400
    max_height = 600  # Increased from 500

    # Get original aspect ratio
    original_width, original_height = cropped_image.size
    aspect_ratio = original_width / original_height

    # Determine new size while maintaining aspect ratio
    if aspect_ratio > (max_width / max_height):  
        new_width = max_width
        new_height = int(max_width / aspect_ratio)
    else:
        new_height = max_height
        new_width = int(max_height * aspect_ratio)

    # Resize the product proportionally
    final_product = cropped_image.resize((new_width, new_height), Image.LANCZOS)

    return final_product

def calculate_position(template, product_image):
    """Calculates the correct position to place the product at a fixed location."""
    template_width, template_height = template.size
    product_width, product_height = product_image.size

    # **Positioning Logic**
    table_center_x = template_width // 2
    table_center_y = 1670  # Position near the base

    # Center the product on the template
    product_x = table_center_x - (product_width // 2)
    product_y = table_center_y - product_height  # Ensures product sits correctly

    return product_x, product_y

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        product_name = request.form["product_name"]
        price = request.form["price"]
        image_url = request.form.get("product_image_url", "")
        uploaded_file = request.files.get("product_image")

        # **Step 1: Load the image**
        if image_url:
            product_image = download_image(image_url)
            if product_image is None:
                return "Invalid Image URL", 400
        elif uploaded_file and uploaded_file.filename != "":
            image_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(image_path)
            product_image = Image.open(image_path).convert("RGBA")
        else:
            return "No image provided!", 400

        # **Step 2: Process the image (Remove background, detect object, resize while keeping proportions)**
        processed_image = process_image(product_image)

        # **Step 3: Open the template and position the product**
        template = Image.open(TEMPLATE_PATH).convert("RGBA")
        product_x, product_y = calculate_position(template, processed_image)

        # **Step 4: Paste product onto the template**
        template.paste(processed_image, (product_x, product_y), processed_image)

        # **Step 5: Add price**
        draw = ImageDraw.Draw(template)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_size = 38
        font = ImageFont.truetype(font_path, font_size)

        price_x = (769 + 932) // 2
        price_y = (1193 + 1323) // 2
        draw.text((price_x, price_y), f"AED {price}", fill="white", font=font, anchor="mm")

        # **Step 6: Save and return the final image**
        template.convert("RGB").save(FINAL_IMAGE_PATH, "JPEG")
        return send_file(FINAL_IMAGE_PATH, mimetype="image/jpeg", as_attachment=True, download_name="whatsapp_offer.jpg")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
