# gui.py
from __future__ import annotations
import traceback
import datetime as dt
import threading
from pathlib import Path
import cv2  # type: ignore
from PIL import Image, ImageTk  # type: ignore
import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import DateEntry  # type: ignore
from tkinterdnd2 import TkinterDnD, DND_FILES  # type: ignore
import config  # type: ignore
from core.pipeline import run as run_pipeline  # type: ignore

POSES = ["Prone", "Supine", "Sitting"]

def parse_drop_path(data: str) -> str:
    # TkDnD often wraps path in braces if it contains spaces
    p = data.strip()
    if p.startswith("{") and p.endswith("}"):
        p = p[1:-1]
    return p

class InfantAnalyzerGUI:
    preview_window: tk.Toplevel
    preview_label: tk.Label
    _current_preview_img: ImageTk.PhotoImage | None = None

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Infant Motor Development Analyzer")
        self.root.configure(bg="#f0f7ff")
        self.root.resizable(False, False)

        # center window
        w, h = 650, 720
        sx, sy = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = int((sx / 2) - (w / 2))
        y = int((sy / 2) - (h / 2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # state
        self.pose_videos = {p: {"path": None, "loaded": False} for p in POSES}
        self.selected_pose = tk.StringVar(value="Prone")
        self.processing = False

        # birthdate state (default = 50 days ago)
        self.birthday_var = tk.StringVar()
        default_date = dt.date.today() - dt.timedelta(days=50)
        self.birthday_var.set(default_date.strftime("%d/%m/%y"))

        self._build_ui()
        self.init_preview_window()
        self.update_generate_state()

    ####################################
    def init_preview_window(self):
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Live Preview")
        self.preview_window.geometry("660x520")
        self.preview_window.configure(bg="black")

        self.preview_label = tk.Label(self.preview_window, bg="black")
        self.preview_label.pack(fill="both", expand=True)

        # start hidden
        self.preview_window.withdraw()

        # if user closes preview window, just hide it (don't destroy)
        self.preview_window.protocol("WM_DELETE_WINDOW", self.preview_window.withdraw)

    def show_preview_window(self):
        # safe even if already visible
        if hasattr(self, "preview_window") and self.preview_window.winfo_exists():
            self.preview_window.deiconify()
            self.preview_window.lift()

    def update_preview_frame(self, frame):
        # If preview window isn't ready yet, ignore frames safely
        if not hasattr(self, "preview_label"):
            return
        if not self.preview_window.winfo_exists():
            return

        # Convert BGR -> RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(rgb)

        # Optional: resize to fit window (keeps it smooth)
        img = img.resize((640, 480))

        imgtk = ImageTk.PhotoImage(image=img)

        # keep reference so it doesn't get garbage-collected
        self._current_preview_img = imgtk
        self.preview_label.config(image=imgtk)

    # ---------------- UI ----------------

    def _build_ui(self):
        tk.Label(
            self.root,
            text="Infant Motor Development Analyzer",
            font=("Helvetica", 20, "bold"),
            bg="#f0f7ff",
            fg="#003366",
        ).pack(pady=(15, 10))

        # birthday
        tk.Label(
            self.root,
            text="Choose Infant Birthday:",
            font=("Segoe UI", 15),
            bg="#f0f7ff",
            fg="#002244",
        ).pack(pady=(10, 5))

        self.calendar = DateEntry(
            self.root,
            textvariable=self.birthday_var,
            width=14,
            background="#0066cc",
            foreground="white",
            borderwidth=0,
            font=("Segoe UI", 11),
            date_pattern="dd/mm/yy",
            selectbackground="#3399ff",
            selectforeground="white",
        )
        self.calendar.pack(pady=5)
        self.calendar.bind("<<DateEntrySelected>>", lambda e: self.update_generate_state())

        self.age_status_label = tk.Label(self.root, text="", font=("Segoe UI", 10), bg="#f0f7ff")
        self.age_status_label.pack(pady=(0, 10))

        # pose selector
        pose_row = tk.Frame(self.root, bg="#f0f7ff")
        pose_row.pack(pady=(5, 10))

        tk.Label(pose_row, text="Run pose:", font=("Segoe UI", 11, "bold"), bg="#f0f7ff", fg="#003366").pack(side="left", padx=(0, 8))
        for p in POSES:
            tk.Radiobutton(
                pose_row,
                text=p,
                variable=self.selected_pose,
                value=p,
                bg="#f0f7ff",
                fg="#003366",
                activebackground="#f0f7ff",
                command=self.update_generate_state,
            ).pack(side="left", padx=6)

        # video inputs
        tk.Label(
            self.root,
            text="Load Infant Videos:",
            font=("Segoe UI", 15),
            bg="#f0f7ff",
            fg="#002244",
        ).pack(pady=(15, 5))

        self.drop_frame = tk.Frame(self.root, bg="#f0f7ff")
        self.drop_frame.pack(pady=10)

        self._create_video_input("Prone", 0, config.PRONE_ICON)
        self._create_video_input("Supine", 1, config.SUPINE_ICON)
        self._create_video_input("Sitting", 2, config.SITTING_ICON)

        # status + buttons
        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10), bg="#f0f7ff", fg="#003366")
        self.status_label.pack(pady=(10, 5))

        self.generate_button = tk.Button(
            self.root,
            text="Generate",
            command=self.on_generate_clicked,
            font=("Segoe UI", 11, "bold"),
            bg="lightgray",
            fg="gray",
            activebackground="#218838",
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.generate_button.pack(side="bottom", pady=15)

    def _create_video_input(self, pose: str, col: int, icon_path: Path):
        # Title
        tk.Label(
            self.drop_frame,
            text=pose,
            font=("Segoe UI", 11, "bold"),
            bg="#f0f7ff",
            fg="#003366",
        ).grid(row=0, column=col, pady=(0, 5))

        # Image
        img = None
        if icon_path and icon_path.exists():
            img = tk.PhotoImage(file=str(icon_path)).subsample(2, 2)
            lbl_img = tk.Label(self.drop_frame, image=img, bg="#f0f7ff")
            lbl_img.image = img
            lbl_img.grid(row=1, column=col, pady=(0, 5))

        # Open button
        tk.Button(
            self.drop_frame,
            text=f"Open {pose} Video",
            command=lambda p=pose: self.open_video(p),
            font=("Segoe UI", 9),
            bg="white",
            fg="#003366",
        ).grid(row=2, column=col, pady=(0, 5))

        # Drop zone
        drop_area = tk.Label(
            self.drop_frame,
            text="Drop Video Here",
            width=18,
            height=5,
            bg="#d0e8ff",
            relief="ridge",
            bd=2,
            font=("Segoe UI", 9, "bold"),
        )
        drop_area.grid(row=3, column=col, pady=(0, 5), padx=15)
        drop_area.drop_target_register(DND_FILES)
        drop_area.dnd_bind("<<Drop>>", lambda e, p=pose: self.on_drop(e, p))

        # Success label
        success_lbl = tk.Label(self.drop_frame, text="", font=("Segoe UI", 9), bg="#f0f7ff", fg="green")
        success_lbl.grid(row=4, column=col)
        success_lbl.grid_remove()

        self.pose_videos[pose]["success_lbl"] = success_lbl

    # ---------------- logic ----------------

    def get_birthdate(self) -> dt.date | None:
        try:
            return dt.datetime.strptime(self.birthday_var.get(), "%d/%m/%y").date()
        except Exception:
            return None

    def is_age_valid(self) -> bool:
        bd = self.get_birthdate()
        if bd is None:
            self.age_status_label.config(text="Invalid date.", fg="red")
            return False

        age_days = (dt.date.today() - bd).days
        age_months = round(age_days / 30.44, 2)

        if age_days < 0:
            self.age_status_label.config(text=f"Biological Age: {age_months} months\nAge must be positive", fg="red")
            return False
        if age_days < 60:
            self.age_status_label.config(text=f"Biological Age: {age_months} months\nToo young (<2 months)", fg="red")
            return False
        if age_days > 180:
            self.age_status_label.config(text=f"Biological Age: {age_months} months\nToo old (>6 months)", fg="red")
            return False

        self.age_status_label.config(text=f"Biological Age: {age_months} months\nValid age", fg="green")
        return True

    def any_video_loaded(self) -> bool:
        return any(v["loaded"] for v in self.pose_videos.values())

    def update_generate_state(self):
        age_ok = self.is_age_valid()
        any_video_ok = self.any_video_loaded()
        enabled = (not self.processing) and age_ok and any_video_ok

        if enabled:
            self.generate_button.config(state=tk.NORMAL, bg="#28a745", fg="white", cursor="hand2")
        else:
            self.generate_button.config(state=tk.DISABLED, bg="lightgray", fg="gray", cursor="arrow")

    def open_video(self, pose: str):
        file_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if file_path:
            self._set_pose_video(pose, file_path)

    def on_drop(self, event, pose: str):
        path = parse_drop_path(event.data)
        if Path(path).exists():
            self._set_pose_video(pose, path)

    def _set_pose_video(self, pose: str, path: str):
        self.pose_videos[pose]["path"] = path
        self.pose_videos[pose]["loaded"] = True

        lbl = self.pose_videos[pose].get("success_lbl")
        if lbl:
            lbl.config(text="Video loaded ✅")
            lbl.grid()

        self.status_label.config(text=f"{pose} video set: {Path(path).name}")
        self.update_generate_state()

    def on_generate_clicked(self):
        if self.processing:
            return

        pose = self.selected_pose.get()
        video_path = self.pose_videos.get(pose, {}).get("path")

        if not video_path:
            messagebox.showerror("Error", f"No video loaded for {pose}.")
            return

        birthdate = self.get_birthdate()
        if birthdate is None:
            messagebox.showerror("Error", "Invalid birthdate.")
            return

        self.processing = True
        self.status_label.config(text="Processing... (this may take a while)")
        self.update_generate_state()
        self.root.after(0, self.show_preview_window)
        thread = threading.Thread(
            target=self._run_pipeline_thread,
            args=(pose, video_path, birthdate),
            daemon=True,
        )
        thread.start()

    def _run_pipeline_thread(self, pose: str, video_path: str, birthdate: dt.date):
        try:
            # unique output folder per run
            stamp = dt.datetime.now().strftime("%d-%m-%y_%H-%M")
            exam_out_dir = Path(config.VIDEOS_OUTPUT_DIR) / f"Exam_{stamp}_gui"
            video_name = Path(video_path).stem
            out_dir = exam_out_dir / f"{pose.lower()}_{video_name}_{stamp}_gui"

            self.root.after(0, self.show_preview_window)

            result = run_pipeline(
                pose=pose,
                video_path=video_path,
                birthdate=birthdate,
                out_dir=out_dir,
                frame_callback=lambda frame: self.root.after(0, lambda f=frame: self.update_preview_frame(f))
            )

            msg = (
                f"Done ✅\n\n"
                f"Pose: {result['pose']}\n"
                f"Age (months): {result['age_months']}\n"
                f"AIMS score: {result['aims_score']}\n\n"
                f"Outputs folder:\n{out_dir}"
            )
            self.root.after(0, lambda: messagebox.showinfo("Success", msg))
            self.root.after(0, lambda: self.status_label.config(text=f"Finished. Outputs: {out_dir}"))

        except Exception as e:
            tb = traceback.format_exc()
            self.root.after(0, lambda: messagebox.showerror("Error", tb))
            self.root.after(0, lambda: self.status_label.config(text="Error. See message box."))

        finally:
            self.processing = False
            self.root.after(0, self.update_generate_state)


def main():
    root = TkinterDnD.Tk()
    app = InfantAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
