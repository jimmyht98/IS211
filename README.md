# Groupr - Student Grouping Application (Prototype)

A Python desktop application that randomly generates students and classes, assigns enrollments, and intelligently groups students together based on how many classes they share. Results are visualized through an interactive Tkinter GUI with embedded Matplotlib charts.

---

## Features

- Randomly generates **120–160 students** (labeled `Elev-1` to `Elev-N`)
- Creates **8 classes** (labeled `Fag-1` to `Fag-8`)
- Assigns each student **3–4 random classes**
- Groups students into **groups of 4–6** using a greedy similarity algorithm that maximizes shared classes
- Visualizes everything in a **multi-tab GUI** with:
  - **Fagfordeling** – Bar chart showing how many students are enrolled in each class
  - **Nettverk** – Network graph showing co-enrollment relationships between classes
  - **Tidslinje** – Timeline chart showing group sizes and shared class statistics
  - **Matrisen** – Animated enrollment matrix with group highlighting

---

## Screenshots

> *(Add screenshots of your application here)*

---

## Requirements

- Python 3.10 or higher (uses the `int | None` union type syntax)
- [numpy](https://numpy.org/)
- [matplotlib](https://matplotlib.org/)
- [networkx](https://networkx.org/) *(optional but recommended — falls back to a basic matplotlib drawing if not installed)*

Tkinter is included with most standard Python installations. If it's missing, install it via your system package manager (e.g. `sudo apt install python3-tk` on Ubuntu/Debian).

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Install dependencies**

   ```bash
   pip install numpy matplotlib networkx
   ```

---

## Usage

Run the script directly with Python:

```bash
python Python_Code_Assignment1.py
```

The GUI will launch automatically with a freshly generated dataset on every run.

---

## How It Works

### Data Generation

- `make_students(n)` — generates student labels
- `make_classes(n)` — generates class labels
- `random_enrollment_matrix(...)` — builds a boolean `(classes × students)` NumPy matrix where each student is randomly enrolled in 3–4 classes

### Grouping Algorithm

The `form_groups()` function uses a **greedy similarity approach**:

1. Computes a `(students × students)` similarity matrix via dot product, where each value represents the number of shared classes between two students.
2. Starts a new group from a random ungrouped student.
3. Iteratively adds the candidate who best preserves (or improves) the group's **minimum shared-class count**.
4. Stops adding when the group is stable (adding anyone would reduce the minimum) or the maximum group size is reached.
5. Any remaining students are distributed to their best-fitting existing group based on total shared-class score.

### Visualization Tabs

| Tab | Description |
|---|---|
| **Fagfordeling** | Bar chart of student counts per class |
| **Nettverk** | Circular network graph; edge thickness = co-enrollment count between class pairs |
| **Tidslinje** | Bar chart of group sizes; dot size indicates minimum shared classes within the group |
| **Matrisen** | Heatmap of the enrollment matrix; highlights the selected group's columns in orange. Supports animated step-through via Play/Pause controls |

---

## Project Structure

```
Python_Code_Assignment1.py   # Main application — all logic and GUI in one file
README.md
```

---

## Known Limitations

- Data is randomly regenerated on every launch; there is no save/load functionality.
- The grouping algorithm is greedy and non-deterministic; results may vary between runs.
- Very large student counts may slow down the matrix animation.

---

## License

This project was created as an assignment. Feel free to use or adapt it for educational purposes.
