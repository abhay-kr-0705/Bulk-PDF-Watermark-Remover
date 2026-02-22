import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from PIL import Image
from pdf_processor import PDFProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Bulk PDF Watermark Manager")
        self.geometry("1400x850") # Wider geometry for split screen
        
        # Configure layout: 2 columns
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=500) # Settings Pane
        self.grid_columnconfigure(1, weight=1, minsize=500) # Preview Pane

        self.input_dir = ""
        self.output_dir = ""
        self.target_image_path = ""
        self.custom_watermark_image_path = ""
        
        self.processor = None
        self.processing_thread = None
        
        # Preview debounce timer
        self.preview_timer = None

        self.create_widgets()
        # Initialize an empty preview
        self.trigger_preview_update()

    def create_widgets(self):
        # ==========================================
        # LEFT PANE: SETTINGS
        # ==========================================
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        # --- Section 1: Directories & Files ---
        ctk.CTkLabel(self.scroll_frame, text="1. Select Input/Output", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w", columnspan=2)

        input_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=10, pady=5, sticky="w", columnspan=2)
        
        self.input_dir_btn = ctk.CTkButton(input_frame, text="Browse Input Folder", command=self.select_input_dir)
        self.input_dir_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.input_file_btn = ctk.CTkButton(input_frame, text="Browse Input File", command=self.select_input_file)
        self.input_file_btn.grid(row=0, column=1, padx=5)

        self.input_label = ctk.CTkLabel(input_frame, text="No input selected", text_color="gray")
        self.input_label.grid(row=0, column=2, padx=10)

        self.output_btn = ctk.CTkButton(self.scroll_frame, text="Browse Output Folder", command=self.select_output_dir)
        self.output_btn.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.output_label = ctk.CTkLabel(self.scroll_frame, text="No folder selected", text_color="gray")
        self.output_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # --- Section 2: Watermark Removal ---
        ctk.CTkLabel(self.scroll_frame, text="2. Remove Existing Watermark Logo", font=ctk.CTkFont(size=18, weight="bold")).grid(row=3, column=0, padx=10, pady=(20, 5), sticky="w", columnspan=2)

        self.image_btn = ctk.CTkButton(self.scroll_frame, text="Select Target Image to Remove", command=self.select_target_image)
        self.image_btn.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.image_label = ctk.CTkLabel(self.scroll_frame, text="No image selected", text_color="gray")
        self.image_label.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        # --- Section 3: Add Custom Watermark ---
        ctk.CTkLabel(self.scroll_frame, text="3. Add Custom Watermark (Optional)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=5, column=0, padx=10, pady=(20, 5), sticky="w", columnspan=2)

        # Type Dropdown
        ctk.CTkLabel(self.scroll_frame, text="Watermark Type:").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.wm_type_var = ctk.StringVar(value="Text")
        self.wm_type_menu = ctk.CTkOptionMenu(self.scroll_frame, values=["Text", "Image"], variable=self.wm_type_var, command=self.handle_type_change)
        self.wm_type_menu.grid(row=6, column=1, padx=10, pady=5, sticky="w")

        # Text input
        self.lbl_wm_text = ctk.CTkLabel(self.scroll_frame, text="Text Content:")
        self.lbl_wm_text.grid(row=7, column=0, padx=10, pady=5, sticky="e")
        self.wm_text_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., CONFIDENTIAL")
        self.wm_text_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        self.wm_text_entry.bind("<KeyRelease>", self.trigger_preview_update)

        # Image input
        self.btn_wm_image = ctk.CTkButton(self.scroll_frame, text="Select Watermark Image", command=self.select_wm_image)
        self.lbl_wm_image = ctk.CTkLabel(self.scroll_frame, text="No image selected", text_color="gray")

        # Common Parameters:
        # Opacity
        ctk.CTkLabel(self.scroll_frame, text="Opacity (0.1 to 1.0):").grid(row=9, column=0, padx=10, pady=5, sticky="e")
        self.opacity_slider = ctk.CTkSlider(self.scroll_frame, from_=0.1, to=1.0, number_of_steps=9, command=self.trigger_preview_update)
        self.opacity_slider.set(0.3)
        self.opacity_slider.grid(row=9, column=1, padx=10, pady=5, sticky="ew")

        # Size/Scale
        self.lbl_size = ctk.CTkLabel(self.scroll_frame, text="Size (Font Size / Scale %):")
        self.lbl_size.grid(row=10, column=0, padx=10, pady=5, sticky="e")
        self.size_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., 50")
        self.size_entry.insert(0, "50")
        self.size_entry.grid(row=10, column=1, padx=10, pady=5, sticky="ew")
        self.size_entry.bind("<KeyRelease>", self.trigger_preview_update)

        # Angle (Text Only)
        self.lbl_angle = ctk.CTkLabel(self.scroll_frame, text="Rotation Angle (Degrees):")
        self.lbl_angle.grid(row=11, column=0, padx=10, pady=5, sticky="e")
        self.angle_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., 30")
        self.angle_entry.insert(0, "30")
        self.angle_entry.grid(row=11, column=1, padx=10, pady=5, sticky="ew")
        self.angle_entry.bind("<KeyRelease>", self.trigger_preview_update)

        # Position
        ctk.CTkLabel(self.scroll_frame, text="Position:").grid(row=12, column=0, padx=10, pady=5, sticky="e")
        self.pos_var = ctk.StringVar(value="Center")
        self.pos_menu = ctk.CTkOptionMenu(self.scroll_frame, values=["Center", "Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right", "Tiled (Everywhere)"], variable=self.pos_var, command=self.trigger_preview_update)
        self.pos_menu.grid(row=12, column=1, padx=10, pady=5, sticky="w")

        # --- Section 4: Add Custom Footer Link ---
        ctk.CTkLabel(self.scroll_frame, text="4. Add Footer Link (Optional)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=13, column=0, padx=10, pady=(20, 5), sticky="w", columnspan=2)

        ctk.CTkLabel(self.scroll_frame, text="Footer Link URL:").grid(row=14, column=0, padx=10, pady=5, sticky="e")
        self.link_url_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., example.com")
        self.link_url_entry.grid(row=14, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.scroll_frame, text="Footer Display Text:").grid(row=15, column=0, padx=10, pady=5, sticky="e")
        self.link_text_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., Visit Our Website")
        self.link_text_entry.grid(row=15, column=1, padx=10, pady=5, sticky="ew")
        self.link_text_entry.bind("<KeyRelease>", self.trigger_preview_update)

        ctk.CTkLabel(self.scroll_frame, text="Link Position:").grid(row=16, column=0, padx=10, pady=5, sticky="e")
        self.link_pos_var = ctk.StringVar(value="Bottom-Center")
        self.link_pos_menu = ctk.CTkOptionMenu(self.scroll_frame, values=["Bottom-Center", "Bottom-Left", "Bottom-Right", "Top-Center", "Top-Left", "Top-Right"], variable=self.link_pos_var, command=self.trigger_preview_update)
        self.link_pos_menu.grid(row=16, column=1, padx=10, pady=5, sticky="w")

        # --- Section 5: Execution ---
        exec_frame = ctk.CTkFrame(self.scroll_frame)
        exec_frame.grid(row=17, column=0, columnspan=2, padx=10, pady=(30, 10), sticky="nsew")
        exec_frame.grid_columnconfigure(0, weight=1)

        self.start_btn = ctk.CTkButton(exec_frame, text="Start Processing", command=self.start_processing, font=ctk.CTkFont(size=16, weight="bold"), height=50)
        self.start_btn.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(exec_frame)
        self.progress_bar.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(exec_frame, text="Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, padx=20, pady=(0, 10))

        # ==========================================
        # RIGHT PANE: LIVE PREVIEW
        # ==========================================
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.preview_frame.grid_rowconfigure(1, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.preview_frame, text="Live Preview", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, pady=10)
        
        self.preview_canvas = ctk.CTkLabel(self.preview_frame, text="Wait for preview...", text_color="gray")
        self.preview_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)


    def handle_type_change(self, value):
        if value == "Text":
            self.btn_wm_image.grid_forget()
            self.lbl_wm_image.grid_forget()
            self.lbl_wm_text.grid(row=7, column=0, padx=10, pady=5, sticky="e")
            self.wm_text_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
            self.lbl_angle.grid(row=11, column=0, padx=10, pady=5, sticky="e")
            self.angle_entry.grid(row=11, column=1, padx=10, pady=5, sticky="ew")
        else:
            self.lbl_wm_text.grid_forget()
            self.wm_text_entry.grid_forget()
            self.lbl_angle.grid_forget()
            self.angle_entry.grid_forget()
            self.btn_wm_image.grid(row=8, column=0, padx=10, pady=5, sticky="e")
            self.lbl_wm_image.grid(row=8, column=1, padx=10, pady=5, sticky="w")
        self.trigger_preview_update()

    def select_input_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_dir = folder
            self.input_label.configure(text=folder, text_color="white")
            self.trigger_preview_update()

    def select_input_file(self):
        file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file:
            self.input_dir = file
            self.input_label.configure(text=os.path.basename(file), text_color="white")
            self.trigger_preview_update()

    def select_output_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.output_label.configure(text=folder, text_color="white")

    def select_target_image(self):
        file = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file:
            self.target_image_path = file
            self.image_label.configure(text=os.path.basename(file), text_color="white")
            self.trigger_preview_update()

    def select_wm_image(self):
        file = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file:
            self.custom_watermark_image_path = file
            self.lbl_wm_image.configure(text=os.path.basename(file), text_color="white")
            self.trigger_preview_update()

    def get_processor_instance(self):
        try:
            wm_size_str = self.size_entry.get().strip()
            wm_size = float(wm_size_str) if wm_size_str else 50
            
            wm_angle_str = self.angle_entry.get().strip()
            wm_angle = float(wm_angle_str) if wm_angle_str else 30
        except ValueError:
            return None

        return PDFProcessor(
            target_image_path=self.target_image_path or None,
            watermark_type=self.wm_type_var.get(),
            custom_watermark_text=self.wm_text_entry.get().strip() or None,
            custom_watermark_image_path=self.custom_watermark_image_path or None,
            watermark_opacity=self.opacity_slider.get(),
            watermark_position=self.pos_var.get(),
            watermark_size=wm_size,
            watermark_angle=wm_angle,
            custom_link_url=self.link_url_entry.get().strip() or None,
            custom_link_text=self.link_text_entry.get().strip() or None,
            custom_link_position=self.link_pos_var.get(),
            update_callback=self.handle_progress_update
        )

    def trigger_preview_update(self, event=None):
        """Debounces and triggers an update of the preview frame."""
        if self.preview_timer:
            self.after_cancel(self.preview_timer)
        self.preview_timer = self.after(300, self.update_preview_canvas)

    def update_preview_canvas(self):
        processor = self.get_processor_instance()
        if not processor:
             return

        # Find first PDF in input directory if available
        sample_pdf = None
        if self.input_dir and os.path.exists(self.input_dir):
            for root, _, files in os.walk(self.input_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        sample_pdf = os.path.join(root, file)
                        break
                if sample_pdf:
                    break

        img = processor.generate_preview(sample_pdf)
        if img:
            # Resize image to fit screen reasonably
            w, h = img.size
            max_height = 700
            
            # constrain width to frame constraint dynamically or hard code limit
            if h > max_height:
                ratio = max_height / h
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            
            w, h = img.size
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
            self.preview_canvas.configure(image=ctk_img, text="")
        else:
            self.preview_canvas.configure(image=None, text="Failed to render preview")

    def handle_progress_update(self, data):
        if data["type"] == "init":
            self.after(0, lambda: self.status_label.configure(text=f"Found {data['total']} PDFs. Preparing..."))
        elif data["type"] == "progress":
            progress_ratio = data["current"] / data["total"]
            self.after(0, lambda: self.progress_bar.set(progress_ratio))
            status_text = f"Processing {data['current']}/{data['total']}: {data['file']}"
            if not data["success"]:
                status_text += " [ERROR]"
            self.after(0, lambda: self.status_label.configure(text=status_text))
        elif data["type"] == "done":
            self.after(0, lambda: self.status_label.configure(text=f"Finished! Successfully processed {data['total']} PDFs.", text_color="green"))
            self.after(0, lambda: self.start_btn.configure(state="normal", text="Start Processing"))
            self.after(0, lambda: messagebox.showinfo("Complete", f"Successfully processed {data['total']} files!"))

    def run_processor(self, processor, in_dir, out_dir):
        processor.process_directory(in_dir, out_dir)

    def start_processing(self):
        if not self.input_dir or not self.output_dir:
            messagebox.showwarning("Missing Input/Output", "Please select both an Input source and an Output directory.")
            return

        if self.input_dir == self.output_dir:
            messagebox.showerror("Error", "Input and Output cannot be exactly the same directory!")
            return

        # Disable button
        self.start_btn.configure(state="disabled", text="Processing...")
        self.progress_bar.set(0)
        self.status_label.configure(text="Initializing...", text_color="white")

        self.processor = self.get_processor_instance()
        if not self.processor:
            self.start_btn.configure(state="normal", text="Start Processing")
            return

        self.processing_thread = threading.Thread(target=self.run_processor, args=(self.processor, self.input_dir, self.output_dir), daemon=True)
        self.processing_thread.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
