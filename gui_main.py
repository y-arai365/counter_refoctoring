from datetime import datetime
import multiprocessing
from pathlib import Path
import pickle
import subprocess
import sys
import tkinter as tk
import tkinter.font as font
import tkinter.ttk as ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

import dfk4tk

from control import Control
from error_window_create import ErrorMessage
from translate_word import translate_word

import registration_window
import output_html_window
import settings_window


class MainWindow(tk.Tk):
    def __init__(self, window_title=u"個数カウントシステム", icon_file="icon.ico"):
        self.control = Control()  # コントロールオブジェクトの作成
        self.control.main_window = self
        now = datetime.now()  # 現在の時刻を取得
        str_now = "{0:%Y_%m_%d_%H_%M}".format(now)
        self.first_width = 640
        self.first_height = 457
        self.magnif = 1  # ウィンドウサイズの倍率
        self.product_names = self.control.product_names
        self.prev_count_date = None
        self.wheel_num = 0
        self.method_num = 0

        self.cam_num = 0
        self.cap = dfk4tk.VideoCapture4DFK(self.cam_num)   # カメラを呼び出す
        self.cam_flag = True  # 動画を動かすかどうかの設定
        self.dialog = False  # ファイルダイアログを使用しているかどうかの設定
        self.count_flag = False  # 表示画像がカウント結果になっているかどうかの設定
        self.setting_flag = False  # 設定ウィンドウを開いているかどうかの設定
        self.is_count = 0
        self.prev_zoom_magnif = 1
        self.min_get = False

        super(MainWindow, self).__init__()  # self = tk.tk()
        self.title(window_title)
        self.geometry("1280x800+100+100")  # ウィンドウの表示サイズ、表示位置
        self.minsize(1080, 720)  # ウィンドウサイズの最小値
        # exeファイルに一体化したアイコンを読み込む
        if getattr(sys, 'frozen', False):
            APPLICATION_PATH = sys._MEIPASS
        else:
            APPLICATION_PATH = str(Path(__file__).parent)

        icon_file = Path(APPLICATION_PATH, icon_file)

        self.iconbitmap(default=icon_file)
        self.prev_win_width = 0
        self.prev_win_height = 0

        self.my_font = font.Font(self, family="メイリオ", size=11)  # 通常使用フォント
        self.my_font_big = font.Font(self, family="メイリオ", size=18)  # 大き目フォント
        self.my_font_small = font.Font(self, family="メイリオ", size=9)  # 小さめフォント

        self.option_add("*Font", self.my_font)  # 基本ウィジェットのフォントはmy_fontに設定

        # ウィンドウ内の領域を縦2、横2に分割する
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=12)

        self.style_setting()  # ttkオブジェクトのスタイルを適用
        self.create_menubar()  # メニューバーの作成
        self.create_widgets()  # ウィジェットの作成

        self.delay = 15  # カメラを更新する頻度(ms)
        self.update_cam()  # カメラを更新する関数

        self.protocol("WM_DELETE_WINDOW", self.on_close)  # ウィンドウを閉じるときに関数を設定

        if self.cap.isOpened() is False:  # カメラが接続できなかった場合
            sub_win = tk.Toplevel()  # エラー表示用のウィンドウを作成
            error_window = ErrorMessage(sub_win)
            error_window.set_message("カメラとの接続に問題があります。\n他のソフトがカメラを利用していないか\n"
                                     "カメラが接続されているかどうか\n確認してください。")

        self.bind("<Configure>", self.window_size)
        self.mainloop()
        self.cap.release()  # カメラのリリース

        self._camera_loop_id = None

    def on_close(self):
        """
        ウィンドウを閉じる
        """
        if self.count_flag is True:
            sub_win = tk.Toplevel()  # エラー表示用のウィンドウを作成
            error_window = ErrorMessage(sub_win)
            error_window.set_message("結果が保存されていません。\n製品情報の下にある\n"
                                     "確認ボタンを押してから\nウィンドウを閉じてください。")
        else:
            self.destroy()
            self.quit()

    def create_menubar(self):
        """
        メニューバーの作成
        """
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)
        # tearoff=Falseでメニューバーからファイルの選択の子要素を切り離せないように設定
        self.filedialog = tk.Menu(self.menubar, tearoff=False)
        soft_info = tk.Menu(self.menubar, tearoff=False)

        self.menubar.add_cascade(label=u"製品名登録", command=self.start_regi)
        self.menubar.add_cascade(label=u"ファイルの選択", menu=self.filedialog)
        self.menubar.add_cascade(label=u"設定", command=self.start_settings)
        self.menubar.add_cascade(label=u"カメラリフレッシュ", command=self.cam_refresh)
        self.menubar.add_cascade(label=u"HTML出力", command=self.start_output)
        self.menubar.add_cascade(label=u"ソフト情報", menu=soft_info)
        self.menubar.add_cascade(label=u"終了", command=self.on_close)

        # ファイルの選択の子要素としてファイル参照と動画に戻るを追加
        self.filedialog.add_command(label=u"ファイル参照", command=self.file_open)
        self.filedialog.add_command(label=u"動画に戻る", command=self.ok_open)

        # バージョン情報
        soft_info.add_command(label=u"バージョン 2.6.0-hls")
        soft_info.add_command(label=u"バージョン情報確認", command=self.open_readme)

        # 動画表示中は動画に戻るは押すことができないように設定
        self.filedialog.entryconfig("動画に戻る", state="disabled")

    def open_readme(self):
        try:
            command = ["notepad.exe", "README.md"]
            subprocess.Popen(command)
        except:
            pass

    def style_setting(self):
        style = ttk.Style()  # ttkオブジェクトのスタイル作成
        try:
            style.theme_use("vista")  # スタイルにvistaが存在しなければttkのデフォルトのものを使用
        except:
            pass
        finally:
            # それぞれウィジェットのスタイルに設定値を追加
            style.configure("R.TFrame")
            style.configure("R.TLabel")
            style.configure("TRadiobutton", font=self.my_font)
            style.configure("R.TRadiobutton", font=self.my_font)
            style.configure("TButton", font=self.my_font, anchor=tk.S + tk.W + tk.N + tk.E)
            style.configure("R.TButton", font=self.my_font, anchor=tk.S + tk.W + tk.N + tk.E)
            style.configure("Count.TButton", font=self.my_font, foreground="#8b0000", anchor=tk.S + tk.W + tk.N + tk.E)
            style.configure("R.TCheckbutton", font=self.my_font)
            style.configure("TEntry", font=self.my_font)
            style.configure("TCombobox", font=self.my_font)
            style.configure("TNotebook", font=self.my_font)
            style.configure("Test.TFrame", background="black")

    def create_widgets(self):
        # 背景フレーム
        root_frame = tk.Frame(self, borderwidth=2, relief="groove")
        root_frame.grid(row=0, column=0, rowspan=2, columnspan=2, sticky=tk.S + tk.W + tk.N + tk.E)

        # 結果画像(又はファイルの選択で選ばれた画像)を表示するフレーム
        self.result = ttk.Frame(self)
        self.result.grid(column=0, row=1)
        self.result_img = ttk.Label(self.result)
        self.result_img.pack()
        self.result_img.bind("<MouseWheel>", self.mousewheel)  # 結果画像上でマウスホイールを動かすと呼び出す
        self.result_img.bind("<Button-1>", self.get_xy)  # 結果画像上でマウス左ボタンを押すと呼び出す
        self.result_img.bind("<Motion>", self.drag_img)  # 結果画像上でマウス左ボタンを離すと呼び出す
        self.result_img.bind("<ButtonRelease-1>", self.release_img)

        # 映像を表示するフレーム
        self.video = ttk.Frame(self)
        self.video.grid(column=0, row=1)
        self.video_img = ttk.Label(self.video)
        self.video_img.pack()

        # 右側のメニュー部分を内包するフレーム
        self.count_frame = tk.Frame(self, relief="groove", borderwidth=2)
        self.count_frame.grid(row=0, column=1, rowspan=2, columnspan=1, sticky=tk.S + tk.W + tk.N + tk.E)
        self.count_frame.grid_columnconfigure(0, weight=1)
        self.count_frame.grid_rowconfigure(0, weight=2)
        self.count_frame.grid_rowconfigure(1, weight=8)
        self.count_frame.grid_rowconfigure(2, weight=3)

        # 作業者に関するフレーム
        self.worker_frame = tk.Frame(self.count_frame)
        # paddingを持たせて上下左右に余白を作る
        self.worker_frame.grid(row=0, column=0, rowspan=1, columnspan=1, sticky=tk.S + tk.W + tk.N + tk.E,
                               padx=30, pady=10)

        worker_n = tk.LabelFrame(self.worker_frame, text="作業者情報", width=380, height=85, font=self.my_font_small,
                                 relief="groove", borderwidth=2)
        worker_n.place(x=0, y=0)

        # ラベルフレーム内にウィジェットを配置
        w_name = ttk.Label(worker_n, text="作業者名：")
        w_name.place(x=30, y=10)
        self.worker = tk.StringVar()  # エントリーにセットする可変のstring変数
        worker_box = ttk.Entry(worker_n, textvariable=self.worker, width=25)
        worker_box.place(x=120, y=10)
        worker_box.focus_set()
        worker_box.bind("<KeyRelease-Tab>", self.focus_sheet)

        method_frame = ttk.Frame(self.count_frame)
        method_frame.grid(row=1, column=0, rowspan=1, columnspan=1, sticky=tk.N+tk.S+tk.W+tk.E, padx=30)

        self.method_note = ttk.Notebook(method_frame, width=377, height=415)
        self.method_note.place(x=0, y=0)
        self.method_note.bind("<<NotebookTabChanged>>", self.tabchange)

        # マッチングの製品選択に関するフレーム ##############################################################################
        select_frame = tk.Frame(self.method_note)
        select_frame.place(x=0, y=0)
        self.method_note.add(select_frame, text="パターン検出")
        # ラベルフレーム内にウィジェットを配置
        product_f = tk.LabelFrame(select_frame, text=u"製品情報", width=355, height=375, font=self.my_font_small,
                                  relief="groove", borderwidth=2)
        product_f.place(x=10, y=0)

        self.var_product = tk.IntVar()  # ラジオボタンにセットする可変のint変数
        self.var_product.set(0)
        check1_product = ttk.Radiobutton(product_f, text="新規", variable=self.var_product, value=0,
                                         command=self.start_or_open)
        check1_product.place(x=15, y=5)
        # ラジオボタンをエンターキーで選択できるように関数をバインド
        check1_product.bind("<Return>", lambda event, product_num=0: self.radiobutton_enter(product_num))
        check2_product = ttk.Radiobutton(product_f, text="開く", variable=self.var_product, value=1,
                                         command=self.start_or_open)
        check2_product.place(x=175, y=5)
        # エンター選択の関数をバインド
        check2_product.bind("<Return>", lambda event, product_num=1: self.radiobutton_enter(product_num))

        date_index = ttk.Label(product_f, text=u"日時:")
        date_index.place(x=15, y=40)
        self.date = tk.StringVar()  # ラベルにセットする可変のstring変数
        date_name = ttk.Label(product_f, textvariable=self.date, width=25)
        date_name.place(x=105, y=40)

        pattern_name = ttk.Label(product_f, text=u"製品名:")
        pattern_name.place(x=15, y=75)
        self.product = tk.StringVar()  # コンボボックスにセットする可変のstring変数
        self.product.set(self.product_names[0])  # 変数の初期値をセット
        # コンボボックスを作成 文字の打ち込みは不可
        self.product_box = ttk.Combobox(product_f, textvariable=self.product, width=23, state="readonly")
        self.product_box.bind("<<ComboboxSelected>>", self.select_pattern)  # コンボボックスを選択した時にselect_pattern開始
        product_names_t = tuple(self.product_names)  # リストをタプルに変換
        self.product_box["values"] = product_names_t  # コンボボックスの中身を設定
        self.product_box.place(x=105, y=75)

        figure_no_index = ttk.Label(product_f, text=u"製品図番:")
        figure_no_index.place(x=15, y=110)
        self.figure_no_str = tk.StringVar()  # ラベルにセットする可変のstring変数
        figure_no_name = ttk.Label(product_f, textvariable=self.figure_no_str, width=25)
        figure_no_name.place(x=105, y=110)

        pattern_name = ttk.Label(product_f, text=u"パターン画像:")
        pattern_name.place(x=15, y=145)

        pattern_frame = ttk.Frame(product_f, height=30)
        pattern_frame.place(x=145, y=138)

        pattern = ttk.Frame(pattern_frame, height=50)  # パターン画像を貼り付けるフレーム
        pattern.pack()
        self.pattern_img = ttk.Label(pattern)
        self.pattern_img.pack()

        theoretical_amount_index = ttk.Label(product_f, text=u"理論数量:")
        theoretical_amount_index.place(x=15, y=180)
        self.theoretical_amount_str = tk.StringVar()  # ラベルにセットする可変のstring関数
        theoretical_amount_name = ttk.Label(product_f, textvariable=self.theoretical_amount_str, width=25)
        theoretical_amount_name.place(x=105, y=180)

        yield_rate_label = ttk.Label(product_f, text="許容歩留率：")
        yield_rate_label.place(x=15, y=210)
        self.yield_rate_str = tk.StringVar()
        self.yield_rate_str.set("50.0")
        yield_rate_value_label = ttk.Label(product_f, textvariable=self.yield_rate_str, width=15)
        yield_rate_value_label.place(x=185, y=210)
        yield_rate_unit_lavel = ttk.Label(product_f, text="%")
        yield_rate_unit_lavel.place(x=310, y=210)

        matching_threshold_index = ttk.Label(product_f, text=u"マッチングの閾値:")
        matching_threshold_index.place(x=15, y=240)
        self.matching_threshold_str = tk.StringVar()  # ラベルにセットする可変のstring関数
        matching_threshold_name = ttk.Label(product_f, textvariable=self.matching_threshold_str, width=15)
        matching_threshold_name.place(x=185, y=240)

        control_no_index = ttk.Label(product_f, text=u"管理No:")
        control_no_index.place(x=15, y=275)
        self.control_no_str = tk.StringVar()  # エントリーにセットする可変のstring関数
        control_no_name = ttk.Entry(product_f, textvariable=self.control_no_str, width=25)
        control_no_name.place(x=105, y=273)

        sheet_no_index = ttk.Label(product_f, text=u"シートNo:")
        sheet_no_index.place(x=15, y=315)

        # MARUWA用。「上中下無」を選択するコンボボックスがあったが、削除。
        # 他の変更を最小限にするため、値を格納した変数はそのまま。初期値だけセットし変更されない。
        self.sheet_select = tk.StringVar()  # コンボボックスにセットする可変のstring関数
        self.sheet_select.set("上")  # 変数の初期値をセット

        self.sheet_no_str = tk.StringVar()  # エントリーにセットする可変のstring関数
        self.sheet_no_name = ttk.Entry(product_f, textvariable=self.sheet_no_str, width=12)
        self.sheet_no_name.place(x=220, y=315)
        # エンターキーでカウントスタート/確認ができるようにバインド
        self.sheet_no_name.bind("<Return>", self.count_bind)
        # キーボードの上下矢印キーで数値が変更できるように関数をバインド
        self.sheet_no_name.bind("<Up>",
                                lambda event, strvar=self.sheet_no_str, num=1: self.up_or_down(strvar, num, 1))
        self.sheet_no_name.bind("<Down>",
                                lambda event, strvar=self.sheet_no_str, num=-1: self.up_or_down(strvar, num, 1))

        # ボタンを格納する領域
        detect_frame = ttk.Frame(select_frame, width=400, height=100)
        detect_frame.place(x=0, y=380)

        # ボタンを格納するフレーム
        detect_f = ttk.Frame(detect_frame, width=353, height=30)
        detect_f.place(x=10, y=0)

        # 開くから表示したときにあらわれるボタンを格納
        self.count_check_frame = ttk.Frame(detect_f, width=353, height=30)
        self.count_check_frame.place(x=0, y=0)

        # 開くから表示したときにあらわれるボタン
        self.prev_ok = ttk.Button(self.count_check_frame, text="確認", command=self.ok_open)
        self.prev_ok.place(relwidth=0.245, relheight=1.0, relx=0, rely=0)
        self.prev_change_button = ttk.Button(self.count_check_frame, text="変更",
                                             command=self.update_prev_count)
        self.prev_change_button.place(relwidth=0.24, relheight=1.0, relx=0.255, rely=0)
        self.prev_delete_button = ttk.Button(self.count_check_frame, text="削除",
                                             command=self.delete_prev_count)
        self.prev_delete_button.place(relwidth=0.24, relheight=1.0, relx=0.505, rely=0)

        self.prev_print_button = ttk.Button(self.count_check_frame, text="印刷", command=self.output_sheet_result)
        self.prev_print_button.place(relwidth=0.245, relheight=1.0, relx=0.755, rely=0)

        # # 新規から表示したときに現れるボタンを格納
        self.count_confirm_frame = ttk.Frame(detect_f, width=353, height=30)
        self.count_confirm_frame.place(x=0, y=0)

        # 新規から表示したときにあらわれるボタン
        self.count_ok = ttk.Button(self.count_confirm_frame, text="確認", command=self.ok_new)
        self.count_ok.place(relwidth=0.745, relheight=1.0, relx=0, rely=0)

        self.print_button = ttk.Button(self.count_confirm_frame, text="印刷", command=self.output_sheet_result)
        self.print_button.place(relwidth=0.245, relheight=1.0, relx=0.755, rely=0)

        self.count_button_text = tk.StringVar()  # ボタン上のテキストにセットする可変のstring変数
        self.count_button_text.set(u"スタート")  # 初期値を設定
        self.count_button = ttk.Button(detect_f, textvariable=self.count_button_text, command=self.count)
        self.count_button.bind("<Button-1>", self.count_bind)
        self.count_button.place(relwidth=1, relheight=1, relx=0, rely=0)
        self.count_button.bind("<KeyRelease-Tab>", self.focus_detect)

        # 輪郭検出の製品情報入力 ##########################################################################################
        contours_frame = ttk.Frame(self.method_note)
        contours_frame.place(x=0, y=0)
        self.method_note.add(contours_frame, text="輪郭検出")

        # ラベルフレーム内にウィジェットを配置
        product_f_cnt = tk.LabelFrame(contours_frame, text=u"製品情報", width=355, height=375, font=self.my_font_small,
                                      relief="groove", borderwidth=2)
        product_f_cnt.place(x=10, y=0)

        self.var_product_cnt = tk.IntVar()  # ラジオボタンにセットする可変のint変数
        self.var_product_cnt.set(0)
        check1_product_cnt = ttk.Radiobutton(product_f_cnt, text="新規", variable=self.var_product_cnt, value=0,
                                             command=self.start_or_open)
        check1_product_cnt.place(x=15, y=5)
        # ラジオボタンをエンターキーで選択できるように関数をバインド
        check1_product_cnt.bind("<Return>",
                                lambda event, product_num=0: self.radiobutton_enter(product_num))
        check2_product_cnt = ttk.Radiobutton(product_f_cnt, text="開く", variable=self.var_product_cnt, value=1,
                                             command=self.start_or_open)
        check2_product_cnt.place(x=175, y=5)
        # エンター選択の関数をバインド
        check2_product_cnt.bind("<Return>",
                                lambda event, product_num=1: self.radiobutton_enter(product_num))

        date_index_cnt = ttk.Label(product_f_cnt, text=u"日時:")
        date_index_cnt.place(x=15, y=35)
        self.date_cnt = tk.StringVar()  # ラベルにセットする可変のstring変数
        date_name_cnt = ttk.Label(product_f_cnt, textvariable=self.date_cnt, width=25)
        date_name_cnt.place(x=105, y=35)

        pattern_name_cnt = ttk.Label(product_f_cnt, text=u"製品名:")
        pattern_name_cnt.place(x=15, y=70)
        self.product_cnt = tk.StringVar()  # コンボボックスにセットする可変のstring変数
        self.product_cnt.set(self.product_names[0])  # 変数の初期値をセット
        # コンボボックスを作成 文字の打ち込みは不可
        self.product_box_cnt = ttk.Combobox(product_f_cnt, textvariable=self.product_cnt, width=23, state="readonly")
        # コンボボックスを選択した時にselect_pattern開始
        self.product_box_cnt.bind("<<ComboboxSelected>>", self.select_pattern)
        product_names_t = tuple(self.product_names)  # リストをタプルに変換
        self.product_box_cnt["values"] = product_names_t  # コンボボックスの中身を設定
        self.product_box_cnt.place(x=105, y=68)

        figure_no_index_cnt = ttk.Label(product_f_cnt, text=u"製品図番:")
        figure_no_index_cnt.place(x=15, y=100)
        self.figure_no_str_cnt = tk.StringVar()  # ラベルにセットする可変のstring変数
        figure_no_name_cnt = ttk.Label(product_f_cnt, textvariable=self.figure_no_str_cnt, width=25)
        figure_no_name_cnt.place(x=105, y=100)

        theoretical_amount_index_cnt = ttk.Label(product_f_cnt, text=u"理論数量:")
        theoretical_amount_index_cnt.place(x=15, y=130)
        self.theoretical_amount_str_cnt = tk.StringVar()  # ラベルにセットする可変のstring関数
        theoretical_amount_name_cnt = ttk.Label(product_f_cnt, textvariable=self.theoretical_amount_str_cnt, width=25)
        theoretical_amount_name_cnt.place(x=105, y=130)

        yield_rate_label_cnt = ttk.Label(product_f_cnt, text="許容歩留率：")
        yield_rate_label_cnt.place(x=15, y=160)
        self.yield_rate_str_cnt = tk.StringVar()
        self.yield_rate_str_cnt.set("54.21")
        yield_rate_value_label_cnt = ttk.Label(product_f_cnt, textvariable=self.yield_rate_str, width=15)
        yield_rate_value_label_cnt.place(x=185, y=160)
        yield_rate_unit_lavel_cnt = ttk.Label(product_f_cnt, text="%")
        yield_rate_unit_lavel_cnt.place(x=310, y=160)

        erode_index_cnt = ttk.Label(product_f_cnt, text=u"収縮量:")
        erode_index_cnt.place(x=15, y=190)
        self.erode_str_cnt = tk.StringVar()  # ラベルにセットする可変のstring関数
        erode_name_cnt = ttk.Label(product_f_cnt, textvariable=self.erode_str_cnt, width=25)
        erode_name_cnt.place(x=105, y=190)

        dilate_index_cnt = ttk.Label(product_f_cnt, text=u"膨張量:")
        dilate_index_cnt.place(x=15, y=220)
        self.dilate_str_cnt = tk.StringVar()  # ラベルにセットする可変のstring関数
        dilate_name_cnt = ttk.Label(product_f_cnt, textvariable=self.dilate_str_cnt, width=25)
        dilate_name_cnt.place(x=105, y=220)

        thresh_area_index_cnt = ttk.Label(product_f_cnt, text=u"除外面積:")
        thresh_area_index_cnt.place(x=15, y=250)
        self.thresh_area_str_cnt = tk.StringVar()  # ラベルにセットする可変のstring関数
        thresh_area_name_cnt = ttk.Label(product_f_cnt, textvariable=self.thresh_area_str_cnt, width=25)
        thresh_area_name_cnt.place(x=105, y=250)

        control_no_index_cnt = ttk.Label(product_f_cnt, text=u"管理No:")
        control_no_index_cnt.place(x=15, y=280)
        self.control_no_str_cnt = tk.StringVar()  # エントリーにセットする可変のstring関数
        control_no_name_cnt = ttk.Entry(product_f_cnt, textvariable=self.control_no_str_cnt, width=25)
        control_no_name_cnt.place(x=105, y=278)

        sheet_no_index_cnt = ttk.Label(product_f_cnt, text=u"シートNo:")
        sheet_no_index_cnt.place(x=15, y=315)

        # MARUWA用。「上中下無」を選択するコンボボックスがあったが、削除。
        # 他の変更を最小限にするため、値を格納した変数はそのまま。初期値だけセットし変更されない。
        self.sheet_select_cnt = tk.StringVar()  # コンボボックスにセットする可変のstring関数
        self.sheet_select_cnt.set("上")  # 変数の初期値をセット

        self.sheet_no_str_cnt = tk.StringVar()  # エントリーにセットする可変のstring関数
        self.sheet_no_name_cnt = ttk.Entry(product_f_cnt, textvariable=self.sheet_no_str_cnt, width=12)
        self.sheet_no_name_cnt.place(x=220, y=313)
        # エンターキーでカウントスタート/確認ができるようにバインド
        self.sheet_no_name_cnt.bind("<Return>", self.count_bind)
        # キーボードの上下矢印キーで数値が変更できるように関数をバインド
        self.sheet_no_name_cnt.bind("<Up>",
                                    lambda event, strvar=self.sheet_no_str_cnt, num=1: self.up_or_down(strvar, num, 1))
        self.sheet_no_name_cnt.bind("<Down>",
                                    lambda event, strvar=self.sheet_no_str_cnt, num=-1: self.up_or_down(strvar, num, 1))

        # ボタンを格納する領域
        detect_frame_cnt = ttk.Frame(contours_frame, width=400, height=90)
        detect_frame_cnt.place(x=0, y=380)

        # ボタンを格納するフレーム
        detect_f_cnt = ttk.Frame(detect_frame_cnt, width=353, height=30)
        detect_f_cnt.place(x=10, y=0)

        # 開くから表示したときにあらわれるボタンを格納
        self.count_check_frame_cnt = ttk.Frame(detect_f_cnt, width=353, height=30)
        self.count_check_frame_cnt.place(x=0, y=0)

        # 開くから表示したときにあらわれるボタン
        self.prev_ok_cnt = ttk.Button(self.count_check_frame_cnt, text="確認", command=self.ok_open)
        self.prev_ok_cnt.place(relwidth=0.245, relheight=1.0, relx=0, rely=0)
        self.prev_change_button_cnt = ttk.Button(self.count_check_frame_cnt, text="変更",
                                                 command=self.update_prev_count)
        self.prev_change_button_cnt.place(relwidth=0.24, relheight=1.0, relx=0.255, rely=0)
        self.prev_delete_button_cnt = ttk.Button(self.count_check_frame_cnt, text="削除",
                                                 command=self.delete_prev_count)
        self.prev_delete_button_cnt.place(relwidth=0.24, relheight=1.0, relx=0.505, rely=0)

        self.prev_print_button_cnt = ttk.Button(self.count_check_frame_cnt, text="印刷",
                                                command=self.output_sheet_result)
        self.prev_print_button_cnt.place(relwidth=0.245, relheight=1.0, relx=0.755, rely=0)

        # 新規から表示したときにあらわれるボタンを格納
        self.count_confirm_frame_cnt = ttk.Frame(detect_f_cnt, width=353, height=30)
        self.count_confirm_frame_cnt.place(x=0, y=0)

        # 新規から表示したときにあらわれるボタン
        self.count_ok_cnt = ttk.Button(self.count_confirm_frame_cnt, text="確認", width=34, command=self.ok_new)
        self.count_ok_cnt.place(relwidth=0.745, relheight=1.0, relx=0, rely=0)

        self.print_button_cnt = ttk.Button(self.count_confirm_frame_cnt, text="印刷",
                                           command=self.output_sheet_result)
        self.print_button_cnt.place(relwidth=0.245, relheight=1.0, relx=0.755, rely=0)

        self.count_button_text_cnt = tk.StringVar()  # ボタン上のテキストにセットする可変のstring変数
        self.count_button_text_cnt.set(u"スタート")  # 初期値を設定
        self.count_button_cnt = ttk.Button(detect_f_cnt, textvariable=self.count_button_text_cnt,
                                           command=self.count)
        self.count_button_cnt.place(relwidth=1, relheight=1, relx=0, rely=0)
        self.count_button_cnt.bind("<KeyRelease-Tab>", self.focus_detect)

        # ##############################################################################################################

        # 結果を表示するフレーム
        message_frame = ttk.Frame(self.count_frame)
        message_frame.grid(row=2, column=0, sticky=tk.S + tk.W + tk.N + tk.E, padx=30)

        message_f = tk.LabelFrame(message_frame, text=u"カウント結果", width=380, height=150, font=self.my_font_small,
                                  relief="groove", borderwidth=2)
        message_f.place(x=0, y=0)
        # それぞれのウィジェットを配置
        count_mes = ttk.Label(message_f, text=u"良品数：", font=self.my_font_big)
        count_mes.place(x=30, y=15)

        # それぞれラベルにセットする可変の変数を定義　初期値に0個をセット
        self.count_message = tk.StringVar()
        self.count_message.set("0個")
        self.count_result = ttk.Label(message_f, textvariable=self.count_message, font=self.my_font_big, anchor="e",
                                      width=8)
        self.count_result.place(x=215, y=15)

        f_detection_index = ttk.Label(message_f, text=u"誤検出:")
        f_detection_index.place(x=30, y=80)
        self.f_detection_str = tk.StringVar()  # エントリーにセットする可変のstring関数
        self.f_detection_str.set("0")
        self.f_detection_entry = ttk.Entry(message_f, textvariable=self.f_detection_str, width=8)
        self.f_detection_entry.place(x=95, y=80)
        # キーボードの上下矢印キーで数値が変更できるように関数をバインド
        self.f_detection_entry.bind("<Up>",
                                    lambda event, strvar=self.f_detection_str: self.detection_event(event, strvar, 0))
        self.f_detection_entry.bind("<Down>",
                                    lambda event, strvar=self.f_detection_str: self.detection_event(event, strvar, 0))
        self.f_detection_entry.bind("<Return>", self.detection_enter)

        n_detection_index = ttk.Label(message_f, text=u"未検出:")
        n_detection_index.place(x=195, y=80)
        self.n_detection_str = tk.StringVar()  # エントリーにセットする可変のstring関数
        self.n_detection_str.set("0")
        n_detection_entry = ttk.Entry(message_f, textvariable=self.n_detection_str, width=8)
        n_detection_entry.place(x=260, y=80)
        # キーボードの上下矢印キーで数値が変更できるように関数をバインド
        n_detection_entry.bind("<Up>",
                               lambda event, strvar=self.n_detection_str: self.detection_event(event, strvar, 0))
        n_detection_entry.bind("<Down>",
                               lambda event, strvar=self.n_detection_str: self.detection_event(event, strvar, 0))
        n_detection_entry.bind("<Return>", self.detection_enter)

        self.size_grip = ttk.Sizegrip(self)
        self.size_grip.grid(row=2, column=0, rowspan=1, columnspan=2, sticky=tk.S + tk.W + tk.N + tk.E)
        self.size_grip.bind("<Button-1>", self.cam_stop)
        self.size_grip.bind("<ButtonRelease-1>", self.cam_restart)

    def tabchange(self, event):
        """
        どのタブを選択しているのかによって、method_numを変更する関数
        :param event:
        :return:
        """
        selection = event.widget.select()
        tab = event.widget.tab(selection, "text")
        if tab == u"パターン検出":
            self.method_num = 0
        elif tab == u"輪郭検出":
            self.method_num = 1

        self.select_pattern(None)

    def mousewheel(self, event):
        """
        マウスホイールで画像を拡大する関数
        :param event:
        :return:
        """
        # マウスホイールイベントを取得する
        if event.delta:
            x = event.x
            y = event.y
            # マウスホイールは120ごとに数字が区切られているので、回転した量を数値化する
            self.wheel_num += (event.delta / 120)  # event.deltaがマウスホイールの値
            # 1倍から6倍までの拡大ができるとする(wheel_num=0のとき1倍、wheel_num=50のとき6倍)
            if 0 < self.wheel_num < 50:
                zoom_magnif = (self.wheel_num * 0.1 + 1)  # 画像の拡大倍率
                new_x = int(self.width * zoom_magnif)  # 画像の幅
                new_y = int(self.height * zoom_magnif)  # 画像の高さ
                img_zoom = cv2.resize(self.white_img, (new_x, new_y))  # 画像のリサイズ
                # もともと表示されていた画像のトリミング枠のズレとイベントが発生した位置から画像のトリミング枠のズレを算出
                zoom_error_x = int(x * (zoom_magnif-self.prev_zoom_magnif) + self.margin_x)  # ズレの分だけ画像のトリミング枠が右にズレる
                zoom_error_y = int(y * (zoom_magnif-self.prev_zoom_magnif) + self.margin_y)  # ズレの分だけ画像がトリミング枠が下にズレる
                if self.dialog is False:
                    img_zoom = cv2.flip(img_zoom, -1)  # 画像を切り取る前に反転する
                # トリミング枠が画像の外になった場合、補正する
                if zoom_error_x < 0:
                    zoom_error_x = 0
                elif zoom_error_x + self.width > new_x:
                    zoom_error_x = new_x - self.width
                if zoom_error_y < 0:
                    zoom_error_y = 0
                elif zoom_error_y + self.height > new_y:
                    zoom_error_y = new_y - self.height
                # 画像のトリミング
                img = img_zoom[zoom_error_y:zoom_error_y + self.height, zoom_error_x:zoom_error_x + self.width]
                # 今回の枠のズレを保存する
                self.margin_y = zoom_error_y
                self.margin_x = zoom_error_x
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # pillowオブジェクトに変換するため色変換
                img_array = Image.fromarray(img)  # pillowオブジェクトに変換
                imgtk = ImageTk.PhotoImage(image=img_array)  # imgtkオブジェクトに変換
                # 画像の貼り付け
                self.result_img.imgtk = imgtk
                self.result_img.configure(image=imgtk)
                self.video_img.imgtk = imgtk
                self.video_img.configure(image=imgtk)
                self.prev_zoom_magnif = zoom_magnif  # 今回の拡大倍率を保存する
            # 拡大倍率が最低値になった場合
            elif self.wheel_num <= 0:
                # self.wheel_num=0のとき必ず枠と画像サイズは一致する
                self.wheel_num = 0
                zoom_magnif = (self.wheel_num * 0.1 + 1)
                new_x = int(self.width * zoom_magnif)
                new_y = int(self.height * zoom_magnif)
                img_zoom = cv2.resize(self.white_img, (new_x, new_y))
                if self.dialog is False:
                    img_zoom = cv2.flip(img_zoom, -1)
                img = img_zoom
                self.margin_x = 0
                self.margin_y = 0
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # pillowオブジェクトに変換するため色変換
                img_array = Image.fromarray(img)  # pillowオブジェクトに変換
                imgtk = ImageTk.PhotoImage(image=img_array)  # imgtkオブジェクトに変換
                # 画像の貼り付け
                self.result_img.imgtk = imgtk
                self.result_img.configure(image=imgtk)
                self.video_img.imgtk = imgtk
                self.prev_zoom_magnif = zoom_magnif  # 今回の拡大倍率を保存する
            # 拡大倍率が上限値を超えた場合
            elif self.wheel_num > 50:
                self.wheel_num = 50

    def get_xy(self, event):
        """
        マウス左ボタンが押されたときに、座標を取得する関数
        :param event:
        :return:
        """
        self.xmin = event.x
        self.ymin = event.y
        self.min_get = True  # 左クリックされた

    def drag_img(self, event):
        """
        マウス左ボタンを離したときに、押されたときからの座標差分画像を移動する関数
        :param event:
        :return:
        """
        # マウスが左クリックされているとき
        if self.min_get is True:
            # 座標の取得
            xmax = event.x
            ymax = event.y
            # 現在のトリミング枠のズレと、今回の移動距離から新たなトリミング枠のズレを計算する
            drag_error_x = int((self.xmin - xmax) + self.margin_x)
            drag_error_y = int((self.ymin - ymax) + self.margin_y)
            zoom_magnif = (self.wheel_num * 0.1 + 1)  # 現在の画像の拡大倍率を計算
            new_x = int(self.width * zoom_magnif)
            new_y = int(self.height * zoom_magnif)
            img_zoom = cv2.resize(self.white_img, (new_x, new_y))
            if self.dialog is False:
                img_zoom = cv2.flip(img_zoom, -1)
            #  トリミング枠が画像の外になった場合補正する
            if drag_error_x < 0:
                drag_error_x = 0
            elif drag_error_x + self.width > new_x:
                drag_error_x = new_x - self.width
            if drag_error_y < 0:
                drag_error_y = 0
            elif drag_error_y + self.height > new_y:
                drag_error_y = new_y - self.height
            # 画像をトリミングする
            img = img_zoom[drag_error_y:drag_error_y + self.height, drag_error_x:drag_error_x + self.width]
            self.margin_y = drag_error_y
            self.margin_x = drag_error_x
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # pillowオブジェクトに変換するため色変換
            img_array = Image.fromarray(img)  # pillowオブジェクトに変換
            imgtk = ImageTk.PhotoImage(image=img_array)  # imgtkオブジェクトに変換
            # 画像の貼り付け
            self.result_img.imgtk = imgtk
            self.result_img.configure(image=imgtk)
            self.video_img.imgtk = imgtk
            self.video_img.configure(image=imgtk)
            # マウスの移動前の値に現在の位置を設定する
            self.xmin = xmax
            self.ymin = ymax

    def release_img(self, event):
        """
        マウスのボタンがリリースされたときにおこる関数
        :param event:
        :return:
        """
        self.min_get = False  # マウスがボタンリリースされた

    def window_size(self, event):
        """
        ウィンドウサイズに応じて右メニューをほぼ一定の幅にするように、左の画像(映像)を拡大
        :param event: ウィンドウサイズ変更用のグリップがクリックされた
        """
        # ウィンドウサイズの取得
        win_width = self.winfo_width()
        win_height = self.winfo_height()
        abs_width = abs(win_width - self.prev_win_width)
        abs_height = abs(win_height - self.prev_win_height)
        if abs_width > 7 or abs_height > 7:
            width_magnif = win_width / 1280
            if width_magnif < 0.85:
                self.grid_columnconfigure(0, weight=1)
                self.grid_columnconfigure(1, weight=5)
                # ウィンドウサイズの初期値から倍率と新しい幅、高さを計算する
                self.magnif = (win_width - ((425 * 6 / 5) + 15)) / self.first_width
            elif 0.85 <= width_magnif < 1:
                self.grid_columnconfigure(0, weight=1)
                self.grid_columnconfigure(1, weight=3)
                # ウィンドウサイズの初期値から倍率と新しい幅、高さを計算する
                self.magnif = (win_width - ((425 * 4 / 3) + 10)) / self.first_width
            else:
                self.grid_columnconfigure(0, weight=1)
                self.grid_columnconfigure(1, weight=2)
                # ウィンドウサイズの初期値から倍率と新しい幅、高さを計算する
                self.magnif = (win_width - ((425 * 3 / 2) + 5)) / self.first_width

            self.height = int(self.first_height * self.magnif)
            self.width = int(self.first_width * self.magnif)
            # 高さの上限値を設定
            height_thresh = win_height - 50
            # 上限値を超える場合は、上限値に変更
            if self.height > height_thresh:
                self.height = height_thresh
                self.magnif = self.height/self.first_height
                self.width = int(self.first_width*self.magnif)

            height_magnif = win_height / 800  # 高さの倍率

            # 高さの倍率によって右側のメニュー領域の割合を変更する
            if height_magnif < 0.97:
                self.count_frame.grid_rowconfigure(0, weight=2)
                self.count_frame.grid_rowconfigure(1, weight=8)
                self.count_frame.grid_rowconfigure(2, weight=3)
                self.worker_frame.grid_configure(pady=10)
            elif 0.97 <= height_magnif < 1.15:
                self.count_frame.grid_rowconfigure(0, weight=2)
                self.count_frame.grid_rowconfigure(1, weight=8)
                self.count_frame.grid_rowconfigure(2, weight=3)
                self.worker_frame.grid_configure(pady=15)
            elif 1.15 <= height_magnif < 1.25:
                self.count_frame.grid_rowconfigure(0, weight=2)
                self.count_frame.grid_rowconfigure(1, weight=6)
                self.count_frame.grid_rowconfigure(2, weight=3)
                self.worker_frame.grid_configure(pady=25)
            else:
                self.count_frame.grid_rowconfigure(0, weight=1)
                self.count_frame.grid_rowconfigure(1, weight=2)
                self.count_frame.grid_rowconfigure(2, weight=1)
                self.worker_frame.grid_configure(pady=30)

            # 画像が表示されている場合、画像のリサイズを行う
            if self.count_flag is True:  # 表示画像がカウント後の画像の場合
                self.x_resize, self.y_resize, img = self.update_size_img(self.img_draw, self.width, self.height)
                img = cv2.flip(img, -1)
            elif self.dialog is True:
                self.x_resize, self.y_resize, img = self.update_size_img(self.frame, self.width, self.height)
            else:  # それ以外の場合
                img = cv2.resize(self.pickle_copy, (self.width, self.height))
                img = cv2.flip(img, -1)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # pillowオブジェクトに変換するため色変換
            img_array = Image.fromarray(img)  # pillowオブジェクトに変換
            imgtk = ImageTk.PhotoImage(image=img_array)  # imgtkオブジェクトに変換
            # 画像の貼り付け
            self.result_img.imgtk = imgtk
            self.result_img.configure(image=imgtk)
            self.video_img.imgtk = imgtk
            self.video_img.configure(image=imgtk)

            self.prev_win_width = win_width
            self.prev_win_height = win_height

    def focus_detect(self, event):
        self.f_detection_entry.focus_set()

    def focus_sheet(self, event):
        self.sheet_no_name.focus_set()

    def detection_event(self, event, detection_str, initial):
        """
        誤検出、未検出をカウントして、正しい良品数を出力する
        :param event: 矢印キーのどちらを押されたか
        :param detection_str: Entryに結びついているStringVar
        :param initial: 初期値
        """
        try:
            if event.keysym == "Up":
                self.up_or_down(detection_str, 1, initial)
            elif event.keysym == "Down":
                self.up_or_down(detection_str, -1, initial)
            n_number = self.n_detection_str.get()
            f_number = self.f_detection_str.get()
            self.new_count = self.is_count + int(n_number) - int(f_number)
            is_c = str(self.new_count) + "個"
            self.count_message.set(is_c)
            if self.method_num == 0:
                theoretical_amount_str = self.theoretical_amount_str.get()
            elif self.method_num == 1:
                theoretical_amount_str = self.theoretical_amount_str_cnt.get()
            # 理論数量が入力されていない場合
            if theoretical_amount_str == "":
                theoretical_amount_str = "100000000000000"
            theoretical_amount = int(theoretical_amount_str)
            if self.new_count <= theoretical_amount:
                self.count_result.configure(foreground="#000000")
            else:
                self.count_result.configure(foreground="#8b0000")
        except ValueError:
            sub_win = tk.Toplevel()
            error_window = ErrorMessage(sub_win)
            error_window.set_message("この文字は計算できません。\n"
                                     "数字を入力してください。")

    def detection_enter(self, event):
        try:
            n_number = self.n_detection_str.get()
            f_number = self.f_detection_str.get()
            if n_number == "":
                n_number = 0
            if f_number == "":
                f_number = 0
            self.new_count = self.is_count + int(n_number) - int(f_number)
            is_c = str(self.new_count) + "個"
            self.count_message.set(is_c)
        except ValueError:
            sub_win = tk.Toplevel()
            error_window = ErrorMessage(sub_win)
            error_window.set_message("この文字は計算できません。\n"
                                     "数字を入力してください。")

    def update_cam(self):
        """
        delayごとにループしてカメラ映像を取り込み出力
        cam_flag=Falseになると、ループが止まる
        cam_flag=Trueにして実行するとまた映像出力が始まる
        """
        try:
            if self.cam_flag is True:
                # first_width, first_height, magnifを渡して画像をリサイズしたもの(pickle_copy)を返す
                self.pickle_copy, self.frame = self.cap.get_frame_for_tk(self.first_width, self.first_height, self.magnif)
                # カメラの映像の関係上、上下左右反転
                pickle_copy = cv2.flip(self.pickle_copy, -1)
                pickle_copy = cv2.cvtColor(pickle_copy, cv2.COLOR_BGR2RGB)
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(pickle_copy))
                self.video_img.imgtk = self.photo
                self.video_img.configure(image=self.photo)
                # delayミリ秒後に関数を繰り返す
                self._camera_loop_id = self.after(self.delay, self.update_cam)
        except TypeError:
            pass

    def cam_stop(self, event):
        if self.dialog is False:
            if self.count_flag is False:
                self.cam_flag = False

    def cam_restart(self, event):
        if self.dialog is False:
            if self.count_flag is False:
                self.cam_flag = True
                self.update_cam()  # 動画の再開

    def cam_refresh(self):
        """
        カメラの接続不良になった場合に実行
        """
        self.cap.__init__(self.cam_num)

    def start_regi(self):
        """
        メニューバーの製品名登録からregistration_windowを呼び出す
        registration_window終了時に、gui_mainの製品名を更新する
        """
        self.cam_flag = False
        regi_win = tk.Toplevel()
        # registration_windowを開く
        registration_window.Registration(regi_win, self.cap, self.control,  self.cam_num,
                                         self.first_width, self.first_height)
        # ウィンドウを閉じた後に製品名のセレクトボックスを更新する
        product_names_t = self.control.start_regi()
        self.product_box["values"] = product_names_t
        self.product_box_cnt["values"] = product_names_t
        self.return_video()

    def start_settings(self):
        """
        メニューバーの設定からsettings_windowを呼び出す
        :return:
        """
        self.setting_flag = True
        settings_win = tk.Toplevel()
        settings_window.SettingsWindow(settings_win, self.control, self.method_num)

    def start_output(self):
        oh_win = tk.Toplevel()
        output_html_window.OutputHtml(oh_win, control=self.control)

    def file_open(self):
        """
        ファイル選択で選択したファイルを表示する
        """
        try:
            self.cam_flag = False
            self.dialog = True
            self.frame = self.control.file_open(self, 0)  # ファイル選択関数を実行
            self.update_result_img(self.frame)  # 画像を表示
            # ファイル参照と動画に戻るの状態を逆にする
            self.filedialog.entryconfig(u"ファイル参照", state="disabled")
            self.filedialog.entryconfig(u"動画に戻る", state="normal")
        except FileNotFoundError:
            self.return_video()

    def select_pattern(self, event):
        """
        製品名を選択したときにその製品の情報を反映する
        :param event: 製品名のセレクトボックスで1つの製品名を選択したとき
        """
        # method_num=0-->パターン検出　method_num=1-->輪郭検出
        if self.method_num == 0:
            product_name = self.product.get()  # 製品名を取得
            idx = max(0, self.product_box.current())  # 「製品情報を登録してください」がある時用。-1になるのを避ける
            self.product_box_cnt.current(idx)
        elif self.method_num == 1:
            product_name = self.product_cnt.get()
            idx = max(0, self.product_box_cnt.current())  # 「製品情報を登録してください」がある時用。-1になるのを避ける
            self.product_box.current(idx)
        # 製品情報を取り出す
        figure_no, theoretical_amount, yield_rate_limit, imgtk = self.control.product_bind(product_name)
        if self.method_num == 0:
            self.figure_no_str.set(figure_no)
            self.theoretical_amount_str.set(theoretical_amount)
            self.yield_rate_str.set(yield_rate_limit)
            # パターン画像に貼り付け
            self.pattern_img.imgtk = imgtk
            self.pattern_img.configure(image=imgtk)
            self.control.change_setting(product_name)  # パターンマッチングの閾値を変更する
            self.matching_threshold_str.set(str(self.control.matching_threshold))
        elif self.method_num == 1:
            self.figure_no_str_cnt.set(figure_no)
            self.theoretical_amount_str_cnt.set(theoretical_amount)
            self.yield_rate_str_cnt.set(yield_rate_limit)
            self.control.change_setting(product_name)  # 設定値を変更する
            self.erode_str_cnt.set(str(self.control.erode))
            self.dilate_str_cnt.set(str(self.control.dilate))
            self.thresh_area_str_cnt.set(str(self.control.thresh_area))

    def return_video(self):
        """
        画像表示状態を終了して動画に戻る
        """
        self.cam_flag = True
        self.dialog = False
        self.update_cam()  # 動画の再開
        self.result.lower(self.video)
        self.filedialog.entryconfig(u"ファイル参照", state="normal")
        self.filedialog.entryconfig(u"動画に戻る", state="disabled")

    def radiobutton_enter(self, product_num):
        """
        ラジオボタンをエンターキーで操作するための関数
        """
        if self.method_num == 0:
            self.var_product.set(product_num)
        elif self.method_num == 1:
            self.var_product_cnt.set(product_num)
        self.start_or_open()

    def start_or_open(self):
        """
        count_buttonの文字を新規、開くによって変更する
        """
        if self.method_num == 0:
            product_num = self.var_product.get()
        elif self.method_num == 1:
            product_num = self.var_product_cnt.get()
        # 新規の場合
        if product_num == 0:
            self.count_button_text_change(False)
        # 開くの場合
        else:
            self.count_button_text_change(None)

    def display_result(self, is_count, img_draw):
        """
        結果を出力する
        :param is_count: 良品数
        :param img_draw: 結果画像
        """
        # 結果個数の反映
        is_c = str(is_count) + "個"
        self.count_message.set(is_c)
        # 結果画像の反映
        self.update_result_img(img_draw, flip=-1)
        if self.method_num == 0:
            self.count_button.lower(self.count_check_frame)
        elif self.method_num == 1:
            self.count_button_cnt.lower(self.count_check_frame_cnt)

    def update_size_img(self, frame, width, height):
        """
        frameを(width, height)にリサイズする関数。
        このときframeの縦横比が(width, height)と違った場合、周囲に余白ができるようにリサイズする。
        :param frame: リサイズしたい画像
        :param width: リサイズ後の幅
        :param height: リサイズ後の高さ
        :return: x:リサイズ後の幅 y:リサイズ後の高さ white:リサイズした画像
        """
        y, x = frame.shape[:2]
        binary = pickle.dumps(frame)
        pickle_copy = pickle.loads(binary)
        # 画像サイズがフレームサイズよりも大きい場合リサイズする
        if x > width:
            new_width = x
            new_height = int(height * x / width)
        else:
            new_width = width
            new_height = height
        if y > new_height:
            new_width = int(width * y / height)
            new_height = y
        white = np.ones((new_height, new_width, 3), np.uint8) * 255  # 画像のサイズとフレームのサイズが合わない部分を埋める白画像を作成
        margin_x = int((new_width - x) / 2)
        margin_y = int((new_height - y) / 2)
        white[margin_y:margin_y + y, margin_x:margin_x + x] = pickle_copy  # 白画像中央にフレームを配置
        self.margin_x = 0
        self.margin_y = 0
        self.wheel_num = 0
        self.white_img = white
        img = cv2.resize(white, (width, height))  # 画像をリサイズする
        return x, y, img

    def update_result_img(self, img, flip=100):
        """
        update_size_imgの数値を利用してリサイズした画像を出力する
        :param img: 変更したい画像
        :param flip: 反転するかどうか 0: 1: -1:上下左右反転
        """
        # 結果画像の表示サイズ取得
        width = int(self.first_width * self.magnif)
        height = int(self.first_height * self.magnif)
        self.x_resize, self.y_resize, white = self.update_size_img(img, width, height)  # 画像のリサイズ
        if flip is not 100:
            white = cv2.flip(white, flip)  # 画像の回転
        img = cv2.cvtColor(white, cv2.COLOR_BGR2RGB)  # pillowオブジェクトに変換
        img_array = Image.fromarray(img)
        # 結果画像の反映
        imgtk = ImageTk.PhotoImage(image=img_array)
        self.result_img.imgtk = imgtk
        self.result_img.configure(image=imgtk)
        self.video.lower(self.result)

    def ok_new(self):
        """
        count_button後の確認ボタンで動画に戻る
        """
        # 情報の取得
        worker_name = self.worker.get()
        n_number = self.n_detection_str.get()
        f_number = self.f_detection_str.get()
        if self.method_num == 0:
            str_now = self.date.get()
            control_no = self.control_no_str.get()
            s_select = self.sheet_select.get()
            s_no = self.sheet_no_str.get()
        elif self.method_num == 1:
            str_now = self.date_cnt.get()
            control_no = self.control_no_str_cnt.get()
            s_select = self.sheet_select_cnt.get()
            s_no = self.sheet_no_str_cnt.get()
        self.new_count = self.is_count + int(n_number) - int(f_number)
        correct_count = self.new_count
        control_no = translate_word(control_no, number=True, not_available=True, upper=True, lower=True)
        s_no = translate_word(s_no, number=True, not_available=True, upper=True, lower=True)
        sheet_no = s_select + s_no
        # 結果の保存
        result = self.control.save_result(self.result_count[0], worker_name, str_now, self.result_count[1],
                                          self.result_count[2], self.result_count[3], self.result_count[4],
                                          self.result_count[5], self.result_count[7], correct_count,
                                          int(f_number), int(n_number), control_no, sheet_no)
        # しっかりと保存できた場合
        if result is True:
            self.return_video()
            if self.method_num == 0:
                self.count_confirm_frame.lower(self.count_button)
                self.count_check_frame.lower(self.count_confirm_frame)
            elif self.method_num == 1:
                self.count_confirm_frame_cnt.lower(self.count_button_cnt)
                self.count_check_frame_cnt.lower(self.count_confirm_frame_cnt)
            self.count_flag = False
            # 個数の初期化
            self.count_message.set("0個")
            self.is_count = 0
            self.n_detection_str.set("0")
            self.f_detection_str.set("0")
            self.count_result.configure(foreground="#000000")
            self.menubar.entryconfig(u"製品名登録", state="normal")
            self.control.test = False
            self.product_box.configure(state="readonly")
            self.product_box_cnt.configure(state="readonly")
            self.method_note.tab(0, state="normal")
            self.method_note.tab(1, state="normal")
        elif result is False:
            sub_win = tk.Toplevel()
            error_window = ErrorMessage(sub_win)
            error_window.set_message("この番号は保存されています。\n"
                                     "別の番号を入力してください。")

    def ok_open(self):
        """
        開く後の確認ボタンで動画に戻る
        """
        self.return_video()
        if self.method_num == 0:
            self.count_confirm_frame.lower(self.count_button)
            self.count_check_frame.lower(self.count_confirm_frame)
        elif self.method_num == 1:
            self.count_confirm_frame_cnt.lower(self.count_button_cnt)
            self.count_check_frame_cnt.lower(self.count_confirm_frame_cnt)
        self.count_flag = False
        # 個数の初期化
        self.count_message.set("0個")
        self.is_count = 0
        self.n_detection_str.set("0")
        self.f_detection_str.set("0")
        self.count_result.configure(foreground="#000000")
        self.menubar.entryconfig(u"製品名登録", state="normal")
        self.product_box.configure(state="readonly")
        self.product_box_cnt.configure(state="readonly")
        self.method_note.tab(0, state="normal")
        self.method_note.tab(1, state="normal")

    def up_or_down(self, strvar, num, initial):
        """
        stringvarの中身を変更するための関数。(矢印キーでの変更など)
        :param strvar: tk.StringVar()オブジェクト
        :param num: 変更値の幅(1 or -1)
        :param initial: 最小値
        """
        number = strvar.get()  # 現在の値の取得
        initial_str = str(initial)
        if number == "":  # 値がない場合は初期値1を入力
            strvar.set(initial_str)
        elif number == initial_str:  # 値が0の場合は、0未満にならないように設定
            if num < 0:
                strvar.set(initial_str)
            else:
                strvar.set("{}".format(initial + 1))
        else:
            number = int(number)  # 現在の値(数値)を取得して変更値を足す
            new_number = number + num
            strvar.set("{}".format(new_number))

    def count_bind(self, event):
        """
        count関数をbindとして使用するための関数。
        count_flagによって呼び出す関数が変わる
        """
        if self.setting_flag is False:  # 設定ウィンドウを開いていないときのみカウントや確認ができる
            # 製品カウントをまだしていない場合
            if self.count_flag is False:
                self.count()
            # カウント後の結果表示中の場合
            else:
                if self.method_num == 0:
                    product = self.var_product.get()
                else:
                    product = self.var_product_cnt.get()
                if product == 0:
                    self.ok_new()
                else:
                    self.ok_open()

    def count_stop(self):
        # 一度カメラのループを止める。
        self.after_cancel(self._camera_loop_id)

        # Trueにして映像更新がループされるように
        self.cam_flag = True

        self.menubar.entryconfig(u"製品名登録", state="normal")
        if self.dialog is True:
            self.return_video()
        else:
            # 映像更新スタート
            self.update_cam()

    def count_button_text_change(self, count):
        if self.method_num == 0:
            if count is True:
                self.count_button_text.set("カウント中...")
                self.count_button.configure(style="Count.TButton")
                self.count_button.update()
            elif count is False:
                self.count_button_text.set("スタート")
                self.count_button.configure(style="TButton")
                self.count_button.update()
            else:
                self.count_button_text.set("開く")
                self.count_button.configure(style="TButton")
                self.count_button.update()
        if self.method_num == 1:
            if count is True:
                self.count_button_text_cnt.set("カウント中...")
                self.count_button_cnt.configure(style="Count.TButton")
                self.count_button_cnt.update()
            elif count is False:
                self.count_button_text_cnt.set("スタート")
                self.count_button_cnt.configure(style="TButton")
                self.count_button_cnt.update()
            else:
                self.count_button_text_cnt.set("開く")
                self.count_button_cnt.configure(style="TButton")
                self.count_button_cnt.update()

    def count(self):
        """
        count_buttonにバインドされた関数
        新規：frameをカウントして結果を受け取り、表示
        開く：既にカウントされた結果を呼び出して表示
        """
        self.cam_flag = False
        # 入力された情報を取得する
        if self.method_num == 0:
            product_name = self.product.get()
            control_no = self.control_no_str.get()
            s_select = self.sheet_select.get()
            s_no = self.sheet_no_str.get()
            new_product = self.var_product.get()
        elif self.method_num == 1:
            product_name = self.product_cnt.get()
            control_no = self.control_no_str_cnt.get()
            s_select = self.sheet_select_cnt.get()
            s_no = self.sheet_no_str_cnt.get()
            new_product = self.var_product_cnt.get()
        control_no = translate_word(control_no, number=True, not_available=True, upper=True, lower=True)
        s_no = translate_word(s_no, number=True, not_available=True, upper=True, lower=True)
        sheet_no = s_select + s_no
        # 新規
        if new_product == 0:
            self.count_button_text_change(True)
            now = datetime.now()
            str_now = "{0:%Y/%m/%d %H:%M:%S}".format(now)
            if self.method_num == 0:
                self.date.set(str_now)
            else:
                self.date_cnt.set(str_now)
            if control_no == "":
                sub_win = tk.Toplevel()
                error_window = ErrorMessage(sub_win)
                error_window.set_message("管理Noが入力されていません。\n"
                                         "管理Noを入力してください。")
                self.count_stop()
                self.count_button_text_change(False)
            # シートNoの数字部分が入力されていない場合、小ウィンドウでエラーを表示
            elif s_no == "":
                sub_win = tk.Toplevel()
                error_window = ErrorMessage(sub_win)
                error_window.set_message("シートNoが入力されていません。\n"
                                         "シートNoを入力してください。")
                self.count_stop()
                self.count_button_text_change(False)
            # 2つとも入力されている場合
            else:
                try:
                    # カウントスタート
                    result = self.control.count(self.method_num, product_name, control_no, sheet_no,
                                                self.dialog, self.cap, self.frame)
                except:
                    import traceback
                    import os
                    error_dir = "./preprocessing_error/"
                    os.makedirs(error_dir, exist_ok=True)
                    now = datetime.now()
                    str_now = "{0:%m%d_%H%M}".format(now)
                    file_name = error_dir + str_now + ".txt"
                    with open(file_name, "w") as f:
                        pass
                    traceback.print_exc(file=open(file_name, "a"))
                    result = 100
                if result is None:
                    self.count_stop()
                # 既に存在するNoを指定した場合
                elif result is False:
                    sub_win = tk.Toplevel()
                    error_window = ErrorMessage(sub_win)
                    error_window.set_message("この番号のファイルは既に\n存在しています。\n"
                                             "別の番号を指定してください。")
                    self.count_stop()
                elif result == 100:  # マッチング中にエラーが起きた場合
                    sub_win = tk.Toplevel()
                    error_window = ErrorMessage(sub_win)
                    error_window.set_message("カウント中にエラーが発生しました。\nやり直してください。")
                    self.control.delete_dir(product_name, control_no, sheet_no)
                    self.count_stop()
                else:  # カウントできた場合
                    self.is_count = result[7]
                    self.new_count = self.is_count
                    self.img_draw = result[8]
                    self.result_count = result
                    theoretical_amount = result[5]
                    self.display_result(self.is_count, self.img_draw)
                    yield_rate_limit = result[6]
                    # カウント数より理論数量が小さければ良品数を赤色で表示する
                    if self.is_count > theoretical_amount:
                        self.count_result.configure(foreground="#8b0000")
                    # 歩留が設定した下限を下回った場合メッセージを表示する
                    if self.is_count/theoretical_amount * 100 < yield_rate_limit:
                        error_win = tk.Toplevel()
                        error_window = ErrorMessage(error_win)
                        error_window.set_message("歩留率が設定値を下回りました")
                    self.count_flag = True
                    self.filedialog.entryconfig(u"ファイル参照", state="disabled")
                    self.filedialog.entryconfig(u"動画に戻る", state="disabled")
                    self.menubar.entryconfig(u"製品名登録", state="disabled")
                    self.dialog = False
                    self.f_detection_str.set("0")
                    self.n_detection_str.set("0")
                    self.product_box.configure(state="disabled")
                    self.product_box_cnt.configure(state="disabled")
                    if self.method_num == 0:
                        self.method_note.tab(1, state="disabled")
                    else:
                        self.method_note.tab(0, state="disabled")
                self.count_button_text_change(False)
        # 開く
        else:
            result = self.control.open_result(control_no, sheet_no, product_name)
            # ファイルが存在しなかった場合(result = False)
            if result is False:
                self.count_stop()
                sub_win = tk.Toplevel()
                error_window = ErrorMessage(sub_win)
                error_window.set_message("この番号のファイルは\n存在していません。\n"
                                         "別の番号を指定してください。")
            # 存在する場合
            else:
                self.is_count = result[0]
                self.new_count = result[1]
                self.img_draw = result[5]
                self.prev_count_date = result[6]
                self.f_detection_str.set(result[2])
                self.n_detection_str.set(result[3])
                theoretical_amount = result[7]
                self.result_count = result
                self.display_result(self.new_count, self.img_draw)
                if self.method_num == 0:
                    self.date.set(self.prev_count_date)
                    self.count_confirm_frame.lower(self.count_check_frame)
                    self.method_note.tab(1, state="disabled")
                elif self.method_num == 1:
                    self.date_cnt.set(self.prev_count_date)
                    self.count_confirm_frame_cnt.lower(self.count_check_frame_cnt)
                    self.method_note.tab(0, state="disabled")
                self.count_flag = True
                # カウント数より理論数量が小さければ良品数を赤色で表示する
                if self.new_count > theoretical_amount:
                    self.count_result.configure(foreground="#8b0000")
                self.filedialog.entryconfig(u"ファイル参照", state="disabled")
                self.filedialog.entryconfig(u"動画に戻る", state="normal")
                self.menubar.entryconfig(u"製品名登録", state="disabled")
                self.product_box.configure(state="disabled")
                self.product_box_cnt.configure(state="disabled")

    def update_prev_count(self):
        """
        開くで開かれたファイルについて、管理No,シートNoを間違えた場合に使用
        管理No,シートNoを変更する
        """
        if self.method_num == 0:
            control_no = self.control_no_str.get()
            s_select = self.sheet_select.get()
            s_no = self.sheet_no_str.get()
        elif self.method_num == 1:
            control_no = self.control_no_str_cnt.get()
            s_select = self.sheet_select_cnt.get()
            s_no = self.sheet_no_str_cnt.get()
        false_detection = self.f_detection_str.get()
        not_detected = self.n_detection_str.get()
        self.new_count = self.is_count + int(not_detected) - int(false_detection)
        s_no = translate_word(s_no, number=True, not_available=True, upper=True, lower=True)
        sheet_no = s_select + s_no
        false_detection = self.f_detection_str.get()
        not_detected = self.n_detection_str.get()
        control_no = translate_word(control_no, number=True, not_available=True, upper=True, lower=True)
        # データベースの情報変更 保存先ディレクトリのリネーム
        result = self.control.update_prev(self.prev_count_date, control_no, sheet_no, self.new_count,
                                          int(false_detection), int(not_detected))
        sub_win = tk.Toplevel()
        error_window = ErrorMessage(sub_win)
        if result is True:
            error_window.set_message("変更が完了しました。")
            error_window.color_change()
            self.ok_open()
        elif result is None:
            error_window.set_message("存在するシートNoには\n変更できません。\n別のNoを指定してください。")
        else:
            error_window.set_message("予期せぬエラーにより\n変更できませんでした。\nやり直してください。")

    def delete_prev_count(self):
        """
        誤って撮影したデータの削除
        """
        result = self.control.delete_prev(self.prev_count_date)
        if result is True:
            sub_win = tk.Toplevel()
            error_window = ErrorMessage(sub_win)
            error_window.set_message("削除しました。")
            error_window.color_change()
            self.ok_open()
        else:
            sub_win = tk.Toplevel()
            error_window = ErrorMessage(sub_win)
            error_window.set_message("予期せぬエラーにより\n削除できませんでした。\nやり直してください。")

    def output_sheet_result(self):
        """
        シートの結果をhtmlで出力する
        """
        # データの取得を行う
        product_name, control_no, sheet_no, date_time = None, None, None, ""
        if self.method_num == 0:
            product_name = self.product.get()
            control_no = self.control_no_str.get()
            sheet_no = self.sheet_no_str.get()
            date_time = self.date.get()
        elif self.method_num == 1:
            product_name = self.product_cnt.get()
            control_no = self.control_no_str_cnt.get()
            sheet_no = self.sheet_no_str_cnt.get()
            date_time = self.date_cnt.get()
        # カウント数を求める(誤検出、未検出に入力したままエンターを押さないとカウント数が変わらないので、計算する)
        false_detection = self.f_detection_str.get()
        not_detected = self.n_detection_str.get()
        new_count = self.is_count + int(not_detected) - int(false_detection)
        worker_name = self.worker.get()
        # date_timeは"日付 時刻"の形になっているので日付だけ取り出す
        date = date_time.split(" ")[0]
        # 全角文字を半角に修正
        control_no = translate_word(control_no, number=True, upper=True, lower=True)
        sheet_no = translate_word(sheet_no, number=True, upper=True, lower=True)
        # HTML化
        self.control.output_sheet_result(product_name, control_no, sheet_no, new_count, worker_name, date)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    MainWindow()
