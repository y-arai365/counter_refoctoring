import datetime
import os
import tkinter as tk
import tkinter.ttk as ttk
import webbrowser

from error_window_create import ErrorMessage
from control import Control

dir_for_html = "count\\report\\"  # カレントディレクトリに対するHTMLの保存先


class OutputHtml(tk.Frame):
    """
    エクセル出力するためのクラス
    管理Noを受け取ってエクセルに出力する
    """
    def __init__(self, master=None, control=None):
        date = datetime.datetime.now()
        self.date = date.strftime("%Y%m%d")
        self.current_dir = os.getcwd()
        super().__init__()
        self.master = master
        self.loop = True
        if control is None:
            control = Control()
        self.control = control
        self.master.geometry("500x300+300+200")
        self.master.title(u"HTML出力")
        self.master.resizable(width=False, height=False)  # ウィンドウサイズの変更を受け付けない
        # self.master.attributes('-topmost', True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # self.master.grab_set()
        self.create_widgets()
        self.output_dir_entry.after(1, self.get_control_number())

    def on_close(self):
        """
        ウィンドウを閉じる
        """
        self.master.destroy()
        self.stop_loop()

    def create_widgets(self):
        # 管理番号を入力するエントリー
        control_l_name = ttk.Label(self.master, text=u"管理No \r(例: 180-100)")
        control_l_name.place(x=30, y=30)
        self.control_left = tk.StringVar()
        self.control_l_box = ttk.Entry(self.master, textvariable=self.control_left, width=28)
        self.control_l_box.place(x=170, y=30)

        # ロット番号を入力するエントリー
        lot_no_name = ttk.Label(self.master, text=u"Lot No")
        lot_no_name.place(x=30, y=90)
        self.lot_no = tk.StringVar()
        lot_no_box = ttk.Entry(self.master, textvariable=self.lot_no, width=28)
        lot_no_box.place(x=170, y=90)

        # 出力先を入力するエントリー
        output_dir_name = ttk.Label(self.master, text=u"保存するファイル名(例: C:\\Users\\〇\\○○\\name.html)")
        output_dir_name.place(x=30, y=150)
        # 保存するファイル名を表示するエントリー(手打ち入力も可能)
        # まずフレームを配置し、ファイル名を表示するエントリーとスクロールバーを配置
        self.path_frame = ttk.Frame(self.master, width=40)
        self.path_frame.place(x=30, y=185)
        self.scrollbar = ttk.Scrollbar(self.path_frame, orient="horizontal")
        self.output_name = tk.StringVar()
        # エントリーは入力禁止に。管理番号を読み込むか、参照からファイル名を読み込む。
        self.output_dir_entry = ttk.Entry(self.path_frame, textvariable=self.output_name, width=35, state="readonly",
                                          xscrollcommand=self.scrollbar.set)
        self.output_dir_entry.focus()
        self.output_dir_entry.pack(side="top", fill="x")
        self.scrollbar.pack(fill="x")
        self.scrollbar.configure(command=self.output_dir_entry.xview)
        # ファイルダイアログ呼び出し。
        output_dir_select = ttk.Button(self.master, text=u"参照", width=7, command=self.set_savename)
        output_dir_select.place(x=390, y=185)
        # output_nameを読み、ファイルを保存
        self.output_button = ttk.Button(self.master, text=u"出 力", width=10, command=self.output)
        self.output_button.place(x=150, y=250)
        # output_nameを読み、ファイルを開く
        self.open_button = ttk.Button(self.master, text=u"開 く", width=10, command=self.open_html)
        self.open_button.place(x=250, y=250)

    def open_html(self):
        """
        保存したHTMLをすぐその場で開ける。
        output_nameを読んでファイルを開く。
        存在しない場合はエラーウィンドウ。
        """
        path = self.output_name.get()
        print(path)
        if os.path.exists(path):
            webbrowser.open(path)
        else:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("ファイルが存在しません。")

    def stop_loop(self):
        """
        get_control_numberのafterによるループを止める
        """
        if self.loop is not None:
            self.after_cancel(self.loop)
            self.loop = None

    def get_control_number(self):
        """
        カレントディレクトリ、保存先のディレクトリ、8ケタの日付、ハイフン、管理番号、拡張子をjoinし、output_nameに代入。
        管理番号をリアルタイムで反映させるため、afterでループ。
        """
        focus = self.master.focus_get()
        if focus == self.control_l_box:
            file_path = os.path.join(self.current_dir, dir_for_html,
                                     self.date + "-" + self.control_left.get() + ".html")
            self.output_name.set(file_path)
            self.loop = self.after(1, self.get_control_number)
        else:
            self.loop = self.after(1, self.get_control_number)

    def set_savename(self):
        """
        ファイルダイアログから保存するファイル名を読み込む
        :return:
        """
        filename = self.control.output_filename(self.master)
        print(filename)
        if filename is False:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("誤った拡張子を使用しています。\n拡張子はhtmlにしてください。")
        elif filename == "":  # 参照をキャンセルした場合
            file_path = os.path.join(self.current_dir, dir_for_html,
                                     self.date + "-" + self.control_left.get() + ".html")
            self.output_name.set(file_path)
            self.loop = self.after(1, self.get_control_number)
        else:  # 参照からoutput_nameを読む際はget_control_numberのループを止める。
            filename = filename.replace("/", "\\")
            self.output_name.set(filename)

    def output(self):
        """
        管理No、LotNo、保存名を渡してHTMLを出力する
        :return:
        """
        control = self.control_left.get()
        lot_No = self.lot_no.get()
        save_name = self.output_name.get()
        if control == "":
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("管理Noが入力されていません。\n必ず入力してください。")
        elif save_name == "":
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("保存するファイル名が\n入力されていません。\nファイル名を入力してください。")
        elif save_name[-5:] != ".html":
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("誤った拡張子を使用しています。\n拡張子は.htmlにしてください。")
        else:
            result = self.control.output(control, lot_No, save_name)
            if result == 10:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.color_change()
                error_window.title_change(u"出力完了")
                error_window.set_message("HTML出力できました。")
            elif result == 1:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("管理Noは存在しません。\n管理Noを再入力してください。")
            else:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("HTML出力中にエラーが発生しました。\n入力内容を確認して\n"
                                         "再度、出力ボタンを押してください。")
