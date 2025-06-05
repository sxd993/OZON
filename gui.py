import sys
import asyncio
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar, QFileDialog
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5 import QtGui
from main import main
import qasync


class TqdmToProgressBar(QObject):
    """Класс для перенаправления обновлений tqdm в QProgressBar."""
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
        self.setStyleSheet("background-color: #f0f0f0;")

        # Основной виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel("Парсер Ozon")
        title_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #333;")
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # Поле для поискового запроса
        self.query_label = QLabel("Поисковый запрос:")
        self.query_label.setStyleSheet("font-size: 14px; color: #555;")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText(
            "Введите запрос, например, 'смартфон'")
        self.query_input.setStyleSheet(
            "font-size: 14px; padding: 5px; border: 1px solid #ccc; border-radius: 5px;")
        query_layout = QHBoxLayout()
        query_layout.addStretch()
        query_layout.addWidget(self.query_input, 1)
        query_layout.addStretch()
        main_layout.addWidget(self.query_label)
        main_layout.addLayout(query_layout)

        # Поле для количества товаров для парсинга
        self.max_products_label = QLabel("Количество товаров для парсинга:")
        self.max_products_label.setStyleSheet("font-size: 14px; color: #555;")
        self.max_products_input = QLineEdit("1000")
        self.max_products_input.setValidator(QtGui.QIntValidator(1, 1000000))
        self.max_products_input.setStyleSheet(
            "font-size: 14px; padding: 5px; border: 1px solid #ccc; border-radius: 5px;")
        max_products_layout = QHBoxLayout()
        max_products_layout.addStretch()
        max_products_layout.addWidget(self.max_products_input, 1)
        max_products_layout.addStretch()
        main_layout.addWidget(self.max_products_label)
        main_layout.addLayout(max_products_layout)

        # Поле для имени выходного файла
        self.output_file_label = QLabel("Имя выходного файла:")
        self.output_file_label.setStyleSheet("font-size: 14px; color: #555;")
        self.output_file_input = QLineEdit("ozon_products.xlsx")
        self.output_file_input.setStyleSheet(
            "font-size: 14px; padding: 5px; border: 1px solid #ccc; border-radius: 5px;")
        output_file_layout = QHBoxLayout()
        output_file_layout.addStretch()
        output_file_layout.addWidget(self.output_file_input, 1)
        self.select_file_button = QPushButton("Выбрать папку")
        self.select_file_button.setStyleSheet("""
            QPushButton {
                font-size: 14px; 
                padding: 8px; 
                background-color: #6B7280; 
                color: white; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        self.select_file_button.clicked.connect(self.select_output_directory)
        output_file_layout.addWidget(self.select_file_button)
        output_file_layout.addStretch()
        main_layout.addWidget(self.output_file_label)
        main_layout.addLayout(output_file_layout)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("font-size: 12px; padding: 5px;")
        self.progress_bar.setTextVisible(True)
        progress_layout = QHBoxLayout()
        progress_layout.addStretch()
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addStretch()
        main_layout.addLayout(progress_layout)

        # Кнопка для запуска парсинга
        self.parse_button = QPushButton("Начать парсинг")
        self.parse_button.setStyleSheet("""
            QPushButton {
                font-size: 16px; 
                padding: 10px; 
                background-color: #4A90E2; 
                color: white; 
                border: none; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:disabled {
                background-color: #A0C4FF;
            }
        """)
        parse_button_layout = QHBoxLayout()
        parse_button_layout.addStretch()
        parse_button_layout.addWidget(self.parse_button, 1)
        parse_button_layout.addStretch()
        self.parse_button.clicked.connect(self.start_parsing)
        main_layout.addLayout(parse_button_layout)

        # Поле для статуса
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setStyleSheet(
            "font-size: 12px; border: 1px solid #ccc; border-radius: 5px; padding: 5px; background-color: white;")
        self.status_output.setFixedHeight(100)
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        status_layout.addWidget(self.status_output, 1)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

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
