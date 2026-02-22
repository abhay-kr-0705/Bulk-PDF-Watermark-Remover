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
        self.geometry("900x800")
        
        # Configure layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.input_dir = ""
        self.output_dir = ""
        self.target_image_path = ""
        self.custom_watermark_image_path = ""
        
        self.processor = None
        self.processing_thread = None

        self.create_widgets()

    def create_widgets(self):
        # We'll use a scrollable frame since we have many options now
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        # --- Section 1: Directories ---
        ctk.CTkLabel(self.scroll_frame, text="1. Select Directories", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w", columnspan=2)

        self.input_btn = ctk.CTkButton(self.scroll_frame, text="Browse Input Folder", command=self.select_input_dir)
        self.input_btn.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.input_label = ctk.CTkLabel(self.scroll_frame, text="No folder selected", text_color="gray")
        self.input_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.output_btn = ctk.CTkButton(self.scroll_frame, text="Browse Output Folder", command=self.select_output_dir)
        self.output_btn.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.output_label = ctk.CTkLabel(self.scroll_frame, text="No folder selected", text_color="gray")
        self.output_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # --- Section 2: Watermark Removal ---
        ctk.CTkLabel(self.scroll_frame, text="2. Remove Existing Watermark Logo (Optional)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=3, column=0, padx=10, pady=(20, 5), sticky="w", columnspan=2)

        self.image_btn = ctk.CTkButton(self.scroll_frame, text="Select Target Image to Remove", command=self.select_target_image)
        self.image_btn.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.image_label = ctk.CTkLabel(self.scroll_frame, text="No image selected", text_color="gray")
        self.image_label.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        # --- Section 3: Add Custom Watermark ---
        ctk.CTkLabel(self.scroll_frame, text="3. Add Custom Watermark (Optional)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=5, column=0, padx=10, pady=(20, 5), sticky="w", columnspan=2)

        # Type Dropdown
        ctk.CTkLabel(self.scroll_frame, text="Watermark Type:").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.wm_type_var = ctk.StringVar(value="Text")
        self.wm_type_menu = ctk.CTkOptionMenu(self.scroll_frame, values=["Text", "Image"], variable=self.wm_type_var, command=self.toggle_wm_type)
        self.wm_type_menu.grid(row=6, column=1, padx=10, pady=5, sticky="w")

        # Text input
        self.lbl_wm_text = ctk.CTkLabel(self.scroll_frame, text="Text Content:")
        self.lbl_wm_text.grid(row=7, column=0, padx=10, pady=5, sticky="e")
        self.wm_text_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., CONFIDENTIAL")
        self.wm_text_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        # Image input
        self.btn_wm_image = ctk.CTkButton(self.scroll_frame, text="Select Watermark Image", command=self.select_wm_image)
        self.lbl_wm_image = ctk.CTkLabel(self.scroll_frame, text="No image selected", text_color="gray")

        # Common Parameters:
        # Opacity
        ctk.CTkLabel(self.scroll_frame, text="Opacity (0.1 to 1.0):").grid(row=9, column=0, padx=10, pady=5, sticky="e")
        self.opacity_slider = ctk.CTkSlider(self.scroll_frame, from_=0.1, to=1.0, number_of_steps=9)
        self.opacity_slider.set(0.3)
        self.opacity_slider.grid(row=9, column=1, padx=10, pady=5, sticky="ew")

        # Size/Scale
        self.lbl_size = ctk.CTkLabel(self.scroll_frame, text="Size (Font Size / Scale %):")
        self.lbl_size.grid(row=10, column=0, padx=10, pady=5, sticky="e")
        self.size_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., 50")
        self.size_entry.insert(0, "50")
        self.size_entry.grid(row=10, column=1, padx=10, pady=5, sticky="ew")

        # Angle (Text Only)
        self.lbl_angle = ctk.CTkLabel(self.scroll_frame, text="Rotation Angle (Degrees):")
        self.lbl_angle.grid(row=11, column=0, padx=10, pady=5, sticky="e")
        self.angle_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., 30")
        self.angle_entry.insert(0, "30")
        self.angle_entry.grid(row=11, column=1, padx=10, pady=5, sticky="ew")

        # Position
        ctk.CTkLabel(self.scroll_frame, text="Position:").grid(row=12, column=0, padx=10, pady=5, sticky="e")
        self.pos_var = ctk.StringVar(value="Center")
        self.pos_menu = ctk.CTkOptionMenu(self.scroll_frame, values=["Center", "Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"], variable=self.pos_var)
        self.pos_menu.grid(row=12, column=1, padx=10, pady=5, sticky="w")

        # --- Section 4: Add Custom Footer Link ---
        ctk.CTkLabel(self.scroll_frame, text="4. Add Footer Link (Optional)", font=ctk.CTkFont(size=18, weight="bold")).grid(row=13, column=0, padx=10, pady=(20, 5), sticky="w", columnspan=2)

        ctk.CTkLabel(self.scroll_frame, text="Footer Link URL:").grid(row=14, column=0, padx=10, pady=5, sticky="e")
        self.link_url_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., example.com")
        self.link_url_entry.grid(row=14, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.scroll_frame, text="Footer Display Text:").grid(row=15, column=0, padx=10, pady=5, sticky="e")
        self.link_text_entry = ctk.CTkEntry(self.scroll_frame, placeholder_text="e.g., Visit Our Website")
        self.link_text_entry.grid(row=15, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.scroll_frame, text="Link Position:").grid(row=16, column=0, padx=10, pady=5, sticky="e")
        self.link_pos_var = ctk.StringVar(value="Bottom-Center")
        self.link_pos_menu = ctk.CTkOptionMenu(self.scroll_frame, values=["Bottom-Center", "Bottom-Left", "Bottom-Right", "Top-Center", "Top-Left", "Top-Right"], variable=self.link_pos_var)
        self.link_pos_menu.grid(row=16, column=1, padx=10, pady=5, sticky="w")

        # --- Section 5: Execution ---
        exec_frame = ctk.CTkFrame(self)
        exec_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        exec_frame.grid_columnconfigure((0, 1), weight=1)

        self.preview_btn = ctk.CTkButton(exec_frame, text="Show Preview", command=self.preview_settings, font=ctk.CTkFont(size=14, weight="bold"), height=40, fg_color="#F2A900", hover_color="#C08400", text_color="black")
        self.preview_btn.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        self.start_btn = ctk.CTkButton(exec_frame, text="Start Processing", command=self.start_processing, font=ctk.CTkFont(size=16, weight="bold"), height=50)
        self.start_btn.grid(row=0, column=1, padx=20, pady=(15, 5), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(exec_frame)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(exec_frame, text="Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10))

    def toggle_wm_type(self, value):
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

    def select_input_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_dir = folder
            self.input_label.configure(text=folder, text_color="white")

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

    def select_wm_image(self):
        file = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file:
            self.custom_watermark_image_path = file
            self.lbl_wm_image.configure(text=os.path.basename(file), text_color="white")

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
            self.after(0, lambda: self.preview_btn.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("Complete", f"Successfully processed {data['total']} files!"))

    def get_processor_instance(self):
        try:
            wm_size = float(self.size_entry.get() or 50)
            wm_angle = float(self.angle_entry.get() or 30)
        except ValueError:
            messagebox.showerror("Input Error", "Size and Angle must be valid numbers.")
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

    def preview_settings(self):
        self.status_label.configure(text="Generating Preview...", text_color="yellow")
        self.update() # Force UI refresh

        processor = self.get_processor_instance()
        if not processor:
             self.status_label.configure(text="Ready", text_color="gray")
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
            max_height = 800
            if h > max_height:
                ratio = max_height / h
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            
            w, h = img.size
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
            
            tl = ctk.CTkToplevel(self)
            tl.title("Watermark Preview")
            tl.geometry(f"{w+40}x{h+40}")
            tl.lift() # Bring to front
            
            lbl = ctk.CTkLabel(tl, text="", image=ctk_img)
            lbl.pack(padx=20, pady=20)
            
            self.status_label.configure(text="Preview Ready!", text_color="green")
            self.after(3000, lambda: self.status_label.configure(text="Ready", text_color="gray"))
        else:
            messagebox.showerror("Error", "Could not generate preview.")
            self.status_label.configure(text="Ready", text_color="gray")

    def run_processor(self, processor, in_dir, out_dir):
        processor.process_directory(in_dir, out_dir)

    def start_processing(self):
        if not self.input_dir or not self.output_dir:
            messagebox.showwarning("Missing Folders", "Please select both Input and Output directories.")
            return

        if self.input_dir == self.output_dir:
            messagebox.showerror("Error", "Input and Output directories cannot be the same!")
            return

        # Disable button
        self.start_btn.configure(state="disabled", text="Processing...")
        self.preview_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Initializing...", text_color="white")

        self.processor = self.get_processor_instance()
        if not self.processor:
            self.start_btn.configure(state="normal", text="Start Processing")
            self.preview_btn.configure(state="normal")
            return

        self.processing_thread = threading.Thread(target=self.run_processor, args=(self.processor, self.input_dir, self.output_dir), daemon=True)
        self.processing_thread.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
