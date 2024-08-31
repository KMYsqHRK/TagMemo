import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import json
from datetime import datetime
import base64
import io
from PIL import Image, ImageTk, ImageGrab
import pyclipper

ctk.set_appearance_mode("System")  # モードをシステム設定に合わせる
ctk.set_default_color_theme("blue")  # テーマカラーを設定


class MemoApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Tag_Memo")
        self.master.geometry("1020x600")

        self.memos = []
        self.tags = set()
        self.load_data()

        self.current_image_data = None
        self.current_memo_id = None
        self.last_clipboard_content = ""

        self.create_widgets()
        self.master.after(100, self.check_clipboard)

    def create_widgets(self):
        self.main_frame = ttk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 左側のフレーム（メモ一覧）
        self.left_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.left_frame)

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(self.left_frame, textvariable=self.search_var)
        self.search_entry.pack(padx=5, pady=5, fill=tk.X)
        self.search_var.trace("w", self.search_memos)

        self.memo_list = ttk.Treeview(
            self.left_frame, columns=("title", "tags"), show="headings"
        )
        self.memo_list.column("title", width=130)
        self.memo_list.column("tags", width=130)
        self.memo_list.heading("title", text="タイトル")
        self.memo_list.heading("tags", text="タグ")
        self.memo_list.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.memo_list.bind("<<TreeviewSelect>>", self.on_memo_select)

        # 右側のフレーム（メモ編集）
        self.right_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.right_frame)

        self.title_label = ttk.Label(
            self.right_frame, text="Title:", font=("Arial", 16)
        )
        self.title_label.pack(padx=5, pady=5, anchor=tk.W)
        self.title_entry = ctk.CTkEntry(self.right_frame, font=("Arial", 16))
        self.title_entry.pack(padx=5, pady=5, fill=tk.X)

        self.tags_label = ttk.Label(self.right_frame, text="Tags:", font=("Arial", 12))
        self.tags_label.pack(padx=5, pady=5, anchor=tk.W)
        self.tags_frame = ttk.Frame(self.right_frame)
        self.tags_frame.pack(padx=5, pady=5, fill=tk.X)
        self.update_tag_checkboxes()

        self.manage_tags_button = ctk.CTkButton(
            self.right_frame,
            width=30,
            height=30,
            text="tag manager",
            command=self.manage_tags,
        )
        self.manage_tags_button.pack(padx=5, pady=5, anchor=tk.W)

        self.text_area = ctk.CTkTextbox(
            self.right_frame,
            border_width=2,
            height=10,
            width=50,
            font=("Arial", 16),
        )
        self.text_area.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.bind("<Control-v>", self.paste_image)
        self.text_area.bind("<Control-x>", self.clear_image)
        self.text_area.bind("<Control-s>", self.save_memo)

        self.image_label = ttk.Label(self.right_frame)
        self.image_label.pack(padx=5, pady=5)

        self.button_frame = ttk.Frame(self.right_frame)
        self.button_frame.pack(padx=5, pady=5, fill=tk.X)

        self.add_image_button = ctk.CTkButton(
            self.button_frame,
            width=30,
            height=30,
            text="add image",
            command=self.add_image,
        )
        self.add_image_button.pack(side=tk.LEFT, padx=5)

        self.paste_button = ctk.CTkButton(
            self.button_frame,
            width=30,
            height=30,
            text="paste image",
            command=self.paste_image,
        )
        self.paste_button.pack(side=tk.LEFT, padx=5)

        self.clear_image_button = ctk.CTkButton(
            self.button_frame,
            width=30,
            height=30,
            text="clear image",
            command=self.clear_image,
        )
        self.clear_image_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ctk.CTkButton(
            self.button_frame,
            width=30,
            height=30,
            fg_color="tomato",
            text="delete memo",
            command=self.delete_memo,
        )
        self.delete_button.pack(side=tk.RIGHT, padx=5)

        self.save_button = ctk.CTkButton(
            self.button_frame,
            width=30,
            height=30,
            fg_color="forestgreen",
            text="save memo",
            command=self.save_memo,
        )
        self.save_button.pack(side=tk.RIGHT, padx=5)

        self.new_button = ctk.CTkButton(
            self.button_frame,
            width=30,
            height=30,
            text="create new memo",
            fg_color="peru",
            command=self.new_memo,
        )
        self.new_button.pack(side=tk.RIGHT, padx=5)

        self.update_memo_list()

    def load_data(self):
        if os.path.exists("memos.json"):
            with open("memos.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.memos = data["memos"]
                self.tags = set(data["tags"])

    def save_data(self):
        data = {"memos": self.memos, "tags": list(self.tags)}
        with open("memos.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_memo_list(self):
        self.memo_list.delete(*self.memo_list.get_children())
        for memo in self.memos:
            self.memo_list.insert(
                "",
                tk.END,
                values=(memo["title"], ", ".join(memo["tags"])),
                iid=memo["id"],
            )

    def update_tag_checkboxes(self):
        for widget in self.tags_frame.winfo_children():
            widget.destroy()

        self.tag_vars = {tag: tk.BooleanVar() for tag in self.tags}
        for tag, var in self.tag_vars.items():
            cb = ctk.CTkCheckBox(
                self.tags_frame,
                border_width=2,
                border_color="grey",
                text=tag,
                variable=var,
                font=("Arial", 12),
            )
            cb.pack(side=tk.LEFT, padx=2)

    def on_memo_select(self, event):
        selected_items = self.memo_list.selection()
        if selected_items:
            memo_id = selected_items[0]
            memo = next((m for m in self.memos if m["id"] == memo_id), None)
            if memo:
                self.current_memo_id = memo_id
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, memo["title"])
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert(tk.END, memo["content"])
                if memo["image_data"]:
                    self.current_image_data = memo["image_data"]
                    self.display_image_from_data(self.current_image_data)
                else:
                    self.current_image_data = None
                    self.image_label.config(image="")

                for tag, var in self.tag_vars.items():
                    var.set(tag in memo["tags"])

    def add_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")]
        )
        if file_path:
            with open(file_path, "rb") as image_file:
                self.current_image_data = base64.b64encode(image_file.read()).decode(
                    "utf-8"
                )
            self.display_image(file_path)

    def clear_image(self, event=None):
        if self.current_image_data:
            if messagebox.askyesno("確認", "現在の画像を消去しますか？"):
                self.current_image_data = None
                self.image_label.config(image="")
        else:
            messagebox.showinfo("情報", "消去する画像がありません。")

    def display_image(self, file_path):
        image = Image.open(file_path)
        image = image.resize((int(200 * image.width / image.height), 200))
        photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=photo)
        self.image_label.image = photo

    def display_image_from_data(self, image_data):
        image_data = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_data))
        image = image.resize((int(200 * image.width / image.height), 200))
        photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=photo)
        self.image_label.image = photo

    def paste_image(self, event=None):
        try:
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                image = image.resize((int(200 * image.width / image.height), 200))
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                self.current_image_data = base64.b64encode(buffer.getvalue()).decode(
                    "utf-8"
                )
                photo = ImageTk.PhotoImage(image)
                self.image_label.config(image=photo)
                self.image_label.image = photo
                messagebox.showinfo("success", "画像がペーストされました。")
        except Exception as e:
            messagebox.showerror("error", f"画像のペーストに失敗しました: {str(e)}")

    def check_clipboard(self):
        try:
            clipboard_content = pyclipper.paste()
            if clipboard_content != self.last_clipboard_content:
                self.last_clipboard_content = clipboard_content
                image = ImageGrab.grabclipboard()
                if isinstance(image, Image.Image):
                    self.paste_button.config(state=tk.NORMAL)
                else:
                    self.paste_button.config(state=tk.DISABLED)
        except:
            pass
        self.master.after(100, self.check_clipboard)

    def save_memo(self, event=None):
        title = self.title_entry.get().strip()
        content = self.text_area.get("1.0", tk.END).strip()
        tags = [tag for tag, var in self.tag_vars.items() if var.get()]

        if not title:
            messagebox.showwarning("warning", "タイトルを入力してください。")
            return

        if self.current_memo_id:
            memo = next(
                (m for m in self.memos if m["id"] == self.current_memo_id), None
            )
            if memo:
                memo["title"] = title
                memo["tags"] = tags
                memo["content"] = content
                memo["image_data"] = self.current_image_data
                memo["updated_at"] = datetime.now().isoformat()
        else:
            new_memo = {
                "id": str(len(self.memos) + 1),
                "title": title,
                "tags": tags,
                "content": content,
                "image_data": self.current_image_data,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self.memos.append(new_memo)

        self.save_data()
        self.update_memo_list()
        messagebox.showinfo("成功", "メモを保存しました。")

    def new_memo(self):
        self.current_memo_id = None
        self.title_entry.delete(0, tk.END)
        self.text_area.delete("1.0", tk.END)
        self.current_image_data = None
        self.image_label.config(image="")
        for var in self.tag_vars.values():
            var.set(False)

    def delete_memo(self):
        if self.current_memo_id:
            if messagebox.askyesno("確認", "このメモを削除しますか？"):
                self.memos = [m for m in self.memos if m["id"] != self.current_memo_id]
                # debug: 消す対象より大きなインデックスを持つメモのインデックス値を1下げる
                for m in self.memos:
                    if int(m["id"]) > int(self.current_memo_id):
                        id_int = int(m["id"])
                        id_int -= 1
                        m["id"] = str(id_int)
                self.save_data()
                self.update_memo_list()
                self.new_memo()
        else:
            messagebox.showwarning("警告", "削除するメモを選択してください。")

    def search_memos(self, *args):
        search_term = self.search_var.get().lower()
        self.memo_list.delete(*self.memo_list.get_children())
        for memo in self.memos:
            if (
                search_term in memo["title"].lower()
                or search_term in memo["content"].lower()
                or any(search_term in tag.lower() for tag in memo["tags"])
            ):
                self.memo_list.insert(
                    "",
                    tk.END,
                    values=(memo["title"], ", ".join(memo["tags"])),
                    iid=memo["id"],
                )

    def manage_tags(self):
        TagManager(self.master, self)

    def update_tags_after_edit(self, old_tag, new_tag):
        # メモ内のタグを更新
        for memo in self.memos:
            if old_tag in memo["tags"]:
                memo["tags"].remove(old_tag)
                memo["tags"].append(new_tag)

        # タグセットを更新
        self.tags.remove(old_tag)
        self.tags.add(new_tag)

        # UI を更新
        self.update_tag_checkboxes()
        self.update_memo_list()
        self.save_data()


class TagManager(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Tag Manager")
        self.geometry("300x400")

        self.create_widgets()

    def create_widgets(self):
        self.tag_listbox = tk.Listbox(self)
        self.tag_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.update_tag_list()

        button_frame = ttk.Frame(self)
        button_frame.pack(padx=10, pady=10, fill=tk.X)

        add_button = ctk.CTkButton(
            button_frame, width=10, text="add new tag", command=self.add_tag
        )
        add_button.pack(side=tk.LEFT, padx=5)

        edit_button = ctk.CTkButton(
            button_frame,
            width=10,
            text="edit tag",
            command=self.edit_tag,
        )
        edit_button.pack(side=tk.LEFT, padx=5)

        delete_button = ctk.CTkButton(
            button_frame,
            width=10,
            fg_color="tomato",
            text="delete tag",
            command=self.delete_tag,
        )
        delete_button.pack(side=tk.LEFT, padx=5)

        close_button = ctk.CTkButton(
            button_frame, width=10, text="×", fg_color="grey", command=self.close
        )
        close_button.pack(side=tk.RIGHT, padx=5)

    def update_tag_list(self):
        self.tag_listbox.delete(0, tk.END)
        for tag in sorted(self.app.tags):
            self.tag_listbox.insert(tk.END, tag)

    def add_tag(self):
        dialog = ctk.CTkInputDialog(title="add new tag", text="Please enter new tag:")
        new_tag = dialog.get_input()
        if new_tag and new_tag not in self.app.tags:
            self.app.tags.add(new_tag)
            self.update_tag_list()
            self.app.update_tag_checkboxes()
            self.app.save_data()

    def delete_tag(self):
        selected = self.tag_listbox.curselection()
        if selected:
            tag = self.tag_listbox.get(selected[0])
            if messagebox.askyesno("Check", f"タグ '{tag}' を削除しますか？"):
                self.app.tags.remove(tag)
                self.update_tag_list()
                self.app.update_tag_checkboxes()
                self.app.save_data()
                for memo in self.app.memos:
                    if tag in memo["tags"]:
                        memo["tags"].remove(tag)
                self.app.save_data()
                self.app.update_memo_list()

    def edit_tag(self):
        selected = self.tag_listbox.curselection()
        if selected:
            old_tag = self.tag_listbox.get(selected[0])
            dialog = ctk.CTkInputDialog(
                title="edit tag", text="Please enter new tag name:"
            )
            new_tag = dialog.get_input()
            if new_tag and new_tag != old_tag:
                if new_tag not in self.app.tags:
                    self.app.update_tags_after_edit(old_tag, new_tag)
                    self.update_tag_list()
                    messagebox.showinfo(
                        "Success", f"Tag '{old_tag}' has been changed to '{new_tag}'."
                    )
                else:
                    messagebox.showwarning(
                        "Warning", f"Tag '{new_tag}' already exists."
                    )
        else:
            messagebox.showwarning("Warning", "Please select a tag to edit.")

    def close(self):
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MemoApp(root)
    root.mainloop()
