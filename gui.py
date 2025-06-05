import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QProgressBar, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5 import QtGui
from PyQt5.QtGui import QPixmap
from main import main
import qasync


class TqdmToProgressBar(QObject):
    progress_updated = pyqtSignal(int)
    total_updated = pyqtSignal(int)

    def __init__(self, progress_bar):
        super().__init__()
        self.progress_bar = progress_bar
        self.progress_updated.connect(self.progress_bar.setValue)
        self.total_updated.connect(self.progress_bar.setMaximum)

    def update(self, n=1):
        self.progress_updated.emit(self.progress_bar.value() + n)

    def set_total(self, total):
        self.total_updated.emit(total)


class ParserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Парсер Ozon")
        self.setGeometry(100, 100, 450, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #000000;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLabel {
                font-size: 14px;
                color: #000000;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #000000;
                padding: 6px;
                border-radius: 6px;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #000000;
                padding: 6px;
                border-radius: 6px;
            }
            QProgressBar {
                border: 1px solid #000000;
                border-radius: 6px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #000000;
                width: 10px;
                margin: 0.5px;
            }
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #222222;
            }
            QPushButton:disabled {
                background-color: #777777;
                color: #dddddd;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- ЛОГОТИП ---
        logo_label = QLabel()
        pixmap = QPixmap()
        pixmap.load("img.png")
        pixmap = pixmap.scaledToHeight(50, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        title_label = QLabel("Парсер Ozon")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(title_label)

        self.query_label = QLabel("Поисковый запрос:")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText(
            "Введите запрос, например, 'смартфон'")
        main_layout.addWidget(self.query_label)
        main_layout.addWidget(self.query_input)

        self.max_products_label = QLabel("Количество товаров для парсинга:")
        self.max_products_input = QLineEdit("1000")
        self.max_products_input.setValidator(QtGui.QIntValidator(1, 1000000))
        main_layout.addWidget(self.max_products_label)
        main_layout.addWidget(self.max_products_input)

        self.output_file_label = QLabel("Имя выходного файла:")
        self.output_file_input = QLineEdit("ozon_products.xlsx")
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.output_file_input)
        self.select_file_button = QPushButton("Выбрать папку")
        self.select_file_button.clicked.connect(self.select_output_directory)
        file_layout.addWidget(self.select_file_button)
        main_layout.addWidget(self.output_file_label)
        main_layout.addLayout(file_layout)

        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.parse_button = QPushButton("Начать парсинг")
        self.parse_button.clicked.connect(self.start_parsing)
        main_layout.addWidget(self.parse_button)

        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setFixedHeight(100)
        main_layout.addWidget(self.status_output)

    def select_output_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Выберите папку для сохранения файла")
        if directory:
            filename = self.output_file_input.text().strip()
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            self.output_file_input.setText(f"{directory}/{filename}")

    async def run_parsing(self, query, max_products, output_file, progress_handler):
        try:
            await main(query, max_products, output_file, progress_handler)
            self.status_output.append(
                f"Парсинг завершен. Файл сохранен: {output_file}")
        except Exception as e:
            self.status_output.append(f"Ошибка при парсинге: {str(e)}")
        finally:
            self.parse_button.setEnabled(True)
            self.progress_bar.setValue(0)

    @qasync.asyncSlot()
    async def start_parsing(self):
        query = self.query_input.text().strip()
        if not query:
            self.status_output.append("Ошибка: Введите поисковый запрос")
            return
        try:
            max_products = int(self.max_products_input.text())
        except ValueError:
            self.status_output.append(
                "Ошибка: Введите корректное число для количества товаров")
            return
        output_file = self.output_file_input.text().strip()
        if not output_file:
            self.status_output.append("Ошибка: Введите имя выходного файла")
            return
        if not output_file.endswith('.xlsx'):
            output_file += '.xlsx'
            self.output_file_input.setText(output_file)
        self.parse_button.setEnabled(False)
        self.status_output.append("Парсинг начат...")
        progress_handler = TqdmToProgressBar(self.progress_bar)
        await self.run_parsing(query, max_products, output_file, progress_handler)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = ParserApp()
    window.show()
    with loop:
        loop.run_forever()
