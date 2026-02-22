import fitz  # PyMuPDF
import os
import cv2
import numpy as np

class PDFProcessor:
    def __init__(self, target_image_path=None, 
                 watermark_type="Text",
                 custom_watermark_text=None, 
                 custom_watermark_image_path=None,
                 watermark_opacity=0.3,
                 watermark_position="Center",
                 watermark_size=50,
                 watermark_angle=30,
                 custom_link_url=None, 
                 custom_link_text=None, 
                 custom_link_position="Bottom-Center",
                 update_callback=None):
        
        self.target_image_path = target_image_path
        self.watermark_type = watermark_type
        self.custom_watermark_text = custom_watermark_text
        self.custom_watermark_image_path = custom_watermark_image_path
        self.watermark_opacity = float(watermark_opacity)
        self.watermark_position = watermark_position
        self.watermark_size = float(watermark_size)
        self.watermark_angle = float(watermark_angle)
        
        # Format URL properly
        self.custom_link_url = custom_link_url
        if self.custom_link_url and not (self.custom_link_url.startswith("http://") or self.custom_link_url.startswith("https://")):
            self.custom_link_url = "https://" + self.custom_link_url
            
        self.custom_link_text = custom_link_text
        self.custom_link_position = custom_link_position
        self.update_callback = update_callback
        self.cancel_requested = False

        self.target_image_cv = None
        if target_image_path and os.path.exists(target_image_path):
            try:
                # Read as grayscale for template matching
                self.target_image_cv = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)
                if self.target_image_cv is not None:
                    # Resize max width/height to 300 for faster/normalized matching
                    h, w = self.target_image_cv.shape
                    if max(h, w) > 300:
                        scale = 300 / max(h, w)
                        self.target_image_cv = cv2.resize(self.target_image_cv, (int(w * scale), int(h * scale)))
            except Exception as e:
                print(f"Error loading target watermark image: {e}")

    def process_directory(self, input_dir, output_dir):
        total_pdfs = 0
        pdf_files = []

        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    total_pdfs += 1
                    pdf_files.append(os.path.join(root, file))

        if self.update_callback:
            self.update_callback({"type": "init", "total": total_pdfs})

        processed_count = 0
        for pdf_path in pdf_files:
            if self.cancel_requested:
                break

            rel_path = os.path.relpath(pdf_path, input_dir)
            output_pdf_path = os.path.join(output_dir, rel_path)
            
            os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
            success = self.process_pdf(pdf_path, output_pdf_path)
            
            processed_count += 1
            if self.update_callback:
                self.update_callback({"type": "progress", "current": processed_count, "total": total_pdfs, "file": rel_path, "success": success})

        if self.update_callback:
            self.update_callback({"type": "done", "total": processed_count})

    def is_target_image(self, pdf_image_bytes):
        if self.target_image_cv is None:
            return False
        try:
            nparr = np.frombuffer(pdf_image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False
                
            # Normalize size for comparison based on template scaling
            h, w = img.shape
            if max(h, w) > 0:
                scale = 300 / max(h, w)
                img_resized = cv2.resize(img, (int(w * scale), int(h * scale)))
            else:
                img_resized = img

            if img_resized.shape[0] < self.target_image_cv.shape[0] or img_resized.shape[1] < self.target_image_cv.shape[1]:
                return False

            result = cv2.matchTemplate(img_resized, self.target_image_cv, cv2.TM_CCOEFF_NORMED)
            threshold = 0.65  # lower threshold to allow for slight rendering differences
            loc = np.where(result >= threshold)
            
            if len(loc[0]) > 0:
                return True
        except Exception:
            pass
        return False

    def get_position_coords(self, page_width, page_height, item_width, item_height):
        padding = 40
        if self.watermark_position == "Top-Left":
            return padding, padding
        elif self.watermark_position == "Top-Right":
            return page_width - item_width - padding, padding
        elif self.watermark_position == "Bottom-Left":
            return padding, page_height - item_height - padding
        elif self.watermark_position == "Bottom-Right":
            return page_width - item_width - padding, page_height - item_height - padding
        else: # Center
            return (page_width - item_width) / 2, (page_height - item_height) / 2

    def process_pdf(self, input_path, output_path):
        try:
            doc = fitz.open(input_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 1. Remove specific target image
                if self.target_image_path:
                    image_list = page.get_images(full=True)
                    for img_info in image_list:
                        xref = img_info[0]
                        try:
                            # Not all images can be extracted
                            base_image = doc.extract_image(xref)
                            if base_image:
                                image_bytes = base_image["image"]
                                if self.is_target_image(image_bytes):
                                    rects = page.get_image_rects(xref)
                                    for rect in rects:
                                        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                        except:
                            pass

                # 2. Add Custom Watermark
                rect = page.rect
                width = rect.width
                height = rect.height
                
                if self.watermark_type == "Text" and self.custom_watermark_text:
                    text_len = fitz.get_text_length(self.custom_watermark_text, fontname="helv", fontsize=self.watermark_size)
                    x, y = self.get_position_coords(width, height, text_len, self.watermark_size)
                    
                    p1 = fitz.Point(x, y + self.watermark_size) # text is drawn from bottom-left of bounds
                    
                    rad = np.radians(self.watermark_angle)
                    cos_a = np.cos(rad)
                    sin_a = np.sin(rad)
                    # rotation matrix around p1
                    text_matrix = fitz.Matrix(cos_a, sin_a, -sin_a, cos_a, 0, 0)
                    
                    page.insert_text(p1, self.custom_watermark_text, fontsize=self.watermark_size, color=(0.5, 0.5, 0.5), fill_opacity=self.watermark_opacity, fontname="helv", morph=(p1, text_matrix))

                elif self.watermark_type == "Image" and self.custom_watermark_image_path and os.path.exists(self.custom_watermark_image_path):
                    try:
                        # Find dimensions of watermark image
                        from PIL import Image
                        with Image.open(self.custom_watermark_image_path) as img:
                            orig_w, orig_h = img.size
                        
                        # Apply scale (self.watermark_size is treated as a percentage multiplier for images)
                        scale = self.watermark_size / 100.0
                        img_w = orig_w * scale
                        img_h = orig_h * scale
                        
                        x, y = self.get_position_coords(width, height, img_w, img_h)
                        img_rect = fitz.Rect(x, y, x + img_w, y + img_h)
                        
                        # PyMuPDF doesn't natively support overlay opacity for insert_image well via simple parameters,
                        # However, we can use the alpha channel of a PIL image.
                        # We convert the image to have opacity and pass bytes
                        with Image.open(self.custom_watermark_image_path).convert("RGBA") as base_image:
                            alpha = base_image.split()[3]
                            alpha = alpha.point(lambda p: p * self.watermark_opacity)
                            base_image.putalpha(alpha)
                            
                            import io
                            img_byte_arr = io.BytesIO()
                            base_image.save(img_byte_arr, format='PNG')
                            img_bytes = img_byte_arr.getvalue()
                            
                            page.insert_image(img_rect, stream=img_bytes, keep_proportion=True)
                    except Exception as e:
                        print(f"Error inserting image watermark: {e}")

                # 3. Add Custom Footer Link
                if self.custom_link_text and self.custom_link_url:
                    text_len = fitz.get_text_length(self.custom_link_text, fontname="helv", fontsize=12)
                    padding = 20
                    
                    if self.custom_link_position == "Bottom-Left":
                        x = padding
                        y = height - 15
                    elif self.custom_link_position == "Bottom-Right":
                        x = width - text_len - padding
                        y = height - 15
                    elif self.custom_link_position == "Top-Left":
                        x = padding
                        # text is drawn from bottom-left of bounds, 15 from edge
                        y = 15 + 12 
                    elif self.custom_link_position == "Top-Right":
                        x = width - text_len - padding
                        y = 15 + 12
                    elif self.custom_link_position == "Top-Center":
                        x = (width - text_len) / 2
                        y = 15 + 12
                    else: # Bottom-Center
                        x = (width - text_len) / 2
                        y = height - 15
                        
                    page.insert_text(fitz.Point(x, y), self.custom_link_text, fontsize=12, color=(0, 0, 1), fontname="helv")
                    link_dict = {"kind": fitz.LINK_URI, "from": fitz.Rect(x, y - 10, x + text_len, y + 5), "uri": self.custom_link_url}
                    page.insert_link(link_dict)

            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            return True
            
        except Exception as e:
            print(f"Failed to process {input_path}: {e}")
            return False

    def generate_preview(self, input_path=None):
        """Generates a preview PIL Image object of the first page with current watermark settings applied."""
        import copy
        from PIL import Image as PILImage
        
        try:
            if input_path and os.path.exists(input_path):
                doc = fitz.open(input_path)
            else:
                # Create a blank letter size dummy document
                doc = fitz.open()
                page = doc.new_page(width=612, height=792) # Standard Letter Size
                page.insert_text(fitz.Point(200, 400), "DUMMY PREVIEW PAGE", fontsize=20, color=(0.7, 0.7, 0.7))
                
            page = doc[0] # Grab first page
            
            # Apply watermarks exactly like process_pdf (excluding the removal of existing images for preview speed)
            rect = page.rect
            width = rect.width
            height = rect.height
            
            if self.watermark_type == "Text" and self.custom_watermark_text:
                text_len = fitz.get_text_length(self.custom_watermark_text, fontname="helv", fontsize=self.watermark_size)
                x, y = self.get_position_coords(width, height, text_len, self.watermark_size)
                
                p1 = fitz.Point(x, y + self.watermark_size)
                
                rad = np.radians(self.watermark_angle)
                cos_a = np.cos(rad)
                sin_a = np.sin(rad)
                text_matrix = fitz.Matrix(cos_a, sin_a, -sin_a, cos_a, 0, 0)
                
                page.insert_text(p1, self.custom_watermark_text, fontsize=self.watermark_size, color=(0.5, 0.5, 0.5), fill_opacity=self.watermark_opacity, fontname="helv", morph=(p1, text_matrix))

            elif self.watermark_type == "Image" and self.custom_watermark_image_path and os.path.exists(self.custom_watermark_image_path):
                from PIL import Image
                with Image.open(self.custom_watermark_image_path) as img:
                    orig_w, orig_h = img.size
                
                scale = self.watermark_size / 100.0
                img_w = orig_w * scale
                img_h = orig_h * scale
                
                x, y = self.get_position_coords(width, height, img_w, img_h)
                img_rect = fitz.Rect(x, y, x + img_w, y + img_h)
                
                with Image.open(self.custom_watermark_image_path).convert("RGBA") as base_image:
                    alpha = base_image.split()[3]
                    alpha = alpha.point(lambda p: p * self.watermark_opacity)
                    base_image.putalpha(alpha)
                    
                    import io
                    img_byte_arr = io.BytesIO()
                    base_image.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    page.insert_image(img_rect, stream=img_bytes, keep_proportion=True)

            if self.custom_link_text: # No need for exact URL routing, just visual preview
                text_len = fitz.get_text_length(self.custom_link_text, fontname="helv", fontsize=12)
                padding = 20
                if self.custom_link_position == "Bottom-Left":
                    x = padding
                    y = height - 15
                elif self.custom_link_position == "Bottom-Right":
                    x = width - text_len - padding
                    y = height - 15
                elif self.custom_link_position == "Top-Left":
                    x = padding
                    y = 15 + 12 
                elif self.custom_link_position == "Top-Right":
                    x = width - text_len - padding
                    y = 15 + 12
                elif self.custom_link_position == "Top-Center":
                    x = (width - text_len) / 2
                    y = 15 + 12
                else: # Bottom-Center
                    x = (width - text_len) / 2
                    y = height - 15
                    
                page.insert_text(fitz.Point(x, y), self.custom_link_text, fontsize=12, color=(0, 0, 1), fontname="helv")

            # Render to Image
            # dpi 150 is good enough for a sharp desktop preview without taking too much memory
            pix = page.get_pixmap(dpi=150) 
            mode = "RGBA" if pix.alpha else "RGB"
            img = PILImage.frombytes(mode, [pix.width, pix.height], pix.samples)
            
            doc.close()
            return img

        except Exception as e:
            print(f"Error generating preview: {e}")
            return None

    def cancel(self):
        self.cancel_requested = True
