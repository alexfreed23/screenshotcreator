"""
Screenshot Tool with Drawing Annotations
Інструмент для скріншотів з можливістю малювання
Requirements: pip install pillow mss tkinter (tkinter вбудований в Python)
"""

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import tkinter.font as tkfont
from PIL import Image, ImageDraw, ImageTk, ImageGrab
import mss
import mss.tools
import os
import sys
import time
import datetime


# ─── Головне вікно ────────────────────────────────────────────────────────────

class ScreenshotTool:
    def __init__(self, root):
        self.root = root
        self.root.title("📸 Screenshot Tool")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        # Стан малювання
        self.current_tool = tk.StringVar(value="arrow")
        self.brush_color = "#FF4444"
        self.brush_size = tk.IntVar(value=3)
        self.fill_shape = tk.BooleanVar(value=False)

        # Зображення
        self.original_image = None
        self.working_image = None
        self.photo_image = None
        self.draw_layer = None

        # Для малювання
        self.start_x = None
        self.start_y = None
        self.temp_item = None
        self.drawn_items = []  # для undo
        self.draw_history = []  # PIL images для undo

        self._build_ui()
        self._bind_events()

    # ─── Побудова інтерфейсу ──────────────────────────────────────────────────

    def _build_ui(self):
        # Верхня панель
        self._build_toolbar()
        # Центральна зона
        self._build_main_area()
        # Нижній статус-бар
        self._build_statusbar()

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg="#16213e", pady=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # ── Скріншот кнопки ──
        section = tk.Frame(toolbar, bg="#16213e")
        section.pack(side=tk.LEFT, padx=8)

        self._tb_label(section, "CAPTURE")
        self._tb_btn(section, "🖥 Весь екран", self.capture_fullscreen)
        self._tb_btn(section, "✂ Область", self.capture_region)

        self._sep(toolbar)

        # ── Інструменти ──
        tools_frame = tk.Frame(toolbar, bg="#16213e")
        tools_frame.pack(side=tk.LEFT, padx=8)
        self._tb_label(tools_frame, "ІНСТРУМЕНТИ")

        tools = [
            ("🖱", "select", "Вибір"),
            ("✏️", "pen", "Олівець"),
            ("➡", "arrow", "Стрілка"),
            ("▭", "rect", "Прямокутник"),
            ("○", "ellipse", "Еліпс"),
            ("╱", "line", "Лінія"),
            ("T", "text", "Текст"),
            ("⬛", "blur", "Блюр (приховати)"),
        ]

        for icon, name, tip in tools:
            self._tool_btn(tools_frame, icon, name, tip)

        self._sep(toolbar)

        # ── Налаштування пензля ──
        brush_frame = tk.Frame(toolbar, bg="#16213e")
        brush_frame.pack(side=tk.LEFT, padx=8)
        self._tb_label(brush_frame, "ПЕНЗЕЛЬ")

        tk.Label(brush_frame, text="Розмір:", bg="#16213e", fg="#8892b0",
                 font=("Consolas", 8)).pack(side=tk.LEFT)
        size_spin = tk.Spinbox(brush_frame, from_=1, to=50,
                               textvariable=self.brush_size,
                               width=4, bg="#0f3460", fg="white",
                               insertbackground="white",
                               buttonbackground="#0f3460",
                               font=("Consolas", 10))
        size_spin.pack(side=tk.LEFT, padx=4)

        tk.Checkbutton(brush_frame, text="Заливка",
                       variable=self.fill_shape,
                       bg="#16213e", fg="#8892b0",
                       selectcolor="#0f3460",
                       activebackground="#16213e",
                       activeforeground="white",
                       font=("Consolas", 8)).pack(side=tk.LEFT, padx=4)

        self._sep(toolbar)

        # ── Колір ──
        color_frame = tk.Frame(toolbar, bg="#16213e")
        color_frame.pack(side=tk.LEFT, padx=8)
        self._tb_label(color_frame, "КОЛІР")

        # Швидкі кольори
        quick_colors = ["#FF4444", "#FF9900", "#FFDD00",
                        "#44FF44", "#4499FF", "#AA44FF",
                        "#FFFFFF", "#000000"]
        for c in quick_colors:
            b = tk.Button(color_frame, bg=c, width=2, height=1,
                          relief="flat", cursor="hand2",
                          command=lambda col=c: self._set_color(col))
            b.pack(side=tk.LEFT, padx=1)

        self.color_preview = tk.Button(
            color_frame, bg=self.brush_color, width=3, height=1,
            relief="raised", cursor="hand2",
            command=self._pick_color,
            text="⊕", fg="white", font=("Consolas", 9))
        self.color_preview.pack(side=tk.LEFT, padx=6)

        self._sep(toolbar)

        # ── Дії ──
        action_frame = tk.Frame(toolbar, bg="#16213e")
        action_frame.pack(side=tk.LEFT, padx=8)
        self._tb_label(action_frame, "ДІЇ")

        self._tb_btn(action_frame, "↩ Undo", self.undo, accent="#e94560")
        self._tb_btn(action_frame, "🗑 Очистити", self.clear_annotations, accent="#e94560")
        self._tb_btn(action_frame, "💾 Зберегти", self.save_image, accent="#00b4d8")
        self._tb_btn(action_frame, "📋 Копіювати", self.copy_to_clipboard, accent="#00b4d8")

    def _tb_label(self, parent, text):
        tk.Label(parent, text=text, bg="#16213e", fg="#4a5568",
                 font=("Consolas", 7, "bold")).pack(side=tk.LEFT, padx=(0, 4))

    def _tb_btn(self, parent, text, cmd, accent="#e2e8f0"):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg="#0f3460", fg=accent,
                        activebackground="#1a4a80", activeforeground="white",
                        relief="flat", padx=8, pady=3,
                        font=("Consolas", 9), cursor="hand2",
                        bd=0)
        btn.pack(side=tk.LEFT, padx=2)
        return btn

    def _sep(self, parent):
        tk.Frame(parent, bg="#2d3561", width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=4)

    def _tool_btn(self, parent, icon, name, tip):
        var = self.current_tool
        btn = tk.Radiobutton(
            parent, text=f"{icon}", variable=var, value=name,
            indicatoron=False,
            bg="#0f3460", fg="white",
            selectcolor="#e94560",
            activebackground="#1a4a80",
            relief="flat", padx=6, pady=3,
            font=("Consolas", 11), cursor="hand2",
            bd=0
        )
        btn.pack(side=tk.LEFT, padx=1)

        # Підказка
        self._tooltip(btn, tip)

    def _tooltip(self, widget, text):
        def enter(e):
            self.status_var.set(f"Інструмент: {text}")
        def leave(e):
            self.status_var.set("Готовий")
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _build_main_area(self):
        main = tk.Frame(self.root, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True)

        # Ліва панель - мініатюри / підказки
        self.sidebar = tk.Frame(main, bg="#16213e", width=160)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="ПІДКАЗКИ",
                 bg="#16213e", fg="#4a5568",
                 font=("Consolas", 8, "bold")).pack(pady=(12, 4))

        hints = [
            ("🖥 Весь екран", "Зробити скріншот\nвсього екрану"),
            ("✂ Область", "Намалювати рамку\nдля вирізання"),
            ("➡ Стрілка", "Клік+тягни\nдля стрілки"),
            ("▭ Прямокутник", "Обводить область"),
            ("✏️ Олівець", "Вільне малювання"),
            ("T Текст", "Клік для введення"),
            ("Ctrl+Z", "Відмінити дію"),
            ("Ctrl+S", "Зберегти файл"),
        ]
        for title, desc in hints:
            f = tk.Frame(self.sidebar, bg="#0f3460", pady=4, padx=6)
            f.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(f, text=title, bg="#0f3460", fg="#00b4d8",
                     font=("Consolas", 8, "bold"),
                     anchor="w").pack(fill=tk.X)
            tk.Label(f, text=desc, bg="#0f3460", fg="#8892b0",
                     font=("Consolas", 7),
                     anchor="w", justify=tk.LEFT).pack(fill=tk.X)

        # Центральна канва зі скролом
        canvas_frame = tk.Frame(main, bg="#1a1a2e")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                                     bg="#0f3460", troughcolor="#16213e")
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                     bg="#0f3460", troughcolor="#16213e")

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#0d0d1a", cursor="crosshair",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
            highlightthickness=0
        )

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Placeholder текст
        self._show_placeholder()

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg="#0f3460", pady=3)
        bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar(value="Готовий. Зробіть скріншот або відкрийте зображення.")
        tk.Label(bar, textvariable=self.status_var,
                 bg="#0f3460", fg="#8892b0",
                 font=("Consolas", 8),
                 anchor="w").pack(side=tk.LEFT, padx=10)

        self.coords_var = tk.StringVar(value="x:0 y:0")
        tk.Label(bar, textvariable=self.coords_var,
                 bg="#0f3460", fg="#4a5568",
                 font=("Consolas", 8)).pack(side=tk.RIGHT, padx=10)

    def _show_placeholder(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 500
        self.canvas.create_text(
            w // 2, h // 2 - 20,
            text="📸",
            font=("", 48), fill="#2d3561"
        )
        self.canvas.create_text(
            w // 2, h // 2 + 40,
            text="Натисніть «Весь екран» або «Область»\nщоб зробити скріншот",
            font=("Consolas", 12), fill="#2d3561",
            justify=tk.CENTER
        )

    # ─── Прив'язка подій ──────────────────────────────────────────────────────

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)

        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-s>", lambda e: self.save_image())
        self.root.bind("<Control-c>", lambda e: self.copy_to_clipboard())

    def _canvas_coords(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        return int(x), int(y)

    def _on_motion(self, event):
        x, y = self._canvas_coords(event)
        self.coords_var.set(f"x:{x}  y:{y}")

    # ─── Скріншоти ────────────────────────────────────────────────────────────

    def capture_fullscreen(self):
        self.root.iconify()
        self.root.after(300, self._do_fullscreen)

    def _do_fullscreen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        self.root.deiconify()
        self._load_image(img)
        self.status_var.set("✅ Скріншот зроблено!")

    def capture_region(self):
        self.root.iconify()
        self.root.after(300, self._show_region_selector)

    def _show_region_selector(self):
        selector = RegionSelector(self.root, self._on_region_selected)

    def _on_region_selected(self, bbox):
        self.root.deiconify()
        if bbox:
            with mss.mss() as sct:
                region = {"left": bbox[0], "top": bbox[1],
                          "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]}
                sct_img = sct.grab(region)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            self._load_image(img)
            self.status_var.set("✅ Область захоплено!")
        else:
            self.root.deiconify()

    def _load_image(self, img: Image.Image):
        self.original_image = img.copy()
        self.working_image = img.copy()
        self.draw_history = [img.copy()]
        self.drawn_items = []
        self._refresh_canvas()

    def _refresh_canvas(self):
        if self.working_image is None:
            return
        w, h = self.working_image.size
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.photo_image = ImageTk.PhotoImage(self.working_image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="image")

    # ─── Малювання ────────────────────────────────────────────────────────────

    def _on_press(self, event):
        if self.working_image is None:
            return
        self.start_x, self.start_y = self._canvas_coords(event)
        self.temp_item = None

        if self.current_tool.get() == "pen":
            self._save_state()

        if self.current_tool.get() == "text":
            self._add_text(self.start_x, self.start_y)

    def _on_drag(self, event):
        if self.working_image is None or self.start_x is None:
            return
        x, y = self._canvas_coords(event)
        tool = self.current_tool.get()
        color = self.brush_color
        size = self.brush_size.get()

        if self.temp_item:
            self.canvas.delete(self.temp_item)

        if tool == "pen":
            self.canvas.create_line(self.start_x, self.start_y, x, y,
                                    fill=color, width=size, smooth=True,
                                    capstyle=tk.ROUND, joinstyle=tk.ROUND,
                                    tags="drawing")
            draw = ImageDraw.Draw(self.working_image)
            draw.line([self.start_x, self.start_y, x, y],
                      fill=color, width=size)
            self.start_x, self.start_y = x, y

        elif tool == "arrow":
            self.temp_item = self.canvas.create_line(
                self.start_x, self.start_y, x, y,
                fill=color, width=size + 1,
                arrow=tk.LAST,
                arrowshape=(12 + size * 2, 15 + size * 2, 5 + size),
                tags="temp"
            )

        elif tool == "rect":
            outline = color
            fill = color if self.fill_shape.get() else ""
            self.temp_item = self.canvas.create_rectangle(
                self.start_x, self.start_y, x, y,
                outline=outline, fill=fill, width=size, tags="temp"
            )

        elif tool == "ellipse":
            outline = color
            fill = color if self.fill_shape.get() else ""
            self.temp_item = self.canvas.create_oval(
                self.start_x, self.start_y, x, y,
                outline=outline, fill=fill, width=size, tags="temp"
            )

        elif tool == "line":
            self.temp_item = self.canvas.create_line(
                self.start_x, self.start_y, x, y,
                fill=color, width=size, tags="temp"
            )

        elif tool == "blur":
            self.temp_item = self.canvas.create_rectangle(
                self.start_x, self.start_y, x, y,
                outline="#FFFFFF", fill="", width=2,
                dash=(4, 4), tags="temp"
            )

    def _on_release(self, event):
        if self.working_image is None or self.start_x is None:
            return
        x, y = self._canvas_coords(event)
        tool = self.current_tool.get()
        color = self.brush_color
        size = self.brush_size.get()

        if tool == "pen":
            self._refresh_canvas()
            return

        self._save_state()

        draw = ImageDraw.Draw(self.working_image)
        fill_color = color if self.fill_shape.get() else None

        if tool == "arrow":
            self._draw_arrow_pil(draw, self.start_x, self.start_y, x, y, color, size)

        elif tool == "rect":
            draw.rectangle([self.start_x, self.start_y, x, y],
                           outline=color, fill=fill_color, width=size)

        elif tool == "ellipse":
            draw.ellipse([self.start_x, self.start_y, x, y],
                         outline=color, fill=fill_color, width=size)

        elif tool == "line":
            draw.line([self.start_x, self.start_y, x, y],
                      fill=color, width=size)

        elif tool == "blur":
            x0, y0 = min(self.start_x, x), min(self.start_y, y)
            x1, y1 = max(self.start_x, x), max(self.start_y, y)
            if x1 > x0 and y1 > y0:
                region = self.working_image.crop((x0, y0, x1, y1))
                blurred = region.resize(
                    (max(1, (x1 - x0) // 10), max(1, (y1 - y0) // 10)),
                    Image.BOX
                ).resize((x1 - x0, y1 - y0), Image.NEAREST)
                self.working_image.paste(blurred, (x0, y0))

        self.start_x = self.start_y = None
        self.temp_item = None
        self._refresh_canvas()

    def _draw_arrow_pil(self, draw, x1, y1, x2, y2, color, size):
        import math
        draw.line([x1, y1, x2, y2], fill=color, width=size + 1)
        angle = math.atan2(y2 - y1, x2 - x1)
        head_len = 15 + size * 3
        head_angle = math.pi / 6
        ax1 = x2 - head_len * math.cos(angle - head_angle)
        ay1 = y2 - head_len * math.sin(angle - head_angle)
        ax2 = x2 - head_len * math.cos(angle + head_angle)
        ay2 = y2 - head_len * math.sin(angle + head_angle)
        draw.polygon([(x2, y2), (ax1, ay1), (ax2, ay2)], fill=color)

    def _add_text(self, x, y):
        dialog = TextInputDialog(self.root, self.brush_color, self.brush_size.get())
        self.root.wait_window(dialog.top)
        if dialog.result:
            text, font_size = dialog.result
            self._save_state()
            draw = ImageDraw.Draw(self.working_image)
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = None
            draw.text((x, y), text, fill=self.brush_color, font=font)
            self._refresh_canvas()

    # ─── Undo / Clear ─────────────────────────────────────────────────────────

    def _save_state(self):
        if self.working_image:
            self.draw_history.append(self.working_image.copy())
            if len(self.draw_history) > 30:
                self.draw_history.pop(0)

    def undo(self):
        if len(self.draw_history) > 1:
            self.draw_history.pop()
            self.working_image = self.draw_history[-1].copy()
            self._refresh_canvas()
            self.status_var.set("↩ Відмінено")
        else:
            self.status_var.set("Немає дій для відміни")

    def clear_annotations(self):
        if self.original_image:
            if messagebox.askyesno("Очистити", "Видалити всі анотації?"):
                self.working_image = self.original_image.copy()
                self.draw_history = [self.working_image.copy()]
                self._refresh_canvas()
                self.status_var.set("🗑 Анотації очищено")

    # ─── Колір ────────────────────────────────────────────────────────────────

    def _pick_color(self):
        color = colorchooser.askcolor(color=self.brush_color,
                                      title="Виберіть колір")[1]
        if color:
            self._set_color(color)

    def _set_color(self, color):
        self.brush_color = color
        self.color_preview.configure(bg=color)

    # ─── Зберегти / Скопіювати ────────────────────────────────────────────────

    def save_image(self):
        if self.working_image is None:
            messagebox.showwarning("Немає зображення", "Спочатку зробіть скріншот.")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"screenshot_{ts}.png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All", "*.*")]
        )
        if path:
            self.working_image.save(path)
            self.status_var.set(f"💾 Збережено: {os.path.basename(path)}")

    def copy_to_clipboard(self):
        if self.working_image is None:
            return
        # Windows clipboard via tkinter
        import io
        try:
            output = io.BytesIO()
            self.working_image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            self.status_var.set("📋 Скопійовано в буфер обміну")
        except Exception as e:
            self.status_var.set(f"Помилка копіювання: {e}")


# ─── Вибір регіону ────────────────────────────────────────────────────────────

class RegionSelector:
    def __init__(self, parent, callback):
        self.callback = callback
        self.start = None
        self.rect = None

        self.win = tk.Toplevel(parent)
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-alpha", 0.3)
        self.win.configure(bg="black")
        self.win.attributes("-topmost", True)

        self.canvas = tk.Canvas(self.win, cursor="cross",
                                bg="gray10", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_text(
            self.win.winfo_screenwidth() // 2,
            self.win.winfo_screenheight() // 2,
            text="Намалюйте область для захвату\n(ESC - скасувати)",
            fill="white", font=("Consolas", 16), justify=tk.CENTER
        )

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.win.bind("<Escape>", lambda e: self._cancel())

    def _press(self, e):
        self.start = (e.x_root, e.y_root)
        self.canvas.delete("rect")

    def _drag(self, e):
        self.canvas.delete("rect")
        x0, y0 = self.start
        self.canvas.create_rectangle(
            x0, y0, e.x_root, e.y_root,
            outline="#00b4d8", width=2, tags="rect"
        )

    def _release(self, e):
        x0, y0 = self.start
        x1, y1 = e.x_root, e.y_root
        bbox = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        self.win.destroy()
        self.callback(bbox)

    def _cancel(self):
        self.win.destroy()
        self.callback(None)


# ─── Діалог вводу тексту ──────────────────────────────────────────────────────

class TextInputDialog:
    def __init__(self, parent, color, size):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Додати текст")
        self.top.configure(bg="#16213e")
        self.top.resizable(False, False)
        self.top.grab_set()

        tk.Label(self.top, text="Текст:", bg="#16213e", fg="white",
                 font=("Consolas", 10)).pack(padx=16, pady=(12, 2), anchor="w")
        self.entry = tk.Entry(self.top, bg="#0f3460", fg=color,
                              insertbackground="white",
                              font=("Consolas", 12), width=30, bd=0, padx=6)
        self.entry.pack(padx=16, pady=4)
        self.entry.focus()

        tk.Label(self.top, text="Розмір шрифту:", bg="#16213e", fg="white",
                 font=("Consolas", 10)).pack(padx=16, pady=(8, 2), anchor="w")
        self.size_var = tk.IntVar(value=max(12, size * 4))
        tk.Spinbox(self.top, from_=8, to=120, textvariable=self.size_var,
                   bg="#0f3460", fg="white", buttonbackground="#0f3460",
                   font=("Consolas", 10), width=6).pack(padx=16, pady=4, anchor="w")

        btn_frame = tk.Frame(self.top, bg="#16213e")
        btn_frame.pack(pady=12)

        tk.Button(btn_frame, text="✔ Додати", command=self._ok,
                  bg="#e94560", fg="white", font=("Consolas", 10),
                  relief="flat", padx=12, pady=4).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="✖ Скасувати", command=self.top.destroy,
                  bg="#0f3460", fg="white", font=("Consolas", 10),
                  relief="flat", padx=12, pady=4).pack(side=tk.LEFT)

        self.entry.bind("<Return>", lambda e: self._ok())

    def _ok(self):
        text = self.entry.get().strip()
        if text:
            self.result = (text, self.size_var.get())
        self.top.destroy()


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    try:
        import mss
        from PIL import Image, ImageDraw, ImageTk
    except ImportError:
        print("Встановіть залежності:")
        print("  pip install mss pillow")
        sys.exit(1)

    root = tk.Tk()
    app = ScreenshotTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()