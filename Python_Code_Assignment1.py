"""Student Grouping Application

Run this script with: python test3.py

This application:
- Generates 120-160 random students (Elev-1..Elev-N)
- Creates 8 classes (Fag-1..Fag-8)
- Assigns each student 3-4 random classes
- Groups students into groups of 4-6 based on maximizing shared classes
- Visualizes groups and statistics in a Tkinter GUI with matplotlib.

Dependencies:
- numpy
- matplotlib
- networkx (optional, but recommended)

If a dependency is missing the app will show an error dialog.
"""

import math
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Core data generation functions

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit("Missing dependency: numpy. Install with `pip install numpy`.") from exc

try:
    import matplotlib
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError as exc:
    raise SystemExit("Missing dependency: matplotlib. Install with `pip install matplotlib`.") from exc

try:
    import networkx as nx
except ImportError:
    nx = None  # network graph will fall back to a basic matplotlib drawing

# -- Utility functions ----------------------------------------------------------------

def make_students(num_students: int):
    """Generate student labels Elev-1..Elev-N."""
    return [f"Elev-{i + 1}" for i in range(num_students)]


def make_classes(num_classes: int):
    """Generate class labels Fag-1..Fag-N."""
    return [f"Fag-{i + 1}" for i in range(num_classes)]


def random_enrollment_matrix(num_classes: int, num_students: int, min_classes: int = 3, max_classes: int = 4, seed: int | None = None):
    """Return an (classes x students) boolean matrix of enrollments."""
    rng = np.random.default_rng(seed)
    matrix = np.zeros((num_classes, num_students), dtype=np.int8)
    for student in range(num_students):
        count = rng.integers(min_classes, max_classes + 1)
        chosen = rng.choice(num_classes, size=count, replace=False)
        matrix[chosen, student] = 1
    return matrix


def class_enrollment_counts(enrollment_matrix: np.ndarray):
    """Calculate how many students attend each class."""
    return np.sum(enrollment_matrix, axis=1)


def class_pair_coenrollment(enrollment_matrix: np.ndarray):
    """Compute co-enrollment counts for each pair of classes."""
    # (classes x students) matrix
    # coenrollment[i,j] = number of students taking both class i and class j
    return enrollment_matrix @ enrollment_matrix.T


def student_shared_classes(enrollment_matrix: np.ndarray):
    """Compute a student x student similarity matrix (shared class count)."""
    # students are columns
    return enrollment_matrix.T @ enrollment_matrix


def group_shared_stats(group_indices: list[int], student_similarity: np.ndarray):
    """Compute stats for a group (min/mean shared classes between members)."""
    if len(group_indices) < 2:
        return 0, 0
    sub = student_similarity[np.ix_(group_indices, group_indices)]
    # ignore diagonal
    offdiag = sub[~np.eye(len(group_indices), dtype=bool)]
    min_shared = int(np.min(offdiag))
    mean_shared = float(np.mean(offdiag))
    return min_shared, mean_shared


def form_groups(enrollment_matrix: np.ndarray, min_group: int = 4, max_group: int = 6):
    """Form groups of students (indices) based on shared class similarity.

    Algorithm:
    - Compute student similarity via dot product.
    - Greedily build groups starting from a random ungrouped student.
    - Add students while maintaining or improving minimum shared classes.
    - Stop when adding anyone would reduce the group's minimum shared count.
    """

    num_students = enrollment_matrix.shape[1]
    similarity = student_shared_classes(enrollment_matrix)
    ungrouped = set(range(num_students))
    groups: list[list[int]] = []

    # Work until we have fewer than min_group ungrouped left.
    while len(ungrouped) >= min_group:
        seed = random.choice(list(ungrouped))
        group = [seed]
        ungrouped.remove(seed)

        # Build group greedily
        while len(group) < max_group and ungrouped:
            current_min, _ = group_shared_stats(group, similarity)
            best_candidate = None
            best_new_min = -1

            for cand in ungrouped:
                # Compute minimum shared classes if candidate is added
                shared_with_group = [similarity[cand, member] for member in group]
                new_min = min(current_min, min(shared_with_group)) if group and current_min != 0 else min(shared_with_group)
                if new_min > best_new_min:
                    best_new_min = new_min
                    best_candidate = cand

            # If adding reduces the minimum shared count and group is already stable, stop
            if best_candidate is None:
                break
            if len(group) >= min_group and best_new_min < current_min:
                break

            group.append(best_candidate)
            ungrouped.remove(best_candidate)

        groups.append(group)

    # If any students remain, distribute them to best-fit existing groups.
    if ungrouped:
        for leftover in list(ungrouped):
            best_group = None
            best_score = -1
            for g in groups:
                if len(g) >= max_group:
                    continue
                # Score by sum of shared classes to group members
                score = sum(similarity[leftover, member] for member in g)
                if score > best_score:
                    best_score = score
                    best_group = g
            if best_group is None:
                # Just put them in the smallest group
                best_group = min(groups, key=len)
            best_group.append(leftover)
            ungrouped.remove(leftover)

    return groups

# -- GUI helpers -----------------------------------------------------------------------

class Theme:
    BLUE = "#2f6fed"
    ORANGE = "#f7b731"
    BG = "#ffffff"
    FG = "#1f1f1f"


def safe_font(root: tk.Tk, size=11, weight="normal"):
    for f in ["Segoe UI", "Helvetica", "Arial"]:
        try:
            return (f, size, weight)
        except Exception:
            continue
    return (None, size, weight)


class GroupingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Student Grouping - Fagfordeling")
        self.geometry("1000x640")
        self.minsize(900, 580)
        self.configure(bg=Theme.BG)

        # Data
        self.students = make_students(random.randint(120, 160))
        self.classes = make_classes(8)
        self.enrollment = random_enrollment_matrix(len(self.classes), len(self.students))
        self.groups = form_groups(self.enrollment)
        self.student_similarity = student_shared_classes(self.enrollment)

        # Derived data
        self.class_counts = class_enrollment_counts(self.enrollment)
        self.pair_co = class_pair_coenrollment(self.enrollment)

        # State
        self.selected_group_index = 0
        self.matrix_step = 0
        self.animating = False
        self.animation_thread = None

        self._build_ui()
        self._refresh_group_list()
        self._update_group_details()
        self._draw_all_tabs()

        self.bind('<Configure>', self._on_resize)

    # --------------- UI Construction ----------------------------------------------

    def _build_ui(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        # Left panel
        self.group_listbox = tk.Listbox(left, activestyle='dotbox', font=safe_font(self, 11), highlightthickness=0)
        self.group_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        self.group_listbox.bind('<<ListboxSelect>>', lambda e: self._on_group_selected())

        self.group_details = tk.Text(left, height=12, wrap=tk.WORD, font=safe_font(self, 10), bg=Theme.BG, bd=1, relief=tk.SOLID)
        self.group_details.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.group_details.configure(state='disabled')

        # Right panel - tabs
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_fagfordeling = ttk.Frame(self.notebook)
        self.tab_nettverk = ttk.Frame(self.notebook)
        self.tab_tidslinje = ttk.Frame(self.notebook)
        self.tab_matrisen = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_fagfordeling, text="Fagfordeling")
        self.notebook.add(self.tab_nettverk, text="Nettverk")
        self.notebook.add(self.tab_tidslinje, text="Tidslinje")
        self.notebook.add(self.tab_matrisen, text="Matrisen")

        # Matplotlib Figures
        self._build_bar_chart()
        self._build_network_chart()
        self._build_timeline_chart()
        self._build_matrix_chart()

    # --------------- Group list + details -----------------------------------------

    def _refresh_group_list(self):
        self.group_listbox.delete(0, tk.END)
        for idx, group in enumerate(self.groups, start=1):
            min_shared, mean_shared = group_shared_stats(group, self.student_similarity)
            self.group_listbox.insert(tk.END, f"Gruppe {idx}: {len(group)} elever  |  min delte fag: {min_shared}")
        self.group_listbox.select_set(0)
        self.selected_group_index = 0

    def _on_group_selected(self):
        selection = self.group_listbox.curselection()
        if not selection:
            return
        self.selected_group_index = selection[0]
        self._update_group_details()
        self._highlight_matrix_step(self.selected_group_index)

    def _update_group_details(self):
        group = self.groups[self.selected_group_index]
        min_shared, mean_shared = group_shared_stats(group, self.student_similarity)
        details = [f"Gruppe {self.selected_group_index + 1}: {len(group)} elever"]
        details.append(f"Min delte fag: {min_shared}")
        details.append(f"Gjennomsnitt delte fag: {mean_shared:.1f}")

        details.append("\nElever:")
        for sid in group:
            classes_for_student = [self.classes[cidx] for cidx in np.where(self.enrollment[:, sid] == 1)[0]]
            details.append(f" - {self.students[sid]}: {', '.join(classes_for_student)}")

        self.group_details.configure(state='normal')
        self.group_details.delete('1.0', tk.END)
        self.group_details.insert('1.0', '\n'.join(details))
        self.group_details.configure(state='disabled')

    # --------------- Plot helpers --------------------------------------------------

    def _build_bar_chart(self):
        fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.bar_ax = fig.add_subplot(111)
        self.bar_canvas = FigureCanvasTkAgg(fig, master=self.tab_fagfordeling)
        self.bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_network_chart(self):
        fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.net_ax = fig.add_subplot(111)
        self.net_canvas = FigureCanvasTkAgg(fig, master=self.tab_nettverk)
        self.net_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_timeline_chart(self):
        fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.timeline_ax = fig.add_subplot(111)
        self.timeline_canvas = FigureCanvasTkAgg(fig, master=self.tab_tidslinje)
        self.timeline_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_matrix_chart(self):
        container = ttk.Frame(self.tab_matrisen)
        container.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(container)
        control_frame.pack(fill=tk.X, padx=8, pady=8)

        self.prev_btn = ttk.Button(control_frame, text="⏮ Forrige", command=self._matrix_prev)
        self.prev_btn.pack(side=tk.LEFT, padx=4)
        self.play_btn = ttk.Button(control_frame, text="▶ Spill", command=self._matrix_play_pause)
        self.play_btn.pack(side=tk.LEFT, padx=4)
        self.next_btn = ttk.Button(control_frame, text="⏭ Neste", command=self._matrix_next)
        self.next_btn.pack(side=tk.LEFT, padx=4)

        self.matrix_status = ttk.Label(control_frame, text="Steg 1")
        self.matrix_status.pack(side=tk.RIGHT, padx=4)

        fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.matrix_ax = fig.add_subplot(111)
        self.matrix_canvas = FigureCanvasTkAgg(fig, master=container)
        self.matrix_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _draw_all_tabs(self):
        self._draw_bar_chart()
        self._draw_network_chart()
        self._draw_timeline_chart()
        self._highlight_matrix_step(0)

    def _draw_bar_chart(self):
        self.bar_ax.clear()
        x = range(len(self.classes))
        self.bar_ax.bar(x, self.class_counts, color=Theme.BLUE)
        self.bar_ax.set_xticks(x)
        self.bar_ax.set_xticklabels(self.classes, rotation=30, ha='right')
        self.bar_ax.set_ylabel('Antall elever')
        self.bar_ax.set_title('Fagfordeling')
        self.bar_canvas.draw_idle()

    def _draw_network_chart(self):
        self.net_ax.clear()
        self.net_ax.set_title('Nettverk (felles fag)')
        self.net_ax.axis('off')

        # Build graph
        if nx is not None:
            G = nx.Graph()
            for i, name in enumerate(self.classes):
                G.add_node(i, label=name)
            max_weight = 0
            for i in range(len(self.classes)):
                for j in range(i + 1, len(self.classes)):
                    weight = int(self.pair_co[i, j])
                    if weight > 0:
                        G.add_edge(i, j, weight=weight)
                        max_weight = max(max_weight, weight)

            pos = nx.circular_layout(G)
            node_colors = [Theme.BLUE] * len(G.nodes)
            nx.draw_networkx_nodes(G, pos, node_color=node_colors, ax=self.net_ax, node_size=600)
            labels = {n: self.classes[n] for n in G.nodes}
            nx.draw_networkx_labels(G, pos, labels=labels, ax=self.net_ax, font_size=9)

            # edges with width based on weight
            weights = [G[u][v]["weight"] for u, v in G.edges()]
            if weights:
                normalized = [1 + 4 * (w / max_weight) for w in weights]
                nx.draw_networkx_edges(G, pos, ax=self.net_ax, width=normalized, edge_color=Theme.ORANGE)
        else:
            # Fallback: draw simple nodes and lines in a circle
            n = len(self.classes)
            angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
            coords = {i: (math.cos(a), math.sin(a)) for i, a in enumerate(angles)}
            for i in range(n):
                x1, y1 = coords[i]
                self.net_ax.text(x1, y1, self.classes[i], ha='center', va='center', fontsize=9,
                                 bbox=dict(boxstyle='round', facecolor=Theme.BLUE, alpha=0.8, edgecolor='none'))
            maxw = float(np.max(self.pair_co))
            if maxw == 0:
                maxw = 1
            for i in range(n):
                for j in range(i + 1, n):
                    w = self.pair_co[i, j]
                    if w == 0:
                        continue
                    x1, y1 = coords[i]
                    x2, y2 = coords[j]
                    self.net_ax.plot([x1, x2], [y1, y2], color=Theme.ORANGE, linewidth=1 + 3 * (w / maxw), alpha=0.7)

        self.net_canvas.draw_idle()

    def _draw_timeline_chart(self):
        self.timeline_ax.clear()
        sizes = [len(g) for g in self.groups]
        mins = []
        means = []
        for g in self.groups:
            m, avg = group_shared_stats(g, self.student_similarity)
            mins.append(m)
            means.append(avg)

        x = list(range(1, len(self.groups) + 1))
        self.timeline_ax.bar(x, sizes, color=Theme.BLUE, alpha=0.7)
        self.timeline_ax.scatter(x, sizes, c=Theme.ORANGE, s=[(m + 1) * 12 for m in mins], alpha=0.8)
        self.timeline_ax.set_xlabel('Gruppe')
        self.timeline_ax.set_ylabel('Antall elever')
        self.timeline_ax.set_title('Tidslinje (gruppe størrelse + delte fag)')
        self.timeline_ax.set_xticks(x)
        self.timeline_canvas.draw_idle()

    def _highlight_matrix_step(self, step: int):
        self.matrix_step = max(0, min(step, len(self.groups) - 1))
        self.matrix_status.configure(text=f"Steg {self.matrix_step + 1} av {len(self.groups)}")

        # Draw the matrix
        self.matrix_ax.clear()
        base = self.enrollment.astype(float)
        cmap = matplotlib.cm.get_cmap('Blues')
        self.matrix_ax.imshow(base, aspect='auto', cmap=cmap)

        group = self.groups[self.matrix_step]
        # highlight students in the current group by a border around their columns
        for student_idx in group:
            self.matrix_ax.add_patch(
                matplotlib.patches.Rectangle((student_idx - 0.5, -0.5), 1, len(self.classes),
                                             fill=False, edgecolor=Theme.ORANGE, linewidth=2)
            )

        self.matrix_ax.set_yticks(range(len(self.classes)))
        self.matrix_ax.set_yticklabels(self.classes)
        self.matrix_ax.set_xlabel('Student')
        self.matrix_ax.set_title('Student-klasse matrise (gruppemarkering)')

        # Legend
        self.matrix_ax.text(0.02, 0.98, 'Blå: påmelding\nOransje: valgt gruppe', transform=self.matrix_ax.transAxes,
                            ha='left', va='top', fontsize=9, bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))

        self.matrix_canvas.draw_idle()

    # --------------- Matrix animation controls ------------------------------------

    def _matrix_prev(self):
        self._stop_animation()
        self._highlight_matrix_step(self.matrix_step - 1)
        self.group_listbox.select_clear(0, tk.END)
        self.group_listbox.select_set(self.matrix_step)
        self.group_listbox.see(self.matrix_step)
        self._update_group_details()

    def _matrix_next(self):
        self._stop_animation()
        self._highlight_matrix_step(self.matrix_step + 1)
        self.group_listbox.select_clear(0, tk.END)
        self.group_listbox.select_set(self.matrix_step)
        self.group_listbox.see(self.matrix_step)
        self._update_group_details()

    def _matrix_play_pause(self):
        if self.animating:
            self._stop_animation()
            return
        self.animating = True
        self.play_btn.configure(text="⏸ Pause")
        self.animation_thread = threading.Thread(target=self._run_animation, daemon=True)
        self.animation_thread.start()

    def _stop_animation(self):
        if self.animating:
            self.animating = False
            self.play_btn.configure(text="▶ Spill")
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join(timeout=0.1)

    def _run_animation(self):
        while self.animating:
            next_step = (self.matrix_step + 1) % len(self.groups)
            self.after(0, lambda s=next_step: self._highlight_matrix_step(s))
            self.after(0, lambda s=next_step: self.group_listbox.select_clear(0, tk.END))
            self.after(0, lambda s=next_step: self.group_listbox.select_set(s))
            self.after(0, lambda s=next_step: self.group_listbox.see(s))
            self.after(0, lambda: self._update_group_details())
            time.sleep(1.2)
            if not self.animating:
                break

    # --------------- Resize handling ------------------------------------------------

    def _on_resize(self, event):
        # Redraw charts so they resize properly
        self._draw_bar_chart()
        self._draw_network_chart()
        self._draw_timeline_chart()
        self._highlight_matrix_step(self.matrix_step)


if __name__ == "__main__":
    app = GroupingApp()
    app.mainloop()
