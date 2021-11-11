from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import TextConverter
from io import StringIO
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import *
from PyQt5 import uic, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPlainTextEdit, QWidget, QFileDialog, QPushButton
from PyQt5.QtCore import Qt
import sys
import sqlite3
import os.path

con = sqlite3.connect('e-book_db.sqlite3')


class PDFDoc:
    def __init__(self, book, path):
        self.book = book
        self.path = path
        self.am_pages = self.how_many_pages()

    def how_many_pages(self):
        # Выясняем, сколько страниц в файле
        filepath = open(self.path, 'rb')
        parser = PDFParser(filepath)
        doc = PDFDocument(parser)
        num_pages = 0
        for _ in PDFPage.create_pages(doc):
            num_pages += 1
        return num_pages

    def get_page(self, path, number):
        # Возвращаем страницу для получения из нее текста
        parser = PDFParser(path)
        doc = PDFDocument(parser)
        for num, page in enumerate(PDFPage.create_pages(doc)):
            if number == num:
                return page

    def get_text_from_page(self, page_num):
        # Получаем текст из страницы
        resource_manager = PDFResourceManager(caching=True)
        out_text = StringIO()
        params = LAParams()
        text_converter = TextConverter(resource_manager, out_text, laparams=params)
        filepath = open(self.path, 'rb')
        interpreter = PDFPageInterpreter(resource_manager, text_converter)
        page = self.get_page(path=filepath, number=page_num)
        interpreter.process_page(page)

        text = out_text.getvalue()

        filepath.close()
        text_converter.close()
        out_text.close()

        text = text.replace('\t', ' ')
        return text


class MainWindow(QMainWindow):
    # Стартовая страница приложения
    def __init__(self):
        super().__init__()
        uic.loadUi('e-book_reader.ui', self)
        self.setWindowTitle('Читалка электронных книг')
        self.prog_name_lbl.setAlignment(Qt.AlignCenter)
        self.add_new_book_btn.clicked.connect(self.open_add_book_window)
        self.choose_book_btn.clicked.connect(self.choose_book)
        self.quotes_btn.clicked.connect(self.open_quotes_window)

    def open_add_book_window(self):
        # Открываем окно добавления новой книги
        self.add_book_form = AddBookForm()
        self.add_book_form.show()

    def choose_book(self):
        # Открываем окно выбора книги
        self.choose_book_form = ChooseBookForm()
        self.choose_book_form.show()

    def open_quotes_window(self):
        # Открываем окно для поиска нужных цитат
        self.choose_quote_book_form = ChooseQuoteBook()
        self.choose_quote_book_form.show()


class AddBookForm(QWidget):
    # Окно для добавления новой книги
    def __init__(self):
        super().__init__()
        uic.loadUi('add_new_book.ui', self)
        self.setWindowTitle('Добавить новую книгу')
        self.select_dir_btn.clicked.connect(self.select_dir)
        self.back_btn.clicked.connect(self.back)
        self.ok_btn.clicked.connect(self.ok)

    def select_dir(self):
        self.path_le.setText(QFileDialog.getOpenFileName(
            self, 'Выбрать файл', '', 'PDF-файл (*pdf)')[0])

    def ok(self):
        # Проверяем, существует ли указанный путь и не пустое ли поле названия книги, после успешной проверки добавляем
        # книгу в БД
        global con
        if os.path.exists(self.path_le.text()):
            filename = self.path_le.text()
            if self.book_le.text().strip() == '':
                self.book_le.setText('Это поле должно быть заполнено')
            else:
                book = self.book_le.text()
                cur = con.cursor()
                cur.execute('''INSERT INTO Books(pdf_file_name,name,page_num) VALUES(?,?,?)''',
                            (filename, book, 0))
                con.commit()
                self.book_added_form = BookAdded()
                self.book_added_form.show()
        else:
            self.path_le.setText('Файла с таким именем не существует')

    def back(self):
        self.hide()


class BookAdded(QWidget):
    # Окно с оповещением о добавленной книге
    def __init__(self):
        super().__init__()
        uic.loadUi('book_added.ui', self)
        self.close_btn.clicked.connect(self.close)

    def close(self):
        self.hide()


class ChooseBookForm(QWidget):
    # Окно для выбора книги
    def __init__(self):
        super().__init__()
        uic.loadUi('choose_book.ui', self)
        self.setWindowTitle('Выбрать книгу')
        self.label.setAlignment(Qt.AlignCenter)
        self.back_btn.clicked.connect(self.back)
        global con
        cur = con.cursor()
        books = cur.execute('''SELECT name FROM Books''').fetchall()
        if not books:
            # Вывод лейбла о том, что книг нет в случае таковой ситуации
            self.lbl_no_books = QLabel(self)
            self.lbl_no_books.setText('Вы еще не добавили книг')
            self.lbl_no_books.move(270, 300)
            self.lbl_no_books.setFont(QtGui.QFont('Open Sans Light', 11))
        else:
            # Вывод кнопок для открытия соответствующих книг
            y = 0
            for book_name in books:
                self.btn = QPushButton(book_name[0], self)
                self.btn.resize(700, 50)
                self.btn.move(20, 70 + y)
                y += 100
                self.btn.setFont(QtGui.QFont('Open Sans Light', 11))
                self.btn.setStyleSheet('background-color: rgb(216, 248, 255);')
                self.btn.clicked.connect(self.open_book)

    def open_book(self):
        # Открытие книги
        global con
        name = self.sender().text()
        cur = con.cursor()
        pdf_file_name, page_num = cur.execute('''SELECT pdf_file_name, page_num FROM Books
                            WHERE name = ?''', (name,)).fetchone()
        self.read_book_form = Reader(pdf_file_name, name, page_num)
        self.read_book_form.show()

    def back(self):
        self.hide()


class Reader(QWidget):
    # Окно с электронной книгой
    def __init__(self, pdf_file_name, name, page_num):
        super().__init__()
        uic.loadUi('e-book_prototype.ui', self)
        self.setWindowTitle('Электронная книга')
        self.temp_doc = PDFDoc(name, pdf_file_name)
        self.text.setPlainText(self.temp_doc.get_text_from_page(page_num))
        self.text.setReadOnly(True)
        if page_num == 0:
            self.prev_page_btn.setEnabled(False)
        self.page_num = page_num + 1
        self.book_name_lbl.setText(self.temp_doc.book)
        self.book_name_lbl.setAlignment(Qt.AlignCenter)
        self.page_num_lbl.setText(str(self.page_num))
        self.page_num_lbl.setAlignment(Qt.AlignCenter)
        self.next_page_btn.clicked.connect(self.next_page)
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.back_btn.clicked.connect(self.back)
        self.add_quote_btn.clicked.connect(self.add_quote)

    def next_page(self):
        # Переход на следующую страницу
        self.page_num += 1
        if self.page_num > self.temp_doc.am_pages:
            global con
            cur = con.cursor()
            cur.execute('''UPDATE Books SET page_num = ? WHERE name = ?''',
                        (0, self.book_name_lbl.text()))
            con.commit()
            self.congrats_form = CongratulationsForm()
            self.congrats_form.show()
            self.hide()
        self.prev_page_btn.setEnabled(True)
        self.page_num_lbl.setText(str(self.page_num))
        self.text.setPlainText(self.temp_doc.get_text_from_page(self.page_num - 1))

    def prev_page(self):
        # Переход на предыдущую страницу
        self.page_num -= 1
        if self.page_num == 1:
            self.prev_page_btn.setEnabled(False)
        self.page_num_lbl.setText(str(self.page_num))
        self.text.setPlainText(self.temp_doc.get_text_from_page(self.page_num - 1))

    def add_quote(self):
        # Открытие окна с добавлением цитаты
        self.add_new_quote = AddQuoteForm(self.book_name_lbl.text())
        self.add_new_quote.show()

    def back(self):
        global con
        cur = con.cursor()
        cur.execute('''UPDATE Books SET page_num = ? WHERE name = ?''',
                    (int(self.page_num_lbl.text()) - 1, self.book_name_lbl.text()))
        con.commit()
        self.hide()


class CongratulationsForm(QWidget):
    # Оповещение о прочтении книги
    def __init__(self):
        super().__init__()
        uic.loadUi('congrats.ui', self)
        self.close_btn.clicked.connect(self.close)

    def close(self):
        self.hide()


class AddQuoteForm(QWidget):
    # Окно для добавления цитаты
    def __init__(self, book_name):
        super().__init__()
        uic.loadUi('add_new_quote.ui', self)
        self.setWindowTitle('Добавить цитату')
        self.book_name = book_name
        self.confirm_btn.clicked.connect(self.confirm)
        self.back_btn.clicked.connect(self.back)

    def confirm(self):
        # Проверка на то, что цитата не пуста, и добавление ее в БД
        if self.quote_le.text().strip() == '':
            self.quote_le.setText('Поле с цитатой не должно быть пустым')
        else:
            global con
            cur = con.cursor()
            id = cur.execute('''SELECT id FROM Books WHERE name = ?''', (self.book_name,)).fetchone()
            cur.execute('''INSERT INTO Quotes(quote,comment,book_id) VALUES (?,?,?)''',
                        (self.quote_le.text(), self.comment_le.text(), id[0]))
            con.commit()

    def back(self):
        self.hide()


class ChooseQuoteBook(QWidget):
    # Окно для выбора книги, в которой нужно найти цитаты
    def __init__(self):
        super().__init__()
        uic.loadUi('choose_quote_book.ui', self)
        self.setWindowTitle('Выбрать книгу')
        self.find_btn.clicked.connect(self.find)
        self.back_btn.clicked.connect(self.back)

    def find(self):
        text = self.book_name_le.text()
        if text.strip() == '':
            self.book_name_le.setText('Поле должно быть заполнено')
        else:
            self.quotes_menu = QuotesMenu(text)
            self.quotes_menu.show()
            self.hide()

    def back(self):
        self.hide()


class QuotesMenu(QWidget):
    # Окно с цитатами для выбранной книги
    def __init__(self, book_name):
        super().__init__()
        uic.loadUi('quotes.ui', self)
        self.setWindowTitle('Цитаты')
        self.book_name = book_name
        self.back_btn.clicked.connect(self.back)
        global con
        cur = con.cursor()
        quotes = cur.execute('''SELECT quote FROM Quotes
                    WHERE book_id = (SELECT id FROM Books WHERE name = ?)''', (self.book_name,)).fetchall()
        if not quotes:
            # Вывод лейбла о том, что цитат нет, в случае таковой ситуации
            lbl_no_quotes = QLabel(self)
            lbl_no_quotes.setText('По этому запросу ничего не найдено')
            lbl_no_quotes.move(270, 300)
            lbl_no_quotes.setFont(QtGui.QFont('Open Sans Light', 11))
        else:
            # Вывод кнопок для открытия соответствующих цитат
            lbl_quotes = QLabel(self)
            lbl_quotes.setText(f'Цитаты из книги {self.book_name}')
            lbl_quotes.move(270, 20)
            lbl_quotes.setFont(QtGui.QFont('Open Sans Light', 11))
            y = 0
            for quote in quotes:
                quote_btn = QPushButton(quote[0], self)
                quote_btn.resize(300, 50)
                quote_btn.move(200, 70 + y)
                y += 100
                quote_btn.setFont(QtGui.QFont('Open Sans Light', 11))
                quote_btn.setStyleSheet('background-color: rgb(216, 248, 255);')
                quote_btn.clicked.connect(self.open_quote)

    def open_quote(self):
        quote = self.sender().text()
        global con
        cur = con.cursor()
        comment = cur.execute('''SELECT comment FROM Quotes WHERE quote = ?''', (quote,)).fetchone()
        self.open_quote_form = OpenQuoteForm(quote, comment[0])
        self.open_quote_form.show()
        self.hide()

    def back(self):
        self.hide()


class OpenQuoteForm(QWidget):
    # Окно с выбранной цитатой
    def __init__(self, quote, comment):
        super().__init__()
        uic.loadUi('open_quote.ui', self)
        self.quote = quote
        self.comment = comment
        self.quote_le.setPlainText(quote)
        self.comment_le.setPlainText(comment)
        self.quote_le.setReadOnly(True)
        self.comment_le.setReadOnly(True)
        self.edit_btn.clicked.connect(self.edit_quote)
        self.back_btn.clicked.connect(self.back)

    def edit_quote(self):
        # Функция для редактирования цитаты
        if self.edit_btn.text() == 'Редактировать':
            self.edit_btn.setText('Подтвердить')
            self.back_btn.setText('Отмена')
            self.quote_le.setReadOnly(False)
            self.comment_le.setReadOnly(False)
        else:
            new_quote = self.quote_le.toPlainText()
            new_comment = self.comment_le.toPlainText()
            if new_quote.strip() == '':
                self.quote_le.setPlainText('Поле должно быть заполнено')
            else:
                global con
                cur = con.cursor()
                id = cur.execute('''SELECT id FROM Quotes WHERE quote = ?''',
                                 (self.quote,)).fetchone()
                self.quote = new_quote
                self.comment = new_comment
                cur.execute('''UPDATE Quotes SET quote = ?, comment = ? WHERE id = ?''',
                            (self.quote, self.comment, id[0]))
                con.commit()
                self.quote_le.setReadOnly(True)
                self.comment_le.setReadOnly(True)
                self.edit_btn.setText('Редактировать')
                self.back_btn.setText('Назад')

    def back(self):
        if self.back_btn.text() == 'Отмена':
            self.quote_le.setPlainText(self.quote)
            self.comment_le.setPlainText(self.comment)
            self.quote_le.setReadOnly(True)
            self.comment_le.setReadOnly(True)
            self.edit_btn.setText('Редактировать')
            self.back_btn.setText('Назад')
        else:
            self.hide()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.excepthook = except_hook
    sys.exit(app.exec_())