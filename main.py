from dotenv import load_dotenv
load_dotenv()
import os
import sys
import json
import requests
import base64
from datetime import datetime
from PIL import Image
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QSpinBox, QDoubleSpinBox, QComboBox, QProgressBar, 
                            QScrollArea, QFileDialog, QMessageBox, QTabWidget, 
                            QGridLayout, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor
from pathlib import Path

class ImageGenerationThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, params):
        super().__init__()
        self.api_key = "YOUR_API_KEY"
        self.params = params

    def run(self):
        try:
            api_host = 'https://api.stability.ai'
            engine_id = "stable-diffusion-xl-1024-v1-0"

            response = requests.post(
                f"{api_host}/v1/generation/{engine_id}/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json=self.params
            )

            if response.status_code != 200:
                self.error.emit(f"Error: {response.status_code} - {response.text}")
                return

            self.finished.emit(response.json())

        except Exception as e:
            self.error.emit(str(e))

class HistoryViewer(QWidget):
    # Same as before...
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # History Grid
        self.grid = QGridLayout()
        scroll = QScrollArea()
        scroll_content = QWidget()
        scroll_content.setLayout(self.grid)
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
        
        self.load_history()

    def load_history(self):
        output_dir = Path("outputs")
        if not output_dir.exists():
            return

        row = 0
        col = 0
        for file in output_dir.glob("*.png"):
            metadata_file = output_dir / f"metadata_{file.stem.split('_')[1]}.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                
                frame = QFrame()
                frame.setFrameStyle(QFrame.Shape.StyledPanel)
                frame_layout = QVBoxLayout()
                
                image_label = QLabel()
                pixmap = QPixmap(str(file))
                image_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
                
                prompt_label = QLabel(f"Prompt: {metadata['prompt'][:50]}...")
                prompt_label.setWordWrap(True)
                
                frame_layout.addWidget(image_label)
                frame_layout.addWidget(prompt_label)
                frame.setLayout(frame_layout)
                
                self.grid.addWidget(frame, row, col)
                
                col += 1
                if col > 2:
                    col = 0
                    row += 1

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AI Image Generator")
        self.setMinimumSize(1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Generator tab
        generator_tab = QWidget()
        generator_layout = QHBoxLayout(generator_tab)
        
        # Left panel (controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)
        
        # Prompt input
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt here...")
        
        # Parameters
        params_frame = QFrame()
        params_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        params_layout = QVBoxLayout(params_frame)
        
        # Image dimensions
        dims_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1024, 1024) 
        self.width_spin.setValue(768)
        self.width_spin.setSingleStep(64)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1024, 1024)
        self.height_spin.setValue(768)
        self.height_spin.setSingleStep(64)
        
        dims_layout.addWidget(QLabel("Width:"))
        dims_layout.addWidget(self.width_spin)
        dims_layout.addWidget(QLabel("Height:"))
        dims_layout.addWidget(self.height_spin)
        
        # Other parameters
        self.cfg_scale = QDoubleSpinBox()
        self.cfg_scale.setRange(0, 35)
        self.cfg_scale.setValue(7)
        
        self.steps = QSpinBox()
        self.steps.setRange(10, 150)
        self.steps.setValue(50)
        
        self.samples = QSpinBox()
        self.samples.setRange(1, 4)
        self.samples.setValue(1)
        
        # Add parameters to layout
        params_layout.addLayout(dims_layout)
        params_layout.addWidget(QLabel("CFG Scale:"))
        params_layout.addWidget(self.cfg_scale)
        params_layout.addWidget(QLabel("Steps:"))
        params_layout.addWidget(self.steps)
        params_layout.addWidget(QLabel("Number of Images:"))
        params_layout.addWidget(self.samples)
        
        # Advanced options
        advanced_frame = QFrame()
        advanced_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        advanced_layout = QVBoxLayout(advanced_frame)
        
        self.style_selection = QComboBox()
        self.style_selection.addItems([
            "None", 
            "Photorealistic", 
            "Digital Art", 
            "Oil Painting", 
            "Watercolor", 
            "Pencil Sketch",
            "3D Render",
            "Anime Style",
            "Comic Book",
            "Fantasy Art"
        ])
        
        self.negative_prompt = QTextEdit()
        self.negative_prompt.setPlaceholderText("Enter negative prompt here (things to avoid in the image)...")
        self.negative_prompt.setMaximumHeight(100)
        
        advanced_layout.addWidget(QLabel("Style:"))
        advanced_layout.addWidget(self.style_selection)
        advanced_layout.addWidget(QLabel("Negative Prompt:"))
        advanced_layout.addWidget(self.negative_prompt)
        
        # Generate button and progress bar
        self.generate_btn = QPushButton("Generate Images")
        self.generate_btn.clicked.connect(self.generate_images)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
            }
        """)
        
        # Add everything to left layout
        left_layout.addWidget(QLabel("Prompt:"))
        left_layout.addWidget(self.prompt_input)
        left_layout.addWidget(params_frame)
        left_layout.addWidget(advanced_frame)
        left_layout.addWidget(self.generate_btn)
        left_layout.addWidget(self.progress_bar)
        left_layout.addStretch()
        
        # Right panel (image display)
        right_panel = QWidget()
        self.right_layout = QGridLayout(right_panel)
        
        # Add panels to generator layout
        generator_layout.addWidget(left_panel)
        generator_layout.addWidget(right_panel)
        
        # History tab
        history_tab = HistoryViewer()
        
        # Add tabs
        tabs.addTab(generator_tab, "Generator")
        tabs.addTab(history_tab, "History")
        
        layout.addWidget(tabs)
        
        self.show()

    def generate_images(self):
        if not self.prompt_input.toPlainText():
            QMessageBox.warning(self, "Error", "Please enter a prompt")
            return

        # Clear previous images
        for i in reversed(range(self.right_layout.count())): 
            self.right_layout.itemAt(i).widget().setParent(None)

        # Prepare parameters
        style = self.style_selection.currentText()
        prompt = self.prompt_input.toPlainText()
        if style != "None":
            prompt = f"{prompt}, {style} style"

        params = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1
                }
            ],
            "cfg_scale": self.cfg_scale.value(),
            "height": self.height_spin.value(),
            "width": self.width_spin.value(),
            "samples": self.samples.value(),
            "steps": self.steps.value(),
        }

        # Add negative prompt if specified
        if self.negative_prompt.toPlainText():
            params["text_prompts"].append({
                "text": self.negative_prompt.toPlainText(),
                "weight": -1
            })

        # Start generation thread
        self.thread = ImageGenerationThread(params)
        self.thread.finished.connect(self.handle_generation_complete)
        self.thread.error.connect(self.handle_generation_error)
        self.thread.progress.connect(self.progress_bar.setValue)
        
        self.generate_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.thread.start()

    def handle_generation_complete(self, result):
        self.generate_btn.setEnabled(True)
        self.progress_bar.setValue(100)

        row = 0
        col = 0
        for idx, image in enumerate(result["artifacts"]):
            # Save image
            image_data = base64.b64decode(image["base64"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if not os.path.exists("outputs"):
                os.makedirs("outputs")
                
            filename = f"outputs/generated_{timestamp}_{idx}.png"
            
            with open(filename, "wb") as f:
                f.write(image_data)

            # Save metadata
            metadata = {
                "prompt": self.prompt_input.toPlainText(),
                "timestamp": timestamp,
                "parameters": {
                    "height": self.height_spin.value(),
                    "width": self.width_spin.value(),
                    "cfg_scale": self.cfg_scale.value(),
                    "steps": self.steps.value(),
                    "style": self.style_selection.currentText(),
                }
            }
            
            with open(f"outputs/metadata_{timestamp}_{idx}.json", "w") as f:
                json.dump(metadata, f, indent=4)

            # Display image
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.StyledPanel)
            layout = QVBoxLayout(frame)
            
            image = QImage.fromData(image_data)
            pixmap = QPixmap.fromImage(image)
            
            image_label = QLabel()
            image_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio))
            
            save_btn = QPushButton("Save Image")
            save_btn.clicked.connect(lambda checked, f=filename: self.save_image(f))
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            
            layout.addWidget(image_label)
            layout.addWidget(save_btn)
            
            self.right_layout.addWidget(frame, row, col)
            
            col += 1
            if col > 1:
                col = 0
                row += 1

    def handle_generation_error(self, error_message):
        self.generate_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", error_message)

    def save_image(self, source_path):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png)")
        if file_name:
            with open(source_path, "rb") as source, open(file_name, "wb") as target:
                target.write(source.read())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Set dark theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)

    window = MainWindow()
    sys.exit(app.exec())