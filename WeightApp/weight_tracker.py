
import json
import os
from datetime import datetime
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtCore import Qt, QTime, QDate
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDateEdit,
    QDoubleSpinBox,
    QWidget,
    QLabel,
    QComboBox,
    QGroupBox,
    QGraphicsDropShadowEffect,
    QFormLayout,
    QTimeEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLineEdit,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
    QProgressBar,
    QInputDialog,
    QHeaderView,
    QAbstractItemView
)

DATA_FILE = "weight_data.json"


class EditEntryDialog(QDialog):

    def __init__(self, entry, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Edit Entry")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)

        self.date_edit.setDate(
            QDate.fromString(entry["date"], "yyyy-MM-dd")
        )

        # Weight
        self.weight_edit = QDoubleSpinBox()
        self.weight_edit.setDecimals(1)
        self.weight_edit.setRange(1, 1000)
        self.weight_edit.setValue(entry["weight"])

        # Time
        self.time_edit = QTimeEdit()

        if entry.get("time"):
            self.time_edit.setTime(
                QTime.fromString(entry["time"], "h:mm AP")
            )

        # Dose
        self.dose_combo = QComboBox()
        self.dose_combo.addItems([
            "2.5 mg",
            "5.0 mg",
            "7.5 mg",
            "10.0 mg",
            "12.5 mg",
            "15.0 mg"
        ])

        index = self.dose_combo.findText(
            entry.get("zepbound_mg", "2.5 mg")
        )

        if index >= 0:
            self.dose_combo.setCurrentIndex(index)

        layout.addRow("Date", self.date_edit)
        layout.addRow("Weight", self.weight_edit)
        layout.addRow("Time", self.time_edit)
        layout.addRow("Zepbound", self.dose_combo)
        self.notes_edit = QTextEdit()

        self.notes_edit.setPlainText(
            entry.get("notes", "")
        )

        self.notes_edit.setMaximumHeight(80)

        layout.addRow("Notes", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def values(self):

        return {
            "date":
                self.date_edit.date().toString("yyyy-MM-dd"),

            "weight":
                self.weight_edit.value(),

            "time":
                self.time_edit.time().toString("h:mm AP"),

            "zepbound_mg":
                self.dose_combo.currentText(),

            "notes":
                self.notes_edit.toPlainText().strip()
        }


class WeightTracker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("WeightTrackerIcon.ico"))
        self.setWindowTitle("Weight Tracker")
        self.resize(700, 700)
        self.setMinimumSize(700, 700)

        self.setStyleSheet("""

        QWidget{
            background:#2d2d30;
            color:white;
            font-size:10pt;
        }

        /* ---------- Stat Cards ---------- */

        QFrame#StatCard{
            background:#3a3a3d;
            border:1px solid #555;
            border-radius:10px;
        }

        QLabel#CardTitle{
            color:#bfbfbf;
            font-size:9pt;
        }

        QLabel#CardValue{
            color:white;
            font-size:18pt;
            font-weight:bold;
        }

        /* ---------- Entry Box ---------- */

        QLineEdit{
            background:#404044;
            border:1px solid #666;
            border-radius:6px;
            padding:8px;
        }

        /* ---------- Buttons ---------- */

        QPushButton{
            background:#4b4b50;
            color:white;
            border:1px solid #666;
            border-radius:6px;
            padding:8px 16px;
            font-weight:bold;
        }

        QPushButton:hover{
            background:#5a5a60;
        }

        QPushButton:pressed{
            background:#3e3e42;
        }

        /* Delete & Reset */

        QPushButton#Danger{
            background:#7a3030;
        }

        QPushButton#Danger:hover{
            background:#934040;
        }

        /* ---------- Table ---------- */

        QHeaderView::section{
            background:#3a3a3d;
            color:white;
            border:none;
            padding:6px;
        }

        QTableWidget{
            background:#323236;
            alternate-background-color:#3a3a3d;
            gridline-color:#555;
            selection-background-color:#5d7aa8;
        }

        /* ---------- Progress Bar ---------- */

        QProgressBar{
            background:#3a3a3d;
            border:1px solid #555;
            border-radius:8px;
            text-align:center;
            color:white;
            font-weight:bold;
        }

        QProgressBar::chunk{
            background:#6BCB77;
            border-radius:7px;
        }

        QGroupBox{
            border:1px solid #555;
            border-radius:8px;
            margin-top:12px;
            font-weight:bold;
            padding-top:12px;
        }

        QGroupBox::title{
            subcontrol-origin: margin;
            left:12px;
            padding:0 5px;
        }

        QFormLayout QLabel{
            color:white;
        }

        """)

        self.data = self.load_data()

        self.start_card, self.start_lbl = self.create_stat_card(
            "Starting Weight")
        self.current_card, self.current_lbl = self.create_stat_card(
            "Current Weight")
        self.goal_card, self.goal_lbl = self.create_stat_card("Goal Weight")
        goal_glow = QGraphicsDropShadowEffect()

        goal_glow.setBlurRadius(20)
        goal_glow.setOffset(0, 0)
        goal_glow.setColor(QColor(107, 203, 119))

        self.goal_card.setGraphicsEffect(goal_glow)
        self.lost_card, self.lost_lbl = self.create_stat_card("Weight Lost")
        self.remaining_card, self.remaining_lbl = self.create_stat_card(
            "Remaining")

        self.progress_lbl = QLabel("Progress to Goal")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(22)

        self.weight_edit = QLineEdit()
        self.weight_edit.setPlaceholderText("Today's weight")
        self.weight_edit.returnPressed.connect(self.log_weight)

        self.log_btn = QPushButton("Log Weight")
        self.log_btn.clicked.connect(self.log_weight)

        # Time weighed
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("h:mm AP")
        self.time_edit.setTime(QTime.currentTime())

        # Zepbound dose
        self.dose_combo = QComboBox()
        self.dose_combo.addItems([
            "2.5 mg",
            "5.0 mg",
            "7.5 mg",
            "10.0 mg",
            "12.5 mg",
            "15.0 mg"
        ])
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Optional notes..."
        )
        self.notes_edit.setMaximumHeight(60)

        # Toolbar Buttons
        self.edit_btn = QPushButton("Edit Entry")
        self.delete_btn = QPushButton("Delete Entry")
        self.delete_btn.setObjectName("Danger")
        self.start_btn = QPushButton("Change Start")
        self.goal_btn = QPushButton("Change Goal")
        self.reset_btn = QPushButton("Reset Tracker")
        self.reset_btn.setObjectName("Danger")

        self.edit_btn.clicked.connect(self.edit_entry)
        self.delete_btn.clicked.connect(self.delete_entry)
        self.start_btn.clicked.connect(self.change_start_weight)
        self.goal_btn.clicked.connect(self.change_goal_weight)
        self.reset_btn.clicked.connect(self.reset_tracker)

        # -------------------------
        # Entry Details
        # -------------------------

        self.details_group = QGroupBox("Entry Details")

        details_layout = QHBoxLayout()

        # -------------------------
        # LEFT SIDE
        # -------------------------

        left = QFormLayout()

        self.detail_date = QLabel("Select an entry...")
        self.detail_weight = QLabel("--")
        self.detail_dose = QLabel("--")
        self.detail_time = QLabel("--")

        left.addRow("Date:", self.detail_date)
        left.addRow("Weight:", self.detail_weight)
        left.addRow("Zepbound:", self.detail_dose)
        left.addRow("Time:", self.detail_time)

        # -------------------------
        # RIGHT SIDE
        # -------------------------

        right = QVBoxLayout()

        right.addWidget(QLabel("Notes"))

        self.detail_notes = QTextEdit()
        self.detail_notes.setReadOnly(True)
        self.detail_notes.setMinimumWidth(300)

        right.addWidget(self.detail_notes)

        details_layout.addLayout(left)
        details_layout.addSpacing(20)
        details_layout.addLayout(right)

        self.details_group.setLayout(details_layout)

        self.table = QTableWidget(0, 4)

        self.table.setHorizontalHeaderLabels(
            ["Date", "Weight", "Δ Start", "Δ Previous"]
        )

        # Stretch all columns
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Alternate row colors
        self.table.setAlternatingRowColors(True)

        # Select entire rows
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        # Only one row at a time
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # User cannot edit directly
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        # Nice looking headers
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setVisible(False)

        # Enable sorting
        self.table.setSortingEnabled(True)

        # Double-click a row to edit
        self.table.doubleClicked.connect(self.edit_entry)
        self.table.itemSelectionChanged.connect(self.show_entry_details)

        top = QHBoxLayout()

        top.setSpacing(12)

        top.addWidget(self.start_card)
        top.addWidget(self.current_card)
        top.addWidget(self.goal_card)
        top.addWidget(self.lost_card)
        top.addWidget(self.remaining_card)

        row = QHBoxLayout()

        row.addWidget(QLabel("Weight"))
        row.addWidget(self.weight_edit)

        row.addSpacing(10)

        row.addWidget(QLabel("Time"))
        row.addWidget(self.time_edit)

        row.addSpacing(10)

        row.addWidget(QLabel("Zepbound"))
        row.addWidget(self.dose_combo)

        row.addStretch()

        row.addWidget(self.log_btn)

        toolbar = QHBoxLayout()

        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)

        toolbar.addStretch()

        toolbar.addWidget(self.start_btn)
        toolbar.addWidget(self.goal_btn)
        toolbar.addWidget(self.reset_btn)

        layout = QVBoxLayout(self)

        layout.addLayout(top)

        layout.addSpacing(8)

        layout.addWidget(self.progress_lbl)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(12)

        layout.addLayout(row)

        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_edit)

        layout.addWidget(self.table)

        layout.addSpacing(10)

        layout.addWidget(self.details_group)

        layout.addSpacing(10)

        layout.addLayout(toolbar)

        self.refresh()

    def create_stat_card(self, title):

        frame = QFrame()
        frame.setObjectName("StatCard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("CardTitle")

        value_lbl = QLabel("--")
        value_lbl.setObjectName("CardValue")

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)

        return frame, value_lbl

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)

        start, ok = QInputDialog.getDouble(
            self, "Setup", "Starting Weight", decimals=1)
        if not ok:
            raise SystemExit
        goal, ok = QInputDialog.getDouble(
            self, "Setup", "Goal Weight", decimals=1)
        if not ok:
            raise SystemExit

        data = {
            "start_weight": start,
            "goal_weight": goal,
            "entries": []
        }
        self.save_data(data)
        return data

    def save_data(self, data=None):
        if data is None:
            data = self.data
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def log_weight(self):
        txt = self.weight_edit.text().strip()
        try:
            wt = float(txt)
        except:
            QMessageBox.warning(self, "Invalid", "Enter a valid weight.")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        for e in self.data["entries"]:
            if e["date"] == today:
                if QMessageBox.question(
                    self, "Replace?",
                    "Today's entry already exists. Replace it?"
                ) == QMessageBox.StandardButton.Yes:
                    e["weight"] = wt
                    e["time"] = self.time_edit.time().toString("h:mm AP")
                    e["zepbound_mg"] = self.dose_combo.currentText()
                    e["notes"] = self.notes_edit.toPlainText().strip()
                else:
                    return
                break
        else:
            self.data["entries"].append({
                "date": today,
                "time": self.time_edit.time().toString("h:mm AP"),
                "weight": wt,
                "zepbound_mg": self.dose_combo.currentText(),
                "notes": self.notes_edit.toPlainText().strip()
            })

        self.data["entries"].sort(key=lambda x: x["date"])
        self.save_data()
        self.weight_edit.clear()
        self.notes_edit.clear()
        self.refresh()

    def refresh(self):
        self.table.setSortingEnabled(False)
        entries = self.data["entries"]
        start = self.data["start_weight"]
        goal = self.data["goal_weight"]

        current = entries[-1]["weight"] if entries else start
        lost = start-current
        remaining = current-goal

        goal_distance = start - goal
        completed = start - current

        if goal_distance <= 0:
            percent = 0
        else:
            percent = max(
                0,
                min(
                    100,
                    round((completed / goal_distance) * 100)
                )
            )

        self.progress_bar.setValue(percent)

        if current <= goal:
            self.progress_bar.setFormat("GOAL REACHED! 🎉")
        else:
            self.progress_bar.setFormat(f"{percent}% Complete")

        self.start_lbl.setText(f"{start:.1f} lbs")
        self.goal_lbl.setText(f"{goal:.1f} lbs")

        # Current Weight
        self.current_lbl.setText(f"{current:.1f} lbs")

        if current <= start:
            self.current_lbl.setStyleSheet("""
                color:#6BCB77;
                font-size:18pt;
                font-weight:bold;
            """)
        else:
            self.current_lbl.setStyleSheet("""
                color:#E57373;
                font-size:18pt;
                font-weight:bold;
            """)

        # Weight Lost
        if lost >= 0:
            self.lost_lbl.setText(f"{lost:.1f} lbs")
            self.lost_lbl.setStyleSheet("""
                color:#6BCB77;
                font-size:18pt;
                font-weight:bold;
            """)
        else:
            self.lost_lbl.setText(f"+{-lost:.1f} lbs")
            self.lost_lbl.setStyleSheet("""
                color:#E57373;
                font-size:18pt;
                font-weight:bold;
            """)

        # Remaining
        if current <= goal:
            self.remaining_lbl.setText("Goal Reached 🎉")
        else:
            self.remaining_lbl.setText(f"{remaining:.1f} lbs")

        self.start_lbl.setStyleSheet("""
            color:white;
            font-size:18pt;
            font-weight:bold;
        """)

        self.goal_lbl.setStyleSheet("""
            color:#6BCB77;
            font-size:18pt;
            font-weight:bold;
        """)

        self.remaining_lbl.setStyleSheet("""
            color:white;
            font-size:18pt;
            font-weight:bold;
        """)

        self.table.setRowCount(len(entries))
        prev = None

        for r, e in enumerate(entries):
            delta_start = e["weight"]-start
            delta_prev = "--" if prev is None else f"{e['weight']-prev:+.1f}"
            prev = e["weight"]
            date_item = QTableWidgetItem(
                datetime.strptime(
                    e["date"],
                    "%Y-%m-%d"
                ).strftime("%m/%d/%y")
            )

            date_item.setData(
                Qt.ItemDataRole.UserRole,
                e["date"]
            )

            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(r, 0, date_item)

            for c, v in enumerate([
                    f"{e['weight']:.1f}",
                    f"{delta_start:+.1f}",
                    delta_prev
            ], start=1):

                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)

        self.table.setSortingEnabled(True)

        # Remember the last selected Zepbound dose
        if entries:
            last = entries[-1]

            dose = last.get("zepbound_mg")

            if dose:
                index = self.dose_combo.findText(dose)
                if index >= 0:
                    self.dose_combo.setCurrentIndex(index)

        # Reset weigh-in time to now
        self.time_edit.setTime(QTime.currentTime())

    def show_entry_details(self):

        row = self.table.currentRow()

        if row < 0:
            self.detail_date.setText("Select an entry...")
            self.detail_weight.setText("--")
            self.detail_dose.setText("--")
            self.detail_time.setText("--")
            self.detail_notes.clear()
            return

        entry_date = self.table.item(
            row,
            0
        ).data(Qt.ItemDataRole.UserRole)

        for entry in self.data["entries"]:

            if entry["date"] == entry_date:

                pretty_date = datetime.strptime(
                    entry["date"],
                    "%Y-%m-%d"
                ).strftime("%B %d, %Y")

                self.detail_date.setText(pretty_date)
                self.detail_weight.setText(f"{entry['weight']:.1f} lbs")
                self.detail_dose.setText(entry.get("zepbound_mg", "--"))
                self.detail_time.setText(entry.get("time", "--"))
                self.detail_notes.setPlainText(
                    entry.get("notes", "")
                )

                return

    def edit_entry(self):

        row = self.table.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select an entry."
            )
            return

        entry_date = self.table.item(
            row,
            0
        ).data(Qt.ItemDataRole.UserRole)

        entry = None

        for e in self.data["entries"]:
            if e["date"] == entry_date:
                entry = e
                break

        if entry is None:
            return

        dlg = EditEntryDialog(entry, self)

        if dlg.exec():

            updated = dlg.values()

            entry.update(updated)

            self.data["entries"].sort(
                key=lambda x: x["date"]
            )

            self.save_data()

            self.refresh()

    def delete_entry(self):

        row = self.table.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select an entry to delete."
            )
            return

        date = self.table.item(row, 0).text()
        weight = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self,
            "Delete Entry",
            f"Delete this entry?\n\n"
            f"Date: {date}\n"
            f"Weight: {weight} lbs",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        entry_date = self.table.item(
            row,
            0
        ).data(Qt.ItemDataRole.UserRole)

        self.data["entries"] = [
            e for e in self.data["entries"]
            if e["date"] != entry_date
        ]

        self.save_data()
        self.refresh()

        QMessageBox.information(
            self,
            "Deleted",
            "Weight entry deleted."
        )

    def change_start_weight(self):

        new_weight, ok = QInputDialog.getDouble(
            self,
            "Starting Weight",
            "Enter new starting weight:",
            value=self.data["start_weight"],
            decimals=1,
            min=1.0,
            max=1000.0
        )

        if not ok:
            return

        self.data["start_weight"] = new_weight

        self.save_data()
        self.refresh()

        QMessageBox.information(
            self,
            "Updated",
            "Starting weight updated."
        )

    def change_goal_weight(self):

        new_weight, ok = QInputDialog.getDouble(
            self,
            "Goal Weight",
            "Enter new goal weight:",
            value=self.data["goal_weight"],
            decimals=1,
            min=1.0,
            max=1000.0
        )

        if not ok:
            return

        self.data["goal_weight"] = new_weight

        self.save_data()
        self.refresh()

        QMessageBox.information(
            self,
            "Updated",
            "Goal weight updated."
        )

    def reset_tracker(self):

        msg = QMessageBox(self)
        msg.setWindowTitle("Reset Tracker")
        msg.setText("Choose what you want to reset:")

        clear_btn = msg.addButton(
            "Clear Logged Weights",
            QMessageBox.ButtonRole.ActionRole
        )

        restart_btn = msg.addButton(
            "Start Completely Over",
            QMessageBox.ButtonRole.ActionRole
        )

        cancel_btn = msg.addButton(
            QMessageBox.StandardButton.Cancel
        )

        msg.exec()

        clicked = msg.clickedButton()

        if clicked == cancel_btn:
            return

        # ---------------------------------------
        # Clear logged weights only
        # ---------------------------------------
        if clicked == clear_btn:

            if QMessageBox.question(
                self,
                "Confirm",
                "Delete ALL logged weights?\n\n"
                "Your starting and goal weights will be kept.",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return

            self.data["entries"] = []

            self.save_data()
            self.refresh()

            QMessageBox.information(
                self,
                "Done",
                "All logged weights have been removed."
            )
            return

        # ---------------------------------------
        # Start over completely
        # ---------------------------------------
        if clicked == restart_btn:

            if QMessageBox.question(
                self,
                "Confirm",
                "Delete everything and start over?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return

            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)

            self.data = self.load_data()
            self.refresh()

            QMessageBox.information(
                self,
                "Done",
                "Tracker has been reset."
            )


if __name__ == "__main__":
    app = QApplication([])
    w = WeightTracker()
    w.show()
    app.exec()
