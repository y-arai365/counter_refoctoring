import os
import pickle
import tkinter as tk
import tkinter.ttk as ttk

import cv2
import numpy as np

from control import Control
from error_window_create import ErrorMessage
from setting_count import create_setting_file, load_setting_file


class SettingsWindow(tk.Frame):
    def __init__(self, master=None, control=None, method_num=0):
        super().__init__()
        self.master = master  # tk.Tk or tk.Toplevelによって与えられたウィンドウ
        if control is None:  # このクラスを呼び出したときに、controlが使われていれば、同じものを共有する
            control = Control()
        self.control = control
        self.method_num = method_num
        self.master.geometry("500x500+300+300")
        self.master.title(u"設定値変更")
        self.master.resizable(width=False, height=False)  # ウィンドウサイズの変更を受け付けない
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()
        self.init_flag = False
        # メインウィンドウのウィジェットを使用できないようにする
        if self.method_num == 0:
            self.control.main_window.count_button.configure(state="disabled")
            self.control.main_window.count_ok.configure(state="disabled")
            self.control.main_window.product_box.configure(state="disabled")
        else:
            self.control.main_window.count_button_cnt.configure(state="disabled")
            self.control.main_window.count_ok_cnt.configure(state="disabled")
            self.control.main_window.product_box_cnt.configure(state="disabled")
        # ファイルからの現在設定値の読み込み
        self.settings_init()

    def on_close(self):
        """
        ウィンドウを閉じる
        """
        self.master.destroy()
        self.control.main_window.setting_flag = False
        # メインウィンドウのウィジェットを元の状態に戻す
        self.control.main_window.count_button.configure(state="normal")
        self.control.main_window.count_ok.configure(state="normal")
        self.control.main_window.product_box.configure(state="readonly")
        self.control.main_window.count_button_cnt.configure(state="normal")
        self.control.main_window.count_ok_cnt.configure(state="normal")
        self.control.main_window.product_box_cnt.configure(state="readonly")
        if self.control.test is True:  # テストによって変更する状態になっている場合
            # メインウィンドウの確認ボタンを再カウント中にする
            if self.method_num == 0:
                self.control.main_window.count_ok.configure(text="再カウント中...", style="Count.TButton")
                self.control.main_window.count_ok.update()
            else:
                self.control.main_window.count_ok_cnt.configure(text="再カウント中...", style="Count.TButton")
                self.control.main_window.count_ok_cnt.update()
            # 保存結果と表示の値が違う場合は検出しなおす。(テストカウントだけして設定値の変更を行わなかった場合に対応するため)
            re_count_flag = False
            setting_dir = self.control.setting_dir
            product_name = self.control.main_window.product.get()
            matching_threshold_pkl, erode_size_pkl, dilate_size_pkl, thresh_area_pkl,\
                h_range_pkl, l_range_pkl, s_range_pkl = load_setting_file(setting_dir, product_name)
            matching_threshold_bar = float(self.matching_th_str.get())
            erode_size_bar = int(self.erode_size_str.get())
            dilate_size_bar = int(self.dilate_size_str.get())
            thresh_area_bar = int(self.thresh_area_str.get())
            h_range_bar = int(self.h_range_str.get())
            l_range_bar = int(self.l_range_str.get())
            s_range_bar = int(self.s_range.get())
            if matching_threshold_pkl != matching_threshold_bar:  # どの条件が変わっているのか分かりづらいので、このようにする
                self.matching_th_str.set(str(matching_threshold_pkl))
                re_count_flag = True
            if erode_size_pkl != erode_size_bar:
                self.erode_size_str.set(str(erode_size_pkl))
                re_count_flag = True
            if dilate_size_pkl != dilate_size_bar:
                self.dilate_size_str.set(str(dilate_size_pkl))
                re_count_flag = True
            if thresh_area_pkl != thresh_area_bar:
                self.thresh_area_str.set(str(thresh_area_pkl))
                re_count_flag = True
            if h_range_pkl != h_range_bar:
                self.h_range_str.set(str(h_range_pkl))
                re_count_flag = True
            if l_range_pkl != l_range_bar:
                self.l_range_str.set(str(l_range_pkl))
                re_count_flag = True
            if s_range_pkl != l_range_bar:
                self.s_range_str.set(str(s_range_pkl))
                re_count_flag = True
            if re_count_flag is True:
                self.test_count()

            # メインウィンドウの確認ボタンを元に戻す
            if self.method_num == 0:
                self.control.main_window.count_ok.configure(text="確認", style="TButton")
                self.control.main_window.count_ok.update()
            else:
                self.control.main_window.count_ok_cnt.configure(text="確認", style="TButton")
                self.control.main_window.count_ok_cnt.update()

    def create_widgets(self):
        setting_label = ttk.Label(self.master, text=u"設定項目")
        setting_label.place(x=220, y=15)
        # それぞれの手法をラベルフレームで囲む
        pattern_matching = tk.LabelFrame(self.master, text=u"パターンマッチング", width=230, height=350)
        pattern_matching.place(x=15, y=50)

        matching_th_label = tk.Label(pattern_matching, text=u"マッチングの閾値")
        matching_th_label.place(x=10, y=10)

        # スライダーの値を表示するエントリーの作成
        self.matching_th_str = tk.StringVar()
        matching_th_box = ttk.Entry(pattern_matching, textvariable=self.matching_th_str, width=5, state="readonly")
        matching_th_box.place(x=155, y=8)
        # スライダーの作成
        self.matching_threshold = tk.IntVar()
        self.matching_threshold.trace("w", self.change_matching_th)  # スライダーが動いたらエントリーの値を変更する
        self.matching_th_slider = ttk.Scale(pattern_matching, variable=self.matching_threshold, orient=tk.HORIZONTAL,
                                            length=200, from_=0, to=1000)
        self.matching_th_slider.place(x=10, y=45)

        color_judgement_tolerance_label = tk.Label(pattern_matching, text=u"色判定許容範囲")
        color_judgement_tolerance_label.place(x=10, y=85)

        h_range_label = tk.Label(pattern_matching, text="H")
        h_range_label.place(x=10, y=120)

        # HLSのHの値を表示するエントリーの作成
        self.h_range_str = tk.StringVar()
        h_range_box = ttk.Entry(pattern_matching, textvariable=self.h_range_str, width=5, state="readonly")
        h_range_box.place(x=155, y=118)

        # HLSのHの範囲
        self.h_range = tk.IntVar()
        self.h_range.trace("w", self._change_h_range)  # スライダーが動いたらエントリーの値を変更する
        self.h_range_slider = ttk.Scale(pattern_matching, variable=self.h_range, orient=tk.HORIZONTAL,
                                        length=200, from_=0, to=180)
        self.h_range_slider.place(x=10, y=155)

        l_range_label = tk.Label(pattern_matching, text="L")
        l_range_label.place(x=10, y=185)

        # HLSのLの値を表示するエントリーの作成
        self.l_range_str = tk.StringVar()
        l_range_box = ttk.Entry(pattern_matching, textvariable=self.l_range_str, width=5, state="readonly")
        l_range_box.place(x=155, y=183)

        # HLSのLの範囲
        self.l_range = tk.IntVar()
        self.l_range.trace("w", self._change_l_range)  # スライダーが動いたらエントリーの値を変更する
        self.l_range_slider = ttk.Scale(pattern_matching, variable=self.l_range, orient=tk.HORIZONTAL,
                                        length=200, from_=0, to=255)
        self.l_range_slider.place(x=10, y=220)

        s_range_label = tk.Label(pattern_matching, text="S")
        s_range_label.place(x=10, y=250)

        # HLSのSの範囲
        self.s_range_str = tk.StringVar()
        s_range_box = ttk.Entry(pattern_matching, textvariable=self.s_range_str, width=5, state="readonly")
        s_range_box.place(x=155, y=248)

        self.s_range = tk.IntVar()
        self.s_range.trace("w", self._change_s_range)  # スライダーが動いたらエントリーの値を変更する
        self.s_range_slider = ttk.Scale(pattern_matching, variable=self.s_range, orient=tk.HORIZONTAL,
                                        length=200, from_=0, to=255)
        self.s_range_slider.place(x=10, y=285)

        find_contours = tk.LabelFrame(self.master, text=u"輪郭抽出", width=230, height=350)
        find_contours.place(x=255, y=50)

        erode_label = ttk.Label(find_contours, text=u"収縮量")
        erode_label.place(x=10, y=10)

        # スライダーの値を表示するエントリーの作成
        self.erode_size_str = tk.StringVar()
        self.erode_box = ttk.Entry(find_contours, textvariable=self.erode_size_str, width=5, state="readonly")
        self.erode_box.place(x=155, y=8)
        # スライダーの作成
        self.erode_size = tk.IntVar()
        self.erode_size.trace("w", self.change_erode)  # スライダーが動いたらエントリーの値を変更する
        self.erode_slider = ttk.Scale(find_contours, variable=self.erode_size, orient=tk.HORIZONTAL, length=200,
                                      from_=0, to=20)
        self.erode_slider.place(x=10, y=45)

        dilate_label = ttk.Label(find_contours, text=u"膨張量")
        dilate_label.place(x=10, y=80)
        self.dilate_size_str = tk.StringVar()
        self.dilate_box = ttk.Entry(find_contours, textvariable=self.dilate_size_str, width=5, state="readonly")
        self.dilate_box.place(x=155, y=78)
        self.dilate_size = tk.IntVar()
        self.dilate_size.trace("w", self.change_dilate)
        self.dilate_slider = ttk.Scale(find_contours, variable=self.dilate_size, orient=tk.HORIZONTAL, length=200,
                                       from_=0, to=20)
        self.dilate_slider.place(x=10, y=115)

        thresh_area_label = ttk.Label(find_contours, text=u"除外面積")
        thresh_area_label.place(x=10, y=150)
        self.thresh_area_str = tk.StringVar()
        self.thresh_area_box = ttk.Entry(find_contours, textvariable=self.thresh_area_str, width=5, state="readonly")
        self.thresh_area_box.place(x=155, y=148)
        self.thresh_area = tk.IntVar()
        self.thresh_area.trace("w", self.change_thresh_area)
        self.thresh_area_slider = ttk.Scale(find_contours, variable=self.thresh_area, orient=tk.HORIZONTAL, length=200,
                                            from_=0, to=2000)
        self.thresh_area_slider.place(x=10, y=185)

        self.test_button = ttk.Button(self.master, text=u"テストカウント", state="disabled", command=self.test_count,
                                      width=14)
        self.test_button.place(x=185, y=410)

        self.change_button = ttk.Button(self.master, text=u"変更", state="disabled", command=self.change_settings,
                                        width=14)
        self.change_button.place(x=185, y=450)

    def settings_init(self):
        """
        設定ファイルから設定値を読み込んで、ウィジェットに反映する関数。
        設定値から、それぞれのウィジェットに入る数値を計算する。
        :return:
        """
        matching_threshold = int(self.control.matching_threshold * 1000)
        erode_size = int(self.control.erode)
        dilate_size = int(self.control.dilate)
        thresh_area = int(self.control.thresh_area)
        h_range, l_range, s_range = self.control.get_hls_range()
        self.matching_threshold.set(matching_threshold)
        self.change_matching_th()
        self.erode_size.set(erode_size)
        self.change_erode()
        self.dilate_size.set(dilate_size)
        self.change_dilate()
        self.thresh_area.set(thresh_area)
        self.change_thresh_area()
        self.h_range.set(h_range)
        self._change_h_range()
        self.l_range.set(l_range)
        self._change_l_range()
        self.s_range.set(s_range)
        self._change_s_range()
        if self.control.test is True:
            if self.method_num == 0:  # ttk.scaleは、configureでstateを設定することはできない
                self.erode_slider.state(["disabled"])
                self.dilate_slider.state(["disabled"])
                self.thresh_area_slider.state(["disabled"])
            else:
                self.matching_th_slider.state(["disabled"])
                self.h_range_slider.state(["disabled"])
                self.l_range_slider.state(["disabled"])
                self.s_range_slider.state(["disabled"])
        self.init_flag = True

    def change_matching_th(self, *args):
        """
        膨張スライダーの値が変更されたら、エントリーの中身を変更する
        :param args: 移動によって得られる変数
        :return:
        """
        # スライダーの値の取得
        matching_th = self.matching_threshold.get()
        matching_th = matching_th / 1000
        self.matching_th_str.set(str(matching_th))
        if self.init_flag is True:
            if self.control.test is True:
                self.test_button.configure(state="normal")
                self.change_button.configure(state="disabled")
            else:
                self.change_button.configure(state="normal")

    def change_erode(self, *args):
        # スライダーの値の取得
        size = self.erode_size.get()
        self.erode_size_str.set(str(size))
        if self.init_flag is True:
            if self.control.test is True:
                self.test_button.configure(state="normal")
                self.change_button.configure(state="disabled")
            else:
                self.change_button.configure(state="normal")

    def change_dilate(self, *args):
        """
        収縮スライダーの値が変更されたら、エントリーの中身を変更する
        :param args: 移動によって得られる変数
        :return:
        """
        # スライダーの値の取得
        size = self.dilate_size.get()
        self.dilate_size_str.set(str(size))
        if self.init_flag is True:
            if self.control.test is True:
                self.test_button.configure(state="normal")
                self.change_button.configure(state="disabled")
            else:
                self.change_button.configure(state="normal")

    def change_thresh_area(self, *args):
        """
        除外面積スライダーの値が変更されたらエントリーの中身を変更する
        :param args: 移動によって得られる変数
        :return:
        """
        # スライダーの値の取得
        area = self.thresh_area.get()
        self.thresh_area_str.set(str(area))
        if self.init_flag is True:
            if self.control.test is True:
                self.test_button.configure(state="normal")
                self.change_button.configure(state="disabled")
            else:
                self.change_button.configure(state="normal")

    def _change_h_range(self, *args):
        """
        Hスライダーの値が変更されたらエントリーの中身を変更する
        :param args: 移動によって得られる変数
        :return:
        """
        self._change_range(self.h_range, self.h_range_str)
    
    def _change_l_range(self, *args):
        """
        Lスライダーの値が変更されたらエントリーの中身を変更する
        :param args: 移動によって得られる変数
        :return:
        """
        self._change_range(self.l_range, self.l_range_str)
    
    def _change_s_range(self, *args):
        """
        Sスライダーの値が変更されたらエントリーの中身を変更する
        :param args: 移動によって得られる変数
        :return:
        """
        self._change_range(self.s_range, self.s_range_str)
                
    def _change_range(self, slider_var, entry_var):
        # スライダーの値の取得
        color_range = slider_var.get()
        entry_var.set(str(color_range))
        if self.init_flag is True:
            if self.control.test is True:
                self.test_button.configure(state="normal")
                self.change_button.configure(state="disabled")
            else:
                self.change_button.configure(state="normal")

    def test_count(self):
        """
        テストカウントボタンを押したときに結果画像を更新していく関数
        :return:
        """
        if self.test_button.winfo_exists() == 1:  # テストボタンの存在を確認(0 or 1が返ってくる)
            self.test_button.configure(text=u"カウント中...")
            self.test_button.configure(style="Count.TButton")
            self.test_button.update()
        product_name = self.control.product_name
        control_no = self.control.control_no
        sheet_no = self.control.sheet_no

        # 保存されたHDR合成後の画像を読み込む。
        product_dir_name = self.control.result_dir_day + product_name + "/"
        dirs_name = product_dir_name + control_no + "/"
        dir_name = dirs_name + sheet_no + "/"
        path = dir_name + "frame.jpg"
        n = np.fromfile(path, dtype=np.uint8)
        frame = cv2.imdecode(n, cv2.IMREAD_COLOR)

        if self.method_num == 0:
            matching_threshold = float(self.matching_th_str.get())
            h_range = int(self.h_range_str.get())
            l_range = int(self.l_range_str.get())
            s_range = int(self.s_range_str.get())
            self.control.set_hls_range(h_range, l_range, s_range)  # 読み取った値をHLSRangeにセット。
            # カウント
            result = self.control.count(self.method_num, product_name, control_no, sheet_no, True,
                                        self.control.main_window.cap,
                                        frame,
                                        matching_threshold=matching_threshold,
                                        h_range=h_range, l_range=l_range, s_range=s_range)
        else:
            erode_size = int(self.erode_size_str.get())
            dilate_size = int(self.dilate_size_str.get())
            thresh_area = int(self.thresh_area_str.get())
            # カウント
            result = self.control.count(self.method_num, product_name, control_no, sheet_no, True,
                                        self.control.main_window.cap,
                                        frame,
                                        matching_threshold=None,
                                        erode_size=erode_size,
                                        dilate_size=dilate_size,
                                        thresh_area=thresh_area)
        # カウント結果をメインウィンドウに反映
        self.control.main_window.is_count = result[6]
        self.control.main_window.new_count = self.control.main_window.is_count
        self.control.main_window.img_draw = result[7]
        self.control.main_window.result_count = result
        theoretical_amount = result[5]
        self.control.main_window.display_result(self.control.main_window.is_count, self.control.main_window.img_draw)
        # カウント数より理論数量が小さければ良品数を赤色で表示する
        if self.control.main_window.is_count > theoretical_amount:
            self.control.main_window.count_result.configure(foreground="#8b0000")
        if self.test_button.winfo_exists() == 1:  # テストボタンを元に戻す
            self.test_button.configure(text=u"テストカウント")
            self.test_button.configure(style="TButton")
            self.test_button.configure(state="disabled")
            self.change_button.configure(state="normal")
            self.test_button.update()

    def change_settings(self):
        """
        ウィジェットから設定値をとってきてファイルの中身を更新する
        :return:
        """
        product_name = self.control.main_window.product.get()
        setting_file = self.control.setting_dir + product_name + ".pkl"  # 変更するファイル名
        if os.path.exists(setting_file) is False:  # ファイルがない場合は何もしない
            return True
        matching_threshold = float(self.matching_th_str.get())
        h_range = int(self.h_range_str.get())
        l_range = int(self.l_range_str.get())
        s_range = int(self.s_range_str.get())
        erode_size = int(self.erode_size_str.get())
        dilate_size = int(self.dilate_size_str.get())
        thresh_area = int(self.thresh_area_str.get())
        create_setting_file(self.control.setting_dir, product_name,
                            matching_threshold, erode_size, dilate_size, thresh_area,
                            h_range, l_range, s_range)
        self.control.change_setting(product_name)  # controllerが保持する設定値の変更
        if self.method_num == 0:
            self.control.main_window.matching_threshold_str.set(str(matching_threshold))
        else:
            self.control.main_window.erode_str_cnt.set(str(erode_size))
            self.control.main_window.dilate_str_cnt.set(str(dilate_size))
            self.control.main_window.thresh_area_str_cnt.set(str(thresh_area))
        sub_win = tk.Toplevel(self.master)
        error_window = ErrorMessage(sub_win)
        error_window.color_change()
        error_window.set_message("設定が変更されました。")
        self.test_button.configure(state="disabled")
        self.change_button.configure(state="disabled")
