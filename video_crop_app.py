import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
import threading

class VideoCropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Kırpma Uygulaması")
        self.root.geometry("1000x700")
        
        self.video_path = None
        self.cap = None
        self.current_frame = None
        self.video_width = 0
        self.video_height = 0
        self.total_frames = 0
        self.fps = 30
        
        self.crop_x = 0
        self.crop_y = 0
        self.crop_width = 0
        self.crop_height = 0
        self.aspect_ratios = {
            "16:9": (16, 9),
            "4:3": (4, 3),
            "1:1": (1, 1),
            "9:16": (9, 16),
            "21:9": (21, 9),
            "Özel": None
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_panel = tk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        tk.Label(left_panel, text="Video Dosyası", font=("Arial", 12, "bold")).pack(pady=5)
        tk.Button(left_panel, text="Video Seç", command=self.select_video, 
                 bg="#4CAF50", fg="white", font=("Arial", 10)).pack(pady=5, fill=tk.X)
        
        self.video_label = tk.Label(left_panel, text="Henüz video seçilmedi", 
                                   wraplength=230, justify="left")
        self.video_label.pack(pady=5)
        
        tk.Label(left_panel, text="En-Boy Oranı", font=("Arial", 12, "bold")).pack(pady=(20, 5))
        
        self.aspect_var = tk.StringVar(value="16:9")
        for ratio in self.aspect_ratios.keys():
            tk.Radiobutton(left_panel, text=ratio, variable=self.aspect_var, 
                          value=ratio, command=self.on_aspect_change).pack(anchor="w")
        
        self.custom_frame = tk.Frame(left_panel)
        self.custom_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.custom_frame, text="Genişlik:").grid(row=0, column=0, sticky="w")
        self.custom_width = tk.Entry(self.custom_frame, width=8)
        self.custom_width.grid(row=0, column=1, padx=5)
        
        tk.Label(self.custom_frame, text="Yükseklik:").grid(row=1, column=0, sticky="w")
        self.custom_height = tk.Entry(self.custom_frame, width=8)
        self.custom_height.grid(row=1, column=1, padx=5)
        
        tk.Button(self.custom_frame, text="Uygula", command=self.apply_custom_size).grid(row=2, column=0, columnspan=2, pady=5)
        
        tk.Label(left_panel, text="Kırpma Pozisyonu", font=("Arial", 12, "bold")).pack(pady=(20, 5))
        
        pos_frame = tk.Frame(left_panel)
        pos_frame.pack(fill=tk.X)
        
        tk.Label(pos_frame, text="X:").grid(row=0, column=0, sticky="w")
        self.pos_x_var = tk.IntVar()
        self.pos_x_scale = tk.Scale(pos_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                   variable=self.pos_x_var, command=self.on_position_change)
        self.pos_x_scale.grid(row=0, column=1, sticky="ew")
        
        tk.Label(pos_frame, text="Y:").grid(row=1, column=0, sticky="w")
        self.pos_y_var = tk.IntVar()
        self.pos_y_scale = tk.Scale(pos_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                   variable=self.pos_y_var, command=self.on_position_change)
        self.pos_y_scale.grid(row=1, column=1, sticky="ew")
        
        pos_frame.columnconfigure(1, weight=1)
        
        tk.Button(left_panel, text="Videoyu Kırp ve Kaydet", command=self.start_crop_video,
                 bg="#FF9800", fg="white", font=("Arial", 11, "bold")).pack(pady=20, fill=tk.X)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(left_panel, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = tk.Label(left_panel, text="")
        self.progress_label.pack()
        
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(right_panel, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
    def select_video(self):
        file_path = filedialog.askopenfilename(
            title="Video Dosyası Seçin",
            filetypes=[
                ("Video dosyaları", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
                ("Tüm dosyalar", "*.*")
            ]
        )
        
        if file_path:
            self.video_path = file_path
            self.video_label.config(text=f"Seçilen: {os.path.basename(file_path)}")
            self.load_video()
    
    def load_video(self):
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Hata", "Video dosyası açılamadı!")
            return
        
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            self.update_preview()
        
        self.update_position_controls()
    
    def update_position_controls(self):
        if not self.video_width or not self.video_height:
            return
            
        max_x = max(0, self.video_width - self.crop_width)
        max_y = max(0, self.video_height - self.crop_height)
        
        self.pos_x_scale.config(to=max_x)
        self.pos_y_scale.config(to=max_y)
    
    def on_aspect_change(self):
        self.calculate_crop_dimensions()
        self.update_preview()
    
    def apply_custom_size(self):
        try:
            w = int(self.custom_width.get())
            h = int(self.custom_height.get())
            if w > 0 and h > 0:
                self.aspect_ratios["Özel"] = (w, h)
                self.aspect_var.set("Özel")
                self.calculate_crop_dimensions()
                self.update_preview()
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz boyut değerleri!")
    
    def calculate_crop_dimensions(self):
        if not self.video_width or not self.video_height:
            return
            
        selected_ratio = self.aspect_var.get()
        ratio = self.aspect_ratios.get(selected_ratio)
        
        if ratio:
            ratio_w, ratio_h = ratio
            
            scale_by_width = self.video_width / ratio_w
            scale_by_height = self.video_height / ratio_h
            scale = min(scale_by_width, scale_by_height)
            
            self.crop_width = int(ratio_w * scale)
            self.crop_height = int(ratio_h * scale)
        
        self.update_position_controls()
    
    def on_position_change(self, value=None):
        self.crop_x = self.pos_x_var.get()
        self.crop_y = self.pos_y_var.get()
        self.update_preview()
    
    def on_canvas_click(self, event):
        if not self.current_frame is None and self.crop_width > 0 and self.crop_height > 0:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 0 and canvas_height > 0:
                video_aspect = self.video_width / self.video_height
                canvas_aspect = canvas_width / canvas_height
                
                if video_aspect > canvas_aspect:
                    display_width = canvas_width
                    display_height = canvas_width / video_aspect
                    offset_x = 0
                    offset_y = (canvas_height - display_height) / 2
                else:
                    display_height = canvas_height
                    display_width = canvas_height * video_aspect
                    offset_x = (canvas_width - display_width) / 2
                    offset_y = 0
                
                video_x = int((event.x - offset_x) / display_width * self.video_width)
                video_y = int((event.y - offset_y) / display_height * self.video_height)
                
                new_x = max(0, min(video_x - self.crop_width // 2, self.video_width - self.crop_width))
                new_y = max(0, min(video_y - self.crop_height // 2, self.video_height - self.crop_height))
                
                self.pos_x_var.set(new_x)
                self.pos_y_var.set(new_y)
                self.crop_x = new_x
                self.crop_y = new_y
                
                self.update_preview()
    
    def update_preview(self):
        if self.current_frame is None:
            return
            
        frame = self.current_frame.copy()
        
        if self.crop_width > 0 and self.crop_height > 0:
            overlay = frame.copy()
            cv2.rectangle(overlay, (self.crop_x, self.crop_y), 
                         (self.crop_x + self.crop_width, self.crop_y + self.crop_height),
                         (0, 255, 0), 3)
            
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.rectangle(mask, (self.crop_x, self.crop_y), 
                         (self.crop_x + self.crop_width, self.crop_y + self.crop_height), 255, -1)
            
            frame_darkened = frame.copy()
            frame_darkened[mask == 0] = frame_darkened[mask == 0] * 0.3
            frame = cv2.addWeighted(frame_darkened, 0.7, overlay, 0.3, 0)
        
        self.display_frame(frame)
    
    def display_frame(self, frame):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            h, w = frame.shape[:2]
            scale = min(canvas_width / w, canvas_height / h)
            
            new_width = int(w * scale)
            new_height = int(h * scale)
            
            frame_resized = cv2.resize(frame, (new_width, new_height))
            
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image)
            
            self.canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            self.canvas.create_image(x, y, anchor=tk.NW, image=photo)
            self.canvas.image = photo
    
    def start_crop_video(self):
        if not self.video_path:
            messagebox.showerror("Hata", "Lütfen önce bir video dosyası seçin!")
            return
            
        if self.crop_width == 0 or self.crop_height == 0:
            messagebox.showerror("Hata", "Lütfen bir en-boy oranı seçin!")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Kırpılmış videoyu kaydet",
            defaultextension=".mp4",
            filetypes=[("MP4 dosyası", "*.mp4"), ("AVI dosyası", "*.avi")]
        )
        
        if output_path:
            thread = threading.Thread(target=self.crop_video, args=(output_path,))
            thread.daemon = True
            thread.start()
    
    def crop_video(self, output_path):
        try:
            self.progress_label.config(text="Video işleniyor...")
            self.progress_var.set(0)
            
            import subprocess
            import tempfile
            
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video_path = temp_video.name
            temp_video.close()
            
            cap = cv2.VideoCapture(self.video_path)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, self.fps, (self.crop_width, self.crop_height))
            
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                cropped_frame = frame[self.crop_y:self.crop_y + self.crop_height,
                                    self.crop_x:self.crop_x + self.crop_width]
                
                out.write(cropped_frame)
                
                frame_count += 1
                progress = (frame_count / self.total_frames) * 50
                self.progress_var.set(progress)
                
                self.root.update_idletasks()
            
            cap.release()
            out.release()
            
            self.progress_label.config(text="Ses ekleniyor...")
            
            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-i', temp_video_path,
                    '-i', self.video_path,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',
                    output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.progress_var.set(100)
                    self.progress_label.config(text="Tamamlandı!")
                    messagebox.showinfo("Başarılı", f"Video ses ile birlikte başarıyla kaydedildi:\n{output_path}")
                else:
                    import shutil
                    shutil.move(temp_video_path, output_path)
                    messagebox.showwarning("Uyarı", 
                        f"Video kırpıldı ancak ses eklenemedi (FFmpeg gerekli).\n"
                        f"Sessiz video kaydedildi: {output_path}\n\n"
                        f"Sesli video için FFmpeg'i yükleyin.")
                
            except FileNotFoundError:
                import shutil
                shutil.move(temp_video_path, output_path)
                messagebox.showwarning("Uyarı", 
                    f"Video kırpıldı ancak ses eklenemedi (FFmpeg bulunamadı).\n"
                    f"Sessiz video kaydedildi: {output_path}\n\n"
                    f"Sesli video için FFmpeg'i yükleyin: https://ffmpeg.org")
            
            try:
                if os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
            except:
                pass
                
        except Exception as e:
            messagebox.showerror("Hata", f"Video işlenirken hata oluştu:\n{str(e)}")
        finally:
            self.progress_var.set(0)
            self.progress_label.config(text="")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCropApp(root)
    root.mainloop()