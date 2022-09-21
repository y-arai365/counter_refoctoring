import os
import tkinter as tk
import tkinter.ttk as ttk

from error_window_create import ErrorMessage
from control import Control


class OutputExcel(tk.Frame):
    """
    エクセル出力するためのクラス
    管理Noを受け取ってエクセルに出力する
    """
    def __init__(self, master=None, control=None):
        super().__init__()
        self.master = master
        if control is None:
            control = Control()
        self.control = control
        self.master.geometry("500x300+300+200")
        self.master.title(u"エクセル出力")
        # self.master.attributes('-topmost', True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # self.master.grab_set()
        self.create_widgets()

    def on_close(self):
        """
        ウィンドウを閉じる
        """
        self.master.destroy()

    def create_widgets(self):
        # 管理番号を入力するエントリー
        control_l_name = ttk.Label(self.master, text=u"管理No(1) (例: 180-100)")
        control_l_name.place(x=30, y=50)
        self.control_left = tk.StringVar()
        control_l_box = ttk.Entry(self.master, textvariable=self.control_left, width=20)
        control_l_box.place(x=30, y=80)

        # 管理番号を入力するエントリー
        control_r_name = ttk.Label(self.master, text=u"管理No(2) (例: 180-101)")
        control_r_name.place(x=280, y=50)
        self.control_right = tk.StringVar()
        control_r_box = ttk.Entry(self.master, textvariable=self.control_right, width=20)
        control_r_box.place(x=280, y=80)

        # 出力先を入力するエントリー
        output_dir_name = ttk.Label(self.master, text=u"保存するファイル名  (例: C:/Users/〇/○○/excel_file.xlsx)")
        output_dir_name.place(x=30, y=130)
        # 保存するファイル名を表示するエントリー(手打ち入力も可能)
        self.output_name = tk.StringVar()
        output_dir_entry = ttk.Entry(self.master, textvariable=self.output_name, width=35)
        output_dir_entry.place(x=30, y=160)
        output_dir_select = ttk.Button(self.master, text=u"参照", width=7, command=self.set_savename)
        output_dir_select.place(x=390, y=160)

        self.output_button = ttk.Button(self.master, text=u"出 力", width=10, command=self.output)
        self.output_button.place(x=200, y=230)

    def set_savename(self):
        """
        ファイルダイアログから保存するファイル名を読み込む
        :return:
        """
        filename = self.control.output_filename(self.master)
        if filename is False:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("誤った拡張子を使用しています。\n拡張子は.xlsxにしてください。")
        else:
            self.output_name.set(filename)

    def output(self):
        """
        管理No、保存名を渡してエクセルを出力する
        :return:
        """
        control1 = self.control_left.get()
        control2 = self.control_right.get()
        savename = self.output_name.get()
        if control1 == "":
            control1 = None
        if control2 == "":
            control2 = None
        if savename == "":
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("保存するファイル名が\n入力されていません。\nファイル名を入力してください。")
        elif savename[-5:] != ".xlsx":
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("誤った拡張子を使用しています。\n拡張子は.xlsxにしてください。")
        elif control1 is None and control2 is None:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("管理Noが入力されていません。\n(1)または(2)のどちらかは\n必ず入力してください。")
            if os.path.exists(savename) is True:
                os.remove(savename)
        else:
            result = self.control.output(control1, control2, savename)
            if result == 10:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.color_change()
                error_window.title_change(u"出力完了")
                error_window.set_message("Excel出力できました。")
            elif result == 1:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("管理No(1)は存在しません。\n管理No(1)を再入力してください。")
            elif result == 2:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("管理No(2)は存在しません。\n管理No(2)を再入力してください。")
            else:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("Excel出力中にエラーが発生しました。\n入力内容を確認して\n"
                                         "再度、出力ボタンを押してください。")

