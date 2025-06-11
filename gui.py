import sys
import asyncio
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog
from PyQt5.QtCore import Qt, QObject
from PyQt5 import QtGui
import qasync
from main import main
from utils.logger import setup_logger

logger = setup_logger(log_file="gui.log")


class StatusOutputHandler(logging.Handler):
    """Кастомный обработчик логов для вывода сообщений в QTextEdit."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        QApplication.processEvents()
        self.text_widget.append(msg)


class ProgressHandler(QObject):
    """Заглушка для совместимости с main.py."""

    def __init__(self):
        super().__init__()
        logger.debug("ProgressHandler initialized")

    def update(self, n=1):
        logger.debug(f"ProgressHandler update called with n={n}")
        pass

    def set_total(self, total):
        logger.debug(f"ProgressHandler set_total called with total={total}")
        pass

    def __call__(self, progress):
        logger.debug(f"ProgressHandler called with progress={progress}")
        pass


class ParserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing ParserApp")
        try:
            self.initUI()
            ozon_logger = logging.getLogger("OzonParser")
            status_handler = StatusOutputHandler(self.status_output)
            status_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"))
            ozon_logger.addHandler(status_handler)
            logger.info("ParserApp UI initialized successfully")
        except Exception as e:
            logger.error(
                f"Error initializing ParserApp UI: {str(e)}", exc_info=True)
            raise

    def initUI(self):
        logger.debug("Setting up UI components")
        self.setWindowTitle("Парсер Ozon")
        self.setGeometry(100, 100, 500, 650)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #E2E8F0, stop:1 #CBD5E1);
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

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

        self.max_products_label = QLabel("Количество товаров (0 для всех):")
        self.max_products_label.setStyleSheet("""
            font-size: 14px; 
            color: #334155; 
            font-family: 'Arial', sans-serif;
        """)
        self.max_products_input = QLineEdit("50")
        self.max_products_input.setValidator(
            QtGui.QIntValidator(0, 100000))  # Разрешаем 0
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
        logger.debug("UI components setup completed")

    def browse_file(self):
        logger.info("Opening file dialog for output file selection")
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Выберите файл для сохранения", "", "Excel Files (*.xlsx);;All Files (*)"
            )
            if file_path:
                self.output_file_input.setText(file_path)
                logger.info(f"Selected output file: {file_path}")
            else:
                logger.debug("File dialog cancelled")
        except Exception as e:
            logger.error(f"Error in browse_file: {str(e)}", exc_info=True)
            self.status_output.append(f"Ошибка при выборе файла: {str(e)}")

    async def run_parsing(self, query, max_products, output_file, progress_handler):
        logger.info(
            f"Starting parsing with query='{query}', max_products={max_products}, output_file='{output_file}'")
        try:
            await main(query, max_products, output_file, progress_handler)
            self.status_output.append(
                f"Парсинг завершён. Файл сохранён: {output_file}")
            logger.info(
                f"Parsing completed successfully, file saved: {output_file}")
        except Exception as e:
            logger.error(f"Error during parsing: {str(e)}", exc_info=True)
            self.status_output.append(f"Ошибка при парсинге: {str(e)}")
        finally:
            self.parse_button.setEnabled(True)
            logger.debug("Parse button re-enabled")

    @qasync.asyncSlot()
    async def start_parsing(self):
        logger.info("Start parsing button clicked")
        try:
            query = self.query_input.text().strip()
            if not query:
                self.status_output.append("Ошибка: Введите поисковый запрос")
                logger.warning("Empty query provided")
                return
            try:
                max_products = int(self.max_products_input.text())
                logger.debug(f"Max products set to: {max_products}")
            except ValueError:
                self.status_output.append(
                    "Ошибка: Введите корректное число для количества товаров")
                logger.warning("Invalid max_products value provided")
                return
            output_file = self.output_file_input.text().strip()
            if not output_file:
                self.status_output.append(
                    "Ошибка: Введите имя выходного файла")
                logger.warning("Empty output file name provided")
                return
            self.parse_button.setEnabled(False)
            logger.debug("Parse button disabled")
            self.status_output.append("Парсинг начат...")
            progress_handler = ProgressHandler()
            await self.run_parsing(query, max_products, output_file, progress_handler)
        except Exception as e:
            logger.error(f"Error in start_parsing: {str(e)}", exc_info=True)
            self.status_output.append(f"Ошибка: {str(e)}")
            self.parse_button.setEnabled(True)
            logger.debug("Parse button re-enabled after error")


if __name__ == "__main__":
    logger.info("Starting QApplication")
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        window = ParserApp()
        window.show()
        logger.info("Application window shown")
        with loop:
            loop.run_forever()
    except Exception as e:
        logger.error(
            f"Error in main application loop: {str(e)}", exc_info=True)
        raise
