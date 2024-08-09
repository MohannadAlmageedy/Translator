import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, 
    QComboBox, QMessageBox, QHBoxLayout, QDialog, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import pyperclip
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import tempfile
import sqlite3


class TranslationThread(QThread):
    translation_done = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, text, target_language):
        super().__init__()
        self.text = text
        self.target_language = target_language

    def run(self):
        try:
            translator = GoogleTranslator(source='auto', target=self.target_language)
            translation = translator.translate(self.text)
            self.translation_done.emit(translation)
        except Exception as e:
            self.error_occurred.emit(str(e))


class SpeakThread(QThread):
    error_occurred = pyqtSignal(str)
    speak_done = pyqtSignal()  # Signal to indicate that speaking is done

    def __init__(self, text, target_language):
        super().__init__()
        self.text = text
        self.target_language = target_language

    def run(self):
        try:
            tts = gTTS(text=self.text, lang=self.target_language)
            temp_file = os.path.join(tempfile.gettempdir(), "temp_audio.mp3")
            tts.save(temp_file)
            os.system(f"start {temp_file}")
            self.speak_done.emit()  # Emit signal when done
        except Exception as e:
            self.error_occurred.emit(str(e))


class TranslatorApp(QWidget):
    def __init__(self):
        super().__init__()

        self.target_language = 'en'  # Default language
        self.initUI()
        self.createDatabase()

    def initUI(self):
        self.setWindowIcon(QIcon('images/icon.ico'))
        self.setWindowTitle('Translator App')
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        # Upper Buttons Layout (History & About)
        upperButtonsLayout = QHBoxLayout()

        self.historyButton = QPushButton('History')
        self.historyButton.setFont(QFont('Arial', 12))
        self.historyButton.clicked.connect(self.showHistory)
        upperButtonsLayout.addWidget(self.historyButton)

        self.aboutButton = QPushButton('About Us')
        self.aboutButton.setFont(QFont('Arial', 12))
        self.aboutButton.clicked.connect(self.showAbout)
        upperButtonsLayout.addWidget(self.aboutButton)

        layout.addLayout(upperButtonsLayout)

        self.label = QLabel('Enter text to translate:')
        self.label.setFont(QFont('Arial', 14))
        layout.addWidget(self.label)

        self.textEdit = QTextEdit()
        self.textEdit.setFont(QFont('Arial', 12))
        layout.addWidget(self.textEdit)

        self.translateButton = QPushButton('Translate')
        self.translateButton.setFont(QFont('Arial', 12))
        self.translateButton.clicked.connect(self.translateText)
        layout.addWidget(self.translateButton)

        self.speakButton = QPushButton('Speak Text')
        self.speakButton.setFont(QFont('Arial', 12))
        self.speakButton.clicked.connect(self.speakText)
        layout.addWidget(self.speakButton)

        self.pasteButton = QPushButton('Paste from Clipboard')
        self.pasteButton.setFont(QFont('Arial', 12))
        self.pasteButton.clicked.connect(self.pasteText)
        layout.addWidget(self.pasteButton)

        self.languageComboBox = QComboBox()
        self.languageComboBox.setFont(QFont('Arial', 12))
        languages = [
            ("English", 'en'), ("Arabic", 'ar'),("Turkish", 'tr'), ("French", 'fr'), 
            ("German", 'de'), ("Spanish", 'es'), ("Chinese (Simplified)", 'zh-cn'), 
            ("Japanese", 'ja'), ("Russian", 'ru'), ("Portuguese", 'pt'), 
            ("Italian", 'it'), ("Dutch", 'nl'), ("Korean", 'ko'), 
            ("Turkish", 'tr'), ("Swedish", 'sv'), ("Danish", 'da'), 
            ("Norwegian", 'no'), ("Finnish", 'fi'), ("Polish", 'pl'), 
            ("Czech", 'cs'), ("Hungarian", 'hu'), ("Romanian", 'ro'), 
            ("Greek", 'el'), ("Hebrew", 'he')
        ]
        for lang_name, lang_code in languages:
            self.languageComboBox.addItem(lang_name, lang_code)
        self.languageComboBox.currentIndexChanged.connect(self.changeLanguage)
        layout.addWidget(self.languageComboBox)

        self.resultLabel = QLabel('Translation:')
        self.resultLabel.setFont(QFont('Arial', 14))
        layout.addWidget(self.resultLabel)

        self.resultEdit = QTextEdit()
        self.resultEdit.setFont(QFont('Arial', 12))
        layout.addWidget(self.resultEdit)

        self.setLayout(layout)

    def createDatabase(self):
        conn = sqlite3.connect('data/translations.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT,
                translated_text TEXT,
                target_language TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def is_internet_available(self):
        try:
            requests.get('https://www.google.com', timeout=3)
            return True
        except requests.ConnectionError:
            return False

    def translateText(self):
        if not self.is_internet_available():
            QMessageBox.warning(self, "No Internet", "Please check your internet connection and try again.")
            return

        text = self.textEdit.toPlainText()
        if text:
            self.translateButton.setEnabled(False)
            self.resultEdit.setPlainText("Translating... Please wait.")
            self.translation_thread = TranslationThread(text, self.target_language)
            self.translation_thread.translation_done.connect(self.displayTranslation)
            self.translation_thread.error_occurred.connect(self.displayError)
            self.translation_thread.start()

    def displayTranslation(self, translation):
        self.resultEdit.setPlainText(translation)
        self.translateButton.setEnabled(True)
        self.saveTranslation(self.textEdit.toPlainText(), translation)

    def saveTranslation(self, original_text, translated_text):
        conn = sqlite3.connect('data/translations.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO translations (original_text, translated_text, target_language)
            VALUES (?, ?, ?)
        ''', (original_text, translated_text, self.target_language))
        conn.commit()
        conn.close()

    def displayError(self, error_message):
        QMessageBox.critical(self, "Error", f"An error occurred during translation: {error_message}")
        self.resultEdit.clear()
        self.translateButton.setEnabled(True)

    def speakText(self):
        text = self.resultEdit.toPlainText()
        if text:
            self.speakButton.setEnabled(False)
            self.speakButton.setStyleSheet("background-color: gray;")  # Change color to gray
            self.speak_thread = SpeakThread(text, self.target_language)
            self.speak_thread.speak_done.connect(self.onSpeakDone)  # Connect speak done signal
            self.speak_thread.error_occurred.connect(self.displaySpeakError)
            self.speak_thread.start()

    def onSpeakDone(self):
        self.speakButton.setEnabled(True)
        self.speakButton.setStyleSheet("")  # Reset color to default

    def displaySpeakError(self, error_message):
        QMessageBox.critical(self, "Error", f"An error occurred while speaking the text: {error_message}")
        self.speakButton.setEnabled(True)
        self.speakButton.setStyleSheet("")  # Reset color to default

    def pasteText(self):
        clipboard_text = pyperclip.paste()
        self.textEdit.setPlainText(clipboard_text)

    def changeLanguage(self):
        self.target_language = self.languageComboBox.currentData()

    def showHistory(self):
        self.historyDialog = QDialog(self)
        self.historyDialog.setWindowTitle("Translation History")
        self.historyDialog.setGeometry(100, 100, 500, 400)

        layout = QVBoxLayout()

        self.historyTable = QTableWidget()
        self.historyTable.setColumnCount(3)
        self.historyTable.setHorizontalHeaderLabels(["Original Text", "Translated Text", "Language"])
        self.historyTable.horizontalHeader().setStretchLastSection(True)
        self.historyTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.historyTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.historyTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.historyTable)

        self.loadHistory()

        deleteButton = QPushButton("Delete Selected")
        deleteButton.clicked.connect(self.deleteSelectedHistory)
        layout.addWidget(deleteButton)

        clearButton = QPushButton("Clear All")
        clearButton.clicked.connect(self.clearHistory)
        layout.addWidget(clearButton)

        self.historyDialog.setLayout(layout)
        self.historyDialog.exec_()

    def loadHistory(self):
        conn = sqlite3.connect('data/translations.db')
        cursor = conn.cursor()
        cursor.execute("SELECT original_text, translated_text, target_language FROM translations")
        records = cursor.fetchall()
        conn.close()

        self.historyTable.setRowCount(len(records))
        for i, record in enumerate(records):
            self.historyTable.setItem(i, 0, QTableWidgetItem(record[0]))
            self.historyTable.setItem(i, 1, QTableWidgetItem(record[1]))
            self.historyTable.setItem(i, 2, QTableWidgetItem(record[2]))

    def deleteSelectedHistory(self):
        selectedRows = self.historyTable.selectionModel().selectedRows()
        if selectedRows:
            conn = sqlite3.connect('data/translations.db')
            cursor = conn.cursor()

            for row in selectedRows:
                original_text = self.historyTable.item(row.row(), 0).text()
                cursor.execute("DELETE FROM translations WHERE original_text = ?", (original_text,))
            
            conn.commit()
            conn.close()
            self.loadHistory()

    def clearHistory(self):
        reply = QMessageBox.question(self, 'Clear All', 'Are you sure you want to clear all history?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect('data/translations.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM translations")
            conn.commit()
            conn.close()
            self.loadHistory()

    def showAbout(self):
        aboutDialog = QDialog(self)
        aboutDialog.setWindowTitle("About Us")
        aboutDialog.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        # Add a logo or image at the top (Optional)
        logoLabel = QLabel()
        pixmap = QPixmap('images/logo.png')  # Assuming you have a logo.png file
        scaledPixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logoLabel.setPixmap(scaledPixmap)
        logoLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(logoLabel)

        # Add the main developer information
        aboutLabel = QLabel("Developed by: <b><font color='#2E86C1'>Mohannad Almageedy</font></b>")
        aboutLabel.setFont(QFont('Arial', 14))
        aboutLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(aboutLabel)

        # Add the email contact
        emailLabel = QLabel("<a href='mailto:mohannadalmageedy013@gmail.com'>mohannadalmageedy013@gmail.com</a>")
        emailLabel.setFont(QFont('Arial', 12))
        emailLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        emailLabel.setOpenExternalLinks(True)
        emailLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(emailLabel)

        # Add a feedback message
        feedbackLabel = QLabel(
            "Do you have any feedback or suggestions for improving this program?<br>"
            "Feel free to contact us at the email address above."
        )
        feedbackLabel.setFont(QFont('Arial', 12))
        feedbackLabel.setAlignment(Qt.AlignCenter)
        feedbackLabel.setWordWrap(True)
        layout.addWidget(feedbackLabel)

        aboutDialog.setLayout(layout)
        aboutDialog.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    translatorApp = TranslatorApp()
    translatorApp.show()
    sys.exit(app.exec_())
