import sys
import asyncio
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5 import QtGui
import qasync
from main import main

class ProgressHandler(QObject):
    """Заглушка для совместимости с main.py."""
    def __init__(self):
        super().__init__()

    def update(self, n=1):
        pass

    def set_total(self, total):
        pass

    def __call__(self, progress):
        pass

class ParserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Парсер Ozon")
        self.setGeometry(100, 100, 500, 650)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #E2E8F0, stop:1 #CBD5E1);
            }
        """)

        # Основной виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Заголовок
        title_label = QLabel("Парсер Ozon")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #1E293B; 
            font-family: 'Arial', sans-serif;
        """)
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # Поле для поискового запроса
        self.query_label = QLabel("Поисковый запрос:")
        self.query_label.setStyleSheet("""
            font-size: 14px; 
            color: #334155; 
            font-family: 'Arial', sans-serif;
        """)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Например, 'кран шаровой'")
        self.query_input.setStyleSheet("""
            font-size: 14px; 
            padding: 10px; 
            border: none; 
            border-radius: 8px; 
            background-color: #FFFFFF; 
            color: #1E293B;
        """)
        query_layout = QHBoxLayout()
        query_layout.addStretch()
        query_layout.addWidget(self.query_input, 1)
        query_layout.addStretch()
        main_layout.addWidget(self.query_label)
        main_layout.addLayout(query_layout)

        # Поле для количества товаров
        self.max_products_label = QLabel("Количество товаров:")
        self.max_products_label.setStyleSheet("""
            font-size: 14px; 
            color: #334155; 
            font-family: 'Arial', sans-serif;
        """)
        self.max_products_input = QLineEdit("50")
        self.max_products_input.setValidator(QtGui.QIntValidator(1, 100000))
        self.max_products_input.setStyleSheet("""
            font-size: 14px; 
            padding: 10px; 
            border: none; 
            border-radius: 8px; 
            background-color: #FFFFFF; 
            color: #1E293B;
        """)
        max_products_layout = QHBoxLayout()
        max_products_layout.addStretch()
        max_products_layout.addWidget(self.max_products_input, 1)
        max_products_layout.addStretch()
        main_layout.addWidget(self.max_products_label)
        main_layout.addLayout(max_products_layout)

        # Поле для имени выходного файла
        self.output_file_label = QLabel("Выходной файл:")
        self.output_file_label.setStyleSheet("""
            font-size: 14px; 
            color: #334155; 
            font-family: 'Arial', sans-serif;
        """)
        self.output_file_input = QLineEdit("ozon_products.xlsx")
        self.output_file_input.setStyleSheet("""
            font-size: 14px; 
            padding: 10px; 
            border: none; 
            border-radius: 8px; 
            background-color: #FFFFFF; 
            color: #1E293B;
        """)
        self.browse_button = QPushButton("Обзор")
        self.browse_button.setStyleSheet("""
            QPushButton {
                font-size: 14px; 
                padding: 10px; 
                background-color: #475569; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                font-family: 'Arial', sans-serif;
            }
            QPushButton:hover {
                background-color: #64748B;
            }
        """)
        self.browse_button.clicked.connect(self.browse_file)
        output_file_layout = QHBoxLayout()
        output_file_layout.addStretch()
        output_file_layout.addWidget(self.output_file_input, 2)
        output_file_layout.addWidget(self.browse_button, 1)
        output_file_layout.addStretch()
        main_layout.addWidget(self.output_file_label)
        main_layout.addLayout(output_file_layout)

        # Кнопка для запуска парсинга
        self.parse_button = QPushButton("Начать парсинг")
        self.parse_button.setStyleSheet("""
            QPushButton {
                font-size: 16px; 
                padding: 12px; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #3B82F6, stop:1 #2563EB);
                color: white; 
                border: none; 
                border-radius: 8px; 
                font-family: 'Arial', sans-serif;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #60A5FA, stop:1 #3B82F6);
            }
            QPushButton:disabled {
                background: #94A3B8;
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
        self.status_output.setStyleSheet("""
            font-size: 14px; 
            padding: 10px; 
            border: none; 
            border-radius: 8px; 
            background-color: #FFFFFF; 
            color: #1E293B; 
            font-family: 'Arial', sans-serif;
        """)
        self.status_output.setFixedHeight(150)
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        status_layout.addWidget(self.status_output, 1)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

    def browse_file(self):
        """Открыть диалог выбора файла."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Выберите файл для сохранения", "", "Excel Files (*.xlsx);;All Files (*)"
        )
        if file_path:
            self.output_file_input.setText(file_path)

    async def run_parsing(self, query, max_products, output_file, progress_handler):
        """Запуск парсинга."""
        try:
            await main(query, max_products, output_file, progress_handler)
            self.status_output.append(f"Парсинг завершён. Файл сохранён: {output_file}")
        except Exception as e:
            self.status_output.append(f"Ошибка при парсинге: {str(e)}")
        finally:
            self.parse_button.setEnabled(True)

    @qasync.asyncSlot()
    async def start_parsing(self):
        """Запуск парсинга при нажатии кнопки."""
        query = self.query_input.text().strip()
        if not query:
            self.status_output.append("Ошибка: Введите поисковый запрос")
            return
        try:
            max_products = int(self.max_products_input.text())
        except ValueError:
            self.status_output.append("Ошибка: Введите корректное число для количества товаров")
            return
        output_file = self.output_file_input.text().strip()
        if not output_file:
            self.status_output.append("Ошибка: Введите имя выходного файла")
            return
        self.parse_button.setEnabled(False)
        self.status_output.append("Парсинг начат...")
        progress_handler = ProgressHandler()
        await self.run_parsing(query, max_products, output_file, progress_handler)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Для кроссплатформенной совместимости
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = ParserApp()
    window.show()
    with loop:
        loop.run_forever()