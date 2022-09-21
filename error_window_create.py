"""
エラーメッセージ表示の小ウィンドウ
"""
import tkinter as tk
import tkinter.ttk as ttk


class ErrorMessage(tk.Frame):
    """
    エラーメッセージのポップアップを表示するクラス
    インスタンス生成後、メッセージを渡すと、そのメッセージが表示される。
    通常のメッセージとして使用する場合は、color_change関数で文字を黒色に変更する
    error_text: エラーメッセージを格納するStringVar
    error_label: エラーメッセージを表示するラベル
    """
    def __init__(self, master=None):
        super().__init__()
        self.master = master
        self.master.geometry("300x200+300+200")
        self.master.title("エラー発生")
        self.master.attributes('-topmost', True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.master.grab_set()
        self.master.rowconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=2)
        self.master.columnconfigure(0, weight=1)
        self.error_text = tk.StringVar()
        self.error_label = self.create_widgets()

    def on_close(self):
        """
        ウィンドウを閉じる
        """
        self.master.destroy()

    def close_event(self, event):
        self.on_close()

    def set_message(self, text):
        """
        error_labelに表示する文字を更新する
        :param text: error_labelに表示する文字
        """
        self.error_text.set(text)

    def color_change(self):
        """
        error_labelの文字の色を変更する
        """
        self.master.title("変更完了")
        self.error_label.configure(foreground="#1e90ff")

    def title_change(self, title):
        """
        ウィンドウのタイトルを変更する
        """
        self.master.title(title)

    def create_widgets(self):
        error_frame = ttk.Frame(self.master)
        error_frame.grid(row=0, column=0, rowspan=2, columnspan=1, sticky=tk.S + tk.W + tk.N + tk.E)
        error_label = tk.Label(self.master, textvariable=self.error_text, width=29, height=5, foreground="#8b0000")
        error_label.grid(row=0, column=0)

        ok_button = ttk.Button(self.master, text="確認", width=5, command=self.on_close)
        ok_button.grid(row=1, column=0)
        ok_button.bind("<Return>", self.close_event)
        ok_button.focus_set()
        return error_label
