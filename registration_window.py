import pickle
import tkinter as tk
import tkinter.font as font
import tkinter.ttk as ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from control import Control
from setting_count import create_setting_file
from db_manage import DatabaseManage
from error_window_create import ErrorMessage
from translate_word import translate_word


class Registration(tk.Frame):
    def __init__(self, master=None, cap=None, control=None, cam_num=0, first_width=0, first_height=0):
        super().__init__()
        self.master = master
        if control is None:
            control = Control()
        self.control = control
        self.db = DatabaseManage("./count/count.db")
        self.first_width = first_width
        self.first_height = first_height
        self.cam_flag = True
        self.dialog = False
        self.product_names = self.control.product_names
        self.select_enlarge = 0
        self.enlarge = "on"
        self.frame = None
        self.frame2 = None
        self.frame_pattern = None
        self.pattern = None
        self.pattern_back = None
        self.x_down = None
        self.x_up = 0
        self.y_down = None
        self.y_up = 0
        self.margin_x = 0
        self.margin_y = 0
        self.pattern_magnif = 1
        self.bg_color = "#ffffff"
        self.fg_color = "#2b2f33"
        self.my_font = font.Font(self, family="メイリオ", size=11)
        self.my_font_small = font.Font(self, family="メイリオ", size=9)
        self.pattern_click = False
        self.wheel_num = 0

        self.master.attributes('-topmost', True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.master.geometry("1280x800")

        self.master.minsize(1280, 800)
        self.master.maxsize(1280, 800)
        self.master.grab_set()

        self.create_menubar()
        self.create_widgets()

        self.cam_num = cam_num
        self.cap = cap
        self.delay = 15
        self.update_cam()

        self.master.mainloop()
        self.cam_flag = False

        self._camera_loop_id = None

    def __del__(self):
        pass

    def create_menubar(self):
        """
        メニューバーの作成
        """
        menubar = tk.Menu(self)
        self.master.config(menu=menubar)
        # tearoff=Falseでメニューバーからファイルの選択の子要素を切り離せないように設定
        self.filedialog = tk.Menu(self.master, menubar, tearoff=False)
        menubar.add_cascade(label="ファイルの選択", menu=self.filedialog)
        menubar.add_cascade(label="カメラリフレッシュ", command=self.cam_refresh)
        menubar.add_cascade(label="終了", command=self.on_close)

        # ファイルの選択の子要素としてファイル参照と動画に戻るを追加
        self.filedialog.add_command(label="ファイル参照", command=self.file_open)
        self.filedialog.add_command(label="動画に戻る", command=self.return_video)
        # 動画表示中は動画に戻るは押すことができないように設定
        self.filedialog.entryconfig("動画に戻る", state="disabled")

    def create_widgets(self):
        # ウィンドウの背景変更ができなかったため、ウィンドウ全体を覆うフレームを作成
        root_frame = tk.Frame(self.master, width=1280, height=800, relief="groove", borderwidth=2)
        root_frame.place(x=0, y=0)
        side_frame = tk.Frame(self.master, width=450, height=800, relief="groove", borderwidth=2)
        side_frame.place(x=830, y=0)

        self.select_button = ttk.Button(self.master, text="選択", width=8, state="disabled", command=self.select_mode,
                                        style="R.TButton")
        self.select_button.place(x=330, y=self.first_width)

        self.enlarge_button = ttk.Button(self.master, text="拡大", width=8, state="normal", command=self.enlarge_mode,
                                         style="R.TButton")
        self.enlarge_button.place(x=440, y=self.first_width)

        # 撮影した画像を表示するフレーム パターンの登録時なども使われるため、click_down, drag, click_upがバインドされている
        self.result_p = ttk.Frame(self.master, style="R.TFrame")
        self.result_p.place(x=100, y=125)
        self.result_p_img = ttk.Label(self.result_p, style="R.TLabel")
        self.result_p_img.pack()
        self.result_p_img.bind("<Button-1>", self.click_down)
        self.result_p_img.bind("<B1-Motion>", self.drag)
        self.result_p_img.bind("<ButtonRelease-1>", self.click_up)

        # 取得した映像を表示するフレーム
        self.video = ttk.Frame(self.master, style="R.TFrame")
        self.video.place(x=100, y=125)
        self.video_img = ttk.Label(self.video, style="R.TLabel")
        self.video_img.pack()

        # 製品情報の要素が含まれたフレーム
        select_frame = tk.LabelFrame(self.master, text=u"製品情報登録", width=400, height=215, font=self.my_font_small,
                                     relief="groove", borderwidth=2)
        select_frame.place(x=855, y=10)

        self.var_regi = tk.IntVar()
        self.var_regi.set(0)
        check1_product = ttk.Radiobutton(select_frame, text="新規", variable=self.var_regi, value=0,
                                         command=self.registrate_or_change, style="R.TRadiobutton")
        check1_product.place(x=30, y=10)
        check2_product = ttk.Radiobutton(select_frame, text="変更", variable=self.var_regi,
                                         command=self.registrate_or_change, style="R.TRadiobutton")
        check2_product.place(x=120, y=10)

        pattern_name = ttk.Label(select_frame, text=u"製品名:", style="R.TLabel")
        pattern_name.place(x=30, y=45)

        # 製品名を表示するドロップダウンリスト
        self.product = tk.StringVar()
        self.product_box = ttk.Combobox(select_frame, textvariable=self.product, width=23)
        self.product_box.bind("<<ComboboxSelected>>", self.get_info)
        # product_namesはリストなので、タプルに変換
        product_names_t = tuple(self.product_names)
        self.product_box["values"] = product_names_t
        self.product_box.place(x=150, y=45)

        # 製品図番表示部分 製品図番は製品名を選択するとそれに準じて変更される
        figure_no_index = ttk.Label(select_frame, text=u"製品図番:", style="R.TLabel")
        figure_no_index.place(x=30, y=80)
        self.figure_no_str = tk.StringVar()
        figure_no_name = ttk.Entry(select_frame, textvariable=self.figure_no_str, width=25)
        figure_no_name.place(x=150, y=80)

        # 理論数量表示部分 理論数量は製品名を選択するとそれに準じて変更される
        theoretical_amount_index = ttk.Label(select_frame, text=u"理論数量:", style="R.TLabel")
        theoretical_amount_index.place(x=30, y=115)
        self.theoretical_amount_str = tk.StringVar()
        theoretical_amount_name = ttk.Entry(select_frame, textvariable=self.theoretical_amount_str, width=25)
        theoretical_amount_name.place(x=150, y=115)

        yield_rate_label = ttk.Label(select_frame, text="許容歩留率(%):", style="R.TLabel")
        yield_rate_label.place(x=30, y=150)
        self.yield_rate_str = tk.StringVar()
        yield_rate_entry = ttk.Entry(select_frame, textvariable=self.yield_rate_str, width=25)
        yield_rate_entry.place(x=150, y=150)

        self.info_change_button = ttk.Button(self.master, text="登録情報変更", width=34, command=self.info_change,
                                             style="R.TButton")
        self.info_change_button.place(x=900, y=230)

        self.icb_hide_frame = ttk.Frame(self.master, width=350, height=50, style="R.TFrame")
        self.icb_hide_frame.place(x=900, y=230)

        # 画像状態から動画状態に戻るボタン
        self.video_return_button = ttk.Button(self.master, text="動画に戻る", width=34, command=self.return_video,
                                              style="R.TButton")
        self.video_return_button.place(x=900, y=275)

        # 撮影ボタン
        self.shutter_text = tk.StringVar()
        self.shutter_text.set("撮影")
        self.shutter_button = ttk.Button(self.master, textvariable=self.shutter_text, width=34, command=self.shutter,
                                         style="R.TButton")
        self.shutter_button.place(x=900, y=275)

        # パターン登録にかかわるウィジェットを含んだフレーム
        pattern_frame = tk.LabelFrame(self.master, text=u"パターン登録", width=400, height=350, font=self.my_font_small,
                                      relief="groove", borderwidth=2)
        pattern_frame.place(x=855, y=320)

        self.pattern_img_frame = ttk.Frame(pattern_frame, width=200, height=200, style="R.TFrame")
        self.pattern_img_frame.place(x=100, y=60)
        self.pattern_img = ttk.Label(self.pattern_img_frame, style="R.TLabel")
        self.pattern_img.pack()
        self.pattern_img.bind("<MouseWheel>", self.mousewheel)  # パターン画像上でマウスホイールを動かすと呼び出す
        self.pattern_img.bind("<Button-1>", self.get_xy)  # 結果画像上でマウス左ボタンを押すと呼び出す
        self.pattern_img.bind("<Motion>", self.drag_img)
        self.pattern_img.bind("<ButtonRelease-1>", self.release_img)  # 結果画像上でマウス左ボタンを離すと呼び出す

        # パターンの微調整機能をもつボタン上下左右±1pxずつ動く
        x_down_minus_button = ttk.Button(pattern_frame, text="◁", width=2,
                                         command=lambda: self.pattern_pixel("x_down", -1), style="R.TButton")
        x_down_minus_button.place(x=20, y=120)
        x_down_plus_button = ttk.Button(pattern_frame, text="▷", width=2,
                                        command=lambda: self.pattern_pixel("x_down", 1), style="R.TButton")
        x_down_plus_button.place(x=20, y=160)

        y_down_minus_button = ttk.Button(pattern_frame, text="△", width=2,
                                         command=lambda: self.pattern_pixel("y_down", -1), style="R.TButton")
        y_down_minus_button.place(x=170, y=5)
        y_down_plus_button = ttk.Button(pattern_frame, text="▽", width=2,
                                        command=lambda: self.pattern_pixel("y_down", 1), style="R.TButton")
        y_down_plus_button.place(x=205, y=5)

        x_down_minus_button = ttk.Button(pattern_frame, text="◁", width=2,
                                         command=lambda: self.pattern_pixel("x_up", -1), style="R.TButton")
        x_down_minus_button.place(x=350, y=120)
        x_down_plus_button = ttk.Button(pattern_frame, text="▷", width=2,
                                        command=lambda: self.pattern_pixel("x_up", 1), style="R.TButton")
        x_down_plus_button.place(x=350, y=160)

        y_down_minus_button = ttk.Button(pattern_frame, text="△", width=2,
                                         command=lambda: self.pattern_pixel("y_up", -1), style="R.TButton")
        y_down_minus_button.place(x=170, y=280)
        y_down_plus_button = ttk.Button(pattern_frame, text="▽", width=2,
                                        command=lambda: self.pattern_pixel("y_up", 1), style="R.TButton")
        y_down_plus_button.place(x=205, y=280)

        self.pattern_change_button = ttk.Button(self.master, text="パターン変更", width=34, command=self.pattern_change,
                                                style="R.TButton")
        self.pattern_change_button.place(x=900, y=685)

        self.save_button = ttk.Button(self.master, text="登録", width=34, command=self.save, style="R.TButton")
        self.save_button.place(x=900, y=685)

    def update_cam(self):
        """
        delayごとにループしてカメラ映像を取り込み出力
        cam_flag=Falseになると、ループが止まる
        cam_flag=Trueにして実行するとまた映像出力が始まる
        """
        try:
            if self.cam_flag is True:
                # first_width, first_height, magnifを渡して画像をリサイズしたもの(pickle_copy)を返す
                pickle_copy, self.frame = self.cap.get_frame_for_tk(self.first_width, self.first_height, 1)
                # カメラの映像の関係上、上下左右反転
                pickle_copy = cv2.flip(pickle_copy, -1)
                pickle_copy = cv2.cvtColor(pickle_copy, cv2.COLOR_BGR2RGB)
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(pickle_copy))
                self.video_img.imgtk = self.photo
                self.video_img.configure(image=self.photo)
                # delayミリ秒後に関数を繰り返す
                self._camera_loop_id = self.after(self.delay, self.update_cam)
        except TypeError:
            pass

    def cam_refresh(self):
        """
        カメラリフレッシュ用の関数。カメラの初期設定をもう一度行う。
        """
        self.cap.__init__(d=self.cam_num)

    def on_close(self):
        """
        ウィンドウを閉じる
        """
        self.master.destroy()
        self.master.quit()

    def file_open(self):
        """
        ファイル選択で選択したファイルを表示する
        """
        try:
            self.after_cancel(self._camera_loop_id)

            self.cam_flag = False
            self.dialog = True
            # 前処理をした画像を表示
            self.frame = self.control.file_open(self.master, 1)
            self.frame2 = self.frame
            self.update_result_img(self.frame)
            self.shutter_button.lower(self.video_return_button)
            # ファイル参照と動画に戻るの状態を逆にする
            self.filedialog.entryconfig(u"ファイル参照", state="disabled")
            self.filedialog.entryconfig(u"動画に戻る", state="normal")
        except FileNotFoundError:
            self.return_video()

    def return_video(self):
        """
         画像表示状態を終了して動画に戻る
         """
        self.cam_flag = True
        self.dialog = False
        self.update_cam()
        self.result_p.lower(self.video)
        self.video_return_button.lower(self.shutter_button)
        self.filedialog.entryconfig(u"ファイル参照", state="normal")
        self.filedialog.entryconfig(u"動画に戻る", state="disabled")

    def update_result_img(self, img, flip=100):
        """
        update_size_imgの数値を利用してリサイズした画像を出力する
        :param img: 変更したい画像
        :param flip: 反転するかどうか 0: 1: -1:上下左右反転
        """
        x, y, white = self.update_size_img(img, self.first_width, self.first_height)
        if flip is not 100:
            white = cv2.flip(white, flip)
        img = cv2.cvtColor(white, cv2.COLOR_BGR2RGB)
        img_array = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img_array)
        self.result_p_img.imgtk = imgtk
        self.result_p_img.configure(image=imgtk)
        self.video.lower(self.result_p)

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
        self.frame = white
        self.frame2 = white
        img = cv2.resize(white, (width, height))  # 画像をリサイズする
        return x, y, img

    def shutter(self):
        """
        撮影ボタンにバインドする関数
        カメラの読み込みを止めて、画像を表示する。
        この時表示する画像は、射影変換、回転後の画像。
        """
        self.after_cancel(self._camera_loop_id)

        self.shutter_text.set("撮影中...")
        self.shutter_button.configure(style="Count.TButton")
        self.shutter_button.update()
        self.cam_flag = False
        self.frame2 = self.control.shutter(self.cap, self.frame, self.dialog)
        self.update_result_img(self.frame2)
        self.shutter_button.lower(self.video_return_button)
        self.shutter_text.set("撮影")
        self.shutter_button.configure(style="R.TButton")
        # ファイル参照と動画に戻るの状態を逆にする
        self.filedialog.entryconfig(u"ファイル参照", state="disabled")
        self.filedialog.entryconfig(u"動画に戻る", state="normal")

    def click_down(self, event):
        """
        選択：左クリックしたときの座標取得。
        拡大：画像の拡大(画像本来のサイズでクリックした点を中心として表示)
        　　　縮小(戻る)(画像全体が表示されるように、倍率を変更して表示)
        """
        # 拡大にチェックされているとき
        if self.select_enlarge == 1:
            x = event.x
            y = event.y
            # 拡大
            if self.enlarge == "on":
                self.frame1, self.large_x, self.large_y = self.control.enlarge_img(self.first_width, self.first_height,
                                                                                   x, y,
                                                                                   self.margin_x, self.margin_y,
                                                                                   self.frame2)
                self.enlarge = "off"
            # 縮小(戻る)
            else:
                # 元画像をself.first_width*self.first_heightに収まるように縮小する
                x, y, white = self.update_size_img(self.frame2, self.first_width, self.first_height)
                self.frame1 = white
                self.enlarge = "on"
            binary = pickle.dumps(self.frame1)
            pickle_copy = pickle.loads(binary)
            img = cv2.cvtColor(pickle_copy, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.result_p_img.imgtk = imgtk
            self.result_p_img.configure(image=imgtk)
        else:
            # クリックした座標を取得
            self.x_down = event.x
            self.y_down = event.y

    def drag(self, event):
        """
        ドラッグしている間の座標取得。
        クリックしたときの座標を使用して、拡大画像に矩形を描き表示する。
        拡大画像が存在しない場合、エラーメッセージを表示する。
        x_down: クリックしたときのx座標
        y_down:　クリックしたときのy座標
        frame_enlarge: 撮影画像の拡大画像(縮小していない画像)
        """
        if self.select_enlarge == 0:
            x2 = event.x
            y2 = event.y
            x1 = self.x_down
            y1 = self.y_down
            try:
                binary = pickle.dumps(self.frame1)
                pickle_copy = pickle.loads(binary)
            except Exception:
                x, y, white = self.update_size_img(self.frame2, self.first_width, self.first_height)
                binary = pickle.dumps(white)
                pickle_copy = pickle.loads(binary)
            finally:
                frame_enlarge_c = pickle_copy[0:self.first_height, 0:self.first_width]
                img = cv2.rectangle(frame_enlarge_c, (x1, y1), (x2, y2), (255, 255, 0), 1)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(image=img)
                self.result_p_img.imgtk = imgtk
                self.result_p_img.configure(image=imgtk)
        else:
            pass

    def cut_pattern(self, frame_pattern, x_down, x_up, y_down, y_up, cx, cy, magnif):
        """
        元画像にパターン画像を重ねてから指定サイズで切り取る
        :param frame_pattern: 元画像
        :param x_down: パターン左上x座標
        :param x_up: パターン右下x座標
        :param y_down: パターン左上y座標
        :param y_up: パターン右下y座標
        :param cx: 切り出し中心のx座標
        :param cy: 切り出し中心のy座標
        :param magnif: 表示画像拡大倍率(1または2.0)
        """
        h, w = frame_pattern.shape[:2]
        black = np.zeros((h, w, 3), np.uint8)
        # 200x200の画像に対して、黒画像を 0.3:0.7の割合で重ねる
        pattern_back = cv2.addWeighted(frame_pattern, 0.3, black, 0.7, 1)
        self.pattern = frame_pattern[y_down:y_up, x_down:x_up]
        # パターンとなる部分の画像を重ねる
        p_img = cv2.cvtColor(self.pattern, cv2.COLOR_BGR2RGB)
        p_img_array = Image.fromarray(p_img)
        p_b_img = cv2.cvtColor(pattern_back, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(p_b_img)
        pil_img.paste(p_img_array, (x_down, y_down))
        # 画像を倍率に合わせてリサイズする
        new_height = int(h * magnif)
        new_width = int(w * magnif)
        pil_img = pil_img.resize((new_width, new_height), Image.BICUBIC)
        # 切り出す座標を計算する(200×200px)
        x1 = cx - 100
        x2 = cx + 100
        y1 = cy - 100
        y2 = cy + 100
        # 画像の外側に座標がある場合補正する
        if x1 < 0:
            x1 = 0
            x2 = 200
        if y1 < 0:
            y1 = 0
            y2 = 200
        if x2 > new_width:
            x1 = new_width - 200
            x2 = new_width
        if y2 > new_height:
            y1 = new_height - 200
            y2 = new_height
        # 画像をトリミングする
        pil_img = pil_img.crop((x1, y1, x2, y2))
        imgtk = ImageTk.PhotoImage(image=pil_img)
        self.pattern_img.imgtk = imgtk
        self.pattern_img.configure(image=imgtk)

    def click_up(self, event):
        """
        リリースしたときの座標を取得。
        右下のパターン微調整機能部分に、パターンを原寸大で表示
        """
        try:
            # 選択状態になっているとき
            if self.select_enlarge == 0:
                if self.x_down is not None:
                    self.x_up = event.x
                    self.y_up = event.y
                    if self.x_down > self.x_up:
                        self.x_down, self.x_up = self.x_up, self.x_down
                    if self.y_down > self.y_up:
                        self.y_down, self.y_up = self.y_up, self.y_down

                    binary = pickle.dumps(self.frame2)
                    self.frame_pattern = pickle.loads(binary)
                    # 拡大されていないとき
                    if self.enlarge == "on":
                        result = self.control.select_img(self.first_width, self.first_height,
                                                         self.x_down, self.y_down, self.x_up, self.y_up,
                                                         self.margin_x, self.margin_y, self.enlarge, self.frame2)
                    # 拡大されているとき
                    else:
                        result = self.control.select_img(self.first_width, self.first_height,
                                                         self.x_down, self.y_down, self.x_up, self.y_up,
                                                         self.margin_x, self.margin_y, self.enlarge, None,
                                                         self.large_x, self.large_y)
                    self.x_down = result[0]
                    self.x_up = result[1]
                    self.y_down = result[2]
                    self.y_up = result[3]
                    self.cx = result[4]
                    self.cy = result[5]
                    self.wheel_num = 0
                    self.pattern_magnif = 1
                    self.cut_pattern(self.frame_pattern, self.x_down, self.x_up, self.y_down, self.y_up,
                                     self.cx, self.cy, self.pattern_magnif)
                else:
                    pass
            else:
                pass
        except Exception:
            pass

    def mousewheel(self, event):
        """
        マウスホイールイベントが発生した座標点が拡大後も同じ座標にくるようにトリミングする
        トリミング後画像 中心C = (100, 100) イベント発生座標A = (x, y)の時
        トリミング前画像 中心CT = (100+d, 100+f)　イベント発生座標AX = (x+d, y+f) (x移動量:d y移動量:f)
        AX-CTの関係　x移動量: 100-x y移動量: 100-y
        リサイズ倍率　resize
        トリミング前画像　イベント発生座標AX' = (resize*(x+d), resize*(y+f))
                       新しい中心座標NEW_CT = (resize*(x+d)+100-x, resize*(y+f)+100-y)
        :param event:
        :return:
        """
        # マウスホイールイベントを取得する
        if event.delta:
            x = event.x
            y = event.y
            # マウスホイールは120ごとに数字が区切られているので、回転した量を数値化する
            self.wheel_num += (event.delta / 120)  # event.deltaがマウスホイールの値
            if -8 <= self.wheel_num < 40:  # 倍率は0.2~5倍までとする
                # 前倍率との比較を行うため
                prev_magnif = self.pattern_magnif
                # 新しい倍率を計算する
                self.pattern_magnif = self.wheel_num * 0.1 + 1
                # イベントが起こった座標を元画像上の座標に移動させたときの移動量
                moved_x = self.cx - 100
                moved_y = self.cy - 100
                # 表示画像からの拡大倍率
                size_magnif = self.pattern_magnif / prev_magnif
                # 新しい中心座標を計算する
                self.cx = int(size_magnif * (x + moved_x) + 100 - x)
                self.cy = int(size_magnif * (y + moved_y) + 100 - y)
                # 画像の更新
                binary = pickle.dumps(self.frame_pattern)
                pattern_back2 = pickle.loads(binary)
                self.cut_pattern(pattern_back2, self.x_down, self.x_up, self.y_down, self.y_up, self.cx, self.cy,
                                 self.pattern_magnif)

    def get_xy(self, event):
        """
        マウス左ボタンが押されたときに、座標を取得する関数
        :param event:
        :return:
        """
        self.pattern_x_down = event.x
        self.pattern_y_down = event.y
        self.pattern_click = True  # 左クリックされた

    def drag_img(self, event):
        """
        マウス左ボタンを離したときに、押されたときからの座標差分画像を移動する関数
        :param event:
        :return:
        """
        # マウスが左クリックされているとき
        if self.pattern_click is True:
            # 座標の取得
            pattern_x_up = event.x
            pattern_y_up = event.y
            # ズレを算出する
            x_gap = int((pattern_x_up - self.pattern_x_down) / self.pattern_magnif)
            y_gap = int((pattern_y_up - self.pattern_y_down) / self.pattern_magnif)
            # 中心座標の更新
            self.cx -= x_gap
            self.cy -= y_gap
            # 画像の更新
            binary = pickle.dumps(self.frame_pattern)
            pattern_back2 = pickle.loads(binary)
            self.cut_pattern(pattern_back2, self.x_down, self.x_up, self.y_down, self.y_up, self.cx, self.cy,
                             self.pattern_magnif)
            # マウスの移動前の値に現在位置を設定
            self.pattern_x_down = pattern_x_up
            self.pattern_y_down = pattern_y_up

    def release_img(self, event):
        """
        マウスのボタンがリリースされたときにおこる関数
        :param event:
        :return:
        """
        self.pattern_click = False  # マウスがボタンリリースされた

    def select_mode(self):
        """
        選択モード
        """
        self.select_button.configure(state="disabled")
        self.enlarge_button.configure(state="normal")
        self.select_enlarge = 0

    def enlarge_mode(self):
        """
        拡大モード
        """
        self.select_button.configure(state="normal")
        self.enlarge_button.configure(state="disabled")
        self.select_enlarge = 1

    def pattern_pixel(self, sides, pixel):
        """
        パターンを1px増減させるコード
        :param sides: どの方向に増減させるか
        :param pixel: 増減させるpx数(+1px, -1px)
        :return:
        """
        h, w = self.frame_pattern.shape[:2]
        # 増減値によって新しい値に更新する。ただし画像からはみ出ている場合は修正する
        try:
            if sides == "x_down":
                self.x_down += pixel
                if self.x_down < 0:
                    self.x_down = 0
            elif sides == "y_down":
                self.y_down += pixel
                if self.y_down < 0:
                    self.y_down = 0
            elif sides == "x_up":
                self.x_up += pixel
                if self.x_up > w:
                    self.x_up = w
            else:
                self.y_up += pixel
                if self.y_up > h:
                    self.y_up = h
            # downとupが同じ値になるとパターンは面積がなくなるので補正する
            if self.x_down == self.x_up:
                self.x_up += 1
            if self.y_down == self.y_up:
                self.y_up += 1
        except NameError:
            pass
        else:
            binary = pickle.dumps(self.frame_pattern)
            pattern_back2 = pickle.loads(binary)
            self.cut_pattern(pattern_back2, self.x_down, self.x_up, self.y_down, self.y_up, self.cx, self.cy,
                             self.pattern_magnif)

    def get_info(self, event):
        """
        既存のパターンの情報を呼び出す
        """
        product_name = self.product.get()
        result = self.control.get_info(product_name)
        # 登録されていない製品情報の場合
        if result is False:
            sub_win = tk.Toplevel()
            error_window = ErrorMessage(sub_win)
            error_window.set_message("この製品の情報はありません。\n"
                                     "新規で情報を入力してください。")
        else:
            figure_no, theoretical_amount, marking, yield_rate_limit = result
            self.figure_no_str.set(figure_no)
            self.theoretical_amount_str.set(theoretical_amount)
            self.yield_rate_str.set(yield_rate_limit)

    def registrate_or_change(self):
        """
        新規登録と変更の切り替え
        ラジオボタンを切り替えると、登録ボタンと変更ボタンがGUI上に切り替わって表示される
        """
        regist = self.var_regi.get()
        # ラジオボタンが新規登録なら保存ボタンだけを表示する
        if regist == 0:
            self.info_change_button.lower(self.icb_hide_frame)
            self.pattern_change_button.lower(self.save_button)
        # ラジオボタンが変更なら情報変更とパターン変更の2つのボタンを表示する
        else:
            self.icb_hide_frame.lower(self.info_change_button)
            self.save_button.lower(self.pattern_change_button)

    def info_change(self):
        """
        既存の登録されたパターンの情報のみを変更する
        """
        product_name = self.product.get()
        product_name = translate_word(product_name, number=True, not_available=True, upper=True, lower=True)
        # 登録済みのパターンについてのみ変更できる
        if product_name in self.product_names:
            figure_no = self.figure_no_str.get()
            theoretical_amount = self.theoretical_amount_str.get()
            yield_rate_limit = self.yield_rate_str.get()
            figure_no = translate_word(figure_no, number=True, not_available=True, upper=True, lower=True)
            theoretical_amount = translate_word(theoretical_amount,
                                                number=True, not_available=True, upper=True, lower=True)
            yield_rate_limit = translate_word(yield_rate_limit, number=True)

            # 許容歩留率: 空文字、数字以外、0~100から外れている場合はエラーメッセージ
            try:  # 数字かどうか。
                yield_rate_limit = float(yield_rate_limit)  # float("")もValueError
            except ValueError:
                error_win = tk.Toplevel()
                error_win = ErrorMessage(error_win)
                error_win.set_message("許容歩留率には0～100の数字を\n入力してください。")
                return
            else:
                if not (0 < float(yield_rate_limit) <= 100):  # 0~100の範囲にはいっているか
                    error_win = tk.Toplevel()
                    error_win = ErrorMessage(error_win)
                    error_win.set_message("許容歩留率には0～100の数字を\n入力してください。")
                    return

            # 情報未記入の部分がある場合それぞれエラーウィンドウを表示する
            if figure_no == "":
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("製品図番が入力されていません。\n入力してください。")
            elif theoretical_amount == "":
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("理論数量が入力されていません。\n入力してください。")
            else:
                marking = 0
                try:
                    # データベースのproductテーブルの情報を更新する
                    self.db.update_row("product",
                                       ("figure_No", figure_no),
                                       ("theoretical_amount", int(theoretical_amount)),
                                       ("marking", marking),
                                       ("yield_rate_limit", yield_rate_limit),
                                       product_name=product_name)
                except ValueError:
                    error_win = tk.Toplevel()
                    error_window = ErrorMessage(error_win)
                    error_window.set_message("理論数量は数字で\n入力してください。")
                else:
                    error_win = tk.Toplevel()
                    error_window = ErrorMessage(error_win)
                    error_window.set_message("変更完了しました。".format(product_name))
                    error_window.color_change()
                    error_window.title_change(u"登録完了")
        # 登録されていないパターンの場合はエラーウィンドウを表示
        else:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("{}\nという製品名は\n登録されていません。".format(product_name))

    def pattern_change(self):
        """
        登録済みの製品のパターンのみを変更する
        """
        try:
            product_name = self.product.get()
            # 登録済みのパターンについてのみ変更できる
            if product_name in self.product_names:
                self.control.pattern_change(product_name, self.pattern)
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("変更完了しました。".format(product_name))
                error_window.color_change()
                error_window.title_change(u"登録完了")
            # 登録されていない製品の場合はエラーウィンドウを表示
            elif product_name == "":
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("製品名が選択されていません。\n選択してください。".format(product_name))
            else:
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("{}\nという製品名は\n登録されていません。".format(product_name))
        # パターン画像が選択されていない場合はエラーメッセージを表示
        except NameError:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("パターン画像が選択されていません。\n画像の選択を行ってください。")

    def save(self):
        """
        製品の新規登録
        """
        product_name = self.product.get()
        product_name = translate_word(product_name, number=True, not_available=True, upper=True, lower=True)
        # 既に登録してある製品名は登録できない
        if product_name not in self.product_names:
            figure_no = self.figure_no_str.get()
            theoretical_amount = self.theoretical_amount_str.get()
            yield_rate_limit = self.yield_rate_str.get()
            figure_no = translate_word(figure_no, number=True, not_available=True, upper=True, lower=True)
            theoretical_amount = translate_word(theoretical_amount,
                                                number=True, not_available=True, upper=True, lower=True)
            yield_rate_limit = translate_word(yield_rate_limit, number=True)

            # 許容歩留率: 空文字、数字以外、0~100から外れている場合はエラーメッセージ
            try:  # 数字かどうか。
                yield_rate_limit = float(yield_rate_limit)  # float("")もValueError
            except ValueError:
                error_win = tk.Toplevel()
                error_win = ErrorMessage(error_win)
                error_win.set_message("許容歩留率には0～100の数字を\n入力してください。")
                return
            else:
                if not (0 < float(yield_rate_limit) <= 100):  # 0~100の範囲にはいっているか
                    error_win = tk.Toplevel()
                    error_win = ErrorMessage(error_win)
                    error_win.set_message("許容歩留率には0～100の数字を\n入力してください。")
                    return

            # 各項目が記入されていない場合エラーウィンドウを表示する
            if product_name == "":
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("製品名が入力されていません。\n入力してください。")
            elif figure_no == "":
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("製品図番が入力されていません。\n入力してください。")
            elif theoretical_amount == "":
                error_win = tk.Toplevel()
                error_window = ErrorMessage(error_win)
                error_window.set_message("理論数量が入力されていません。\n入力してください。")
            else:
                marking = 0
                # パターン保存用のディレクトリを作成
                result = self.control.save(figure_no, product_name, theoretical_amount, yield_rate_limit, marking,
                                           self.pattern)
                if result is False:
                    error_win = tk.Toplevel()
                    error_window = ErrorMessage(error_win)
                    error_window.set_message("パターン画像が\n選択されていません。\n画像選択を行ってください。")
                elif result is None:
                    error_win = tk.Toplevel()
                    error_window = ErrorMessage(error_win)
                    error_window.set_message("理論数量は数字で\n入力してください。")
                elif result == 100:
                    error_win = tk.Toplevel()
                    error_window = ErrorMessage(error_win)
                    error_window.set_message("エラーが発生しました。\nやり直してください。")
                else:
                    self.product_names = result
                    product_names_t = tuple(self.product_names)
                    self.product_box["values"] = product_names_t
                    self.return_video()
                    error_win = tk.Toplevel()
                    error_window = ErrorMessage(error_win)
                    create_setting_file(self.control.setting_dir, product_name)  # 設定ファイルの作成
                    error_window.set_message("登録完了しました。".format(product_name))
                    error_window.color_change()
                    error_window.title_change(u"登録完了")

        # 登録済み製品名の場合はエラーウィンドウを表示
        else:
            error_win = tk.Toplevel()
            error_window = ErrorMessage(error_win)
            error_window.set_message("{}\nという製品名は\n登録されています".format(product_name))

