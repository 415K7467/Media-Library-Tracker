"""Tkinter GUI for the Media Library Tracker."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from media_item import Category, MediaItem, Status
from media_library import MediaLibrary, MediaLibraryError, SEARCHABLE_FIELDS

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

COLUMNS = ("title", "category", "status", "rating", "watched", "notes")
COLUMN_LABELS = {
    "title": "Title",
    "category": "Category",
    "status": "Status",
    "rating": "Rating",
    "watched": "Watched/Read",
    "notes": "Notes",
}


class MediaItemDialog(tk.Toplevel):
    """Modal dialog used to create or edit a MediaItem."""

    def __init__(self, parent: tk.Widget, item: Optional[MediaItem] = None) -> None:
        super().__init__(parent)
        self.title("Edit Item" if item else "Add Item")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[dict] = None
        self._image_path = tk.StringVar(value=item.image_path if item else "")
        self._preview_image = None

        self._build_form(item)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_form(self, item: Optional[MediaItem]) -> None:
        padding = {"padx": 8, "pady": 4}

        tk.Label(self, text="Title *").grid(row=0, column=0, sticky="w", **padding)
        self.title_var = tk.StringVar(value=item.title if item else "")
        tk.Entry(self, textvariable=self.title_var, width=32).grid(row=0, column=1, **padding)

        tk.Label(self, text="Category *").grid(row=1, column=0, sticky="w", **padding)
        self.category_var = tk.StringVar(value=item.category.value if item else Category.OTHER.value)
        ttk.Combobox(
            self, textvariable=self.category_var, values=Category.values(), state="readonly", width=29
        ).grid(row=1, column=1, **padding)

        tk.Label(self, text="Status *").grid(row=2, column=0, sticky="w", **padding)
        self.status_var = tk.StringVar(value=item.status.value if item else Status.PLANNED.value)
        ttk.Combobox(
            self, textvariable=self.status_var, values=Status.values(), state="readonly", width=29
        ).grid(row=2, column=1, **padding)

        tk.Label(self, text="Rating (0-5)").grid(row=3, column=0, sticky="w", **padding)
        self.rating_var = tk.StringVar(value=str(item.rating) if item and item.rating is not None else "")
        tk.Spinbox(self, from_=0, to=5, textvariable=self.rating_var, width=5).grid(
            row=3, column=1, sticky="w", **padding
        )

        self.watched_var = tk.BooleanVar(value=item.watched if item else False)
        tk.Checkbutton(self, text="Watched / Read", variable=self.watched_var).grid(
            row=4, column=1, sticky="w", **padding
        )

        tk.Label(self, text="Notes").grid(row=5, column=0, sticky="nw", **padding)
        self.notes_text = tk.Text(self, width=32, height=5)
        if item:
            self.notes_text.insert("1.0", item.notes)
        self.notes_text.grid(row=5, column=1, **padding)

        tk.Label(self, text="Cover image").grid(row=6, column=0, sticky="w", **padding)
        image_frame = tk.Frame(self)
        image_frame.grid(row=6, column=1, sticky="w", **padding)
        tk.Entry(image_frame, textvariable=self._image_path, width=24, state="readonly").pack(side="left")
        tk.Button(image_frame, text="Browse...", command=self._browse_image).pack(side="left", padx=4)

        button_frame = tk.Frame(self)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        tk.Button(button_frame, text="Save", width=10, command=self._on_save).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", width=10, command=self._on_cancel).pack(side="left", padx=5)

    def _browse_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select cover image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")],
        )
        if path:
            self._image_path.set(path)

    def _on_save(self) -> None:
        try:
            rating_raw = self.rating_var.get().strip()
            rating = int(rating_raw) if rating_raw else None
            self.result = {
                "title": self.title_var.get(),
                "category": self.category_var.get(),
                "status": self.status_var.get(),
                "rating": rating,
                "notes": self.notes_text.get("1.0", "end").strip(),
                "watched": self.watched_var.get(),
                "image_path": self._image_path.get(),
            }
            # Validate through a throwaway MediaItem before accepting.
            MediaItem.from_dict({**self.result, "item_id": None})
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            self.result = None
            return
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


class MediaLibraryApp(tk.Tk):
    """Main application window."""

    def __init__(self, library: MediaLibrary) -> None:
        super().__init__()
        self.library = library
        self.title("Media Library Tracker")
        self.geometry("980x560")
        self.minsize(760, 440)

        self._sort_field = "title"
        self._sort_reverse = False
        self._current_items: list[MediaItem] = []
        self._preview_image = None

        self._build_layout()
        self._reload()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._reload())
        tk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side="left", padx=4)

        tk.Label(search_frame, text="Field:").pack(side="left", padx=(12, 0))
        self.search_field_var = tk.StringVar(value="All")
        ttk.Combobox(
            search_frame,
            textvariable=self.search_field_var,
            values=["All", *SEARCHABLE_FIELDS],
            state="readonly",
            width=10,
        ).pack(side="left", padx=4)
        self.search_field_var.trace_add("write", lambda *_: self._reload())

        button_bar = tk.Frame(self)
        button_bar.pack(fill="x", padx=8, pady=(2, 6))
        tk.Button(button_bar, text="Add", width=10, command=self._on_add).pack(side="left", padx=2)
        tk.Button(button_bar, text="Edit", width=10, command=self._on_edit).pack(side="left", padx=2)
        tk.Button(button_bar, text="Delete", width=10, command=self._on_delete).pack(side="left", padx=2)
        tk.Button(button_bar, text="Toggle Watched", width=14, command=self._on_toggle_watched).pack(
            side="left", padx=2
        )
        tk.Button(button_bar, text="Export CSV", width=10, command=self._on_export_csv).pack(side="left", padx=2)
        tk.Button(button_bar, text="Statistics", width=10, command=self._on_show_statistics).pack(
            side="left", padx=2
        )

        body_frame = tk.Frame(self)
        body_frame.pack(fill="both", expand=True, padx=8, pady=4)

        tree_frame = tk.Frame(body_frame)
        tree_frame.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=COLUMNS, show="headings", selectmode="browse")
        for column in COLUMNS:
            self.tree.heading(column, text=COLUMN_LABELS[column], command=lambda c=column: self._on_sort(c))
            width = 260 if column == "notes" else 100
            self.tree.column(column, width=width, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._update_preview())
        self.tree.bind("<Double-1>", lambda _e: self._on_edit())

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        preview_frame = tk.Frame(body_frame, width=180)
        preview_frame.pack(side="right", fill="y", padx=(8, 0))
        preview_frame.pack_propagate(False)
        tk.Label(preview_frame, text="Cover preview").pack()
        self.preview_label = tk.Label(preview_frame, text="(no image)", relief="groove", width=20, height=12)
        self.preview_label.pack(pady=6)

        status_frame = tk.Frame(self)
        status_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(status_frame, textvariable=self.status_var, anchor="w").pack(fill="x")

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------
    def _reload(self) -> None:
        query = self.search_var.get()
        field = self.search_field_var.get()
        field = None if field in ("", "All") else field

        try:
            items = self.library.search(query, field)
            items = self.library.sort(items, self._sort_field, self._sort_reverse)
        except MediaLibraryError as exc:
            messagebox.showerror("Error", str(exc))
            items = self.library.items

        self._current_items = items
        self.tree.delete(*self.tree.get_children())
        for item in items:
            self.tree.insert(
                "",
                "end",
                iid=str(item.item_id),
                values=(
                    item.title,
                    item.category.value,
                    item.status.value,
                    item.rating if item.rating is not None else "",
                    "Yes" if item.watched else "No",
                    item.notes.replace("\n", " ")[:80],
                ),
            )
        self.status_var.set(f"{len(items)} item(s) shown / {len(self.library.items)} total.")
        self._update_preview()

    def _get_selected_item(self) -> Optional[MediaItem]:
        selection = self.tree.selection()
        if not selection:
            return None
        item_id = int(selection[0])
        try:
            return self.library.get_item(item_id)
        except MediaLibraryError:
            return None

    def _update_preview(self) -> None:
        item = self._get_selected_item()
        self._preview_image = None
        if not item or not item.image_path or not os.path.exists(item.image_path):
            self.preview_label.configure(image="", text="(no image)")
            return

        if not PIL_AVAILABLE:
            self.preview_label.configure(image="", text="(preview needs Pillow)")
            return

        try:
            image = Image.open(item.image_path)
            image.thumbnail((160, 200))
            self._preview_image = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self._preview_image, text="")
        except Exception:
            self.preview_label.configure(image="", text="(could not load image)")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_add(self) -> None:
        dialog = MediaItemDialog(self)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            item = MediaItem.from_dict({**dialog.result, "item_id": None})
            self.library.add_item(item)
        except (ValueError, MediaLibraryError) as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._reload()

    def _on_edit(self) -> None:
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("No selection", "Select an item to edit first.")
            return

        dialog = MediaItemDialog(self, item)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.library.update_item(item.item_id, **dialog.result)
        except (ValueError, MediaLibraryError) as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._reload()

    def _on_delete(self) -> None:
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("No selection", "Select an item to delete first.")
            return
        if not messagebox.askyesno("Confirm delete", f"Delete '{item.title}'?"):
            return
        try:
            self.library.delete_item(item.item_id)
        except MediaLibraryError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._reload()

    def _on_toggle_watched(self) -> None:
        item = self._get_selected_item()
        if not item:
            messagebox.showinfo("No selection", "Select an item to toggle first.")
            return
        try:
            self.library.toggle_watched(item.item_id)
        except MediaLibraryError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._reload()

    def _on_export_csv(self) -> None:
        if not self._current_items:
            messagebox.showinfo("Nothing to export", "There are no items in the current view.")
            return
        path = filedialog.asksaveasfilename(
            title="Export filtered list to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        try:
            self.library.export_csv(path, self._current_items)
        except MediaLibraryError as exc:
            messagebox.showerror("Error", str(exc))
            return
        messagebox.showinfo("Export complete", f"Exported {len(self._current_items)} item(s) to {path}.")

    def _on_show_statistics(self) -> None:
        stats = self.library.statistics()
        window = tk.Toplevel(self)
        window.title("Statistics")
        window.resizable(False, False)
        window.transient(self)

        tk.Label(window, text=f"Total items: {stats['total']}", font=("", 10, "bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        tk.Label(window, text=f"Watched / Read: {stats['watched']}").pack(anchor="w", padx=10)
        tk.Label(window, text=f"Unwatched / Unread: {stats['unwatched']}").pack(anchor="w", padx=10, pady=(0, 8))

        tk.Label(window, text="By category:", font=("", 10, "bold")).pack(anchor="w", padx=10)
        if stats["by_category"]:
            for category, count in sorted(stats["by_category"].items()):
                tk.Label(window, text=f"  {category}: {count}").pack(anchor="w", padx=10)
        else:
            tk.Label(window, text="  (no items yet)").pack(anchor="w", padx=10)

        tk.Button(window, text="Close", command=window.destroy).pack(pady=10)

    def _on_sort(self, field: str) -> None:
        if self._sort_field == field:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_field = field
            self._sort_reverse = False
        self._reload()
